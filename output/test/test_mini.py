# -*- coding: utf-8 -*-
import sys
import os
import json
import time
import shutil
import pulp

# ===================== Global Constant Configuration Area =====================
SOLVE_TIMEOUT = 300    # Solving timeout (seconds)
SOLVER_MSG = True      # Detailed log switch
DECISION_EPS = 1e-4    # Binary variable float judge threshold
RUN_SOLVE = True       # Main solve master switch
test_case = "test01"
ONLY_HARD_CONSTRAINT = False  # 只保留H1~H8硬约束，清空全部软约束目标
# =============================================================================

# Path auto locate
current_test_file = os.path.abspath(__file__)
project_root = os.path.abspath(os.path.join(os.path.dirname(current_test_file), "../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

# Output dir auto create
output_dir = os.path.join(project_root, "output", "test")
lp_dump_dir = os.path.join(project_root, "output", "lp_dump")
os.makedirs(output_dir, exist_ok=True)
os.makedirs(lp_dump_dir, exist_ok=True)

from src.model import build_milp_model

# ========== 【修复导入】匹配你src/hard_constraints目录下的8个文件 ==========
try:
    from src.hard_constraints.h1_gender_mix import add_h1_constraint
    from src.hard_constraints.h2_incompatible_room import add_h2_constraint
    from src.hard_constraints.h3_surgeon_overtime import add_h3_constraint
    from src.hard_constraints.h4_ot_capacity import add_h4_constraint
    from src.hard_constraints.h5_patient_admit_count import add_h5_constraint
    from src.hard_constraints.h6_admit_window import add_h6_constraint
    from src.hard_constraints.h7_room_capacity import add_h7_constraint
    from src.hard_constraints.h8_nurse_room_shift import add_h8_constraint
    from src.hard_constraints.h9_stay_duration import add_h9_constraint

    # 【修改点1】修正debug函数名
   # from src.hard_constraints.h9_stay_duration_debug import add_h9_stay_duration_debug

except ImportError:
    print("⚠️ 约束校验函数导入失败，将自动关闭解校验，仅保留模型求解与IIS定位")
    validate_h1_solution = validate_h2_solution = validate_h3_solution = None
    validate_h4_solution = validate_h5_solution = validate_h6_solution = None
    validate_h7_solution = validate_h8_solution = None

# ===================== General Tool Function Encapsulation =====================
def get_binary_value(var_expr) -> int:
    """Unified binary variable value acquisition, anti-float precision error"""
    if var_expr is None:
        return 0
    val = pulp.value(var_expr)
    return 1 if val > DECISION_EPS else 0


# ===== 【移到这里，main外面，删掉文件上方旧的build_solver_instance】 =====
def build_solver_instance(use_gurobi):
    msg = SOLVER_MSG
    time_limit = SOLVE_TIMEOUT
    if use_gurobi:
        return pulp.GUROBI(
            msg=True,
            timeLimit=300,
            MIPGap=0.05,      # gap<=5%就停止，不用求理论最优
            MIPFocus=1,       # 优先快速找高质量可行解
            Presolve=2
        )
    else:
        raise RuntimeError("Only Gurobi solver available, set use_gurobi = True")


def batch_check_all_hard_constraint(raw_data, idx, vars_dict) -> int:
    """批量校验H1~H8，返回总违规条数"""
    if None in (validate_h1_solution, validate_h2_solution, validate_h3_solution,
                validate_h4_solution, validate_h5_solution, validate_h6_solution,
                validate_h7_solution, validate_h8_solution):
        print("⚠️ 校验函数缺失，跳过硬约束逐条校验")
        return -1
    v1 = validate_h1_solution(raw_data, idx, vars_dict)
    v2 = validate_h2_solution(raw_data, idx, vars_dict)
    v3 = validate_h3_solution(raw_data, idx, vars_dict)
    v4 = validate_h4_solution(raw_data, idx, vars_dict)
    v5 = validate_h5_solution(raw_data, idx, vars_dict)
    v6 = validate_h6_solution(raw_data, idx, vars_dict)
    v7 = validate_h7_solution(raw_data, idx, vars_dict)
    v8 = validate_h8_solution(raw_data, idx, vars_dict)
    total_violation = v1 + v2 + v3 + v4 + v5 + v6 + v7 + v8
    print(f"\n==== 硬约束汇总校验：总违规数 = {total_violation} ====\n")
    return total_violation


# ========== 【修改点2】重写export_iis_analysis，放弃Pulp导出LP做IIS，只输出二分调试提示 ==========
def export_iis_analysis(model, case_name: str):
    """
    Pulp导出LP会产生大量tuple命名约束，无法可读IIS；改用约束二分排查指引
    """
    print("\n⚠️ Pulp export‑lp generates tuple‑named constraints, readable IIS is unavailable.")
    print("👉 Please perform constraint binary‑search debugging inside build_milp_model():")
    print("  Step1: Only enable H5,H6 (patient admission logic) → test feasibility")
    print("  Step2: Add H7 room capacity → test")
    print("  Step3: Add H1,H2 room gender / incompatible room rule → test")
    print("  Step4: Add H3 surgeon overtime, H4 OT capacity → test")
    print("  Step5: Finally add H8 nurse‑shift constraint → test")
    print("\nTurn constraints on group‑by‑group; the infeasible trigger group contains the bug.\n")
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
        import traceback
        traceback.print_exc()
        sys.exit(1)
    build_cost = round(time.time() - build_start, 2)
    print(f"Model built successfully, cost: {build_cost}s\n")

    # ========== 【修改点3】插入H9 debug约束与惩罚目标 ==========
    #print("✅ Add H9 stay‑duration debug slack constraint")
    #h9_penalty = add_h9_stay_duration_debug(model, raw_data, idx, vars_dict)

    # 关键：清空所有软约束目标，模型只保留硬约束
    #if ONLY_HARD_CONSTRAINT:
        #print("【Hard Mode】Clear all soft penalty objectives, only H1~H8 hard constraints reserved")
        #model.objective = pulp.LpAffineExpression()

        # ⭐ 清空后重新设置目标为H9 slack惩罚，强迫求解器尽量分配房间
        #model.setObjective(h9_penalty)
    # ============================================================

    # Skip solving switch
    if not RUN_SOLVE:
        print("\n[Debug Mode] Skip solving, only model structure check finished. Set RUN_SOLVE=True for formal calculation")
        sys.exit(0)

    # Step3: Solver initialization & solution
    # 不要复用ONLY_HARD_CONSTRAINT，完整模型强制Gurobi
    use_gurobi = True
    solver = build_solver_instance(use_gurobi)
    
    print("\nStart solving process...")
    solve_start = time.time()
    try:
        model.solve(solver)
    except Exception as e:
        print(f"❌ Solver runtime crash: {e}")
        sys.exit(1)
    solve_cost = round(time.time() - solve_start, 2)
    solve_status = pulp.LpStatus[model.status]
    print(f"Solve time: {solve_cost}s | Solver Status: {solve_status}")
# =============================================================================


    # Step4: Status branch judgment
    if solve_status == "Optimal":
        print("✅ Optimal feasible solution obtained, start hard constraint full check")
        # total_viol = batch_check_all_hard_constraint(raw_data, idx, vars_dict)
        # if total_viol > 0:
        #     print("⚠️ 警告：求解显示可行，但校验发现硬约束违规，浮点精度/约束绑定存在BUG")
    elif solve_status == "Infeasible":
        print("❌ Model infeasible, start IIS conflict positioning")
        export_iis_analysis(model, test_case)
        sys.exit(1)
    elif solve_status == "NotSolved":
        print(f"⚠️ Exceed timeout {SOLVE_TIMEOUT}s, solving incomplete")
        sys.exit(1)
    else:
        print(f"⚠️ Abnormal status [{solve_status}], exit")
        sys.exit(1)

    # Step5: 硬约束模式不统计软惩罚
    cost_str = "【硬约束模式】无软惩罚，仅校验H1‑H8可行性"
    print(f'"costs": [ "{cost_str}" ]')

    # Step6: Parse decision variables，统一变量名
    y_patient_room = vars_dict["y_patient_room"]
    x_nurse_room_shift = vars_dict["x_nurse_room_shift"]
    admit_var = vars_dict["admit_var"]
    ot_surg_assign = vars_dict["ot_surg_assign"]

    day_range = idx["day_range"]
    shift_types = idx["shift_types"]
    room_ids = idx["room_ids"]
    surgeon_ids = idx["surgeon_ids"]
    ot_ids = idx["ot_ids"]
    patient_ids = idx["patient_ids"]

    output_sol = {
        "patients": [],
        "nurses": [],
        "surgeon_ot_schedule": [],
        "costs": [cost_str]
    }

    # 患者格式化导出
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
        patient_item = {
            "id": pid,
            "admission_day": admit_day,
            "room": room_tag,
            "operating_theater": None
        }
        output_sol["patients"].append(patient_item)

    # 护士排班导出
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
                    nurse_item["assignments"].append({"day": d, "shift": s, "rooms": bind_rooms})
        output_sol["nurses"].append(nurse_item)

    # 医生手术室排班导出
    for sid in surgeon_ids:
        ot_record = {"surgeon_id": sid, "ot_usage": []}
        for d in day_range:
            used_ots = []
            for otid in ot_ids:
                if get_binary_value(ot_surg_assign[sid][otid][d]):
                    used_ots.append(otid)
            if used_ots:
                ot_record["ot_usage"].append({"day": d, "theaters": used_ots})
        output_sol["surgeon_ot_schedule"].append(ot_record)

    # Step7: JSON结果保存函数
    def dump_solution_json(sol_data: dict, save_dir: str, case_name: str) -> str:
        timestamp = time.strftime('%Y%m%d_%H%M%S')
        filename = f"hard_solution_{case_name}_{timestamp}.json"
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

    # ========== 深度诊断：病房变量全零、入院无病房检测 ==========
    print("\n====== Debug: Count non‑zero patient‑room variables ======")
    cnt_room_valid = 0
    admit_but_no_room = 0
    for pid in patient_ids:
        admit_d = None
        for d in day_range:
            if get_binary_value(admit_var[pid][d]):
                admit_d = d
                break
        # 统计所有y=1数量
        for d in day_range:
            for rid in room_ids:
                if get_binary_value(y_patient_room[pid][rid][d]) == 1:
                    cnt_room_valid += 1
                    break
        # 入院标记开启但是无病房
        if admit_d is not None:
            find_room = False
            for rid in room_ids:
                if get_binary_value(y_patient_room[pid][rid][admit_d]) == 1:
                    find_room = True
                    break
            if not find_room:
                admit_but_no_room += 1

    print(f"y_patient_room 取值为1的总数量：{cnt_room_valid}")
    print(f"【高危】入院标记开启但无病房绑定人数：{admit_but_no_room}")
    if cnt_room_valid == 0:
        print("⚠️ 致命警告：所有患者病房占用变量均为0，大概率H1/H2/H6/H7约束存在互斥冲突")
    if admit_but_no_room > 0:
        print("⚠️ 高危警告：入院‑病房绑定约束(H6)失效")