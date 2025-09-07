import random
from datetime import datetime, timedelta
from typing import List, Tuple, Dict, Any

def generate_dummy_data(
    num_interviewers: int = 100,
    num_stages: int = 5,
    stage_duration_range: Tuple[int, int] = (30, 120),
    num_weeks: int = 3,
    seats_per_stage: Tuple[int, int] = (2, 5),
    roles: List[str] = ["trained", "shadow", "reverse_shadow"],
    # New parameters for our features
    daily_availability_start: str = "09:00",
    daily_availability_end: str = "17:00",
    min_gap_between_stages: int = 120,
    schedule_on_same_day: bool = True,
    require_distinct_days: bool = False,
    # Realistic interviewer characteristics
    busy_intervals_per_interviewer: Tuple[int, int] = (3, 8),
    busy_interval_durations: List[int] = [30, 60, 90, 120],
    # Load distribution parameters
    current_week_load_range: Tuple[int, int] = (0, 4),
    last_2w_load_range: Tuple[int, int] = (0, 8)
):
    """
    Generate realistic dummy data for testing the interview scheduler.
    
    This function creates synthetic data that mimics real-world interview scheduling scenarios,
    including interviewer availability conflicts, varying workloads, and realistic scheduling patterns.
    
    Args:
        num_interviewers: Number of interviewers to generate
        num_stages: Number of interview stages
        stage_duration_range: Range of stage durations in minutes (min, max)
        num_weeks: Number of weeks to generate availability for
        seats_per_stage: Range of seats per stage (min, max)
        roles: List of role types for each seat
        daily_availability_start: Daily start time in HH:MM format
        daily_availability_end: Daily end time in HH:MM format
        min_gap_between_stages: Minimum gap between stages in minutes
        schedule_on_same_day: Whether to prefer same-day scheduling
        require_distinct_days: Whether to require stages on different days
        busy_intervals_per_interviewer: Range of busy intervals per interviewer (min, max)
        busy_interval_durations: List of possible busy interval durations in minutes
        current_week_load_range: Range of current week loads per interviewer (min, max)
        last_2w_load_range: Range of last 2-week loads per interviewer (min, max)
        
    Returns:
        Tuple of (stages, availability, busy_intervals, current_week_load, last_2w_load)
    """
    # Generate interviewer IDs with realistic names
    first_names = ["Alex", "Maria", "James", "Emily", "Michael", "Sarah", "Robert", "Lisa", 
                   "David", "Jennifer", "William", "Amanda", "Christopher", "Ashley", "Matthew",
                   "Jessica", "Daniel", "Nicole", "Joseph", "Megan", "Thomas", "Rachel", 
                   "Andrew", "Stephanie", "Ryan", "Lauren", "Kevin", "Michelle", "Brian", 
                   "Heather", "Jason", "Samantha", "Eric", "Brittany", "Jonathan", "Amber",
                   "Jeffrey", "Danielle", "Frank", "Kimberly", "Patrick", "Rebecca", "Jacob",
                   "Angela", "Tyler", "Melissa", "Austin", "Courtney", "Zachary", "Vanessa"]
    
    last_names = ["Johnson", "Garcia", "Smith", "Chen", "Brown", "Davis", "Wilson", "Miller",
                  "Taylor", "Anderson", "Thomas", "Jackson", "White", "Harris", "Martin",
                  "Thompson", "Robinson", "Lewis", "Walker", "Hall", "Allen", "Young",
                  "King", "Wright", "Scott", "Green", "Baker", "Adams", "Nelson", "Hill",
                  "Carter", "Mitchell", "Roberts", "Turner", "Phillips", "Campbell",
                  "Parker", "Evans", "Edwards", "Collins", "Stewart", "Sanchez", "Morris",
                  "Rogers", "Reed", "Cook", "Morgan", "Bell", "Murphy", "Rivera"]
    
    # Generate unique interviewer names
    interviewers = []
    used_names = set()
    for i in range(num_interviewers):
        while True:
            first = random.choice(first_names)
            last = random.choice(last_names)
            name = f"{first} {last}"
            if name not in used_names:
                used_names.add(name)
                interviewers.append(name)
                break
        # Fallback if we run out of unique combinations
        if len(interviewers) <= i:
            interviewers.append(f"Interviewer_{i+1}")

    # Generate stages with realistic names
    stage_names = ["Initial_Tech_Screen", "Deep_Tech_Interview", "System_Design", 
                   "Behavioral_Interview", "Leadership_Round", "Cultural_Fit", "Final_Review"]
    
    stages = []
    for s in range(num_stages):
        stage_name = stage_names[s] if s < len(stage_names) else f"Stage_{s+1}"
        duration = random.randint(*stage_duration_range)

        seats = []
        num_seats = random.randint(*seats_per_stage)
        for seat_idx in range(num_seats):
            seat_id = f"{stage_name}_Room_{seat_idx+1}"

            # For each seat, we need to define pools for ALL roles
            role_interviewers = {}
            for role in roles:
                # Make sure we have enough interviewers for each role
                num_candidates = min(random.randint(3, 8), len(interviewers))
                role_interviewers[role] = random.sample(
                    interviewers,
                    k=num_candidates  # candidate pool per seat-role
                )

            seats.append({
                "seat_id": seat_id,
                "interviewers": role_interviewers
            })

        stages.append({
            "stage_name": stage_name,
            "duration": duration,
            "seats": seats
        })

    # Generate availability windows (workdays with custom hours)
    start_date = datetime(2025, 9, 1, 0, 0)  # Start of September
    availability = []
    
    # Parse daily availability times
    start_hour, start_minute = map(int, daily_availability_start.split(":"))
    end_hour, end_minute = map(int, daily_availability_end.split(":"))
    
    days_generated = 0
    current_date = start_date
    while days_generated < num_weeks * 5:  # 5 workdays per week
        if current_date.weekday() < 5:  # only weekdays
            availability.append({
                "start": current_date.replace(hour=start_hour, minute=start_minute).isoformat()[:-3],
                "end": current_date.replace(hour=end_hour, minute=end_minute).isoformat()[:-3]
            })
            days_generated += 1
        current_date += timedelta(days=1)

    # Generate realistic busy intervals
    busy_intervals = []
    for interviewer in interviewers:
        num_busy_intervals = random.randint(*busy_intervals_per_interviewer)
        # Keep track of used time slots to avoid overlaps
        used_slots = []
        
        for _ in range(num_busy_intervals):
            # Pick a random day from availability
            if availability:
                day_window = random.choice(availability)
                day_start = datetime.fromisoformat(day_window["start"])
                
                # Generate a busy interval during work hours
                work_duration = (datetime.fromisoformat(day_window["end"]) - day_start).total_seconds() / 60
                duration = random.choice(busy_interval_durations)
                
                # Make sure the interval fits in the day
                if duration <= work_duration:
                    max_start_offset = int(work_duration - duration)
                    if max_start_offset > 0:
                        start_offset = random.randint(0, max_start_offset)
                        start_time = day_start + timedelta(minutes=start_offset)
                        end_time = start_time + timedelta(minutes=duration)
                        
                        # Check for overlap with existing intervals
                        overlap = False
                        for used_start, used_end in used_slots:
                            if not (end_time <= used_start or start_time >= used_end):
                                overlap = True
                                break
                        
                        if not overlap:
                            used_slots.append((start_time, end_time))
                            busy_intervals.append({
                                "interviewer_id": interviewer,
                                "start": start_time.isoformat()[:-3],
                                "end": end_time.isoformat()[:-3]
                            })

    # Generate realistic load distributions
    current_week_load = {
        iv: random.randint(*current_week_load_range) for iv in interviewers
    }
    last_2w_load = {
        iv: random.randint(*last_2w_load_range) for iv in interviewers
    }

    return stages, availability, busy_intervals, current_week_load, last_2w_load


# Example usage:
# stages, availability, busy_intervals, current_week_load, last_2w_load = generate_dummy_data(
#     num_interviewers=50,
#     num_stages=5,
#     daily_availability_start="08:00",
#     daily_availability_end="18:00",
#     min_gap_between_stages=60,
#     schedule_on_same_day=True
# )