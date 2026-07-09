import pulp

def add_h6_constraint(model, data, index_sets, var_dict):
    """
    H6 Hard Constraint: Patient admission must be within release day window; mandatory patients have fixed due deadline
    """
    patients = data["patients"]
    day_range = index_sets["day_range"]
    admit_var = var_dict["admit_var"]

    # ========== H6 Admission day window constraint ==========
    # Hard Constraint Formal Instruction:
    # 1. Each patient has an earliest feasible admission day defined by field "surgery_release_day".
    #    No admission can be scheduled on any day strictly earlier than this release day.
    # 2. Mandatory patients (mandatory = True) contain an upper bound deadline "surgery_due_day".
    #    Their admission cannot be scheduled on any day later than this due deadline.
    # 3. Optional patients (mandatory = False) have no upper time limit within the planning horizon.
    #    They can be admitted on any day >= surgery_release_day, or fully postponed without admission.
    for p in patients:
        pid = p["id"]
        release_day = p["surgery_release_day"]
        # Separate logic branch for mandatory patients with a hard deadline
        if p["mandatory"]:
            due_day = p["surgery_due_day"]
            for d in day_range:
                # Block days earlier than release or later than the mandatory deadline
                if d < release_day or d > due_day:
                    model += admit_var[pid][d] == 0, f"H6_mandatory_p{pid}_invalid_day{d}"
        else:
            # Optional patient: only restrict early days, no upper bound cutoff
            for d in day_range:
                if d < release_day:
                    model += admit_var[pid][d] == 0, f"H6_optional_p{pid}_invalid_day{d}"


def validate_h6_solution(sol_data, index_sets, var_dict):
    """
    Post-solution validation for H6 admission time window rule
    Detect patients admitted outside allowed release / due date range
    Return total violation count and print violation logs
    """
    patients = sol_data["patients"]
    day_range = index_sets["day_range"]
    admit = var_dict["admit_var"]
    h6_violation_count = 0

    for p in patients:
        pid = p["id"]
        release_day = p["surgery_release_day"]
        is_mandatory = p["mandatory"]
        if is_mandatory:
            due_day = p["surgery_due_day"]
        # Check every day if patient was admitted out of window
        for d in day_range:
            admit_flag = pulp.value(admit[pid][d])
            if admit_flag < 1e-6:
                continue
            # Admitted on day d, judge if violates window
            if is_mandatory:
                if d < release_day or d > due_day:
                    h6_violation_count += 1
                    print(f"H6 VIOLATION: Mandatory patient {pid} admitted on Day {d} (valid window [{release_day}, {due_day}])")
            else:
                if d < release_day:
                    h6_violation_count += 1
                    print(f"H6 VIOLATION: Optional patient {pid} admitted on Day {d} (earlier than release day {release_day})")

    if h6_violation_count == 0:
        print("✅ H6 Test Passed: All patient admissions comply with release/due day window rules")
    else:
        print(f"❌ H6 Test Failed, total {h6_violation_count} admission window violations")
    return h6_violation_count