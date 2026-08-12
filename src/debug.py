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
        print("===== 导出LP模型，启动Gurobi-IIS精准分析 =====")
        model.writeLP("model_named.lp")
        gp_model = gp.read("model_named.lp")
        gp_model.optimize()
        if gp_model.Status in (GRB.INFEASIBLE, GRB.INF_OR_UNBD):
            gp_model.computeIIS()
            gp_model.write("conflict_constraints.ilp")
            print("【IIS最小冲突约束清单】")
            for con in gp_model.getConstrs():
                if con.IISConstr:
                    name = con.ConstrName
                    print(f"冲突约束名称：{name}")
                    # 自动归类提示
                    if name.startswith("h"):
                        print(f"  归类：硬约束，查看src/hard_constraints对应脚本")
                    elif name.startswith("s"):
                        print(f"  归类：软约束，不会导致无解，可忽略")