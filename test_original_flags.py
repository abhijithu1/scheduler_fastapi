import json
from scheduler import OptimizedInterviewScheduler

# Load the sample request
with open('sample_request_full.json', 'r') as f:
    request_data = json.load(f)

print("Original flags in sample_request_full.json:")
print(f"  schedule_on_same_day: {request_data['schedule_on_same_day']}")
print(f"  require_distinct_days: {request_data['require_distinct_days']}")

# Test with the exact flags from the sample file
scheduler = OptimizedInterviewScheduler(
    stages=request_data['stages'],
    current_week_load=request_data['current_week_load'],
    last_2w_load=request_data['last_2w_load'],
    availability_windows=request_data['availability_windows'],
    busy_intervals=request_data['busy_intervals'],
    time_step_minutes=request_data['time_step_minutes'],
    weekly_limit=request_data['weekly_limit'],
    max_time_seconds=request_data['max_time_seconds'],
    require_distinct_days=request_data['require_distinct_days'],
    top_k_solutions=request_data['top_k_solutions'],
    schedule_on_same_day=request_data['schedule_on_same_day']
)

print(f"\nTesting with schedule_on_same_day={request_data['schedule_on_same_day']}, require_distinct_days={request_data['require_distinct_days']}")
result = scheduler.solve()
print(f"Status: {result['status']}")

if result['status'] != 'INFEASIBLE' and result['schedules']:
    first_schedule_key = list(result['schedules'].keys())[0]
    first_schedule = result['schedules'][first_schedule_key]
    
    print("\nFirst schedule events:")
    for event in first_schedule['events']:
        print(f"  {event['stage_name']}: {event['start']} to {event['end']}")
        
    # Count distinct days
    if first_schedule['events']:
        dates = [event['start'][:10] for event in first_schedule['events']]
        unique_dates = set(dates)
        print(f"\nDistinct days used: {sorted(list(unique_dates))}")
        print(f"Number of distinct days: {len(unique_dates)}")
        print(f"All events on same day: {len(unique_dates) == 1}")
else:
    print("No feasible solution found")

# Now let's test with the opposite values
opposite_schedule_on_same_day = not request_data['schedule_on_same_day']
opposite_require_distinct_days = not request_data['require_distinct_days']

print(f"\nTesting with schedule_on_same_day={opposite_schedule_on_same_day}, require_distinct_days={opposite_require_distinct_days}")
scheduler2 = OptimizedInterviewScheduler(
    stages=request_data['stages'],
    current_week_load=request_data['current_week_load'],
    last_2w_load=request_data['last_2w_load'],
    availability_windows=request_data['availability_windows'],
    busy_intervals=request_data['busy_intervals'],
    time_step_minutes=request_data['time_step_minutes'],
    weekly_limit=request_data['weekly_limit'],
    max_time_seconds=request_data['max_time_seconds'],
    require_distinct_days=opposite_require_distinct_days,
    top_k_solutions=request_data['top_k_solutions'],
    schedule_on_same_day=opposite_schedule_on_same_day
)

result2 = scheduler2.solve()
print(f"Status: {result2['status']}")

if result2['status'] != 'INFEASIBLE' and result2['schedules']:
    first_schedule_key = list(result2['schedules'].keys())[0]
    first_schedule = result2['schedules'][first_schedule_key]
    
    print("\nFirst schedule events:")
    for event in first_schedule['events']:
        print(f"  {event['stage_name']}: {event['start']} to {event['end']}")
        
    # Count distinct days
    if first_schedule['events']:
        dates = [event['start'][:10] for event in first_schedule['events']]
        unique_dates = set(dates)
        print(f"\nDistinct days used: {sorted(list(unique_dates))}")
        print(f"Number of distinct days: {len(unique_dates)}")
        print(f"All events on same day: {len(unique_dates) == 1}")
else:
    print("No feasible solution found")

print(f"\nComparison:")
print(f"Original flags: schedule_on_same_day={request_data['schedule_on_same_day']}, require_distinct_days={request_data['require_distinct_days']}")
print(f"Opposite flags: schedule_on_same_day={opposite_schedule_on_same_day}, require_distinct_days={opposite_require_distinct_days}")
print("If the flags are working correctly, we should see different behaviors.")