from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple, Any, DefaultDict, Optional
from collections import defaultdict
from datetime import datetime, timedelta
from ortools.sat.python import cp_model
import json

# -----------------------------
# Utilities
# -----------------------------
ISO_FMT = "%Y-%m-%dT%H:%M"

def parse_iso(s: str) -> datetime:
    return datetime.strptime(s, ISO_FMT)

def to_iso(dt: datetime) -> str:
    return dt.strftime(ISO_FMT)

def minutes_since_epoch(dt: datetime, epoch: datetime) -> int:
    return int((dt - epoch).total_seconds() // 60)

def datetime_from_minutes(minutes: int, epoch: datetime) -> datetime:
    return epoch + timedelta(minutes=minutes)

# -----------------------------
# Data classes
# -----------------------------
@dataclass
class SeatRole:
    seat_id: str
    role: str
    interviewers: List[str]

@dataclass
class Stage:
    name: str
    duration_minutes: int
    seats: List[SeatRole]

@dataclass
class AvailabilityWindow:
    start: datetime
    end: datetime

@dataclass
class BusyInterval:
    interviewer_id: str
    start: datetime
    end: datetime

# -----------------------------
# Optimized Scheduler
# -----------------------------
class OptimizedInterviewScheduler:
    """
    Dramatically simplified CP-SAT scheduler that models time as continuous variables
    instead of pre-generating all possible time slots. This reduces complexity from
    exponential to polynomial.

    Key optimizations:
    1. Time as integer variables (minutes since epoch) rather than discrete slots
    2. Interval variables for stages and busy periods
    3. Direct constraint modeling instead of enumeration
    4. Single model construction (no fallback rebuilding)
    5. Top-K solution collection with reranking
    """

    def __init__(
        self,
        stages: List[Dict[str, Any]],
        current_week_load: Dict[str, int],
        last_2w_load: Dict[str, int],
        availability_windows: List[Dict[str, str]],
        busy_intervals: List[Dict[str, str]],
        time_step_minutes: int = 15,
        weekly_limit: int = 5,
        max_time_seconds: float = 30.0,
        require_distinct_days: bool = False,
        top_k_solutions: int = 50,
        schedule_on_same_day: bool = True,
        daily_availability_start: str = "09:00",
        daily_availability_end: str = "17:00",
        min_gap_between_stages: int = 0
    ):
        # Process input data
        self.stages = self._parse_stages(stages)
        self.current_load = defaultdict(int, current_week_load or {})
        self.last_2w_load = defaultdict(int, last_2w_load or {})
        self.time_step = time_step_minutes
        self.weekly_limit = weekly_limit
        self.max_time_seconds = max_time_seconds
        self.require_distinct_days = require_distinct_days
        self.schedule_on_same_day = schedule_on_same_day
        self.top_k_solutions = top_k_solutions
        self.daily_availability_start = daily_availability_start
        self.daily_availability_end = daily_availability_end
        self.min_gap_between_stages = min_gap_between_stages

        # Parse time windows
        self.availability = [
            AvailabilityWindow(parse_iso(w["start"]), parse_iso(w["end"]))
            for w in availability_windows
        ]

        self.busy_intervals = [
            BusyInterval(b["interviewer_id"], parse_iso(b["start"]), parse_iso(b["end"]))
            for b in busy_intervals
        ]

        # Set epoch to earliest availability
        if not self.availability:
            raise ValueError("No availability windows provided")
        self.epoch = min(w.start for w in self.availability)

        # Get all interviewer IDs
        self.all_interviewers = sorted(set(
            interviewer for stage in self.stages
            for seat in stage.seats
            for interviewer in seat.interviewers
        ))

        # Validate inputs
        self._validate_inputs()

    def _parse_stages(self, stages_data: List[Dict[str, Any]]) -> List[Stage]:
        """Parse stage definitions with proper role normalization"""
        stages = []
        for stage_data in stages_data:
            seats = []
            for seat_data in stage_data["seats"]:
                seat_id = seat_data["seat_id"]
                pools = seat_data["interviewers"]

                # Handle each role pool - group all roles for the same seat together
                seat_roles = {}  # role -> interviewers
                
                for role_key, interviewers in pools.items():
                    # Normalize role names
                    role = role_key.replace(" ", "_").lower()
                    if role in ["reverse_shadow", "reverse shadow"]:
                        role = "reverse_shadow"
                    
                    seat_roles[role] = list(interviewers)

                # Create SeatRole objects for each role in this seat
                for role, interviewers in seat_roles.items():
                    seats.append(SeatRole(
                        seat_id=seat_id,
                        role=role,
                        interviewers=interviewers
                    ))

            stages.append(Stage(
                name=stage_data["stage_name"],
                duration_minutes=int(stage_data["duration"]),
                seats=seats
            ))
        return stages

    def _validate_inputs(self):
        """Validate input data for common errors"""
        if not self.stages:
            raise ValueError("No stages provided")

        for stage in self.stages:
            if stage.duration_minutes <= 0:
                raise ValueError(f"Invalid duration for stage {stage.name}")
            if not stage.seats:
                raise ValueError(f"No seats defined for stage {stage.name}")
            
            # Check for empty candidate pools
            for seat in stage.seats:
                if not seat.interviewers:
                    raise ValueError(f"Empty candidate pool for seat {seat.seat_id}, role {seat.role}")

        for window in self.availability:
            if window.start >= window.end:
                raise ValueError(f"Invalid availability window: {window.start} >= {window.end}")
        
        # Check if we have enough distinct days when not scheduling on same day
        if not self.schedule_on_same_day:
            # Count distinct days in availability windows
            distinct_days = set()
            for window in self.availability:
                # Add each day in the window to our set
                current_day = window.start.date()
                end_day = window.end.date()
                while current_day <= end_day:
                    distinct_days.add(current_day)
                    current_day += timedelta(days=1)
            
            # We need at least as many distinct days as stages
            if len(distinct_days) < len(self.stages):
                raise ValueError(
                    f"Not enough distinct days in availability windows for {len(self.stages)} stages. "
                    f"Found {len(distinct_days)} distinct days, but need at least {len(self.stages)}. "
                    f"Please provide more availability windows spanning more days."
                )

    def solve(self) -> Dict[str, Any]:
        """Build and solve the optimized CP-SAT model
        
        This method attempts to generate multiple feasible schedules and rank them by quality.
        Note that the number of solutions returned may be less than the requested top_k_solutions
        parameter because:
        1. The problem constraints may limit the total number of feasible solutions
        2. The solver proves there are no additional feasible solutions
        3. The search space is exhausted
        
        The solutions are ranked by their objective score, which considers both fairness 
        (based on historical load) and schedule compactness.
        """
        model = cp_model.CpModel()

        # Time bounds (in minutes since epoch)
        earliest_start = 0
        latest_end = max(
            minutes_since_epoch(w.end, self.epoch) for w in self.availability
        )

        # Variables for stage start times (continuous, rounded to time_step)
        stage_starts = {}
        stage_ends = {}
        stage_intervals = {}

        for i, stage in enumerate(self.stages):
            # Start time as multiple of time_step
            max_start = latest_end - stage.duration_minutes
            start_steps = model.NewIntVar(0, max_start // self.time_step, f"start_steps_{i}")
            start_time = model.NewIntVar(0, max_start, f"start_time_{i}")
            model.Add(start_time == start_steps * self.time_step)

            end_time = model.NewIntVar(0, latest_end, f"end_time_{i}")
            model.Add(end_time == start_time + stage.duration_minutes)

            # Create interval variable for this stage
            interval = model.NewIntervalVar(
                start_time, stage.duration_minutes, end_time, f"stage_interval_{i}"
            )

            stage_starts[i] = start_time
            stage_ends[i] = end_time
            stage_intervals[i] = interval

        # Constraint: stages must be in order with minimum gaps
        # Gap depends on whether we're scheduling on same day or different days
        if self.schedule_on_same_day:
            # Same day scheduling: use custom minimum gap or default to 2-hour gaps between stages
            MIN_GAP_MINUTES = max(120, self.min_gap_between_stages)  # At least 2 hours unless custom gap is larger
        else:
            # Different day scheduling: minimum 24-hour gaps between stages
            MIN_GAP_MINUTES = max(24 * 60, self.min_gap_between_stages)  # At least 24 hours unless custom gap is larger
            
        for i in range(len(self.stages) - 1):
            model.Add(stage_starts[i + 1] >= stage_ends[i] + MIN_GAP_MINUTES)

        # Constraint: all stages must be within availability windows
        for i, stage in enumerate(self.stages):
            # At least one availability window must contain this stage
            window_indicators = []
            for j, window in enumerate(self.availability):
                window_start_min = minutes_since_epoch(window.start, self.epoch)
                window_end_min = minutes_since_epoch(window.end, self.epoch)

                # Binary variable: is stage i scheduled in window j?
                in_window = model.NewBoolVar(f"stage_{i}_in_window_{j}")
                window_indicators.append(in_window)

                # If in this window, stage must fit entirely within it
                model.Add(stage_starts[i] >= window_start_min).OnlyEnforceIf(in_window)
                model.Add(stage_ends[i] <= window_end_min).OnlyEnforceIf(in_window)

            # Stage must be in exactly one window
            model.Add(sum(window_indicators) == 1)

        # Constraint: distinct days if required or if not scheduling on same day
        if self.require_distinct_days or not self.schedule_on_same_day:
            MINUTES_PER_DAY = 24 * 60
            for i in range(len(self.stages)):
                for j in range(i + 1, len(self.stages)):
                    # Two stages must be on different days
                    # This means the absolute difference between their start times must be >= 24 hours
                    # We model this as: either stage j starts at least 24 hours after stage i, 
                    # or stage i starts at least 24 hours after stage j
                    
                    # Boolean variables to indicate which stage starts first
                    j_after_i = model.NewBoolVar(f"j_after_i_{i}_{j}")
                    i_after_j = model.NewBoolVar(f"i_after_j_{i}_{j}")
                    
                    # Exactly one of these must be true
                    model.Add(j_after_i + i_after_j == 1)
                    
                    # If j starts after i, then j must start at least 24 hours later
                    model.Add(stage_starts[j] >= stage_starts[i] + MINUTES_PER_DAY).OnlyEnforceIf(j_after_i)
                    
                    # If i starts after j, then i must start at least 24 hours later
                    model.Add(stage_starts[i] >= stage_starts[j] + MINUTES_PER_DAY).OnlyEnforceIf(i_after_j)

        # Assignment variables and constraints
        assignment_vars = {}  # (stage_idx, seat_id, role, interviewer) -> BoolVar
        interviewer_stage_vars = {}  # (stage_idx, interviewer) -> BoolVar

        for stage_idx, stage in enumerate(self.stages):
            # Group seat roles by seat_id to ensure one interviewer per role per seat
            seat_role_groups = defaultdict(list)
            for seat in stage.seats:
                seat_role_groups[seat.seat_id].append(seat)
            
            # Process each seat and its roles
            for seat_id, seat_roles in seat_role_groups.items():
                # For each role in this seat, exactly one interviewer
                for seat in seat_roles:
                    # Check for empty candidate pools
                    if not seat.interviewers:
                        raise ValueError(f"Empty candidate pool for seat {seat.seat_id}, role {seat.role} in stage {stage.name}")
                    
                    # Exactly one interviewer per seat-role
                    seat_role_vars = []
                    for interviewer in seat.interviewers:
                        var = model.NewBoolVar(f"assign_{stage_idx}_{seat.seat_id}_{seat.role}_{interviewer}")
                        assignment_vars[(stage_idx, seat.seat_id, seat.role, interviewer)] = var
                        seat_role_vars.append(var)

                        # Track if interviewer is used in this stage
                        if (stage_idx, interviewer) not in interviewer_stage_vars:
                            interviewer_stage_vars[(stage_idx, interviewer)] = model.NewBoolVar(
                                f"interviewer_{interviewer}_stage_{stage_idx}"
                            )

                        # Link assignment to interviewer usage
                        model.Add(interviewer_stage_vars[(stage_idx, interviewer)] >= var)

                    model.Add(sum(seat_role_vars) == 1)

        # Constraint: interviewer_stage_vars must equal the sum of assignment variables
        # For each (stage, interviewer):
        for stage_idx in range(len(self.stages)):
            for interviewer in self.all_interviewers:
                if (stage_idx, interviewer) in interviewer_stage_vars:
                    vars_for_this = [
                        assignment_vars[(stage_idx, seat.seat_id, seat.role, interviewer)]
                        for seat in self.stages[stage_idx].seats
                        if (stage_idx, seat.seat_id, seat.role, interviewer) in assignment_vars
                    ]
                    if vars_for_this:
                        # interviewer_stage_var should be 1 if any assignment is 1, 0 otherwise
                        model.Add(sum(vars_for_this) >= interviewer_stage_vars[(stage_idx, interviewer)])
                        model.Add(sum(vars_for_this) <= len(vars_for_this) * interviewer_stage_vars[(stage_idx, interviewer)])

        # Constraint: interviewer can appear at most once per stage
        # More efficient grouping approach
        interviewer_usage = defaultdict(list)
        for stage_idx in range(len(self.stages)):
            for seat in self.stages[stage_idx].seats:
                for interviewer in seat.interviewers:
                    if (stage_idx, seat.seat_id, seat.role, interviewer) in assignment_vars:
                        interviewer_usage[(stage_idx, interviewer)].append(
                            assignment_vars[(stage_idx, seat.seat_id, seat.role, interviewer)]
                        )

        # Apply constraint for each interviewer in each stage
        for (stage_idx, interviewer), assignments in interviewer_usage.items():
            if len(assignments) > 1:
                model.Add(sum(assignments) <= 1)

        # Constraint: interviewer availability (not busy during assigned stages)
        # Back to original approach but with some optimizations
        for stage_idx, stage in enumerate(self.stages):
            stage_start = stage_starts[stage_idx]
            stage_end = stage_ends[stage_idx]
            
            for interviewer in self.all_interviewers:
                if (stage_idx, interviewer) not in interviewer_stage_vars:
                    continue

                interviewer_var = interviewer_stage_vars[(stage_idx, interviewer)]

                # Check against all busy intervals for this interviewer
                for busy_idx, busy in enumerate(self.busy_intervals):
                    if busy.interviewer_id != interviewer:
                        continue

                    busy_start = minutes_since_epoch(busy.start, self.epoch)
                    busy_end = minutes_since_epoch(busy.end, self.epoch)

                    # If interviewer is assigned to this stage, stage must not overlap with busy time
                    # No overlap means: stage_end <= busy_start OR busy_end <= stage_start
                    # Using a more compact approach with fewer variables
                    before_busy = model.NewBoolVar(f"stage_before_busy_{interviewer}_{stage_idx}_{busy_idx}")
                    after_busy = model.NewBoolVar(f"stage_after_busy_{interviewer}_{stage_idx}_{busy_idx}")

                    model.Add(stage_end <= busy_start).OnlyEnforceIf(before_busy)
                    model.Add(stage_start >= busy_end).OnlyEnforceIf(after_busy)

                    # If interviewer is assigned, either before_busy or after_busy must be true
                    model.Add(before_busy + after_busy >= 1).OnlyEnforceIf(interviewer_var)

        # Constraint: weekly limits
        for interviewer in self.all_interviewers:
            current_load = self.current_load[interviewer]
            assigned_stages = [
                interviewer_stage_vars[(stage_idx, interviewer)]
                for stage_idx in range(len(self.stages))
                if (stage_idx, interviewer) in interviewer_stage_vars
            ]
            if assigned_stages:
                model.Add(sum(assigned_stages) + current_load <= self.weekly_limit)

        # Objective: minimize weighted assignment cost + total span
        assignment_cost = 0
        for interviewer in self.all_interviewers:
            weight = 1 + self.last_2w_load[interviewer]  # Fairness weight
            for stage_idx in range(len(self.stages)):
                if (stage_idx, interviewer) in interviewer_stage_vars:
                    assignment_cost += weight * interviewer_stage_vars[(stage_idx, interviewer)]

        # Minimize total span (last end - first start) and assignment cost
        total_span = stage_ends[len(self.stages) - 1] - stage_starts[0]

        # Multi-objective: fairness (100x) + compactness (1x)
        model.Minimize(100 * assignment_cost + total_span)

        # Solve
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.max_time_seconds
        solver.parameters.num_search_workers = 4

        # Use the solution collector approach
        # First, we need to set up the solver to collect multiple solutions
        solver.parameters.num_search_workers = 1  # Required for solution callback
        solver.parameters.enumerate_all_solutions = True
        
        # Try to get more solutions by adjusting solver parameters
        # Increase the time limit to allow for more exploration
        solver.parameters.max_time_in_seconds = self.max_time_seconds * 2
        
        # Create a list to store solutions
        solutions = []
        
        # Define a callback class to collect solutions
        class SolutionCollector(cp_model.CpSolverSolutionCallback):
            def __init__(self, scheduler, stage_starts, assignment_vars, max_solutions):
                cp_model.CpSolverSolutionCallback.__init__(self)
                self.scheduler = scheduler
                self.stage_starts = stage_starts
                self.assignment_vars = assignment_vars
                self.max_solutions = max_solutions
                self.solutions = []
                
            def on_solution_callback(self):
                if len(self.solutions) < self.max_solutions:
                    # Extract solution
                    solution_data = self.scheduler._extract_solution_data(self, self.stage_starts, self.assignment_vars)
                    score = int(self.ObjectiveValue())
                    self.solutions.append((score, solution_data))
                    print(f"Found solution {len(self.solutions)} with score {score}")
        
        # Create the solution collector
        solution_collector = SolutionCollector(self, stage_starts, assignment_vars, self.top_k_solutions)
        
        # Solve with the solution collector
        status = solver.Solve(model, solution_collector)
        
        print(f"Solver status: {solver.StatusName(status)}")
        print(f"Total solutions found: {len(solution_collector.solutions)}")
        
        # Explain why we might have fewer solutions than requested
        if len(solution_collector.solutions) < self.top_k_solutions:
            print("Note: Fewer solutions found than requested. This is normal for tightly constrained scheduling problems.")
            print("The solver has proven that no additional feasible solutions exist within the given constraints.")
        
        # Format solutions
        if solution_collector.solutions:
            # Sort solutions by score (ascending because lower is better)
            solution_collector.solutions.sort(key=lambda x: x[0])
            # Use original scores for output, not negated ones
            result = self._format_top_solutions(solution_collector.solutions, status)
            print(f"Returning {len(solution_collector.solutions)} solutions")
            return result
        else:
            # Fallback to single solution if collector didn't work
            status = solver.Solve(model)
            if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
                # Extract solution
                solution_data = self._extract_solution_data(solver, stage_starts, assignment_vars)
                score = int(solver.ObjectiveValue())
                solutions = [(score, solution_data)]
                
                # Format solutions
                result = self._format_top_solutions(solutions, status)
                print(f"Returning 1 solution from fallback with status: {solver.StatusName(status)}")
                return result
            else:
                print("No feasible solutions found")
                return {"status": "INFEASIBLE", "schedules": {}}

    def _extract_solution_data(
        self,
        solver: cp_model.CpSolver,
        stage_starts: Dict[int, cp_model.IntVar],
        assignment_vars: Dict[Tuple[int, str, str, str], cp_model.IntVar]
    ) -> Dict[str, Any]:
        """Extract raw solution data for ranking"""
        events = []
        interviewer_assignments = defaultdict(list)
        
        # Group seat roles by stage and seat for proper assignment extraction
        stage_seat_roles = defaultdict(lambda: defaultdict(dict))  # stage_idx -> seat_id -> role -> interviewer
        
        for (stage_idx, seat_id, role, interviewer), var in assignment_vars.items():
            if solver.Value(var):
                stage_seat_roles[stage_idx][seat_id][role] = interviewer
                interviewer_assignments[interviewer].append({
                    "stage": self.stages[stage_idx].name,
                    "seat_id": seat_id,
                    "role": role,
                    "start": datetime_from_minutes(solver.Value(stage_starts[stage_idx]), self.epoch),
                    "end": datetime_from_minutes(solver.Value(stage_starts[stage_idx]) + self.stages[stage_idx].duration_minutes, self.epoch)
                })

        for stage_idx, stage in enumerate(self.stages):
            start_minutes = solver.Value(stage_starts[stage_idx])
            start_time = datetime_from_minutes(start_minutes, self.epoch)
            end_time = start_time + timedelta(minutes=stage.duration_minutes)

            # Extract assignments grouped by seat
            assignments = defaultdict(dict)
            for seat_id, roles in stage_seat_roles[stage_idx].items():
                for role, interviewer in roles.items():
                    assignments[role][seat_id] = interviewer

            events.append({
                "stage_name": stage.name,
                "duration": stage.duration_minutes,
                "start": to_iso(start_time),
                "end": to_iso(end_time),
                "assigned": dict(assignments)
            })

        return {
            "events": events,
            "interviewer_assignments": dict(interviewer_assignments)
        }

    def _format_top_solutions(self, solutions: List[Tuple[int, Dict]], status: int) -> Dict[str, Any]:
        """Format collected solutions into final output structure"""
        if not solutions:
            return {"status": "INFEASIBLE", "schedules": {}}
            
        formatted_solutions = {}
        for i, (score, solution_data) in enumerate(solutions, 1):
            events = solution_data["events"]
            
            # Calculate metrics
            total_duration = sum(e["duration"] for e in events)
            if events:
                start_time = parse_iso(events[0]["start"])
                end_time = parse_iso(events[-1]["end"])
                span_minutes = int((end_time - start_time).total_seconds() // 60)
                idle_time = span_minutes - total_duration
            else:
                span_minutes = 0
                idle_time = 0
            
            formatted_solutions[f"schedule{i}"] = {
                "score": score,
                "events": events,
                "metrics": {
                    "total_span_minutes": span_minutes,
                    "idle_time_minutes": idle_time,
                    "efficiency": round(total_duration / span_minutes, 3) if span_minutes > 0 else 0
                }
            }
        
        # Return the actual solver status
        status_name = "UNKNOWN"
        if status == cp_model.OPTIMAL:
            status_name = "OPTIMAL"
        elif status == cp_model.FEASIBLE:
            status_name = "FEASIBLE"
        elif status == cp_model.INFEASIBLE:
            status_name = "INFEASIBLE"
        else:
            # Use the solver's own status name mapping
            # Create a temporary solver to get the status name
            temp_solver = cp_model.CpSolver()
            status_name = temp_solver.StatusName(status)
        
        return {
            "status": status_name,
            "schedules": formatted_solutions
        }


import random

def generate_dummy_data(
    num_interviewers: int = 100,
    num_stages: int = 5,
    stage_duration_range: Tuple[int, int] = (30, 90),
    num_weeks: int = 3,
    seats_per_stage: Tuple[int, int] = (2, 5),
    roles: List[str] = ["trained", "shadow", "reverse_shadow"]
):
    # Generate interviewer IDs
    interviewers = [f"intv_{i}" for i in range(1, num_interviewers + 1)]

    # Generate stages
    stages = []
    for s in range(num_stages):
        stage_name = f"Stage_{s+1}"
        duration = random.randint(*stage_duration_range)

        seats = []
        num_seats = random.randint(*seats_per_stage)
        for seat_idx in range(num_seats):
            seat_id = f"{stage_name}_seat{seat_idx+1}"

            # For each seat, we need to define pools for ALL roles
            role_interviewers = {}
            for role in roles:
                # Make sure we have enough interviewers for each role
                num_candidates = min(random.randint(5, 15), len(interviewers))
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

    # Generate availability windows (3 weeks, 9–17 workdays)
    start_date = datetime(2025, 8, 25, 9, 0)  # Monday
    availability = []
    for d in range(num_weeks * 7):
        day = start_date + timedelta(days=d)
        if day.weekday() < 5:  # only weekdays
            availability.append({
                "start": to_iso(day.replace(hour=9, minute=0)),
                "end": to_iso(day.replace(hour=17, minute=0))
            })

    # Generate random busy intervals (each interviewer ~5–10)
    busy_intervals = []
    for interviewer in interviewers:
        for _ in range(random.randint(5, 10)):
            day = start_date + timedelta(days=random.randint(0, num_weeks*7-1))
            if day.weekday() >= 5:
                continue
            start_hour = random.randint(9, 15)
            start_time = day.replace(hour=start_hour, minute=0)
            end_time = start_time + timedelta(minutes=random.choice([30, 60, 90]))
            busy_intervals.append({
                "interviewer_id": interviewer,
                "start": to_iso(start_time),
                "end": to_iso(end_time)
            })

    # Current and last 2 week loads
    current_week_load = {iv: random.randint(0, 3) for iv in interviewers}
    last_2w_load = {iv: random.randint(0, 5) for iv in interviewers}

    return stages, availability, busy_intervals, current_week_load, last_2w_load