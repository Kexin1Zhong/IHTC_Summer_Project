# 自动挂载项目根目录，彻底解决 No module named 'src'
import sys
import os

current_file = os.path.abspath(__file__)
# 当前文件路径：src/validator/hard_validator.py，向上两层回到项目根目录
project_root = os.path.abspath(os.path.join(os.path.dirname(current_file), "../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

import pulp
# 导入所有硬约束校验函数
from src.hard_constraints.h1_gender_mix import validate_h1_solution
from src.hard_constraints.h2_incompatible_room import validate_h2_solution
from src.hard_constraints.h3_surgeon_overtime import validate_h3_solution
from src.hard_constraints.h4_ot_capacity import validate_h4_solution
from src.hard_constraints.h5_patient_admit_count import validate_h5_solution
from src.hard_constraints.h6_admit_window import validate_h6_solution
from src.hard_constraints.h7_room_capacity import validate_h7_solution
from src.hard_constraints.h8_nurse_room_shift import validate_h8_solution


def full_all_hard_validation(sol_data, index_sets, var_dict):
    """
    One-click batch validation for all H1-H8 hard constraints
    :param sol_data: Original instance json data
    :param index_sets: Index set dictionary from model
    :param var_dict: Solved MILP variable values
    :return: report(dict: Hx -> violation count), total_violations(int)
    """
    violation_report = {}
    violation_report["H1"] = validate_h1_solution(sol_data, index_sets, var_dict)
    violation_report["H2"] = validate_h2_solution(sol_data, index_sets, var_dict)
    violation_report["H3"] = validate_h3_solution(sol_data, index_sets, var_dict)
    violation_report["H4"] = validate_h4_solution(sol_data, index_sets, var_dict)
    violation_report["H5"] = validate_h5_solution(sol_data, index_sets, var_dict)
    violation_report["H6"] = validate_h6_solution(sol_data, index_sets, var_dict)
    violation_report["H7"] = validate_h7_solution(sol_data, index_sets, var_dict)
    violation_report["H8"] = validate_h8_solution(sol_data, index_sets, var_dict)

    total_violations = sum(violation_report.values())

    print("\n==================== FULL HARD CONSTRAINT VALIDATION REPORT ====================")
    for rule_name, count in violation_report.items():
        if count == 0:
            print(f"{rule_name}: ✅ PASSED | 0 violations")
        else:
            print(f"{rule_name}: ❌ FAILED | {count} violation(s)")
    print(f"==================================================================================")
    print(f"Total hard constraint violations across all rules: {total_violations}")
    print("==================================================================================\n")

    return violation_report, total_violations


if __name__ == "__main__":
    # 独立运行测试入口：加载test01算例、求解、全量校验
    from src.model import build_milp_model
    model, data, index_sets, var_dict = build_milp_model("test01")
    # 打开求解器日志，方便排查无解/卡顿
    model.solve(pulp.PULP_CBC_CMD(msg=1, timeLimit=120))
    solver_status = pulp.LpStatus[model.status]
    print(f"\nSolver finished, Case: test01 | Status: {solver_status}")
    if solver_status == "Optimal":
        full_all_hard_validation(data, index_sets, var_dict)
    else:
        print(f"WARNING: test01 has no feasible solution, skip validation!")