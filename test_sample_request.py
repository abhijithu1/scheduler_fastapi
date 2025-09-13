import json
from scheduler import OptimizedInterviewScheduler

def test_sample_request():
    print("Testing with updated minimal sample request...")
    
    try:
        # Load the sample request
        with open('sample_request_minimal.json', 'r') as f:
            request_data = json.load(f)
        
        # Create scheduler instance
        scheduler = OptimizedInterviewScheduler(
            stages=request_data["stages"],
            interviewers=request_data["interviewers"],
            availability_windows=request_data["availability_windows"],
            busy_intervals=request_data.get("busy_intervals", []),
            time_step_minutes=request_data.get("time_step_minutes", 15),
            weekly_limit=request_data.get("weekly_limit", 5),
            max_time_seconds=request_data.get("max_time_seconds", 30.0),
            require_distinct_days=request_data.get("require_distinct_days", False),
            top_k_solutions=request_data.get("top_k_solutions", 50),
            schedule_on_same_day=request_data.get("schedule_on_same_day", True),
            daily_availability_start=request_data.get("daily_availability_start", "09:00"),
            daily_availability_end=request_data.get("daily_availability_end", "17:00"),
            min_gap_between_stages=request_data.get("min_gap_between_stages", 0)
        )
        
        # Generate schedules
        result = scheduler.solve()
        print(f"Status: {result['status']}")
        
        if result['status'] != 'INFEASIBLE' and result['schedules']:
            first_schedule_key = list(result['schedules'].keys())[0]
            first_schedule = result['schedules'][first_schedule_key]
            
            print("\nGenerated schedule:")
            for event in first_schedule['events']:
                print(f"  {event['stage_name']}: {event['start']} to {event['end']}")
                for role, assignments in event['assigned'].items():
                    print(f"    {role}: {assignments}")
            return True
        else:
            print("No feasible solution found")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    test_sample_request()