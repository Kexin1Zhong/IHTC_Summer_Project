# -*- coding: utf-8 -*-
import json
import os
import matplotlib.pyplot as plt
import pandas as pd


def load_instance_meta(json_path: str):
    #Read the original dataset and obtain the patient's length_of_stay information
    folder = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/ihtc2024_test_dataset"))
    instance_meta_path = os.path.join(folder, "test01.json")
    with open(instance_meta_path, "r", encoding="utf-8") as f:
        return json.load(f)


def visualize_solution(result_json_path: str):
    # Read, solve and output
    with open(result_json_path, "r", encoding="utf-8") as f:
        sol = json.load(f)

    instance_name = "test01"
    meta_data = load_instance_meta(result_json_path)
    raw_patients = meta_data["patients"]

    # pid -> length_of_stay
    los_map = {p["id"]: p["length_of_stay"] for p in meta_data["patients"]}

    output_prefix = os.path.join(os.path.dirname(result_json_path), f"{instance_name}")

    # ========== 1. Patient Gantt Chart In‑hospital  ==========
    plt.rcParams["font.size"] = 9
    fig, ax = plt.subplots(figsize=(14, len(sol["patients"])*0.35 + 2))
    y_ticks_labels = []
    y_pos = 0

    for p in sol["patients"]:
        pid = p["id"]
        admit_day = p.get("admission_day")
        room_id = p.get("room", "-")
        y_ticks_labels.append(f"{pid} | room:{room_id}")
        if admit_day is not None:
            los = los_map[pid]
            ax.barh(y=y_pos, width=los, left=admit_day, height=0.6, color="#4472C4", alpha=0.75)
        y_pos += 1

    ax.set_yticks(list(range(y_pos)))
    ax.set_yticklabels(y_ticks_labels)
    ax.set_xlabel("Simulation Day")
    ax.set_title(f"Patient Stay Gantt | {instance_name}")
    ax.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{output_prefix}_patient_gantt.png", dpi=150)
    plt.close()

    # ========== 2. Operating Theatre Gantt  ==========
    fig2, ax2 = plt.subplots(figsize=(13, 3.5))
    ot_ids = ["t0", "t1"]
    ot_y = {ot: idx for idx, ot in enumerate(ot_ids)}

    for entry in sol["surgeon_ot_schedule"]:
        for usage in entry.get("ot_usage", []):
            day = usage["day"]
            for ot in usage["theaters"]:
                if ot in ot_y:
                    ax2.barh(y=ot_y[ot], width=1, left=day, height=0.55, color="#ED7D31", alpha=0.8)

    ax2.set_yticks(list(range(len(ot_ids))))
    ax2.set_yticklabels(ot_ids)
    ax2.set_xlabel("Simulation Day")
    ax2.set_title("Operating Theatre Usage Gantt")
    ax2.grid(axis="x", alpha=0.3)
    plt.tight_layout()
    plt.savefig(f"{output_prefix}_ot_gantt.png", dpi=150)
    plt.close()


        # ========== 3. Static HTML Report  ==========
    html_lines = []
    html_lines.append("<html lang='en'><head><meta charset='utf-8'>")
    html_lines.append("""
    <style>
    *{font-family: -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; font-size:14px;}
    body{max-width:1400px;margin:20px auto;padding:0 20px;}
    h1{font-size:22px;color:#222;}
    h2{font-size:18px;color:#333;margin-top:24px;}
    table{border-collapse:collapse;width:100%;margin:12px 0;}
    th,td{border:1px solid #bbbbbb;padding:9px 12px;text-align:left;}
    th{background:#2b5797;color:#ffffff;font-weight:bold;}
    tr:nth-child(even){background:#f6f8fb;}
    /* 异常告警行 */
    tr[style*="background:#ffdddd"]{background:#ffdddd !important;}
    </style>
    """)
    html_lines.append(f"<title>IHTC Solution Report {instance_name}</title></head><body style='margin:16px;'>")

    html_lines.append(f"<h1>Solution Report: {instance_name}</h1>")
    html_lines.append(f"<h3>Total objective cost: {sol.get('costs', [0])[0]}</h3>")

    html_lines.append("<h2>Patient Schedule</h2>")
    html_lines.append("<table><tr><th>PatientID</th><th>Mandatory</th><th>AdmitDay</th><th>Room</th><th>OperatingTheater</th></tr>")

    # sol["patients"] solution output; raw_patients raw input data["patients"]
    for sol_p, raw_p in zip(sol["patients"], raw_patients):
        mandatory_val = raw_p.get("mandatory")
        # Add emoji markers
        if mandatory_val:
            mandatory_text = "🔴 True"
        else:
            mandatory_text = "⚪ False"
        admit = sol_p.get("admission_day")

        # Alert: mandatory=True but not admitted to hospital, entire row in light red
        if mandatory_val is True and admit is None:
            tr_style = 'style="background:#ffdddd;"'
        else:
            tr_style = ""

        html_lines.append(
            f"<tr {tr_style}><td>{sol_p.get('id')}</td><td>{mandatory_text}</td><td>{admit}</td>"
            f"<td>{sol_p.get('room')}</td><td>{sol_p.get('operating_theater')}</td></tr>"
        )

    html_lines.append("</table>")

    html_lines.append("<h2>Surgeon‑OT Schedule</h2>")
    html_lines.append("<table><tr><th>Surgeon</th><th>Day</th><th>Used OT</th></tr>")
    for entry in sol["surgeon_ot_schedule"]:
        s_id = entry.get("surgeon_id")
        for u in entry.get("ot_usage", []):
            html_lines.append(f"<tr><td>{s_id}</td><td>{u.get('day')}</td><td>{', '.join(u.get('theaters',[]))}</td></tr>")
    html_lines.append("</table>")

    html_lines.append("<hr/><p>Generated by visualize_result.py</p>")
    html_lines.append("</body></html>")

    with open(f"{output_prefix}_report.html", "w", encoding="utf-8") as f:
        f.write("\n".join(html_lines))


if __name__ == "__main__":
    # Pass in the JSON path of your solution result here
    res_json = "/Users/mac/Desktop/IHTC_Summer_Project/output/test/final_solution_test01.json"
    visualize_solution(res_json)