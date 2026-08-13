import pulp

def add_h9_stay_duration_debug(model, data, index_sets, var_dict):
    patients = data["patients"]
    day_range = index_sets["day_range"]
    room_ids = index_sets["room_ids"]
    slack_list = []

    for p in patients:
        pid = p["id"]
        los = p["length_of_stay"]
        for d in day_range:
            for k in range(los):
                day_stay = d + k
                if day_stay not in day_range:
                    continue
                slack = pulp.LpVariable(f"slack_h9_{pid}_{d}_{day_stay}", lowBound=0, cat=pulp.LpContinuous)
                slack_list.append(slack)
                model += (
                    pulp.lpSum([var_dict["y_patient_room"][pid][rid][day_stay] for rid in room_ids]) + slack
                    >= var_dict["admit_var"][pid][d],
                    f"H9_stay_debug_{pid}_d{d}_s{day_stay}"
                )
    # 重点：把所有slack加到目标，给一个很大权重，强迫求解器尽量少用slack
    penalty_weight = 10000
    h9_penalty_expr = penalty_weight * pulp.lpSum(slack_list)
    return h9_penalty_expr