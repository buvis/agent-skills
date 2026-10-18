---
prd: docs/dev/project-management/prds/wip/00045-survey-single-read-and-log-time-trim-v1.md
review: 3
date: 2026-10-18
head_sha: c2444b4a416c667c8513274f7213473d0dbfa9dc
codex_thread_id: 01a14f5d-067d-77f0-9393-34e05c718051
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
dispatch_rows:
  bob: 7e17dc41
  carl: c036134c
---

# Review: 00045-survey-single-read-and-log-time-trim-v1

Diff range: `d4d73c0f4cddca5aa7844fb5557420fdd8c75eb2..c2444b4a416c667c8513274f7213473d0dbfa9dc`

codex_rung_guard: not fired

## Review Summary

Reviewed: 13 completed tasks (4 cycle-2 rework tasks since the prior review: tasks 10-13)
PRDs checked: 00045-survey-single-read-and-log-time-trim-v1

### Agent Status

- Alice: ✅ Available
- Blake: ✅ Available
- Bob: ✅ Available (first run was a lack-of-input refusal - the codex sandbox failed `sandbox_apply` before reading the staged files, the same shape as cycles 1 and 2; re-dispatched as the inlined retry per retry-policy.md, `after one retry (inlined)`)
- Carl: ✅ Available (`backend=copilot model=gemini-3.8-flash`)

Notes on this cycle's mechanics:

- `engram pack` failed (`not inside a registered repo`), so both doubt/consensus prompts carried `(no pack available this cycle)`. Degraded, not invalid.
- `review-stage --gate-command dev/bin/release-checks` exited 127 (that script does not exist in this repo), so its `Tests:` line was unusable and the suite was run here instead. The `Tests:` line below is that run.
- Bob's retry emitted its three findings as `- [BOB] …` bullet lines. `consolidate_findings.py` parses only unbulleted `[AGENT] …` lines and silently dropped all three on the first consolidation run; the bullets were stripped and consolidation re-run, so Bob's findings are in the table. Flagging the parser's silent drop as a pack-level issue, not a finding against this PRD.
- Carl ran `uv run ruff check skills/survey/scripts` and it exits 1 with 13 pre-existing lint errors (import sorting, 4x E501, 2x UP012) in `skills/survey/scripts`. These predate this PRD's work and are repo-wide style, not part of the reviewed diff; recorded here so they are not silently ignored.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [3/4] | 🟡 | The unreadable-file fix in `_read_sampled_texts` (`texts[f] = ""`) is not pinned by any test. `test_survey_unreadable_file_is_skipped_without_error` only checks the brief output, which is identical with the old `pass`. The single-read tests do not count attempts on a failing file. Reverting run.py:421 to `pass` would therefore leave the suite green, and the cycle-2 R1 suggestion to add a test asserting one attempt was not taken. Add a test that fails reads for one file with `OSError` and asserts exactly one attempt, for example by counting calls in `failing_read` at skills/survey/scripts/test_survey_single_read.py:121. | skills/survey/scripts/test_survey_single_read.py:111 | 12 | ALICE, BLAKE, BOB |
| R2 | [1/4] | 🟡 | The restored equality test pairs each shape with one budget; the PRD requires every shape at all four budgets. Iterate over the four shapes × four budgets. | skills/survey/scripts/test_survey_brief.py:478 | 5 | BOB |
| R3 | [1/4] | 🟡 | The encode-count assertion accepts zero calls, so restoring the original inline pop loop would pass this performance test. Assert `1 <= call_count["n"] <= 12`; retain the separate output oracle. | skills/survey/scripts/test_survey_brief.py:515 | 6 | BOB |
| R4 | [1/4] | ⚪ | Task 2 acceptance says every `read_text` in `run.py` must sit on a `text is None` or `texts`-miss fallback, but skills/survey/scripts/run.py:419 is the primary read in `_read_sampled_texts`. The intent (one read per file) is met; a literal reading of the criterion is not. | skills/survey/scripts/run.py | 2 | BLAKE |
| R5 | [1/4] | ⚪ | The byte-for-byte trim test pairs one input with one budget (0, 64, 512, 5120). The PRD acceptance could be read as every case at every budget. Coverage is adequate but not a full cross-product. | skills/survey/scripts/test_survey_brief.py:477 | 5 | BLAKE |
| R6 | [1/4] | 🟡 | 2 touched test(s) pass against the pre-change code: test_trim_matches_the_pop_loop_byte_for_byte, test_trim_encodes_a_logarithmic_number_of_times | skills/survey/scripts/test_survey_brief.py | general | mech-check |
| R7 | [1/4] | 🟡 | 1 touched test(s) pass against the pre-change code: test_survey_empty_file_is_read_from_disk_only_once | skills/survey/scripts/test_survey_single_read.py | general | mech-check |

