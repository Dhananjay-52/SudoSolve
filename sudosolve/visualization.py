"""
visualization.py - Interactive Sudoku Board Canvas, Visual Highlighting, and Educational Explanations.

Provides:
- SudokuTheme: Modern palettes for Dark and Light modes.
- SudokuBoardCanvas: A custom, responsive Tkinter Canvas for 9x9 Sudoku rendering with:
  * Thick 3x3 box borders and thin cell dividers.
  * Distinct styling for original clues vs. solver/demo values.
  * Active cell, peer constraint cells, assigned cells, backtracks, and conflicts highlighting.
  * Direct click selection and keyboard input (1-9, Delete, Backspace, Arrow keys).
- Visual step explanation formatters and CSP flowchart generator.
"""

from __future__ import annotations
import tkinter as tk
from typing import List, Tuple, Optional, Callable, Dict, Set
from solver import TraceEvent, EventType, get_peers, cell_to_name


class SudokuTheme:
    """Color themes for Dark and Light mode."""

    DARK = {
        "bg": "#1E1E2E",
        "board_bg": "#181825",
        "cell_bg": "#1E1E2E",
        "peer_bg": "#25273A",           # Soft highlight on peer row/col/box
        "grid_thin": "#45475A",
        "grid_thick": "#89B4FA",
        "selected_cell": "#313244",
        "selected_border": "#CBA6F7",
        "clue_text": "#F5E0DC",          # Warm bold white for original clues
        "solver_text": "#89DCEB",        # Cyan for solved/assigned values
        "active_bg": "#3B4261",          # MRV selected cell
        "assigned_bg": "#1E3A3A",        # Greenish tint
        "assigned_text": "#A6E3A1",
        "backtrack_bg": "#4A242A",       # Reddish/wine tint
        "backtrack_text": "#F38BA8",
        "rejected_bg": "#3C271E",        # Amber tint
        "rejected_text": "#FAB387",
        "conflict_bg": "#581825",
        "conflict_text": "#F38BA8",
        "text_font_clue": ("Segoe UI", 18, "bold"),
        "text_font_solver": ("Segoe UI", 18, "normal"),
        "sub_font": ("Segoe UI", 9)
    }

    LIGHT = {
        "bg": "#F8FAFC",
        "board_bg": "#FFFFFF",
        "cell_bg": "#FFFFFF",
        "peer_bg": "#F1F5F9",           # Soft highlight on peer row/col/box
        "grid_thin": "#CBD5E1",
        "grid_thick": "#2563EB",
        "selected_cell": "#E0E7FF",
        "selected_border": "#4F46E5",
        "clue_text": "#0F172A",          # Strong dark slate for original clues
        "solver_text": "#0284C7",        # Blue for solved/assigned values
        "active_bg": "#FEF08A",          # Soft yellow for MRV selected cell
        "assigned_bg": "#DCFCE7",        # Soft mint green
        "assigned_text": "#15803D",
        "backtrack_bg": "#FEE2E2",       # Soft crimson
        "backtrack_text": "#B91C1C",
        "rejected_bg": "#FFEDD5",        # Soft orange
        "rejected_text": "#C2410C",
        "conflict_bg": "#FCA5A5",
        "conflict_text": "#991B1B",
        "text_font_clue": ("Segoe UI", 18, "bold"),
        "text_font_solver": ("Segoe UI", 18, "normal"),
        "sub_font": ("Segoe UI", 9)
    }

    @classmethod
    def get(cls, mode: str = "dark") -> Dict:
        return cls.DARK if mode.lower() == "dark" else cls.LIGHT


