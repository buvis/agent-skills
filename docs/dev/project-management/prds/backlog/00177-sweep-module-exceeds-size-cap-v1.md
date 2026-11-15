---
design: skip
default_model: sonnet
model_tier_rationale: verbatim move of six pure functions and one constant; the existing render tests pin the output
---

# sweep.py is over the module size cap

Source: `docs/dev/project-management/reviews/00134-empty-sweep-lacks-verification-marker-v1-review-1.md`,
finding F5 (four reviewers), recorded 2026-11-15.

## Problem

`skills/sweep-fix/scripts/sweep.py` held 828 lines on 2026-11-15; the project
cap is 800 lines per file. Each sweep-fix change since PRD 00104 added to it,
and PRD 00178 will add more. Reviews keep raising the overrun, and no bounded
fix can clear it without moving code out.

## Solution

Move the report rendering block into a new sibling module, verbatim. The block
is pure string formatting with three outside dependencies. `sweep.py` imports
the two public names back, so `sweep.render_report` and
`sweep.DEADLINE_REASON` keep resolving for the script and for every test.

## Requirements

### Must have
- `skills/sweep-fix/scripts/sweep.py` holds at most 800 lines.
- The rendered report is byte-identical for every input the existing render tests cover.
- `sweep.render_report` and `sweep.DEADLINE_REASON` still resolve.
- No test file changes.

### Nice to have
- None.

## Implementation

### Module: sweep report rendering
- **Location**: `skills/sweep-fix/scripts/sweep_report.py`
- **Responsibility**: render the plain-text sweep report from scan results; own the deadline reason text the partial section compares against.
- **Exports**: `render_report`, `DEADLINE_REASON`
- New symbols: `sweep_report.py`

### Module: sweep
- **Location**: `skills/sweep-fix/scripts/sweep.py`
- **Responsibility**: scan, control verification and the command line; imports the report names from the module above.
- **Exports**: `main`, `scan`, `verify_control`, `render_report`, `DEADLINE_REASON`

### Dependencies
- sweep report rendering: depends on `skills/sweep-fix/scripts/sweep_rule_pack.py` only (foundation)
- sweep: depends on [sweep report rendering]

## Tasks

### Phase 0: Foundation
- [ ] Create `skills/sweep-fix/scripts/sweep_report.py`. Premise: in `skills/sweep-fix/scripts/sweep.py` the functions `_render_hits_section`, `_render_suppressed_section`, `_render_partial_section`, `_render_failed_section`, `_render_gaps_section` and `render_report` use no module-level name other than `Path`, `DEADLINE_REASON` and `_render_astgrep_rule_block`, and no test patches any of them on the `sweep` module. Re-check both at execution (read the block; `rg -n "setattr\(sweep[^)]*(DEADLINE_REASON|_render_|render_report)" skills/sweep-fix` prints nothing). If either premise fails, stop and report; do not force the move. The new file holds `from pathlib import Path`, `from sweep_rule_pack import _render_astgrep_rule_block`, the line `DEADLINE_REASON = "sweep deadline expired"`, and the six functions copied without any change. - Acceptance: `uv run python -c "import sys; sys.path.insert(0, 'skills/sweep-fix/scripts'); import sweep_report; print(sweep_report.DEADLINE_REASON)"` prints `sweep deadline expired`.

### Phase 1: Core
- [ ] In `skills/sweep-fix/scripts/sweep.py` delete the six function definitions and the `DEADLINE_REASON` assignment, replace the line `from sweep_rule_pack import _render_astgrep_rule_block` with `from sweep_report import DEADLINE_REASON, render_report`, and change nothing else (depends on: Phase 0) - Acceptance: `uv run pytest skills/sweep-fix/scripts/test_sweep_render_report.py skills/sweep-fix/scripts/test_sweep_main.py` passes; `awk 'END { exit NR > 800 }' skills/sweep-fix/scripts/sweep.py` exits 0; `rg -c "^def _render_|^def render_report" skills/sweep-fix/scripts/sweep.py` prints nothing; `git diff --stat` names no `test_` file.

## Success Criteria

- `skills/sweep-fix/scripts/sweep.py` is at most 800 lines and the new module holds the moved block unchanged.
- `uv run python scripts/gate.py` ends with `FAIL 0` and `EXIT 0`.
- `uv run python3 skills/create-skill/scripts/validate_skill.py skills/sweep-fix` reports the skill valid.
