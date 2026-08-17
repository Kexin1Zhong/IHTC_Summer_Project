import json
import os

# Current script file path
script_path = os.path.abspath(__file__)
# Trace back two levels upwards to locate the project root directory IHTC_Summer_Project
project_root = os.path.dirname(os.path.dirname(os.path.dirname(script_path)))

data_path = os.path.join(project_root, "data", "ihtc2024_test_dataset", "test01.json")
print(f"looking for data file: {data_path}")

with open(data_path, "r") as f:
    data = json.load(f)

days_total = data["days"]
day_range = list(range(days_total))
print(f"day_range: {day_range}\n")

for p in data["patients"]:
    pid = p["id"]
    mandatory = p["mandatory"]
    rel = p["surgery_release_day"]
    due = p.get("surgery_due_day", None)
    if not mandatory:
        continue

    valid_days = [d for d in day_range if rel <= d <= due]
    if len(valid_days) == 0:
        print(f"❌ Mandatory patient {pid} NO VALID ADMISSION DAY！")
        print(f"    release={rel}, due={due}, day_range={day_range}")
    else:
        print(f"✅ Mandatory patient {pid} valid_days:{valid_days[:5]}...")