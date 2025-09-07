import json
from scheduler import OptimizedInterviewScheduler

# Load the sample request
with open('sample_request_full.json', 'r') as f:
    request_data = json.load(f)

print("Original request flags:")
print(f"  schedule_on_same_day: {request_data['schedule_on_same_day']}")
print(f"  require_distinct_days: {request_data['require_distinct_days']}")

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
    schedule_on_same_day=False  # This is the difference
)

print("\nTesting with schedule_on_same_day=False and require_distinct_days=False")
print("Expected: 24-hour gaps between stages")
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
            print(f"    Gap from previous: {prev_end} to {curr_start}")
else:
    print("No feasible solution found")