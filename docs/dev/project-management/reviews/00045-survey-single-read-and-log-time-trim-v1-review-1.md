---
prd: docs/dev/project-management/prds/wip/00045-survey-single-read-and-log-time-trim-v1.md
review: 1
date: 2026-10-18
head_sha: 7a9c07e5c942b3b567c7a4c86cfbdd7d042c12cf
codex_thread_id: 01a14f37-bb0f-7ff2-80cd-da03a450cb21
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
dispatch_rows:
  bob: 4016b455
  bob_retry: 1caae303
  carl: e57d3df6
---

# Review: 00045-survey-single-read-and-log-time-trim-v1 (cycle 1, full)

Diff range: `370f43ba5633280fbbc9db2cc5656abfcb760f59..7a9c07e5c942b3b567c7a4c86cfbdd7d042c12cf`

codex_rung_guard: not fired

pack: failed (engram pack exit 1: not inside a registered repo; run `gita add /Users/bob/git/src/github.com/buvis/agent-skills`)

Mechanical checks: 3 `[MECH]` findings from the fail-first replay (87 test functions checked in 6 test files, 0 tautological shapes). Replay: 85 touched tests ran against `370f43ba5633`, 36 failed there, 49 passed. The three replay lines are absorbed as findings R9-R11 below.

## Review Summary

Reviewed: 6 completed tasks
PRDs checked: 00045-survey-single-read-and-log-time-trim-v1

### Agent Status

- Alice: ✅ Available
- Blake: ✅ Available
- Bob: ✅ Available (first run was a lack-of-input refusal - the codex sandbox failed `sandbox_apply` before reading the staged files; re-dispatched as the inlined retry per retry-policy.md, `after one retry (inlined)`)
- Carl: ✅ Available (`backend=copilot model=gemini-3.8-flash`)

Consolidation note: Bob emits his issue lines inside the FIX/KNOWN buckets with a `- ` list prefix, which `consolidate_findings.py` does not parse. His three lines were re-emitted unprefixed into `bob-output-20261018t1330.norm.txt` and that file was consolidated, so his attribution appears in the table. No wording was changed.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [4/4] | 🟡 | Redundant tests: test_survey_trim.py repeats work the PRD-named tests already do. It defines a second _reference_trim at test_survey_trim.py:185, duplicating test_survey_brief.py:444. It defines a second test_trim_encodes_a_logarithmic_number_of_times at test_survey_trim.py:243, duplicating test_survey_brief.py:472. Its budget-sweep test overlaps test_trim_matches_the_pop_loop_byte_for_byte. Keep one oracle and one call-count test, for example by importing the reference from one place or deleting the weaker copy. The 29 tests in this file that pass against the pre-change code are the behaviour-preserving pins the sweep makes redundant | skills/survey/scripts/test_survey_trim.py:185 | 6 | ALICE, BLAKE, BOB, CARL |
| R2 | [4/4] | 🟡 | Contract deviation, accepted in the design but not fully met: _survey skips any file absent from texts (run.py:435) instead of passing texts.get(f) as the contract states. Behaviour is equivalent, because both extractors return [] on OSError. But an unreadable file is still attempted twice, once in _read_sampled_texts (run.py:416) and once in the _compute_error_style fallback (run.py:254). That is strictly "read more than once" for the failing case. Impact is negligible | skills/survey/scripts/run.py:435 | 2 | ALICE, BLAKE, BOB, CARL |
| R3 | [3/4] | 🟠 | Unrelated changes in the diff. skills/glean/scripts/glean.py and test_glean.py carry formatter-only rewrites: re.I becomes re.IGNORECASE, trailing commas and line wraps. They are the pre-existing uncommitted edits, not part of PRD 00045. Keep them out of this PRD's commit | skills/glean/scripts/glean.py:38 | general | ALICE, BOB, CARL |
| R4 | [1/4] | 🟠 | Unreadable file failing initial read is re-read from disk in _compute_error_style | skills/survey/scripts/run.py:254 | 2 | CARL |
| R5 | [1/4] | 🟡 | Scope creep: _build_brief was split into three new helpers (_brief_naming_section, _brief_index_section, _brief_extension_section). No PRD task or the design doc asks for this. The binary-search and single-read changes do not touch brief assembly. Revert it to keep the diff traceable, or record it as a separate pre-existing function-size cleanup | skills/survey/scripts/run.py:287 | general | ALICE |
| R6 | [1/4] | 🟡 | Redundant tests: test_survey_single_read.py:73 (reads each sampled file exactly once) and :192 (the same check beyond 50 files) re-assert the single-read rule that test_no_sampled_file_is_read_from_disk_twice (test_survey.py:387) already pins. The new file is useful for the empty-text, over-50-file, unreadable-file and fresh-per-call cases. Fold the exact-once checks into the PRD-named test, or drop the overlap | skills/survey/scripts/test_survey_single_read.py:73 | 3 | ALICE |
| R7 | [1/4] | 🟡 | _read_sampled_texts omits if f not in texts guard specified in task contract | skills/survey/scripts/run.py:415 | 2 | CARL |
| R8 | [1/4] | ⚪ | _read_sampled_texts is a new helper not listed under the PRD's "New symbols". It is private and the PRD only names _encoded_len | skills/survey/scripts/run.py:410 | 2 | BLAKE |
| R9 | [1/4] | 🟡 | 16 touched test(s) pass against the pre-change code: test_trim_matches_the_pop_loop_byte_for_byte +10 more | skills/survey/scripts/test_survey_brief.py | general | mech-check |
| R10 | [1/4] | 🟡 | 4 touched test(s) pass against the pre-change code: test_survey_brief_still_reflects_file_contents_after_single_read, test_survey_reads_current_contents_on_every_call, test_survey_unreadable_file_is_skipped_without_error, test_survey_invalid_utf8_file_degrades_instead_of_crashing | skills/survey/scripts/test_survey_single_read.py | general | mech-check |
| R11 | [1/4] | 🟡 | 29 touched test(s) pass against the pre-change code: test_trim_keeps_largest_prefix_of_whole_lines_that_fits +23 more | skills/survey/scripts/test_survey_trim.py | general | mech-check |

