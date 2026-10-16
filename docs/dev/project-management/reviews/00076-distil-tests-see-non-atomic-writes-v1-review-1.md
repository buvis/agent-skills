---
prd: docs/dev/project-management/prds/wip/00076-distil-tests-see-non-atomic-writes-v1.md
review: 1
date: 2026-10-16
head_sha: 9705c3dcb6aafffe4f514c00fa15ea42a1bfdd60
codex_thread_id: 01a14645-6acd-7d02-b54b-b9aca230e9e9
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
dispatch_rows:
  bob: 3a1ae986
  bob_retry: 20c098fe
  carl: 96128fac
---

# Review: 00076-distil-tests-see-non-atomic-writes-v1 (cycle 1, full)

Diff range: `bde94d7872861cf65a1e3d11028bd377398dba18..9705c3dcb6aafffe4f514c00fa15ea42a1bfdd60`

codex_rung_guard: not fired

pack: failed (engram pack exit 1: not inside a registered repo; run `gita add /Users/bob/git/src/worktrees/agent-skills/prd-00076-00077-distil-docket`)

Mechanical checks: 0 tautological shapes (72 test functions in 5 files). Fail-first replay: 28 touched tests ran, 1 failed against base, 27 passed. The five replay `[MECH]` lines are absorbed as R9-R13 below. This PRD is test-only by design (the one production change is the `docket.py` `is_dir()` refusal), so new tests that pin existing correct behaviour pass against base as intended; Alice and Blake confirmed the named mutants turn them red.

codex_thread_id note: the stamped id is the inlined retry's session (`01a14645-...`). The first run's session (`01a1463f-3a36-7ce1-91e1-bebe0e7f130b`, in `bob-thread-00076c1-20261016.txt`) died on a sandbox error and holds no review.

## Review Summary

Reviewed: 6 completed tasks
PRDs checked: 00076-distil-tests-see-non-atomic-writes-v1

### Agent Status

