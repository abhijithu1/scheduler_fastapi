from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Tuple, Any, DefaultDict, Optional
from collections import defaultdict
from datetime import datetime, timedelta
from ortools.sat.python import cp_model
from itertools import permutations
import json

# -----------------------------
# Utilities
# -----------------------------

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


def generate_stage_permutations(stages: List[Stage]) -> List[List[Stage]]:
    """
    Generate all possible permutations of stages while keeping fixed stages in their positions.
    
    Args:
        stages: List of Stage objects, each with an is_fixed attribute
        
    Returns:
        List of all valid stage permutations
    """
    # Separate fixed and non-fixed stages
    fixed_stages = [(i, stage) for i, stage in enumerate(stages) if stage.is_fixed]
    non_fixed_stages = [stage for stage in stages if not stage.is_fixed]
    
    # If all stages are fixed, return the original order
    if len(fixed_stages) == len(stages):
        return [stages]
    
    # If no stages are fixed, return all permutations
    if len(fixed_stages) == 0:
        return [list(p) for p in permutations(non_fixed_stages)]
    
    # Generate permutations of non-fixed stages
    non_fixed_permutations = list(permutations(non_fixed_stages))
    
    # For each permutation of non-fixed stages, insert fixed stages at their fixed positions
    result = []
    for perm in non_fixed_permutations:
        # Create a list with None placeholders for all positions
        arrangement = [None] * len(stages)
        
        # Place fixed stages at their fixed positions
        for pos, stage in fixed_stages:
            arrangement[pos] = stage
        
        # Fill remaining positions with non-fixed stages from the permutation
        non_fixed_index = 0
        for i in range(len(arrangement)):
            if arrangement[i] is None:
                arrangement[i] = perm[non_fixed_index]
                non_fixed_index += 1
        
        result.append(arrangement)
    
    return result

# -----------------------------
# Data classes
# -----------------------------
@dataclass
class InterviewerInfo:
    id: str
    current_load: int
    last2w_load: int
    mode: str  # "trained", "shadow", or "reverse_shadow"

@dataclass
class SeatRole:
    seat_id: str
    role: str
    # Will now contain interviewer IDs that match the required mode
    interviewers: List[str]

