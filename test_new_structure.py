import json
from scheduler import OptimizedInterviewScheduler

# Create a simple test case with the new structure
simple_request = {
    "stages": [
        {
            "stage_name": "Short_Interview_1",
            "duration": 30,  # 30 minutes
            "seats": [
                {
                    "seat_id": "Room_1"
                }
            ]
        },
        {
            "stage_name": "Short_Interview_2",
            "duration": 45,  # 45 minutes
            "seats": [
                {
                    "seat_id": "Room_1"
                }
            ]
        }
    ],
    "interviewers": [
        {
            "id": "Alex Johnson",
            "current_load": 0,
            "last2w_load": 0,
            "mode": "trained"
        },
        {
            "id": "Maria Garcia",
            "current_load": 0,
            "last2w_load": 0,
            "mode": "trained"
        },
        {
            "id": "Sarah Davis",
            "current_load": 0,
            "last2w_load": 0,
            "mode": "shadow"
        },
        {
            "id": "Robert Wilson",
            "current_load": 0,
            "last2w_load": 0,
            "mode": "shadow"
        },
        {
            "id": "James Smith",
            "current_load": 0,
            "last2w_load": 0,
            "mode": "trained"
        },
        {
            "id": "Emily Chen",
            "current_load": 0,
            "last2w_load": 0,
            "mode": "trained"
        },
        {
            "id": "Lisa Miller",
            "current_load": 0,
            "last2w_load": 0,
            "mode": "shadow"
        },
        {
            "id": "David Taylor",
            "current_load": 0,
            "last2w_load": 0,
            "mode": "shadow"
        },
        {
            "id": "William Thomas",
            "current_load": 0,
            "last2w_load": 0,
            "mode": "reverse_shadow"
        },
        {
            "id": "Amanda Jackson",
            "current_load": 0,
            "last2w_load": 0,
            "mode": "reverse_shadow"
        }
    ],
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

print("Testing with a simple case that should fit on one day with new structure")

# Test with schedule_on_same_day=True
scheduler = OptimizedInterviewScheduler(
    stages=simple_request["stages"],
    interviewers=simple_request["interviewers"],
    availability_windows=simple_request["availability_windows"],
    busy_intervals=simple_request["busy_intervals"],
    time_step_minutes=simple_request["time_step_minutes"],
    weekly_limit=simple_request["weekly_limit"],
    max_time_seconds=simple_request["max_time_seconds"],
    require_distinct_days=simple_request["require_distinct_days"],
    top_k_solutions=simple_request["top_k_solutions"],
    schedule_on_same_day=simple_request["schedule_on_same_day"]
)

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