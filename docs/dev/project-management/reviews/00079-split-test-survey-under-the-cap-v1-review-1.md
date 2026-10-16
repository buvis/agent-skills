---
prd: docs/dev/project-management/prds/wip/00079-split-test-survey-under-the-cap-v1.md
review: 1
date: 2026-10-16
head_sha: 217017a35926d8f36c6b45c548241a33617d3651
codex_thread_id: 01a14647-67a8-75d1-9b14-2a745c991301
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
dispatch_rows:
  bob: 3f7e66b1
  bob_retry: 79a24077
  carl: f0014c7d
  carl_retry: b5fe60d7
---

# Review: 00079-split-test-survey-under-the-cap-v1 (cycle 1, full)

Diff range: `bde94d7872861cf65a1e3d11028bd377398dba18..217017a35926d8f36c6b45c548241a33617d3651`

codex_rung_guard: not fired

pack: failed (engram pack exit 1: not inside a registered repo; run `gita add /Users/bob/git/src/worktrees/agent-skills/prd-00079-survey-split`)

Mechanical checks: 0 `[MECH]` findings (34 test functions checked in 3 test files, 0 tautological shapes). Fail-first replay skipped: the runner hit `ModuleNotFoundError: No module named 'survey_test_helpers'` overlaying HEAD's tests on the base worktree, which lacks the new helper module. For a pure test move this is expected; Alice and Blake each confirmed body-hash equivalence against master instead.

## Review Summary

Reviewed: 2 completed tasks
PRDs checked: 00079-split-test-survey-under-the-cap-v1

### Agent Status

- Alice: ✅ Available
- Blake: ✅ Available
- Bob: ✅ Available (first run was a lack-of-input refusal - the codex sandbox failed `sandbox_apply` before reading the staged files; re-dispatched as the inlined retry per retry-policy.md, `after one retry (inlined)`)
- Carl: ✅ Available (`backend=copilot model=gemini-3.8-flash`; first run exited 0 with tool narration only and no issue or verdict lines, so format-invalid; one retry with a format note produced a full review)

## Consolidated Findings

2 findings, both ⚪ Low. No 🔴, 🟠 or 🟡.

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [2/4] | ⚪ | New conftest.py and survey_test_helpers.py fail ruff I001 (import order), and the moved `_init_git_repo` line `subprocess.run(["git", "config", "user.email", ...` is 105 chars, over E501's 100. Same shape as the pre-split code, so cosmetic only | skills/survey/scripts/survey_test_helpers.py:32 | 2 | ALICE, BLAKE |
| R2 | [1/4] | ⚪ | ruff flags I001 import ordering in `conftest.py`, `survey_test_helpers.py` and all three test modules. The spec-mandated `sys.path.insert` header sits before `import run` and the helpers import, so the sorting complaint comes from the required layout. The E501 hits in `test_survey_brief.py` and `survey_test_helpers.py` are lines moved unchanged from the old file. | skills/survey/scripts/test_survey_brief.py:182 | 2 | BLAKE |

Consolidation note: script-run, no ledger (cycle 1). Row R1 merged Blake's second finding (`survey_test_helpers.py:14`, the module does `import run` with no `sys.path` header and relies on pytest's rootdir insertion) with Alice's lint finding after suffix stripping; both are kept in the reviewer sections below.

## Alice

Consensus lens, implementation-aware. 1 finding (row R1). Verified fresh: collect-only 55; inventory (test-name multiset, body hashes, markers with reasons, helper/constant/fixture names) identical to `docs/dev/tmp/00079-inventory-before.txt`; line counts 380/437/249/12/48, all under 800; `uv run pytest skills/survey/scripts -q` 50 passed, 5 skipped (`requires_tree_sitter`), 0 failed; scope limited to test modules, conftest.py and survey_test_helpers.py; headers kept; no duplicated shared names.

```
R1: pass
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: pass
R10: pass
R11: pass
R12: pass
R13: pass
```

## Blake

Blind lens, PRD-only. 2 findings (rows R1, R2). Independently verified against master with an AST comparison: 46 function/class definitions hash identical in both directions, 55 collected tests on both sides with matching ids, decorators and markers identical, run.py untouched.

- [BLAKE] ⚪ `survey_test_helpers.py` has no `sys.path` header but does `import run` at import time. It only works because pytest puts the scripts directory on `sys.path` for `conftest.py`. Running it outside pytest would fail. | File: skills/survey/scripts/survey_test_helpers.py:14 | Task: 2

```
B1: pass
B2: pass
B3: pass
B4: pass
B5: pass
B6: pass
B7: pass
B8: pass
B9: pass
B10: pass
B11: pass
B12: pass
B13: pass
B14: pass
B15: pass
B16: pass
B17: pass
B18: pass
B19: pass
```

## Bob

Doubt lens + de-slop (codex), `after one retry (inlined)`. No issues found.

FIX: (none). VERIFY: (none). KNOWN: (none).

```
R1: pass
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: pass
R10: pass
R11: pass
R12: pass
R13: pass
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass
```

## Carl

Generalist lens (no UI surface in this diff), `backend=copilot model=gemini-3.8-flash`, after one retry (format). No issues found. Diffed the before/after inventories (identical), ran the survey suite and `validate_skill.py skills/survey` (OK); `braid` was not on its PATH.

```
R1: pass
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: pass
R10: pass
R11: pass
R12: pass
R13: pass
```

Verdict: 2 findings
Tests: 3800 passed, 1 failed, 6 skipped (suite run this cycle; the failure is tests/test_conftest_fixtures.py::test_armed_directory_refuses_a_childs_stat, untouched by this diff, Python 3.14 pathlib behavior, already deferred in the batch deferred JSON)