@dataclass
class Stage:
    name: str
    duration_minutes: int
    seats: List[SeatRole]
    is_fixed: bool = False

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
# Two-Phase Optimized Scheduler
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
        interviewers: List[Dict[str, Any]],  # New structure: list of interviewer objects
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
        self.interviewers = self._parse_interviewers(interviewers)  # Parse interviewers first
        self.stages = self._parse_stages(stages)  # Then parse stages which uses interviewers
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

    def _parse_interviewers(self, interviewers_data: List[Dict[str, Any]]) -> Dict[str, InterviewerInfo]:
        """Parse interviewer definitions"""
        interviewers = {}
        for interviewer_data in interviewers_data:
            interviewer_id = interviewer_data["id"]
            interviewers[interviewer_id] = InterviewerInfo(
                id=interviewer_id,
                current_load=int(interviewer_data["current_load"]),
                last2w_load=int(interviewer_data["last2w_load"]),
                mode=interviewer_data["mode"]
            )
        return interviewers

    def _parse_stages(self, stages_data: List[Dict[str, Any]]) -> List[Stage]:
        """Parse stage definitions with proper role normalization"""
        stages = []
        for stage_data in stages_data:
            seats = []
            for seat_data in stage_data["seats"]:
                seat_id = seat_data["seat_id"]
                
                # For each seat, we need to define pools for ALL roles
                # We'll filter interviewers by mode for each role
                required_roles = ["trained", "shadow", "reverse_shadow"]
                
                for role in required_roles:
                    # Filter interviewers by mode
                    role_interviewers = [
                        interviewer.id for interviewer in self.interviewers.values() 
                        if interviewer.mode == role
                    ]
                    
                    seats.append(SeatRole(
                        seat_id=seat_id,
                        role=role,
                        interviewers=role_interviewers
                    ))

            stages.append(Stage(
                name=stage_data["stage_name"],
                duration_minutes=int(stage_data["duration"]),
                seats=seats,
                is_fixed=stage_data.get("is_fixed", False)
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
        """Build and solve the optimized CP-SAT model for all valid stage permutations
        
        This method generates all valid permutations of stages based on the is_fixed parameter,
        creates a separate optimization model for each permutation, solves them, and combines
        the solutions ranked by quality score.
        
        The solutions are ranked by their objective score, which considers both fairness 
        (based on historical load) and schedule compactness.
        """
        # Generate all valid permutations of stages
        stage_permutations = generate_stage_permutations(self.stages)
        num_permutations = len(stage_permutations)
        
        all_solutions = []
        
        # Calculate how many solutions we still need to find
        remaining_solutions = self.top_k_solutions
        
        # Solve for each permutation
        for perm_idx, perm_stages in enumerate(stage_permutations):
            print(f"Solving for permutation {perm_idx + 1}/{num_permutations}")
            
            # Get solutions for this permutation, limiting to how many we still need
            perm_solutions = self._solve_single_permutation(perm_stages, remaining_solutions)
            all_solutions.extend(perm_solutions)
            
            # Update how many more solutions we need
            remaining_solutions = max(0, self.top_k_solutions - len(all_solutions))
            
            # If we already have enough solutions, potentially stop early (depending on implementation)
            # Note: We'll still process all permutations to be thorough, but we could optimize this later
        
        # Sort all solutions by score and return top k
        all_solutions.sort(key=lambda x: x[0])
        top_solutions = all_solutions[:self.top_k_solutions]
        
        if top_solutions:
            # For now, we'll return the status of the first solution's model
            # In a more sophisticated implementation, we might want to track this better
            return self._format_top_solutions(top_solutions, cp_model.OPTIMAL)
        else:
            return {"status": "INFEASIBLE", "schedules": {}}

    def solve_with_two_phase_approach(self) -> Dict[str, Any]:
        """
        Two-phase scheduling approach (now the default approach):
        
        Phase 1: Generate initial schedule using only trained interviewers
        Phase 2: Enrich the existing schedule with shadowers and reverse shadowers
        """
        print("Starting Phase 1: Initial schedule with trained interviewers only")
        
        # Create a modified version of stages that only includes seats relevant for trained interviewers
        original_stages = self.stages
        temp_stages = []
        
        for stage in self.stages:
            # Create new seats list with only unique seat_ids (for trained interviewers)
            # Group seats by seat_id to avoid duplicates, but only consider trained roles
            seat_id_to_trained_interviewers = {}
            for seat in stage.seats:
                if seat.role == "trained":
                    if seat.seat_id not in seat_id_to_trained_interviewers:
                        seat_id_to_trained_interviewers[seat.seat_id] = []
                    seat_id_to_trained_interviewers[seat.seat_id].extend(seat.interviewers)
            
            # Create SeatRole objects for the phase 1 with only trained interviewers
            trained_seats = []
            for seat_id, trained_interviewers in seat_id_to_trained_interviewers.items():
                trained_seats.append(SeatRole(
                    seat_id=seat_id,
                    role="trained",  # Only marked as trained for this phase
                    interviewers=trained_interviewers
                ))
            
            temp_stage = Stage(
                name=stage.name,
                duration_minutes=stage.duration_minutes,
                seats=trained_seats,
                is_fixed=stage.is_fixed
            )
            temp_stages.append(temp_stage)
        
        # Temporarily replace stages for phase 1
        self.stages = temp_stages
        
        # Create filtered interviewers (only trained)
        original_interviewers = self.interviewers
        filtered_interviewers = {
            iv_id: iv_info for iv_id, iv_info in self.interviewers.items() 
            if iv_info.mode == "trained"
        }
        
        # Update all_interviewers to match filtered ones
        original_all_interviewers = self.all_interviewers
        self.interviewers = filtered_interviewers
        self.all_interviewers = sorted(filtered_interviewers.keys())
        
        # Solve for initial schedules with trained interviewers only
        phase1_result = self.solve()
        
        # Restore original data after phase 1
        self.stages = original_stages
        self.interviewers = original_interviewers
        self.all_interviewers = original_all_interviewers
        
        if phase1_result["status"] not in ["OPTIMAL", "FEASIBLE"]:
            return {"status": "INFEASIBLE", "schedules": {}}
        
        # Get ALL schedules from phase 1, not just the best one
        phase1_schedules = phase1_result.get("schedules", {})
        
        if not phase1_schedules:
            return {"status": "INFEASIBLE", "schedules": {}}
        
        # Phase 2: Enrich ALL schedules with shadowers and reverse shadowers
        print("Starting Phase 2: Enriching schedules with shadowers and reverse shadowers")
        enriched_schedules = {}
        
        # Process each schedule from phase 1
        for schedule_key, initial_schedule in phase1_schedules.items():
            enriched_schedule = self._enrich_schedule_with_shadowers(initial_schedule)
            
            # Get the enriched schedule from the returned dict
            if "schedules" in enriched_schedule and enriched_schedule["schedules"]:
                # Use the same key to maintain consistency
                for enriched_key, enriched_data in enriched_schedule["schedules"].items():
                    enriched_schedules[schedule_key] = enriched_data
            else:
                # If enrichment failed for some reason, keep the original
                enriched_schedules[schedule_key] = initial_schedule
        
        # Return all enriched schedules
        return {
            "status": phase1_result["status"],
            "schedules": enriched_schedules
        }

    def _get_best_schedule(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """Extract the best schedule from the result"""
        if result["schedules"]:
            # Get the schedule with the lowest score (best)
            best_schedule_key = min(result["schedules"].keys(), 
                                  key=lambda k: result["schedules"][k]["score"])
            best_schedule = result["schedules"][best_schedule_key]
            best_schedule["schedule_key"] = best_schedule_key
            return best_schedule
        return {}
    
    def _enrich_schedule_with_shadowers(self, initial_schedule: Dict[str, Any]) -> Dict[str, Any]:
        """Enrich the initial schedule with shadowers and reverse shadowers"""
        # Create a deep copy of the initial schedule
        import copy
        enriched_schedule = copy.deepcopy(initial_schedule)
        
        # Get all the shadowers and reverse shadowers from the original data
        shadowers = {iv_id: iv_info for iv_id, iv_info in self.interviewers.items() 
                     if iv_info.mode in ["shadow", "reverse_shadow"]}
        
        # Extract busy intervals per interviewer to respect their availability
        iv_busy_intervals = defaultdict(list)
        for busy_interval in self.busy_intervals:
            iv_busy_intervals[busy_interval.interviewer_id].append(busy_interval)
        
        # Go through each event in the schedule and try to assign shadowers and reverse shadowers
        for event_idx, event in enumerate(enriched_schedule.get("events", [])):
            stage_name = event["stage_name"]
            event_start = parse_iso(event["start"])
            event_end = parse_iso(event["end"])
            
            # Find all available shadowers and reverse shadowers for this time slot
            available_shadowers = self._find_available_interviewers(
                shadowers, 
                event_start, 
                event_end, 
                iv_busy_intervals
            )
            
            # Add shadowers and reverse shadowers to the event assignments
            for role in ["shadow", "reverse_shadow"]:
                # Get role-specific available interviewers
                role_available = {iv_id: iv_info for iv_id, iv_info in available_shadowers.items() 
                                if iv_info.mode == role}
                
                # Get all seats that currently have trained interviewers
                trained_assignments = event.get("assigned", {}).get("trained", {})
                
                # Assign one shadower/reverse shadower per seat if possible
                for seat_id in trained_assignments.keys():
                    if role_available and seat_id not in event.get("assigned", {}).get(role, {}):
                        # Assign one available interviewer to this seat
                        assigned_iv = next(iter(role_available.keys()))  # Get first key
                        del role_available[assigned_iv]  # Remove from available
                        
                        if role not in event["assigned"]:
                            event["assigned"][role] = {}
                        event["assigned"][role][seat_id] = assigned_iv
        
        return {
            "status": "OPTIMAL",
            "schedules": {"schedule1": enriched_schedule}
        }
    
    def _find_available_interviewers(self, interviewers: Dict[str, InterviewerInfo], 
                                   event_start: datetime, event_end: datetime,
                                   iv_busy_intervals: DefaultDict[str, List[BusyInterval]]) -> Dict[str, InterviewerInfo]:
        """Find interviewers that are available during the specified time slot"""
        available = {}
        for iv_id, iv_info in interviewers.items():
            # Check if the interviewer is busy during this time slot
            is_available = True
            for busy_interval in iv_busy_intervals.get(iv_id, []):
                # Check for overlap between event and busy interval
                if not (event_end <= busy_interval.start or busy_interval.end <= event_start):
                    is_available = False
                    break
            
            if is_available:
                available[iv_id] = iv_info
        
        return available

    
    
    def _solve_single_permutation(self, perm_stages: List[Stage], max_solutions_needed: int) -> List[Tuple[int, Dict]]:
        """Solve a single permutation of stages and return solutions"""
        # Find the primary optimal solution first
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

        for i, stage in enumerate(perm_stages):
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
            
        for i in range(len(perm_stages) - 1):
            model.Add(stage_starts[i + 1] >= stage_ends[i] + MIN_GAP_MINUTES)

        # Constraint: all stages must be within availability windows
        for i, stage in enumerate(perm_stages):
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
            for i in range(len(perm_stages)):
                for j in range(i + 1, len(perm_stages)):
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

        for stage_idx, stage in enumerate(perm_stages):
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
                    for interviewer_id in seat.interviewers:
                        var = model.NewBoolVar(f"assign_{stage_idx}_{seat.seat_id}_{seat.role}_{interviewer_id}")
                        assignment_vars[(stage_idx, seat.seat_id, seat.role, interviewer_id)] = var
                        seat_role_vars.append(var)

                        # Track if interviewer is used in this stage
                        if (stage_idx, interviewer_id) not in interviewer_stage_vars:
                            interviewer_stage_vars[(stage_idx, interviewer_id)] = model.NewBoolVar(
                                f"interviewer_{interviewer_id}_stage_{stage_idx}"
                            )

                        # Link assignment to interviewer usage
                        model.Add(interviewer_stage_vars[(stage_idx, interviewer_id)] >= var)

                    model.Add(sum(seat_role_vars) == 1)

        # Constraint: interviewer_stage_vars must equal the sum of assignment variables
        # For each (stage, interviewer):
        for stage_idx in range(len(perm_stages)):
            for interviewer_id in self.all_interviewers:
                if (stage_idx, interviewer_id) in interviewer_stage_vars:
                    vars_for_this = [
                        assignment_vars[(stage_idx, seat.seat_id, seat.role, interviewer_id)]
                        for seat in perm_stages[stage_idx].seats
                        if (stage_idx, seat.seat_id, seat.role, interviewer_id) in assignment_vars
                    ]
                    if vars_for_this:
                        # interviewer_stage_var should be 1 if any assignment is 1, 0 otherwise
                        model.Add(sum(vars_for_this) >= interviewer_stage_vars[(stage_idx, interviewer_id)])
                        model.Add(sum(vars_for_this) <= len(vars_for_this) * interviewer_stage_vars[(stage_idx, interviewer_id)])

        # Constraint: interviewer can appear at most once per stage
        # More efficient grouping approach
        interviewer_usage = defaultdict(list)
        for stage_idx in range(len(perm_stages)):
            for seat in perm_stages[stage_idx].seats:
                for interviewer_id in seat.interviewers:
                    if (stage_idx, seat.seat_id, seat.role, interviewer_id) in assignment_vars:
                        interviewer_usage[(stage_idx, interviewer_id)].append(
                            assignment_vars[(stage_idx, seat.seat_id, seat.role, interviewer_id)]
                        )

        # Apply constraint for each interviewer in each stage
        for (stage_idx, interviewer_id), assignments in interviewer_usage.items():
            if len(assignments) > 1:
                model.Add(sum(assignments) <= 1)

        # Constraint: interviewer availability (not busy during assigned stages)
        # Back to original approach but with some optimizations
        for stage_idx, stage in enumerate(perm_stages):
            stage_start = stage_starts[stage_idx]
            stage_end = stage_ends[stage_idx]
            
            for interviewer_id in self.all_interviewers:
                if (stage_idx, interviewer_id) not in interviewer_stage_vars:
                    continue

                interviewer_var = interviewer_stage_vars[(stage_idx, interviewer_id)]

                # Check against all busy intervals for this interviewer
                for busy_idx, busy in enumerate(self.busy_intervals):
                    if busy.interviewer_id != interviewer_id:
                        continue

                    busy_start = minutes_since_epoch(busy.start, self.epoch)
                    busy_end = minutes_since_epoch(busy.end, self.epoch)

                    # If interviewer is assigned to this stage, stage must not overlap with busy time
                    # No overlap means: stage_end <= busy_start OR busy_end <= stage_start
                    # Using a more compact approach with fewer variables
                    before_busy = model.NewBoolVar(f"stage_before_busy_{interviewer_id}_{stage_idx}_{busy_idx}")
                    after_busy = model.NewBoolVar(f"stage_after_busy_{interviewer_id}_{stage_idx}_{busy_idx}")

                    model.Add(stage_end <= busy_start).OnlyEnforceIf(before_busy)
                    model.Add(stage_start >= busy_end).OnlyEnforceIf(after_busy)

                    # If interviewer is assigned, either before_busy or after_busy must be true
                    model.Add(before_busy + after_busy >= 1).OnlyEnforceIf(interviewer_var)

        # Constraint: weekly limits
        for interviewer_id in self.all_interviewers:
            interviewer_info = self.interviewers.get(interviewer_id)
            if interviewer_info:
                current_load = interviewer_info.current_load
                assigned_stages = [
                    interviewer_stage_vars[(stage_idx, interviewer_id)]
                    for stage_idx in range(len(perm_stages))
                    if (stage_idx, interviewer_id) in interviewer_stage_vars
                ]
                if assigned_stages:
                    model.Add(sum(assigned_stages) + current_load <= self.weekly_limit)

        # Objective: minimize weighted assignment cost + total span
        assignment_cost = 0
        for interviewer_id in self.all_interviewers:
            interviewer_info = self.interviewers.get(interviewer_id)
            if interviewer_info:
                weight = 1 + interviewer_info.last2w_load  # Fairness weight
                for stage_idx in range(len(perm_stages)):
                    if (stage_idx, interviewer_id) in interviewer_stage_vars:
                        assignment_cost += weight * interviewer_stage_vars[(stage_idx, interviewer_id)]

        # Minimize total span (last end - first start) and assignment cost
        total_span = stage_ends[len(perm_stages) - 1] - stage_starts[0]

        # Multi-objective: fairness (100x) + compactness (1x)
        model.Minimize(100 * assignment_cost + total_span)

        # Try to find multiple diverse solutions using iterative approach
        all_solutions = []
        objective_values = set()  # Keep track of unique objective values found
        num_solutions_found = 0
        
        # First, try using the solution callback approach
        solver = cp_model.CpSolver()
        solver.parameters.max_time_in_seconds = self.max_time_seconds
        solver.parameters.num_search_workers = 1  # Required for solution callback
        solver.parameters.enumerate_all_solutions = True
        
        # Try to get more solutions by adjusting solver parameters
        # Increase the time limit to allow for more exploration
        solver.parameters.max_time_in_seconds = self.max_time_seconds * 2
        
        # Define a callback class to collect solutions
        class SolutionCollector(cp_model.CpSolverSolutionCallback):
            def __init__(self, scheduler, stage_starts, assignment_vars, max_solutions_needed):
                cp_model.CpSolverSolutionCallback.__init__(self)
                self.scheduler = scheduler
                self.stage_starts = stage_starts
                self.assignment_vars = assignment_vars
                self.max_solutions_needed = max_solutions_needed
                self.solutions = []
                
            def on_solution_callback(self):
                if len(self.solutions) < self.max_solutions_needed:
                    # Extract solution
                    solution_data = self.scheduler._extract_solution_data_perm(self, self.stage_starts, self.assignment_vars, perm_stages)
                    score = int(self.ObjectiveValue())
                    self.solutions.append((score, solution_data))
                    print(f"Found solution {len(self.solutions)} with score {score}")
        
        # Create the solution collector
        solution_collector = SolutionCollector(self, stage_starts, assignment_vars, max_solutions_needed)
        
        # Solve with the solution collector
        status = solver.Solve(model, solution_collector)
        
        print(f"Initial solver status: {solver.StatusName(status)}")
        print(f"Initial solutions found: {len(solution_collector.solutions)}")
        
        # If we found solutions with the callback, use those
        if solution_collector.solutions:
            all_solutions.extend(solution_collector.solutions)
            num_solutions_found = len(solution_collector.solutions)
        else:
            # If callback didn't work well, try the single solution approach
            solver = cp_model.CpSolver()
            status = solver.Solve(model)
            
            if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
                solution_data = self._extract_solution_data_perm(solver, stage_starts, assignment_vars, perm_stages)
                score = int(solver.ObjectiveValue())
                all_solutions.append((score, solution_data))
                print(f"Found solution {len(all_solutions)} with score {score}")
                num_solutions_found = 1
        
        print(f"Total solutions found for this permutation: {len(all_solutions)}")
        return all_solutions

    def _extract_solution_data_perm(
        self,
        solver: cp_model.CpSolver,
        stage_starts: Dict[int, cp_model.IntVar],
        assignment_vars: Dict[Tuple[int, str, str, str], cp_model.IntVar],
        perm_stages: List[Stage]
    ) -> Dict[str, Any]:
        """Extract raw solution data for ranking from a specific permutation"""
        events = []
        interviewer_assignments = defaultdict(list)
        
        # Group seat roles by stage and seat for proper assignment extraction
        stage_seat_roles = defaultdict(lambda: defaultdict(dict))  # stage_idx -> seat_id -> role -> interviewer
        
        for (stage_idx, seat_id, role, interviewer_id), var in assignment_vars.items():
            if solver.Value(var):
                stage_seat_roles[stage_idx][seat_id][role] = interviewer_id
                interviewer_assignments[interviewer_id].append({
                    "stage": perm_stages[stage_idx].name,
                    "seat_id": seat_id,
                    "role": role,
                    "start": datetime_from_minutes(solver.Value(stage_starts[stage_idx]), self.epoch),
                    "end": datetime_from_minutes(solver.Value(stage_starts[stage_idx]) + perm_stages[stage_idx].duration_minutes, self.epoch)
                })

        for stage_idx, stage in enumerate(perm_stages):
            start_minutes = solver.Value(stage_starts[stage_idx])
            start_time = datetime_from_minutes(start_minutes, self.epoch)
            end_time = start_time + timedelta(minutes=stage.duration_minutes)

            # Extract assignments grouped by seat
            assignments = defaultdict(dict)
            for seat_id, roles in stage_seat_roles[stage_idx].items():
                for role, interviewer_id in roles.items():
                    assignments[role][seat_id] = interviewer_id

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
        
        for (stage_idx, seat_id, role, interviewer_id), var in assignment_vars.items():
            if solver.Value(var):
                stage_seat_roles[stage_idx][seat_id][role] = interviewer_id
                interviewer_assignments[interviewer_id].append({
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
                for role, interviewer_id in roles.items():
                    assignments[role][seat_id] = interviewer_id

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
    interviewer_names = [f"intv_{i}" for i in range(1, num_interviewers + 1)]
    
    # Generate interviewer data with attributes
    interviewers_data = []
    for i, name in enumerate(interviewer_names):
        # Assign a random mode to each interviewer
        mode = random.choice(roles)
        interviewers_data.append({
            "id": name,
            "current_load": random.randint(0, 3),
            "last2w_load": random.randint(0, 5),
            "mode": mode
        })

    # Generate stages
    stages = []
    for s in range(num_stages):
        stage_name = f"Stage_{s+1}"
        duration = random.randint(*stage_duration_range)

        seats = []
        num_seats = random.randint(*seats_per_stage)
        for seat_idx in range(num_seats):
            seat_id = f"{stage_name}_seat{seat_idx+1}"
            
            # In the new structure, we don't need to specify interviewers per seat
            # The scheduler will filter by mode
            seats.append({
                "seat_id": seat_id
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
    for interviewer in interviewer_names:
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

    return stages, interviewers_data, availability, busy_intervals