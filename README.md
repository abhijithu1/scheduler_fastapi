# Interview Scheduling API

A FastAPI-based REST API for the Interview Scheduling System that generates optimized interview schedules using Google's OR-Tools CP-SAT solver.

## Features

- Generate optimized interview schedules with multiple solutions
- Flexible scheduling options (same-day or different-day)
- Constraint satisfaction for interviewer availability and workload
- RESTful API interface for easy integration
- Docker support for containerized deployment

## Prerequisites

- Python 3.8+
- pip (Python package installer)

## Installation

1. Clone the repository or navigate to the project directory
2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

### Running the Server

1. Start the FastAPI server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

2. Or run directly with Python:
   ```bash
   python main.py
   ```

The API will be available at `http://localhost:8000`

### API Endpoints

#### 1. Health Check
- **Endpoint**: `GET /health`
- **Description**: Check if the API is running
- **Response**: 
  ```json
  {
    "status": "healthy"
  }
  ```

#### 2. Generate Schedule
- **Endpoint**: `POST /schedule`
- **Description**: Generate optimized interview schedules
- **Request Body**:
  ```json
  {
    "stages": [
      {
        "stage_name": "string",
        "duration": 0,
        "seats": [
          {
            "seat_id": "string",
            "interviewers": {
              "role_name": ["interviewer_id1", "interviewer_id2"]
            }
          }
        ]
      }
    ],
    "current_week_load": {"interviewer_id": 0},
    "last_2w_load": {"interviewer_id": 0},
    "availability_windows": [
      {
        "start": "2025-09-01T09:00",
        "end": "2025-09-01T17:00"
      }
    ],
    "busy_intervals": [
      {
        "interviewer_id": "string",
        "start": "2025-09-01T10:00",
        "end": "2025-09-01T11:00"
      }
    ],
    "time_step_minutes": 15,
    "weekly_limit": 5,
    "max_time_seconds": 30.0,
    "require_distinct_days": false,
    "top_k_solutions": 50,
    "schedule_on_same_day": true
  }
  ```

- **Response**:
  ```json
  {
    "status": "OPTIMAL",
    "schedules": {
      "schedule1": {
        "score": 0,
        "events": [
          {
            "stage_name": "string",
            "duration": 0,
            "start": "2025-09-01T09:00",
            "end": "2025-09-01T10:00",
            "assigned": {
              "role_name": {
                "seat_id": "interviewer_id"
              }
            }
          }
        ],
        "metrics": {
          "total_span_minutes": 0,
          "idle_time_minutes": 0,
          "efficiency": 0
        }
      }
    }
  }
  ```

### Running with Docker

1. Build the Docker image:
   ```bash
   docker build -t interview-scheduler .
   ```

2. Run the container:
   ```bash
   docker run -p 8000:8000 interview-scheduler
   ```

### Testing the API

Use the provided example client script:
```bash
python example_client.py
```

Or use curl with one of the sample request files:
```bash
curl -X POST "http://localhost:8000/schedule" \\
     -H "Content-Type: application/json" \\
     -d @sample_request_minimal.json
```

We provide three sample request files with different levels of complexity:
1. `sample_request_minimal.json` - Only required parameters
2. `sample_request_partial.json` - Some optional parameters included
3. `sample_request_full.json` - All parameters included with realistic data

## API Documentation

Once the server is running, you can access the interactive API documentation at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Parameters

### ScheduleRequest Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| stages | List[StageInput] | Required | Interview stages to schedule |
| current_week_load | Dict[str, int] | {} | Current week workload per interviewer |
| last_2w_load | Dict[str, int] | {} | Last 2 weeks workload per interviewer |
| availability_windows | List[AvailabilityWindowInput] | Required | Time windows when interviews can be scheduled |
| busy_intervals | List[BusyIntervalInput] | Required | Interviewer busy time intervals |
| time_step_minutes | int | 15 | Time granularity in minutes |
| weekly_limit | int | 5 | Maximum interviews per interviewer per week |
| max_time_seconds | float | 30.0 | Maximum solver time in seconds |
| require_distinct_days | bool | false | Force stages on different days |
| top_k_solutions | int | 50 | Number of solutions to generate |
| schedule_on_same_day | bool | true | Schedule all stages on same day |

## Error Handling

The API returns appropriate HTTP status codes:
- `200`: Success
- `400`: Bad request (invalid input data)
- `500`: Internal server error

Error responses include a detailed message:
```json
{
  "detail": "Error description"
}
```