# SudoSolve — Sudoku Solver Using Constraint Satisfaction Problems (CSP)

A modern desktop application built with Python and CustomTkinter demonstrating the **Constraint Satisfaction Problem (CSP)** formulation of Sudoku.

Developed for academic demonstration, practical exams, and viva voce defense.

---

## 1. Project Overview & Features

- **Desktop-Native GUI:** Pure Python desktop interface built with `CustomTkinter` and `Tkinter` Canvas. **No web framework, no Streamlit, Flask, or browser needed.**
- **Dual Solving Modes:**
  1. **Step-by-Step Demonstration:** Real-time visual walkthrough of the search tree. Visually inspects MRV variable selection, candidate domain calculation, LCV ordering, assignments, constraint checking, and backtracking unwinding.
  2. **Quick Solve:** Instant solution with high-precision metrics (execution time in milliseconds, recursive search nodes, backtracks, and constraint checks).
- **Interactive 9×9 Sudoku Grid:**
  - High-contrast 3×3 box boundaries.
  - Interactive cell editing with keyboard input (`1-9` to enter, `0` or `Backspace/Delete` to clear, `Arrow keys` to navigate).
  - Visual distinction between original clues and solver-generated numbers.
  - Multi-state cell highlighting: Active variable, soft peer constraints (row, column, and box), candidate assignments, rejected candidates, backtracks, and rule violations.
- **Academic Educational Panel:**
  - Tabbed interface with CSP theory, MRV/LCV heuristic comparisons, worked domain calculation, and viva flowchart.
- **Dark & Light Mode:** Seamless toggle with custom-tuned color palettes for optimal visibility.

---

## 2. CSP Formulation in Sudoku

Sudoku is formally modeled as a **Constraint Satisfaction Problem $\langle X, D, C \rangle$**:

1. **Variables ($X$):**
   The 81 cells on the grid, indexed by $(r, c)$ where $r, c \in \{0, 1, \dots, 8\}$.
2. **Domains ($D$):**
   For each empty cell $(r, c)$, $D(r, c) \subseteq \{1, 2, 3, 4, 5, 6, 7, 8, 9\}$ containing only values that do not violate any constraint with already assigned peers.
3. **Constraints ($C$):**
   - **Row Constraint:** $\text{All-Different}(\text{Row } r)$ for each $r \in [0, 8]$.
   - **Column Constraint:** $\text{All-Different}(\text{Column } c)$ for each $c \in [0, 8]$.
   - **3×3 Box Constraint:** $\text{All-Different}(\text{Box } b)$ for each 3×3 block.

### Heuristics Implemented

- **Minimum Remaining Values (MRV):**
  Also known as the *"Most Constrained Variable"* heuristic. At each step, the solver selects the unassigned variable with the smallest legal domain size:
  $$\text{cell} = \arg\min_{(r,c) \in \text{unassigned}} |D(r, c)|$$
  *Why MRV?* It drastically prunes the branching factor of the search tree. If a cell has domain size 1 (a naked single), MRV fills it immediately. If a cell has domain size 0 (a contradiction), MRV immediately triggers backtracking without exploring doomed subtrees. Ties are broken deterministically by coordinate order.

- **Least Constraining Value (LCV):**
  Once an unassigned cell is chosen, candidate values from its domain are ordered by the number of choices they rule out for neighboring unassigned cells.
  *Why LCV?* Values that leave maximum flexibility for peer cells are evaluated first, maximizing the chance of finding a valid solution on the first branch.

---

## 3. Installation & Execution (Windows)

### Prerequisites
- Python 3.11 or later (Tested with Python 3.11 - 3.14 on Windows).

### Step 1: Create Virtual Environment
Open PowerShell or Command Prompt in the project folder:
```powershell
python -m venv .venv
```

### Step 2: Activate the Virtual Environment
```powershell
.venv\Scripts\activate
```

### Step 3: Install Dependencies
```powershell
python -m pip install -r requirements.txt
```

### Step 4: Run the Application
```powershell
python main.py
```

### Step 5: Run Automated Tests
```powershell
pytest -v
```

---

## 4. Step-by-Step Algorithm Walkthrough (Worked Example)

### Domain Reduction Example: Cell R3C5

Suppose we want to compute the domain for cell `R3C5` (Row 3, Column 5):

1. **Initial Domain:**
   $$D = \{1, 2, 3, 4, 5, 6, 7, 8, 9\}$$
