import sys
import os
import json
import time
import pulp

current_test_file = os.path.abspath(__file__)
project_root = os.path.abspath(os.path.join(os.path.dirname(current_test_file), "../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.model import build_milp_model

if __name__ == "__main__":
    test_case = "test01"

# ===================== Mode Toggle Switch =====================
    # True = Full construction + solving + result export (Formal Run)
    # False = Model construction only, skip solving. Used for debugging constraints/weights 【Avoid long-time freezing】

    RUN_SOLVE = False
    # =======================================================
    
    model, raw_data, idx, vars, s1_expr, s2_expr, s3_expr, s4_expr, s5_expr, s6_expr, s7_expr, s8_expr = build_milp_model(test_case)

    # ===== Debug Print: Verify Weights and 8 Sets of Soft Constraint Expressions (Focus on Troubleshooting Abnormal Cost) =====
    print("==== DEBUG: Load weights from data ====")
    print(raw_data["weights"])
    print("\n==== DEBUG: Soft constraint penalty expressions ====")
    print("s1(AgeMix):", s1_expr)
    print("s2(Skill):", s2_expr)
    print("s3(Continuity):", s3_expr)
    print("s4(Excess):", s4_expr)
    print("s5(OpenOT):", s5_expr)
    print("s6(SurgeonTransfer):", s6_expr)
    print("s7(Delay):", s7_expr)
    print("s8(Unscheduled):", s8_expr)
    
    if not RUN_SOLVE:
        print("\n【调试模式开启】已跳过求解，仅完成模型构建校验。如需正式求解，请修改上方 RUN_SOLVE = True")
    else:
        # Use CBC after permission repair
        model.solve(pulp.PULP_CBC_CMD(msg=False))

        status = pulp.LpStatus[model.status]
        print(f"\nSolver Status: {status}")
        
# Keep all the code for reading cost and exporting JSON unchanged below


        if status != "Optimal":
            print("No optimal solution, exit.")
        else:
            # Read all itemized costs
            s1 = pulp.value(s1_expr)
            s2 = pulp.value(s2_expr)
            s3 = pulp.value(s3_expr)
            s4 = pulp.value(s4_expr)
            s5 = pulp.value(s5_expr)
            s6 = pulp.value(s6_expr)
            s7 = pulp.value(s7_expr)
            s8 = pulp.value(s8_expr)
            total = pulp.value(model.objective)

            # Output format fully aligned with the official answers
            cost_str = (
                f"Cost: {total:.0f}, Unscheduled: {s8:.0f}, Delay: {s7:.0f}, OpenOT: {s5:.0f}, "
                f"AgeMix: {s1:.0f}, Skill: {s2:.0f}, Excess: {s4:.0f}, Continuity: {s3:.0f}, SurgeonTransfer: {s6:.0f}"
            )
            print(f'"costs": [ "{cost_str}" ]')

            # Scheme Export
            y = vars["y_patient_room"]
            x = vars["x_nurse_room_shift"]
            admit_var = vars["admit_var"]
            day_range = idx["day_range"]
            shift_types = idx["shift_types"]

            output_sol = {"patients": [], "nurses": [], "costs": [cost_str]}

            for p in raw_data["patients"]:
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
                    for r in idx["room_ids"]:
                        if pulp.value(y[pid][r][d0]) > 0.5:
                            assign_room = r
                            break
                if assign_room is not None:
                    sol_p["room"] = assign_room
                output_sol["patients"].append(sol_p)

            for n in raw_data["nurses"]:
                nid = n["id"]
                sol_n = {"id": nid, "assignments": []}
                for d in day_range:
                    for s in shift_types:
                        rooms = []
                        for r in idx["room_ids"]:
                            if pulp.value(x[nid][r][d][s]) > 0.5:
                                rooms.append(r)
                        sol_n["assignments"].append({"day": d, "shift": s, "rooms": rooms})
                output_sol["nurses"].append(sol_n)

            out_file_name = f"solution_{test_case}_{time.strftime('%Y%m%d_%H%M%S')}.json"
            out_file_path = os.path.join(project_root, "output", "test", out_file_name)
            with open(out_file_path, "w", encoding="utf-8") as f:
                json.dump(output_sol, f, indent=2, ensure_ascii=False)
            print(f"\nSolution saved to: {out_file_path}")