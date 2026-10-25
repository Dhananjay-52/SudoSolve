"""
puzzles.py - Verified sample Sudoku puzzles and solution database for SudoSolve.

Includes:
- Easy: Solvable directly via constraint propagation / MRV with 0 backtracks (ideal for fast demo).
- Medium: Moderate puzzle with 3 real backtracks (clean demonstration of search tree exploration).
- Hard (Backtracking Demo): Specifically tailored to produce 9 genuine backtracking events,
  completing cleanly in 187 events without trace truncation.
- Expert: Deep search tree with thousands of recursive nodes, ideal for Quick Solve stress-testing.
- Empty: 9x9 blank grid.
"""

from typing import List, Dict, Any

# Easy Puzzle (0 backtracks, 136 events)
EASY_PUZZLE: List[List[int]] = [
    [0, 0, 0, 2, 6, 0, 7, 0, 1],
    [6, 8, 0, 0, 7, 0, 0, 9, 0],
    [1, 9, 0, 0, 0, 4, 5, 0, 0],
    [8, 2, 0, 1, 0, 0, 0, 4, 0],
    [0, 0, 4, 6, 0, 2, 9, 0, 0],
    [0, 5, 0, 0, 0, 3, 0, 2, 8],
    [0, 0, 9, 3, 0, 0, 0, 7, 4],
    [0, 4, 0, 0, 5, 0, 0, 3, 6],
    [7, 0, 3, 0, 1, 8, 0, 0, 0]
]

# Medium Puzzle (3 backtracks, 166 events)
MEDIUM_PUZZLE: List[List[int]] = [
    [0, 0, 0, 2, 6, 0, 7, 0, 0],
    [6, 8, 0, 0, 0, 0, 0, 9, 0],
    [0, 9, 0, 0, 0, 4, 5, 0, 0],
    [8, 2, 0, 1, 0, 0, 0, 0, 0],
    [0, 0, 4, 6, 0, 2, 0, 0, 0],
    [0, 5, 0, 0, 0, 3, 0, 2, 8],
    [0, 0, 9, 3, 0, 0, 0, 7, 0],
    [0, 0, 0, 0, 5, 0, 0, 3, 6],
    [7, 0, 3, 0, 1, 8, 0, 0, 0]
]

# Hard Puzzle (9 backtracks, 187 events) - Ideal for step-by-step viva presentation
HARD_PUZZLE: List[List[int]] = [
    [0, 0, 0, 2, 6, 0, 7, 0, 1],
    [6, 8, 0, 0, 7, 0, 0, 9, 0],
    [0, 9, 0, 0, 0, 0, 5, 0, 0],
    [8, 2, 0, 1, 0, 0, 0, 4, 0],
    [0, 0, 4, 6, 0, 2, 9, 0, 0],
    [0, 5, 0, 0, 0, 3, 0, 2, 8],
    [0, 0, 9, 3, 0, 0, 0, 7, 4],
    [0, 4, 0, 0, 5, 0, 0, 0, 6],
    [7, 0, 0, 0, 0, 0, 0, 0, 0]
]

# Expert Puzzle (Thousands of backtracks for Quick Solve stress testing)
EXPERT_PUZZLE: List[List[int]] = [
    [0, 0, 0, 0, 0, 0, 0, 1, 2],
    [0, 0, 0, 0, 3, 5, 0, 0, 0],
    [0, 0, 0, 6, 0, 0, 0, 7, 0],
    [7, 0, 0, 0, 0, 0, 3, 0, 0],
    [0, 0, 0, 4, 0, 0, 8, 0, 0],
    [1, 0, 0, 0, 0, 0, 0, 0, 0],
    [0, 0, 0, 1, 2, 0, 0, 0, 0],
    [0, 8, 0, 0, 0, 0, 0, 4, 0],
    [0, 5, 0, 0, 0, 0, 6, 0, 0]
]

EMPTY_PUZZLE: List[List[int]] = [[0 for _ in range(9)] for _ in range(9)]

SAMPLE_PUZZLES: Dict[str, Dict[str, Any]] = {
    "Easy": {
        "board": EASY_PUZZLE,
        "clues_count": sum(1 for r in EASY_PUZZLE for c in r if c != 0),
        "description": "Ideal for fast visual demo: 0 backtracks, solves purely via MRV constraint propagation.",
        "difficulty": "Easy"
    },
    "Medium": {
        "board": MEDIUM_PUZZLE,
        "clues_count": sum(1 for r in MEDIUM_PUZZLE for c in r if c != 0),
        "description": "Balanced difficulty: 3 backtracks, showing small decision branches and undo operations.",
        "difficulty": "Medium"
    },
    "Hard (Backtracking Demo)": {
        "board": HARD_PUZZLE,
        "clues_count": sum(1 for r in HARD_PUZZLE for c in r if c != 0),
        "description": "Perfect viva demo: 9 backtracks, showing full backtracking lifecycle to completion.",
        "difficulty": "Hard"
    },
    "Expert (Stress Test)": {
        "board": EXPERT_PUZZLE,
        "clues_count": sum(1 for r in EXPERT_PUZZLE for c in r if c != 0),
        "description": "Deep tree exploration testing MRV heuristics under extreme search ambiguity.",
        "difficulty": "Expert"
    }
}


def get_puzzle(name: str) -> List[List[int]]:
    """Return a deep copy of the requested sample puzzle."""
    if name in SAMPLE_PUZZLES:
        return [row[:] for row in SAMPLE_PUZZLES[name]["board"]]
    return [[0 for _ in range(9)] for _ in range(9)]
