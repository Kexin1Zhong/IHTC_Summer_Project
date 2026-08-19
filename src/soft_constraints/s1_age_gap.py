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

    
# Full mapping, compatible with all tags of test01‑06 and test07

    age_mapping = {
        "infant": 1,
        "baby": 1,
        "child": 2,
        "young": 3,
        "adult": 4,
        "elderly": 5
    }

    age_nums = [age_mapping[p["age_group"]] for p in patients]
    max_age_num = max(age_nums)
    min_age_num = min(age_nums)
    M = max_age_num - min_age_num

    pen_age_gap = pulp.LpVariable.dicts(
        "s1_pen_age_gap",
        (room_ids, day_range),
        lowBound=0,
        cat=pulp.LpContinuous
    )
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

            model += pulp.lpSum([y[p["id"]][rid][d] for p in patients]) >= room_occupy[rid][d]
            model += pulp.lpSum([y[p["id"]][rid][d] for p in patients]) <= len(patients) * room_occupy[rid][d]

            for p in patients:
                pid = p["id"]
                ag_num = age_mapping[p["age_group"]]

                model += max_age >= ag_num * y[pid][rid][d]
                model += max_age <= max_age_num * room_occupy[rid][d]

                model += min_age <= ag_num * y[pid][rid][d] + max_age_num * (1 - y[pid][rid][d])
                model += min_age >= min_age_num * room_occupy[rid][d]

            model += pen_age_gap[rid][d] >= max_age - min_age
            model += pen_age_gap[rid][d] <= M * room_occupy[rid][d]

            s1_total_expr += weight_s1 * pen_age_gap[rid][d]

    return s1_total_expr