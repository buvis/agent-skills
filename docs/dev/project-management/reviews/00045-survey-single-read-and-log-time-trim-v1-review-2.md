---
prd: docs/dev/project-management/prds/wip/00045-survey-single-read-and-log-time-trim-v1.md
review: 2
date: 2026-10-18
head_sha: d4d73c0f4cddca5aa7844fb5557420fdd8c75eb2
codex_thread_id: 01a14f5d-067d-77f0-9393-34e05c718051
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
dispatch_rows:
  bob: f78c26a0
  bob_retry: 0418b615
  carl: b6bd088c
---

# Review: 00045-survey-single-read-and-log-time-trim-v1 (cycle 2, incremental)

Diff range: `7a9c07e5c942b3b567c7a4c86cfbdd7d042c12cf..d4d73c0f4cddca5aa7844fb5557420fdd8c75eb2`

codex_rung_guard: not fired

pack: failed (engram pack exit 1: not inside a registered repo; run `gita add /Users/bob/git/src/github.com/buvis/agent-skills`)

Mechanical checks: 39 test functions checked in 3 test files, 0 tautological shapes. Fail-first replay: 1 touched test ran against `7a9c07e5c942`, 0 failed there, 1 passed. That one replay line is absorbed as R8 below.

## Review Summary

Reviewed: 9 completed tasks (3 cycle-1 rework tasks since the prior review)
PRDs checked: 00045-survey-single-read-and-log-time-trim-v1

### Agent Status

- Alice: ✅ Available
- Blake: ✅ Available
- Bob: ✅ Available (first run was a lack-of-input refusal - the codex sandbox failed `sandbox_apply` before reading the staged files, same shape as cycle 1; re-dispatched as the inlined retry per retry-policy.md, `after one retry (inlined)`)
- Carl: ✅ Available (`backend=copilot model=gemini-3.8-flash`)

Consolidation note: `consolidate_findings.py` merged by suffix-stripped citation, so R2 (Blake + Carl, `test_survey_brief.py`) and R3 (Alice, `test_survey_trim.py:217`) are two rows for **one defect** - the PRD-named tests deleted from `test_survey_brief.py`. Judged as one finding at 3/4 consensus by the decision gate. Nothing was ledger-dismissed this cycle.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [3/4] | 🟡 | The unreadable-file path got worse with the rework. Before, an unreadable file was attempted twice (`_read_sampled_texts`, then `_compute_error_style`). Now `texts.get(f)` is None, so it is also re-read inside `_extract_file_symbols`. That is up to four attempts with tree-sitter present (initial read, tree-sitter read, regex fallback, error-style scan), or up to three in degraded mode. This violates the PRD must-have "no file is read more than once", though the design accepts it. `test_survey_unreadable_file_is_skipped_without_error` (`skills/survey/scripts/test_survey_single_read.py:111`) never counts attempts, so nothing pins the count either way. Either record failed reads in `_read_sampled_texts` (for example as `""`, with a test asserting one attempt), or record the exception in the PRD | skills/survey/scripts/run.py:437 | 2 | ALICE, BLAKE, BOB |
| R2 | [2/4] | 🟠 | Two spec-mandated tests are not where, or what, the PRD says. `test_trim_matches_the_pop_loop_byte_for_byte` does not exist anywhere. A sweep test named `test_trim_matches_reference_pop_loop_across_a_budget_sweep` sits in a different file, skills/survey/scripts/test_survey_trim.py:217. The log-bound test is in skills/survey/scripts/test_survey_trim.py:243 rather than skills/survey/scripts/test_survey_brief.py. It uses 1000 lines of ~40 chars and a `ceil(log2(n+1))+2` bound, not the specified 600 lines at 5120 bytes with `<= 12`. The acceptance commands `pytest ...test_survey_brief.py::test_trim_matches_the_pop_loop_byte_for_byte` and `...::test_trim_encodes_a_logarithmic_number_of_times` cannot pass as written: skills/survey/scripts/test_survey_brief.py defines neither test. Late commits 796d230 and f69b8b4 deleted the PRD-named tests as "duplicated". The behavior is covered, but the contractual symbols and locations are gone. | skills/survey/scripts/test_survey_brief.py | 5,6 | BLAKE, CARL |
| R3 | [1/4] | 🟠 | The PRD-named test `test_trim_matches_the_pop_loop_byte_for_byte` no longer exists anywhere in the repo; rework commit 796d230 deleted it from `test_survey_brief.py`. The PRD (Tasks, Success Criteria, Module test_survey_brief.py Exports) requires it in that file, runnable as `test_survey_brief.py::test_trim_matches_the_pop_loop_byte_for_byte`. `test_trim_encodes_a_logarithmic_number_of_times` now lives only in `test_survey_trim.py`, not in `test_survey_brief.py` as the PRD specifies. The replacement `test_trim_matches_reference_pop_loop_across_a_budget_sweep` has a different name and file. Restore the PRD names and locations, for example by moving the oracle and the two named tests into `test_survey_brief.py`, or update the PRD if relocation is intended | skills/survey/scripts/test_survey_trim.py:217 | 5 | ALICE |
| R4 | [1/4] | 🟡 | The rework deleted `test_survey_reads_each_sampled_file_exactly_once`, which was the only test covering an empty-text file read once. Its docstring said an implementation that treats "" as missing "re-reads empty.py". `text is None` is checked at `skills/survey/scripts/run.py:139` and `skills/survey/scripts/run.py:184`. Changing either to `if not text` would re-read empty files and no remaining test fails: `test_no_sampled_file_is_read_from_disk_twice` and the over-fifty test have no empty file, and the other `test_survey_single_read.py` tests do not count reads. The `empty.py` fixture is now unused for its stated purpose, and the `_build_repo` docstring at `skills/survey/scripts/test_survey_single_read.py:40` is stale. Add an `empty.py` to `test_no_sampled_file_is_read_from_disk_twice` or the over-fifty test, or keep a narrow empty-file read-count test | skills/survey/scripts/test_survey_single_read.py:40 | 3 | ALICE |
| R5 | [1/4] | ⚪ | The `if f in texts: continue` guard in `_read_sampled_texts` cannot fire, because `_scan_layers` builds disjoint per-directory file lists (`skills/survey/scripts/run.py:62`) and no test exercises it. It follows the design snippet, so it is harmless. Drop it if you take the simplification, otherwise leave it | skills/survey/scripts/run.py:416 | 2 | ALICE |
| R6 | [1/4] | ⚪ | The tree-sitter path (`_extract_tree_sitter` with a supplied `text`, and the `.go` merge on that path) is not exercised by the single-read test. 8 tests were skipped in this environment because tree-sitter is unavailable, so the single-read guarantee on that path is unverified here. By inspection, run.py:139-143, run.py:162 and run.py:173 forward `text` correctly. | skills/survey/scripts/test_survey.py:387 | 3 | BLAKE |
| R7 | [1/4] | ⚪ | Extra test coverage beyond the spec (about 15 tests in skills/survey/scripts/test_survey_trim.py) is not harmful. It does split the PRD's stated test layout across a file the PRD never names. | skills/survey/scripts/test_survey_trim.py | general | BLAKE |
| R8 | [1/4] | 🟡 | 1 touched test(s) pass against the pre-change code: test_implementations_index_file_path_includes_relative_directory | skills/survey/scripts/test_survey_brief.py | general | mech-check |

