"""
solver.py - Constraint Satisfaction Problem (CSP) Sudoku Solver with Trace Generation.

This module models Sudoku as a Constraint Satisfaction Problem:
- Variables: The 81 cells of the 9x9 grid, indexed by (row, col) with 0 <= row, col < 9.
- Domains: For each empty cell, the subset of {1, 2, 3, 4, 5, 6, 7, 8, 9} that does not violate
  any binary/all-different constraints with already-assigned cells.
- Constraints: All-Different on each row, column, and 3x3 subgrid box.

Heuristics implemented:
- Minimum Remaining Values (MRV): Chooses the unassigned cell with the smallest candidate domain.
- Least Constraining Value (LCV): Orders candidate values by how few options they rule out
  for neighboring unassigned cells.
"""

from __future__ import annotations
import copy
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Tuple, Optional, Dict, Set


class EventType(str, Enum):
    """Types of events recorded during CSP search."""
    SELECT_VARIABLE = "SELECT_VARIABLE"
    COMPUTE_DOMAIN = "COMPUTE_DOMAIN"
    CHOOSE_VALUE = "CHOOSE_VALUE"
    CHECK_CONSTRAINTS = "CHECK_CONSTRAINTS"
    ASSIGN_VALUE = "ASSIGN_VALUE"
    CONTINUE_NEXT = "CONTINUE_NEXT"
    CONTRADICTION = "CONTRADICTION"
    BACKTRACK = "BACKTRACK"
    TRY_NEXT = "TRY_NEXT"
    PUZZLE_SOLVED = "PUZZLE_SOLVED"
    UNSOLVABLE = "UNSOLVABLE"


@dataclass
class SolverStats:
    """Execution performance statistics for CSP solving."""
    execution_time_ms: float = 0.0
    nodes_visited: int = 0
    candidate_attempts: int = 0
    successful_assignments: int = 0
    backtracks: int = 0
    constraint_checks: int = 0

    def copy(self) -> SolverStats:
        return SolverStats(
            execution_time_ms=self.execution_time_ms,
            nodes_visited=self.nodes_visited,
            candidate_attempts=self.candidate_attempts,
            successful_assignments=self.successful_assignments,
            backtracks=self.backtracks,
            constraint_checks=self.constraint_checks,
        )


@dataclass
class TraceEvent:
    """A deterministic snapshot of an algorithm step for step-by-step demonstration."""
    step_number: int
    event_type: EventType
    cell: Optional[Tuple[int, int]]  # (row, col) 0-indexed
    cell_name: str  # e.g. "R3C5"
    domain: List[int]
    chosen_value: Optional[int]
    explanation: str
    board_snapshot: List[List[int]]
    stats_snapshot: SolverStats
    highlight_type: str = "normal"  # 'active', 'assigned', 'backtrack', 'rejected', 'solved', 'conflict'


def cell_to_name(row: int, col: int) -> str:
    """Convert (row, col) 0-indexed to human-friendly 1-indexed string like 'R1C1'."""
    return f"R{row + 1}C{col + 1}"


