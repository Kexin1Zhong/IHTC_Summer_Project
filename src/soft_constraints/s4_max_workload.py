import pulp

def add_s4_max_workload_penalty(model: pulp.LpProblem, data: dict, index_sets: dict, var_dict: dict) -> pulp.LpAffineExpression:
    """
    S4 Maximum workload Soft Constraint
    Pure Linear Model: Penalties incurred when a nurse's total patient load exceeds the limit in a single shift
    Rule: If the sum of daily loads of all inpatients in the rooms assigned to a nurse on duty exceeds the nurse's shift upper limit 
    → weighted penalty for the excess portion
    Optimization Point: Combine two layers of binary AND gates into a single three-variable AND operation, cutting auxiliary variables and constraints by half and significantly reducing memory usage
    """
    # Index Collection
    room_ids = index_sets["room_ids"]
    day_range = index_sets["day_range"]
    shift_types = index_sets["shift_types"]
    patient_ids = index_sets["patient_ids"]
    nurse_ids = index_sets["nurse_ids"]

    # Basic Data and Weights
    patients = data["patients"]
    nurses = data["nurses"]
    weight_s4 = data["weights"]["nurse_eccessive_workload"]
    max_load_upper = 1000  # 大M常数

    # Core Decision Variables
    y = var_dict["y_patient_room"]    # y[pid][rid][d] Patient p stays in room r on day d
    x = var_dict["x_nurse_room_shift"]# x[nid][rid][d][s] Nurse n, shift s, in charge of r
    admit = var_dict["admit_var"]    # admit[pid][t0] Patient admission date t0

    # Preload Static Constants
    patient_wl = {p["id"]: p["workload_produced"] for p in patients}
    patient_los = {p["id"]: p["length_of_stay"] for p in patients}
    nurse_shift_max = {}
    for n in nurses:
        nid = n["id"]
        shift_limit = {s["shift"]: s["max_load"] for s in n["working_shifts"]}
        nurse_shift_max[nid] = shift_limit

    # Nurse-Day-Shift Overtime Penalty Variable
    pen_nurse_load = pulp.LpVariable.dicts(
        "s4_nurse_load_penalty",
        (nurse_ids, day_range, shift_types),
        lowBound=0, cat=pulp.LpContinuous
    )
    total_s4 = pulp.LpAffineExpression()

    # Outer Layer: Nurse / Day / Shift
    for n in nurses:
        nid = n["id"]
        for d in day_range:
            for s in shift_types:
                limit = nurse_shift_max[nid].get(s, 0)
                total_load = pulp.LpAffineExpression()

                # Traverse the Room
                for rid in room_ids:
                    x_nrs = x[nid][rid][d][s]
                    # Iterate through patients
                    for p in patients:
                        pid = p["id"]
                        los = patient_los[pid]
                        wl_arr = patient_wl[pid]
                        y_prd = y[pid][rid][d]
                       # Traverse the admission start date
                        for t0 in day_range:
                            t = d - t0
                            if t < 0 or t >= los:
                                continue
                            w = wl_arr[t]  # Fixed Load Constant for Patient on Day t

                            # Optimization: Merge z1 & z2, use a single binary variable to represent that all three conditions hold simultaneously
                            # z = admit[pid][t0] ∧ y_prd ∧ x_nrs
                            z = pulp.LpVariable(f"s4_z_{nid}_{rid}_{pid}_{t0}", cat=pulp.LpBinary)
                            model += z <= admit[pid][t0]
                            model += z <= y_prd
                            model += z <= x_nrs
                            model += z >= admit[pid][t0] + y_prd + x_nrs - 2

                            # Linear accumulation constant * binary, no multiplication
                            total_load += w * z

                # Calculate the excess load for this shift max(0, Total Load - Upper Limit)
                excess = pulp.LpVariable(f"s4_ex_{nid}_{d}_{s}", lowBound=0, cat=pulp.LpContinuous)
                model += excess >= total_load - limit

                # Bind Penalty Variables
                model += pen_nurse_load[nid][d][s] >= excess
                total_s4 += weight_s4 * pen_nurse_load[nid][d][s]

    return total_s4