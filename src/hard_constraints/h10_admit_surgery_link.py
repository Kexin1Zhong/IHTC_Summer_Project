import pulp

def add_h10_constraint(model, data, index_sets, var_dict):
    """
    H10 Hard Link Constraint
    If patient p is admitted on day d (admit_var[p][d]==1),
    then p must receive surgery on exactly day d, performed by p's own surgeon in some OT.
    """
    patients = data["patients"]
    day_range = index_sets["day_range"]
    surgeon_ids = index_sets["surgeon_ids"]
    ot_ids = index_sets["ot_ids"]

    admit_var = var_dict["admit_var"]
    patient_surgery_var = var_dict["patient_surgery_var"]
    ot_surg_assign = var_dict["ot_surg_assign"]

    for p in patients:
        pid = p["id"]
        p_surgeon = p["surgeon_id"]  # Primary Surgeon Bound to the Patient
        for d in day_range:
            # ========= H10‑1: Admission ⇒ Surgery Must Be Performed on the Same Day, and Only the Patient’s Own Surgeon Can Be Used =========
            model += (
                pulp.lpSum([
                    patient_surgery_var[pid][p_surgeon][ot][d]
                    for ot in ot_ids
                ]) >= admit_var[pid][d],
                f"H10_admit_implies_surgery_p{pid}_d{d}"
            )

            # ========= H10‑2: If surgery occurs, activate ot_surg_assign (for use by H3/H4) =========
            for ot in ot_ids:
                model += (
                    ot_surg_assign[p_surgeon][ot][d]
                    >= patient_surgery_var[pid][p_surgeon][ot][d],
                    f"H10_trigger_otsurg_p{pid}_ot{ot}_d{d}"
                )

            # ========= H10‑3: Maximum one surgery per patient per day =========
            model += (
                pulp.lpSum([
                    patient_surgery_var[pid][sur][ot][d]
                    for sur in surgeon_ids
                    for ot in ot_ids
                ]) <= 1,
                f"H10_max_one_op_p{pid}_d{d}"
            )