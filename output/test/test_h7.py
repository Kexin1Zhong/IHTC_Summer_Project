import sys
import os

# Mount the project root directory to resolve module import warnings
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

import pulp
from pulp import LpStatus
from src.runner import run_single_constraint_test
# Import H7 exclusive verification function
from src.hard_constraints.h7_room_capacity import validate_h7_solution

if __name__ == "__main__":
    run_single_constraint_test("test01", validate_h7_solution)