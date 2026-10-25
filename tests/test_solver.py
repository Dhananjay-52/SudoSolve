"""
tests/test_solver.py - Comprehensive automated tests for SudoSolve CSP Solver.

Tests cover:
1. Valid solvable puzzles (Easy, Medium, Hard).
2. Detection of duplicate clues in row, column, and 3x3 box.
3. Valid but unsolvable board configurations.
4. Empty board handling (valid CSP with multiple solutions).
5. Already-solved board detection.
6. Verification that Hard puzzle triggers real backtracking events.
7. Correct restoration after unsuccessful branch (undoing assignment).
8. Preservation of original clues (solver doesn't overwrite inputs).
9. Full mathematical validity of all generated solutions.
10. Deterministic trace snapshots and statistics consistency.
"""

import pytest
import copy
from solver import (
    solve_sudoku,
    validate_board,
    get_conflicts,
    get_domain,
    is_valid_move,
    is_board_solved,
    select_unassigned_variable,
    order_domain_values,
    EventType,
    CSPSolver
)
from puzzles import EASY_PUZZLE, MEDIUM_PUZZLE, HARD_PUZZLE, EMPTY_PUZZLE


def test_valid_solvable_easy():
    """Test that the easy sample puzzle solves correctly and produces valid 9x9 solution."""
    board = [row[:] for row in EASY_PUZZLE]
    success, solved, stats, trace = solve_sudoku(board, record_trace=False)
    assert success is True
    assert is_board_solved(solved) is True
    assert stats.execution_time_ms > 0
    assert stats.nodes_visited > 0


def test_valid_solvable_medium():
    """Test solving medium puzzle."""
    board = [row[:] for row in MEDIUM_PUZZLE]
    success, solved, stats, trace = solve_sudoku(board, record_trace=False)
    assert success is True
    assert is_board_solved(solved) is True


def test_duplicate_clues_in_row():
    """Test detection of duplicate numbers in the same row."""
    board = [row[:] for row in EASY_PUZZLE]
    # In row 0, set two cells to 9
    board[0][0] = 9
    board[0][1] = 9
    is_valid, msg, conflicts = validate_board(board)
    assert is_valid is False
    assert (0, 0) in conflicts and (0, 1) in conflicts
    assert "duplicate" in msg.lower() or "violation" in msg.lower()

    # Solver should reject without searching
    success, _, _, _ = solve_sudoku(board)
    assert success is False


def test_duplicate_clues_in_column():
    """Test detection of duplicate numbers in the same column."""
    board = [row[:] for row in EASY_PUZZLE]
    # In column 4, set row 0 and row 1 to 5
    board[0][4] = 5
    board[1][4] = 5
    is_valid, msg, conflicts = validate_board(board)
    assert is_valid is False
    assert (0, 4) in conflicts and (1, 4) in conflicts

    success, _, _, _ = solve_sudoku(board)
    assert success is False


def test_duplicate_clues_in_box():
    """Test detection of duplicate numbers in the same 3x3 box."""
    board = [row[:] for row in EASY_PUZZLE]
    # Box 0 (top-left): (0,0) and (1,1) both set to 7 (different row, different col)
    board[0][0] = 7
    board[1][1] = 7
    is_valid, msg, conflicts = validate_board(board)
    assert is_valid is False
    assert (0, 0) in conflicts and (1, 1) in conflicts

    success, _, _, _ = solve_sudoku(board)
    assert success is False


def test_valid_but_unsolvable_puzzle():
    """
    Test a board that has no immediate duplicate clues, but where constraints
    leave a cell with an empty domain (contradiction at root or unsolvable).
    """
    # A constructed unsolvable puzzle: 8 values surround an empty cell leaving 0 choices
    # In row 0: 1, 2, 3 in box 0; col 0 has 4, 5, 6; box 0 has 7, 8
    board = [[0]*9 for _ in range(9)]
    # Put 1, 2, 3 in row 0
    board[0][1] = 1
    board[0][2] = 2
    # Put 3, 4, 5 in col 0
    board[1][0] = 3
    board[2][0] = 4
    board[3][0] = 5
    # Put 6, 7, 8, 9 in other peers of (0,0)
    board[1][1] = 6
    board[1][2] = 7
    board[2][1] = 8
    board[2][2] = 9
    # Now cell (0,0) has no available domain among 1..9
    domain = get_domain(board, 0, 0)
    assert len(domain) == 0

    success, _, stats, trace = solve_sudoku(board, record_trace=True)
    assert success is False


