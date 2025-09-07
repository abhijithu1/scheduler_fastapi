import json
from scheduler import OptimizedInterviewScheduler

# Load the sample request
with open('sample_request_full.json', 'r') as f:
    request_data = json.load(f)

# Test with schedule_on_same_day=True (should use 2-hour gaps)
scheduler = OptimizedInterviewScheduler(
    stages=request_data['stages'],
    current_week_load=request_data['current_week_load'],
    last_2w_load=request_data['last_2w_load'],
    availability_windows=request_data['availability_windows'],
    busy_intervals=request_data['busy_intervals'],
    time_step_minutes=request_data['time_step_minutes'],
    weekly_limit=request_data['weekly_limit'],
    max_time_seconds=request_data['max_time_seconds'],
    require_distinct_days=False,
    top_k_solutions=request_data['top_k_solutions'],
    schedule_on_same_day=True
)

print("Testing with schedule_on_same_day=True")
print("Expected: 2-hour gaps between stages")
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
else:
    print("No feasible solution found")

print("\n" + "="*50)

# Test with schedule_on_same_day=False (should use 24-hour gaps)
scheduler = OptimizedInterviewScheduler(
    stages=request_data['stages'],
    current_week_load=request_data['current_week_load'],
    last_2w_load=request_data['last_2w_load'],
    availability_windows=request_data['availability_windows'],
    busy_intervals=request_data['busy_intervals'],
    time_step_minutes=request_data['time_step_minutes'],
    weekly_limit=request_data['weekly_limit'],
    max_time_seconds=request_data['max_time_seconds'],
    require_distinct_days=False,
    top_k_solutions=request_data['top_k_solutions'],
    schedule_on_same_day=False
)

print("\nTesting with schedule_on_same_day=False")
print("Expected: ~24-hour gaps between stages")
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
else:
    print("No feasible solution found")