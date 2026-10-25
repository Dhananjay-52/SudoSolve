"""
main.py - SudoSolve: Sudoku Solver Using Constraint Satisfaction Problems (CSP).
Modern desktop GUI built with CustomTkinter and Tkinter.

Features:
- Pure Python desktop GUI (No web dependencies, no Streamlit/Flask/Django/Node).
- Interactive 9x9 Sudoku canvas with thick 3x3 box boundaries.
- Full CSP solving engine with Minimum Remaining Values (MRV) and Least Constraining Value (LCV).
- Step-by-step interactive demonstration with forward/backward scrubbing, play/pause, and restart.
- Quick Solve mode with millisecond timing, search nodes, backtracks, and constraint statistics.
- Comprehensive educational panel with CSP theory, worked domain filtering, and viva flowchart.
- Dark and Light theme toggle.
"""

from __future__ import annotations
import sys
import copy
import time
import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
from typing import List, Optional, Tuple

from solver import (
    solve_sudoku,
    validate_board,
    get_domain,
    get_conflicts,
    is_board_solved,
    cell_to_name,
    TraceEvent,
    EventType,
    SolverStats
)
from visualization import (
    SudokuBoardCanvas,
    SudokuTheme,
    format_step_explanation,
    get_csp_flowchart_text,
    get_worked_example_text
)
from puzzles import SAMPLE_PUZZLES, get_puzzle, EASY_PUZZLE, HARD_PUZZLE