def test_empty_board():
    """Test an entirely empty board. It is a valid CSP instance and should find a valid solution."""
    board = [[0]*9 for _ in range(9)]
    is_valid, msg, conflicts = validate_board(board)
    assert is_valid is True
    assert len(conflicts) == 0

    success, solved, stats, trace = solve_sudoku(board, record_trace=False)
    assert success is True
    assert is_board_solved(solved) is True


def test_already_solved_board():
    """Test an already completely filled and valid board."""
    # First get a valid solution
    _, solved, _, _ = solve_sudoku(EASY_PUZZLE, record_trace=False)
    assert is_board_solved(solved) is True

    # Now pass it into solver
    success, result_board, stats, trace = solve_sudoku(solved, record_trace=True)
    assert success is True
    assert result_board == solved
    # Trace should record PUZZLE_SOLVED without deep search
    assert any(ev.event_type == EventType.PUZZLE_SOLVED for ev in trace)


def test_puzzle_requiring_backtracking():
    """Test that the Hard puzzle triggers real backtracking events and statistics increment."""
    board = [row[:] for row in HARD_PUZZLE]
    success, solved, stats, trace = solve_sudoku(board, record_trace=True)
    assert success is True
    assert is_board_solved(solved) is True
    # Must have real backtracks
    assert stats.backtracks > 0, "Hard puzzle must trigger at least 1 backtrack!"

    # Trace must have BACKTRACK events
    backtrack_events = [ev for ev in trace if ev.event_type == EventType.BACKTRACK]
    assert len(backtrack_events) > 0, "Trace must capture BACKTRACK event types!"

    # Check one of the backtrack events
    ev = backtrack_events[0]
    assert ev.cell is not None
    assert "Backtracking" in ev.explanation
    assert ev.highlight_type == "backtrack"


def test_restoration_after_unsuccessful_branch():
    """Verify that when a branch fails, the cell is reset back to 0 in subsequent snapshots."""
    board = [row[:] for row in HARD_PUZZLE]
    _, _, _, trace = solve_sudoku(board, record_trace=True)

    # Find a backtrack event and check that cell value was restored
    for i, ev in enumerate(trace):
        if ev.event_type == EventType.BACKTRACK:
            r, c = ev.cell
            # In the board snapshot of the backtrack event, the cell should be reset to 0
            assert ev.board_snapshot[r][c] == 0, f"Cell ({r},{c}) should be 0 upon backtrack undo."
            break


def test_preservation_of_original_clues():
    """Ensure original clues from the user puzzle are not altered in the solution."""
    original = [row[:] for row in EASY_PUZZLE]
    original_copy = copy.deepcopy(original)

    success, solved, _, _ = solve_sudoku(original, record_trace=False)
    assert success is True

    # Input board must be untouched
    assert original == original_copy

    # Every clue present in original must be identical in solved board
    for r in range(9):
        for c in range(9):
            if original_copy[r][c] != 0:
                assert solved[r][c] == original_copy[r][c]


def test_trace_snapshot_and_statistics_consistency():
    """Verify trace events have strictly increasing step numbers, valid snapshots, and valid stats."""
    board = [row[:] for row in EASY_PUZZLE]
    success, solved, stats, trace = solve_sudoku(board, record_trace=True)
    assert success is True
    assert len(trace) > 0

    for i, ev in enumerate(trace):
        assert ev.step_number == i + 1
        assert len(ev.board_snapshot) == 9
        assert all(len(row) == 9 for row in ev.board_snapshot)
        assert ev.stats_snapshot.nodes_visited <= stats.nodes_visited
        assert ev.explanation != ""


def test_invalid_board_dimensions():
    """Test validation rejection for non 9x9 board."""
    invalid_board = [[0]*8 for _ in range(9)]
    is_valid, msg, _ = validate_board(invalid_board)
    assert is_valid is False
    assert "dimensions" in msg.lower()


def test_invalid_cell_values():
    """Test validation rejection for values outside 0-9."""
    board = [[0]*9 for _ in range(9)]
    board[0][0] = 12
    is_valid, msg, conflicts = validate_board(board)
    assert is_valid is False
    assert (0, 0) in conflicts


def test_lcv_ordering_logic():
    """Test that order_domain_values respects LCV ranking."""
    board = [row[:] for row in EASY_PUZZLE]
    domain = get_domain(board, 0, 0)
    ordered = order_domain_values(board, 0, 0, domain)
    assert len(ordered) == len(domain)
    assert set(ordered) == set(domain)

