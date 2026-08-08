import pulp

def add_s8_unscheduled_optional_penalty(model: pulp.LpProblem, data: dict, index_sets: dict, var_dict: dict) -> pulp.LpAffineExpression:
    """
    S8 Unscheduled optional patients Soft Constraint
    Rule: Penalise optional patients who are not admitted on any day.
    Weight key: unscheduled_optional
    Logic:
        unscheduled=1 <=> patient has zero admission in all days
        Penalty = weight * sum(unscheduled binary variables)
    """
    patient_ids = index_sets["patient_ids"]
    day_range = index_sets["day_range"]
    patients = data["patients"]
    weight_s8 = data["weights"]["unscheduled_optional"]
    day_count = len(day_range)

    admit = var_dict["admit_var"]
    total_s8_penalty = pulp.LpAffineExpression()

    for p in patients:
        pid = p["id"]
        # Skip mandatory patients, only optional patients are constrained
        if p["mandatory"]:
            continue

        # Total admission count across planning horizon
        sum_admit = pulp.lpSum([admit[pid][d] for d in day_range])
        # Binary flag: 1 = never admitted, 0 = admitted at least once
        unscheduled = pulp.LpVariable(f"s8_unsched_{pid}", cat=pulp.LpBinary)

        # Constraint 1: unscheduled=0 → at least one admission
        model += sum_admit >= 1 - unscheduled, f"S8_flag_low_p{pid}"
        # Constraint 2: unscheduled=1 → no admission allowed (critical fix)
        model += sum_admit <= day_count * (1 - unscheduled), f"S8_flag_high_p{pid}"

        # Accumulate penalty term
        total_s8_penalty += weight_s8 * unscheduled

    return total_s8_penalty