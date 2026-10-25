"""
SudoSolve - Sudoku Solving Through Constraint Satisfaction Problems.
"""

from .solver import (
    solve_sudoku,
    validate_board,
    get_domain,
    get_conflicts,
    is_board_solved,
    select_unassigned_variable,
    order_domain_values,
    EventType,
    TraceEvent,
    SolverStats
)
from .puzzles import SAMPLE_PUZZLES, get_puzzle
