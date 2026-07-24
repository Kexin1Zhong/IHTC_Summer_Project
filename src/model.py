import sys
import os
# Locate the project root directory IHTC_Summer_Project
current_file = os.path.abspath(__file__)
# Current file path src/model.py,
# jumping up one level = project root directory
project_root = os.path.abspath(os.path.join(os.path.dirname(current_file), "../"))
if project_root not in sys.path:
    sys.path.append(project_root)


import json
import os
import pulp

# Uniformly import all hard constraint construction functions
# (read from hard_constraints)
from src.hard_constraints.h1_gender_mix import add_h1_constraint
from src.hard_constraints.h2_incompatible_room import add_h2_constraint
from src.hard_constraints.h3_surgeon_overtime import add_h3_constraint
from src.hard_constraints.h4_ot_capacity import add_h4_constraint
from src.hard_constraints.h5_patient_admit_count import add_h5_constraint
from src.hard_constraints.h6_admit_window import add_h6_constraint
from src.hard_constraints.h7_room_capacity import add_h7_constraint
from src.hard_constraints.h8_nurse_room_shift import add_h8_constraint

# ========== Import all soft constraint modeling functions (S1~S8) ==========
from src.soft_constraints.s1_age_gap import add_s1_age_gap_penalty
from src.soft_constraints.s2_nurse_skill_shortage import add_s2_nurse_skill_penalty
from src.soft_constraints.s3_nurse_continuity import add_s3_care_continuity_penalty
from src.soft_constraints.s4_max_workload import add_s4_max_workload_penalty
from src.soft_constraints.s5_open_ot import add_s5_open_ot_penalty
from src.soft_constraints.s6_surgeon_transfer import add_s6_surgeon_transfer_penalty
from src.soft_constraints.s7_admission_delay import add_s7_admission_delay_penalty
from src.soft_constraints.s8_unscheduled_optional import add_s8_unscheduled_optional_penalty


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
    :return: patient_list, nurse_list, total_days, shift_list, room_list, surgeon_list, ot_list, weight_dict
    """
    patients = instance_data["patients"]
    nurses = instance_data["nurses"]
    total_days = instance_data["days"]
    shift_list = instance_data["shift_types"]
    rooms = instance_data["rooms"]
    surgeons = instance_data["surgeons"]
    operating_theaters = instance_data["operating_theaters"]
    penalty_weights = instance_data["weights"]
    return patients, nurses, total_days, shift_list, rooms, surgeons, operating_theaters, penalty_weights


def build_milp_model(instance_name: str):
    """
    Initialize PuLP MILP model for IHTC integrated hospital scheduling problem
    Contains complete constraint framework for H(hard) & S(soft) rules
    :param instance_name: target test case name
    :return: model, raw_data, index_sets, var_dict
    """
    # Load raw dataset
    data = load_instance(instance_name)
    patients, nurses, total_days, shift_list, rooms, surgeons, ots, weights = extract_basic_info(data)

    # Create minimization MILP model (minimize total soft constraint penalty)
    model = pulp.LpProblem(f"IHTC_Schedule_{instance_name}", pulp.LpMinimize)

    # -------------------------- Index Sets Definition --------------------------
    nurse_ids = [n["id"] for n in nurses]
    patient_ids = [p["id"] for p in patients]
    room_ids = [r["id"] for r in rooms]
    surgeon_ids = [s["id"] for s in surgeons]
    ot_ids = [ot["id"] for ot in ots]
    day_range = list(range(total_days))
    shift_list = ["early", "late", "night"]

    # Pre-build room capacity dict to avoid repeated loop lookup in H8
    room_cap_dict = {r["id"]: r["capacity"] for r in rooms}

    # -------------------------- Core Binary Decision Variables --------------------------
    # 1. x[n][r][d][s]: Nurse n assigned to room r on day d shift s
    x_nurse_room = pulp.LpVariable.dicts(
        "nurse_room_assign",
        (nurse_ids, room_ids, day_range, shift_list),
        cat=pulp.LpBinary
    )
    # 2. y[p][r][d]: Patient p occupies room r on day d
    y_patient_room = pulp.LpVariable.dicts(
        "patient_room_occupy",
        (patient_ids, room_ids, day_range),
        cat=pulp.LpBinary
    )
    # 3. a[p][d]: Patient p admitted on day d
    admit_var = pulp.LpVariable.dicts(
        "patient_admit_day",
        (patient_ids, day_range),
        cat=pulp.LpBinary
    )
    # 4. ot_surg[sur][ot][d]: Surgeon uses OT ot on day d
    ot_surg_assign = pulp.LpVariable.dicts(
        "surgeon_ot_assign",
        (surgeon_ids, ot_ids, day_range),
        cat=pulp.LpBinary
    )

    # -------------------------- Pack index & variable dict FIRST --------------------------
    # Revise the key to be unified as shift_types
    # to match the codes of S1/S2/S3/S4/S5/S6/S7/S8 and avoid KeyError
    index_sets = {
        "nurse_ids": nurse_ids,
        "patient_ids": patient_ids,
        "room_ids": room_ids,
        "surgeon_ids": surgeon_ids,
        "ot_ids": ot_ids,
        "day_range": day_range,
        "shift_types": shift_list
    }
    var_dict = {
        "x_nurse_room_shift": x_nurse_room,  # 同步所有软约束变量key
        "y_patient_room": y_patient_room,
        "admit_var": admit_var,
        "ot_surg_assign": ot_surg_assign
    }

    # -------------------------- Phase3 Hard Constraints (H Series) --------------------------
    # All hard constraint logic moved to src/hard_constraints/ separate files
    add_h1_constraint(model, data, index_sets, var_dict)
    add_h2_constraint(model, data, index_sets, var_dict)
    add_h3_constraint(model, data, index_sets, var_dict)
    add_h4_constraint(model, data, index_sets, var_dict)
    add_h5_constraint(model, data, index_sets, var_dict)
    add_h6_constraint(model, data, index_sets, var_dict)
    add_h7_constraint(model, data, index_sets, var_dict)
    add_h8_constraint(model, data, index_sets, var_dict)

    # -------------------------- Phase4 Soft Constraints & Objective Function (S Series) --------------------------
    total_penalty = 0
    # S1 Age group gap penalty
    s1_pen = add_s1_age_gap_penalty(model, data, index_sets, var_dict)
    total_penalty += s1_pen

    # S2 Nurse skill level shortage penalty
    s2_pen = add_s2_nurse_skill_penalty(model, data, index_sets, var_dict)
    total_penalty += s2_pen

    # S3 Continuity of care (distinct nurse count) penalty
    s3_pen = add_s3_care_continuity_penalty(model, data, index_sets, var_dict)
    total_penalty += s3_pen

    # S4 Max nurse workload penalty
    s4_pen = add_s4_max_workload_penalty(model, data, index_sets, var_dict)
    total_penalty += s4_pen

    # ========== New Penalty for Opening S5 Operating Room ==========
    s5_pen = add_s5_open_ot_penalty(model, data, index_sets, var_dict)
    total_penalty += s5_pen

    # ========== New S6 Surgeon Transfer Penalty ==========
    s6_pen = add_s6_surgeon_transfer_penalty(model, data, index_sets, var_dict)
    total_penalty += s6_pen

    # ========== New S7 Admission Delay Penalty ==========
    s7_pen = add_s7_admission_delay_penalty(model, data, index_sets, var_dict)
    total_penalty += s7_pen

    # ========== New S8 Unscheduled Optional Patient Penalty ==========
    s8_pen = add_s8_unscheduled_optional_penalty(model, data, index_sets, var_dict)
    total_penalty += s8_pen

    model += total_penalty, "MinimizeTotalSoftConstraintPenalty"

    return model, data, index_sets, var_dict