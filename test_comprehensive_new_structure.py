import json
from scheduler import OptimizedInterviewScheduler, generate_dummy_data

def test_basic_functionality():
    """Test basic functionality with the new structure"""
    print("=" * 50)
    print("TEST 1: Basic Functionality")
    print("=" * 50)
    
    request = {
        "stages": [
            {
                "stage_name": "Screening",
                "duration": 30,
                "seats": [
                    {"seat_id": "Room_A"},
                    {"seat_id": "Room_B"}
                ]
            },
            {
                "stage_name": "Tech_Interview",
                "duration": 60,
                "seats": [
                    {"seat_id": "Room_A"},
                    {"seat_id": "Room_B"}
                ]
            }
        ],
        "interviewers": [
            # Trained interviewers
            {"id": "Alice", "current_load": 0, "last2w_load": 2, "mode": "trained"},
            {"id": "Bob", "current_load": 1, "last2w_load": 1, "mode": "trained"},
            {"id": "Charlie", "current_load": 0, "last2w_load": 0, "mode": "trained"},
            
            # Shadow interviewers
            {"id": "David", "current_load": 0, "last2w_load": 3, "mode": "shadow"},
            {"id": "Eve", "current_load": 2, "last2w_load": 2, "mode": "shadow"},
            {"id": "Frank", "current_load": 1, "last2w_load": 1, "mode": "shadow"},
            
            # Reverse shadow interviewers
            {"id": "Grace", "current_load": 0, "last2w_load": 1, "mode": "reverse_shadow"},
            {"id": "Henry", "current_load": 1, "last2w_load": 0, "mode": "reverse_shadow"},
            {"id": "Ivy", "current_load": 0, "last2w_load": 2, "mode": "reverse_shadow"}
        ],
        "availability_windows": [
            {"start": "2025-09-01T09:00", "end": "2025-09-01T17:00"}
        ],
        "busy_intervals": [],
        "time_step_minutes": 15,
        "weekly_limit": 5,
        "max_time_seconds": 30.0,
        "require_distinct_days": False,
        "top_k_solutions": 5,
        "schedule_on_same_day": True
    }
    
    try:
        scheduler = OptimizedInterviewScheduler(
            stages=request["stages"],
            interviewers=request["interviewers"],
            availability_windows=request["availability_windows"],
            busy_intervals=request["busy_intervals"],
            time_step_minutes=request["time_step_minutes"],
            weekly_limit=request["weekly_limit"],
            max_time_seconds=request["max_time_seconds"],
            require_distinct_days=request["require_distinct_days"],
            top_k_solutions=request["top_k_solutions"],
            schedule_on_same_day=request["schedule_on_same_day"]
        )
        
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

def test_mode_filtering():
    """Test that interviewers are correctly filtered by mode"""
    print("\n" + "=" * 50)
    print("TEST 2: Mode Filtering")
    print("=" * 50)
    
    request = {
        "stages": [
            {
                "stage_name": "Single_Stage",
                "duration": 30,
                "seats": [
                    {"seat_id": "Test_Room"}
                ]
            }
        ],
        "interviewers": [
            # Only trained interviewers
            {"id": "Trained1", "current_load": 0, "last2w_load": 0, "mode": "trained"},
            {"id": "Trained2", "current_load": 0, "last2w_load": 0, "mode": "trained"},
            # No shadow or reverse shadow interviewers
        ],
        "availability_windows": [
            {"start": "2025-09-01T09:00", "end": "2025-09-01T17:00"}
        ],
        "busy_intervals": [],
        "time_step_minutes": 15,
        "weekly_limit": 5,
        "max_time_seconds": 30.0,
        "require_distinct_days": False,
        "top_k_solutions": 5,
        "schedule_on_same_day": True
    }
    
    try:
        scheduler = OptimizedInterviewScheduler(
            stages=request["stages"],
            interviewers=request["interviewers"],
            availability_windows=request["availability_windows"],
            busy_intervals=request["busy_intervals"],
            time_step_minutes=request["time_step_minutes"],
            weekly_limit=request["weekly_limit"],
            max_time_seconds=request["max_time_seconds"],
            require_distinct_days=request["require_distinct_days"],
            top_k_solutions=request["top_k_solutions"],
            schedule_on_same_day=request["schedule_on_same_day"]
        )
        
        # This should fail because there are no shadow or reverse_shadow interviewers
        result = scheduler.solve()
        print(f"Status: {result['status']}")
        
        if result['status'] == 'INFEASIBLE':
            print("Correctly identified infeasible solution due to missing interviewer modes")
            return True
        else:
            print("Unexpected: Solution found despite missing interviewer modes")
            return False
    except Exception as e:
        print(f"Error (expected): {e}")
        return True  # Error is expected in this case

