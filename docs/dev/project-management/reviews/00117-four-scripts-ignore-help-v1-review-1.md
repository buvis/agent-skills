---
prd: docs/dev/project-management/prds/wip/00117-four-scripts-ignore-help-v1.md
review: 1
date: 2026-10-29
head_sha: 5f89ff0b6072e48fa75d55d10cfab24f2088dd6e
codex_thread_id: 01a18857-3d00-7031-84fc-b0d4c4372a72
reviewers: alice,blake,bob
agents:
  alice: available
  blake: available
  bob: available
  carl: unavailable
dispatch_rows:
  bob: 35c4be21
  carl: 11fad2de
---

# Review: 00117-four-scripts-ignore-help-v1

Diff range: `cb873b030cc5d5e652b131073342b147bb26619f..5f89ff0b6072e48fa75d55d10cfab24f2088dd6e`

codex_rung_guard: not fired

## Review Summary

Reviewed: 1 completed task
PRDs checked: 00117-four-scripts-ignore-help-v1.md
Consensus engine: legacy (single Alice subagent)
Pack: ok
Mechanical blocks: tautological-shape scan checked 22 test functions in 4 files (no shape findings); fail-first replay ran 35 touched tests, 11 failed against base, 24 passed.

### Agent Status

- Alice: ✅ Available
- Blake: ✅ Available
- Bob: ✅ Available (codex, cycle-1 full review, thread id captured)
- Carl: ⚠️ Unavailable: gemini-run exit 1, backend=copilot model=gemini-3.8-flash, "You have exceeded your monthly quota". One-off runtime/quota failure, not exit 4, so no batch latch and no retry of an exhausted monthly quota.
- Eve: ⏸️ Disabled: resolved doubt reviewer is `codex` and no task was codex-implemented, so the codex doubt-roster guard did not fire.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [2/3] | 🟡 | `test_help_flag_does_not_create_any_output_artifact` passes against the pre-change code, and the fail-first replay flags it. It only lists an empty `tmp_path` before and after, so it cannot tell help from a survey. The old `run.py` also writes nothing, so a regression that wrote a file on help is the only way it could fail. Pin it instead by running `-h` in a directory with a source file and asserting stdout has no brief, which is already covered. Alternatively, drop it and the "artifact" comment, which wrongly says the brief goes "anywhere" other than stdout. | skills/survey/scripts/test_survey_help.py:75 | 1 | ALICE, mech-check |
| R2 | [1/3] | 🟡 | `import sys` sits inside `main()`, while every other import is at module top (skills/survey/scripts/run.py:1). This is style drift, and a function-local import has no reason here since `sys` is cheap and always needed. Move `import sys` to the top-level import block with `os` and `re`. This does not change behavior. | skills/survey/scripts/run.py:468 | 1 | ALICE |
| R3 | [1/3] | 🟡 | The three review-helper test files are near-verbatim copies. Only the script name and the valid-doc content differ, and each has the same `_run` helper, help test, near-miss test and preservation tests. One parametrized test over the three scripts would remove about 200 duplicated lines. This is a behavior-preserving simplification. | skills/review-design-doc/scripts/test_claim_ladder_scan.py:1 | 1 | ALICE |
| R4 | [1/3] | 🟡 | Help tests never assert the required document argument appears in usage; printing only the script name passes. Assert `<path/to/doc.md>` in all three helpers' help outputs. | skills/review-design-doc/scripts/test_adversarial_signal_scan.py:33 | 1 | BOB |
| R5 | [1/3] | 🟡 | Each `test_help_flag_runs_before_file_validity_check` repeats the preceding parametrized test's `-h` invocation with weaker assertions. Remove these redundant tests; the preceding tests already require exit 0 and empty stderr. | skills/review-design-doc/scripts/test_adversarial_signal_scan.py:50 | 1 | BOB |
| R6 | [1/3] | ⚪ | `test_help_flag_runs_before_file_validity_check` repeats the assertions of the parametrized `-h` case, which already asserts exit 0 and empty stderr. It is redundant, and the same redundancy was flagged in review 00036 as a 🟡. | skills/review-design-doc/scripts/test_section_weight_audit.py:49 | 1 | ALICE |
| R7 | [1/3] | ⚪ | The survey usage line `usage: run.py` is accurate, since `run.py` takes no positional input and surveys the cwd. It does not say that, so a user learns nothing about where the survey runs. Consider `usage: run.py  (surveys the current directory)`. This is optional, because the PRD only requires the script name. | skills/survey/scripts/run.py:471 | 1 | ALICE |
| R8 | [1/3] | ⚪ | The diff includes autopilot metrics, ledger and capsule files, which are harness bookkeeping and not part of the reviewed feature. They are not defects. | N/A | general | ALICE |
| R9 | [1/3] | ⚪ | No spec defects found. All four entry points handle -h/--help as argv[1] and print a one-line usage to stdout. They return, so exit is 0, before any repo scan or file check. Direct runs of run.py --help and claim_ladder_scan.py -h printed the usage line only. | skills/survey/scripts/run.py:470 | 1 | BLAKE |
| R10 | [1/3] | ⚪ | Normal paths are untouched. The diff for 8b48133 is +18 lines across the 4 scripts, all in the help branch. The survey footer and brief logic are unchanged. The review helpers keep exit 2 for a wrong argument count and exit 1 with "error: not a file" for an invalid file. | skills/review-design-doc/scripts/section_weight_audit.py:154 | 1 | BLAKE |
| R11 | [1/3] | ⚪ | Survey usage is "usage: run.py" with no positional argument. That is correct because run.py takes none and scans cwd. The three helpers name <path/to/doc.md>, matching their existing usage strings. | skills/survey/scripts/run.py:471 | 1 | BLAKE |
| R12 | [1/3] | ⚪ | Four per-script help test files were added in 949477f, for example skills/survey/scripts/test_survey_help.py. The PRD says "direct command checks suffice" and forbids only a repository-wide documented-script help test. These are per-script, so they stay within the letter of the spec, but they go slightly beyond it. They pass: 35 passed in a narrow run of those files. I did not rerun the full suite (the test gate shows exit 0, no counts). | skills/survey/scripts/test_survey_help.py | general | BLAKE |
| R13 | [1/3] | ⚪ | Help is only recognised as argv[1], so `script file.md --help` falls through to the usage error with exit 2. This is acceptable under "preserve normal invocation and error behavior". It is not a defect. | skills/review-design-doc/scripts/claim_ladder_scan.py:86 | 1 | BLAKE |
| R14 | [1/3] | ⚪ | I did not run validate_skill.py or braid --check myself. I did not check the exit criteria for the normal-invocation preservation of each review helper beyond reading the unchanged code. | N/A | general | BLAKE |
| R15 | [1/3] | 🟡 | 6 touched test(s) pass against the pre-change code: test_near_miss_help_spelling_falls_through_to_file_check, test_missing_argument_still_exits_2_with_usage_on_stderr, test_invalid_file_path_still_exits_1_with_error_on_stderr, test_normal_invocation_on_valid_doc_still_scans_and_exits_0 | skills/review-design-doc/scripts/test_adversarial_signal_scan.py | general | mech-check |
| R16 | [1/3] | 🟡 | 6 touched test(s) pass against the pre-change code: test_near_miss_help_spelling_falls_through_to_file_check, test_missing_argument_still_exits_2_with_usage_on_stderr, test_invalid_file_path_still_exits_1_with_error_on_stderr, test_normal_invocation_on_valid_doc_still_scans_and_exits_0 | skills/review-design-doc/scripts/test_claim_ladder_scan.py | general | mech-check |
| R17 | [1/3] | 🟡 | 6 touched test(s) pass against the pre-change code: test_near_miss_help_spelling_falls_through_to_file_check, test_missing_argument_still_exits_2_with_usage_on_stderr, test_invalid_file_path_still_exits_1_with_error_on_stderr, test_normal_invocation_on_valid_doc_still_scans_and_exits_0 | skills/review-design-doc/scripts/test_section_weight_audit.py | general | mech-check |

