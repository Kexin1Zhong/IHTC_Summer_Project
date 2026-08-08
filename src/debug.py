import sys
import os
import pulp
import gurobipy as gp
from gurobipy import GRB

# 自动添加项目根目录，解决src包导入异常
current_file = os.path.abspath(__file__)
src_dir = os.path.dirname(current_file)
root_dir = os.path.dirname(src_dir)
sys.path.append(root_dir)

from src.model import build_milp_model

if __name__ == "__main__":
    # 严格解包12个返回值，第一个为PuLP模型对象
    model, data, index_sets, var_dict, s1_pen, s2_pen, s3_pen, s4_pen, s5_pen, s6_pen, s7_pen, s8_pen = build_milp_model("test01")

    # 调用Gurobi求解器
    model.solve(pulp.GUROBI_CMD())

    # 状态判断
    if model.status == pulp.LpStatusInfeasible:
        print("===== Start identifying conflicting hard constraints via IIS =====")
        # 导出模型文件，用原生Gurobi做IIS冲突定位
        model.writeLP("model_export.lp")
        g_model = gp.read("model_export.lp")
        g_model.optimize()
        if g_model.Status == GRB.INFEASIBLE:
            g_model.computeIIS()
            g_model.write("infeasible_constraint.ilp")
            sense_map = {GRB.LESS_EQUAL: "<=", GRB.GREATER_EQUAL: ">=", GRB.EQUAL: "=="}
            for con in g_model.getConstrs():
                if con.IISConstr:
                    expr = con.getExpr()
                    sense = sense_map[con.Sense]
                    print(f"【Conflicting Constraint】Name: {con.ConstrName}")
                    print(f"Expression: {expr} {sense} {con.RHS}\n")
    else:
        print("Feasible solution exists, IIS diagnosis is not required")
        print(f"Optimal Objective Value: {model.objective.value()}")