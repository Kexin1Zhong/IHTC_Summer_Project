import pulp

def add_s4_max_workload_penalty(model: pulp.LpProblem, data: dict, index_sets: dict, var_dict: dict) -> pulp.LpAffineExpression:
    """
    S4 Maximum workload Soft Constraint
    Rule: Sum workload of patients in nurse's assigned rooms ≤ nurse shift max workload
    Penalty = excess workload if sum > limit; else 0
    Weight key: nurse_eccessive_workload
    """
    # Unpack index sets
    room_ids = index_sets["room_ids"]
    day_range = index_sets["day_range"]
    shift_types = index_sets["shift_types"]
    patient_ids = index_sets["patient_ids"]
    nurse_ids = index_sets["nurse_ids"]

    # Raw data & weight
    patients = data["patients"]
    nurses = data["nurses"]
    weight_s4 = data["weights"]["nurse_eccessive_workload"]
    max_load_upper = 1000  # Big-M, Global Upper Bound of Load Theory

    # Core variables
    y = var_dict["y_patient_room"]
    x = var_dict["x_nurse_room_shift"]
    admit = var_dict["admit_var"]

    # Pre-cache static data
    patient_workload_list = {p["id"]: p["workload_produced"] for p in patients}
    patient_los = {p["id"]: p["length_of_stay"] for p in patients}
    nurse_max_load = {}
    for n in nurses:
        nid = n["id"]
        nurse_max_load[nid] = {}
        shift_map = {item["shift"]: item["max_load"] for item in n["working_shifts"]}
        for s in shift_types:
            nurse_max_load[nid][s] = shift_map.get(s, 0)

    # Aux penalty variable for each nurse-day-shift
    pen_nurse_load = pulp.LpVariable.dicts(
        "s4_nurse_load_penalty",
        (nurse_ids, day_range, shift_types),
        lowBound=0,
        cat=pulp.LpContinuous
    )
    total_s4_penalty = 0

    # Outer loop: Nurse → Day → Shift
    for n in nurses:
        nid = n["id"]
        for d in day_range:
            for s in shift_types:
                single_shift_excess = 0
                nurse_limit = nurse_max_load[nid][s]
                total_patient_load = pulp.LpAffineExpression()

                for rid in room_ids:
                    x_n_r_d_s = x[nid][rid][d][s]
                    for p in patients:
                        pid = p["id"]
                        y_p_r_d = y[pid][rid][d]
                        los = patient_los[pid]
                        wl_list = patient_workload_list[pid]
                        # Skip patient not occupying this room
                        if y_p_r_d == 0:
                            continue
                        # Traverse all admission day t0 to get relative stay day t
                        for t0 in day_range:
                            t = d - t0
                            if t < 0 or t >= los:
                                continue
                            # Binary flag: patient admitted t0 & stay in room r day d
                            admit_flag = pulp.LpVariable(f"s4_admit_flag_p{pid}_t0{t0}_d{d}", cat=pulp.LpBinary)
                            model += admit_flag <= admit[pid][t0]
                            model += admit_flag <= y_p_r_d
                            model += admit_flag >= admit[pid][t0] + y_p_r_d - 1
                            # Get single daily workload value
                            daily_p_load = wl_list[t]
                            # Binary flag: patient room + nurse assigned room
                            room_p_flag = pulp.LpVariable(f"s4_flag_p{pid}_r{rid}_n{nid}_d{d}_{s}_t0{t0}", cat=pulp.LpBinary)
                            model += room_p_flag <= y_p_r_d
                            model += room_p_flag <= x_n_r_d_s
                            model += room_p_flag >= y_p_r_d + x_n_r_d_s - 1
                            # Only accumulate when both flags equal 1
                            total_patient_load += daily_p_load * room_p_flag * admit_flag

                # Calculate excess load max(0, total_patient_load - nurse_limit)
                excess_load = pulp.LpVariable(f"s4_excess_n{nid}_d{d}_{s}", lowBound=0, cat=pulp.LpContinuous)
                load_gap = total_patient_load - nurse_limit
                model += excess_load >= load_gap
                model += excess_load <= load_gap + max_load_upper
                single_shift_excess += excess_load

                model += pen_nurse_load[nid][d][s] >= single_shift_excess, f"S4_n{nid}_d{d}_s{s}_sum"
                total_s4_penalty += weight_s4 * pen_nurse_load[nid][d][s]

    return total_s4_penalty