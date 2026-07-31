import pulp

def add_s5_open_ot_penalty(model: pulp.LpProblem, data: dict, index_sets: dict, var_dict: dict) -> pulp.LpAffineExpression:
    """
    S5 Open Operating Theatre Soft Constraint
    Rule: OT opened if any surgeon uses it that day; each open OT adds fixed penalty
    Penalty = open_ot_flag * open_operating_theater_weight
    """
    # Unpack index sets
    ot_ids = index_sets["ot_ids"]
    day_range = index_sets["day_range"]
    surgeon_ids = index_sets["surgeon_ids"]

    # Weight config
    weight_s5 = data["weights"]["open_operating_theater"]
    max_surg = len(surgeon_ids)  # Big-M上限

    # Core assignment var: ot_surg_assign[sur][ot][day] binary
    ot_surg_assign = var_dict["ot_surg_assign"]

    # Binary flag: whether operating theater tid opens on day d
    ot_open = pulp.LpVariable.dicts(
        "s5_ot_open_flag",
        (ot_ids, day_range),
        cat=pulp.LpBinary
    )
    total_s5_expr = pulp.LpAffineExpression()

    for tid in ot_ids:
        for d in day_range:
            # 约束1：任意医生使用手术室 → 手术室必须开启
            # ot_open >= 任意单个分配变量，等效只要有1个=1则ot_open=1
            for sur in surgeon_ids:
                model += ot_open[tid][d] >= ot_surg_assign[sur][tid][d], f"S5_usage_bind_t{tid}_d{d}_sur{sur}"

            # 约束2：手术室关闭，则当天无医生可分配（可选，严格贴合题意）
            sum_usage = pulp.lpSum([ot_surg_assign[sur][tid][d] for sur in surgeon_ids])
            model += sum_usage <= max_surg * ot_open[tid][d], f"S5_close_limit_t{tid}_d{d}"

            # 累加惩罚
            total_s5_expr += weight_s5 * ot_open[tid][d]

    return total_s5_expr