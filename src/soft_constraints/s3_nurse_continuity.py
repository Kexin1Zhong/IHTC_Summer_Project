import pulp

def add_s3_care_continuity_penalty(model: pulp.LpProblem, data: dict, index_sets, var_dict) -> pulp.LpAffineExpression:
    patient_ids = index_sets["patient_ids"]
    nurse_ids = index_sets["nurse_ids"]
    room_ids = index_sets["room_ids"]
    day_range = index_sets["day_range"]
    shift_types = index_sets["shift_types"]

    patients_raw = data["patients"]
    weight_s3 = data["weights"]["continuity_of_care"]

    y = var_dict["y_patient_room"]
    x = var_dict["x_nurse_room_shift"]

    total_s3 = pulp.LpAffineExpression()
    adm_map = {}
    stay_end_map = {}
    for p in patients_raw:
        pid = p["id"]
        adm_day = p["surgery_release_day"]
        los = p["length_of_stay"]
        dis_day = adm_day + los
        adm_map[pid] = adm_day
        stay_end_map[pid] = dis_day

    valid_patient_cnt = 0
    max_link = len(day_range) * len(shift_types)

    for pid in patient_ids:
        adm_day = adm_map[pid]
        dis_day = stay_end_map[pid]
        if adm_day is None or dis_day is None:
            continue
        valid_patient_cnt += 1
        valid_days = [d for d in day_range if adm_day <= d <= dis_day]

        care_link = pulp.LpVariable.dicts(
            "s3_care_link",
            (nurse_ids, room_ids, valid_days, shift_types),
            cat=pulp.LpBinary
        )
        unique_nurse = pulp.LpVariable.dicts("s3_unique_nurse", nurse_ids, cat=pulp.LpBinary)
        nurse_count = pulp.LpVariable("s3_nurse_cnt_" + pid, lowBound=0, cat=pulp.LpInteger)
        s3_penalty = pulp.LpVariable("s3_penalty_" + pid, lowBound=0, cat=pulp.LpContinuous)

        for rid in room_ids:
            for nid in nurse_ids:
                for d in valid_days:
                    for s in shift_types:
                        cl = care_link[nid][rid][d][s]
                        model += cl <= y[pid][rid][d]
                        model += cl <= x[nid][rid][d][s]
                        model += cl >= y[pid][rid][d] + x[nid][rid][d][s] - 1

        for nid in nurse_ids:
            sum_cl = pulp.lpSum([care_link[nid][r][d][s] for r in room_ids for d in valid_days for s in shift_types])
            model += sum_cl <= unique_nurse[nid] * max_link

        model += nurse_count == pulp.lpSum([unique_nurse[nid] for nid in nurse_ids])
        model += s3_penalty >= nurse_count - 3
        model += s3_penalty >= 0
        model += s3_penalty <= nurse_count
        total_s3 += weight_s3 * s3_penalty

    return total_s3