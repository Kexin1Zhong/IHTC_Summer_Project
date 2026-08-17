import sys
import os
import pulp
import gurobipy as gp
from gurobipy import GRB

current_file = os.path.abspath(__file__)
src_dir = os.path.dirname(current_file)
root_dir = os.path.dirname(src_dir)
sys.path.append(root_dir)
from src.model import build_milp_model

if __name__ == "__main__":
    model, data, index_sets, var_dict, s1_pen, s2_pen, s3_pen, s4_pen, s5_pen, s6_pen, s7_pen, s8_pen = build_milp_model("test01")
    solver = pulp.GUROBI_CMD(msg=1, timeLimit=180)
    model.solve(solver)

    if model.status == pulp.LpStatusInfeasible:
        print("===== Export LP model and start Gurobi‑IIS precise analysis =====")
        model.writeLP("model_named.lp")
        gp_model = gp.read("model_named.lp")
        gp_model.optimize()
        if gp_model.Status in (GRB.INFEASIBLE, GRB.INF_OR_UNBD):
            gp_model.computeIIS()
            gp_model.write("conflict_constraints.ilp")
            print("[IIS Minimum Conflict Constraint List]")
            for con in gp_model.getConstrs():
                if con.IISConstr:
                    name = con.ConstrName
                    print(f"Conflict constraint name: {name}")
                    # Auto‑categorization Prompt
                    if name.startswith("h"):
                        print(f" Classification: Hard Constraints, check the scripts corresponding to src/hard_constraints")
                    elif name.startswith("s"):
                        print(f"  Category: soft constraint, will not lead to no‑solution, can be ignored")