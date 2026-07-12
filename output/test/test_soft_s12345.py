import sys
import os
import json
import time

# Get the absolute path of the current test file
current_test_file = os.path.abspath(__file__)
# Go up two levels of directories: output/test → Root directory of the IHTC_Summer_Project
project_root = os.path.abspath(os.path.join(os.path.dirname(current_test_file), "../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.model import build_milp_model
import pulp

if __name__ == "__main__":
    # Config test case name, easy to switch datasets
    test_case = "test01"
    # Build full model (Hard H1-H8 + S1/S2/S3/S4/S5 soft)
    model, raw_data, idx, vars = build_milp_model(test_case)
    
    # Update print prompt to include S5
    print("Model built successfully! Hard H1-H8 + S1/S2/S3/S4/S5 soft constraints loaded.")
    print(f"Total variables count: {model.numVariables()}")
    print(f"Total constraints count: {model.numConstraints()}")

    # Record solve start time
    start_time = time.time()

    # 120-second timeout limit for solving to prevent freezing
    solver = pulp.PULP_CBC_CMD(msg=0, timeLimit=120)
    model.solve(solver)

    solve_time = round(time.time() - start_time, 2)
    print(f"\nSolver Status: {pulp.LpStatus[model.status]}")
    print(f"Solve Time: {solve_time} seconds")
    print(f"Global minimal total soft penalty: {pulp.value(model.objective):.2f}")

    # Export structured schedule JSON only if optimal solution exists
    if pulp.LpStatus[model.status] == "Optimal":
        # Unpack core variables & index data
        y = vars["y_patient_room"]
        x = vars["x_nurse_room_shift"]
        admit = vars["admit_var"]
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

        # Fill patient admission & room & operating theater info
        for p in raw_patients:
            pid = p["id"]
            sol_p = {"id": pid}
            admit_day = "none"
            # Locate patient's admission day
            for d in day_range:
                if pulp.value(admit[pid][d]) > 0.5:
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
                sol_p["operating_theater"] = p["operating_theater"]
            output_sol["patients"].append(sol_p)

        # Fill all nurse daily shift room assignments
        for n in raw_nurses:
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

        # Summarize total penalty cost
        total_cost = pulp.value(model.objective)
        output_sol["costs"] = [f"Total Cost: {total_cost:.2f}"]

        # Generate unique filename with timestamp to avoid overwriting old results
        time_stamp = time.strftime("%Y%m%d_%H%M%S")
        out_file_name = f"solution_{test_case}_{time_stamp}.json"
        out_file_path = os.path.join(project_root, "output", "test", out_file_name)

        # Write schedule data into independent json file
        with open(out_file_path, "w", encoding="utf-8") as f:
            json.dump(output_sol, f, indent=2, ensure_ascii=False)

        print(f"\n✅ Unique schedule file saved successfully:")
        print(f"File Path: {out_file_path}")
        print(f"File Name: {out_file_name}")

    else:
        print("\n⚠️ Model does NOT have optimal solution, skip exporting schedule file.")