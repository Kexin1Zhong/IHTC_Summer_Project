# ========== H4 OT overtime: The duration of all surgeries allocated to an OT on a day must not exceed the OT’s maximum capacity ==========
    # Hard Constraint Formal Instruction:
    # 1. Every operating theater (OT) has a predefined fixed upper bound on total cumulative surgery time permitted within a single simulation day, stored as field "max_daily_time" in OT data.
    # 2. Decision variable definition: ot_surg_assign[surgeon_id][ot_id][day] is a binary variable.
    #    - Value = 1: Surgeon surgeon_id uses operating theater ot_id to conduct surgeries on day d.
    #    - Value = 0: Surgeon surgeon_id does not perform any surgery in OT ot_id on day d.
    # 3. Patient-surgeon binding rule: Each patient p is permanently assigned to one fixed surgeon via field "surgeon_id" in patient data; all surgery time of patient p belongs exclusively to this assigned surgeon.
    # 4. Time counting logic: The surgery duration of patient p will be counted toward the daily total time of OT ot_id on day d only if two conditions hold simultaneously:
    #    a) admit_var[p["id"]][d] = 1: Patient p is admitted and receives surgery on day d.
    #    b) ot_surg_assign[p["surgeon_id"]][ot_id][d] = 1: The fixed surgeon of patient p uses OT ot_id on day d.
    #    If either condition fails, the surgery duration of patient p contributes zero to the OT’s daily total time.
    #for ot in ots:
        #ot_id = ot["id"]
        #ot_max_cap = ot["max_daily_time"]  ##mistake here: it assumes fixed operating time
        #for d in day_range:
            # Calculate total occupied surgery time of current OT on day d
            #daily_ot_total_time = pulp.lpSum([
                #p["surgery_duration"] * admit_var[p["id"]][d] * ot_surg_assign[p["surgeon_id"]][ot_id][d]
                #for p in patients
            #])
            ## Hard constraint: daily total surgery time cannot exceed OT daily maximum capacity
            #model += daily_ot_total_time <= ot_max_cap, f"H4_ot{ot_id}_day{d}_no_overtime"

#mistake reason:
#The day maximum operating time for each operating theatre can vary day by day