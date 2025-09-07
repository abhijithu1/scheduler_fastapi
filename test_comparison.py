import json
from scheduler import OptimizedInterviewScheduler

# Load the custom sample request
with open('sample_request_custom.json', 'r') as f:
    request_data = json.load(f)

# Test with custom parameters
print("=== Test with custom parameters ===")
print(f"daily_availability: {request_data['daily_availability_start']}-{request_data['daily_availability_end']}")
print(f"min_gap_between_stages: {request_data['min_gap_between_stages']} minutes")
print(f"schedule_on_same_day: {request_data['schedule_on_same_day']}")

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
    schedule_on_same_day=request_data['schedule_on_same_day'],
    daily_availability_start=request_data['daily_availability_start'],
    daily_availability_end=request_data['daily_availability_end'],
    min_gap_between_stages=request_data['min_gap_between_stages']
)

result = scheduler.solve()
print(f"Status: {result['status']}")

if result['status'] != 'INFEASIBLE' and result['schedules']:
    first_schedule_key = list(result['schedules'].keys())[0]
    first_schedule = result['schedules'][first_schedule_key]
    print(f"Score: {first_schedule['score']}")
    
    if first_schedule['events']:
        dates = [event['start'][:10] for event in first_schedule['events']]
        unique_dates = set(dates)
        print(f"Distinct days: {len(unique_dates)}")

# Test with default parameters (simulating old behavior)
print("\n=== Test with default parameters (old behavior) ===")
request_data_old = request_data.copy()
# Remove the new parameters to use defaults
scheduler_old = OptimizedInterviewScheduler(
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
    # Default values for new parameters:
    # daily_availability_start="09:00"
    # daily_availability_end="17:00" 
    # min_gap_between_stages=0 (will use 120 min for same_day)
)

result_old = scheduler_old.solve()
print(f"Status: {result_old['status']}")

if result_old['status'] != 'INFEASIBLE' and result_old['schedules']:
    first_schedule_key = list(result_old['schedules'].keys())[0]
    first_schedule = result_old['schedules'][first_schedule_key]
    print(f"Score: {first_schedule['score']}")
    
    if first_schedule['events']:
        dates = [event['start'][:10] for event in first_schedule['events']]
        unique_dates = set(dates)
        print(f"Distinct days: {len(unique_dates)}")