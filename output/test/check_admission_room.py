import sys
import os

# add project root to python path
current_file = os.path.abspath(__file__)
project_root = os.path.abspath(os.path.join(os.path.dirname(current_file), "../../"))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.model import load_instance

data = load_instance("test01")
T = data["days"]
day_range = list(range(T))

for p in data["patients"]:
    pid = p["id"]
    los = p["length_of_stay"]
    can_fit = any( (d + los -1) in day_range for d in day_range )
    if not can_fit and p["mandatory"]:
        print(f"bad mandatory patient {pid}, los={los}, T={T}")