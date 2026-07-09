import pulp

def add_h3_constraint(model, data, index_sets, var_dict):
    """
    H3 Hard Constraint: Surgeon daily total surgery time cannot exceed individual daily max limit
    """
    patients = data["patients"]
    surgeons = data["surgeons"]
    day_range = index_sets["day_range"]
    admit_var = var_dict["admit_var"]

    # Hard Constraint Formal Instruction:
    # 1. Each surgeon stores a list "max_surgery_time", where max_surgery_time[d] is the maximum allowed total surgery duration on simulation day d.
    # 2. For every surgeon s and every day d, the sum of surgery durations of all patients admitted on day d who belong to this surgeon cannot exceed s["max_surgery_time"][d].
    # 3. Violation of this rule renders the solution infeasible (hard constraint, no penalty).
    # 4. A patient’s surgery is fixed to their assigned surgeon, so all surgery time of patient p counts towards surgeon p["surgeon_id"] on admit day d.
    for sur in surgeons:
        sur_id = sur["id"]
        sur_daily_max_list = sur["max_surgery_time"]
        for d in day_range:
            sur_max_time = sur_daily_max_list[d]
            total_surg_time = pulp.lpSum([
                p["surgery_duration"] * admit_var[p["id"]][d]
                for p in patients if p["surgeon_id"] == sur_id
            ])
            model += total_surg_time <= sur_max_time, f"H3_surgeon{sur_id}_day{d}_no_overtime"

            


def validate_h3_solution(sol_data, index_sets, var_dict):
    """
    Post-solution validation for H3 surgeon overtime hard rule
    Count and print all daily surgeon overtime violations
    Return total violation count
    """
    patients = sol_data["patients"]
    surgeons = sol_data["surgeons"]
    day_range = index_sets["day_range"]
    admit = var_dict["admit_var"]
    h3_violation_count = 0

    for sur in surgeons:
        sur_id = sur["id"]
        daily_max_times = sur["max_surgery_time"]
        for d in day_range:
            max_allowed = daily_max_times[d]
            real_total_time = 0.0
            for p in patients:
                if p["surgeon_id"] == sur_id:
                    admit_flag = pulp.value(admit[p["id"]][d])
                    real_total_time += p["surgery_duration"] * admit_flag
            # Judge overtime (floating point tolerance 1e-6)
            if real_total_time - max_allowed > 1e-6:
                h3_violation_count += 1
                print(f"H3 VIOLATION: Surgeon {sur_id}, Day {d} | Max:{max_allowed}, Actual:{round(real_total_time,2)}")

    if h3_violation_count == 0:
        print("✅ H3 Test Passed: No surgeon daily overtime violations")
    else:
        print(f"❌ H3 Test Failed, total {h3_violation_count} surgeon overtime violations")
    return h3_violation_count