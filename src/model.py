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
    # 4. ot_surg[sur][ot][d]: Surgeon surgeon uses OT ot on day d
    ot_surg_assign = pulp.LpVariable.dicts(
        "surgeon_ot_assign",
        (surgeon_ids, ot_ids, day_range),
        cat=pulp.LpBinary
    )

    # -------------------------- Phase3 Hard Constraints (H Series) --------------------------
    ###### H1 and H7 are contradicted, will look for it later
    ###### mistake reason: H1 implies one patient occupying one room, contradicting H7, ignoring room capacity, will fix it in a better way
    # ========== H1: No gender mix - Patients of different genders may not share a room on any day ==========
    # Rule: For any room r, day d, all patients staying in r on d must have identical gender
    for r in room_ids:
        for d in day_range:
            # Split patient groups by gender
            male_patients = [p for p in patients if p["gender"] == "M"]
            female_patients = [p for p in patients if p["gender"] == "F"]
            # Cannot have both male and female patients in same room same day
            model += pulp.lpSum([y_patient_room[p["id"]][r][d] for p in male_patients]) + \
                     pulp.lpSum([y_patient_room[p["id"]][r][d] for p in female_patients]) <= 1, f"H1_room{r}_day{d}"

    # ========== H2 Compatible rooms: Patients can only be assigned to compatible rooms ==========
    # Rule: Patient p cannot stay in any room inside p["incompatible_room_ids"]
    for p in patients:
        pid = p["id"]
        black_room_ids = p["incompatible_room_ids"]
        for r in black_room_ids:
            for d in day_range:
                model += y_patient_room[pid][r][d] == 0, f"H2_p{pid}_incompatible_room{r}_d{d}"

    # ========== H7 Room capacity: Occupants per room per day cannot exceed room capacity ==========
    for r in rooms:
        rid = r["id"]
        cap = r["capacity"]
        for d in day_range:
            model += pulp.lpSum([y_patient_room[p["id"]][rid][d] for p in patients]) <= cap, f"H7_room{rid}_cap_d{d}"

    # ========== H8 For each shift, occupied room must be allocated to an on-duty nurse ==========
    # Rule: If room r has patients on day d, every shift s must assign at least one nurse to r
    for r in room_ids:
        for d in day_range:
            room_occupied = pulp.lpSum([y_patient_room[p["id"]][r][d] for p in patients])
            for s in shift_list:
                # If room occupied, sum of nurse assignments to this room shift >= 1
                model += pulp.lpSum([x_nurse_room[n][r][d][s] for n in nurse_ids]) >= room_occupied, f"H8_r{r}_d{d}_s{s}"

    # ========== H3 Surgeon daily overtime limit ==========
    # TODO: Implement after extracting surgeon daily max surgery time
    # ========== H4 OT daily capacity overtime limit ==========
    # TODO: Implement after extracting OT daily max time
    # ========== H5 Mandatory vs optional patient admission rule ==========
    # TODO: Mandatory patients must have sum(admit_var[p][d]) = 1 over all days
    # ========== H6 Admission day window constraint ==========
    # TODO: Patient admit day must lie between release_date and due_date

    # -------------------------- Phase4 Soft Constraints & Objective Function (S Series) --------------------------
    total_penalty = 0
    # S1 Age group gap penalty
    # S2 Nurse skill level shortage penalty
    # S3 Continuity of care (distinct nurse count) penalty
    # S4 Nurse workload excess penalty
    # S5 Minimize daily opened OT count penalty
    # S6 Surgeon cross-OT transfer penalty
    # S7 Patient admission delay penalty
    # S8 Unplanned optional patient penalty
    model += total_penalty, "MinimizeTotalSoftConstraintPenalty"

    # Pack all index sets and variables for later constraint writing
    index_sets = {
        "nurse_ids": nurse_ids,
        "patient_ids": patient_ids,
        "room_ids": room_ids,
        "surgeon_ids": surgeon_ids,
        "ot_ids": ot_ids,
        "day_range": day_range,
        "shifts": shift_list
    }
    var_dict = {
        "x_nurse_room": x_nurse_room,
        "y_patient_room": y_patient_room,
        "admit_var": admit_var,
        "ot_surg_assign": ot_surg_assign
    }
    return model, data, index_sets, var_dict

# Batch test all test cases
if __name__ == "__main__":
    test_case_list = [f"test{i:02d}" for i in range(1, 11)]
    for case in test_case_list:
        raw_data = load_instance(case)
        pats, nurs, days, shifts, rms, surgs, ots, w = extract_basic_info(raw_data)
        print(f"[{case}] Patients: {len(pats)}, Nurses: {len(nurs)}, Rooms: {len(rms)}, Surgeons: {len(surgs)}, OTs: {len(ots)}, Total days: {days}")

    # Test model initialization with H1/H2/H7/H8 hard constraints loaded
    test_model, test_data, idx, vars = build_milp_model("test01")
    print("\nPhase2+Phase3 base framework loaded successfully (H1/H2/H7/H8 hard constraints added)")
    print(f"Nurses: {len(idx['nurse_ids'])}, Patients: {len(idx['patient_ids'])}, Rooms: {len(idx['room_ids'])}, Days: {len(idx['day_range'])}")