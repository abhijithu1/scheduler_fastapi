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
class InterviewerInfoInput(BaseModel):
    id: str
    current_load: int
    last2w_load: int
    mode: str  # "trained", "shadow", or "reverse_shadow"

class SeatRoleInput(BaseModel):
    seat_id: str
    # In the new structure, we don't need to specify interviewers per seat-role
    # The interviewers will be filtered by mode when creating assignments

class StageInput(BaseModel):
    stage_name: str
    duration: int
    is_fixed: Optional[bool] = False
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
    interviewers: List[InterviewerInfoInput]  # New structure: list of interviewer objects
    availability_windows: List[AvailabilityWindowInput]
    busy_intervals: List[BusyIntervalInput]
    time_step_minutes: Optional[int] = 15
    weekly_limit: Optional[int] = 5
    max_time_seconds: Optional[float] = 30.0
    require_distinct_days: Optional[bool] = False
    top_k_solutions: Optional[int] = 50
    schedule_on_same_day: Optional[bool] = True
    daily_availability_start: Optional[str] = "09:00"
    daily_availability_end: Optional[str] = "17:00"
    min_gap_between_stages: Optional[int] = 0

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
                    "seat_id": seat.seat_id
                    # In the new structure, we don't need to specify interviewers per seat
                    # The scheduler will filter interviewers by mode
                })
            
            stages_data.append({
                "stage_name": stage.stage_name,
                "duration": stage.duration,
                "is_fixed": stage.is_fixed if stage.is_fixed is not None else False,
                "seats": seats_data
            })
        
        # Convert interviewer data
        interviewers_data = []
        for interviewer in request.interviewers:
            interviewers_data.append({
                "id": interviewer.id,
                "current_load": interviewer.current_load,
                "last2w_load": interviewer.last2w_load,
                "mode": interviewer.mode
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
            interviewers=interviewers_data,  # New structure
            availability_windows=availability_data,
            busy_intervals=busy_intervals_data,
            time_step_minutes=request.time_step_minutes,
            weekly_limit=request.weekly_limit,
            max_time_seconds=request.max_time_seconds,
            require_distinct_days=request.require_distinct_days,
            top_k_solutions=request.top_k_solutions,
            schedule_on_same_day=request.schedule_on_same_day,
            daily_availability_start=request.daily_availability_start,
            daily_availability_end=request.daily_availability_end,
            min_gap_between_stages=request.min_gap_between_stages
        )
        
        # Generate schedules using the two-phase approach (now the default)
        result = scheduler.solve_with_two_phase_approach()
        
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