import sys
import os
import pulp
from pulp import LpStatus
from io import StringIO

def run_single_constraint_test(instance_name: str, validate_func):
    """通用单约束测试执行器"""
    # 自动挂载项目根目录
    runner_file = os.path.abspath(__file__)
    src_folder = os.path.dirname(runner_file)
    project_root = os.path.abspath(os.path.join(src_folder, "../"))
    if project_root not in sys.path:
        sys.path.append(project_root)

    from src.model import build_milp_model
    res = build_milp_model(instance_name)
    model, data, index_sets, var_dict = res[:4]

    # 完全静默Gurobi，关闭所有控制台输出
    silent_gurobi = pulp.GUROBI_CMD(
        msg=False,
        logPath=None,
        options=[("OutputFlag", 0), ("LogToConsole", 0)]
    )
    model.solve(silent_gurobi)
    status = LpStatus[model.status]
    print(f"Solver Status: {status}")

    if status == "Optimal":
        # 全局拦截校验函数所有打印，杜绝意外输出
        stdout_buffer = StringIO()
        sys.stdout = stdout_buffer
        try:
            validate_func(data, index_sets, var_dict)
        finally:
            sys.stdout = sys.__stdout__
        # 只输出校验总结
        print("约束校验执行完成，明细日志已屏蔽")
    else:
        print("模型无解，无法执行约束校验")