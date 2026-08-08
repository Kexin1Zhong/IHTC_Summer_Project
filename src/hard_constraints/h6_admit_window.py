import pulp

def add_h6_constraint(model, data, index_sets, var_dict):
    """
    H6 Hard Constraint: Patient admission must be within release day window; mandatory patients have fixed due deadline
    New added binding constraint: If admitted on day d, patient must occupy at least one room on day d
    Supplement constraint: One patient can only be admitted on at most one single day
    """
    patients = data["patients"]
    day_range = index_sets["day_range"]
    admit_var = var_dict["admit_var"]
    y_patient_room = var_dict["y_patient_room"]
    room_ids = index_sets["room_ids"]

    # ========== H6 第一部分：入院时间窗口约束 ==========
    # 1. 强制患者：仅 [release_day, due_day] 可入院
    # 2. 可选患者：早于release_day不可入院，无最晚截止
    for p in patients:
        pid = p["id"]
        release_day = p["surgery_release_day"]
        if p["mandatory"]:
            due_day = p["surgery_due_day"]
            for d in day_range:
                if d < release_day or d > due_day:
                    model += admit_var[pid][d] == 0, f"H6_mandatory_p{pid}_invalid_day{d}"
        else:
            for d in day_range:
                if d < release_day:
                    model += admit_var[pid][d] == 0, f"H6_optional_p{pid}_invalid_day{d}"

    # ========== H6 第二部分：入院-床位绑定约束 ==========
    # admit=1 → 当日必须占用任意病房床位
    for p in patients:
        pid = p["id"]
        for d in day_range:
            model += (
                pulp.lpSum([y_patient_room[pid][rid][d] for rid in room_ids]) >= admit_var[pid][d],
                f"H6_bind_admit_room_p{pid}_d{d}"
            )

    # ========== H6 第三部分：新增约束：单个患者最多仅1天入院（修复漏洞） ==========
    for p in patients:
        pid = p["id"]
        model += (
            pulp.lpSum([admit_var[pid][d] for d in day_range]) <= 1,
            f"H6_single_admit_limit_p{pid}"
        )


def validate_h6_solution(sol_data, index_sets, var_dict):
    """
    Post-solution validation for H6 admission time window rule
    Detect: out-of-window admission, multiple-day admission, admission without room occupation
    Return total violation count and print violation logs
    """
    patients = sol_data["patients"]
    day_range = index_sets["day_range"]
    admit = var_dict["admit_var"]
    y_patient_room = var_dict["y_patient_room"]
    room_ids = index_sets["room_ids"]
    h6_violation_count = 0

    for p in patients:
        pid = p["id"]
        release_day = p["surgery_release_day"]
        is_mandatory = p["mandatory"]
        admit_days = []
        if is_mandatory:
            due_day = p["surgery_due_day"]

        # 收集所有入院日期 + 校验窗口合法性
        for d in day_range:
            admit_flag = pulp.value(admit[pid][d])
            if admit_flag < 1e-6:
                continue
            admit_days.append(d)
            # 校验入院窗口
            if is_mandatory:
                if d < release_day or d > due_day:
                    h6_violation_count += 1
                    print(f"H6 VIOLATION: Mandatory patient {pid} admitted on Day {d} (valid window [{release_day}, {due_day}])")
            else:
                if d < release_day:
                    h6_violation_count += 1
                    print(f"H6 VIOLATION: Optional patient {pid} admitted on Day {d} (earlier than release day {release_day})")

        # 校验：同一患者多日入院
        if len(admit_days) > 1:
            h6_violation_count += 1
            print(f"H6 VIOLATION: Patient {pid} admitted on multiple days {admit_days}")

        # 校验：入院当日无床位占用
        for d in admit_days:
            room_sum = sum(pulp.value(y_patient_room[pid][rid][d]) for rid in room_ids)
            if room_sum < 1e-6:
                h6_violation_count += 1
                print(f"H6 VIOLATION: Patient {pid} admitted on Day {d} but no room occupied")

    if h6_violation_count == 0:
        print("✅ H6 Test Passed: All patient admissions comply with H6 full rules")
    else:
        print(f"❌ H6 Test Failed, total {h6_violation_count} H6 rule violations")
    return h6_violation_count