import pulp

def add_s3_care_continuity_penalty(model: pulp.LpProblem, data: dict, index_sets, var_dict) -> pulp.LpAffineExpression:
    print("========== S3 DEBUG: S3 function starts running ==========")
    # 索引集合读取
    patient_ids = index_sets["patient_ids"]
    nurse_ids = index_sets["nurse_ids"]
    room_ids = index_sets["room_ids"]
    day_range = index_sets["day_range"]
    shift_types = index_sets["shift_types"]

    patients_raw = data["patients"]
    weight_s3 = data["weights"]["continuity_of_care"]
    print(f"S3 DEBUG: S3 penalty weight = {weight_s3}")

  # Global Basic Variables
    y = var_dict["y_patient_room"]    # y[p][r][d]: Patient p stays in room r on day d
    x = var_dict["x_nurse_room_shift"]# x[n][r][d][s]: Nurse n is on duty in room r on day d during shift s

    # 1. Define the core binary variable: care_link[p][n][d][s]
    care_link = pulp.LpVariable.dicts(
        "s3_care_link",
        (patient_ids, nurse_ids, day_range, shift_types),
        cat=pulp.LpBinary
    )
    # 2. unique_nurse[p][n]: whether nurse n has cared for patient p
    unique_nurse = pulp.LpVariable.dicts(
        "s3_unique_nurse",
        (patient_ids, nurse_ids),
        cat=pulp.LpBinary
    )
    # 3. Total number of nurses assigned to each patient
    nurse_count = pulp.LpVariable.dicts(
        "s3_nurse_total_count",
        patient_ids,
        lowBound=0, cat=pulp.LpInteger
    )
    # 4. Penalty Variable for Excess Nurses
    s3_penalty = pulp.LpVariable.dicts(
        "s3_overage_penalty",
        patient_ids,
        lowBound=0, cat=pulp.LpContinuous
    )

    total_s3 = pulp.LpAffineExpression()

    # ========== Fix 1: Properly Construct Admission and Discharge Date Mapping (Adapted to the Fields of Your Dataset) ==========
    adm_map = {}
    stay_end_map = {}
    for p in patients_raw:
        pid = p["id"]
        adm_day = p["surgery_release_day"]
        los = p["length_of_stay"]
        dis_day = adm_day + los
        adm_map[pid] = adm_day
        stay_end_map[pid] = dis_day

    valid_patient_cnt = 0
    max_day_num = len(day_range)
    max_shift_num = len(shift_types)
    max_link = max_day_num * max_shift_num

    # Traverse each patient one by one
    for pid in patient_ids:
        adm_day = adm_map[pid]
        dis_day = stay_end_map[pid]
        # It theoretically cannot be None at present, and the fallback judgment is reserved
        if adm_day is None or dis_day is None:
            print(f"S3 DEBUG: Patient {pid} not admitted, skip")
            continue
        valid_patient_cnt += 1
        print(f"S3 DEBUG: Process Patient {pid}, admission:{adm_day}, discharge:{dis_day}")

        # Only traverse the days within the patient's hospitalization period, filter out invalid days and reduce constraints
        valid_days = [d for d in day_range if adm_day <= d <= dis_day]

        # ========== Fix 2: Optimization of loop hierarchy, elevate room to the outermost layer to reduce redundant calculations ==========
        for rid in room_ids:
            for nid in nurse_ids:
                for d in valid_days:
                    for s in shift_types:
                        # Standard 0-1 logical constraints for nursing binding, writing format remains unchanged, only the loop range is narrowed down
                        model += care_link[pid][nid][d][s] >= y[pid][rid][d] + x[nid][rid][d][s] - 1
                        model += care_link[pid][nid][d][s] <= y[pid][rid][d]
                        model += care_link[pid][nid][d][s] <= x[nid][rid][d][s]

        # ========== Fix 3: Standardize the unique_nurse constraint to eliminate numerical instability of large values ==========
        for nid in nurse_ids:
            sum_link = pulp.lpSum([care_link[pid][nid][d][s] for d in valid_days for s in shift_types])
            # Standard writing rule: unique_nurse is set to 1 upon any single binding operation
            model += sum_link <= unique_nurse[pid][nid] * max_link

        # Constraint 3: Count the total number of nurses
        model += nurse_count[pid] == pulp.lpSum([unique_nurse[pid][nid] for nid in nurse_ids])

        # ========== Fix 4: Upper and lower bound constraints for penalty variables to prevent unlimited expansion ==========
        model += s3_penalty[pid] >= nurse_count[pid] - 3
        model += s3_penalty[pid] >= 0
        model += s3_penalty[pid] <= nurse_count[pid]

        total_s3 += weight_s3 * s3_penalty[pid]

    print(f"S3 DEBUG: Valid admitted patients processed: {valid_patient_cnt}")
    print("========== S3 function construction finished ==========\n")
    return total_s3