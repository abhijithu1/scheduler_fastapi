"""
FastAPI server for the Interview Scheduling System
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
from scheduler import OptimizedInterviewScheduler
import json

app = FastAPI(
    title="Interview Scheduling API",
    description="API for generating optimized interview schedules",
    version="1.0.0"
)

# Pydantic models for request/response validation
class SeatRoleInput(BaseModel):
    seat_id: str
    interviewers: Dict[str, List[str]]

class StageInput(BaseModel):
    stage_name: str
    duration: int
    seats: List[SeatRoleInput]

class AvailabilityWindowInput(BaseModel):
    start: str
    end: str

class BusyIntervalInput(BaseModel):
    interviewer_id: str
    start: str
    end: str

class ScheduleRequest(BaseModel):
    stages: List[StageInput]
    current_week_load: Optional[Dict[str, int]] = {}
    last_2w_load: Optional[Dict[str, int]] = {}
    availability_windows: List[AvailabilityWindowInput]
    busy_intervals: List[BusyIntervalInput]
    time_step_minutes: Optional[int] = 15
    weekly_limit: Optional[int] = 5
    max_time_seconds: Optional[float] = 30.0
    require_distinct_days: Optional[bool] = False
    top_k_solutions: Optional[int] = 50
    schedule_on_same_day: Optional[bool] = True

class ScheduleResponse(BaseModel):
    status: str
    schedules: Dict[str, Any]

@app.get("/")
async def root():
    return {"message": "Interview Scheduling API is running"}

@app.post("/schedule", response_model=ScheduleResponse)
async def generate_schedule(request: ScheduleRequest):
    """
    Generate optimized interview schedules based on provided constraints
    """
    try:
        # Convert input data to the format expected by the scheduler
        stages_data = []
        for stage in request.stages:
            seats_data = []
            for seat in stage.seats:
                seats_data.append({
                    "seat_id": seat.seat_id,
                    "interviewers": seat.interviewers
                })
            
            stages_data.append({
                "stage_name": stage.stage_name,
                "duration": stage.duration,
                "seats": seats_data
            })
        
        availability_data = []
        for window in request.availability_windows:
            availability_data.append({
                "start": window.start,
                "end": window.end
            })
        
        busy_intervals_data = []
        for interval in request.busy_intervals:
            busy_intervals_data.append({
                "interviewer_id": interval.interviewer_id,
                "start": interval.start,
                "end": interval.end
            })
        
        # Create scheduler instance
        scheduler = OptimizedInterviewScheduler(
            stages=stages_data,
            current_week_load=request.current_week_load,
            last_2w_load=request.last_2w_load,
            availability_windows=availability_data,
            busy_intervals=busy_intervals_data,
            time_step_minutes=request.time_step_minutes,
            weekly_limit=request.weekly_limit,
            max_time_seconds=request.max_time_seconds,
            require_distinct_days=request.require_distinct_days,
            top_k_solutions=request.top_k_solutions,
            schedule_on_same_day=request.schedule_on_same_day
        )
        
        # Generate schedules
        result = scheduler.solve()
        
        return ScheduleResponse(**result)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)