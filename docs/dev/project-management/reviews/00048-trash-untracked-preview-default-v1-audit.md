# Decision Audit Log: 00048-trash-untracked-preview-default-v1

PRD: `00048-trash-untracked-preview-default-v1.md`
Started: 2026-10-18T16:46:46Z
Completed: 2026-10-18T16:46:46Z
Autonomous: 4  |  Deferred: 1  |  Doubts: 0

### [autonomous] 2026-10-18T16:46:46Z

**Decision**: Cycle 1 converged (no CRITICAL/HIGH, doubt-roster constraint certified); 5 low findings settled in the ledger as accepted limitations or documented notes

**Choice**: settled, no task

**Rationale**: Each is recorded by the design doc, the docstring or the PRD itself as accepted or as a human follow-up; the raising reviewer agrees no change is needed.

### [autonomous] 2026-10-18T16:46:46Z

**Decision**: The new tests are redundant, beyond the PRD's two named tests. `test_dry_run_without_apply_leaves_the_file_and_writes_no_trash` duplicates `test_preview_moves_nothing`. `test_dry_run_preview_and_apply_report_identical_moved_and_refused` overlaps `test_preview_json_matches_the_apply_run`. Five more `test_dry_run_*` tests plus seven `trash_dest` and `relocate` tests also go beyond the PRD. Merge the overlapping ones and drop the duplicates to cut about 100 lines. The `test_dry_run_with_apply_*` names also contradict their own content.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T16:46:46Z

**Decision**: The CHANGELOG has no entry. `trash_untracked.py` now previews by default, so any caller without `--apply` silently stops moving files. That is a user-visible breaking change, and the repo CHANGELOG already carries brush entries for this script (CHANGELOG.md:473). Add a `### Changed` line under `[Unreleased]` such as "**brush**: `trash_untracked.py` previews by default; pass `--apply` to move".

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T16:46:46Z

**Decision**: `_expected_trash` and several tests compute the date with `datetime.date.today()` while `main()` computes its own. A run that crosses midnight can flake. The build session already noted this. Freeze the date or compare against the date taken from the output.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [deferred] 2026-10-18T16:46:46Z

**Decision**: Uncommitted glean reformatting outside PRD 00048 range (also pushes cmd_scan to 54 lines)

**Choice**: deferred to batch end

**Rationale**: Working-tree drift predating this PRD; committing or reverting another session unreviewed work is the operator call, not this gate.
