import sys
import os
import json
import time
import pulp

# Get the absolute path of the current test file
current_test_file = os.path.abspath(__file__)
# Go up two levels of directories: output/test → Root directory of the IHTC_Summer_Project
project_root = os.path.abspath(os.path.join(os.path.dirname(current_test_file), "../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.model import build_milp_model

if __name__ == "__main__":
    test_case = "test01"
    model, raw_data, idx, vars, s1_expr, s2_expr, s3_expr, s4_expr, s5_expr, s6_expr, s7_expr, s8_expr = build_milp_model(test_case)
    
    print("Model built successfully! Hard H1-H8 + S1/S2/S3/S4/S5/S6/S7/S8 soft constraints loaded.")
    print(f"Total variables count: {model.numVariables()}")
    print(f"Total constraints count: {model.numConstraints()}")

    start_time = time.time()
    solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=120)
    model.solve(solver)

    solve_time = round(time.time() - start_time, 2)
    print(f"\nSolver Status: {pulp.LpStatus[model.status]}")
    print(f"Solve Time: {solve_time} seconds")
    print(f"Global minimal total soft penalty: {pulp.value(model.objective):.2f}")

    if pulp.LpStatus[model.status] == "Optimal":
        y = vars["y_patient_room"]
        x = vars["x_nurse_room_shift"]
        admit_var = vars["admit_var"]
        patient_ids = idx["patient_ids"]
        nurse_ids = idx["nurse_ids"]
        room_ids = idx["room_ids"]
        day_range = idx["day_range"]
        shift_types = idx["shift_types"]
        raw_patients = raw_data["patients"]
        raw_nurses = raw_data["nurses"]

        output_sol = {
            "patients": [],
            "nurses": [],
            "costs": []
        }

        # Fill patient admission & room info
        for p in raw_patients:
            pid = p["id"]
            sol_p = {"id": pid}
            admit_day = "none"
            for d in day_range:
                if pulp.value(admit_var[pid][d]) > 0.5:
                    admit_day = d
                    break
            sol_p["admission_day"] = str(admit_day)
            assign_room = None
            if admit_day != "none":
                d0 = int(admit_day)
                for r in room_ids:
                    if pulp.value(y[pid][r][d0]) > 0.5:
                        assign_room = r
                        break
            if assign_room is not None:
                sol_p["room"] = assign_room
            output_sol["patients"].append(sol_p)

        # Fill nurse assignments
        for n in raw_data["nurses"]:
            nid = n["id"]
            sol_n = {"id": nid, "assignments": []}
            for d in day_range:
                for s in shift_types:
                    assigned_rooms = []
                    for r in room_ids:
                        if pulp.value(x[nid][r][d][s]) > 0.5:
                            assigned_rooms.append(r)
                    sol_n["assignments"].append({
                        "day": d,
                        "shift": s,
                        "rooms": assigned_rooms
                    })
            output_sol["nurses"].append(sol_n)

        # Read each soft cost breakdown (ONLY use precomputed expressions, NO function calls)
        s1 = pulp.value(s1_expr)
        s2 = pulp.value(s2_expr)
        s3 = pulp.value(s3_expr)
        s4 = pulp.value(s4_expr)
        s5 = pulp.value(s5_expr)
        s6 = pulp.value(s6_expr)
        s7 = pulp.value(s7_expr)
        s8 = pulp.value(s8_expr)
        total = pulp.value(model.objective)

        cost_str = (
            f"Cost: {total:.0f}, Unscheduled: {s8:.0f}, Delay: {s7:.0f}, OpenOT: {s5:.0f}, "
            f"AgeMix: {s1:.0f}, Skill: {s2:.0f}, Excess: {s4:.0f}, Continuity: {s3:.0f}, SurgeonTransfer: {s6:.0f}"
        )
        output_sol["costs"] = [cost_str]

        time_stamp = time.strftime("%Y%m%d_%H%M%S")
        out_file_name = f"solution_{test_case}_{time_stamp}.json"
        out_file_path = os.path.join(project_root, "output", "test", out_file_name)

        with open(out_file_path, "w", encoding="utf-8") as f:
            json.dump(output_sol, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Unique schedule file saved successfully:")
        print(f"File Path: {out_file_path}")
        print(f"File Name: {out_file_name}")

    else:
        print("\n⚠️ Model does NOT have optimal solution, skip exporting schedule file.")