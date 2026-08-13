# -*- coding: utf-8 -*-
import sys
import os
import json
import time
import shutil
import pulp

# ===================== Global Constant Configuration Area =====================
SOLVE_TIMEOUT = 300    # Solving timeout (seconds)
SOLVER_MSG = False     # Detailed log switch
DECISION_EPS = 1e-4    # Binary variable float judge threshold
RUN_SOLVE = True       # Main solve master switch
test_case = "test01"
# =============================================================================

# Path auto locate
current_test_file = os.path.abspath(__file__)
project_root = os.path.abspath(os.path.join(os.path.dirname(current_test_file), "../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

# Output dir auto create
output_dir = os.path.join(project_root, "output", "test")
os.makedirs(output_dir, exist_ok=True)

from src.model import build_milp_model


# ===================== General Tool Function Encapsulation =====================
def get_binary_value(var_expr) -> int:
    """Unified binary variable value acquisition, anti-float precision error"""
    if var_expr is None:
        return 0
    val = pulp.value(var_expr)
    return 1 if val > DECISION_EPS else 0


def build_solver_instance():
    """
    Generate standardized HiGHS solver instance
    Use highspy native binding, no executable path dependency, stable on Mac ARM
    Inherit global timeout & log config
    """
    base_kwargs = {
        "msg": SOLVER_MSG,
        "timeLimit": SOLVE_TIMEOUT
    }
    print("✅ Using HiGHS solver (native highspy binding)")
    return pulp.HiGHS(**base_kwargs)
# =============================================================================


if __name__ == "__main__":
    # Step 1: Build MILP Model
    print(f"Start building the model, test case：{test_case}")
    build_start = time.time()
    try:
        model, raw_data, idx, vars_dict, \
        s1_expr, s2_expr, s3_expr, s4_expr, \
        s5_expr, s6_expr, s7_expr, s8_expr = build_milp_model(test_case)
    except Exception as e:
        print(f"❌ Model construction failed: {e}")
        sys.exit(1)
    build_cost = round(time.time() - build_start, 2)
    print(f"Model built successfully, cost: {build_cost}s\n")


    # Skip solving switch
    if not RUN_SOLVE:
        print("\n[Debug Mode] Skip solving, only model structure check finished. Set RUN_SOLVE=True for formal calculation")
        sys.exit(0)

    # Step3: Solver initialization & solution
    print("\nStart HiGHS solving process...")
    solve_start = time.time()
    solver = build_solver_instance()
    try:
        model.solve(solver)
    except Exception as e:
        print(f"❌ Solver runtime crash: {e}")
        sys.exit(1)
    solve_cost = round(time.time() - solve_start, 2)
    solve_status = pulp.LpStatus[model.status]
    print(f"Solve time: {solve_cost}s | Solver Status: {solve_status}")

    # Step4: Status branch judgment
    if solve_status == "Optimal":
        print("✅ Optimal feasible solution obtained")
    elif solve_status == "Infeasible":
        print("❌ Model infeasible, exit program")
        sys.exit(1)
    elif solve_status == "NotSolved":
        print(f"⚠️ Exceed timeout {SOLVE_TIMEOUT}s, solving incomplete")
        sys.exit(1)
    else:
        print(f"⚠️ Abnormal status [{solve_status}], exit")
        sys.exit(1)

    # Step5: Collect all penalty objective values
    s1 = pulp.value(s1_expr)
    s2 = pulp.value(s2_expr)
    s3 = pulp.value(s3_expr)
    s4 = pulp.value(s4_expr)
    s5 = pulp.value(s5_expr)
    s6 = pulp.value(s6_expr)
    s7 = pulp.value(s7_expr)
    s8 = pulp.value(s8_expr)
    total_cost = pulp.value(model.objective)

    cost_str = (
        f"Cost: {total_cost:.0f}, Unscheduled: {s8:.0f}, Delay: {s7:.0f}, OpenOT: {s5:.0f}, "
        f"AgeMix: {s1:.0f}, Skill: {s2:.0f}, Excess: {s4:.0f}, Continuity: {s3:.0f}, SurgeonTransfer: {s6:.0f}"
    )
    print(f'"costs": [ "{cost_str}" ]')

    print(f"[DEBUG] raw_data nurses count: {len(raw_data.get('nurses', []))}")
    print(f"[DEBUG] raw_data surgeons count: {len(raw_data.get('surgeons', []))}")
    # p01 admit_day=1，已经分配t1手术
    ps_val = get_binary_value(vars_dict["patient_surgery_var"]["p01"]["s0"]["t1"][1])
    ot_val = get_binary_value(vars_dict["ot_surg_assign"]["s0"]["t1"][1])
    print(f"[DEBUG] p01 d=1 patient_surgery_var={ps_val}, ot_surg_assign[s0][t1][1]={ot_val}")

 # Step6: Parse decision variables
    y_patient_room = vars_dict["y_patient_room"]
    x_nurse_room_shift = vars_dict["x_nurse_room_shift"]
    admit_var = vars_dict["admit_var"]
    ot_surg_assign = vars_dict["ot_surg_assign"]
    patient_surgery_var = vars_dict["patient_surgery_var"]  # 新增取出手术变量

    day_range = idx["day_range"]
    shift_types = idx["shift_types"]
    room_ids = idx["room_ids"]
    surgeon_ids = idx["surgeon_ids"]
    ot_ids = idx["ot_ids"]

    output_sol = {
        "patients": [],
        "nurses": [],
        "surgeon_ot_schedule": [],
        "costs": [cost_str]
    }

    # ========== 患者格式化：id / admission_day(int) / room / operating_theater ==========
    for patient in raw_data.get("patients", []):
        pid = patient["id"]
        admit_day = None
        for d in day_range:
            if get_binary_value(admit_var[pid][d]):
                admit_day = d
                break
        room_tag = None
        if admit_day is not None:
            for r in room_ids:
                if get_binary_value(y_patient_room[pid][r][admit_day]):
                    room_tag = r
                    break
        #==== H10回填手术室、外科医生 ====
        ot_tag = None
        sur_tag = None
        if admit_day is not None:
            for sur in surgeon_ids:
                for ot in ot_ids:
                    if get_binary_value(patient_surgery_var[pid][sur][ot][admit_day]):
                        ot_tag = ot
                        sur_tag = sur
                        break
                if ot_tag is not None:
                    break

        patient_item = {
            "id": pid,
            "admission_day": admit_day if admit_day is not None else None,
            "room": room_tag,
            "operating_theater": ot_tag,
            "operating_surgeon": sur_tag
        }
        output_sol["patients"].append(patient_item)
        
       
        
# ----------------这里下面插入护士、手术室解析代码----------------
for nurse in raw_data.get("nurses", []):
    nid = nurse["id"]
    nurse_item = {"id": nid, "assignments": []}
    for d in day_range:
        for s in shift_types:
            bind_rooms = []
            for r in room_ids:
                if get_binary_value(x_nurse_room_shift[nid][r][d][s]):
                    bind_rooms.append(r)
            if bind_rooms:
                nurse_item["assignments"].append({
                    "day": d,
                    "shift": s,
                    "rooms": bind_rooms
                })
    output_sol["nurses"].append(nurse_item)

for sid in surgeon_ids:
    ot_record = {
        "surgeon_id": sid,
        "ot_usage": []
    }
    for d in day_range:
        used_ots = []
        for otid in ot_ids:
            if get_binary_value(ot_surg_assign[sid][otid][d]):
                used_ots.append(otid)
        if used_ots:
            ot_record["ot_usage"].append({
                "day": d,
                "theaters": used_ots
            })
    output_sol["surgeon_ot_schedule"].append(ot_record)


    # Step7: Export solution json
    def dump_solution_json(sol_data: dict, save_dir: str, case_name: str) -> str:
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = f"solution_{case_name}_{timestamp}.json"
        full_path = os.path.join(save_dir, filename)
        try:
            with open(full_path, "w", encoding="utf-8") as f:
                json.dump(sol_data, f, indent=2, ensure_ascii=False)
            return full_path
        except Exception as e:
            print(f"❌ JSON write exception: {str(e)}")
            return ""

    save_path = dump_solution_json(output_sol, output_dir, test_case)
    if save_path:
        print(f"\n✅ Solution file saved: {save_path}")
    else:
        print("\n❌ Result file saving failed")

    # ========== 调试代码：检测y_patient_room是否全为0，定位约束问题 ==========
    print("\n====== Debug: Count non-zero patient-room variables ======")
    cnt_room_valid = 0
    for pid in idx["patient_ids"]:
        for d in day_range:
            for rid in room_ids:
                if get_binary_value(y_patient_room[pid][rid][d]) == 1:
                    cnt_room_valid += 1
    print(f"y_patient_room 取值为1的总数量：{cnt_room_valid}")
    if cnt_room_valid == 0:
        print("警告：所有患者病房占用变量均为0，根源在硬约束(H7/H2等)逻辑错误，不是导出代码")

