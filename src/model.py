import json
import os
import pulp

def load_instance(instance_name: str) -> dict:
    """
    Load IHTC instance json file with full error handling
    :param instance_name: test01 ~ test10
    :return: raw instance dictionary
    """
    file_path = os.path.join("data", "ihtc2024_test_dataset", f"{instance_name}.json")
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Instance file missing: {file_path}")
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        raise ValueError(f"Invalid JSON format in {file_path}")

def extract_basic_info(instance_data: dict) -> tuple:
    """
    Extract core data from loaded instance dict
    :param instance_data: raw json data from load_instance()
    :return: patient_list, nurse_list, total_days, shift_list
    """
    patients = instance_data["patients"]
    nurses = instance_data["nurses"]
    total_days = instance_data["days"]
    shift_list = instance_data["shift_types"]
    return patients, nurses, total_days, shift_list

def build_milp_model(instance_name: str):
    """
    Initialize PuLP MILP model for IHTC nurse-patient scheduling
    :param instance_name: target test case name
    :return: model, data, x, nurse_ids, patient_ids, day_range, shift_list
    """
    # Load raw instance data
    data = load_instance(instance_name)
    patients, nurses, total_days, shift_list = extract_basic_info(data)

    # Create minimization MILP model
    model = pulp.LpProblem(f"IHTC_Schedule_{instance_name}", pulp.LpMinimize)

    # Index sets
    nurse_ids = [n["id"] for n in nurses]
    patient_ids = [p["id"] for p in patients]
    day_range = list(range(total_days))

    # Core binary decision variable: x[n][p][d][s]
    # x[n][p][d][s] = 1 if nurse n cares patient p on day d shift s
    x = pulp.LpVariable.dicts(
        "assign",
        (nurse_ids, patient_ids, day_range, shift_list),
        lowBound=0,
        upBound=1,
        cat=pulp.LpBinary
    )

    # --------------------------
    # Phase 3: Hard Constraints H1 ~ H8 (to be filled one by one)
    # --------------------------
    # H1: One nurse can only take care of at most one patient per shift per day
    # H2: One patient can only be cared by at most one nurse per shift per day
    # H3: Each patient must receive minimum required total care time
    # H4: Nurse skill level must match patient required skill
    # H5: Maximum total working shifts per nurse across all days
    # H6: Continuous care limit for patients
    # H7: Mandatory rest interval for nurses between shifts
    # H8: Special night shift restriction rules

    # --------------------------
    # Phase 4: Objective function (sum all soft penalty costs)
    # --------------------------
    total_penalty = 0
    model += total_penalty, "MinimizeTotalPenalty"

    return model, data, x, nurse_ids, patient_ids, day_range, shift_list

# Batch test all test cases
if __name__ == "__main__":
    test_case_list = [f"test{i:02d}" for i in range(1, 11)]
    for case in test_case_list:
        data = load_instance(case)
        pats, nurs, total_days, shifts = extract_basic_info(data)
        print(f"[{case}] Patients: {len(pats)}, Nurses: {len(nurs)}, Total days: {total_days}, Shifts: {shifts}")

    # Test model initialization for test01
    test_model, test_data, var_x, n_ids, p_ids, day_list, s_list = build_milp_model("test01")
    print("\nPhase2 full variable framework loaded successfully for test01")
    print(f"Nurses: {len(n_ids)}, Patients: {len(p_ids)}, Days: {len(day_list)}, Shift types: {s_list}")