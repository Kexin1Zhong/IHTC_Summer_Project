import sys
import os
# Get the absolute path of the current test file
current_test_file = os.path.abspath(__file__)
# Go up two levels of directories: output/test → Root directory of the IHTC_Summer_Project
project_root = os.path.abspath(os.path.join(os.path.dirname(current_test_file), "../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.model import build_milp_model
import pulp

if __name__ == "__main__":
    # Load test01 instance
    model, raw_data, idx, vars = build_milp_model("test01")
    print("Model built successfully! Hard + S1/S2/S3 soft constraints loaded.")
    print(f"Total variables count: {model.numVariables()}")
    print(f"Total constraints count: {model.numConstraints()}")

    # Solve with CBC, mute redundant log
    model.solve(pulp.PULP_CBC_CMD(msg=0))
    print(f"Solver Status: {pulp.LpStatus[model.status]}")
    print(f"Global minimal total soft penalty: {pulp.value(model.objective)}")