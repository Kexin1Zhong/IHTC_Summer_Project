import sys
import os

# Mount project root to resolve src module import
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

import pulp
from pulp import LpStatus
from src.runner import run_single_constraint_test
from src.hard_constraints.h5_patient_admit_count import validate_h5_solution

if __name__ == "__main__":
    run_single_constraint_test("test01", validate_h5_solution)