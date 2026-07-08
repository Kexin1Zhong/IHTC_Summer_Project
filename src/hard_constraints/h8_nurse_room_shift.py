import pulp

def add_h8_constraint(model, data, index_sets, var_dict):
    """
    H8 Hard Constraint: Any room with patients must have at least one assigned nurse for every shift on that day
    """
    # 提取所需数据与索引
    patients = data["patients"]
    rooms = data["rooms"]
    nurse_ids = index_sets["nurse_ids"]
    room_ids = index_sets["room_ids"]
    day_range = index_sets["day_range"]
    shift_list = index_sets["shifts"]
    y_patient_room = var_dict["y_patient_room"]
    x_nurse_room = var_dict["x_nurse_room"]

    # 预存房间容量，用于Big-M
    room_cap_dict = {r["id"]: r["capacity"] for r in rooms}

# Hard Constraint Formal Instruction:
    # 1. For any room r, any day d, any shift s: if the room contains at least one patient on day d,
    #    at least one nurse must be assigned to this room during shift s.
    # 2. Empty rooms (zero patients) have no mandatory nurse assignment requirement.
    # 3. Auxiliary binary variable has_patient: has_patient = 1 if room r has ≥1 patient on day d; else 0.
    # 4. Linking big-M constraint: If total room occupants > 0, force has_patient = 1.
    # 5. Core constraint: Total assigned nurses for the shift ≥ has_patient, which enforces nurse assignment only for occupied rooms.
    for r in room_ids:
        for d in day_range:
            # Total patients staying in room r on day d
            room_occupied = pulp.lpSum([y_patient_room[p["id"]][r][d] for p in patients])
            # Get pre-cached room maximum capacity for Big-M parameter
            room_cap = room_cap_dict[r]
            # Binary auxiliary flag to mark room occupancy status
            has_patient = pulp.LpVariable(f"H8_hasPatient_r{r}_d{d}", cat=pulp.LpBinary)
            # Link occupancy sum to binary flag
            model += room_occupied <= room_cap * has_patient, f"H8_linkFlag_r{r}_d{d}"
            # Apply nurse assignment rule for every shift
            for s in shift_list:
                total_nurse_on_shift = pulp.lpSum([x_nurse_room[n][r][d][s] for n in nurse_ids])
                # Core H8 hard constraint
                model += total_nurse_on_shift >= has_patient, f"H8_core_r{r}_d{d}_s{s}"


def validate_h8_solution(sol_data, index_sets, var_dict):
    """
    H8 校验函数：检查有人的房间每个班次都分配了护士
    """
    patients = sol_data["patients"]
    rooms = sol_data["rooms"]
    nurse_ids = index_sets["nurse_ids"]
    room_ids = index_sets["room_ids"]
    day_range = index_sets["day_range"]
    shift_list = index_sets["shifts"]
    y = var_dict["y_patient_room"]
    x = var_dict["x_nurse_room"]

    h8_violation_count = 0

    for r in room_ids:
        for d in day_range:
            # 统计当日房间是否有人
            total_p = 0.0
            for p in patients:
                pid = p["id"]
                total_p += pulp.value(y[pid][r][d])
            # 房间为空，跳过校验
            if total_p < 1e-6:
                continue
            # 房间有人，遍历所有班次检查护士
            for s in shift_list:
                nurse_sum = 0.0
                for n in nurse_ids:
                    nurse_sum += pulp.value(x[n][r][d][s])
                if nurse_sum < 1e-6:
                    h8_violation_count += 1
                    print(f"H8 VIOLATION: Room {r}, Day {d}, Shift {s} has patients but no assigned nurse")

    if h8_violation_count == 0:
        print("✅ H8 Test Passed: All occupied rooms have nurse coverage for every shift")
    else:
        print(f"❌ H8 Test Failed, total {h8_violation_count} nurse coverage violations")
    return h8_violation_count