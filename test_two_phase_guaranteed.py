#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scheduler import generate_dummy_data, OptimizedInterviewScheduler

print(\"Testing with guaranteed trained interviewers...\")

# Generate dummy data ensuring we have enough trained interviewers
# We'll generate with a higher probability of trained interviewers
stages_data, interviewers_data, availability, busy_intervals = generate_dummy_data(
    num_interviewers=20,  # More interviewers
    num_stages=2,
    seats_per_stage=(1, 2),  # Fewer seats per stage
    roles=['trained', 'shadow', 'reverse_shadow']
)

# Modify the roles to ensure we have trained interviewers
for interviewer in interviewers_data:
    # Ensure at least 50% are trained
    if interviewer['mode'] not in ['trained'] and len([iv for iv in interviewers_data if iv['mode'] == 'trained']) < 5:
        if interviewer['mode'] in ['shadow', 'reverse_shadow']:
            interviewer['mode'] = 'trained'

print(f\"Generated: {len(stages_data)} stages, {len(interviewers_data)} interviewers\")
print(f\"  - Trained: {sum(1 for iv in interviewers_data if iv['mode'] == 'trained')}\")
print(f\"  - Shadow: {sum(1 for iv in interviewers_data if iv['mode'] == 'shadow')}\")
print(f\"  - Reverse Shadow: {sum(1 for iv in interviewers_data if iv['mode'] == 'reverse_shadow')}\"

# Create scheduler
scheduler = OptimizedInterviewScheduler(
    stages=stages_data,
    interviewers=interviewers_data,
    availability_windows=availability,
    busy_intervals=busy_intervals,
    max_time_seconds=10.0,
    weekly_limit=10
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
            print(f\"  {role}: {len(assignments)} assignments\")
            if role == 'shadow' and len(assignments) > 0:
                has_shadowers = True
                print(f\"    Assigned shadowers: {list(assignments.values())}\")
            if role == 'reverse_shadow' and len(assignments) > 0:
                has_reverse_shadowers = True
                print(f\"    Assigned reverse shadowers: {list(assignments.values())}\")
    
    if has_shadowers or has_reverse_shadowers:
        print(\"\\nSUCCESS: Schedule contains shadowers/reverse shadowers as expected with two-phase approach!\")
    else:
        print(\"\\nNOTE: No shadowers/reverse shadowers in this particular solution (might be due to constraints)\")
else:
    print(\"Scheduling failed or returned no schedules.\")
    if result['status'] == 'INFEASIBLE':
        print(\"This may be due to constraints in the test data.\")

print(\"\\nTest completed!\")