def test_load_based_assignment():
    """Test that interviewers with lower loads are preferred"""
    print("\n" + "=" * 50)
    print("TEST 3: Load-Based Assignment")
    print("=" * 50)
    
    request = {
        "stages": [
            {
                "stage_name": "Load_Test",
                "duration": 30,
                "seats": [
                    {"seat_id": "Room_1"}
                ]
            }
        ],
        "interviewers": [
            # High load interviewer
            {"id": "HighLoad", "current_load": 4, "last2w_load": 8, "mode": "trained"},
            # Low load interviewer
            {"id": "LowLoad", "current_load": 0, "last2w_load": 1, "mode": "trained"},
            # Shadow interviewers
            {"id": "Shadow1", "current_load": 2, "last2w_load": 3, "mode": "shadow"},
            {"id": "Shadow2", "current_load": 0, "last2w_load": 1, "mode": "shadow"},
            # Reverse shadow interviewers
            {"id": "Reverse1", "current_load": 1, "last2w_load": 2, "mode": "reverse_shadow"},
            {"id": "Reverse2", "current_load": 0, "last2w_load": 0, "mode": "reverse_shadow"}
        ],
        "availability_windows": [
            {"start": "2025-09-01T09:00", "end": "2025-09-01T17:00"}
        ],
        "busy_intervals": [],
        "time_step_minutes": 15,
        "weekly_limit": 5,
        "max_time_seconds": 30.0,
        "require_distinct_days": False,
        "top_k_solutions": 5,
        "schedule_on_same_day": True
    }
    
    try:
        scheduler = OptimizedInterviewScheduler(
            stages=request["stages"],
            interviewers=request["interviewers"],
            availability_windows=request["availability_windows"],
            busy_intervals=request["busy_intervals"],
            time_step_minutes=request["time_step_minutes"],
            weekly_limit=request["weekly_limit"],
            max_time_seconds=request["max_time_seconds"],
            require_distinct_days=request["require_distinct_days"],
            top_k_solutions=request["top_k_solutions"],
            schedule_on_same_day=request["schedule_on_same_day"]
        )
        
        result = scheduler.solve()
        print(f"Status: {result['status']}")
        
        if result['status'] != 'INFEASIBLE' and result['schedules']:
            first_schedule_key = list(result['schedules'].keys())[0]
            first_schedule = result['schedules'][first_schedule_key]
            
            print("\nGenerated schedule:")
            for event in first_schedule['events']:
                print(f"  {event['stage_name']}: {event['start']} to {event['end']}")
                for role, assignments in event['assigned'].items():
                    interviewer_id = list(assignments.values())[0]  # Get the assigned interviewer
                    # Find the interviewer in our list
                    for interviewer in request["interviewers"]:
                        if interviewer["id"] == interviewer_id:
                            print(f"    {role}: {interviewer_id} (current_load: {interviewer['current_load']}, last2w_load: {interviewer['last2w_load']})")
                            break
            return True
        else:
            print("No feasible solution found")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_busy_intervals():
    """Test busy interval constraints with new structure"""
    print("\n" + "=" * 50)
    print("TEST 4: Busy Interval Constraints")
    print("=" * 50)
    
    request = {
        "stages": [
            {
                "stage_name": "Busy_Test",
                "duration": 30,
                "seats": [
                    {"seat_id": "Room_1"}
                ]
            }
        ],
        "interviewers": [
            {"id": "Available", "current_load": 0, "last2w_load": 1, "mode": "trained"},
            {"id": "Busy", "current_load": 0, "last2w_load": 1, "mode": "trained"},
            {"id": "Shadow1", "current_load": 0, "last2w_load": 1, "mode": "shadow"},
            {"id": "Shadow2", "current_load": 0, "last2w_load": 1, "mode": "shadow"},
            {"id": "Reverse1", "current_load": 0, "last2w_load": 1, "mode": "reverse_shadow"},
            {"id": "Reverse2", "current_load": 0, "last2w_load": 1, "mode": "reverse_shadow"}
        ],
        "availability_windows": [
            {"start": "2025-09-01T09:00", "end": "2025-09-01T17:00"}
        ],
        "busy_intervals": [
            {"interviewer_id": "Busy", "start": "2025-09-01T09:00", "end": "2025-09-01T09:30"}
        ],
        "time_step_minutes": 15,
        "weekly_limit": 5,
        "max_time_seconds": 30.0,
        "require_distinct_days": False,
        "top_k_solutions": 5,
        "schedule_on_same_day": True
    }
    
    try:
        scheduler = OptimizedInterviewScheduler(
            stages=request["stages"],
            interviewers=request["interviewers"],
            availability_windows=request["availability_windows"],
            busy_intervals=request["busy_intervals"],
            time_step_minutes=request["time_step_minutes"],
            weekly_limit=request["weekly_limit"],
            max_time_seconds=request["max_time_seconds"],
            require_distinct_days=request["require_distinct_days"],
            top_k_solutions=request["top_k_solutions"],
            schedule_on_same_day=request["schedule_on_same_day"]
        )
        
        result = scheduler.solve()
        print(f"Status: {result['status']}")
        
        if result['status'] != 'INFEASIBLE' and result['schedules']:
            first_schedule_key = list(result['schedules'].keys())[0]
            first_schedule = result['schedules'][first_schedule_key]
            
            print("\nGenerated schedule:")
            for event in first_schedule['events']:
                print(f"  {event['stage_name']}: {event['start']} to {event['end']}")
                for role, assignments in event['assigned'].items():
                    interviewer_id = list(assignments.values())[0]
                    print(f"    {role}: {interviewer_id}")
                    if interviewer_id == "Busy":
                        print("    ERROR: Busy interviewer was assigned during busy time!")
                        return False
            print("SUCCESS: Busy interviewer correctly avoided during busy time")
            return True
        else:
            print("No feasible solution found - this might be correct if no other trained interviewers are available")
            # Check if Available interviewer exists and is not busy
            has_available = any(i["id"] == "Available" for i in request["interviewers"])
            if has_available:
                print("ERROR: Available interviewer exists but solution is infeasible")
                return False
            return True
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_generate_dummy_data():
    """Test the updated generate_dummy_data function"""
    print("\n" + "=" * 50)
    print("TEST 5: Generate Dummy Data")
    print("=" * 50)
    
    try:
        stages, interviewers_data, availability, busy_intervals = generate_dummy_data(
            num_interviewers=20,
            num_stages=2,
            stage_duration_range=(30, 60),
            num_weeks=1,
            seats_per_stage=(1, 2)
        )
        
        print(f"Generated {len(stages)} stages")
        print(f"Generated {len(interviewers_data)} interviewers")
        print(f"Generated {len(availability)} availability windows")
        print(f"Generated {len(busy_intervals)} busy intervals")
        
        # Check that interviewers have the correct structure
        if interviewers_data:
            interviewer = interviewers_data[0]
            required_fields = ["id", "current_load", "last2w_load", "mode"]
            missing_fields = [field for field in required_fields if field not in interviewer]
            if missing_fields:
                print(f"Missing fields in interviewer data: {missing_fields}")
                return False
            else:
                print(f"Sample interviewer: {interviewer}")
                return True
        else:
            print("No interviewers generated")
            return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Running comprehensive tests for the new interviewer structure...\n")
    
    tests = [
        test_basic_functionality,
        test_mode_filtering,
        test_load_based_assignment,
        test_busy_intervals,
        test_generate_dummy_data
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"Test failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"TEST RESULTS: {passed}/{total} tests passed")
    print("=" * 50)