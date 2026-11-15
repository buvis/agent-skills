---
design: run
default_model: opus
model_tier_rationale: a new flag and a pre-image export are invented contracts on a verification path, with temporary files to remove on every exit path
eligibility: test -f docs/dev/project-management/prds/done/00177-sweep-module-exceeds-size-cap-v1.md
---

# A clean sweep can never be verified

Source: `docs/dev/project-management/reviews/00134-empty-sweep-lacks-verification-marker-v1-review-1.md`,
findings K1 and K2 (doubt review), recorded 2026-11-15. Runs after PRD 00177,
which brings `skills/sweep-fix/scripts/sweep.py` back under the size cap.

## Problem

The documented invocation passes the current repo as `--control-repo`, and
`enumerate_repos` always sweeps the current repo too. So a zero-hit sweep has
no way to exit 0. If the control term is absent, the report is saved as
unverified and the exit is 1. If the control term is present, the script
aborts as a broken pattern. If the pattern matches the control repo, the sweep
is no longer zero-hit. Since PRD 00134 closed the one false exit 0, an
operator can never get a verified "the portfolio is clean" result, which is
the result the skill exists to give.

A second defect makes it worse. The control-term search reads the whole
control repo, including the reports saved under
`docs/dev/project-management/audit-results/`. A saved report quotes the
pattern and the reason, so a rerun can find the control term in the first
run's report and flip from "unverified" to "broken pattern".

## Solution

Verify the pattern against the fix's pre-image instead of the live tree. A new
optional flag names the fix commit. The script exports the files that commit
changed, as they were in its first parent, into a temporary directory outside
every swept repo, and runs the existing control check on that directory. The
pre-image still holds the bug, so a correct pattern matches there; that proves
the pattern, and the zero-hit sweep can exit 0. Without the flag the script
behaves as today. The control-term search also skips saved reports, using the
exclusion the scan already applies.

## Requirements

### Must have
- With `--control-rev REV` (guess: flag name), a zero-hit sweep whose pattern matches the pre-image saves a report with no `Unverified:` line and exits 0.
- With the flag, a pattern that misses the pre-image while the control term is present there still aborts as a broken pattern: exit 1, one stderr line, no report.
- With the flag, a pre-image holding neither the pattern nor the control term still saves the report with `Unverified: control term not found` and exits 1.
- The export uses read-only git commands. It never changes the index, the working tree or any ref of `--control-repo`.
- The temporary directory is outside every swept repo and is removed on every exit path, including errors and an expired `--deadline`. The export counts against that deadline.
- A revision that does not resolve, or has no parent, exits 1 with one stderr line that starts `sweep unverified:` (guess: the wording after the prefix) and writes no report.
- The control-term search skips `docs/dev/project-management/audit-results/`, with or without the flag: a saved report cannot make the control term "present".
- Without the flag, every existing test passes unchanged.
- `skills/sweep-fix/SKILL.md` documents the flag as the normal invocation and drops the sentence that a zero-hit sweep never exits 0. `CHANGELOG.md` gains one `### Fixed` line under `[Unreleased]`.

### Nice to have
- None.

## Implementation

### Module: sweep
- **Location**: `skills/sweep-fix/scripts/sweep.py`
- **Location**: `skills/sweep-fix/scripts/sweep_preimage.py`
- **Responsibility**: parse the new flag, export the pre-image, run the control check on it, and skip saved reports in the control-term search. The export lives in its own module (added at implementation, 2026-11-15) so that `skills/sweep-fix/scripts/sweep.py` stays under the size cap.
- **Exports**: `main`, `verify_control`
- New symbols: `--control-rev`, `_export_preimage`, `sweep_preimage.py`

### Module: control verification tests
- **Location**: `skills/sweep-fix/scripts/test_sweep_control_rev.py`
- **Location**: `skills/sweep-fix/scripts/test_sweep_verify_control.py`
- **Responsibility**: prove each outcome of the pre-image check, the cleanup, the read-only export and the saved-report exclusion. Build every repo under `tmp_path`; never sweep the operator's real registry.
- **Exports**: none
- New symbols: `test_sweep_control_rev.py`, `test_verify_control_ignores_the_control_term_inside_a_saved_report`, `test_zero_hit_sweep_verified_against_the_fix_preimage_exits_zero`, `test_preimage_with_control_term_but_no_pattern_match_aborts_as_broken_pattern`, `test_preimage_without_pattern_or_control_term_saves_an_unverified_report`, `test_preimage_export_leaves_no_temporary_directory_on_any_exit_path`, `test_preimage_export_does_not_change_the_control_repo`, `test_unusable_control_rev_exits_one_with_one_stderr_line_and_no_report`, `test_sweep_without_control_rev_behaves_as_before`

### Module: documentation
- **Location**: `skills/sweep-fix/SKILL.md`
- **Location**: `CHANGELOG.md`
- **Responsibility**: state the new invocation and the changed outcome.
- **Exports**: none

### Dependencies
- sweep: No dependencies (foundation)
- control verification tests: Depends on [sweep]
- documentation: Depends on [sweep]

## Tasks

### Phase 0: Foundation
- [ ] In `_search_control_term` pass `"--glob", AUDIT_RESULTS_GLOB` to the `rg` call, and add `test_verify_control_ignores_the_control_term_inside_a_saved_report` to `skills/sweep-fix/scripts/test_sweep_verify_control.py` (a control repo whose only occurrence of the term is in a file under `docs/dev/project-management/audit-results/` returns `False`). - Acceptance: `uv run pytest skills/sweep-fix/scripts/test_sweep_verify_control.py -k saved_report` passes, and the test fails when the glob argument is removed.

### Phase 1: Core
- [ ] Add the flag, the export and the wiring in `skills/sweep-fix/scripts/sweep.py`, with these tests in the new `skills/sweep-fix/scripts/test_sweep_control_rev.py`: `test_zero_hit_sweep_verified_against_the_fix_preimage_exits_zero`, `test_preimage_with_control_term_but_no_pattern_match_aborts_as_broken_pattern`, `test_preimage_without_pattern_or_control_term_saves_an_unverified_report`, `test_preimage_export_leaves_no_temporary_directory_on_any_exit_path`, `test_preimage_export_does_not_change_the_control_repo`, `test_unusable_control_rev_exits_one_with_one_stderr_line_and_no_report`, `test_sweep_without_control_rev_behaves_as_before` (depends on: Phase 0) - Acceptance: `uv run pytest skills/sweep-fix/scripts/test_sweep_control_rev.py` passes; `awk 'END { exit NR > 800 }' skills/sweep-fix/scripts/sweep.py` exits 0.
- [ ] Update `skills/sweep-fix/SKILL.md` and `CHANGELOG.md` as the last Must-have states (depends on: Phase 1 code task) - Acceptance: `rg -c "control-rev" skills/sweep-fix/SKILL.md` and `rg -c "control-rev" CHANGELOG.md` each print at least 1; `rg -c "never exits 0" skills/sweep-fix/SKILL.md` prints nothing.

## Success Criteria

- A sweep run right after a fix, with the fix commit named, exits 0 when no other repo holds the bug shape, and the saved report carries no `Unverified:` line.
- A second run of an inconclusive sweep gives the same outcome as the first.
- `uv run python scripts/gate.py` ends with `FAIL 0` and `EXIT 0`.
- `uv run python3 skills/create-skill/scripts/validate_skill.py skills/sweep-fix` reports the skill valid.
