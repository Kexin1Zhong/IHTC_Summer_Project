import pulp

def add_h2_constraint(model, data, index_sets, var_dict):
    """
    H2 Hard Constraint Builder: Patients cannot stay in incompatible rooms
    Hard Rule: Patient p cannot occupy any room listed in p["incompatible_room_ids"] on any day
    """
    patients = data["patients"]
    day_range = index_sets["day_range"]
    y_patient_room = var_dict["y_patient_room"]

    for p in patients:
        pid = p["id"]
        black_room_ids = p["incompatible_room_ids"]
        for r in black_room_ids:
            for d in day_range:
                model += y_patient_room[pid][r][d] == 0, f"H2_p{pid}_incompatible_room{r}_d{d}"


def validate_h2_solution(sol_data, index_sets, var_dict):
    """
    Post-solution validation for H2 incompatible room rule
    Detect if any patient is assigned to their forbidden room on any day
    Return total violation count and print violation logs
    """
    all_patients = sol_data["patients"]
    y = var_dict["y_patient_room"]
    days = index_sets["day_range"]
    h2_violation_count = 0

    # H2 Rule Verification: Patients cannot be placed in rooms incompatible with them
    for p in all_patients:
        pid = p["id"]
        forbidden_rooms = p["incompatible_room_ids"]
        for rid in forbidden_rooms:
            for d in days:
                occupy_val = pulp.value(y[pid][rid][d])
                # If the patient has any check-in records for restricted rooms, a violation shall be confirmed
                if occupy_val > 1e-6:
                    h2_violation_count += 1
                    print(f"H2 VIOLATION DETECTED: Patient {pid} incompatible room {rid}, Day {d} | Occupied = {occupy_val}")

    if h2_violation_count == 0:
        print("✅ H2 Test Passed: No patient assigned to incompatible rooms")
    else:
        print(f"❌ H2 Test Failed: Total {h2_violation_count} incompatible room assignments found")
    return h2_violation_count