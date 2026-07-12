import pulp

def add_s5_open_ot_penalty(model: pulp.LpProblem, data: dict, index_sets: dict, var_dict: dict) -> pulp.LpAffineExpression:
    """
    S5 Open Operating Theatre Soft Constraint
    Rule: Minimize daily opened OT count. OT only opens if any surgeon uses it that day.
    Penalty = opened OT count per day × weight
    Weight key: open_operating_theater
    Adapted to your dataset: OT usage is stored in ot_surg_assign[sur][ot][day]
    """
    # Unpack index sets
    ot_ids = index_sets["ot_ids"]
    day_range = index_sets["day_range"]
    surgeon_ids = index_sets["surgeon_ids"]

    # Raw weight
    weight_s5 = data["weights"]["open_operating_theater"]
    big_m_surgeon = len(surgeon_ids)  # Big-M: max surgeons using one OT per day

    # Core variable: surgeon-OT daily assignment
    ot_surg_assign = var_dict["ot_surg_assign"]

    # Binary flag: ot_open[ot][d] = 1 if OT opens on day d
    ot_open = pulp.LpVariable.dicts(
        "s5_ot_open_flag",
        (ot_ids, day_range),
        cat=pulp.LpBinary
    )
    total_s5_penalty = 0

    # Iterate every OT & every day
    for tid in ot_ids:
        for d in day_range:
            # Sum all surgeons assigned to this OT on day d
            total_surgeons_use_ot = pulp.lpSum([
                ot_surg_assign[sur][tid][d]
                for sur in surgeon_ids
            ])
            # If any surgeon uses OT t on day d → ot_open must be 1
            model += ot_open[tid][d] >= total_surgeons_use_ot / big_m_surgeon, f"S5_ot{tid}_d{d}_open_req"
            # Accumulate penalty
            total_s5_penalty += weight_s5 * ot_open[tid][d]

    return total_s5_penalty