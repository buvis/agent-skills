---
prd: docs/dev/project-management/prds/wip/00077-docket-never-raises-v1.md
review: 1
date: 2026-10-17
head_sha: 635474028cce467897f0ada9293b1150ea98e4b8
codex_thread_id: 01a1489f-70cb-7603-81d3-e966b8fa5f1e
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
dispatch_rows:
  bob: 8fa95eb2
  carl: ecf92b0a
---

# Review: 00077-docket-never-raises-v1

Diff range: `b7112b5969a6fd6407839016e82303664e835b1e..635474028cce467897f0ada9293b1150ea98e4b8`

codex_rung_guard: not fired

## Review Summary

Reviewed: 3 completed tasks (full review, cycle 1, scope `work_start_sha..HEAD`)
PRDs checked: 00077-docket-never-raises-v1.md
Consensus engine: legacy (single Alice subagent)
Doubt reviewer: codex (no codex-implemented task in `state.tasks`, so Eve did not join)
Cycle id: 00077-c1-20261017

Staging notes:
- pack: failed (engram pack exit 1: worktree not registered with gita); prompts carried `(no pack available this cycle)`. Degraded, not invalid.
- Mechanical test checks: 0 tautological shapes in 9 test functions; fail-first replay 9 touched tests ran, 9 failed against base `b7112b5969a6`, 0 passed. No `[MECH]` finding absorbed.
- Previous-cycle checks carry-forward: none (cycle 1).
- Settled-decisions ledger: none (cycle 1), so no `--ledger` flags on consolidation.
- Verification-check queue: not written this cycle. Bob's VERIFY bucket was `(none)`.
- Bob's first dispatch (row 96dd0f41) returned the lack-of-input refusal shape: codex's `cat` of the context file was blocked by the fact-forcing gate PreToolUse hook, so he emitted only a `⚪ Cannot statically verify` line and twelve `R{n}: fail` verdicts. Closed as `lack-of-input`. The one inlined retry (`bob-prompt-00077-c1-20261017-retry.md`, 67 KB, row 8fa95eb2) produced the review below.
- Consolidation ran via `consolidate_findings.py` (script-side, not model-side). R1 (Alice) and R2 (Blake) describe the same defect, a non-string `file` value in a six-key record still raising TypeError, but anchor different lines (`docket.py:266` vs `docket.py:300`), so the paraphrase merger kept them as two rows. The decision gate should read them as one finding at effective consensus 2/4.

### Agent Status
- Alice: ✅ Available (Claude subagent `autopilot:alice`)
- Blake: ✅ Available (Claude subagent `autopilot:blake`, blind lens, PRD-only)
- Bob: ✅ Available (codex, doubt lens, after one retry (inlined))
- Carl: ✅ Available (gemini-run backend=copilot model=gemini-3.8-flash)

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [1/4] | 🟡 | `save --proposals-dir` still raises a traceback when a record has all six keys but a wrong-typed `file`. A `file` of `null` or a number reaches `proposals_dir / record["file"]` and raises TypeError, which the `(OSError, ValueError)` guard does not catch. I reproduced it with `file: null`: TypeError at docket.py:300, no exit code. This falls just outside the PRD's literal "six keys present" contract but inside its success criterion that the route prints no traceback. Suggested fix: have `_check_batch` also require `isinstance(record["file"], str)` and refuse with a message such as `the record at position {i} has a file that is not a string`. Add a test for it. | skills/distil-memory/scripts/docket.py:266 | 1 | ALICE |
| R2 | [1/4] | 🟡 | A record with the right keys but a non-string `file` (for example `"file": 5` or `null`) still raises an uncaught TypeError at `proposals_dir / record["file"]` (I reproduced the traceback). The spec's goal is that none of these routes print a traceback, though its named cases cover only missing keys, so this is a gap in the spirit of the spec. `transcript` and `line_no` types also go unchecked, and a non-string `transcript` can fail later in `slice_key`/`save`. | skills/distil-memory/scripts/docket.py:300 | Phase 0 task 1 | BLAKE |
| R3 | [1/4] | 🟡 | Tests do not pin whole-batch validation before sibling reads: the later-invalid-record test supplies every sibling, so validation interleaved with reads would also pass. Add a case with an unreadable first sibling and a later malformed record; assert the later record's schema error wins and no queue is written. | skills/distil-memory/scripts/test_docket_never_raises.py:106 | 1 | BOB |
| R4 | [1/4] | ⚪ | Failure before the rename can leave a `.tmp` queue file behind: `_save_queue` has no cleanup if `tmp.write_text` partially writes. The queue itself is unchanged, so this meets "queue bytes unchanged" and is only residue. | skills/distil-memory/scripts/docket.py:32 | Phase 0 task 2 | BLAKE |
| R5 | [1/4] | ⚪ | The spec names `test_docket_refusals.py` as the test module, but the nine new tests are in `test_docket_never_raises.py`. All nine named tests exist with the exact spec names, so this is a placement deviation only. | skills/distil-memory/scripts/test_docket_never_raises.py:52 | general | BLAKE |

Severity totals: 🔴 0, 🟠 0, 🟡 3, ⚪ 2.

## Alice

