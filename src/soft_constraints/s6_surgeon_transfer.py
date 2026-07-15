import pulp

def add_s6_surgeon_transfer_penalty(model: pulp.LpProblem, data: dict, index_sets: dict, var_dict: dict) -> pulp.LpAffineExpression:
    """
    S6 Surgeon transfer Soft Constraint
    Rule: Minimize number of distinct OTs assigned to a surgeon on each working day
    Penalty = (distinct OT count per surgeon per day - 1) × weight
    Only penalize when surgeon uses ≥2 different OTs in one day
    Weight key: surgeon_transfer
    """
    # Unpack index sets
    surgeon_ids = index_sets["surgeon_ids"]
    ot_ids = index_sets["ot_ids"]
    day_range = index_sets["day_range"]
    penalty_weights = index_sets["penalty_weights"]

    # Fetch penalty weight from unified index set
    weight_s6 = penalty_weights["surgeon_transfer"]

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
                # Two-way bound to lock sur_ot_used exactly equal to assignment
                model += sur_ot_used[sur][otid][d] >= ot_surg_assign[sur][otid][d], f"S6_s{sur}_ot{otid}_d{d}_lb"
                model += sur_ot_used[sur][otid][d] <= ot_surg_assign[sur][otid][d], f"S6_s{sur}_ot{otid}_d{d}_ub"
                daily_distinct_ot += sur_ot_used[sur][otid][d]

            # Key fix: subtract 1, only penalize extra OT rooms
            penalty_per_day = weight_s6 * (daily_distinct_ot - 1)
            total_s6_penalty += penalty_per_day

    return total_s6_penalty