- Alice: ✅ Available
- Blake: ✅ Available
- Bob: ✅ Available (first run was a lack-of-input refusal: codex's read-only `cat` calls failed with `sandbox-exec: sandbox_apply: Operation not permitted`. Re-dispatched as the inlined retry per retry-policy.md, `after one retry (inlined)`. The retry's `-o` file also captured the echoed prompt, whose template `[BOB]` example lines would have parsed as findings, so `bob-output-00076c1-20261016.txt` was trimmed to codex's final message; the untrimmed file is kept as `bob-output-00076c1-20261016-raw.txt`.)
- Carl: ✅ Available (`backend=copilot model=gemini-3.8-flash`)

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [2/4] | 🟡 | The rewritten rollback-failure assertion (`all(index_fault in line or rollback_fault in line ...)`) still passes if production appends a "rolled back" claim to the same stderr line as one of the two faults. It catches only a separate extra line. Today's messages are separate lines, so no live defect. Assert that each fault appears and that the line count equals the number of faults, or assert on a fixed phrase list | skills/distil-memory/scripts/test_write_crash_safety.py:448 | 5 | ALICE, BOB |
| R2 | [1/4] | ⚪ | The new `is_dir()` guard prints "no such directory" when `--proposals-dir` exists but is a regular file. The message is then wrong, though the exit code and the named path are right. Use a neutral "not a directory" or "cannot read" wording | skills/distil-memory/scripts/docket.py:270 | 3 | ALICE |
| R3 | [1/4] | ⚪ | Simplification: the new atomicity module re-declares `_REAL_REPLACE` and `_run_write`. `test_write_crash_safety.py` already defines `_REAL_REPLACE`, and the stdin-then-`write.main` pattern appears in many tests there. Moving these into `write_test_helpers` would remove the duplication. It is optional and behaviour-preserving | skills/distil-memory/scripts/test_write_atomicity.py:451 | 1 | ALICE |
| R4 | [1/4] | ⚪ | test_decide_reads_the_file_once counts only Path.read_text calls on the note. A second read through read_bytes(), open() or io.open() slips past it. The read-count pin is narrower than the "read exactly once" requirement implies. | skills/distil-memory/scripts/test_docket_refusals.py:589 | 4 | BLAKE |
| R5 | [1/4] | ⚪ | test_main_write_reports_both_the_pointer_error_and_the_rollback_error_when_restoring_an_updated_target_fails (the second rollback-failure test) never asserts that no restoration is claimed. Only the first rollback-failure test got the "every stderr line carries one of the two faults" check. The spec asks that the rollback-failure assertion bind "both errors reported, no restoration claimed". `"rolled back" not in` is gone from the whole directory, so the Phase 2 acceptance rg passes, but the sibling test is looser than its twin. | skills/distil-memory/scripts/test_write_crash_safety.py:454 | 5 | BLAKE |
| R6 | [1/4] | ⚪ | The new is_dir() refusal line in docket.py is 105 chars. ruff E501 (limit 100) flags it. Neighbouring lines already violate it, so this is consistent with the file, but it adds one more violation. | skills/distil-memory/scripts/docket.py:270 | 3 | BLAKE |
| R7 | [1/4] | ⚪ | test_main_start_returns_zero now asserts queue behaviour (next empty before start, remaining entry after, cursor unchanged), so its name no longer says what it enforces. The spec says to keep existing names, so this is only a note. | skills/distil-memory/scripts/test_docket_cli.py:122 | 6 | BLAKE |
| R8 | [1/4] | ⚪ | Pre-existing, outside PRD 00076: `_save_from_proposals_dir` catches only OSError and JSONDecodeError. A non-UTF-8 proposals.json or sibling file raises UnicodeDecodeError and produces a traceback instead of a refusal. A record missing a key raises KeyError the same way. The PRD assigns record-shape refusals to 00077, so I did not count this against 00076. | skills/distil-memory/scripts/docket.py:292 | general | BLAKE |
| R9 | [1/4] | 🟡 | 4 touched test(s) pass against the pre-change code: test_main_start_returns_zero, test_main_save_carries_a_records_dedup_error_into_the_stored_entry, test_main_save_ingests_a_record_whose_dedup_error_key_is_absent_and_stores_none, test_main_save_keeps_each_entrys_dedup_error_matched_to_the_right_entry_in_a_mixed_batch | skills/distil-memory/scripts/test_docket_cli.py | general | mech-check |
| R10 | [1/4] | 🟡 | 7 touched test(s) pass against the pre-change code: test_save_blames_only_the_absent_middle_sibling, test_save_never_partially_saves_after_three_readable_records, test_decide_accepts_an_empty_file, test_decide_refusal_never_calls_save_queue, test_decide_propagates_keyboard_interrupt, test_decide_reads_the_file_once +1 more | skills/distil-memory/scripts/test_docket_refusals.py | general | mech-check |
| R11 | [1/4] | 🟡 | 1 touched test(s) pass against the pre-change code: test_edit_path_refuses_a_linkless_edit_against_a_store_whose_index_names_memories | skills/distil-memory/scripts/test_walkthrough_integration.py | general | mech-check |
| R12 | [1/4] | 🟡 | 6 touched test(s) pass against the pre-change code: test_atomic_write_target_is_complete_the_instant_the_rename_lands, test_a_realistic_size_malformed_memory_is_refused, test_a_refused_memory_triggers_no_write_call, test_rollback_restores_only_the_target, test_a_later_fault_does_not_revert_an_earlier_success | skills/distil-memory/scripts/test_write_atomicity.py | general | mech-check |
| R13 | [1/4] | 🟡 | 9 touched test(s) pass against the pre-change code: test_main_write_rolls_the_store_back_byte_for_byte_when_the_index_step_fails +3 more | skills/distil-memory/scripts/test_write_crash_safety.py | general | mech-check |

No CRITICAL or HIGH finding.

## Alice

[ALICE] ⚪ The rewritten rollback-failure assertion (`all(index_fault in line or rollback_fault in line ...)`) still passes if production appends a "rolled back" claim to the same stderr line as one of the two faults. It catches only a separate extra line. Today's messages are separate lines, so no live defect. Assert that each fault appears and that the line count equals the number of faults, or assert on a fixed phrase list | File: skills/distil-memory/scripts/test_write_crash_safety.py:448 | Task: 5
[ALICE] ⚪ The new `is_dir()` guard prints "no such directory" when `--proposals-dir` exists but is a regular file. The message is then wrong, though the exit code and the named path are right. Use a neutral "not a directory" or "cannot read" wording | File: skills/distil-memory/scripts/docket.py:270 | Task: 3
[ALICE] ⚪ Simplification: the new atomicity module re-declares `_REAL_REPLACE` and `_run_write`. Moving these into `write_test_helpers` would remove the duplication. Optional, behaviour-preserving | File: skills/distil-memory/scripts/test_write_atomicity.py:451 | Task: 1

Checks: distil-memory suite 759 passed; placeholder-move `_atomic_write` and dropped `advance()` mutants each turn the target tests red (run in a scratch copy); the other named mutants judged by reading only.

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

## Blake

[BLAKE] ⚪ test_decide_reads_the_file_once counts only Path.read_text calls on the note; a read via read_bytes(), open() or io.open() slips past it | File: skills/distil-memory/scripts/test_docket_refusals.py:589 | Task: 4
[BLAKE] ⚪ The second rollback-failure test never asserts that no restoration is claimed; only its twin got the check | File: skills/distil-memory/scripts/test_write_crash_safety.py:454 | Task: 5
[BLAKE] ⚪ The new is_dir() refusal line is 105 chars (ruff E501, limit 100) | File: skills/distil-memory/scripts/docket.py:270 | Task: 3
[BLAKE] ⚪ test_main_start_returns_zero's name no longer says what it enforces; the spec keeps names, so a note only | File: skills/distil-memory/scripts/test_docket_cli.py:122 | Task: 6
[BLAKE] ⚪ Pre-existing, outside 00076: `_save_from_proposals_dir` lets UnicodeDecodeError and KeyError through as tracebacks (record-shape refusals are PRD 00077's) | File: skills/distil-memory/scripts/docket.py:292 | Task: general

Checks: distil-memory suite 759 passed; placeholder-move mutant re-run red; every Must-have item located.

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

## Bob

after one retry (inlined)

[BOB] 🟡 Rollback-failure assertion still permits a restoration-success claim: a line containing `index_fault` plus “store restored successfully” passes `all(...)`. Assert rollback failure explicitly and reject restoration-success claims even when they share a line with either error. | File: skills/distil-memory/scripts/test_write_crash_safety.py:448 | Task: 5

FIX: the line above. VERIFY: (none). KNOWN: (none).

R1: pass
R2: fail
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: fail
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

[CARL] ✅ No issues found

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

Verdict: 13 findings
Tests: 3815 passed, 1 failed, 6 skipped (suite run this cycle; the 1 failure is tests/test_conftest_fixtures.py::test_armed_directory_refuses_a_childs_stat, which fails identically at base bde94d7)