[ALICE] 🟡 `save --proposals-dir` still raises a traceback when a record has all six keys but a wrong-typed `file`. A `file` of `null` or a number reaches `proposals_dir / record["file"]` and raises TypeError, which the `(OSError, ValueError)` guard does not catch. I reproduced it with `file: null`: TypeError at docket.py:300, no exit code. This falls just outside the PRD's literal "six keys present" contract but inside its success criterion that the route prints no traceback. Suggested fix: have `_check_batch` also require `isinstance(record["file"], str)` and refuse with a message such as `the record at position {i} has a file that is not a string`. Add a test for it. | File: skills/distil-memory/scripts/docket.py:266 | Task: 1

Checks run:
- `uv run pytest skills/distil-memory/scripts -q`: 769 passed, 1 warning (a pytest tmp-dir cleanup warning), 0 failed.
- `rg -n "json.JSONDecodeError" skills/distil-memory/scripts/docket.py` matches only docket.py:50, inside `load()`, as required.
- The fail-first replay in the context shows all 9 new tests failing against the base commit, so none is tautological.
- Function sizes are within the 50-line limit; `_save_from_proposals_dir` is 43 lines.
- `QueueError` is a `ValueError`, but the widened guard wraps only the reads. The separate `save()` guard catches only `OSError`, so a corrupt queue still leaves through `main()` as exit 2.

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

[BLAKE] 🟡 A record with the right keys but a non-string `file` (for example `"file": 5` or `null`) still raises an uncaught TypeError at `proposals_dir / record["file"]` (I reproduced the traceback). The spec's goal is that none of these routes print a traceback, though its named cases cover only missing keys, so this is a gap in the spirit of the spec. `transcript` and `line_no` types also go unchecked, and a non-string `transcript` can fail later in `slice_key`/`save`. | File: skills/distil-memory/scripts/docket.py:300 | Task: Phase 0 task 1
[BLAKE] ⚪ Failure before the rename can leave a `.tmp` queue file behind: `_save_queue` has no cleanup if `tmp.write_text` partially writes. The queue itself is unchanged, so this meets "queue bytes unchanged" and is only residue. | File: skills/distil-memory/scripts/docket.py:32 | Task: Phase 0 task 2
[BLAKE] ⚪ The spec names `test_docket_refusals.py` as the test module, but the nine new tests are in `test_docket_never_raises.py`. All nine named tests exist with the exact spec names, so this is a placement deviation only. | File: skills/distil-memory/scripts/test_docket_never_raises.py:52 | Task: general

Verified:
- The proposals read guard is `(OSError, ValueError)` (docket.py:313).
- `_check_batch` (docket.py:266-277) rejects a non-list top level, a non-object record, and a record missing any of the six keys. It runs before any sibling read and before any queue write, and it reports the record's position.
- The `save`, `decide` and `start` verbs map OSError to exit 1 with `cannot write the review queue <path>: <error>` (docket.py:316-320, 341-343, 354-358).
- QueueError still exits 2 through main (docket.py:382-384).
- `decide` still reads the queue once (docket.py:335).
- `JSONDecodeError` appears only in `load()` (docket.py:50), as the success criterion requires.
- SKILL.md:205-207 names the failed-write case, and CHANGELOG.md:104-105 has the `**distil-memory**` Fixed entries.
- `uv run pytest skills/distil-memory/scripts -q` gives 769 passed, 0 failed. `validate_skill.py` reports the skill valid.

B1: pass
B2: pass
B3: pass
B4: pass
B5: pass
B6: pass
B7: pass
B8: pass
B9: pass
B10: fail
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

First run (row 96dd0f41): lack-of-input refusal. codex's `cat docs/dev/tmp/review-context-00077-c1-20261017.md` was blocked by the fact-forcing gate PreToolUse hook; the output was a single `[BOB] ⚪ Cannot statically verify ...` line with twelve `R{n}: fail` verdicts and `D1`-`D5: pass`. Not consolidated. Retry (row 8fa95eb2, inlined context and diff) produced:

[BOB] 🟡 Tests do not pin whole-batch validation before sibling reads: the later-invalid-record test supplies every sibling, so validation interleaved with reads would also pass. Add a case with an unreadable first sibling and a later malformed record; assert the later record's schema error wins and no queue is written. | File: skills/distil-memory/scripts/test_docket_never_raises.py:106 | Task: 1

FIX:
- Pin validation before sibling reads — skills/distil-memory/scripts/test_docket_never_raises.py:106 — Add a missing first sibling followed by a record missing `evidence_text`; assert stderr names `position 2` and `missing evidence_text`, with no queue written.

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

Backend: copilot, model gemini-3.8-flash (no native fallback). Carl read the context and diff, ran `uv run pytest skills/distil-memory/scripts -q` and the skill validator, and searched for `json.JSONDecodeError`, the SKILL.md exit-code line, the CHANGELOG entry and TODO markers.

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

## Verdict

Verdict: 5 findings
Tests: 3825 passed, 1 failed, 6 skipped (suite run this cycle)

The one failure is `tests/test_conftest_fixtures.py::test_armed_directory_refuses_a_childs_stat`, a pre-existing environment failure that also fails at base `b7112b5` and touches none of this PRD's files (recorded in the build contract card). `uv run pytest skills/distil-memory/scripts -q`: 769 passed, 0 failed.