## Alice

Five findings, listed above as R1, R2, R3, R5, R6. Alice checked the trimmer against the pre-change pop loop and found no divergence: 1 `_encoded_len` call when the content fits, about log2(n) more otherwise, which is 11 calls for 600 lines against the bound of 12. A negative budget and k=0 both return `""`. She ran `uv run pytest skills/survey/scripts -q`: 135 passed, 8 skipped, 0 failed. The skips are the pre-existing tree-sitter-conditional marks in `survey_test_helpers.py`, not new ones.

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

Three Low findings, listed above as R1 (test_survey_trim.py duplication), R2/R8 (the unreadable-file second attempt, and `_read_sampled_texts` not being a PRD-named new symbol). No spec violations found.

Blake verified independently: the only `read_text` calls in `run.py` are at lines 141, 186, 254 and 417; 141, 186 and 254 are fallback branches and 417 is the single read in `_read_sampled_texts`. `_encoded_len` exists at `run.py:367`, `while lines and len` no longer matches, and the trailing blank/`## ` cleanup survives at `run.py:391-392`. All three PRD-named tests exist and pass. He ran `uv run pytest skills/survey/scripts -q`: 135 passed, 8 skipped, 0 failed, 0 errors. He did not run the new tests against the pre-fix `run.py`, so the spec's fail-before-fix criterion is unconfirmed by him; the mechanical fail-first replay covers it instead (36 of 85 touched tests fail at base).

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

## Bob (doubt lens + de-slop) — after one retry (inlined)

FIX:
- 🟡 An unreadable sampled file is read twice: `_read_sampled_texts` catches its OSError, then `_compute_error_style` retries it. This violates the single-read must-have; the unreadable-file test never counts attempts. Cache failed reads as empty text during `_survey` and assert exactly one attempted read. | File: skills/survey/scripts/run.py:410 | Task: 2
- 🟡 Two identical `_reference_trim` implementations duplicate the behavioral oracle. Keep one shared reference helper while retaining the required named tests and broader budget sweep. | File: skills/survey/scripts/test_survey_trim.py:185 | Task: 5

VERIFY:
- (none)

KNOWN:
- ⚪ `cmd_scan` measures 54 lines, exceeding the 50-line rubric limit. The context identifies glean edits as pre-existing unrelated work; exclude their cleanup from this survey PRD. | File: skills/glean/scripts/glean.py:191 | Task: general

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
R12: fail
R13: pass

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

`backend=copilot model=gemini-3.8-flash`. Six findings, consolidated above as R1, R2, R3, R4, R7 (his `cmd_scan` 54-line 🟠 merged into R3, the glean out-of-scope row, on file match). Carl ran `uv run pytest skills/survey/scripts skills/glean/scripts -q` and checked for TODO/FIXME/pdb markers in both skills: none found.

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
R12: fail
R13: pass

Verdict: 11 findings
Tests: 3943 passed, 0 failed, 9 skipped (suite run this cycle)
