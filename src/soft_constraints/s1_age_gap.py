import pulp

def add_s1_age_gap_penalty(model: pulp.LpProblem, data: dict, index_sets: dict, var_dict: dict) -> pulp.LpAffineExpression:
    """
    S1 Age group gap soft constraint: Minimize maximum age group difference inside each room per day
    Construct penalty terms and return total S1 penalty expression to be added to global objective
    Args:
        model: pulp MILP model instance
        data: raw loaded instance json data
        index_sets: pre-defined index sets dict
        var_dict: all decision variables dict (y_patient_room required)
    Return:
        pulp.LpAffineExpression: total weighted penalty expression of S1
    """
    # Unpack index & data
    room_ids = index_sets["room_ids"]
    day_range = index_sets["day_range"]
    patients = data["patients"]
    # Correction: Match JSON weight key room_mixed_age
    weight_s1 = data["weights"]["room_mixed_age"]
    y = var_dict["y_patient_room"]

    # Map string age_group to numeric value for difference calculation
    age_mapping = {
        "infant": 1,
        "adult": 2,
        "elderly": 3
    }
    # Precompute global max numeric age group for Big-M
    max_age_num = max(age_mapping[p["age_group"]] for p in patients)

    # Auxiliary continuous variable: max age group gap for room r on day d
    pen_age_gap = pulp.LpVariable.dicts(
        "s1_pen_age_gap",
        (room_ids, day_range),
        lowBound=0,
        cat=pulp.LpContinuous
    )

    s1_total_expr = 0

    for rid in room_ids:
        for d in day_range:
            # Aux variables to track current room-day max / min numeric age group
            max_age = pulp.LpVariable(f"s1_max_age_r{rid}_d{d}", lowBound=0, cat=pulp.LpContinuous)
            min_age = pulp.LpVariable(f"s1_min_age_r{rid}_d{d}", lowBound=0, cat=pulp.LpContinuous)

            # Constraint 1: max_age >= numeric age of every patient staying in this room-day
            for p in patients:
                pid = p["id"]
                ag_num = age_mapping[p["age_group"]]
                model += max_age >= ag_num * y[pid][rid][d], f"S1_max_ge_p{pid}_r{rid}_d{d}"

            # Constraint 2: min_age <= numeric age of every occupied patient; ignore empty beds with Big-M
            for p in patients:
                pid = p["id"]
                ag_num = age_mapping[p["age_group"]]
                model += min_age <= ag_num * y[pid][rid][d] + (1 - y[pid][rid][d]) * max_age_num, f"S1_min_le_p{pid}_r{rid}_d{d}"

            # Penalty variable lower bound equals age gap (max - min)
            model += pen_age_gap[rid][d] >= max_age - min_age, f"S1_gap_penalty_r{rid}_d{d}"

            # Accumulate weighted penalty
            s1_total_expr += weight_s1 * pen_age_gap[rid][d]

    return s1_total_expr