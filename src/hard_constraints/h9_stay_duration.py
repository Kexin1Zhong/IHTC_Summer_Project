import pulp

#def add_h9_constraint(model, data, index_sets, var_dict):
    #"""
    #H9 Stay‑duration linking hard constraint (not part of original H1‑H8, required business linking rule)
    #Logic:
        #If patient p is admitted on day d (admit_var[p][d]==1),
        #then for every offset k in [0, length_of_stay‑1], on day (d+k):
            #patient p must occupy at least one room (sum over rooms of y_patient_room >= 1)
        #Only generate constraints for admission day d where full stay period lies within simulation horizon.
    #"""
    #patients = data["patients"]
    #day_range = index_sets["day_range"]
    #room_ids = index_sets["room_ids"]

    #for p in patients:
        #pid = p["id"]
        #los = p["length_of_stay"]
        #for d in day_range:
            #last_stay_day = d + los - 1
            # Skip this d if full stay would go outside simulation time window
            #if last_stay_day not in day_range:
                #continue
            #for k in range(los):
                #day_stay = d + k
                #model += (
                    #pulp.lpSum([var_dict["y_patient_room"][pid][rid][day_stay] for rid in room_ids])
                    #>= var_dict["admit_var"][pid][d],
                    #f"H9_stay_p{pid}_admit{d}_stayday{day_stay}"
                #)

def add_h9_constraint(model, data, index_sets, var_dict):
    patients = data["patients"]
    day_range = index_sets["day_range"]
    room_ids = index_sets["room_ids"]

    total_generated = 0

    for p in patients:
        pid = p["id"]
        los = p["length_of_stay"]
        patient_cnt = 0
        for d in day_range:
            for k in range(los):
                day_stay = d + k
                if day_stay not in day_range:
                    continue
                patient_cnt += 1
                total_generated +=1
                model += (
                    pulp.lpSum([var_dict["y_patient_room"][pid][rid][day_stay] for rid in room_ids])
                    >= var_dict["admit_var"][pid][d],
                    f"H9_stay_p{pid}_d{d}_s{day_stay}"
                )
        #print(f"[H9 debug] pid {pid}, los={los}, generated {patient_cnt} constraints")
    #print(f"==== H9 total constraints generated: {total_generated} ====")


def validate_h9_solution(sol_data, index_sets, var_dict):
    """
    Post‑solve validation for H9 admission‑stay linking rule
    Violation: patient admitted on day d, but any stay‑day [d … d+los‑1] has zero room occupation.
    Returns total violation count, prints violation logs.
    """
    patients = sol_data["patients"]
    day_range = index_sets["day_range"]
    admit_var = var_dict["admit_var"]
    y_patient_room = var_dict["y_patient_room"]
    room_ids = index_sets["room_ids"]
    h9_violation_count = 0

    for p in patients:
        pid = p["id"]
        los = p["length_of_stay"]
        admit_days = []
        for d in day_range:
            if pulp.value(admit_var[pid][d]) > 1e-6:
                admit_days.append(d)

        for d_admit in admit_days:
            last_stay_day = d_admit + los - 1
            if last_stay_day not in day_range:
                print(f"H9 WARNING: patient {pid} admitted day {d_admit}, full stay exceeds simulation horizon")
                continue
            for k in range(los):
                day_stay = d_admit + k
                room_occ = sum(pulp.value(y_patient_room[pid][rid][day_stay]) for rid in room_ids)
                if room_occ < 1e-6:
                    h9_violation_count += 1
                    print(f"H9 VIOLATION: patient {pid} admitted day {d_admit}, stay‑day {day_stay} has zero room occupied")

    if h9_violation_count == 0:
        print("✅ H9 Test Passed: Admission‑stay duration linking rules satisfied")
    else:
        print(f"❌ H9 Test Failed, total {h9_violation_count} stay‑link violations")
    return h9_violation_count