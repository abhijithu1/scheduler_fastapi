"""
Example client script to test the Interview Scheduling API
"""

import requests
import json

# API endpoint
BASE_URL = "http://localhost:8000"

def test_schedule_generation():
    """Test the schedule generation endpoint"""
    
    # Sample data for scheduling
    sample_request = {
        "stages": [
            {
                "stage_name": "Tech_Screen",
                "duration": 60,
                "seats": [
                    {
                        "seat_id": "Room_1",
                        "interviewers": {
                            "trained": ["intv_1", "intv_2"],
                            "shadow": ["intv_3", "intv_4"],
                            "reverse_shadow": ["intv_5", "intv_6"]
                        }
                    }
                ]
            },
            {
                "stage_name": "System_Design",
                "duration": 90,
                "seats": [
                    {
                        "seat_id": "Room_2",
                        "interviewers": {
                            "trained": ["intv_7", "intv_8"],
                            "shadow": ["intv_9", "intv_10"],
                            "reverse_shadow": ["intv_11", "intv_12"]
                        }
                    }
                ]
            }
        ],
        "availability_windows": [
            {
                "start": "2025-09-01T09:00",
                "end": "2025-09-01T17:00"
            },
            {
                "start": "2025-09-02T09:00",
                "end": "2025-09-02T17:00"
            }
        ],
        "busy_intervals": [
            {
                "interviewer_id": "intv_1",
                "start": "2025-09-01T10:00",
                "end": "2025-09-01T11:00"
            }
        ],
        "schedule_on_same_day": True
    }
    
    try:
        # Send POST request to schedule endpoint
        response = requests.post(
            f"{BASE_URL}/schedule",
            json=sample_request,
            headers={"Content-Type": "application/json"}
        )
        
        # Check if request was successful
        if response.status_code == 200:
            result = response.json()
            print("Schedule generation successful!")
            print(json.dumps(result, indent=2))
            return True
        else:
            print(f"Error: {response.status_code}")
            print(response.text)
            return False
            
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the API. Make sure the server is running.")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_health_check():
    """Test the health check endpoint"""
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("Health check passed!")
            print(response.json())
            return True
        else:
            print(f"Health check failed: {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("Error: Could not connect to the API. Make sure the server is running.")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Interview Scheduling API...")
    
    # Test health check
    print("\n1. Testing health check endpoint:")
    test_health_check()
    
    # Test schedule generation
    print("\n2. Testing schedule generation endpoint:")
    test_schedule_generation()