class SudokuBoardCanvas(tk.Canvas):
    """
    High-performance interactive 9x9 Sudoku Canvas.
    Supports cell clicking, arrow key navigation, keyboard editing,
    read-only demo playback, and multi-layered visual highlighting.
    """

    def __init__(
        self,
        master: tk.Widget,
        size: int = 468,
        theme_mode: str = "dark",
        on_cell_change: Optional[Callable[[int, int, int], None]] = None,
        on_cell_select: Optional[Callable[[int, int], None]] = None,
        **kwargs
    ):
        super().__init__(
            master,
            width=size,
            height=size,
            highlightthickness=0,
            **kwargs
        )
        self.size = size
        self.cell_size = size / 9.0
        self.theme_mode = theme_mode
        self.colors = SudokuTheme.get(theme_mode)

        # Internal state
        self.board: List[List[int]] = [[0]*9 for _ in range(9)]
        self.clues: List[List[bool]] = [[False]*9 for _ in range(9)]
        self.selected_cell: Optional[Tuple[int, int]] = (0, 0)

        # Demonstration highlights
        self.highlight_cell: Optional[Tuple[int, int]] = None
        self.highlight_type: str = "normal"  # 'active', 'assigned', 'backtrack', 'rejected', 'conflict'
        self.conflict_cells: Set[Tuple[int, int]] = set()

        # Operational flags
        self.interactive: bool = True  # Disabled during active demo playback
        self.show_peers: bool = True   # Softly highlight row/col/box of selected cell

        # Callbacks
        self.on_cell_change = on_cell_change
        self.on_cell_select = on_cell_select

        # Bindings
        self.bind("<Button-1>", self._on_click)
        self.bind("<Key>", self._on_key)
        self.bind("<Configure>", self._on_resize)
        self.focus_set()

        self.redraw()

    def set_theme(self, theme_mode: str) -> None:
        """Switch between 'dark' and 'light' theme palettes."""
        self.theme_mode = theme_mode
        self.colors = SudokuTheme.get(theme_mode)
        self.configure(bg=self.colors["board_bg"])
        self.redraw()

    def set_board(self, board: List[List[int]], is_clues: bool = False) -> None:
        """Set current board grid. If is_clues is True, marks non-zeros as permanent clues."""
        self.board = [row[:] for row in board]
        if is_clues:
            self.clues = [[val != 0 for val in row] for row in board]
        self.redraw()

    def set_clues(self, clues: List[List[bool]]) -> None:
        """Explicitly set which cells are original puzzle clues."""
        self.clues = [row[:] for row in clues]
        self.redraw()

    def set_conflicts(self, conflicts: List[Tuple[int, int]]) -> None:
        """Set list of cells that have rule violations to render in red."""
        self.conflict_cells = set(conflicts)
        self.redraw()

    def set_step_highlight(self, cell: Optional[Tuple[int, int]], highlight_type: str) -> None:
        """Set active cell and status from trace event."""
        self.highlight_cell = cell
        self.highlight_type = highlight_type
        if cell is not None:
            self.selected_cell = cell
        self.redraw()

    def clear_highlights(self) -> None:
        """Clear all active step and conflict highlights."""
        self.highlight_cell = None
        self.highlight_type = "normal"
        self.conflict_cells.clear()
        self.redraw()

    def _on_resize(self, event: tk.Event) -> None:
        """Keep grid square and proportionally scale cell size."""
        side = min(event.width, event.height)
        if side > 100 and abs(side - self.size) > 4:
            self.size = side
            self.cell_size = self.size / 9.0
            self.redraw()

    def _on_click(self, event: tk.Event) -> None:
        self.focus_set()
        col = int(event.x // self.cell_size)
        row = int(event.y // self.cell_size)
        if 0 <= row < 9 and 0 <= col < 9:
            self.selected_cell = (row, col)
            if self.on_cell_select:
                self.on_cell_select(row, col)
            self.redraw()

    def _on_key(self, event: tk.Event) -> None:
        if not self.interactive or self.selected_cell is None:
            return

        r, c = self.selected_cell
        key = event.keysym

        # Arrow key navigation
        if key in ("Up", "k"):
            self.selected_cell = (max(0, r - 1), c)
            self.redraw()
            return
        elif key in ("Down", "j"):
            self.selected_cell = (min(8, r + 1), c)
            self.redraw()
            return
        elif key in ("Left", "h"):
            self.selected_cell = (r, max(0, c - 1))
            self.redraw()
            return
        elif key in ("Right", "l"):
            self.selected_cell = (r, min(8, c + 1))
            self.redraw()
            return

        # Numeric input (1-9)
        if event.char in "123456789":
            val = int(event.char)
            self.board[r][c] = val
            self.clues[r][c] = True  # User entered clue
            if self.on_cell_change:
                self.on_cell_change(r, c, val)
            self.redraw()
            return

        # Clear cell
        if key in ("BackSpace", "Delete", "0") or event.char == "0":
            self.board[r][c] = 0
            self.clues[r][c] = False
            if self.on_cell_change:
                self.on_cell_change(r, c, 0)
            self.redraw()
            return

    def redraw(self) -> None:
        """Render the complete 9x9 board on the canvas."""
        self.delete("all")
        cs = self.cell_size
        peers = get_peers(self.selected_cell[0], self.selected_cell[1]) if (self.show_peers and self.selected_cell) else set()

        # 1. Draw cell backgrounds
        for r in range(9):
            for c in range(9):
                x1 = c * cs
                y1 = r * cs
                x2 = x1 + cs
                y2 = y1 + cs

                cell_color = self.colors["cell_bg"]

                # Check conflict
                if (r, c) in self.conflict_cells:
                    cell_color = self.colors["conflict_bg"]
                # Check active step highlight
                elif self.highlight_cell == (r, c):
                    if self.highlight_type == "active":
                        cell_color = self.colors["active_bg"]
                    elif self.highlight_type == "assigned":
                        cell_color = self.colors["assigned_bg"]
                    elif self.highlight_type == "backtrack":
                        cell_color = self.colors["backtrack_bg"]
                    elif self.highlight_type == "rejected":
                        cell_color = self.colors["rejected_bg"]
                    elif self.highlight_type == "conflict":
                        cell_color = self.colors["conflict_bg"]
                # Selected cell
                elif self.selected_cell == (r, c):
                    cell_color = self.colors["selected_cell"]
                # Soft peer highlight
                elif (r, c) in peers:
                    cell_color = self.colors["peer_bg"]

                self.create_rectangle(x1, y1, x2, y2, fill=cell_color, width=0)

        # 2. Draw thin inner grid lines
        for i in range(1, 9):
            if i % 3 != 0:
                pos = i * cs
                # Vertical
                self.create_line(pos, 0, pos, self.size, fill=self.colors["grid_thin"], width=1)
                # Horizontal
                self.create_line(0, pos, self.size, pos, fill=self.colors["grid_thin"], width=1)

        # 3. Draw thick 3x3 box grid lines and outer border
        for i in range(0, 10, 3):
            pos = i * cs
            # Ensure line stays inside canvas bounds
            clamped_pos = max(1, min(pos, self.size - 1))
            # Vertical
            self.create_line(clamped_pos, 0, clamped_pos, self.size, fill=self.colors["grid_thick"], width=3)
            # Horizontal
            self.create_line(0, clamped_pos, self.size, clamped_pos, fill=self.colors["grid_thick"], width=3)

        # 4. Highlight border for selected cell
        if self.selected_cell:
            sr, sc = self.selected_cell
            sx1, sy1 = sc * cs + 1, sr * cs + 1
            sx2, sy2 = sx1 + cs - 2, sy1 + cs - 2
            self.create_rectangle(
                sx1, sy1, sx2, sy2,
                outline=self.colors["selected_border"],
                width=2
            )

        # 5. Draw cell numbers
        for r in range(9):
            for c in range(9):
                val = self.board[r][c]
                if val == 0:
                    continue

                cx = c * cs + cs / 2.0
                cy = r * cs + cs / 2.0

                is_clue = self.clues[r][c]

                # Choose text color
                if (r, c) in self.conflict_cells:
                    text_color = self.colors["conflict_text"]
                    font = self.colors["text_font_clue"]
                elif self.highlight_cell == (r, c) and self.highlight_type == "backtrack":
                    text_color = self.colors["backtrack_text"]
                    font = self.colors["text_font_clue"]
                elif self.highlight_cell == (r, c) and self.highlight_type == "assigned":
                    text_color = self.colors["assigned_text"]
                    font = self.colors["text_font_clue"]
                elif is_clue:
                    text_color = self.colors["clue_text"]
                    font = self.colors["text_font_clue"]
                else:
                    text_color = self.colors["solver_text"]
                    font = self.colors["text_font_solver"]

                self.create_text(
                    cx, cy,
                    text=str(val),
                    fill=text_color,
                    font=font
                )


def format_step_explanation(event: TraceEvent) -> Dict[str, str]:
    """
    Format a TraceEvent into structured dictionary for GUI inspector card.
    """
    badge_titles = {
        EventType.SELECT_VARIABLE: "1. Select Variable (MRV)",
        EventType.COMPUTE_DOMAIN: "2. Compute Legal Domain",
        EventType.CHOOSE_VALUE: "3. Choose Candidate (LCV)",
        EventType.CHECK_CONSTRAINTS: "4. Check Constraints",
        EventType.ASSIGN_VALUE: "5. Assign Candidate",
        EventType.CONTINUE_NEXT: "6. Proceed Forward",
        EventType.CONTRADICTION: "7. Contradiction / Dead End",
        EventType.BACKTRACK: "8. Undo Assignment (Backtrack)",
        EventType.TRY_NEXT: "9. Try Next Candidate",
        EventType.PUZZLE_SOLVED: "10. Solution Found!",
        EventType.UNSOLVABLE: "Exhausted / Unsolvable"
    }

    badge = badge_titles.get(event.event_type, event.event_type.value)
    domain_str = ", ".join(map(str, event.domain)) if event.domain else "None (Empty)"
    chosen_str = str(event.chosen_value) if event.chosen_value is not None else "-"

    return {
        "step": f"Step {event.step_number}",
        "badge": badge,
        "cell": event.cell_name,
        "domain": domain_str,
        "chosen": chosen_str,
        "explanation": event.explanation,
        "nodes": str(event.stats_snapshot.nodes_visited),
        "backtracks": str(event.stats_snapshot.backtracks),
        "assignments": str(event.stats_snapshot.successful_assignments),
        "checks": str(event.stats_snapshot.constraint_checks),
    }


def get_csp_flowchart_text() -> str:
    """Return a crisp, educational ASCII/Unicode flowchart for viva presentation."""
    return """
+====================================================================+
|             SUDOKU CSP BACKTRACKING FLOWCHART (MRV + LCV)           |
+====================================================================+

                         [ START SEARCH ]
                                |
                                v
               +----------------------------------+
               |  Are all 81 variables assigned?  |
               +----------------------------------+
                      /                    \\
                   [YES]                  [NO]
                    /                        \\
                   v                          v
          +------------------+    +------------------------------+
          | SUCCESS / SOLVED |    |  Apply MRV Heuristic         |
          +------------------+    |  Find unassigned cell with   |
                                  |  smallest valid domain       |
                                  +------------------------------+
                                                  |
                                                  v
                                     +--------------------------+
                                     |  Is domain size == 0?    |
                                     +--------------------------+
                                            /            \\
                                         [YES]          [NO]
                                          /                \\
                                         v                  v
                       +-------------------+   +------------------------+
                       | CONTRADICTION!    |   | Apply LCV Heuristic    |
                       | (Dead end branch) |   | Order domain values by |
                       +-------------------+   | least neighbor impact  |
                                 |             +------------------------+
                                 v                          |
                       +-------------------+                v
                       |   BACKTRACK       |   +------------------------+
                       | Undo previous cell|   | Pick next candidate v  |
                       | assignment;       |   +------------------------+
                       | return False      |                |
                       +-------------------+                v
                                 ^             +------------------------+
                                 |  [FAILURE]  | Assign cell = v        |
                                 +-------------| Recursively backtrack  |
                                               +------------------------+
                                                            |
                                                        [SUCCESS]
                                                            |
                                                            v
                                                   +------------------+
                                                   | Return True      |
                                                   +------------------+
+====================================================================+
"""


def get_worked_example_text() -> str:
    """Return a clear worked example showing row, column, and box filtering."""
    return """
Worked Example: Calculating the Domain of Cell R3C5

Suppose we want to find the valid candidate domain for Cell R3C5 (Row 3, Column 5):

Initial Domain:
D = {1, 2, 3, 4, 5, 6, 7, 8, 9}

1. Row 3 Constraint (All-Different in Row):
   Values already present in Row 3: {1, 4, 7}
   Filtered Domain:
   D' = D \\ {1, 4, 7} = {2, 3, 5, 6, 8, 9}

2. Column 5 Constraint (All-Different in Column):
   Values already present in Column 5: {2, 5, 8}
   Filtered Domain:
   D'' = D' \\ {2, 5, 8} = {3, 6, 9}

3. 3x3 Box Constraint (Top-Middle Box: Rows 1-3, Cols 4-6):
   Values already present in Box: {3, 7}
   Filtered Domain:
   D''' = D'' \\ {3} = {6, 9}

Resulting Domain:
Cell R3C5 has candidate domain {6, 9} (size = 2).

MRV Decision:
If another cell R7C2 has domain {5} (size = 1), MRV selects R7C2 first!
If R3C5 has size 2 and all other cells have size >= 3, MRV selects R3C5!
"""
