# ========== H3 Surgeon overtime: The maximum daily surgery time of a surgeon must not be exceeded ==========
    # Hard Constraint Formal Instruction:
    # 1. Each surgeon has a predefined maximum allowed total surgery duration per single simulation day.
    # 2. For every surgeon s and every day d, the sum of surgery durations of all patients admitted on day d who belong to this surgeon cannot exceed the surgeon’s daily time limit.
    # 3. Violation of this rule renders the solution infeasible (hard constraint, no penalty).
    # 4. A patient’s surgery is fixed to their assigned surgeon, so all surgery time of patient p counts towards surgeon p["surgeon_id"] on admit day d.
    #for sur in surgeons:
        #sur_id = sur["id"]
        #sur_max_time = sur["max_surgery_time"] ## mistake here, it assumes fixed surgery time
        #for d in day_range:
            #total_surg_time = 0
            #for p in patients:
                #if p["surgeon_id"] == sur_id:
                    #dur = p["surgery_duration"]
                    #total_surg_time += dur * admit_var[p["id"]][d]
            #model += total_surg_time <= sur_max_time, f"H3_surgeon{sur_id}_day{d}_no_overtime"

#mistake reason:
#The daily maximum limit for each doctor can vary day by day