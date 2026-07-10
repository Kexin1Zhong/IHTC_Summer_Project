import pulp

def add_s3_care_continuity_penalty(model: pulp.LpProblem, data: dict, index_sets: dict, var_dict: dict) -> pulp.LpAffineExpression:
    """
    S3 Continuity of care soft constraint
    Minimize distinct nurses caring for each patient over their stay
    Base minimum distinct nurses per patient = 3, penalty = max(0, distinct_nurse - 3) * weight
    Args:
        model: pulp MILP model instance
        data: raw input json dataset
        index_sets: pre-defined index set dict
        var_dict: decision variables dict (y_patient_room, x_nurse_room_shift required)
    Return:
        pulp.LpAffineExpression: total weighted penalty expression of S3 for objective
    """
    # Unpack index sets
    patient_ids = index_sets["patient_ids"]
    nurse_ids = index_sets["nurse_ids"]
    room_ids = index_sets["room_ids"]
    day_range = index_sets["day_range"]
    shift_types = index_sets["shift_types"]

    # Raw data & weight
    patients = data["patients"]
    nurses = data["nurses"]
    weight_s3 = data["weights"]["continuity_of_care"]

    # Core decision variables
    y = var_dict["y_patient_room"]
    x = var_dict["x_nurse_room_shift"]

    # Aux 1: Binary flag assign_p_n[p][n] = 1 if nurse n ever cares for patient p
    assign_p_n = pulp.LpVariable.dicts(
        "s3_assign_patient_nurse",
        (patient_ids, nurse_ids),
        cat=pulp.LpBinary
    )

    # Aux 2: Count distinct nurses for each patient p
    distinct_nurse_cnt = pulp.LpVariable.dicts(
        "s3_distinct_nurse_count",
        patient_ids,
        lowBound=0,
        cat=pulp.LpContinuous
    )

    # Aux 3: Continuity penalty for excess nurses over minimum 3
    pen_continuity = pulp.LpVariable.dicts(
        "s3_pen_continuity_excess",
        patient_ids,
        lowBound=0,
        cat=pulp.LpContinuous
    )

    s3_total_expr = 0

    # Step1: Linearize assign_p_n[p][n] = 1 if p and n overlap on any room-day-shift
    for p in patients:
        pid = p["id"]
        for n in nurses:
            nid = n["id"]
            # If any room/day/shift has y[p][r][d] & x[n][r][d][s] = 1, assign_p_n = 1
            for rid in room_ids:
                for d in day_range:
                    for s in shift_types:
                        model += assign_p_n[pid][nid] >= y[pid][rid][d] + x[nid][rid][d][s] - 1, f"S3_flag_p{pid}_n{nid}_r{rid}_d{d}_{s}"

    # Step2: Sum assign flags to get total distinct nurses per patient
    for p in patients:
        pid = p["id"]
        sum_nurse_flags = 0
        for n in nurses:
            nid = n["id"]
            sum_nurse_flags += assign_p_n[pid][nid]
        model += distinct_nurse_cnt[pid] == sum_nurse_flags, f"S3_count_sum_p{pid}"

        # Step3: Penalty = max(0, distinct_nurse_cnt - 3)
        model += pen_continuity[pid] >= distinct_nurse_cnt[pid] - 3, f"S3_penalty_min3_p{pid}"

        # Step4: Accumulate weighted penalty
        s3_total_expr += weight_s3 * pen_continuity[pid]

    return s3_total_expr