#========== H8 For each shift, occupied room must be allocated to an on-duty nurse ==========
    # Rule: If room r has patients on day d, every shift s must assign at least one nurse to r
    ## Here is stricter than H8, will change it later
    ## Here indicates the number of nurse must be >= room occupied while h8 says at least 1 
    #for r in room_ids:
        #for d in day_range:
            #room_occupied = pulp.lpSum([y_patient_room[p["id"]][r][d] for p in patients])
            #for s in shift_list:
                # If room occupied, sum of nurse assignments to this room shift >= 1
                #model += pulp.lpSum([x_nurse_room[n][r][d][s] for n in nurse_ids]) >= room_occupied, f"H8_r{r}_d{d}_s{s}"


#mistake reason:
#It incorrectly sets the total assigned nurses per shift to be greater than or equal to the number of patients in the room 
# (nurse_sum >= room_occupied)
# The official rule H8 only requires at least one nurse to be assigned to an occupied room for every shift, 
# rather than requiring the nurse count to match or exceed the patient count.
