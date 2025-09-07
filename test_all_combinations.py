import json
from scheduler import OptimizedInterviewScheduler

# Load the sample request
with open('sample_request_full.json', 'r') as f:
    request_data = json.load(f)

def test_combination(schedule_on_same_day, require_distinct_days, description):
    print(f"\n{description}")
    print(f"schedule_on_same_day={schedule_on_same_day}, require_distinct_days={require_distinct_days}")
    
    scheduler = OptimizedInterviewScheduler(
        stages=request_data['stages'],
        current_week_load=request_data['current_week_load'],
        last_2w_load=request_data['last_2w_load'],
        availability_windows=request_data['availability_windows'],
        busy_intervals=request_data['busy_intervals'],
        time_step_minutes=request_data['time_step_minutes'],
        weekly_limit=request_data['weekly_limit'],
        max_time_seconds=request_data['max_time_seconds'],
        require_distinct_days=require_distinct_days,
        top_k_solutions=3,  # Just get a few solutions for testing
        schedule_on_same_day=schedule_on_same_day
    )
    
    result = scheduler.solve()
    print(f"Status: {result['status']}")
    
    if result['status'] != 'INFEASIBLE' and result['schedules']:
        first_schedule_key = list(result['schedules'].keys())[0]
        first_schedule = result['schedules'][first_schedule_key]
        print(f"Score: {first_schedule['score']}")
        
        # Count distinct days
        if first_schedule['events']:
            dates = [event['start'][:10] for event in first_schedule['events']]
            unique_dates = set(dates)
            print(f"Distinct days: {len(unique_dates)}")
            
            # Show first few events
            print("First events:")
            for i, event in enumerate(first_schedule['events'][:3]):  # Show first 3
                print(f"  {event['stage_name']}: {event['start']}")
    else:
        print("No solution found")

# Test all combinations
test_combination(True, False, "Case 1: Prefer same day")
test_combination(True, True, "Case 2: Prefer same day but require distinct days")
test_combination(False, False, "Case 3: Schedule on different days")
test_combination(False, True, "Case 4: Schedule on different days and require distinct days")