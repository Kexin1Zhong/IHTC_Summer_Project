import pulp

def add_h6_constraint(model, data, index_sets, var_dict):
    """
    H6 Hard Constraint: Patient admission must be within release day window; mandatory patients have fixed due deadline
    """
    patients = data["patients"]
    day_range = index_sets["day_range"]
    admit_var = var_dict["admit_var"]

    # ========== H6 第一部分：入院时间窗口约束（原题要求） ==========
    # 1. mandatory患者：仅 [release_day, due_day] 允许入院
    # 2. optional患者：d >= release_day 允许入院，无due截止
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

    # ========== 已全部移除：自行增加的 admit→当日占房间 绑定约束 + slack调试代码 ==========
    # 该绑定不属于官方H6硬约束，会造成数据集可行解被人为掐掉，导致infeasible


def validate_h6_solution(sol_data, index_sets, var_dict):
    """
    Post‑solution validation for H6 admission time window rule
    Detect: out‑of‑window admission, multiple‑day admission
    Return total violation count and print violation logs
    """
    patients = sol_data["patients"]
    day_range = index_sets["day_range"]
    admit = var_dict["admit_var"]
    h6_violation_count = 0

    for p in patients:
        pid = p["id"]
        release_day = p["surgery_release_day"]
        is_mandatory = p["mandatory"]
        admit_days = []
        if is_mandatory:
            due_day = p["surgery_due_day"]

        # collect admission days & check window
        for d in day_range:
            admit_flag = pulp.value(admit[pid][d])
            if admit_flag < 1e-6:
                continue
            admit_days.append(d)
            if is_mandatory:
                if d < release_day or d > due_day:
                    h6_violation_count += 1
                    print(f"H6 VIOLATION: Mandatory patient {pid} admitted on Day {d} (valid window [{release_day}, {due_day}])")
            else:
                if d < release_day:
                    h6_violation_count += 1
                    print(f"H6 VIOLATION: Optional patient {pid} admitted on Day {d} (earlier than release day {release_day})")

        # check multiple admission days
        if len(admit_days) > 1:
            h6_violation_count += 1
            print(f"H6 VIOLATION: Patient {pid} admitted on multiple days {admit_days}")

    if h6_violation_count == 0:
        print("✅ H6 Test Passed: All patient admissions comply with H6 full rules")
    else:
        print(f"❌ H6 Test Failed, total {h6_violation_count} H6 rule violations")
    return h6_violation_count