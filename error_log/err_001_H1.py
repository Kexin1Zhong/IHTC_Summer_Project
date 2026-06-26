# ========== H1: No gender mix - Patients of different genders may not share a room on any day ==========
# Rule: For any room r, day d, all patients staying in r on d must have identical gender
#for r in room_ids:
    #for d in day_range:
        # Split patient groups by gender
        #A_patients = [p for p in patients if p["gender"] == "A"]
        #B_patients = [p for p in patients if p["gender"] == "B"]
        # Cannot have both male and female patients in same room same day
        #model += pulp.lpSum([y_patient_room[p["id"]][r][d] for p in male_patients]) + \
                 #pulp.lpSum([y_patient_room[p["id"]][r][d] for p in female_patients]) <= 1, f"H1_room{r}_day{d}"
        

#mistake_reason:
# This constraint incorrectly restricts the total number of patients in one room per day to at most 1. 
# It fails to support multi-capacity rooms: 
# if a room’s capacity ≥ 2 and two patients of gender A are assigned (no gender B patients), 
# the sum of male and female assignments equals 2, 
# violating the <=1 limit and causing an infeasible model, 
# even though the original gender-separation rule is satisfied. 
# The constraint only intends to ban mixed genders, not limit total occupancy.