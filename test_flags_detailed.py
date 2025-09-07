import json
from scheduler import OptimizedInterviewScheduler

# Load the sample request
with open('sample_request_full.json', 'r') as f:
    request_data = json.load(f)

print("Original request flags:")
print(f"  schedule_on_same_day: {request_data['schedule_on_same_day']}")
print(f"  require_distinct_days: {request_data['require_distinct_days']}")

# Test with both flags explicitly set to allow same-day scheduling
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

print("\nTesting with schedule_on_same_day=True and require_distinct_days=False")
result = scheduler.solve()
print(f"Status: {result['status']}")

if result['status'] != 'INFEASIBLE' and result['schedules']:
    # Check the first schedule
    first_schedule_key = list(result['schedules'].keys())[0]
    first_schedule = result['schedules'][first_schedule_key]
    
    print("\nFirst schedule events:")
    for event in first_schedule['events']:
        print(f"  {event['stage_name']}: {event['start']} to {event['end']}")
        
    # Check if events are on the same day
    if first_schedule['events']:
        dates = [event['start'][:10] for event in first_schedule['events']]
        unique_dates = set(dates)
        print(f"\nDates used: {sorted(list(unique_dates))}")
        print(f"Number of distinct days: {len(unique_dates)}")
        print(f"All events on same day: {len(unique_dates) == 1}")
else:
    print("No feasible solution found")

# Let's also test with require_distinct_days=True to see the difference
print("\n" + "="*50)
print("Testing with schedule_on_same_day=True and require_distinct_days=True")

scheduler2 = OptimizedInterviewScheduler(
    stages=request_data['stages'],
    current_week_load=request_data['current_week_load'],
    last_2w_load=request_data['last_2w_load'],
    availability_windows=request_data['availability_windows'],
    busy_intervals=request_data['busy_intervals'],
    time_step_minutes=request_data['time_step_minutes'],
    weekly_limit=request_data['weekly_limit'],
    max_time_seconds=request_data['max_time_seconds'],
    require_distinct_days=True,  # This is the difference
    top_k_solutions=request_data['top_k_solutions'],
    schedule_on_same_day=True
)

result2 = scheduler2.solve()
print(f"Status: {result2['status']}")

if result2['status'] != 'INFEASIBLE' and result2['schedules']:
    # Check the first schedule
    first_schedule_key = list(result2['schedules'].keys())[0]
    first_schedule = result2['schedules'][first_schedule_key]
    
    print("\nFirst schedule events:")
    for event in first_schedule['events']:
        print(f"  {event['stage_name']}: {event['start']} to {event['end']}")
        
    # Check if events are on the same day
    if first_schedule['events']:
        dates = [event['start'][:10] for event in first_schedule['events']]
        unique_dates = set(dates)
        print(f"\nDates used: {sorted(list(unique_dates))}")
        print(f"Number of distinct days: {len(unique_dates)}")
        print(f"All events on same day: {len(unique_dates) == 1}")
else:
    print("No feasible solution found")