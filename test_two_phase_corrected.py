#!/usr/bin/env python3
\"\"\"
Test script for two-phase scheduling implementation
\"\"\"
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scheduler import generate_dummy_data, OptimizedInterviewScheduler

def test_two_phase_scheduling():
    print(\"Starting two-phase scheduling test...\")
    
    # Generate minimal dummy data for fast testing
    print(\"Generating minimal dummy data...\")
    stages, interviewers, availability, busy_intervals = generate_dummy_data(
        num_interviewers=10,  # Very small dataset
        num_stages=2,
        seats_per_stage=(1, 2),  # Only 1-2 seats per stage
        roles=[\"trained\", \"shadow\", \"reverse_shadow\"]
    )
    
    print(f\"Generated: {len(stages)} stages, {len(interviewers)} interviewers\")
    
    # Count interviewers by role
    trained_count = sum(1 for iv in interviewers if iv[\"mode\"] == \"trained\")
    shadow_count = sum(1 for iv in interviewers if iv[\"mode\"] == \"shadow\")
    reverse_shadow_count = sum(1 for iv in interviewers if iv[\"mode\"] == \"reverse_shadow\")
    
    print(f\"  - Trained: {trained_count}, Shadow: {shadow_count}, Reverse Shadow: {reverse_shadow_count}\")
    
    # Create scheduler with minimal constraints
    print(\"Creating scheduler...\")
    scheduler = OptimizedInterviewScheduler(
        stages=stages,
        interviewers=interviewers,
        availability_windows=availability,
        busy_intervals=busy_intervals,
        max_time_seconds=10.0,  # Shorter time limit for testing
        weekly_limit=10  # Higher limit to make it easier to find solutions
    )
    print(\"Scheduler created successfully\")
    
    # Test regular solve method
    print(\"\\nTesting regular solve method...\")
    try:
        result1 = scheduler.solve()
        print(f\"Regular solve result status: {result1['status']}\")
    except Exception as e:
        print(f\"Regular solve failed with error: {e}\")
        import traceback
        traceback.print_exc()
        return False
    
    # Test two-phase solve method
    print(\"\\nTesting two-phase solve method...\")
    try:
        result2 = scheduler.solve_with_two_phase_approach()
        print(f\"Two-phase solve result status: {result2['status']}\")
        
        if result2['status'] in ['OPTIMAL', 'FEASIBLE']:
            print(\"Two-phase scheduling successful!\")
            
            if 'schedules' in result2 and result2['schedules']:
                schedule_key = list(result2['schedules'].keys())[0] 
                schedule = result2['schedules'][schedule_key]
                print(f\"Schedule {schedule_key} has {len(schedule.get('events', []))} events\")
                
                for i, event in enumerate(schedule.get('events', [])):
                    print(f\"  Event {i+1}: {event['stage_name']}\")
                    for role, assignments in event.get('assigned', {}).items():
                        print(f\"    {role} assignments: {len(assignments)} seats - {assignments}\")
            
            return True
        else:
            print(\"Two-phase scheduling failed.\")
            return False
            
    except Exception as e:
        print(f\"Two-phase solve failed with error: {e}\")
        import traceback
        traceback.print_exc()
        return False

if __name__ == \"__main__\":
    success = test_two_phase_scheduling()
    if success:
        print(\"\\nTest passed!\")
    else:
        print(\"\\nTest failed!\")
        sys.exit(1)