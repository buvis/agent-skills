---
default_model: opus
rework_cap: 5
---

# Give `trash_untracked` a preview default behind `--apply`

## Problem

`skills/brush/scripts/trash_untracked.py` builds its parser inline in `main()`
(lines 88-93) with only `--repo`, `--rule`, `--min-age-days` and positional
`paths`; there is no `--apply` and no `--dry-run`, and `main()` calls
`relocate()` on the first pass (line 109), so every invocation moves files at
once. The report packet names a `_parse_args` function; no such symbol exists
in this file. The destructive half of the brush pair has no preview while the
less destructive sibling `skills/purge-devlocal/scripts/purge_devlocal.py`
defaults to dry-run and prints `DRY-RUN (use --apply)` (line 534). Source:
agoge run `dev/local/audit-results/agoge-2026-08-31.md`, finding 44 (LOW,
security lane); decision 2026-09-02: add `--apply`, default to preview, and
update every documented call site in the same change.

```
Every probe in this run moved files on the first invocation with no preview
step - e.g. {"moved": [{"path":"sub/../dev/local/tmp/marker.json", ...}]}
with the file gone from its original path. Its sibling purge_devlocal.py
defaults to dry-run and prints DRY-RUN (use --apply).
```

## Solution

Add `--apply` and make its absence a preview. Preview runs the same loop and
takes the same veto decisions but calls neither `relocate()` nor
`note_manifest()`, so the tree is untouched while stdout carries the identical
`{"moved": ..., "refused": ...}` JSON a caller can diff against the run that
follows. Reporting the destination without moving needs the path arithmetic
split out of `relocate()` into a `trash_dest(root, rel, date)` helper. Both documented call
sites gain `--apply` in the same change, since a missed caller turns silently
into a no-op.

## Requirements

### Must have

- Without `--apply` nothing on disk changes: no file moves, `dev/local/.trash/`
  is not created, and no manifest row is appended.
- Preview stdout is the same JSON, with the same `path`, `trash` and `reason`
  values the immediately following `--apply` run prints for the same corpus.
- Preview prints the marker `DRY-RUN (use --apply)`, the wording at
  `purge_devlocal.py:534`, on stderr so stdout stays parseable JSON.
- `--apply` is `action="store_true"` with help text `move files to .trash
  (default: dry-run)`, matching `purge_devlocal.py:481-485`; with it, behaviour
  and output match today's.
- `skills/brush/SKILL.md:62` and `skills/brush/references/report-template.md:27`
  both pass `--apply` in the same change.

### Nice to have

- none

## Implementation

### Module: trash_untracked
- **Location**: `skills/brush/scripts/`
- **Responsibility**: veto, move and record paths; previews unless `--apply`
- **Exports**: `trash_dest()`, `relocate()`, `main()`

### Module: test_brush_scripts
- **Location**: `skills/brush/scripts/`
- **Responsibility**: regression net for the brush helper scripts
- **Exports**: `test_preview_moves_nothing`, `test_preview_json_matches_the_apply_run`

### Module: brush-skill-doc
- **Location**: `skills/brush/`
- **Responsibility**: the Phase-2 instruction naming the sanctioned trash command
- **Exports**: the `trash_untracked.py` invocation on `SKILL.md:62`

### Module: brush-report-template
- **Location**: `skills/brush/references/`
- **Responsibility**: the BR-item command shape brush copies into its report
- **Exports**: the BR-3 `cmd:` invocation on `report-template.md:27`

### Dependencies
- trash_untracked: No dependencies (foundation). PRD 00012 edits the same file
  under a lower number, so it lands first; its tests drive `main()` through a
  monkeypatched `sys.argv`, which these tests reuse.
- test_brush_scripts: Depends on [trash_untracked]
- brush-skill-doc: Depends on [trash_untracked]
- brush-report-template: Depends on [trash_untracked]

## Tasks

### Phase 0: Foundation
- [ ] Split the destination arithmetic out of `relocate()` into `trash_dest(root, rel, date) -> Path` (the `dev/local/.trash/<date>/<rel>` join plus the `.dup<ts>` collision suffix) and have `relocate()` call it - Acceptance: `uv run pytest "skills/brush/scripts/test_brush_scripts.py::test_relocate_writes_manifest_row" -q` reports `1 passed` with no edit to that test.
- [ ] Add `--apply` to the parser in `main()` with `action="store_true"` and help `move files to .trash (default: dry-run)`, gate the `relocate()` and `note_manifest()` calls behind it, fill the `trash` field from `trash_dest()` in both modes, and print `DRY-RUN (use --apply)` to stderr when `--apply` is absent - Acceptance: `uv run pytest skills/brush/scripts/test_brush_scripts.py -q` ends with a summary line containing neither `failed` nor `error`.
- [ ] Add `test_preview_moves_nothing`: an aged `old_junk.log`, `sys.argv` monkeypatched to `["trash_untracked.py", "--repo", str(repo), "old_junk.log"]`, `tu.main()` called - Acceptance: `uv run pytest "skills/brush/scripts/test_brush_scripts.py::test_preview_moves_nothing" -q` reports `1 passed`; `repo / "old_junk.log"` still exists, `repo / "dev/local/.trash"` does not exist, and the parsed stdout holds exactly one `moved` entry whose `path` is `old_junk.log`.
- [ ] Add `test_preview_json_matches_the_apply_run`: the same corpus, `main()` driven once without `--apply` and once with it, both stdouts parsed - Acceptance: `uv run pytest "skills/brush/scripts/test_brush_scripts.py::test_preview_json_matches_the_apply_run" -q` reports `1 passed`; the two parsed objects compare equal, and `repo / "dev/local/.trash/manifest.tsv"` exists only after the second run.
- [ ] Add `--apply` to the two documented invocations. Premise: `rg -n "trash_untracked.py --repo" skills/brush` matches exactly two lines, `skills/brush/SKILL.md:62` and `skills/brush/references/report-template.md:27`, and neither carries `--apply`; if the re-check at execution time returns any other set of lines, skip the edit and report it - Acceptance: `rg -n "trash_untracked.py --repo" skills/brush` prints exactly those two lines and both contain `--apply`.
- [ ] Run the repo suite - Acceptance: `uv run pytest -q` from the repo root ends with a summary line containing neither `failed` nor `error`.

## Success Criteria

- A preview run leaves every file at its original path and writes no
  `dev/local/.trash/`, while printing the JSON the `--apply` run then prints.
- `rg -n "trash_untracked.py --repo" skills/brush` shows `--apply` on both
  documented call sites.
- `uv run pytest -q` from the repo root reports no failures and no errors.
- Human follow-up: a caller outside this repo keeps working only if it adds
  `--apply`; the flip is silent to such a caller and the in-repo sweep above
  cannot see it.
