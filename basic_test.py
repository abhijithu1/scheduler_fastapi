#!/usr/bin/env python3
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scheduler import OptimizedInterviewScheduler, generate_dummy_data

print("Testing imports...")

# Generate minimal dummy data for fast testing
print("Generating minimal dummy data...")
stages, interviewers, availability, busy_intervals = generate_dummy_data(
    num_interviewers=6,  # Very small dataset
    num_stages=2,
    seats_per_stage=(1, 1),  # Only 1 seat per stage
    roles=["trained", "shadow", "reverse_shadow"]
)

print(f"Generated: {len(stages)} stages, {len(interviewers)} interviewers")

# Count interviewers by role
trained_count = sum(1 for iv in interviewers if iv["mode"] == "trained")
shadow_count = sum(1 for iv in interviewers if iv["mode"] == "shadow")
reverse_shadow_count = sum(1 for iv in interviewers if iv["mode"] == "reverse_shadow")

print(f"  - Trained: {trained_count}, Shadow: {shadow_count}, Reverse Shadow: {reverse_shadow_count}")

# Create scheduler with minimal constraints
print("Creating scheduler...")
scheduler = OptimizedInterviewScheduler(
    stages=stages,
    interviewers=interviewers,
    availability_windows=availability,
    busy_intervals=busy_intervals,
    max_time_seconds=5.0,  # Shorter time limit for testing
    weekly_limit=10  # Higher limit to make it easier to find solutions
)
print("Scheduler created successfully")

# Test that the new methods exist
print("Checking for two-phase method...")
has_method = hasattr(scheduler, 'solve_with_two_phase_approach')
print(f"Has solve_with_two_phase_approach method: {has_method}")

if has_method:
    print("All tests passed!")
else:
    print("Method not found!")
    sys.exit(1)