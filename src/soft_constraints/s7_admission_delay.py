import pulp

def add_s7_admission_delay_penalty(model: pulp.LpProblem, data: dict, index_sets: dict, var_dict: dict) -> pulp.LpAffineExpression:
    """
    S7 Admission delay Soft Constraint
    Rule: Minimize days between patient surgery release day and actual admission day
    Penalty = delay days (actual_admit_day - release_day) if positive, else 0
    Weight key: patient_delay
    """
    # Unpack index sets
    day_range = index_sets["day_range"]
    patient_ids = index_sets["patient_ids"]

    # Raw data & weight
    patients = data["patients"]
    weight_s7 = data["weights"]["patient_delay"]
    big_m_days = max(day_range) + 10  # Maximum Day Boundary of Big-M

    # Core variable: admit[pid][d] binary flag for patient admission day
    admit = var_dict["admit_var"]

    # Pre-cache each patient's earliest allowed admission day
    patient_release_day = {p["id"]: p["surgery_release_day"] for p in patients}

    # Aux continuous variable: delay penalty per patient
    patient_delay_penalty = pulp.LpVariable.dicts(
        "s7_patient_delay",
        patient_ids,
        lowBound=0,
        cat=pulp.LpContinuous
    )
    total_s7_penalty = 0

    for p in patients:
        pid = p["id"]
        release_d = patient_release_day[pid]
        # Linear expression for actual admission day value: sum(d * admit[pid][d])
        actual_admit_day = pulp.lpSum([d * admit[pid][d] for d in day_range])
        delay_gap = actual_admit_day - release_d

        # Linearize max(0, delay_gap)
        delay_var = patient_delay_penalty[pid]
        model += delay_var >= delay_gap
        model += delay_var <= delay_gap + big_m_days
        model += delay_var <= big_m_days

        total_s7_penalty += weight_s7 * delay_var

    return total_s7_penalty