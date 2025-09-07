import json
from scheduler import OptimizedInterviewScheduler

# Load the full sample request
with open('sample_request_full.json', 'r') as f:
    request_data = json.load(f)

print("=== Test with full sample and custom parameters ===")
print(f"daily_availability: 08:00-18:00 (10 hours vs default 8 hours)")
print(f"min_gap_between_stages: 30 minutes (vs default 120 minutes)")
print(f"schedule_on_same_day: {request_data['schedule_on_same_day']}")

# Modify availability windows to be 08:00-18:00 instead of 09:00-17:00
custom_availability = []
for window in request_data['availability_windows']:
    start_date = window['start'][:11]  # Keep date part
    end_date = window['end'][:11]      # Keep date part
    custom_availability.append({
        "start": start_date + "08:00",
        "end": end_date + "18:00"
    })

scheduler = OptimizedInterviewScheduler(
    stages=request_data['stages'],
    current_week_load=request_data['current_week_load'],
    last_2w_load=request_data['last_2w_load'],
    availability_windows=custom_availability,
    busy_intervals=request_data['busy_intervals'],
    time_step_minutes=request_data['time_step_minutes'],
    weekly_limit=request_data['weekly_limit'],
    max_time_seconds=request_data['max_time_seconds'],
    require_distinct_days=request_data['require_distinct_days'],
    top_k_solutions=request_data['top_k_solutions'],
    schedule_on_same_day=request_data['schedule_on_same_day'],
    daily_availability_start="08:00",
    daily_availability_end="18:00",
    min_gap_between_stages=30  # 30 minutes instead of default 120
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
        print("First few events:")
        for i, event in enumerate(first_schedule['events'][:3]):
            print(f"  {event['stage_name']}: {event['start']} to {event['end']}")

print("\n=== Test with full sample and default parameters ===")
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
        print("First few events:")
        for i, event in enumerate(first_schedule['events'][:3]):
            print(f"  {event['stage_name']}: {event['start']} to {event['end']}")