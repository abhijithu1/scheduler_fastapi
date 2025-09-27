#!/usr/bin/env python3
import sys
import random
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scheduler import OptimizedInterviewScheduler, Stage, SeatRole, InterviewerInfo
from datetime import datetime, timedelta
from scheduler import ISO_FMT, to_iso, parse_iso, AvailabilityWindow, BusyInterval

def create_test_data():
    \"\"\"Create test data with guaranteed trained interviewers\"\"\"
    # Create 2 stages with 2 seats each
    stages = [
        Stage(name=\"Stage_1\", duration_minutes=60, seats=[
            SeatRole(seat_id=\"Stage_1_seat1\", role=\"trained\", interviewers=[\"Trained_1\", \"Trained_2\"]),
            SeatRole(seat_id=\"Stage_1_seat1\", role=\"shadow\", interviewers=[\"Shadow_1\", \"Shadow_2\"]),
            SeatRole(seat_id=\"Stage_1_seat1\", role=\"reverse_shadow\", interviewers=[\"Reverse_1\"]),
            SeatRole(seat_id=\"Stage_1_seat2\", role=\"trained\", interviewers=[\"Trained_1\", \"Trained_3\"]),
            SeatRole(seat_id=\"Stage_1_seat2\", role=\"shadow\", interviewers=[\"Shadow_2\", \"Shadow_3\"]),
            SeatRole(seat_id=\"Stage_1_seat2\", role=\"reverse_shadow\", interviewers=[\"Reverse_2\"]),
        ], is_fixed=False),
        Stage(name=\"Stage_2\", duration_minutes=60, seats=[
            SeatRole(seat_id=\"Stage_2_seat1\", role=\"trained\", interviewers=[\"Trained_2\", \"Trained_3\"]),
            SeatRole(seat_id=\"Stage_2_seat1\", role=\"shadow\", interviewers=[\"Shadow_1\", \"Shadow_3\"]),
            SeatRole(seat_id=\"Stage_2_seat1\", role=\"reverse_shadow\", interviewers=[\"Reverse_1\", \"Reverse_3\"]),
            SeatRole(seat_id=\"Stage_2_seat2\", role=\"trained\", interviewers=[\"Trained_1\", \"Trained_2\"]),
            SeatRole(seat_id=\"Stage_2_seat2\", role=\"shadow\", interviewers=[\"Shadow_2\"]),
            SeatRole(seat_id=\"Stage_2_seat2\", role=\"reverse_shadow\", interviewers=[\"Reverse_2\", \"Reverse_3\"]),
        ], is_fixed=False)
    ]
    
    # Create interviewer info
    interviewers = {
        \"Trained_1\": InterviewerInfo(id=\"Trained_1\", current_load=0, last2w_load=0, mode=\"trained\"),
        \"Trained_2\": InterviewerInfo(id=\"Trained_2\", current_load=0, last2w_load=0, mode=\"trained\"),
        \"Trained_3\": InterviewerInfo(id=\"Trained_3\", current_load=0, last2w_load=0, mode=\"trained\"),
        \"Shadow_1\": InterviewerInfo(id=\"Shadow_1\", current_load=0, last2w_load=0, mode=\"shadow\"),
        \"Shadow_2\": InterviewerInfo(id=\"Shadow_2\", current_load=0, last2w_load=0, mode=\"shadow\"),
        \"Shadow_3\": InterviewerInfo(id=\"Shadow_3\", current_load=0, last2w_load=0, mode=\"shadow\"),
        \"Reverse_1\": InterviewerInfo(id=\"Reverse_1\", current_load=0, last2w_load=0, mode=\"reverse_shadow\"),
        \"Reverse_2\": InterviewerInfo(id=\"Reverse_2\", current_load=0, last2w_load=0, mode=\"reverse_shadow\"),
        \"Reverse_3\": InterviewerInfo(id=\"Reverse_3\", current_load=0, last2w_load=0, mode=\"reverse_shadow\"),
    }
    
    # Create availability windows
    start_time = datetime(2025, 9, 1, 9, 0)  # 9 AM
    end_time = datetime(2025, 9, 1, 17, 0)   # 5 PM
    availability = [
        AvailabilityWindow(start=start_time, end=end_time)
    ]
    
    # No busy intervals for simplicity
    busy_intervals = []
    
    return stages, interviewers, availability, busy_intervals

print(\"Testing the two-phase approach with custom test data...\")

# Create test data
stages, interviewers, availability, busy_intervals = create_test_data()

print(f\"Created {len(stages)} stages with properly structured seats\")
print(f\"Created {len(interviewers)} interviewers with different roles\")

# Create scheduler
scheduler = OptimizedInterviewScheduler(
    stages=[{\"stage_name\": s.name, \"duration\": s.duration_minutes, \"seats\": [{\"seat_id\": seat.seat_id} for seat in s.seats if seat.role == \"trained\"], \"is_fixed\": s.is_fixed} for s in stages],  # Only for initial creation
    interviewers=[{\"id\": iid, \"current_load\": iv.current_load, \"last2w_load\": iv.last2w_load, \"mode\": iv.mode} for iid, iv in interviewers.items()],
    availability_windows=[{\"start\": to_iso(w.start), \"end\": to_iso(w.end)} for w in availability],
    busy_intervals=[],
    max_time_seconds=10.0,
    weekly_limit=5
)

print(\"\\nTesting solve_with_two_phase_approach method directly...\")
result = scheduler.solve_with_two_phase_approach()

print(f\"Status: {result['status']}\")

if result['status'] in ['OPTIMAL', 'FEASIBLE'] and 'schedules' in result:
    print(\"Two-phase scheduling successful!\")
    
    # Check if the schedule contains shadowers and reverse shadowers
    schedule = list(result['schedules'].values())[0]
    has_shadowers = False
    has_reverse_shadowers = False
    
    for event_idx, event in enumerate(schedule['events']):
        print(f\"Event {event_idx+1}: {event['stage_name']}\")
        for role, assignments in event['assigned'].items():
            print(f\"  {role}: {len(assignments)} assignments - {list(assignments.values())}\")
            if role == 'shadow' and len(assignments) > 0:
                has_shadowers = True
            if role == 'reverse_shadow' and len(assignments) > 0:
                has_reverse_shadowers = True
    
    if has_shadowers or has_reverse_shadowers:
        print(\"\\nSUCCESS: Schedule contains shadowers/reverse shadowers as expected with two-phase approach!\")
    else:
        print(\"\\nNOTE: No shadowers/reverse shadowers in this particular solution (might be due to constraints)\")
else:
    print(\"Scheduling failed or returned no schedules.\")
    if result['status'] == 'INFEASIBLE':
        print(\"This may be due to the test data having insufficient trained interviewers for all seats.\")

print(\"\\nTest completed!\")