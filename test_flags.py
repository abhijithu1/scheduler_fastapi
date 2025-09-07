import json
from scheduler import OptimizedInterviewScheduler

# Load the sample request
with open('sample_request_full.json', 'r') as f:
    request_data = json.load(f)

# Create scheduler with the specific flags mentioned in the issue
# require_distinct_days = False, schedule_on_same_day = True
scheduler = OptimizedInterviewScheduler(
    stages=request_data['stages'],
    current_week_load=request_data['current_week_load'],
    last_2w_load=request_data['last_2w_load'],
    availability_windows=request_data['availability_windows'],
    busy_intervals=request_data['busy_intervals'],
    time_step_minutes=request_data['time_step_minutes'],
    weekly_limit=request_data['weekly_limit'],
    max_time_seconds=request_data['max_time_seconds'],
    require_distinct_days=False,  # This is False in the sample
    top_k_solutions=request_data['top_k_solutions'],
    schedule_on_same_day=True  # This is True in the sample
)

print("Testing with require_distinct_days=False and schedule_on_same_day=True")
print("Expected behavior: Stages should be scheduled on the same day with 2-hour gaps")

result = scheduler.solve()
print(f"Status: {result['status']}")

if result['status'] != 'INFEASIBLE':
    # Check the first schedule
    first_schedule_key = list(result['schedules'].keys())[0]
    first_schedule = result['schedules'][first_schedule_key]
    
    print("\nFirst schedule events:")
    for event in first_schedule['events']:
        print(f"  {event['stage_name']}: {event['start']} to {event['end']}")
        
    # Check if events are on the same day
    if first_schedule['events']:
        start_date = first_schedule['events'][0]['start'][:10]  # Extract date part
        all_same_day = all(event['start'][:10] == start_date for event in first_schedule['events'])
        print(f"\nAll events on same day: {all_same_day}")
else:
    print("No feasible solution found")