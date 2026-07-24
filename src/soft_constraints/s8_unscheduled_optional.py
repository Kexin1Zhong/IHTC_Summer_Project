import pulp

def add_s8_unscheduled_optional_penalty(model: pulp.LpProblem, data: dict, index_sets: dict, var_dict: dict) -> pulp.LpAffineExpression:
    """
    S8 Unscheduled optional patients Soft Constraint
    Rule: Penalise optional patients who are not admitted on any day.
    Weight key: unscheduled_optional
    """
    patient_ids = index_sets["patient_ids"]
    day_range = index_sets["day_range"]
    patients = data["patients"]
    weight_s8 = data["weights"]["unscheduled_optional"]

    admit = var_dict["admit_var"]
    total_s8_penalty = 0

    for p in patients:
        pid = p["id"]
        # Only process optional patients mandatory=false
        if p["mandatory"]:
            continue
        

# sum_admit = 1 means admission arranged successfully; 
# =0 means no admission arranged throughout the process

        sum_admit = pulp.lpSum([admit[pid][d] for d in day_range])
        # binary indicator: unscheduled = 1 当且仅当 sum_admit == 0
        unscheduled = pulp.LpVariable(f"s8_unsched_{pid}", cat=pulp.LpBinary)
        
# Linear constraint: sum_admit >= 1 - unscheduled
        # If unscheduled=1 → sum_admit >=0 (no constraint)
        # If unscheduled=0 → sum_admit >=1 → admission must be scheduled
        model += sum_admit >= 1 - unscheduled, f"S8_p{pid}_unscheduled_flag"

        total_s8_penalty += weight_s8 * unscheduled

    return total_s8_penalty