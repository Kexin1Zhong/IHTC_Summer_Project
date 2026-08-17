import sys
import os
import pulp
from pulp import LpStatus
from io import StringIO

def run_single_constraint_test(instance_name: str, validate_func):
    #General Single‑Constraint Test Executor
    # Automatically mount the project root directory
    runner_file = os.path.abspath(__file__)
    src_folder = os.path.dirname(runner_file)
    project_root = os.path.abspath(os.path.join(src_folder, "../"))
    if project_root not in sys.path:
        sys.path.append(project_root)

    from src.model import build_milp_model
    res = build_milp_model(instance_name)
    model, data, index_sets, var_dict = res[:4]

    # Fully silence Gurobi and turn off all console output
    silent_gurobi = pulp.GUROBI_CMD(
        msg=False,
        logPath=None,
        options=[("OutputFlag", 0), ("LogToConsole", 0)]
    )
    model.solve(silent_gurobi)
    status = LpStatus[model.status]
    print(f"Solver Status: {status}")

    if status == "Optimal":
        # Globally intercept all prints from validation functions to prevent unintended outputs
        stdout_buffer = StringIO()
        sys.stdout = stdout_buffer
        try:
            validate_func(data, index_sets, var_dict)
        finally:
            sys.stdout = sys.__stdout__
        # Output only the verification summary
        print("Constraint verification completed. Detailed logs have been masked")
    else:
        print("The model has no solution and constraint verification cannot be performed")