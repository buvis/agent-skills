---
default_model: sonnet
rework_cap: 5
design: skip
---

# survey prunes skip-dirs at every depth

## Problem

`_scan_layers` in `skills/survey/scripts/run.py` applies `_SKIP_DIRS` (lines 29-39) and the
dot-directory skip only to the top-level `repo_path.iterdir()` comprehension on lines 43-47. The
per-layer walk on line 62, `[f for f in d.rglob("*") if f.is_file()]`, then descends into every
skipped name, so build output is enumerated and sampled: on this repo the `src` layer selected 6
files and 4 were `src/agent_skills_braid/__pycache__/*.pyc`. The brief a session reads therefore
calls compiled bytecode the source layout, and the walk is unbounded because `rglob` materialises
every path before the 50-file cap applies. Source: agoge run
dev/local/audit-results/agoge-2026-08-31.md, finding 25 (MEDIUM, performance lane) and finding 24
(MEDIUM, performance lane); decision 2026-09-02: prune inside the descent via `os.walk`, folding
finding 24 into that same traversal fix.

```
layer src  selected=6  of which build/dep output=4 - four
src/agent_skills_braid/__pycache__/*.pyc files, 67% of the layer.
rglob_paths_under_SKIP_DIRS=3826 of 5277 (72.5%) plus 69 under dot-dirs.
corpus200 -> rglob_entries=200, corpus400 -> 400, corpus800 -> 800, with
read_text_calls=100 and brief_bytes=1467 unchanged throughout.
Real repo: rglob_entries=5277, distinct_files_read=163 (3.1%).
```

## Solution

Replace the `d.rglob("*")` comprehension with an `os.walk` over each top-level directory that
mutates `dirnames` in place, dropping `_SKIP_DIRS` names and dot-prefixed names before the walker
descends. Rebuild each surviving file as `Path(dirpath) / filename` so callers keep getting `Path`
values. The walk avoids excluded subtrees; it still enumerates the surviving source tree before
applying the existing selection cap, so its remaining cost is proportional to eligible files.

## Requirements

### Must have
- No file with a `_SKIP_DIRS` segment or a dot-directory segment at any depth appears in a layer.
- `os.walk` never descends into a pruned directory, so the cost drops with the pruning.
- `_scan_layers` keeps its `(layers, truncated)` shape, its 50-file `_FILE_CAP`, and `Path` values.
- The depth-1 rule covered by `test_build_output_is_skipped_but_ordinary_dirs_are_not` still holds.

### Nice to have
- none

## Implementation

### Module: run.py
- **Location**: `skills/survey/scripts/`
- **Responsibility**: builds the layer map; owns the traversal and the skip lists
- **Exports**: `_scan_layers()`, `_SKIP_DIRS`

### Module: test_survey.py
- **Location**: `skills/survey/scripts/`
- **Responsibility**: behavioral tests for the brief generator
- **Exports**: `test_skip_dirs_are_pruned_at_every_depth()`, `test_pruned_directories_are_never_descended_into()`

### Dependencies
- run.py: No dependencies (foundation)
- test_survey.py: Depends on [run.py]

## Tasks

### Phase 0: Foundation

- [ ] Replace the `d.rglob("*")` comprehension in `_scan_layers` with an `os.walk` that removes `_SKIP_DIRS` names and dot-prefixed names from `dirnames` in place at every level, rebuilding files as `Path(dirpath) / filename` - Acceptance: `rg -n "rglob" skills/survey/scripts/run.py` prints no match; `rg -n "os.walk" skills/survey/scripts/run.py` matches a line inside `_scan_layers`; `uv run pytest skills/survey/scripts/test_survey.py -q` reports 0 failed and 0 errors.
- [ ] Add `test_skip_dirs_are_pruned_at_every_depth` to `skills/survey/scripts/test_survey.py`, building a repo holding `src/real.py`, `src/node_modules/pkg/junk.js`, `src/build/out.py` and `src/.venv/lib/dep.py` - Acceptance: the test asserts `[p.name for p in run._scan_layers(repo)[0]["src"]] == ["real.py"]`, and `uv run pytest "skills/survey/scripts/test_survey.py::test_skip_dirs_are_pruned_at_every_depth" -q` passes.
- [ ] Add `test_pruned_directories_are_never_descended_into` to the same file, monkeypatching `run.os.walk` with a wrapper that records every yielded `dirpath` and delegates to the real `os.walk` - Acceptance: the test asserts no recorded `dirpath` has a segment in `run._SKIP_DIRS` or a segment starting with `.`, and `uv run pytest "skills/survey/scripts/test_survey.py::test_pruned_directories_are_never_descended_into" -q` passes.

### Phase 1: Core

No additional work; the Phase 0 tasks deliver this capability and its regression coverage.

## Success Criteria

- `uv run pytest skills/survey/scripts/test_survey.py -q` reports 0 failed and 0 errors, including
  both new tests.
- `rg -n "rglob" skills/survey/scripts/run.py` prints no match.
- `uv run pytest "skills/survey/scripts/test_survey.py::test_build_output_is_skipped_but_ordinary_dirs_are_not" -q`
  still passes, so the depth-1 behaviour is unchanged.
- Briefs sample different files after this change; that difference is the fix, so any shifted
  `test_survey.py` expectation is updated in the task that shifts it.

## Post-completion notes (2026-09-07)

Converged (batch 202609050909); two deferred rows walked 2026-09-07 in the config-audit closure walkthrough
(`~/.claude/dev/local/audit-results/2026-09-05.md`). The ledger's decision fields get backfilled at batch end.

- `test_survey.py` is over the 800-line cap (855 before this PRD, 1022 after, 1073 by 2026-09-07): PRD 00079
  splits it by concern with the collected test count as the contract.
- The residual overlapping pruning tests stay: the reviewers judged the parametrized cases broader real
  coverage than the PRD-mandated one. Accepted.