Alice's ⚪ stale-docstring note (`test_survey_unreadable_file_is_skipped_without_error` still describes a KeyError that the `""` change removed, test_survey_single_read.py:114) merged into R1 by suffix-stripped citation matching; it belongs to the same test and the same fix.

### Auto-dismissed (ledger)

- [BLAKE] ⚪ The tree-sitter path (`_extract_tree_sitter` with supplied text, and the Go merge) has no run coverage here because `tree_sitter_language_pack` is absent. The single-read test only exercises the regex path in this environment. | File: skills/survey/scripts/test_survey.py — Environmental, not a code defect: tree-sitter is not installed in this sandbox, so the existing tree-sitter-conditional tests skip. Blake verified by inspection that run.py:139-143, 162 and 173 forward `text` on that path. Adding a test that can only skip here buys no coverage; the pre-existing conditional marks already cover it where tree-sitter is present.

### Prior-cycle findings

- Cycle-2 R2, R3 (PRD-named tests deleted) → **resolved**: `test_trim_matches_the_pop_loop_byte_for_byte` and `test_trim_encodes_a_logarithmic_number_of_times` are back in `skills/survey/scripts/test_survey_brief.py`, the oracle `_reference_trim` is defined once, and the duplicates were removed from `test_survey_trim.py` with no orphan imports. Both PRD acceptance node ids pass.
- Cycle-2 R4 (empty-file read count) → **resolved**: `test_survey_empty_file_is_read_from_disk_only_once` pins it and would fail under an `if not text` check.
- Cycle-2 R1 (unreadable file read more than once) → **code fixed, pin missing**: `_read_sampled_texts` records a failed read as `""` (run.py:421), so no consumer re-reads; no test counts the attempts, which is R1 above.
- Cycle-2 R5-R8 stay closed under the settled decisions.

## Alice

Two findings (R1, and the ⚪ stale docstring merged into it). She confirmed cycle-2 R2, R3 and R4 resolved and R1's code fixed but unpinned, and re-raised nothing from the settled ledger. She ran `uv run pytest skills/survey/scripts -q`: 114 passed, 8 skipped, 0 failed, plus the two PRD acceptance tests by node id (both pass).

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

## Blake

Blind lens, PRD only. He located the implementation himself and verified the optional-`text` plumbing (`_extract_tree_sitter`, `_extract_file_symbols`, `_extract_file_symbols_regex`, the `.go` merge call), `_compute_error_style(texts=None)`, `_survey`'s single `_read_sampled_texts` pass, `_encoded_len`'s existence and the absence of the old pop loop, the binary-search trimmer's equivalence to the pop loop, and the encode-call bound (11 calls against a limit of 12 for 600 lines). He ran `uv run pytest skills/survey/scripts -q`: 114 passed, 8 skipped, 0 failed. Four ⚪ findings, no Critical/High/Medium, one of them ledger-dismissed. No secrets, auth, destructive or migration concerns.

B1-B19: pass (all nineteen).

## Bob (doubt lens + de-slop) — after one retry (inlined)

Three 🟡 findings (R1, R2, R3), all about tests not pinning the behavior they name. FIX bucket: the three above. VERIFY: none. KNOWN: none. No verification-check queue was written for this cycle: the doubt lens emitted no VERIFY items.

R1: fail
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

`[CARL] ✅ No issues found`. He read the context and the whole diff, ran the survey suite and the four PRD acceptance node ids, read the changed `run.py` and test regions, ran `validate_skill.py skills/survey` (ok) and the repo suite, and found no TODO/FIXME/breakpoint markers. His `braid --check` and `ruff` observations are recorded in the summary notes above (braid is not on this sandbox's PATH; the ruff errors are pre-existing).

R1-R13: pass (all twelve emitted).

Verdict: 7 findings
Tests: 3922 passed, 0 failed, 9 skipped (suite run this cycle)
