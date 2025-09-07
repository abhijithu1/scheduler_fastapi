import json
from scheduler import OptimizedInterviewScheduler

# Load the sample request
with open('sample_request_full.json', 'r') as f:
    request_data = json.load(f)

# Test with schedule_on_same_day=True (should prefer same day)
scheduler1 = OptimizedInterviewScheduler(
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

print("Testing with schedule_on_same_day=True (should prefer same day)")
result1 = scheduler1.solve()
print(f"Status: {result1['status']}")

if result1['status'] != 'INFEASIBLE' and result1['schedules']:
    first_schedule_key = list(result1['schedules'].keys())[0]
    first_schedule = result1['schedules'][first_schedule_key]
    print(f"Score: {first_schedule['score']}")
    
    # Count distinct days
    if first_schedule['events']:
        dates = [event['start'][:10] for event in first_schedule['events']]
        unique_dates = set(dates)
        print(f"Number of distinct days: {len(unique_dates)}")

# Test with schedule_on_same_day=False (should not prefer same day)
request_data_modified = request_data.copy()
request_data_modified['schedule_on_same_day'] = False

scheduler2 = OptimizedInterviewScheduler(
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

print("\nTesting with schedule_on_same_day=False (should not prefer same day)")
result2 = scheduler2.solve()
print(f"Status: {result2['status']}")

if result2['status'] != 'INFEASIBLE' and result2['schedules']:
    first_schedule_key = list(result2['schedules'].keys())[0]
    first_schedule = result2['schedules'][first_schedule_key]
    print(f"Score: {first_schedule['score']}")
    
    # Count distinct days
    if first_schedule['events']:
        dates = [event['start'][:10] for event in first_schedule['events']]
        unique_dates = set(dates)
        print(f"Number of distinct days: {len(unique_dates)}")

print("\nComparison:")
print("When schedule_on_same_day=True, we expect lower scores (preference for same day)")
print("When schedule_on_same_day=False, we expect higher scores (no preference for same day)")