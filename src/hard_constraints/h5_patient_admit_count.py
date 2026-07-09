import pulp

def add_h5_constraint(model, data, index_sets, var_dict):
    """
    H5 Hard Constraint: Mandatory patients must be admitted exactly once; optional patients at most once
    """
    patients = data["patients"]
    day_range = index_sets["day_range"]
    admit_var = var_dict["admit_var"]

# ========== H5 Mandatory vs optional patient admission rule ==========
    # Hard Constraint Formal Instruction:
    # 1. Patient classification: Each patient carries a boolean field "mandatory" to distinguish two types:
    #    a) Mandatory patient ("mandatory": True): Treatment cannot be delayed outside the simulation planning window.
    #       The patient must be scheduled admission on exactly one single day within total_days.
    #       If zero admission day is selected, the solution is mathematically infeasible (hard rule).
    #    b) Optional patient ("mandatory": False): Treatment can be delayed to future planning cycles.
    #       The patient can either be admitted on at most one day inside the window, or not admitted at all (zero admission days).
    for p in patients:
        pid = p["id"]
        is_mandatory = p["mandatory"]
        # Sum all admission binary flags across every day to count total admission days
        total_admit_days = pulp.lpSum([admit_var[pid][d] for d in day_range])
        if is_mandatory:
            # Hard rule: mandatory patients must have exactly one admission day in the whole planning period
            model += total_admit_days == 1, f"H5_mandatory_patient{pid}_must_admit_once"
        else:
            # Hard rule: optional patients cannot be admitted more than once (0 or 1 admission only)
            model += total_admit_days <= 1, f"H5_optional_patient{pid}_max_one_admit"


def validate_h5_solution(sol_data, index_sets, var_dict):
    """
    Post-solution validation for H5 patient admission count rule
    Count violations: mandatory patients with 0 / >=2 admits; optional patients with >=2 admits
    Return total violation count and print violation logs
    """
    patients = sol_data["patients"]
    day_range = index_sets["day_range"]
    admit = var_dict["admit_var"]
    h5_violation_count = 0

    for p in patients:
        pid = p["id"]
        is_mandatory = p["mandatory"]
        actual_admit_days = 0.0
        for d in day_range:
            actual_admit_days += pulp.value(admit[pid][d])
        # Floating point tolerance
        actual_admit = round(actual_admit_days, 6)

        if is_mandatory:
            if abs(actual_admit - 1.0) > 1e-6:
                h5_violation_count += 1
                print(f"H5 VIOLATION: Mandatory patient {pid} admitted {actual_admit} times (must be exactly 1)")
        else:
            if actual_admit > 1.0 + 1e-6:
                h5_violation_count += 1
                print(f"H5 VIOLATION: Optional patient {pid} admitted {actual_admit} times (max 1 allowed)")

    if h5_violation_count == 0:
        print("✅ H5 Test Passed: All patients follow mandatory/optional admission count rules")
    else:
        print(f"❌ H5 Test Failed, total {h5_violation_count} admission count violations")
    return h5_violation_count