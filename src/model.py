import json
import os

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
    :return: patient_list, nurse_list
    """
    patients = instance_data["patients"]
    nurses = instance_data["nurses"]
    return patients, nurses

# Batch test all test cases
if __name__ == "__main__":
    test_case_list = [f"test{i:02d}" for i in range(1, 11)]
    for case in test_case_list:
        data = load_instance(case)
        pats, nurs = extract_basic_info(data)
        print(f"[{case}] Patients: {len(pats)}, Nurses: {len(nurs)}")