2. **Row 3 Constraint:**
   Row 3 already contains the numbers $\{1, 4, 7\}$.
   $$D' = D \setminus \{1, 4, 7\} = \{2, 3, 5, 6, 8, 9\}$$
3. **Column 5 Constraint:**
   Column 5 already contains the numbers $\{2, 5, 8\}$.
   $$D'' = D' \setminus \{2, 5, 8\} = \{3, 6, 9\}$$
4. **3×3 Box Constraint (Top-Middle Box):**
   The top-middle box already contains the numbers $\{3, 7\}$.
   $$D''' = D'' \setminus \{3\} = \{6, 9\}$$
5. **Final Result:**
   Cell `R3C5` has legal candidate domain $\{6, 9\}$ with domain size $= 2$.

### Demonstration of Backtracking Unwinding

When using the built-in **Hard (Backtracking Demo)** sample puzzle:
1. At Step 31, the solver reaches cell `R7C2` with domain `[1, 5]`.
2. LCV selects candidate `1`.
3. Downstream at Step 35, cell `R8C1` has zero valid candidates remaining (Domain $= \emptyset$).
4. The solver flags a **Contradiction / Dead End**, increments the backtrack counter, undoes assignment of `1` at `R7C2`, and tries candidate `5`.
5. The demonstration mode captures this exact state transition: the board is restored and the failed candidate is flagged.

---

## 5. Project Architecture

```
AI_micro_FINAL/
├── main.py              # CustomTkinter GUI, application state, and event loops
├── solver.py            # Core CSP solver, MRV, LCV, backtracking, trace generator
├── visualization.py     # Interactive Sudoku canvas, theme palettes, flowchart text
├── puzzles.py           # Verified sample puzzle database (Easy, Medium, Hard, Expert)
├── requirements.txt     # Python package requirements
├── README.md            # Comprehensive documentation and viva guide
├── tests/
│   └── test_solver.py   # 15 automated pytest tests covering all requirements
└── sudosolve/           # Modular package distribution
    ├── __init__.py
    ├── main.py
    ├── solver.py
    ├── visualization.py
    └── puzzles.py
```

---

## 6. Performance Statistics & Metrics

| Metric | Definition |
| :--- | :--- |
| **Execution Time (ms)** | High-precision search duration measured using `time.perf_counter()`. Excludes GUI draw times. |
| **Search Nodes** | Total calls to the recursive `backtrack()` search function. |
| **Candidate Attempts** | Number of value placements tested against constraints. |
| **Successful Assignments** | Number of assignments that passed row, column, and box constraints. |
| **Backtracks** | Number of times an assignment failed downstream and was unwound (reset to 0). |
| **Constraint Checks** | Row, column, and 3×3 box conflict checks evaluated. |

---

## 7. Viva Voce Questions & Answers

**Q1: Why is Sudoku represented as a CSP instead of standard brute-force search?**
> Standard brute-force explores $9^{81}$ configurations without guidance. In a CSP, constraints prune impossible states early, and heuristics like MRV drastically reduce the branching factor from 9 down to 1 or 2, solving most puzzles in under 10 milliseconds.

**Q2: What is the difference between an invalid puzzle and a valid but unsolvable puzzle?**
> An *invalid puzzle* violates constraints immediately (e.g., duplicate digit in the same row, column, or 3×3 box). A *valid-but-unsolvable puzzle* has no initial duplicates, but the combination of clues leaves no complete assignment that satisfies all constraints across all 81 cells.

**Q3: How does the step-by-step demonstration restore previous states?**
> The solver records a deterministic trace of immutable `TraceEvent` snapshots during the search. Clicking **Previous Step** reads the exact previous board and counter snapshot from the trace array without re-running the solver, ensuring 100% deterministic, lag-free scrubbing.

---

## 8. Automated Testing

All 15 automated test cases in `tests/test_solver.py` pass cleanly:

```powershell
pytest -v
```

Test coverage includes:
- Valid solvable puzzles (Easy, Medium, Hard).
- Duplicate clues in a row.
- Duplicate clues in a column.
- Duplicate clues in a 3×3 box.
- Valid but mathematically unsolvable puzzles.
- Empty 9×9 board.
- Already solved board.
- Puzzle requiring genuine backtracking.
- Verification of cell restoration after failed branch.
- Clue preservation (original clues never altered).
- Mathematical validity of all generated solutions.
- Trace snapshot and statistics consistency.
- Non-9×9 dimension validation.
- Invalid non-digit value handling.
- LCV ordering logic verification.
