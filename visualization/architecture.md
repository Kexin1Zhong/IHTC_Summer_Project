# IHTC MILP Project Architecture

```mermaid
%%{init: {'theme':'default'}}%%
flowchart LR
    A["test_all.py<br/>Entry: load dataset, launch model"]
    B["model.py<br/>Create all decision variables"]

    subgraph HardConstraints["Hard Constraints"]
        direction TB
        H1["h1_gender_mix.py<br/>H1 Gender‑mix constraint"]
        H2["h2_incompatible_room.py<br/>H2 Incompatible room assignment"]
        H3["h3_surgeon_overtime.py<br/>H3 Surgeon overtime limit"]
        H4["h4_ot_capacity.py<br/>H4 Operating theatre capacity"]
        H5["h5_patient_admit_count.py<br/>H5 Mandatory / Optional admission"]
        H6["h6_admit_window.py<br/>H6 Admission time window"]
        H7["h7_room_capacity.py<br/>H7 Room occupancy capacity"]
        H8["h8_nurse_room_shift.py<br/>H8 Nurse‑room shift assignment"]
        H9["h9_stay_duration.py<br/>H9 Patient stay duration"]
        H10["h10_admit_surgery_link.py<br/>H10 Admission‑surgery linkage"]
    end

    subgraph SoftConstraints["Soft Constraints / Penalty Terms"]
        direction TB
        S1["s1_age_gap.py<br/>S1 Patient age gap preference"]
        S2["s2_nurse_skill_shortage.py<br/>S2 Nurse skill shortage penalty"]
        S3["s3_nurse_continuity.py<br/>S3 Nurse assignment continuity"]
        S4["s4_max_workload.py<br/>S4 Nurse maximum workload"]
        S5["s5_open_ot.py<br/>S5 Open operating‑theatre penalty"]
        S6["s6_surgeon_transfer.py<br/>S6 Surgeon patient transfer penalty"]
        S7["s7_admission_delay.py<br/>S7 Admission delay penalty"]
        S8["s8_unscheduled_optional.py<br/>S8 Unscheduled optional patient penalty"]
    end

    Obj["Objective Function<br/>Weighted sum of hard‑constraint logic & soft penalty terms"]
    Solver["Gurobi Solver"]
    OutputJson["final_solution_test01.json<br/>MILP solution output"]

    subgraph Visualization["Result Visualization"]
        V["visualize_result.py<br/>Generate HTML report & Gantt PNG"]
    end

    %% flow
    A --> B
    B --> HardConstraints
    B --> SoftConstraints

    HardConstraints --> Obj
    SoftConstraints --> Obj

    Obj --> Solver
    Solver --> OutputJson
    OutputJson --> V