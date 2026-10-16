## 1: Record the execution-time pre-split inventory

- The inventory script runs pytest from the caller's working directory, so it must be launched from the repo root. (Ivan)
- Only top-level statements are inventoried; test methods inside classes and nested functions are not covered, and none exist today. (Ivan)
- A marker assignment such as `requires_tree_sitter` is listed both under markers (full value, so the reason is recorded) and under constants (value hash). (Ivan)
- Line formats are the implementor's choice: `name count`, `test name [dec1 | dec2]`, `marker name = value`. (Ivan)
- Helpers and fixtures carry their decorators and a body hash, not only their names, so a helper changed during the split shows up as a diff; the orchestrator added this after Ivan's name-only version. (orchestrator)

## 2: Split test_survey.py into test_survey_scan.py and test_survey_brief.py with shared conftest.py and survey_test_helpers.py

- The old "# Helpers" banner was dropped, since every name under it moved to `survey_test_helpers.py` or `conftest.py`. (Ivan)
- The "Tree-sitter symbol extraction + degraded gating" banner went with the degraded tests into `test_survey_brief.py`. The orchestrator then renamed it "Tree-sitter degraded gating" and gave the extraction tests in `test_survey.py` their own "Tree-sitter symbol extraction" banner. (Ivan, orchestrator)
- `test_survey_scan.py` and `test_survey_brief.py` got short new module docstrings. (Ivan)
- Following Pat's LOW finding, the `requires_tree_sitter` comment no longer says "the two cases below". Comment only; the inventory is unchanged. (orchestrator)
- `VALID_ERROR_STYLES`, `MD_SECTIONS`, `TRUNCATION_FOOTER`, `_COMPLETE_MD_LINE` and the `_repo_with_many_layers` / `_make_repo_*` helpers live in `test_survey_brief.py`, the one module that uses them. Only the four names the PRD lists went to `survey_test_helpers.py`. (orchestrator)
