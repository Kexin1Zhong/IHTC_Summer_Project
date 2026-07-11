import pulp

def add_s2_nurse_skill_penalty(model: pulp.LpProblem, data: dict, index_sets: dict, var_dict: dict) -> pulp.LpAffineExpression:
    """
    S2 Minimum skill level Soft Constraint (Simplified Low-Version)
    Rule: If assigned nurse skill < patient daily required skill → penalty = req_skill - nurse_skill
    Nurse skill ≥ required: no penalty
    Weight key: room_nurse_skill
    Major optimization: Remove t offset loop, skip patients not occupying room on day d
    """
    # Unpack index sets
    room_ids = index_sets["room_ids"]
    day_range = index_sets["day_range"]
    shift_types = index_sets["shift_types"]
    patient_ids = index_sets["patient_ids"]
    nurse_ids = index_sets["nurse_ids"]
    max_day = max(day_range)

    # Raw input data & penalty weight
    patients = data["patients"]
    nurses = data["nurses"]
    weight_s2 = data["weights"]["room_nurse_skill"]
    max_skill = data["skill_levels"] - 1  # Big-M upper bound for skill gap

    # Unpack core decision variables (unified key names)
    y = var_dict["y_patient_room"]
    x = var_dict["x_nurse_room_shift"]
    admit = var_dict["admit_var"]

    # Pre-cache static patient & nurse data to avoid repeated lookup
    patient_los = {p["id"]: p["length_of_stay"] for p in patients}
    patient_skill_req = {p["id"]: p["skill_level_required"] for p in patients}
    nurse_skill = {n["id"]: n["skill_level"] for n in nurses}

    # Aux variable: total skill shortage penalty for each room-day-shift
    pen_skill_short = pulp.LpVariable.dicts(
        "s2_pen_skill_shortage",
        (room_ids, day_range, shift_types),
        lowBound=0,
        cat=pulp.LpContinuous
    )
    total_s2_penalty = 0

    # Outer triple loop: Room → Day → Shift
    for rid in room_ids:
        for d in day_range:
            for s in shift_types:
                shift_total_shortage = 0

                # Iterate all patients
                for p in patients:
                    pid = p["id"]
                    los = patient_los[pid]
                    req_list = patient_skill_req[pid]
                    y_p_r_d = y[pid][rid][d]

                    # Critical Filter: Skip patient if they do NOT stay in this room on day d
                    # No auxiliary variables/constraints will be generated for skipped patients
                    if y_p_r_d == 0:
                        continue

                    # Calculate patient's relative day of stay t (global day d minus admission day t0)
                    # Enumerate all possible admission days t0 to get valid relative offset t
                    for t0 in day_range:
                        t = d - t0
                        # Skip invalid offset: t out of patient's length of stay range
                        if t < 0 or t >= los:
                            continue
                        # Binary flag: patient admitted on t0 AND occupies this room on day d
                        admit_flag = pulp.LpVariable(f"s2_admit_flag_p{pid}_t0{t0}_d{d}", cat=pulp.LpBinary)
                        model += admit_flag <= admit[pid][t0]
                        model += admit_flag <= y_p_r_d
                        model += admit_flag >= admit[pid][t0] + y_p_r_d - 1

                        # Fixed constant required skill (no variable list index error)
                        fixed_req_skill = req_list[t]

                        # Iterate all nurses assigned to this room-day-shift
                        for n in nurses:
                            nid = n["id"]
                            nurse_s = nurse_skill[nid]
                            x_n_r_d_s = x[nid][rid][d][s]

                            # Binary flag: Nurse n assigned to room r day d shift s
                            assign_flag = pulp.LpVariable(f"s2_nurse_flag_p{pid}_n{nid}_r{rid}_d{d}_{s}", cat=pulp.LpBinary)
                            model += assign_flag <= y_p_r_d
                            model += assign_flag <= x_n_r_d_s
                            model += assign_flag >= y_p_r_d + x_n_r_d_s - 1

                            # Continuous shortage variable: max(0, fixed_req_skill - nurse_s)
                            shortage = pulp.LpVariable(
                                f"s2_shortage_p{pid}_n{nid}_r{rid}_d{d}_{s}_t0{t0}",
                                lowBound=0,
                                cat=pulp.LpContinuous
                            )
                            skill_gap = fixed_req_skill - nurse_s
                            # Linear constraints for shortage calculation
                            model += shortage >= skill_gap * assign_flag - max_skill * (1 - admit_flag)
                            model += shortage <= skill_gap * assign_flag + max_skill * (1 - admit_flag)
                            model += shortage <= max_skill * assign_flag

                            shift_total_shortage += shortage

                # Link total shortage of this room-day-shift to penalty variable
                model += pen_skill_short[rid][d][s] >= shift_total_shortage, f"S2_room{rid}_day{d}_shift{s}_sum"
                # Accumulate weighted global penalty
                total_s2_penalty += weight_s2 * pen_skill_short[rid][d][s]

    return total_s2_penalty