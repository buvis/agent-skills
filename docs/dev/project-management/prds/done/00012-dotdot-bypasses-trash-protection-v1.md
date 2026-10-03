---
default_model: opus
rework_cap: 5
---

# Normalise the path `trash_untracked` vetoes, moves and records

## Problem

`skills/brush/scripts/trash_untracked.py` checks containment on the resolved
path (lines 101-102) but every protection on the raw string (`veto_reason`,
line 57), then moves the raw string (`relocate`, line 75). A `sub/../` prefix
passes containment, misses `PROTECT_PREFIXES` and lands on the protected file,
so `dev/local/`, `docs/` and `.git/` are reachable from any caller that joins
relative paths. The manifest keeps the unnormalised destination that
`mkdir(parents=True)` normalised away, so the docstring's restore line (line 9)
cannot work there. Source: agoge run
`dev/local/audit-results/agoge-2026-08-31.md`, finding 2 (HIGH, security lane);
decision 2026-09-02: normalise once, then use one path everywhere.

```
Same file, two spellings, opposite outcomes: dev/local/tmp/marker.json ->
{"refused": [{"reason": "protected path (dev/local, docs, .git)"}]};
sub/../dev/local/tmp/marker.json -> {"moved": [{"trash": ".../2026-08-31/
sub/../dev/local/tmp/marker.json"}]}, and the original is gone.
```

## Solution

`veto_reason` normalises its own `rel` before the tracked, prefix, suffix and
glob checks, so a direct caller is covered too: the authored test calls it
directly, and a fix confined to `main()` would leave that test red. `main()`
then computes `rel = os.path.relpath(p, root)` once after the containment check
and hands that `rel` to `veto_reason`, `relocate` and `note_manifest`, ending
the raw/resolved split behind both defects.

## Requirements

### Must have

- `veto_reason("sub/../dev/local/keep.bin", ...)` returns `protected path
  (dev/local, docs, .git)`, the string the plain spelling already gets.
- `main()` derives `rel` once and reports it in every `moved` and `refused`
  entry; the `outside repo` refusal keeps the caller's own spelling.
- Every manifest row's fourth column names an existing file under
  `dev/local/.trash/<date>/`.
- The strict-xfail marker above the authored test, which sits on master
  (merged in 636d94f), goes away in the same change.

### Nice to have

- none

## Implementation

### Module: trash_untracked
- **Location**: `skills/brush/scripts/`
- **Responsibility**: veto, move and record one repo-relative path per call
- **Exports**: `veto_reason()`, `relocate()`, `note_manifest()`, `main()`

### Module: test_brush_scripts
- **Location**: `skills/brush/scripts/`
- **Responsibility**: regression net for the brush helper scripts
- **Exports**: `test_veto_devlocal_protected_through_a_dotdot_segment`, `test_main_refuses_a_protected_path_spelled_through_dotdot`, `test_manifest_row_names_the_file_that_was_moved`

### Dependencies
- trash_untracked: No dependencies (foundation)
- test_brush_scripts: Depends on [trash_untracked]

## Tasks

### Phase 0: Foundation
- [ ] Normalise `rel` at the top of `veto_reason` and delete the strict-xfail marker above `test_veto_devlocal_protected_through_a_dotdot_segment` - Acceptance: `uv run pytest "skills/brush/scripts/test_brush_scripts.py::test_veto_devlocal_protected_through_a_dotdot_segment" -q` reports `1 passed`, and `rg -n "xfail" skills/brush/scripts/test_brush_scripts.py` prints no output.
- [ ] Compute `rel = os.path.relpath(p, root)` in `main()` after the `is_relative_to` check and pass that one string to `veto_reason`, `relocate` and `note_manifest` - Acceptance: `rg -n "os.path.relpath" skills/brush/scripts/trash_untracked.py` matches exactly one line, and `uv run pytest skills/brush/scripts/test_brush_scripts.py -q` ends with a summary line containing neither `failed` nor `error`.
- [ ] Add `test_main_refuses_a_protected_path_spelled_through_dotdot`: aged `dev/local/keep.bin` plus an empty `sub/`, `sys.argv` monkeypatched to `["trash_untracked.py", "--repo", str(repo), "sub/../dev/local/keep.bin"]`, `tu.main()` called, stdout parsed with `json.loads` - Acceptance: `uv run pytest "skills/brush/scripts/test_brush_scripts.py::test_main_refuses_a_protected_path_spelled_through_dotdot" -q` reports `1 passed`; the parsed JSON has `moved == []` and one `refused` entry whose `path` is `dev/local/keep.bin` and whose `reason` is `protected path (dev/local, docs, .git)`; `repo / "dev/local/keep.bin"` still exists.
- [ ] Add `test_manifest_row_names_the_file_that_was_moved`: aged `old_junk.log` plus an empty `sub/`, `main()` driven the same way with `sub/../old_junk.log` - Acceptance: `uv run pytest "skills/brush/scripts/test_brush_scripts.py::test_manifest_row_names_the_file_that_was_moved" -q` reports `1 passed`; `dev/local/.trash/manifest.tsv` holds one row whose third column is `old_junk.log`, the path in its fourth column exists under the repo root, and `uv run pytest -q` from the repo root ends with neither `failed` nor `error`.

## Success Criteria

- `uv run pytest -q` reports no failures and no errors, and `rg -n "xfail"
  skills/brush/scripts/test_brush_scripts.py` prints nothing.
- Both spellings of a protected path get the same `refused` reason, and the
  reported `path` is the normalised one.
- Every manifest row names an existing file, so the docstring restore line
  (`trash_untracked.py:9`) and the "it re-vetoes protected paths itself" claim
  (`skills/brush/SKILL.md:63`) hold again with no doc edit.
- `../` callers see a changed `path` spelling; the two call sites listed by
  `rg -n "trash_untracked.py --repo" skills/brush` do not read the JSON.