R15-R17 are the fail-first replay's remaining `[MECH]` rows. The fourth replay row (`skills/survey/scripts/test_survey_help.py`) named the same test file and test as Alice's R1, so `mech-check` was appended to that row's finders instead of adding a duplicate row.

## Alice

Six findings, three 🟡 and three ⚪, listed as R1-R3 and R6-R8 above. Her raw output is `docs/dev/tmp/alice-output-00117-c1.txt`.

R1: pass
R2: fail
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

## Blake

Blind lens, PRD-only prompt. No spec defects; six ⚪ observations, listed as R9-R14 above. All nineteen blind-rubric rules pass.

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

Blake named two self-reported gaps (he did not run `validate_skill.py` or `braid --check`). Both were run green in the build session and are recorded on the contract card.

### Doubt buckets (Bob)

FIX:
- Medium: help tests never assert the required document argument appears in usage (R4)
- Medium: redundant `test_help_flag_runs_before_file_validity_check` in each of the three helper test files (R5)

VERIFY:
- (none)

KNOWN:
- (none)

No VERIFY item, so no verification-check queue was written for this cycle.

## Bob

Codex, static-only sandbox, inlined prompt (79874 bytes). Two 🟡 FIX findings, listed as R4-R5 above. Consensus-rubric verdicts plus the five doubt-rubric verdicts:

R1: fail
R2: fail
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

## Carl

Not run. `gemini-run.sh` exited 1 with "You have exceeded your monthly quota" on backend `copilot`, model `gemini-3.8-flash`. No output file was published and none was consolidated. The diff has no frontend or design surface, so Carl's absence costs this cycle no specialist coverage.

## Follow-up Tasks Created

None by this skill (PRD 00249 removed task creation here). The decision gate in `run-autopilot/references/phase-review.md` classifies the rows above and makes the task-creating `review-close` calls.

Verdict: 17 findings
Tests: 4180 passed, 0 failed, 9 skipped (suite run this cycle; review-stage's gate exited 0 but pytest's native summary did not match the PASS/FAIL/SKIP/EXIT parser, so gate.tests_line reported counts unavailable and no last-verification.json record was written; counts read from docs/dev/tmp/gate-00117-c1.log at the same sha)
