import pulp

def add_s3_care_continuity_penalty(model: pulp.LpProblem, data: dict, index_sets, var_dict) -> pulp.LpAffineExpression:
    # 索引修正
    patient_ids = index_sets["patient_ids"]
    nurse_ids = index_sets["nurse_ids"]
    room_ids = index_sets["room_ids"]
    day_range = index_sets["day_range"]
    shift_types = index_sets["room_ids"]

    patients = data["patients"]
    nurses = data["nurses"]
    weight_s3 = data["weights"]["continuity_of_care"]

    y = var_dict["y_patient_room"]
    x = var_dict["x_nurse_room_shift"]

    # 病人p是否被护士n照看过
    assign_p_n = pulp.LpVariable.dicts(
        "s3_assign_patient_nurse",
        (patient_ids, nurse_ids),
        cat=pulp.LpBinary
    )
    # 看护该病人的护士总数
    distinct_nurse_cnt = pulp.LpVariable.dicts(
        "s3_distinct_nurse_count",
        patient_ids,
        lowBound=0, cat=pulp.LpInteger
    )
    # 超额护士惩罚
    pen_continuity = pulp.LpVariable.dicts(
        "s3_pen_continuity_excess",
        patient_ids,
        lowBound=0, cat=pulp.LpContinuous
    )

    s3_total_expr = pulp.LpAffineExpression()

    # 第一步：线性化 病人+护士同时出现则assign=1
    for p in patients:
        pid = p["id"]
        adm_day = p.get("admission_day", "none")
        if adm_day == "none":
            continue
        for n in nurses:
            nid = n["id"]
            # 只要任意房间/天/班次同时有病人、护士，assign至少1
            for rid in room_ids:
                for d in day_range:
                    for s in shift_types:
                        model += assign_p_n[pid][nid] >= y[pid][rid][d] + x[nid][rid][d] - 1, \
                            f"S3_link_{pid}_{nid}_{rid}_{d}_{s}"
            # 修复关键BUG：二维索引 [pid][nid]
            model += assign_p_n[pid][nid] <= 1, f"S3_binlimit_{pid}_{nid}"

    # 第二步：统计每个病人总看护护士数量
    for p in patients:
        pid = p["id"]
        adm_day = p.get("admission_day", "none")
        if adm_day == "none":
            continue
        total_nurse = 0
        for n in nurses:
            nid = n["id"]
            total_nurse += assign_p_n[pid][nid]
        model += distinct_nurse_cnt[pid] == total_nurse, f"S3_sum_{pid}"
        # 超过3名护士产生惩罚
        model += pen_continuity[pid] >= distinct_nurse_cnt[pid] - 3, f"S3_pen_{pid}"
        s3_total_expr += weight_s3 * pen_continuity

    return s3_total_expr