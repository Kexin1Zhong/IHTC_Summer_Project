import pulp

def add_h1_constraint(model, data, index_sets, var_dict):
    """
    H1 Hard Constraint Builder: No gender mix may share a single room
    """
    patients = data["patients"]
    rooms = data["rooms"]
    day_range = index_sets["day_range"]
    y_patient_room = var_dict["y_patient_room"]

    for r in rooms:
        rid = r["id"]
        cap = r["capacity"]
        for d in day_range:
            group_A = [p for p in patients if p["gender"] == "A"]
            group_B = [p for p in patients if p["gender"] == "B"]

            sum_A = pulp.lpSum([y_patient_room[p["id"]][rid][d] for p in group_A])
            sum_B = pulp.lpSum([y_patient_room[p["id"]][rid][d] for p in group_B])

            has_A = pulp.LpVariable(f"hasA_room{rid}_day{d}", cat=pulp.LpBinary)
            has_B = pulp.LpVariable(f"hasB_room{rid}_day{d}", cat=pulp.LpBinary)

            model += sum_A <= cap * has_A, f"H1_auxA_room{rid}_day{d}"
            model += sum_B <= cap * has_B, f"H1_auxB_room{rid}_day{d}"
            model += has_A + has_B <= 1, f"H1_no_gender_mix_room{rid}_day{d}"


def validate_h1_solution(sol_data, index_sets, var_dict):
    """
    Post-solution validation for H1 gender mix rule
    Return total violation count and print logs
    """
    patients = sol_data["patients"]
    rooms = sol_data["rooms"]
    day_range = index_sets["day_range"]
    y = var_dict["y_patient_room"]
    h1_violation_count = 0

    for room in rooms:
        rid = room["id"]
        for d in day_range:
            sumA = 0.0
            sumB = 0.0
            for p in patients:
                if p["id"] == rid:
                    continue
                val = pulp.value(y[p["id"]][rid][d])
                if p["gender"] == "A":
                    sumA += val
                else:
                    sumB += val
            if sumA > 1e-6 and sumB > 1e-6:
                h1_violation_count += 1
                print(f"H1 VIOLATION: Room {rid}, Day {d} mixed A/B patients")

    if h1_violation_count == 0:
        print("✅ H1 Test Passed: No mixed gender rooms")
    else:
        print(f"❌ H1 Test Failed, total {h1_violation_count} mixed gender violations")
    return h1_violation_count