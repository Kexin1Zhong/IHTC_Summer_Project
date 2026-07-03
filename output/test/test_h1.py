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

    # -------------------------- Phase3 Hard Constraints (H Series) --------------------------
    # ========== H1: No gender mix - Patients of different genders may not share a room on any day ==========
    # Hard Constraint Formal Instruction:
    # 1. For any room r and any simulation day d, the room cannot simultaneously accommodate patients of gender A and gender B.
    # 2. Multiple patients with identical gender are allowed to occupy the same multi-bed room, limited only by the room’s capacity defined in H7.
    # 3. Two auxiliary binary variables are introduced to indicate whether the room contains patients of each gender:
    #    - has_A = 1 if at least one gender A patient stays in room r on day d; otherwise has_A = 0
    #    - has_B = 1 if at least one gender B patient stays in room r on day d; otherwise has_B = 0
    # 4. Auxiliary linking constraints: If the total count of a gender exceeds 0, its corresponding binary flag must be forced to 1.
    # 5. Core feasibility constraint: The sum of two binary flags cannot exceed 1, forbidding mixed-gender co-location.
    # 6. This formulation fully supports multi-bed rooms and eliminates logical conflict with H7 room capacity limit.
    for r in rooms:
        rid = r["id"]
        cap = r["capacity"]  # Obtain maximum number of patients this room can hold
        for d in day_range:
            # Split all patients into two gender groups based on dataset label "A" / "B"
            group_A = [p for p in patients if p["gender"] == "A"]
            group_B = [p for p in patients if p["gender"] == "B"]

            # Calculate total number of gender A patients staying in room rid on day d
            sum_A = pulp.lpSum([y_patient_room[p["id"]][rid][d] for p in group_A])
            # Calculate total number of gender B patients staying in room rid on day d
            sum_B = pulp.lpSum([y_patient_room[p["id"]][rid][d] for p in group_B])

            # Create binary auxiliary variables to mark whether this room has A / B patients on day d
            has_A = pulp.LpVariable(f"hasA_room{rid}_day{d}", cat=pulp.LpBinary)
            has_B = pulp.LpVariable(f"hasB_room{rid}_day{d}", cat=pulp.LpBinary)

            # Link sum_A to binary flag has_A: sum_A > 0 → has_A = 1
            model += sum_A <= cap * has_A, f"H1_auxA_room{rid}_day{d}"
            # Link sum_B to binary flag has_B: sum_B > 0 → has_B = 1
            model += sum_B <= cap * has_B, f"H1_auxB_room{rid}_day{d}"
            # Core hard constraint: Cannot have both gender A and gender B patients in the same room on the same day
            model += has_A + has_B <= 1, f"H1_no_gender_mix_room{rid}_day{d}"

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
    # Hard Constraint Formal Instruction:
    # 1. For any room r, any day d, any shift s: if the room contains at least one patient on day d,
    #    at least one nurse must be assigned to this room during shift s.
    # 2. Empty rooms (zero patients) have no mandatory nurse assignment requirement.
    # 3. Auxiliary binary variable has_patient: has_patient = 1 if room r has ≥1 patient on day d; else 0.
    # 4. Linking big-M constraint: If total room occupants > 0, force has_patient = 1.
    # 5. Core constraint: Total assigned nurses for the shift ≥ has_patient, which enforces nurse assignment only for occupied rooms.
    for r in room_ids:
        for d in day_range:
            # Total patients staying in room r on day d
            room_occupied = pulp.lpSum([y_patient_room[p["id"]][r][d] for p in patients])
            # Get pre-cached room maximum capacity for Big-M parameter
            room_cap = room_cap_dict[r]
            # Binary auxiliary flag to mark room occupancy status
            has_patient = pulp.LpVariable(f"H8_hasPatient_r{r}_d{d}", cat=pulp.LpBinary)
            # Link occupancy sum to binary flag
            model += room_occupied <= room_cap * has_patient, f"H8_linkFlag_r{r}_d{d}"
            # Apply nurse assignment rule for every shift
            for s in shift_list:
                total_nurse_on_shift = pulp.lpSum([x_nurse_room[n][r][d][s] for n in nurse_ids])
                # Core H8 hard constraint
                model += total_nurse_on_shift >= has_patient, f"H8_core_r{r}_d{d}_s{s}"

    # ========== H3 Surgeon overtime: The maximum daily surgery time of a surgeon must not be exceeded ==========
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

    # ========== Dedicated H1 Constraint Validation Test Logic ==========
    print("\n==================== H1 Constraint Validation Test ====================")
    # Build model for small test01 (fast to solve)
    test_model, test_data, idx, vars = build_milp_model("test01")

    # Solve with CBC solver, print solver log, set time limit 120s
    test_model.solve(pulp.PULP_CBC_CMD(msg=1, timeLimit=120))
    print(f"Solver Status: {pulp.LpStatus[test_model.status]}")
    if test_model.status != pulp.LpStatusOptimal:
        print("Warning: No feasible solution found, H1 or other hard constraints may conflict!")
    else:
        print("Feasible schedule found, start H1 check...")

    # Extract data & variables for H1 inspection
    all_patients = test_data["patients"]
    y = vars["y_patient_room"]
    room_list = test_data["rooms"]
    days = idx["day_range"]

    # Iterate every room & every day to verify H1 rule: no A+B coexist
    h1_violation_count = 0
    for room in room_list:
        r_id = room["id"]
        for d in days:
            sumA = 0
            sumB = 0
            for p in all_patients:
                p_id = p["id"]
                val = pulp.value(y[p_id][r_id][d])
                if p["gender"] == "A":
                    sumA += val
                else:
                    sumB += val
            # H1 violation condition: both gender A and B have patients in same room same day
            if sumA > 1e-6 and sumB > 1e-6:
                h1_violation_count += 1
                print(f"H1 VIOLATION DETECTED: Room {r_id}, Day {d} | A count={sumA}, B count={sumB}")

    if h1_violation_count == 0:
        print("✅ H1 Test Passed: No mixed-gender rooms found in any room/day combination")
    else:
        print(f"❌ H1 Test Failed: Total {h1_violation_count} mixed-gender room/day violations exist")