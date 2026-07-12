import pulp

def add_s6_surgeon_transfer_penalty(model: pulp.LpProblem, data: dict, index_sets: dict, var_dict: dict) -> pulp.LpAffineExpression:
    """
    S6 Surgeon transfer Soft Constraint
    Rule: Minimize number of distinct OTs assigned to a surgeon on each working day
    Penalty = count of different OTs used by surgeon per day × weight
    Weight key: surgeon_transfer
    """
    # Unpack index sets
    surgeon_ids = index_sets["surgeon_ids"]
    ot_ids = index_sets["ot_ids"]
    day_range = index_sets["day_range"]

    # Raw weight
    weight_s6 = data["weights"]["surgeon_transfer"]
    big_m_ot = len(ot_ids)

    # Core variable: surgeon-OT daily assignment
    ot_surg_assign = var_dict["ot_surg_assign"]

    # Aux binary flag: sur_ot_used[sur][ot][d] = 1 if surgeon uses OT ot on day d
    sur_ot_used = pulp.LpVariable.dicts(
        "s6_surgeon_ot_used",
        (surgeon_ids, ot_ids, day_range),
        cat=pulp.LpBinary
    )
    total_s6_penalty = 0

    # Loop surgeon → day → OT
    for sur in surgeon_ids:
        for d in day_range:
            daily_distinct_ot = 0
            for tid in ot_ids:
                # If surgeon assigned to OT on day d → mark OT as used
                model += sur_ot_used[sur][tid][d] >= ot_surg_assign[sur][tid][d], f"S6_s{sur}_ot{tid}_d{d}_used"
                daily_distinct_ot += sur_ot_used[sur][tid][d]

            # Accumulate transfer penalty for this surgeon-day
            total_s6_penalty += weight_s6 * daily_distinct_ot

    return total_s6_penalty