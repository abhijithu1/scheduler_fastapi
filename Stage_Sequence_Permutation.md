# Stage Sequence Permutation with Fixed Positions

## Overview

This document explains the new `is_fixed` parameter that has been added to the interview scheduling system. This parameter allows users to control which interview stages have fixed positions in the sequence and which can be permuted.

## Parameter Details

### Name
`is_fixed`

### Type
Boolean (`True` or `False`)

### Default Value
`False`

### Purpose
Controls whether an interview stage has a fixed position in the sequence:
- When `True`: The stage maintains its position in the provided sequence
- When `False`: The stage can be reordered with other non-fixed stages

## Implementation Details

### Permutation Logic
The system generates all valid permutations of stages while keeping fixed stages in their specified positions:

1. **Fixed stages**: Remain in their original positions
2. **Non-fixed stages**: Are permuted among themselves in all possible arrangements
3. **Combined result**: Each permutation maintains fixed stages in place while varying the order of non-fixed stages

### Example
With 4 interview rounds (r1, r2, r3, r4) where r1 and r3 are fixed:
- Original order: [r1, r2, r3, r4]
- Valid permutations:
  - [r1, r2, r3, r4] (original)
  - [r1, r4, r3, r2] (r2 and r4 swapped)
  
If r1, r2, and r3 were all fixed:
- Only one valid sequence: [r1, r2, r3, r4]
- No permutations are generated

If all stages were non-fixed:
- All 24 permutations (4!) would be generated

### Algorithm
1. Separate stages into fixed and non-fixed categories
2. Generate all permutations of non-fixed stages
3. For each permutation, insert fixed stages at their specified positions
4. Solve the scheduling problem for each valid stage sequence
5. Combine and rank all solutions across all permutations

## Usage Examples

### Mixed Fixed and Non-Fixed Stages
```json
{
  "stages": [
    {
      "stage_name": "Initial_Screen",
      "duration": 30,
      "is_fixed": true,
      "seats": [{"seat_id": "Room_1"}]
    },
    {
      "stage_name": "Tech_Interview",
      "duration": 60,
      "is_fixed": false,
      "seats": [{"seat_id": "Room_2"}]
    },
    {
      "stage_name": "System_Design",
      "duration": 90,
      "is_fixed": true,
      "seats": [{"seat_id": "Room_3"}]
    },
    {
      "stage_name": "Cultural_Fit",
      "duration": 45,
      "is_fixed": false,
      "seats": [{"seat_id": "Room_1"}]
    }
  ]
}
```

### All Stages Fixed
```json
{
  "stages": [
    {
      "stage_name": "Screen",
      "duration": 30,
      "is_fixed": true,
      "seats": [{"seat_id": "Room_1"}]
    },
    {
      "stage_name": "Interview",
      "duration": 60,
      "is_fixed": true,
      "seats": [{"seat_id": "Room_2"}]
    }
  ]
}
```

### No Fixed Stages (Default Behavior)
```json
{
  "stages": [
    {
      "stage_name": "Screen",
      "duration": 30,
      "is_fixed": false,
      "seats": [{"seat_id": "Room_1"}]
    },
    {
      "stage_name": "Interview",
      "duration": 60,
      "is_fixed": false,
      "seats": [{"seat_id": "Room_2"}]
    }
  ]
}
```

## Benefits

1. **Flexibility**: Users can control which stages must occur in specific positions
2. **Optimization**: The system explores multiple valid sequences to find optimal schedules
3. **Business Logic Compliance**: Ensures critical stages occur at required points in the process
4. **Backward Compatibility**: Default behavior maintains existing functionality when all stages are non-fixed

## Performance Considerations

- The number of permutations grows factorially with the number of non-fixed stages
- For n non-fixed stages, n! permutations will be generated
- Each permutation requires a separate optimization run
- Consider the trade-off between flexibility and computation time

## Best Practices

1. **Limit Non-Fixed Stages**: For better performance, minimize the number of non-fixed stages
2. **Strategic Fixing**: Fix stages that have business-critical ordering requirements
3. **Performance Testing**: Test with realistic data to ensure acceptable solution times
4. **Solution Limits**: Adjust `top_k_solutions` parameter to balance comprehensiveness with performance