class SudoSolveApp(ctk.CTk):
    """Main desktop application window for SudoSolve."""

    def __init__(self):
        super().__init__()

        # Window settings
        self.title("SudoSolve — Sudoku Solving Through Constraint Satisfaction Problems")
        self.geometry("1180x820")
        self.minsize(980, 720)

        # Set default appearance
        self.theme_mode = "dark"
        ctk.set_appearance_mode("Dark")
        ctk.set_default_color_theme("blue")

        # Application state
        self.initial_puzzle: List[List[int]] = [row[:] for row in EASY_PUZZLE]
        self.current_board: List[List[int]] = [row[:] for row in EASY_PUZZLE]
        self.clues_mask: List[List[bool]] = [[val != 0 for val in row] for row in EASY_PUZZLE]
        self.user_has_edited: bool = False

        # Demo playback state
        self.is_demo_mode: bool = False
        self.is_playing: bool = False
        self.trace: List[TraceEvent] = []
        self.current_step_index: int = 0
        self.play_timer_id: Optional[str] = None
        self.play_delay_ms: int = 250

        # Build GUI
        self._build_header()
        self._build_main_layout()
        self._build_bottom_toolbar()
        self._build_status_bar()

        # Load initial puzzle
        self._load_board_data(self.initial_puzzle, is_sample=True)

        # Handle window closing cleanup
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # =========================================================================
    # GUI Layout Builders
    # =========================================================================

    def _build_header(self) -> None:
        """Create the top branding header with title, subtitle, and theme toggle."""
        self.header_frame = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray90", "#181825"))
        self.header_frame.pack(side="top", fill="x", padx=0, pady=0)

        # Left title section
        title_box = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        title_box.pack(side="left", padx=20, pady=12)

        title_lbl = ctk.CTkLabel(
            title_box,
            text="SudoSolve",
            font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"),
            text_color=("#1E293B", "#CBA6F7")
        )
        title_lbl.pack(anchor="w")

        subtitle_lbl = ctk.CTkLabel(
            title_box,
            text="Interactive Sudoku Solver Demonstrating Constraint Satisfaction Problems (CSP)",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=("#64748B", "#A6ADC8")
        )
        subtitle_lbl.pack(anchor="w")

        # Right header controls (Theme Toggle)
        header_actions = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        header_actions.pack(side="right", padx=20, pady=12)

        self.theme_btn = ctk.CTkButton(
            header_actions,
            text="☀ Light Mode" if self.theme_mode == "dark" else "🌙 Dark Mode",
            width=110,
            height=32,
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#E2E8F0", "#313244"),
            text_color=("#0F172A", "#CDD6F4"),
            hover_color=("#CBD5E1", "#45475A"),
            command=self._toggle_theme
        )
        self.theme_btn.pack(side="right", padx=6)

    def _build_main_layout(self) -> None:
        """Create the two-column layout: Left = Sudoku Grid, Right = Inspector & Education."""
        self.main_container = ctk.CTkFrame(self, fg_color="transparent")
        self.main_container.pack(side="top", fill="both", expand=True, padx=16, pady=10)

        # ----------------- Left Panel: Sudoku Board -----------------
        self.left_panel = ctk.CTkFrame(self.main_container, corner_radius=12, fg_color=("gray95", "#181825"))
        self.left_panel.pack(side="left", fill="y", padx=(0, 10), pady=0)

        # Board Title / Legend
        legend_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        legend_frame.pack(side="top", fill="x", padx=16, pady=(12, 6))

        board_lbl = ctk.CTkLabel(
            legend_frame,
            text="Sudoku Grid (9×9)",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        board_lbl.pack(side="left")

        self.cell_info_lbl = ctk.CTkLabel(
            legend_frame,
            text="Cell: R1C1 | Domain: -",
            font=ctk.CTkFont(size=12),
            text_color=("#64748B", "#9399B2")
        )
        self.cell_info_lbl.pack(side="right")

        # Canvas Wrapper
        canvas_wrapper = ctk.CTkFrame(self.left_panel, fg_color="transparent")
        canvas_wrapper.pack(side="top", padx=16, pady=8)

        self.canvas = SudokuBoardCanvas(
            canvas_wrapper,
            size=450,
            theme_mode=self.theme_mode,
            on_cell_change=self._on_user_cell_change,
            on_cell_select=self._on_user_cell_select
        )
        self.canvas.pack()

        # Board instructions
        instructions_lbl = ctk.CTkLabel(
            self.left_panel,
            text="Click cell and type [1-9] to set, [0/Backspace] to clear, [Arrow keys] to navigate.",
            font=ctk.CTkFont(size=11),
            text_color=("#94A3B8", "#6C7086")
        )
        instructions_lbl.pack(side="top", padx=16, pady=(4, 12))

        # ----------------- Right Panel: Inspector & Tabs -----------------
        self.right_panel = ctk.CTkFrame(self.main_container, corner_radius=12, fg_color=("gray95", "#181825"))
        self.right_panel.pack(side="right", fill="both", expand=True, padx=(10, 0), pady=0)

        self.tabview = ctk.CTkTabview(self.right_panel)
        self.tabview.pack(fill="both", expand=True, padx=12, pady=10)

        self.tab_demo = self.tabview.add("Demo Inspector & Trace")
        self.tab_stats = self.tabview.add("Performance Statistics")
        self.tab_theory = self.tabview.add("CSP Theory")
        self.tab_worked = self.tabview.add("Worked Example")
        self.tab_flowchart = self.tabview.add("Flowchart & Viva")

        self._build_tab_demo()
        self._build_tab_stats()
        self._build_tab_theory()
        self._build_tab_worked()
        self._build_tab_flowchart()

    def _build_tab_demo(self) -> None:
        """Create the Step-by-Step Demonstration Inspector tab."""
        tab = self.tab_demo

        # Top Step & Event Badge
        top_meta = ctk.CTkFrame(tab, fg_color="transparent")
        top_meta.pack(fill="x", padx=10, pady=(6, 8))

        self.lbl_step_number = ctk.CTkLabel(
            top_meta,
            text="Step 0 / 0",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#1E293B", "#89B4FA")
        )
        self.lbl_step_number.pack(side="left")

        self.lbl_event_badge = ctk.CTkLabel(
            top_meta,
            text="Ready to Start Demo",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#E0E7FF", "#313244"),
            text_color=("#3730A3", "#CBA6F7"),
            corner_radius=8,
            padx=10,
            pady=4
        )
        self.lbl_event_badge.pack(side="right")

        # Step Scrub Slider
        slider_frame = ctk.CTkFrame(tab, fg_color="transparent")
        slider_frame.pack(fill="x", padx=10, pady=(0, 8))

        self.scrub_slider = ctk.CTkSlider(
            slider_frame,
            from_=1,
            to=100,
            number_of_steps=99,
            command=self._on_scrub_slider
        )
        self.scrub_slider.pack(fill="x")
        self.scrub_slider.set(1)

        # Variables / Candidates Card
        vars_card = ctk.CTkFrame(tab, corner_radius=10, fg_color=("white", "#1E1E2E"))
        vars_card.pack(fill="x", padx=10, pady=6)

        v_row1 = ctk.CTkFrame(vars_card, fg_color="transparent")
        v_row1.pack(fill="x", padx=12, pady=6)

        ctk.CTkLabel(v_row1, text="Selected Variable:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        self.lbl_cell_target = ctk.CTkLabel(v_row1, text="-", font=ctk.CTkFont(size=13, weight="bold"), text_color=("#2563EB", "#89B4FA"))
        self.lbl_cell_target.pack(side="left", padx=8)

        ctk.CTkLabel(v_row1, text="Chosen Candidate:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(16, 0))
        self.lbl_chosen_val = ctk.CTkLabel(v_row1, text="-", font=ctk.CTkFont(size=13, weight="bold"), text_color=("#16A34A", "#A6E3A1"))
        self.lbl_chosen_val.pack(side="left", padx=8)

        v_row2 = ctk.CTkFrame(vars_card, fg_color="transparent")
        v_row2.pack(fill="x", padx=12, pady=(0, 8))

        ctk.CTkLabel(v_row2, text="Candidate Domain:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        self.lbl_domain_list = ctk.CTkLabel(v_row2, text="None", font=ctk.CTkFont(size=12), text_color=("#D97706", "#FAB387"))
        self.lbl_domain_list.pack(side="left", padx=8)

        # Step Explanation Box
        expl_frame = ctk.CTkFrame(tab, corner_radius=10, fg_color=("white", "#1E1E2E"))
        expl_frame.pack(fill="both", expand=True, padx=10, pady=6)

        ctk.CTkLabel(
            expl_frame,
            text="Algorithm Step Explanation",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=12, pady=(8, 4))

        self.txt_explanation = ctk.CTkTextbox(
            expl_frame,
            wrap="word",
            font=ctk.CTkFont(size=12),
            fg_color="transparent",
            activate_scrollbars=True
        )
        self.txt_explanation.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.txt_explanation.insert("1.0", "Click 'Start Demo' to record and visualize the CSP search step-by-step.")
        self.txt_explanation.configure(state="disabled")

        # Live Metrics Strip
        metrics_frame = ctk.CTkFrame(tab, fg_color="transparent")
        metrics_frame.pack(fill="x", padx=10, pady=6)

        self.lbl_live_nodes = self._create_mini_stat(metrics_frame, "Search Nodes", "0")
        self.lbl_live_assigns = self._create_mini_stat(metrics_frame, "Assignments", "0")
        self.lbl_live_backtracks = self._create_mini_stat(metrics_frame, "Backtracks", "0")
        self.lbl_live_checks = self._create_mini_stat(metrics_frame, "Constraint Checks", "0")

    def _create_mini_stat(self, parent: ctk.CTkFrame, title: str, val: str) -> ctk.CTkLabel:
        box = ctk.CTkFrame(parent, corner_radius=8, fg_color=("white", "#1E1E2E"))
        box.pack(side="left", fill="both", expand=True, padx=4, pady=2)
        ctk.CTkLabel(box, text=title, font=ctk.CTkFont(size=10), text_color=("#64748B", "#9399B2")).pack(pady=(4, 0))
        val_lbl = ctk.CTkLabel(box, text=val, font=ctk.CTkFont(size=14, weight="bold"))
        val_lbl.pack(pady=(0, 4))
        return val_lbl

    def _build_tab_stats(self) -> None:
        """Create the Performance Statistics tab for Quick Solve and comprehensive benchmarking."""
        tab = self.tab_stats

        title_lbl = ctk.CTkLabel(
            tab,
            text="Solver Execution Performance",
            font=ctk.CTkFont(size=16, weight="bold")
        )
        title_lbl.pack(anchor="w", padx=16, pady=(12, 6))

        desc_lbl = ctk.CTkLabel(
            tab,
            text="Measured using high-precision time.perf_counter() and search tree recursion counters.",
            font=ctk.CTkFont(size=12),
            text_color=("#64748B", "#9399B2")
        )
        desc_lbl.pack(anchor="w", padx=16, pady=(0, 12))

        # Grid of metrics
        grid_frame = ctk.CTkFrame(tab, corner_radius=12, fg_color=("white", "#1E1E2E"))
        grid_frame.pack(fill="x", padx=16, pady=8)

        self.stat_time_lbl = self._create_stat_row(grid_frame, "⏱ Total Execution Time", "0.00 ms")
        self.stat_nodes_lbl = self._create_stat_row(grid_frame, "🌲 Recursive Search Nodes Visited", "0")
        self.stat_attempts_lbl = self._create_stat_row(grid_frame, "🎯 Candidate Assignments Attempted", "0")
        self.stat_success_lbl = self._create_stat_row(grid_frame, "✅ Successful Assignments Placed", "0")
        self.stat_backtracks_lbl = self._create_stat_row(grid_frame, "↺ Backtracks (Failed Branches)", "0")
        self.stat_checks_lbl = self._create_stat_row(grid_frame, "🔍 Constraint Consistency Checks", "0")

        # Metric Definitions & Viva Notes
        notes_card = ctk.CTkFrame(tab, corner_radius=12, fg_color=("white", "#1E1E2E"))
        notes_card.pack(fill="both", expand=True, padx=16, pady=12)

        ctk.CTkLabel(
            notes_card,
            text="Metric Definitions for Viva:",
            font=ctk.CTkFont(size=13, weight="bold")
        ).pack(anchor="w", padx=14, pady=(10, 4))

        notes_text = (
            "• Execution Time: Total elapsed search time in milliseconds (excluding GUI rendering).\n"
            "• Search Nodes: Number of calls to backtrack() in the state-space search tree.\n"
            "• Candidate Attempts: Number of value placements evaluated against constraints.\n"
            "• Backtracks: Number of times an assignment failed downstream and had to be unwound.\n"
            "• Constraint Checks: Row, column, and 3×3 box conflict evaluations performed."
        )
        txt = ctk.CTkLabel(notes_card, text=notes_text, justify="left", font=ctk.CTkFont(size=12))
        txt.pack(anchor="w", padx=14, pady=(0, 10))

    def _create_stat_row(self, parent: ctk.CTkFrame, title: str, default_val: str) -> ctk.CTkLabel:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=16, pady=6)
        ctk.CTkLabel(row, text=title, font=ctk.CTkFont(size=12, weight="bold")).pack(side="left")
        val_lbl = ctk.CTkLabel(
            row,
            text=default_val,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=("#2563EB", "#89B4FA")
        )
        val_lbl.pack(side="right")
        return val_lbl

    def _build_tab_theory(self) -> None:
        """Educational Panel: CSP theory, MRV, LCV, and constraints."""
        tab = self.tab_theory
        textbox = ctk.CTkTextbox(tab, wrap="word", font=ctk.CTkFont(size=12), activate_scrollbars=True)
        textbox.pack(fill="both", expand=True, padx=8, pady=8)

        theory_content = """CONSTRAINT SATISFACTION PROBLEMS (CSP) IN SUDOKU
==================================================

1. WHAT IS A CSP?
A Constraint Satisfaction Problem consists of three core components:
  • Variables (X): The set of variables {X1, X2, ..., Xn}.
  • Domains (D): The set of allowed values {D1, D2, ..., Dn} for each variable.
  • Constraints (C): The set of rules specifying allowable combinations of values.

In Sudoku:
  • Variables: The 81 grid cells (row, col) where 0 <= row, col < 9.
  • Domains: For each empty cell, a subset of {1, 2, 3, 4, 5, 6, 7, 8, 9}.
  • Constraints:
      - Row Constraint: All non-empty values in each row must be distinct.
      - Column Constraint: All non-empty values in each column must be distinct.
      - 3x3 Box Constraint: All non-empty values in each 3x3 box must be distinct.

2. MINIMUM REMAINING VALUES (MRV) HEURISTIC:
  • MRV (also called the "Most Constrained Variable" heuristic) chooses the
    unassigned cell with the smallest candidate domain.
  • Why? It minimizes the branching factor of the search tree. If a cell has
    only 1 candidate (a "naked single"), evaluating it immediately eliminates
    search without branching.
  • If an empty cell has 0 legal candidates, MRV detects the contradiction
    immediately and triggers backtracking without wasting time on unrelated cells.

3. LEAST CONSTRAINING VALUE (LCV) HEURISTIC:
  • Once a variable is selected, LCV orders its candidate values by how few
    options they rule out for neighboring unassigned cells in the same row,
    column, and 3x3 box.
  • Why? By choosing the value that leaves maximum flexibility for remaining
    variables, we maximize the probability of finding a valid solution on the
    first attempt without backtracking.

4. BACKTRACKING SEARCH:
  • A depth-first search that recursively assigns values to variables.
  • If any variable reaches an empty domain (dead end), the solver reverses
    (backtracks) to the preceding decision point, restores the cell to 0,
    and tries the next alternative candidate.

5. INVALID VS. VALID-BUT-UNSOLVABLE PUZZLES:
  • Invalid Puzzle: Contains direct constraint violations (duplicate digits
    in the same row, column, or 3x3 box).
  • Valid-but-Unsolvable Puzzle: Has no initial duplicate digits, but the
    constraint combination leaves zero solutions across the entire search space.
"""
        textbox.insert("1.0", theory_content)
        textbox.configure(state="disabled")

    def _build_tab_worked(self) -> None:
        """Educational Panel: Step-by-step worked domain reduction example."""
        tab = self.tab_worked
        textbox = ctk.CTkTextbox(tab, wrap="word", font=ctk.CTkFont(family="Consolas", size=12), activate_scrollbars=True)
        textbox.pack(fill="both", expand=True, padx=8, pady=8)
        textbox.insert("1.0", get_worked_example_text())
        textbox.configure(state="disabled")

    def _build_tab_flowchart(self) -> None:
        """Educational Panel: Algorithm flowchart and viva guide."""
        tab = self.tab_flowchart
        textbox = ctk.CTkTextbox(tab, wrap="none", font=ctk.CTkFont(family="Consolas", size=11), activate_scrollbars=True)
        textbox.pack(fill="both", expand=True, padx=8, pady=8)
        textbox.insert("1.0", get_csp_flowchart_text())
        textbox.configure(state="disabled")

    def _build_bottom_toolbar(self) -> None:
        """Create the bottom controls for normal mode and demo mode."""
        self.bottom_bar = ctk.CTkFrame(self, corner_radius=0, fg_color=("gray90", "#181825"))
        self.bottom_bar.pack(side="bottom", fill="x", padx=0, pady=0)

        # Standard Editing Controls Deck
        self.deck_normal = ctk.CTkFrame(self.bottom_bar, fg_color="transparent")
        self.deck_normal.pack(fill="x", padx=16, pady=8)

        # Sample Selector
        ctk.CTkLabel(self.deck_normal, text="Sample:", font=ctk.CTkFont(size=12, weight="bold")).pack(side="left", padx=(0, 6))

        self.sample_combo = ctk.CTkComboBox(
            self.deck_normal,
            values=list(SAMPLE_PUZZLES.keys()),
            width=200,
            command=self._on_sample_select
        )
        self.sample_combo.pack(side="left", padx=4)
        self.sample_combo.set("Easy")

        self.btn_load_sample = ctk.CTkButton(
            self.deck_normal,
            text="Load Sample",
            width=100,
            command=lambda: self._on_sample_select(self.sample_combo.get())
        )
        self.btn_load_sample.pack(side="left", padx=4)

        self.btn_clear = ctk.CTkButton(
            self.deck_normal,
            text="Clear Board",
            width=95,
            fg_color=("#EF4444", "#DC2626"),
            hover_color=("#DC2626", "#B91C1C"),
            command=self._on_clear_board
        )
        self.btn_clear.pack(side="left", padx=4)

        self.btn_validate = ctk.CTkButton(
            self.deck_normal,
            text="Validate Puzzle",
            width=110,
            fg_color=("#64748B", "#475569"),
            hover_color=("#475569", "#334155"),
            command=self._on_validate_puzzle
        )
        self.btn_validate.pack(side="left", padx=4)

        self.btn_reset = ctk.CTkButton(
            self.deck_normal,
            text="Reset",
            width=70,
            fg_color=("#6B7280", "#4B5563"),
            hover_color=("#4B5563", "#374151"),
            command=self._on_reset_board
        )
        self.btn_reset.pack(side="left", padx=4)

        # Primary Solvers
        self.btn_quick_solve = ctk.CTkButton(
            self.deck_normal,
            text="⚡ Quick Solve",
            width=120,
            font=ctk.CTkFont(weight="bold"),
            fg_color=("#0284C7", "#0284C7"),
            hover_color=("#0369A1", "#0369A1"),
            command=self._on_quick_solve
        )
        self.btn_quick_solve.pack(side="right", padx=6)

        self.btn_start_demo = ctk.CTkButton(
            self.deck_normal,
            text="🎬 Start Demo",
            width=120,
            font=ctk.CTkFont(weight="bold"),
            fg_color=("#8B5CF6", "#7C3AED"),
            hover_color=("#7C3AED", "#6D28D9"),
            command=self._on_start_demo
        )
        self.btn_start_demo.pack(side="right", padx=4)

        # Demonstration Controls Deck (Initially hidden)
        self.deck_demo = ctk.CTkFrame(self.bottom_bar, fg_color="transparent")

        self.btn_exit_demo = ctk.CTkButton(
            self.deck_demo,
            text="✕ Exit Demo",
            width=90,
            fg_color=("#EF4444", "#DC2626"),
            hover_color=("#DC2626", "#B91C1C"),
            command=self._on_exit_demo
        )
        self.btn_exit_demo.pack(side="left", padx=4)

        self.btn_restart_demo = ctk.CTkButton(
            self.deck_demo,
            text="↺ Restart",
            width=85,
            command=self._on_restart_demo
        )
        self.btn_restart_demo.pack(side="left", padx=4)

        self.btn_prev_step = ctk.CTkButton(
            self.deck_demo,
            text="⏮ Prev Step",
            width=100,
            command=self._on_prev_step
        )
        self.btn_prev_step.pack(side="left", padx=4)

        self.btn_play_pause = ctk.CTkButton(
            self.deck_demo,
            text="▶ Play",
            width=95,
            font=ctk.CTkFont(weight="bold"),
            fg_color=("#16A34A", "#15803D"),
            hover_color=("#15803D", "#166534"),
            command=self._on_toggle_play_pause
        )
        self.btn_play_pause.pack(side="left", padx=4)

        self.btn_next_step = ctk.CTkButton(
            self.deck_demo,
            text="Next Step ⏭",
            width=100,
            command=self._on_next_step
        )
        self.btn_next_step.pack(side="left", padx=4)

        self.btn_final_solution = ctk.CTkButton(
            self.deck_demo,
            text="Show Solution ⏩",
            width=120,
            command=self._on_show_final_solution
        )
        self.btn_final_solution.pack(side="left", padx=4)

        # Speed Slider
        ctk.CTkLabel(self.deck_demo, text="Speed:", font=ctk.CTkFont(size=11)).pack(side="left", padx=(12, 4))
        self.speed_slider = ctk.CTkSlider(
            self.deck_demo,
            from_=20,
            to=800,
            number_of_steps=20,
            width=110,
            command=self._on_speed_slider
        )
        self.speed_slider.pack(side="left", padx=4)
        self.speed_slider.set(250)

    def _build_status_bar(self) -> None:
        """Create the bottom status bar for user feedback and notifications."""
        self.status_bar = ctk.CTkFrame(self, height=26, corner_radius=0, fg_color=("gray85", "#11111B"))
        self.status_bar.pack(side="bottom", fill="x", padx=0, pady=0)

        self.lbl_status = ctk.CTkLabel(
            self.status_bar,
            text="Ready. Select a sample puzzle or click on cells to enter your own.",
            font=ctk.CTkFont(size=11),
            text_color=("#475569", "#A6ADC8")
        )
        self.lbl_status.pack(side="left", padx=16, pady=2)

    # =========================================================================
    # Theme & Canvas Callbacks
    # =========================================================================

    def _toggle_theme(self) -> None:
        """Switch between dark and light CustomTkinter mode."""
        if self.theme_mode == "dark":
            self.theme_mode = "light"
            ctk.set_appearance_mode("Light")
            self.theme_btn.configure(text="🌙 Dark Mode")
        else:
            self.theme_mode = "dark"
            ctk.set_appearance_mode("Dark")
            self.theme_btn.configure(text="☀ Light Mode")

        self.canvas.set_theme(self.theme_mode)

    def _on_user_cell_change(self, row: int, col: int, val: int) -> None:
        """Fired when user types into a cell on the board."""
        self.current_board[row][col] = val
        self.user_has_edited = True
        self.initial_puzzle[row][col] = val
        self.clues_mask[row][col] = (val != 0)

        # Invalidate old trace
        self.trace.clear()
        self.canvas.clear_highlights()
        self._update_cell_info(row, col)
        self._set_status(f"Updated {cell_to_name(row, col)} to {val if val != 0 else 'empty'}.")

    def _on_user_cell_select(self, row: int, col: int) -> None:
        """Fired when user clicks on a cell."""
        self._update_cell_info(row, col)

    def _update_cell_info(self, row: int, col: int) -> None:
        """Update the header domain badge for currently selected cell."""
        val = self.current_board[row][col]
        name = cell_to_name(row, col)
        domain = get_domain(self.current_board, row, col)
        val_str = str(val) if val != 0 else "Empty"
        dom_str = ", ".join(map(str, domain)) if domain else "None (Contradiction)"
        self.cell_info_lbl.configure(text=f"Cell: {name} ({val_str}) | Legal Domain: [{dom_str}]")

    def _set_status(self, text: str, is_error: bool = False, is_success: bool = False) -> None:
        color = ("#DC2626", "#F38BA8") if is_error else (("#16A34A", "#A6E3A1") if is_success else ("#475569", "#A6ADC8"))
        self.lbl_status.configure(text=text, text_color=color)

    # =========================================================================
    # Puzzle Board Management
    # =========================================================================

    def _load_board_data(self, board: List[List[int]], is_sample: bool = False) -> None:
        """Load puzzle data into internal state and canvas."""
        self.initial_puzzle = [row[:] for row in board]
        self.current_board = [row[:] for row in board]
        self.clues_mask = [[val != 0 for val in row] for row in board]
        self.user_has_edited = False
        self.trace.clear()

        self.canvas.set_board(self.current_board, is_clues=True)
        self.canvas.clear_highlights()
        self._update_cell_info(0, 0)

        # Reset stats
        self._update_stats_display(SolverStats())

    def _on_sample_select(self, choice: str) -> None:
        """Load selected sample puzzle with confirmation if user made edits."""
        if self.user_has_edited:
            if not messagebox.askyesno(
                "Confirm Load Sample",
                "You have unsaved changes on the board. Loading a sample puzzle will overwrite them. Proceed?"
            ):
                return

        puzzle = get_puzzle(choice)
        self._load_board_data(puzzle, is_sample=True)
        self._set_status(f"Loaded '{choice}' puzzle. Clues: {sum(1 for r in puzzle for c in r if c != 0)}.", is_success=True)

    def _on_clear_board(self) -> None:
        """Clear all cells on the board."""
        if any(c != 0 for row in self.current_board for c in row):
            if not messagebox.askyesno("Clear Board", "Are you sure you want to clear the entire board?"):
                return
        empty = [[0]*9 for _ in range(9)]
        self._load_board_data(empty)
        self._set_status("Board cleared. Ready for custom puzzle input.")

    def _on_reset_board(self) -> None:
        """Reset board back to initial loaded puzzle."""
        self.current_board = [row[:] for row in self.initial_puzzle]
        self.canvas.set_board(self.current_board, is_clues=True)
        self.canvas.clear_highlights()
        self.trace.clear()
        self._set_status("Board reset to initial puzzle clues.")

    def _on_validate_puzzle(self) -> None:
        """Check current board for row, column, or box constraint conflicts."""
        is_valid, msg, conflicts = validate_board(self.current_board)
        if not is_valid:
            self.canvas.set_conflicts(conflicts)
            self._set_status(f"Validation Error: {msg}", is_error=True)
            messagebox.showwarning("Puzzle Constraint Violation", msg)
        else:
            self.canvas.clear_highlights()
            if is_board_solved(self.current_board):
                self._set_status("Puzzle is completely and correctly solved!", is_success=True)
                messagebox.showinfo("Sudoku Solved", "Congratulations! The board is completely and correctly solved.")
            else:
                self._set_status(f"Valid configuration: {msg}", is_success=True)
                messagebox.showinfo("Validation Success", "Board is valid with no duplicate clues in any row, column, or 3x3 box.")

    # =========================================================================
    # Quick Solve Mode
    # =========================================================================

    def _on_quick_solve(self) -> None:
        """Solve Sudoku immediately and display final grid and statistics."""
        is_valid, msg, conflicts = validate_board(self.current_board)
        if not is_valid:
            self.canvas.set_conflicts(conflicts)
            self._set_status(f"Cannot solve: {msg}", is_error=True)
            messagebox.showerror("Invalid Puzzle", f"Cannot solve puzzle with constraint violations:\n\n{msg}")
            return

        if is_board_solved(self.current_board):
            self._set_status("Puzzle is already completely solved!", is_success=True)
            messagebox.showinfo("Already Solved", "The board is already completely solved.")
            return

        # Solve via CSP
        board_to_solve = [row[:] for row in self.current_board]
        success, solved_board, stats, _ = solve_sudoku(board_to_solve, record_trace=False)

        if success:
            self.current_board = solved_board
            self.canvas.set_board(solved_board, is_clues=False)
            self.canvas.set_clues(self.clues_mask)
            self.canvas.clear_highlights()

            self._update_stats_display(stats)
            self.tabview.set("Performance Statistics")

            status_msg = (
                f"Solved in {stats.execution_time_ms:.2f} ms | "
                f"Nodes: {stats.nodes_visited} | Backtracks: {stats.backtracks} | Checks: {stats.constraint_checks}"
            )
            self._set_status(status_msg, is_success=True)
            messagebox.showinfo("Puzzle Solved Successfully", status_msg)
        else:
            self._set_status("No solution exists for this board configuration.", is_error=True)
            messagebox.showwarning(
                "Unsolvable Puzzle",
                "The CSP solver exhausted all candidate branches without finding a valid solution.\n\n"
                "This puzzle is valid under initial constraints but mathematically unsolvable."
            )

    def _update_stats_display(self, stats: SolverStats) -> None:
        """Update labels on the Performance Statistics tab."""
        self.stat_time_lbl.configure(text=f"{stats.execution_time_ms:.2f} ms")
        self.stat_nodes_lbl.configure(text=str(stats.nodes_visited))
        self.stat_attempts_lbl.configure(text=str(stats.candidate_attempts))
        self.stat_success_lbl.configure(text=str(stats.successful_assignments))
        self.stat_backtracks_lbl.configure(text=str(stats.backtracks))
        self.stat_checks_lbl.configure(text=str(stats.constraint_checks))

    # =========================================================================
    # Step-by-Step Demonstration Mode
    # =========================================================================

    def _on_start_demo(self) -> None:
        """Generate deterministic trace and switch UI into demonstration mode."""
        is_valid, msg, conflicts = validate_board(self.current_board)
        if not is_valid:
            self.canvas.set_conflicts(conflicts)
            self._set_status(f"Cannot start demo: {msg}", is_error=True)
            messagebox.showerror("Invalid Puzzle", f"Cannot demonstrate solving with invalid clues:\n\n{msg}")
            return

        # Generate trace
        board_to_solve = [row[:] for row in self.current_board]
        success, solved_board, stats, trace = solve_sudoku(board_to_solve, record_trace=True, max_trace_steps=5000)

        if not trace:
            self._set_status("No trace generated (board might be already solved).")
            return

        self.trace = trace
        self.current_step_index = 0
        self.is_demo_mode = True
        self.is_playing = False

        # Switch toolbar deck
        self.deck_normal.pack_forget()
        self.deck_demo.pack(fill="x", padx=16, pady=8)

        # Configure scrub slider safely
        steps_count = len(self.trace)
        if steps_count > 1:
            self.scrub_slider.configure(from_=1, to=steps_count, number_of_steps=steps_count - 1)
        else:
            self.scrub_slider.configure(from_=1, to=2, number_of_steps=1)
        self.scrub_slider.set(1)

        # Disable direct canvas typing during demo
        self.canvas.interactive = False

        # Switch to Demo tab
        self.tabview.set("Demo Inspector & Trace")

        # Display first step
        self._display_step(0)
        self._set_status(f"Demonstration ready: {len(self.trace)} total algorithm events recorded.")

    def _on_exit_demo(self) -> None:
        """Exit demo mode and restore normal editing mode without losing initial puzzle."""
        self._stop_playback()
        self.is_demo_mode = False

        # Restore original board
        self.current_board = [row[:] for row in self.initial_puzzle]
        self.canvas.set_board(self.current_board, is_clues=True)
        self.canvas.clear_highlights()
        self.canvas.interactive = True

        # Switch back to normal toolbar deck
        self.deck_demo.pack_forget()
        self.deck_normal.pack(fill="x", padx=16, pady=8)

        self._set_status("Exited demonstration mode. Restored puzzle clues.")

    def _on_restart_demo(self) -> None:
        """Rewind demonstration to step 1."""
        self._stop_playback()
        self.current_step_index = 0
        self._display_step(0)
        self._set_status("Demonstration restarted to Step 1.")

    def _on_prev_step(self) -> None:
        """Step backward exactly one event, restoring previous board snapshot."""
        self._stop_playback()
        if self.current_step_index > 0:
            self.current_step_index -= 1
            self._display_step(self.current_step_index)

    def _on_next_step(self) -> None:
        """Step forward exactly one event."""
        self._stop_playback()
        if self.current_step_index < len(self.trace) - 1:
            self.current_step_index += 1
            self._display_step(self.current_step_index)
        else:
            self._set_status("Demonstration reached final event.")

    def _on_toggle_play_pause(self) -> None:
        """Toggle automatic playback of events."""
        if self.is_playing:
            self._stop_playback()
        else:
            self._start_playback()

    def _start_playback(self) -> None:
        """Start auto-stepping through trace events."""
        if self.current_step_index >= len(self.trace) - 1:
            # If at end, loop to beginning
            self.current_step_index = 0

        self.is_playing = True
        self.btn_play_pause.configure(
            text="⏸ Pause",
            fg_color=("#F59E0B", "#D97706"),
            hover_color=("#D97706", "#B45309")
        )
        self._schedule_next_tick()

    def _stop_playback(self) -> None:
        """Pause auto-stepping."""
        self.is_playing = False
        if self.play_timer_id is not None:
            self.after_cancel(self.play_timer_id)
            self.play_timer_id = None
        self.btn_play_pause.configure(
            text="▶ Play",
            fg_color=("#16A34A", "#15803D"),
            hover_color=("#15803D", "#166534")
        )

    def _schedule_next_tick(self) -> None:
        if self.is_playing:
            self.play_timer_id = self.after(self.play_delay_ms, self._demo_tick)

    def _demo_tick(self) -> None:
        """Advance one step during playback."""
        if not self.is_playing:
            return

        if self.current_step_index < len(self.trace) - 1:
            self.current_step_index += 1
            self._display_step(self.current_step_index)
            self._schedule_next_tick()
        else:
            self._stop_playback()
            self._set_status("Demonstration complete! Reached final solution.", is_success=True)

    def _on_speed_slider(self, val: float) -> None:
        """Adjust playback speed (inverted so higher slider = faster/lower ms delay)."""
        # slider from 20 to 800
        # Map: 20 -> 800ms, 800 -> 30ms
        self.play_delay_ms = max(20, int(820 - val))

    def _on_scrub_slider(self, val: float) -> None:
        """Jump to specific step from scrubber slider."""
        idx = int(round(val)) - 1
        idx = max(0, min(idx, len(self.trace) - 1))
        if idx != self.current_step_index:
            self._stop_playback()
            self.current_step_index = idx
            self._display_step(idx)

    def _on_show_final_solution(self) -> None:
        """Jump to the final trace event."""
        self._stop_playback()
        if self.trace:
            self.current_step_index = len(self.trace) - 1
            self._display_step(self.current_step_index)

    def _display_step(self, index: int) -> None:
        """Update all visual components to reflect the trace event at `index`."""
        if not (0 <= index < len(self.trace)):
            return

        event = self.trace[index]
        self.current_board = [row[:] for row in event.board_snapshot]

        # Update canvas
        self.canvas.set_board(self.current_board, is_clues=False)
        self.canvas.set_clues(self.clues_mask)
        self.canvas.set_step_highlight(event.cell, event.highlight_type)

        # Update inspector metadata
        info = format_step_explanation(event)
        self.lbl_step_number.configure(text=f"Step {event.step_number} / {len(self.trace)}")
        self.lbl_event_badge.configure(text=info["badge"])
        self.lbl_cell_target.configure(text=info["cell"])
        self.lbl_chosen_val.configure(text=info["chosen"])
        self.lbl_domain_list.configure(text=info["domain"])

        # Update text explanation
        self.txt_explanation.configure(state="normal")
        self.txt_explanation.delete("1.0", "end")
        self.txt_explanation.insert("1.0", event.explanation)
        self.txt_explanation.configure(state="disabled")

        # Update mini metrics
        self.lbl_live_nodes.configure(text=info["nodes"])
        self.lbl_live_assigns.configure(text=info["assignments"])
        self.lbl_live_backtracks.configure(text=info["backtracks"])
        self.lbl_live_checks.configure(text=info["checks"])

        # Update scrubber slider without re-triggering command
        self.scrub_slider.set(event.step_number)

    def _on_close(self) -> None:
        """Clean up background timers and safely close application."""
        self._stop_playback()
        self.destroy()


def main() -> None:
    app = SudoSolveApp()
    app.mainloop()


if __name__ == "__main__":
    main()