def get_peers(row: int, col: int) -> Set[Tuple[int, int]]:
    """Return all unique (r, c) cells in the same row, column, or 3x3 box, excluding (row, col)."""
    peers = set()
    # Row and Column peers
    for i in range(9):
        if i != col:
            peers.add((row, i))
        if i != row:
            peers.add((i, col))
    # 3x3 Box peers
    box_row, box_col = 3 * (row // 3), 3 * (col // 3)
    for r in range(box_row, box_row + 3):
        for c in range(box_col, box_col + 3):
            if (r, c) != (row, col):
                peers.add((r, c))
    return peers


def is_valid_move(board: List[List[int]], row: int, col: int, value: int, stats: Optional[SolverStats] = None) -> bool:
    """
    Check if placing `value` at (row, col) is valid under Sudoku constraints.
    Does not assume cell is empty, but checks against all other cells in row, col, and box.
    """
    if stats:
        stats.constraint_checks += 1

    # Check row constraint
    for c in range(9):
        if c != col and board[row][c] == value:
            return False

    # Check column constraint
    for r in range(9):
        if r != row and board[r][col] == value:
            return False

    # Check 3x3 box constraint
    box_r, box_c = 3 * (row // 3), 3 * (col // 3)
    for r in range(box_r, box_r + 3):
        for c in range(box_c, box_c + 3):
            if (r != row or c != col) and board[r][c] == value:
                return False

    return True


def get_domain(board: List[List[int]], row: int, col: int, stats: Optional[SolverStats] = None) -> List[int]:
    """
    Return list of legal candidate values (1..9) for cell (row, col).
    If cell is already filled, returns [board[row][col]] if valid, or [].
    """
    if board[row][col] != 0:
        val = board[row][col]
        return [val] if is_valid_move(board, row, col, val, stats) else []

    legal_values = []
    for val in range(1, 10):
        if is_valid_move(board, row, col, val, stats):
            legal_values.append(val)
    return legal_values


def get_conflicts(board: List[List[int]]) -> List[Tuple[int, int]]:
    """
    Find all cell coordinates (row, col) that violate row, column, or 3x3 box constraints.
    Returns sorted list of unique coordinates.
    """
    conflicting_cells = set()

    # Row duplicates
    for r in range(9):
        seen: Dict[int, List[int]] = {}
        for c in range(9):
            val = board[r][c]
            if val != 0:
                seen.setdefault(val, []).append(c)
        for val, cols in seen.items():
            if len(cols) > 1:
                for c in cols:
                    conflicting_cells.add((r, c))

    # Column duplicates
    for c in range(9):
        seen: Dict[int, List[int]] = {}
        for r in range(9):
            val = board[r][c]
            if val != 0:
                seen.setdefault(val, []).append(r)
        for val, rows in seen.items():
            if len(rows) > 1:
                for r in rows:
                    conflicting_cells.add((r, c))

    # 3x3 Box duplicates
    for br in range(0, 9, 3):
        for bc in range(0, 9, 3):
            seen: Dict[int, List[Tuple[int, int]]] = {}
            for r in range(br, br + 3):
                for c in range(bc, bc + 3):
                    val = board[r][c]
                    if val != 0:
                        seen.setdefault(val, []).append((r, c))
            for val, cells in seen.items():
                if len(cells) > 1:
                    for cell in cells:
                        conflicting_cells.add(cell)

    return sorted(list(conflicting_cells))


def validate_board(board: List[List[int]]) -> Tuple[bool, str, List[Tuple[int, int]]]:
    """
    Validate board structure and check for constraint conflicts.
    Returns (is_valid, message, conflict_coordinates).
    """
    if len(board) != 9 or any(len(row) != 9 for row in board):
        return False, "Board dimensions must be 9x9.", []

    for r in range(9):
        for c in range(9):
            val = board[r][c]
            if not isinstance(val, int) or val < 0 or val > 9:
                return False, f"Invalid value '{val}' at {cell_to_name(r, c)}. Allowed values are 0-9.", [(r, c)]

    conflicts = get_conflicts(board)
    if conflicts:
        names = ", ".join(cell_to_name(r, c) for r, c in conflicts[:6])
        if len(conflicts) > 6:
            names += f" and {len(conflicts) - 6} more"
        return False, f"Constraint violation (duplicate numbers) at: {names}.", conflicts

    # Check if empty cells have empty domain already (valid but unsolvable clue configuration)
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                domain = get_domain(board, r, c)
                if len(domain) == 0:
                    return True, f"Board has no immediate duplicates, but {cell_to_name(r, c)} has an empty domain (unsolvable).", [(r, c)]

    return True, "Board configuration is valid.", []


def is_board_solved(board: List[List[int]]) -> bool:
    """Check if all cells are filled (non-zero) and there are no conflicts."""
    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                return False
    return len(get_conflicts(board)) == 0


def select_unassigned_variable(
    board: List[List[int]],
    stats: Optional[SolverStats] = None
) -> Optional[Tuple[int, int, List[int]]]:
    """
    Minimum Remaining Values (MRV) heuristic:
    Select the unassigned cell (row, col) with the smallest legal domain.
    Ties broken deterministically by (domain_size, row, col).
    Returns (row, col, domain) or None if all cells are assigned.
    """
    best_cell = None
    best_domain: List[int] = []
    min_domain_len = 10

    for r in range(9):
        for c in range(9):
            if board[r][c] == 0:
                domain = get_domain(board, r, c, stats)
                dom_len = len(domain)
                if dom_len < min_domain_len:
                    min_domain_len = dom_len
                    best_cell = (r, c)
                    best_domain = domain
                    # If domain is 0 or 1, we can't do better than this
                    if dom_len == 0:
                        return r, c, domain

    if best_cell is None:
        return None
    return best_cell[0], best_cell[1], best_domain


def order_domain_values(
    board: List[List[int]],
    row: int,
    col: int,
    domain: List[int],
    stats: Optional[SolverStats] = None
) -> List[int]:
    """
    Least Constraining Value (LCV) heuristic:
    Orders candidate values by the number of options they rule out for neighbor unassigned cells.
    Values ruling out fewer choices are tried first.
    Ties are broken deterministically by value ascending.
    """
    if len(domain) <= 1:
        return list(domain)

    peers = get_peers(row, col)
    unassigned_peers = [(r, c) for (r, c) in peers if board[r][c] == 0]

    def count_eliminations(val: int) -> int:
        eliminated = 0
        for pr, pc in unassigned_peers:
            if stats:
                stats.constraint_checks += 1
            if is_valid_move(board, pr, pc, val, stats):
                eliminated += 1
        return eliminated

    # Sort domain by (eliminations, val)
    return sorted(domain, key=lambda v: (count_eliminations(v), v))


class CSPSolver:
    """
    Main CSP solver managing search state, statistics, and deterministic trace generation.
    """

    def __init__(self, board: List[List[int]], record_trace: bool = False, max_trace_steps: int = 5000):
        self.original_board = [row[:] for row in board]
        self.current_board = [row[:] for row in board]
        self.record_trace = record_trace
        self.max_trace_steps = max_trace_steps
        self.stats = SolverStats()
        self.trace: List[TraceEvent] = []
        self._step_counter = 0

    def _add_event(
        self,
        event_type: EventType,
        cell: Optional[Tuple[int, int]],
        domain: List[int],
        chosen_value: Optional[int],
        explanation: str,
        highlight_type: str = "normal"
    ) -> None:
        if not self.record_trace or len(self.trace) >= self.max_trace_steps:
            return
        self._step_counter += 1
        name = cell_to_name(cell[0], cell[1]) if cell else "-"
        event = TraceEvent(
            step_number=self._step_counter,
            event_type=event_type,
            cell=cell,
            cell_name=name,
            domain=list(domain),
            chosen_value=chosen_value,
            explanation=explanation,
            board_snapshot=[row[:] for row in self.current_board],
            stats_snapshot=self.stats.copy(),
            highlight_type=highlight_type,
        )
        self.trace.append(event)

    def solve(self) -> Tuple[bool, List[List[int]], SolverStats, List[TraceEvent]]:
        """
        Solve the Sudoku board using CSP with MRV, LCV, and Backtracking.
        Returns (success, solved_board, stats, trace).
        """
        start_time = time.perf_counter()

        # Step 0: Initial validation
        is_valid, msg, conflicts = validate_board(self.current_board)
        if not is_valid:
            self._add_event(
                EventType.UNSOLVABLE,
                conflicts[0] if conflicts else None,
                [],
                None,
                f"Puzzle validation failed: {msg}",
                highlight_type="conflict"
            )
            self.stats.execution_time_ms = (time.perf_counter() - start_time) * 1000.0
            return False, self.current_board, self.stats, self.trace

        # Check if already solved
        if is_board_solved(self.current_board):
            self._add_event(
                EventType.PUZZLE_SOLVED,
                None,
                [],
                None,
                "The board is already completely and correctly filled!",
                highlight_type="solved"
            )
            self.stats.execution_time_ms = (time.perf_counter() - start_time) * 1000.0
            return True, self.current_board, self.stats, self.trace

        # Recursive backtracking
        success = self._backtrack()

        self.stats.execution_time_ms = (time.perf_counter() - start_time) * 1000.0

        if success:
            self._add_event(
                EventType.PUZZLE_SOLVED,
                None,
                [],
                None,
                f"Puzzle successfully solved! Total nodes: {self.stats.nodes_visited}, "
                f"backtracks: {self.stats.backtracks}, time: {self.stats.execution_time_ms:.2f} ms.",
                highlight_type="solved"
            )
        else:
            self._add_event(
                EventType.UNSOLVABLE,
                None,
                [],
                None,
                f"Puzzle has no valid solution under CSP constraints (exhausted search tree).",
                highlight_type="conflict"
            )

        return success, self.current_board, self.stats, self.trace

    def _backtrack(self) -> bool:
        self.stats.nodes_visited += 1

        # 1. Select unassigned variable using MRV
        selection = select_unassigned_variable(self.current_board, self.stats)
        if selection is None:
            # All variables assigned and valid!
            return True

        row, col, domain = selection
        cell_name = cell_to_name(row, col)

        self._add_event(
            EventType.SELECT_VARIABLE,
            (row, col),
            domain,
            None,
            f"MRV selected unassigned cell {cell_name} with domain size {len(domain)}: {domain}.",
            highlight_type="active"
        )

        # 2. Check for dead-end / empty domain
        if len(domain) == 0:
            self.stats.backtracks += 1
            self._add_event(
                EventType.CONTRADICTION,
                (row, col),
                [],
                None,
                f"Contradiction detected: Cell {cell_name} has 0 valid candidates remaining. Must backtrack.",
                highlight_type="backtrack"
            )
            return False

        # 3. Order domain values using LCV
        ordered_values = order_domain_values(self.current_board, row, col, domain, self.stats)

        # 4. Try candidates
        for val in ordered_values:
            self.stats.candidate_attempts += 1

            self._add_event(
                EventType.CHOOSE_VALUE,
                (row, col),
                ordered_values,
                val,
                f"Considering candidate {val} for cell {cell_name} (LCV ordered domain: {ordered_values}).",
                highlight_type="active"
            )

            # Check constraint
            valid = is_valid_move(self.current_board, row, col, val, self.stats)
            if not valid:
                self._add_event(
                    EventType.CHECK_CONSTRAINTS,
                    (row, col),
                    ordered_values,
                    val,
                    f"Candidate {val} at {cell_name} violates row, column, or box constraints. Rejected.",
                    highlight_type="rejected"
                )
                continue

            # Assign candidate
            self.current_board[row][col] = val
            self.stats.successful_assignments += 1

            self._add_event(
                EventType.ASSIGN_VALUE,
                (row, col),
                ordered_values,
                val,
                f"Assigned value {val} to cell {cell_name}. Proceeding to next unassigned variable.",
                highlight_type="assigned"
            )

            # Recursive step
            if self._backtrack():
                return True

            # Contradiction in branch: Undo assignment (Backtrack)
            self.current_board[row][col] = 0
            self.stats.backtracks += 1

            self._add_event(
                EventType.BACKTRACK,
                (row, col),
                ordered_values,
                val,
                f"Backtracking: Undoing assignment of {val} at {cell_name} because downstream search failed.",
                highlight_type="backtrack"
            )

        return False


def solve_sudoku(
    board: List[List[int]],
    record_trace: bool = False,
    max_trace_steps: int = 5000
) -> Tuple[bool, List[List[int]], SolverStats, List[TraceEvent]]:
    """
    Public entry point to solve a 9x9 Sudoku grid.
    Never modifies original board. Returns (success, solved_board, stats, trace).
    """
    solver = CSPSolver(board, record_trace=record_trace, max_trace_steps=max_trace_steps)
    return solver.solve()
