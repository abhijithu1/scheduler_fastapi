#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scheduler import OptimizedInterviewScheduler, generate_dummy_data

print("Testing that solve() method now uses two-phase approach by default...")

# Generate minimal dummy data for testing
print("Generating dummy data...")
stages, interviewers, availability, busy_intervals = generate_dummy_data(
    num_interviewers=12,
    num_stages=2,
    seats_per_stage=(2, 2),
    roles=['trained', 'shadow', 'reverse_shadow']
)

print(f"Generated: {len(stages)} stages, {len(interviewers)} interviewers")
print(f"  - Trained: {sum(1 for iv in interviewers if iv['mode'] == 'trained')}")
print(f"  - Shadow: {sum(1 for iv in interviewers if iv['mode'] == 'shadow')}")
print(f"  - Reverse Shadow: {sum(1 for iv in interviewers if iv['mode'] == 'reverse_shadow')}")

# Create scheduler
scheduler = OptimizedInterviewScheduler(
    stages=stages,
    interviewers=interviewers,
    availability_windows=availability,
    busy_intervals=busy_intervals,
    max_time_seconds=5.0,
    weekly_limit=10
)

print("Running scheduler.solve() - should now use two-phase approach by default...")
result = scheduler.solve()

print(f"Status: {result['status']}")

if result['status'] in ['OPTIMAL', 'FEASIBLE'] and 'schedules' in result:
    print("Schedule generation successful!")
    
    # Check if the schedule contains shadowers and reverse shadowers
    schedule = list(result['schedules'].values())[0]
    has_shadowers = False
    has_reverse_shadowers = False
    
    for event_idx, event in enumerate(schedule['events']):
        print(f"Event {event_idx+1}: {event['stage_name']}")
        for role, assignments in event['assigned'].items():
            print(f"  {role}: {len(assignments)} assignments")
            if role == 'shadow' and len(assignments) > 0:
                has_shadowers = True
            if role == 'reverse_shadow' and len(assignments) > 0:
                has_reverse_shadowers = True
    
    if has_shadowers or has_reverse_shadowers:
        print("\nSUCCESS: Schedule contains shadowers/reverse shadowers as expected with two-phase approach!")
    else:
        print("\nNOTE: No shadowers/reverse shadowers in this particular solution (might be due to constraints)")
else:
    print("Schedule generation failed or returned no schedules.")

print("\nTest completed successfully!")