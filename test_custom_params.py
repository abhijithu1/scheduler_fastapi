import json
from scheduler import OptimizedInterviewScheduler

# Load the custom sample request
with open('sample_request_custom.json', 'r') as f:
    request_data = json.load(f)

print("Testing custom parameters:")
print(f"  daily_availability_start: {request_data['daily_availability_start']}")
print(f"  daily_availability_end: {request_data['daily_availability_end']}")
print(f"  min_gap_between_stages: {request_data['min_gap_between_stages']} minutes")
print(f"  schedule_on_same_day: {request_data['schedule_on_same_day']}")

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
print(f"\nStatus: {result['status']}")

if result['status'] != 'INFEASIBLE' and result['schedules']:
    first_schedule_key = list(result['schedules'].keys())[0]
    first_schedule = result['schedules'][first_schedule_key]
    
    print(f"\nFirst schedule events:")
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
            print(f"    Gap: {gap_minutes} minutes (minimum required: {request_data['min_gap_between_stages']})")
            
    # Check if events are on the same day
    if first_schedule['events']:
        dates = [event['start'][:10] for event in first_schedule['events']]
        unique_dates = set(dates)
        print(f"\nDates used: {sorted(list(unique_dates))}")
        print(f"Number of distinct days: {len(unique_dates)}")
        print(f"All events on same day: {len(unique_dates) == 1}")
else:
    print("No feasible solution found")