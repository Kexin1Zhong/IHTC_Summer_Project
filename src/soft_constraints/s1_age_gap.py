import pulp

def add_s1_age_gap_penalty(model: pulp.LpProblem, data: dict, index_sets: dict, var_dict: dict) -> pulp.LpAffineExpression:
    """
    S1 Age group gap soft constraint:
    For each day and each room, minimize maximum difference between age‑groups of patients sharing that room.
    No penalty for empty room or room with single patient.
    Return weighted total penalty expression for global objective.
    """
    room_ids = index_sets["room_ids"]
    day_range = index_sets["day_range"]
    patients = data["patients"]
    weight_s1 = data["weights"]["room_mixed_age"]
    y = var_dict["y_patient_room"]

    age_mapping = {
        "infant": 1,
        "adult": 2,
        "elderly": 3
    }
    max_age_num = max(age_mapping[p["age_group"]] for p in patients)
    min_age_num = min(age_mapping[p["age_group"]] for p in patients)
    M = max_age_num - min_age_num

    pen_age_gap = pulp.LpVariable.dicts(
        "s1_pen_age_gap",
        (room_ids, day_range),
        lowBound=0,
        cat=pulp.LpContinuous
    )
    # Aux binary: 1 if room rid on day d has at least one patient
    room_occupy = pulp.LpVariable.dicts(
        "s1_room_occ",
        (room_ids, day_range),
        cat=pulp.LpBinary
    )

    s1_total_expr = 0

    for rid in room_ids:
        for d in day_range:
            max_age = pulp.LpVariable(f"s1_max_age_r{rid}_d{d}", lowBound=0, cat=pulp.LpContinuous)
            min_age = pulp.LpVariable(f"s1_min_age_r{rid}_d{d}", lowBound=0, cat=pulp.LpContinuous)

            # room_occupy indicator: sum(y) >0 → 1
            model += pulp.lpSum([y[p["id"]][rid][d] for p in patients]) >= room_occupy[rid][d]
            model += pulp.lpSum([y[p["id"]][rid][d] for p in patients]) <= len(patients) * room_occupy[rid][d]

            for p in patients:
                pid = p["id"]
                ag_num = age_mapping[p["age_group"]]
                # max_age >= age of assigned patient (active when room occupied)
                model += max_age >= ag_num * y[pid][rid][d]
                model += max_age <= max_age_num * room_occupy[rid][d]

                # min_age bound
                model += min_age <= ag_num * y[pid][rid][d] + max_age_num * (1 - y[pid][rid][d])
                model += min_age >= min_age_num * room_occupy[rid][d]

            # Penalty >= age gap; zero penalty when room empty
            model += pen_age_gap[rid][d] >= max_age - min_age
            model += pen_age_gap[rid][d] <= M * room_occupy[rid][d]

            s1_total_expr += weight_s1 * pen_age_gap[rid][d]

    return s1_total_expr