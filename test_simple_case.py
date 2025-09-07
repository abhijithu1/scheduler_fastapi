import json
from scheduler import OptimizedInterviewScheduler

# Create a simple test case that could fit on one day
simple_request = {
    "stages": [
        {
            "stage_name": "Short_Interview_1",
            "duration": 30,  # 30 minutes
            "seats": [
                {
                    "seat_id": "Room_1",
                    "interviewers": {
                        "trained": ["Alex Johnson", "Maria Garcia"],
                        "shadow": ["Sarah Davis", "Robert Wilson"]
                    }
                }
            ]
        },
        {
            "stage_name": "Short_Interview_2",
            "duration": 45,  # 45 minutes
            "seats": [
                {
                    "seat_id": "Room_1",
                    "interviewers": {
                        "trained": ["James Smith", "Emily Chen"],
                        "shadow": ["Lisa Miller", "David Taylor"]
                    }
                }
            ]
        }
    ],
    "current_week_load": {
        "Alex Johnson": 0, "Maria Garcia": 0, "Sarah Davis": 0, "Robert Wilson": 0,
        "James Smith": 0, "Emily Chen": 0, "Lisa Miller": 0, "David Taylor": 0
    },
    "last_2w_load": {
        "Alex Johnson": 0, "Maria Garcia": 0, "Sarah Davis": 0, "Robert Wilson": 0,
        "James Smith": 0, "Emily Chen": 0, "Lisa Miller": 0, "David Taylor": 0
    },
    "availability_windows": [
        {"start": "2025-09-01T09:00", "end": "2025-09-01T17:00"},
        {"start": "2025-09-02T09:00", "end": "2025-09-02T17:00"}
    ],
    "busy_intervals": [],
    "time_step_minutes": 15,
    "weekly_limit": 5,
    "max_time_seconds": 30.0,
    "require_distinct_days": False,
    "top_k_solutions": 5,
    "schedule_on_same_day": True
}

print("Testing with a simple case that should fit on one day")

# Test with schedule_on_same_day=True
scheduler = OptimizedInterviewScheduler(**simple_request)

print("\nTesting with schedule_on_same_day=True")
print("Expected: Both stages on same day with 2-hour gap")
result = scheduler.solve()
print(f"Status: {result['status']}")

if result['status'] != 'INFEASIBLE' and result['schedules']:
    # Check the first schedule
    first_schedule_key = list(result['schedules'].keys())[0]
    first_schedule = result['schedules'][first_schedule_key]
    
    print("\nFirst schedule events:")
    for i, event in enumerate(first_schedule['events']):
        print(f"  {event['stage_name']}: {event['start']} to {event['end']}")
        # Show gaps between consecutive events
        if i > 0:
            prev_end = first_schedule['events'][i-1]['end']
            curr_start = event['start']
            # Calculate actual gap in minutes
            from datetime import datetime
            prev_end_dt = datetime.fromisoformat(prev_end)
            curr_start_dt = datetime.fromisoformat(curr_start)
            gap_minutes = (curr_start_dt - prev_end_dt).total_seconds() / 60
            print(f"    Gap: {gap_minutes} minutes (expected: ~120)")
            
    # Check if events are on the same day
    if first_schedule['events']:
        dates = [event['start'][:10] for event in first_schedule['events']]
        unique_dates = set(dates)
        print(f"\nDates used: {sorted(list(unique_dates))}")
        print(f"Number of distinct days: {len(unique_dates)}")
        print(f"All events on same day: {len(unique_dates) == 1}")
else:
    print("No feasible solution found")

# Test with schedule_on_same_day=False for comparison
simple_request["schedule_on_same_day"] = False
scheduler = OptimizedInterviewScheduler(**simple_request)

print("\n" + "="*50)
print("\nTesting with schedule_on_same_day=False")
print("Expected: Stages on different days with ~24-hour gaps")
result = scheduler.solve()
print(f"Status: {result['status']}")

if result['status'] != 'INFEASIBLE' and result['schedules']:
    # Check the first schedule
    first_schedule_key = list(result['schedules'].keys())[0]
    first_schedule = result['schedules'][first_schedule_key]
    
    print("\nFirst schedule events:")
    for i, event in enumerate(first_schedule['events']):
        print(f"  {event['stage_name']}: {event['start']} to {event['end']}")
        # Show gaps between consecutive events
        if i > 0:
            prev_end = first_schedule['events'][i-1]['end']
            curr_start = event['start']
            # Calculate actual gap in minutes
            from datetime import datetime
            prev_end_dt = datetime.fromisoformat(prev_end)
            curr_start_dt = datetime.fromisoformat(curr_start)
            gap_minutes = (curr_start_dt - prev_end_dt).total_seconds() / 60
            print(f"    Gap: {gap_minutes} minutes (expected: ~1440)")
            
    # Check if events are on the same day
    if first_schedule['events']:
        dates = [event['start'][:10] for event in first_schedule['events']]
        unique_dates = set(dates)
        print(f"\nDates used: {sorted(list(unique_dates))}")
        print(f"Number of distinct days: {len(unique_dates)}")
        print(f"All events on same day: {len(unique_dates) == 1}")
else:
    print("No feasible solution found")