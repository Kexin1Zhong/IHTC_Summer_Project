import sys
import os
import pulp
from pulp import LpStatus

def get_project_root(file_path: str) -> str:
    """
    Unified project root path resolver for all test scripts
    """
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
    if project_root not in sys.path:
        sys.path.append(project_root)
    return project_root

def run_single_constraint_test(instance_name: str, validate_func):
    """
    General single hard constraint test executor
    Shared test logic, only written once, reused by all test scripts
    """
    from model import build_milp_model

    # Build full MILP model
    model, data, index_sets, var_dict = build_milp_model(instance_name)
    # Unified solver setting
    model.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=120))
    solver_status = LpStatus[model.status]
    print(f"\nSolver Global Status: {solver_status}")

    if solver_status == "Optimal":
        validate_func(data, index_sets, var_dict)
    else:
        print(f"WARNING: Instance {instance_name} has no feasible solution, cannot run constraint validation.")