## Alice

Five findings, listed above as R3 (the PRD-named tests), R4, R1, R5 and the vestigial `_count_reads` spy. She confirmed the cycle-1 rework resolved R1 (duplicate `_reference_trim` and duplicate log-call test gone from `test_survey_brief.py`), R2 (`_survey` now passes `texts.get(f)` at `run.py:437`), R6 (duplicate exact-once test removed) and R7 (the `if f in texts: continue` guard added at `run.py:416`). Prior R3, R5 and R9-R11 stay closed under the settled decisions. She ran `uv run pytest skills/survey/scripts -q`: 117 passed, 8 skipped, 0 failed.

R1: fail
R2: pass
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

## Blake

One High and four Low findings, listed above as R2, R1 (the unreadable-file hole), R6, the `_read_sampled_texts` new-symbol note (merged into R1 on file match) and R7.

Blake verified independently: `_trim_lines_to_budget` (`run.py:372-393`) keeps the cleanup loop and handles empty content, under-budget content and a budget of 0 or below; the binary search is monotone and equals the old pop result; `_encoded_len` is called about 1 + ceil(log2 n) times, within the PRD bound; `rg "while lines and len"` has no match and `def _encoded_len` is at `run.py:367`; `read_text` appears only on fallback branches (`run.py:141`, `186`, `254`) plus the single read in `_read_sampled_texts` (`run.py:419`); `test_no_sampled_file_is_read_from_disk_twice` is present at `test_survey.py:387` with 60 `.py` files plus one `.go` file across 2 layers. He ran the suite: 117 passed, 8 skipped, 0 failed.

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
B15: fail
B16: pass
B17: pass
B18: pass
B19: pass

## Bob (doubt lens + de-slop) — after one retry (inlined)

FIX:
- 🟡 Unreadable files still violate the single-read requirement. `_read_sampled_texts` leaves failed reads uncached; the restored `texts.get(f)` call now retries extraction, and `_compute_error_style` retries again. Cache failed reads as empty text and extend the unreadable-file test to assert one attempted read. | File: skills/survey/scripts/run.py:439 | Task: 2

VERIFY:
- (none)

KNOWN:
- (none)

R1: fail
R2: pass
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

`backend=copilot model=gemini-3.8-flash`. Two findings, consolidated above as R2 (both of his lines name `test_survey_brief.py:437`: the deleted byte-for-byte test and the relocated logarithmic test). He executed the PRD's acceptance commands directly: `pytest skills/survey/scripts/test_survey_brief.py::test_trim_matches_the_pop_loop_byte_for_byte` and `::test_trim_encodes_a_logarithmic_number_of_times` both exit 4 with `not found ... no match in any of [<Module test_survey_brief.py>]`. He also ran `uv run pytest skills/survey/scripts -q` (green) and found no TODO/FIXME/XXX/breakpoint/pdb markers.

R1: pass
R2: pass
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

Verdict: 8 findings
Tests: 3925 passed, 0 failed, 9 skipped (suite run this cycle)
