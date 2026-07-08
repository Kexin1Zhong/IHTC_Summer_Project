import sys
import os
import pulp
from pulp import LpStatus

def run_single_constraint_test(instance_name: str, validate_func):
    """通用单约束测试执行器"""
    # 自动挂载项目根目录
    runner_file = os.path.abspath(__file__)
    src_folder = os.path.dirname(runner_file)
    project_root = os.path.abspath(os.path.join(src_folder, "../"))
    if project_root not in sys.path:
        sys.path.append(project_root)
    
    # 正确完整导入路径，不能简写 from model
    from src.model import build_milp_model

    # 构建模型并求解
    model, data, index_sets, var_dict = build_milp_model(instance_name)
    model.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=120))
    status = LpStatus[model.status]
    print(f"Solver Status: {status}")

    if status == "Optimal":
        validate_func(data, index_sets, var_dict)
    else:
        print("模型无解，无法执行约束校验")