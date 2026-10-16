---
default_model: opus
model_tier_rationale: a behaviour-preserving split carries an equivalence obligation (test-name multiset, bodies, markers and helper inventory identical before and after), which the authoring rubric places at the opus floor
rework_cap: 3
catchup: skip
design: skip
---

# Split test_survey.py under the 800-line cap

## Problem

`skills/survey/scripts/test_survey.py` is 1073 lines (855 before PRD 00030, 1022 after it), past the 800-line
file limit in the user-global `~/.claude/rules/coding-style.md` (rubric R13). Two of four reviewers raised it on 00030 and Bob filed it in his KNOWN
bucket; the surgical-changes rule kept 00030 from splitting a suite it only extended. The next survey PRD
extends it again. Source: batch 202609050909 deferred ledger, PRD 00030 `review-deferral` rows; decided
2026-09-07 in the config-audit closure walkthrough (`~/.claude/docs/dev/project-management/audit-results/2026-09-05.md`).
The residual overlapping pruning tests stay: the reviewers judged the parametrized cases broader real
coverage than the PRD-mandated one, so the split moves them, it does not delete them.

## Solution

Split by concern the way PRD 00053 split the brief-portfolio suites: the traversal and pruning tests into
`test_survey_scan.py`, the brief rendering tests into `test_survey_brief.py`, and whatever remains in
`test_survey.py`, each under 800 lines. Pytest fixtures used by more than one module (`git_repo`) move to a
`conftest.py` beside them; plain helpers and constants used by more than one module (`_init_git_repo`,
`_section_body`, `PINNED_KINDS`, `requires_tree_sitter`, at 2026-10-10) move to `survey_test_helpers.py`,
the repo's `*_test_helpers.py` idiom, and are imported from there. A test whose concern is ambiguous
(e.g. `test_extracted_kinds_are_within_pinned_enum`) stays in `test_survey.py`. Every module keeps the
`sys.path.insert(0, str(Path(__file__).resolve().parent))` + `import run` header. No test is renamed or
deleted; the collected count before and after is identical.

## Requirements

### Must have

- Every `skills/survey/scripts/test_*.py` is under 800 lines.
- `uv run pytest skills/survey/scripts --collect-only -q` reports the same number of tests before and after,
  and the multiset of test names, the test bodies (hashed), the `pytest.mark` markers and reasons, and the
  helper/fixture inventory are identical before and after, measured at execution time, not from this PRD.
- Shared fixtures live in `skills/survey/scripts/conftest.py` and shared plain helpers and constants in
  `skills/survey/scripts/survey_test_helpers.py`; no fixture, helper or constant is duplicated across modules.
- If part of the split already landed, preserve it and report what remains instead of recreating files.
- No change under `skills/survey/scripts/` other than test modules, the conftest and `survey_test_helpers.py`.

### Nice to have

- none

## Implementation

### Module: test_survey_scan (new)
- **Location**: `skills/survey/scripts/`
- **Responsibility**: `_scan_layers()` traversal, `_SKIP_DIRS` pruning, the parametrized pruning cases
- **Exports**: the moved tests

### Module: test_survey_brief (new)
- **Location**: `skills/survey/scripts/`
- **Responsibility**: brief rendering and output shape
- **Exports**: the moved tests

### Module: conftest
- **Location**: `skills/survey/scripts/`
- **Responsibility**: fixtures used by more than one module
- **Exports**: the shared fixtures

### Module: survey_test_helpers (new)
- **Location**: `skills/survey/scripts/`
- **Responsibility**: plain helpers and constants used by more than one test module
- **Exports**: the shared helpers and constants

### Dependencies
- test_survey_scan: Depends on [conftest, survey_test_helpers]
- test_survey_brief: Depends on [conftest, survey_test_helpers]

## Tasks

### Phase 0: Foundation

- [ ] Record the execution-time pre-split inventory - Acceptance: `docs/dev/tmp/00079-inventory-before.txt`
  holds the test-name multiset (names without file or line prefixes, with multiplicities), a hash of each test
  body, every marker with its reason, and the helper, constant and fixture names, taken from
  `skills/survey/scripts/test_*.py`, `conftest.py` and `survey_test_helpers.py` (whichever exist) at
  execution time, so a helper that moves between files keeps its inventory line; the collect-only count is recorded in the commit body.
- [ ] Move the traversal and pruning tests into `test_survey_scan.py` and the rendering tests into
  `test_survey_brief.py`, sharing fixtures via `conftest.py` (depends on: the inventory task) - Acceptance:
  `uv run pytest skills/survey/scripts --collect-only -q` reports the recorded count; the same inventory taken
  after the move equals the recorded one line for line; `wc -l skills/survey/scripts/test_*.py` prints under
  800 for each; `uv run pytest skills/survey/scripts -q` reports 0 failing.

### Phase 1: Core

- none

## Success Criteria

- Each survey test module is under 800 lines, the collected test count is unchanged, and no test was renamed.
- The next survey PRD's reviewers no longer fail rubric R13 on file size.
