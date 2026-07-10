#import pulp

#def add_s2_nurse_skill_penalty(model: pulp.LpProblem, data: dict, index_sets: dict, var_dict: dict) -> pulp.LpAffineExpression:
    #"""
    #S2 Nurse skill shortage soft constraint
    #Penalty = skill_required - nurse_skill if nurse skill < patient required min skill, else 0
    #Args:
        #model: pulp MILP model instance
        #data: raw input json data
        #index_sets: pre-defined index sets
        #var_dict: decision variables dict (y_patient_room, x_nurse_room_shift required)
    #Return:
        #pulp.LpAffineExpression: total weighted penalty of S2 to add to global total_penalty
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
   # weight_s2 = data["weights"]["room_nurse_skill"]

    # Unpack core decision variables
    #y = var_dict["y_patient_room"]
    #x = var_dict["x_nurse_room_shift"]

    # Preload patient skill requirement dict: pid -> list of daily required skill
    #patient_skill_req = {p["id"]: p["skill_level_required"] for p in patients}
    # Preload nurse skill dict: nid -> fixed skill level
    #nurse_skill = {n["id"]: n["skill_level"] for n in nurses}
    #max_skill = data["skill_levels"] - 1  # max possible skill value for Big-M

    # Aux variable: total skill shortage penalty for room r, day d, shift s
    #pen_skill_short = pulp.LpVariable.dicts(
        #"s2_pen_skill_shortage",
        #(room_ids, day_range, shift_types),
        #lowBound=0,
        #cat=pulp.LpContinuous
   # )

    #s2_total_expr = 0

   #for rid in room_ids:
        #for d in day_range:
            #for s in shift_types:
                # Local expression to sum all skill shortage in this room-day-shift
                #shift_shortage = 0

                #for p in patients:
                    #pid = p["id"]
                    # Patient p's min required skill on day d
                    #req_skill = patient_skill_req[pid][d] 
#Error root cause: 
# Using global planning day d directly as index to access patient skill_level_required list.
#The length of this list only equals the patient’s length_of_stay, 
# which is much shorter than total planning days (21). 
# Global d exceeds list index range and triggers IndexError.
#Core logic flaw: 
# Failed to distinguish global absolute day d and patient relative admission offset day, 
# they cannot be used interchangeably.

                    #y_p_r_d = y[pid][rid][d]

                    #for n in nurses:
                        #nid = n["id"]
                        #ns = nurse_skill[nid]
                        #x_n_r_d_s = x[nid][rid][d][s]

                        # Aux binary: patient p in room r day d AND nurse n assigned to room r day d shift s
                        #assign_flag = pulp.LpVariable(f"s2_flag_p{pid}_n{nid}_r{rid}_d{d}_{s}", cat=pulp.LpBinary)
                        # Linearize assign_flag = y_p_r_d * x_n_r_d_s
                        #model += assign_flag <= y_p_r_d
                        #model += assign_flag <= x_n_r_d_s
                        #model += assign_flag >= y_p_r_d + x_n_r_d_s - 1

                        # Shortage for this pair: max(0, req_skill - ns) * assign_flag
                        #shortage = pulp.LpVariable(f"s2_short_p{pid}_n{nid}_r{rid}_d{d}_{s}", lowBound=0, cat=pulp.LpContinuous)
                        # Linear constraint for shortage >= (req_skill - ns) * assign_flag
                        #model += shortage >= (req_skill - ns) - max_skill * (1 - assign_flag)
                        #model += shortage <= (req_skill - ns) + max_skill * (1 - assign_flag)
                        #model += shortage <= max_skill * assign_flag

                        #shift_shortage += shortage

                # Penalty variable >= total shortage of this room-day-shift
                #model += pen_skill_short[rid][d][s] >= shift_shortage, f"S2_pen_sum_r{rid}_d{d}_{s}"
                # Accumulate weighted penalty
                #s2_total_expr += weight_s2 * pen_skill_short[rid][d][s]

    #return s2_total_expr