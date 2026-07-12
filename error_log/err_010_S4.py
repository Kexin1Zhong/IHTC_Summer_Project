#import pulp

#def add_s4_max_workload_penalty(model: pulp.LpProblem, data: dict, index_sets: dict, var_dict: dict) -> pulp.LpAffineExpression:
    #"""
    #S4 Maximum workload Soft Constraint
    #Rule: Sum workload of patients in nurse's assigned rooms ≤ nurse shift max workload
    #Penalty = excess workload if sum > limit; else 0
    #Weight key: nurse_eccessive_workload
    #"""
    # Unpack index sets
    #room_ids = index_sets["room_ids"]
    #day_range = index_sets["day_range"]
    #shift_types = index_sets["shift_types"]
    #patient_ids = index_sets["patient_ids"]
    #nurse_ids = index_sets["nurse_ids"]

    # Raw data & weight
    #patients = data["patients"]
    #nurses = data["nurses"]
    # Correct the key to the actually existing nurse_excessive_workload in JSON
    #weight_s4 = data["weights"]["nurse_eccessive_workload"]
    #max_load_upper = 1000  # Big-M, Global Upper Bound of Load Theory

    # Core variables
    #y = var_dict["y_patient_room"]
    #x = var_dict["x_nurse_room_shift"]
    #admit = var_dict["admit_var"]

    # Pre-cache static data
    # Patient's own load value 
    # patient["workload_produced"]
    #patient_workload = {p["id"]: p["workload_produced"] for p in patients}
    # Maximum workload limit for nurses per shift 
    # nurse["shift_max_workload"][s]
    #nurse_max_load = {}
    #for n in nurses:
        #nid = n["id"]
        #nurse_max_load[nid] = {}
        #for s in shift_types:
            # Match the structure of nurse["working_shifts"] in JSON 
            # and extract the max_load of corresponding shifts
            #shift_map = {item["shift"]: item["max_load"] for item in n["working_shifts"]}
            #nurse_max_load[nid][s] = shift_map[s]   
            # ###mistake here:
            # Looping over shift_types = ["early", "late", "night"] iterates through all three shifts. 
            # If a nurse has no early shift on the day, 
            # the key "early" does not exist in the shift_map dictionary, 
            # and direct indexing will raise a KeyError.






    # Aux penalty variable for each nurse-day-shift
    #pen_nurse_load = pulp.LpVariable.dicts(
        #"s4_nurse_load_penalty",
        #(nurse_ids, day_range, shift_types),
        #lowBound=0,
        #cat=pulp.LpContinuous
    #)
    #total_s4_penalty = 0

    # Outer loop: Nurse → Day → Shift
    #for n in nurses:
        #nid = n["id"]
        #for d in day_range:
            #for s in shift_types:
                #single_shift_excess = 0
                #nurse_limit = nurse_max_load[nid][s]
                # Nurse assignment marker x[n][r][d][s] = 1 
                # means nurse n is in charge of ward r during shift s on day d
                # Calculate the total patient workload of all wards assigned to this nurse for this shift
                #total_patient_load = pulp.LpAffineExpression()

                #for rid in room_ids:
                    #x_n_r_d_s = x[nid][rid][d][s]
                    # Iterate through all patients and add their individual loads 
                    # if they occupy this room on the current day
                    #for p in patients:
                        #pid = p["id"]
                        #y_p_r_d = y[pid][rid][d]
                        #p_load = patient_workload[pid]
                        # Binary flag: 
                        # Patient occupies this room + Nurse assigns this room
                        #room_p_flag = pulp.LpVariable(f"s4_flag_p{pid}_r{rid}_n{nid}_d{d}_{s}", cat=pulp.LpBinary)
                        #model += room_p_flag <= y_p_r_d
                        #model += room_p_flag <= x_n_r_d_s
                        #model += room_p_flag >= y_p_r_d + x_n_r_d_s - 1
                        #total_patient_load += p_load * room_p_flag

                # Calculate excess load max(0, total_patient_load - nurse_limit)
                #excess_load = pulp.LpVariable(f"s4_excess_n{nid}_d{d}_{s}", lowBound=0, cat=pulp.LpContinuous)
                #load_gap = total_patient_load - nurse_limit
                #model += excess_load >= load_gap
                #model += excess_load <= load_gap + max_load_upper
                #single_shift_excess += excess_load

                # Bind the total overtime of this nurse's daily shift to the penalty variable
                #model += pen_nurse_load[nid][d][s] >= single_shift_excess, f"S4_n{nid}_d{d}_s{s}_sum"
                #total_s4_penalty += weight_s4 * pen_nurse_load[nid][d][s]

    #return total_s4_penalty