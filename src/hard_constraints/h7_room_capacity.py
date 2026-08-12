import sys
from pathlib import Path
root_path = Path(__file__).parent.parent.parent
sys.path.append(str(root_path))
import pulp

# ===================== H1 =====================
def add_h1_constraint(model, data, index_sets, var_dict):
    patients = data["patients"]
    rooms = data["rooms"]
    day_range = index_sets["day_range"]
    y_patient_room = var_dict["y_patient_room"]
    for r in rooms:
        rid = r["id"]
        cap = r["capacity"]
        for d in day_range:
            group_A = [p for p in patients if p["gender"] == "A"]
            group_B = [p for p in patients if p["gender"] == "B"]
            sum_A = pulp.lpSum([y_patient_room[p["id"]][rid][d] for p in group_A])
            sum_B = pulp.lpSum([y_patient_room[p["id"]][rid][d] for p in group_B])
            has_A = pulp.LpVariable(f"hasA_room{rid}_day{d}", cat=pulp.LpBinary)
            has_B = pulp.LpVariable(f"hasB_room{rid}_day{d}", cat=pulp.LpBinary)
            model += sum_A <= cap * has_A, f"H1_auxA_room{rid}_day{d}"
            model += sum_B <= cap * has_B, f"H1_auxB_room{rid}_day{d}"
            model += has_A + has_B <= 1, f"H1_no_gender_mix_room{rid}_day{d}"

def validate_h1_solution(sol_data, index_sets, var_dict):
    patients = sol_data["patients"]
    rooms = sol_data["rooms"]
    day_range = index_sets["day_range"]
    y = var_dict["y_patient_room"]
    h1_violation_count = 0
    for room in rooms:
        rid = room["id"]
        for d in day_range:
            sumA = 0.0
            sumB = 0.0
            for p in patients:
                val = pulp.value(y[p["id"]][rid][d])
                if p["gender"] == "A":
                    sumA += val
                else:
                    sumB += val
            if sumA > 1e-6 and sumB > 1e-6:
                h1_violation_count += 1
                print(f"H1 VIOLATION: Room {rid}, Day {d} mixed A/B patients")
    if h1_violation_count == 0:
        print("✅ H1 Test Passed: No mixed gender rooms")
    else:
        print(f"❌ H1 Test Failed, total {h1_violation_count} mixed gender violations")
    return h1_violation_count

# ===================== H2 =====================
def add_h2_constraint(model, data, index_sets, var_dict):
    patients = data["patients"]
    day_range = index_sets["day_range"]
    y_patient_room = var_dict["y_patient_room"]
    for p in patients:
        pid = p["id"]
        black_room_ids = p["incompatible_room_ids"]
        for r in black_room_ids:
            for d in day_range:
                model += y_patient_room[pid][r][d] == 0, f"H2_p{pid}_incompatible_room{r}_d{d}"

def validate_h2_solution(sol_data, index_sets, var_dict):
    all_patients = sol_data["patients"]
    y = var_dict["y_patient_room"]
    days = index_sets["day_range"]
    h2_violation_count = 0
    for p in all_patients:
        pid = p["id"]
        forbidden_rooms = p["incompatible_room_ids"]
        for rid in forbidden_rooms:
            for d in days:
                occupy_val = pulp.value(y[pid][rid][d])
                if occupy_val > 1e-6:
                    h2_violation_count += 1
                    print(f"H2 VIOLATION DETECTED: Patient {pid} incompatible room {rid}, Day {d} | Occupied = {occupy_val}")
    if h2_violation_count == 0:
        print("✅ H2 Test Passed: No patient assigned to incompatible rooms")
    else:
        print(f"❌ H2 Test Failed: Total {h2_violation_count} incompatible room assignments found")
    return h2_violation_count

# ===================== H7 =====================
def add_h7_constraint(model, data, index_sets, var_dict):
    patients = data["patients"]
    rooms = data["rooms"]
    day_range = index_sets["day_range"]
    y_patient_room = var_dict["y_patient_room"]
    for r in rooms:
        rid = r["id"]
        cap = r["capacity"]
        for d in day_range:
            model += pulp.lpSum([y_patient_room[p["id"]][rid][d] for p in patients]) <= cap, f"H7_room{rid}_cap_d{d}"

def validate_h7_solution(sol_data, index_sets, var_dict):
    all_rooms = sol_data["rooms"]
    all_patients = sol_data["patients"]
    y = var_dict["y_patient_room"]
    days = index_sets["day_range"]
    h7_violation_count = 0
    for room in all_rooms:
        rid = room["id"]
        cap = room["capacity"]
        for d in days:
            total_occupy = 0.0
            for p in all_patients:
                pid = p["id"]
                val = pulp.value(y[pid][rid][d])
                total_occupy += val
            if total_occupy - cap > 1e-6:
                h7_violation_count += 1
                print(f"H7 VIOLATION DETECTED: Room {rid}, Day {d} | Capacity={cap}, Actual occupants={total_occupy:.2f}")
    if h7_violation_count == 0:
        print("✅ H7 Test Passed: All rooms satisfy daily capacity limit")
    else:
        print(f"❌ H7 Test Failed: Total {h7_violation_count} room capacity over-limit violations")
    return h7_violation_count

# ===================== 迷你测试数据 =====================
mini_data = {
    "patients": [
        {"id": "p1", "gender": "A", "incompatible_room_ids": ["r1"]},
        {"id": "p2", "gender": "B", "incompatible_room_ids": ["r2"]}
    ],
    "rooms": [
        {"id": "r1", "capacity": 1},
        {"id": "r2", "capacity": 1}
    ]
}
index_sets = {
    "day_range": [1]
}

# ===================== 三维变量初始化 =====================
model = pulp.LpProblem("mini_case", pulp.LpMinimize)
var_dict = {}
y_patient_room = {}
for p in mini_data["patients"]:
    pid = p["id"]
    y_patient_room[pid] = {}
    for r in mini_data["rooms"]:
        rid = r["id"]
        y_patient_room[pid][rid] = {}
        for d in index_sets["day_range"]:
            y_patient_room[pid][rid][d] = pulp.LpVariable(f"y_{pid}_{rid}_{d}", cat=pulp.LpBinary)
var_dict["y_patient_room"] = y_patient_room

# ===================== 加载全部约束 =====================
add_h1_constraint(model, mini_data, index_sets, var_dict)
add_h2_constraint(model, mini_data, index_sets, var_dict)
add_h7_constraint(model, mini_data, index_sets, var_dict)

model += 0

# ===================== 求解与校验/冲突定位 =====================
model.solve(pulp.GUROBI_CMD(msg=1))
if model.status == pulp.LpStatusOptimal:
    validate_h1_solution(mini_data, index_sets, var_dict)
    validate_h2_solution(mini_data, index_sets, var_dict)
    validate_h7_solution(mini_data, index_sets, var_dict)
elif model.status == pulp.LpStatusInfeasible:
    print("模型无解，启动IIS冲突定位")
    model.writeLP("mini_h1h2h7.lp")
    import gurobipy as gp
    gp_model = gp.read("mini_h1h2h7.lp")
    gp_model.optimize()
    if gp_model.Status in (gp.GRB.INFEASIBLE, gp.GRB.INF_OR_UNBD):
        gp_model.computeIIS()
        gp_model.write("conflict.ilp")
        print("====冲突约束清单====")
        for con in gp_model.getConstrs():
            if con.IISConstr:
                print(con.ConstrName)