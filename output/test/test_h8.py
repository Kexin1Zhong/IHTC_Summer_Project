import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

import pulp
from pulp import LpStatus
from src.runner import run_single_constraint_test
# Import H8 exclusive verification function
from src.hard_constraints.h8_nurse_room_shift import validate_h8_solution

if __name__ == "__main__":
    # Input test case test01 + H8 check function
    run_single_constraint_test("test01", validate_h8_solution)