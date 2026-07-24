import pulp

def add_s6_surgeon_transfer_penalty(model: pulp.LpProblem, data: dict, index_sets: dict, var_dict: dict) -> pulp.LpAffineExpression:
    """
    S6 Surgeon transfer Soft Constraint
    Rule: Minimize number of distinct OTs assigned to a surgeon on each working day
    Penalty = max(0, distinct OT count per surgeon per day - 1) × weight
    Only penalize when surgeon uses ≥2 different OTs in one day
    Weight key: surgeon_transfer
    """
    # Unpack index sets
    surgeon_ids = index_sets["surgeon_ids"]
    ot_ids = index_sets["ot_ids"]
    day_range = index_sets["day_range"]

    # ✅ Fix 1: Read weights from data and stop accessing index_sets["penalty_weights"]
    weight_s6 = data["weights"]["surgeon_transfer"]
    max_ot = len(ot_ids)

    # Core variable: surgeon-OT daily assignment
    ot_surg_assign = var_dict["ot_surg_assign"]

    # Aux binary flag: sur_ot_used[sur][ot][d] = 1 if surgeon uses OT ot on day d
    sur_ot_used = pulp.LpVariable.dicts(
        "s6_surgeon_ot_used",
        (surgeon_ids, ot_ids, day_range),
        cat=pulp.LpBinary
    )
    total_s6_penalty = pulp.LpAffineExpression()

    # Loop surgeon → day → OT
    for sur in surgeon_ids:
        for d in day_range:
            daily_distinct_ot = pulp.LpAffineExpression()
            for otid in ot_ids:
                model += sur_ot_used[sur][otid][d] >= ot_surg_assign[sur][otid][d], f"S6_s{sur}_ot{otid}_d{d}_lb"
                model += sur_ot_used[sur][otid][d] <= ot_surg_assign[sur][otid][d], f"S6_s{sur}_ot{otid}_d{d}_ub"
                daily_distinct_ot += sur_ot_used[sur][otid][d]

            # ✅ Fix 2: Linearize max(0, distinct-1) to avoid negative penalties
            transfer_penalty = pulp.LpVariable(f"s6_transfer_s{sur}_d{d}", lowBound=0, cat=pulp.LpContinuous)
            model += transfer_penalty >= daily_distinct_ot - 1
            model += transfer_penalty <= max_ot

            total_s6_penalty += weight_s6 * transfer_penalty

    return total_s6_penalty