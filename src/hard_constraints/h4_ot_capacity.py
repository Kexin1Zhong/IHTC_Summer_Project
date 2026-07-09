import pulp

def add_h4_constraint(model, data, index_sets, var_dict):
    """
    H4 Hard Constraint: Daily total surgery time assigned to each OT cannot exceed its daily availability limit
    """
    patients = data["patients"]
    ots = data["operating_theaters"]
    ot_ids = index_sets["ot_ids"]
    patient_ids = index_sets["patient_ids"]
    day_range = index_sets["day_range"]
    admit_var = var_dict["admit_var"]
    ot_surg_assign = var_dict["ot_surg_assign"]

     # ========== H4 OT overtime: The duration of all surgeries allocated to an OT on a day must not exceed the OT’s maximum capacity ==========
    # Hard Constraint Formal Instruction:
    # 1. Every operating theater (OT) stores a daily time limit list named "availability", where availability[d] is the maximum total surgery time allowed on day d.
    # 2. Binary variable ot_surg_assign[sur][ot][d] = 1 if surgeon sur uses OT ot on day d, else 0.
    # 3. Binary variable admit_var[p][d] = 1 if patient p is admitted on day d, else 0.
    # 4. Introduce auxiliary binary var use_p_ot[p][ot][d] = admit_var[p][d] * ot_surg_assign[p["surgeon_id"]][ot][d]
    #    Linearization rules for product of two binaries a*b:
    #       use_p_ot <= admit_var
    #       use_p_ot <= ot_surg_assign
    #       use_p_ot >= admit_var + ot_surg_assign - 1
    # 5. Total surgery time for OT ot on day d = sum over all patients (p["surgery_duration"] * use_p_ot[p][ot][d])
    # 6. Aggregated surgery time cannot exceed OT daily availability value (hard constraint).

    # Step 1: Create auxiliary variable for patient-OT-day usage (linearize product)
    use_p_ot = pulp.LpVariable.dicts(
        "patient_ot_usage",
        (patient_ids, ot_ids, day_range),
        cat=pulp.LpBinary
    )

    # Step 2: Linearization constraints for use_p_ot[p][ot][d] = admit_var[p][d] * ot_surg_assign[sur][ot][d]
    for p in patients:
        pid = p["id"]
        sur_p = p["surgeon_id"]
        dur_p = p["surgery_duration"]
        for ot in ots:
            ot_id = ot["id"]
            for d in day_range:
                aux = use_p_ot[pid][ot_id][d]
                a = admit_var[pid][d]
                b = ot_surg_assign[sur_p][ot_id][d]
                # Linearize a * b
                model += aux <= a
                model += aux <= b
                model += aux >= a + b - 1

    # Step3: OT daily capacity limit constraint
    for ot in ots:
        ot_id = ot["id"]
        ot_daily_availability = ot["availability"]
        for d in day_range:
            ot_max_cap = ot_daily_availability[d]
            daily_ot_total_time = pulp.lpSum([
                p["surgery_duration"] * use_p_ot[p["id"]][ot_id][d]
                for p in patients
            ])
            model += daily_ot_total_time <= ot_max_cap, f"H4_ot{ot_id}_day{d}_no_overtime"




def validate_h4_solution(sol_data, index_sets, var_dict):
    """
    Post-solution validation for H4 OT daily capacity hard rule
    Count and print all OT daily overtime violations
    Return total violation count
    """
    patients = sol_data["patients"]
    ots = sol_data["operating_theaters"]
    ot_ids = index_sets["ot_ids"]
    patient_ids = index_sets["patient_ids"]
    day_range = index_sets["day_range"]
    admit = var_dict["admit_var"]
    ot_surg = var_dict["ot_surg_assign"]
    h4_violation_count = 0

    # Reconstruct auxiliary usage variable from solved binary values
    for ot in ots:
        ot_id = ot["id"]
        daily_max_times = ot["availability"]
        for d in day_range:
            max_allowed = daily_max_times[d]
            real_total_time = 0.0
            for p in patients:
                pid = p["id"]
                sur_id = p["surgeon_id"]
                admit_val = pulp.value(admit[pid][d])
                ot_use_val = pulp.value(ot_surg[sur_id][ot_id][d])
                # Recover linearized product value
                usage = min(admit_val, ot_use_val)
                real_total_time += p["surgery_duration"] * usage
            # Floating point tolerance comparison
            if real_total_time - max_allowed > 1e-6:
                h4_violation_count += 1
                print(f"H4 VIOLATION: OT {ot_id}, Day {d} | Max:{max_allowed}, Actual:{round(real_total_time,2)}")

    if h4_violation_count == 0:
        print("✅ H4 Test Passed: No OT daily capacity overtime violations")
    else:
        print(f"❌ H4 Test Failed, total {h4_violation_count} OT capacity violations")
    return h4_violation_count