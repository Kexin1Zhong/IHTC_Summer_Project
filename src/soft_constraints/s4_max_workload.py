import pulp

def add_s4_max_workload_penalty(model: pulp.LpProblem, data: dict, index_sets: dict, var_dict: dict) -> pulp.LpAffineExpression:
    """
    S4 Maximum workload Soft Constraint
    纯线性模型：护士单班次总患者负荷超限产生惩罚
    规则：护士单班次总患者负荷超限产生惩罚
    """
    # 索引集合
    room_ids = index_sets["room_ids"]
    day_range = index_sets["day_range"]
    shift_types = index_sets["shift_types"]  # 修复：原错误写patient_ids
    patient_ids = index_sets["patient_ids"]
    nurse_ids = index_sets["nurse_ids"]

    # 基础数据与权重
    patients = data["patients"]
    nurses = data["nurses"]
    weight_s4 = data["weights"]["nurse_eccessive_workload"]
    max_load_upper = 1000  # 大M常数

    # 核心决策变量
    y = var_dict["y_patient_room"]    # y[pid][rid][d] 病人p第d天住r
    x = var_dict["x_nurse_room_shift"]# x[nid][rid][d][s]护士n班次s看管r
    admit = var_dict["admit_var"]    # admit[pid][t0]病人入院日t0

    # 预加载静态常量
    patient_wl = {p["id"]: p["workload_produced"] for p in patients}
    patient_los = {p["id"]: p["length_of_stay"] for p in patients}
    nurse_shift_max = {}
    for n in nurses:
        nid = n["id"]
        shift_limit = {s["shift"]: s["max_load"] for s in n["working_shifts"]}
        nurse_shift_max[nid] = shift_limit

    # 护士-天-班次 超额惩罚变量
    pen_nurse_load = pulp.LpVariable.dicts(
        "s4_nurse_load_penalty",
        (nurse_ids, day_range, shift_types),
        lowBound=0, cat=pulp.LpContinuous
    )
    total_s4 = pulp.LpAffineExpression()

    # 外层：护士 / 天 / 班次
    for n in nurses:
        nid = n["id"]
        for d in day_range:
            for s in shift_types:
                limit = nurse_shift_max[nid].get(s, 0)
                total_load = pulp.LpAffineExpression()

                # 遍历房间
                for rid in room_ids:
                    x_nrs = x[nid][rid][d][s]
                    # 遍历患者
                    for p in patients:
                        pid = p["id"]
                        los = patient_los[pid]
                        wl_arr = patient_wl[pid]
                        y_prd = y[pid][rid][d]
                        # 遍历入院起始天
                        for t0 in day_range:
                            t = d - t0
                            if t < 0 or t >= los:
                                continue
                            w = wl_arr[t]  # 患者第t天固定负荷常数

                            # Z1 = admit[pid][t0] & y[pid][rid][d] 病人当天在该房间住院
                            z1 = pulp.LpVariable(f"s4_z1_{pid}_{rid}_{t0}", cat=pulp.LpBinary)
                            model += z1 <= admit[pid][t0]
                            model += z1 <= y_prd
                            model += z1 >= admit[pid][t0] + y_prd - 1

                            # Z2 = z1 & x_nrs 护士看管该房间+病人当天住院
                            z2 = pulp.LpVariable(f"s4_z2_{nid}_{rid}_{pid}_{t0}", cat=pulp.LpBinary)
                            model += z2 <= z1
                            model += z2 <= x_nrs
                            model += z2 >= z1 + x_nrs - 1

                            # 线性累加常数*二元，无乘法
                            total_load += w * z2

                # 计算本班次超额负荷 max(0, 总负载-上限)
                excess = pulp.LpVariable(f"s4_ex_{nid}_{d}_{s}", lowBound=0, cat=pulp.LpContinuous)
                model += excess >= total_load - limit
                # 移除多余上限约束

                # 绑定惩罚变量
                model += pen_nurse_load[nid][d][s] >= excess
                total_s4 += weight_s4 * pen_nurse_load[nid][d][s]  # 修复：补充[d][s]维度

    return total_s4