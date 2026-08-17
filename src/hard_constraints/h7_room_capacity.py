import pulp

def add_h7_constraint(model, data, index_sets, var_dict):
    """
    H7 Hard Constraint Builder: Daily room occupancy cannot exceed room capacity
    Hard Rule: The total number of patients staying in a single room on one day cannot exceed its predefined capacity
    """
    patients = data["patients"]
    rooms = data["rooms"]
    day_range = index_sets["day_range"]
    y_patient_room = var_dict["y_patient_room"]

    for r in rooms:
        rid = r["id"]
        cap = r["capacity"]
        for d in day_range:
            model += pulp.lpSum([y_patient_room[p["id"]][rid][d] for p in patients]) <= cap, f"H7_room{rid}_cap_d{d}"


def validate_h7_solution(sol_data, index_sets, var_dict):
    """
    Post-solution validation for H7 room capacity rule
    Detect if any room exceeds its maximum patient capacity on any day
    Return total violation count and print violation logs
    """
    all_rooms = sol_data["rooms"]
    all_patients = sol_data["patients"]
    y = var_dict["y_patient_room"]
    days = index_sets["day_range"]
    h7_violation_count = 0

    # H7 Rule: Total patients in one room per day cannot exceed room capacity
    for room in all_rooms:
        rid = room["id"]
        cap = room["capacity"]
        for d in days:
            total_occupy = 0.0
            for p in all_patients:
                pid = p["id"]
                val = pulp.value(y[pid][rid][d])
                total_occupy += val
            # Exceed capacity = violation
            if total_occupy - cap > 1e-6:
                h7_violation_count += 1
                print(f"H7 VIOLATION DETECTED: Room {rid}, Day {d} | Capacity={cap}, Actual occupants={total_occupy:.2f}")

    if h7_violation_count == 0:
        print("✅ H7 Test Passed: All rooms satisfy daily capacity limit")
    else:
        print(f"❌ H7 Test Failed: Total {h7_violation_count} room capacity over-limit violations")
    return h7_violation_count