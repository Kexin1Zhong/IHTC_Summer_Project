import sys
import os
# Add the project root directory to the Python module search path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

import pulp
from pulp import LpStatus
from src.model import build_milp_model
from src.hard_constraints.h7_room_capacity import validate_h7_solution

if __name__ == "__main__":
    # Build the complete model with the filename test01 (Correct)
    model, data, idx, vars_dict = build_milp_model("test01")
    #Solution: Disable redundant logs
    model.solve(pulp.PULP_CBC_CMD(msg=0, timeLimit=120))
    status = LpStatus[model.status]
    print(f"Solver Status: {status}")

    if status == "Optimal":
        ## Call the H7 check function separately
        violation_count = validate_h7_solution(data, idx, vars_dict)
    else:
        print("No solution from the model; H7 cannot be verified.")