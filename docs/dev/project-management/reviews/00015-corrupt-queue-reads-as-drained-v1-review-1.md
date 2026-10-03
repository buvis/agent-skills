---
prd: dev/local/prds/wip/00015-corrupt-queue-reads-as-drained-v1.md
review: 1
date: 2026-09-05
head_sha: 5ef8be11fdc299d360d553f0a45793fe1a48b917
codex_thread_id: 01a070c2-d9c9-7130-9f3f-11e7c42f7ec0
reviewers: alice,blake,bob
agents:
  alice: available
  blake: available
  bob: available
  carl: unavailable
---

# Review: 00015-corrupt-queue-reads-as-drained-v1

Diff range: `aaf190cae3aaf35b94b9c75518e46ca7750333ef..5ef8be11fdc299d360d553f0a45793fe1a48b917`

codex_rung_guard: not fired

pack: unavailable (`engram pack` exited 1 twice — "not inside a registered repo; register it in /Users/bob/.config/gita/repos.csv"). `{PACK_FILE}` and `{PACK_FINDINGS}` were substituted with `(no pack available this cycle)`. The review is degraded by the missing retrieval context, not invalid.

## Review Summary

Reviewed: 3 completed tasks
PRDs checked: 00015-corrupt-queue-reads-as-drained-v1

### Agent Status

- Alice: ✅ Available (consensus lens, engine `legacy`)
- Blake: ✅ Available (blind lens, PRD-only)
- Bob: ✅ Available (doubt + de-slop lens, codex) — **after one retry**, see below
- Carl: ⚠️ Unavailable: both Gemini backends refused. copilot: `Model "gemini-3.1-pro-preview" from --model flag is not available`. Native gemini: `IneligibleTierError: This client is no longer supported for Gemini Code Assist for individuals` (free-tier `UNSUPPORTED_CLIENT`). One retry spent per `retry-policy.md`; consolidation ran at N=3.

### Degradations recorded loud

1. **`gather-context.sh` produced the wrong diff and was overridden.** It resolved its own base as "vs master", but the working branch IS `master`, so it emitted the dirty working tree (three concurrent peer sessions' uncommitted edits to `skills/capture-experiment/**`, `skills/sweep-fix/**`, `skills/handoff-session/`) and none of this PRD's commits. That diff was discarded and rebuilt by hand as `git diff aaf190ca..5ef8be11 -- skills/distil-memory CHANGELOG.md` (428 lines), which is what every reviewer actually received.
2. **Bob's first codex run returned nothing usable.** His sandbox forbids shell commands, so he could not open the context or diff files at all and failed all twelve R rules for lack of input (`bob-output-00015-c1.txt`, retained as evidence). Retried once with the full context and diff inlined as prompt text (`bob-output-00015-c1-retry.txt`); that run produced a real review and is what was consolidated.
3. **`braid --check` could not be run** — warden blocks it in this session too (`[warden] blocked braid: unknown command`), the same gap the build session flagged. Still unverified; it is not a gate for this PRD's files but remains an open check for the repo.

## Consolidated Findings

13 findings, all Medium or Low as raised. One was escalated at the decision gate (below). No reviewer raised a Critical.

| Consensus | Severity | Issue | File | Found By |
|-----------|----------|-------|------|----------|
| [1/3] → 🟠 | 🟠 High (escalated) | F1: Invalid text encoding raises uncaught UnicodeDecodeError, leaving an unreadable queue with process exit 1. | skills/distil-memory/scripts/docket.py:50 | BOB |
| [3/3] | 🟡 Medium | Exit-code tests live in `test_docket_exit_codes.py`, so the literal acceptance command (`pytest test_docket.py`) does not exercise them and the "three test files" sweep returns four | skills/distil-memory/scripts/test_docket_exit_codes.py | ALICE, BLAKE, BOB |
| [2/3] | 🟡 Medium | PRD success criterion demands no xfailed tests across `skills/distil-memory/scripts`; the run reports `545 passed, 1 xfailed` | skills/distil-memory/scripts/test_write.py | ALICE, BLAKE |
| [1/3] | 🟡 Medium | F2: JSON `null` is incorrectly diagnosed as an empty file; it should receive the non-dict schema error. | skills/distil-memory/scripts/docket.py:49 | BOB |
| [1/3] | 🟡 Medium | F3: The preliminary load does not protect against a subsequent read failure inside decide(); that QueueError is still classified as refusal and returns 1. | skills/distil-memory/scripts/docket.py:232 | BOB |
| [1/3] | 🟡 Medium | F4: Corruption fixtures omit a present, non-list `entries` value, leaving an explicitly required rejection untested. | skills/distil-memory/scripts/test_docket_exit_codes.py:38 | BOB |
| [1/3] | 🟡 Medium | F5: The new _proposal helper exposes transcript, name, and file_text variations that none of its callers use. | skills/distil-memory/scripts/test_docket_exit_codes.py:10 | BOB |
| [1/3] | 🟡 Medium | F6: The decide tests introduce tagged failure cases and conditional dispatch for one mocked scenario while duplicating the real-file next test. | skills/distil-memory/scripts/test_docket_exit_codes.py:174 | BOB |
| [1/3] | ⚪ Low | SKILL.md step 5 still says "`decide` and `write` both exit 1 ... instead of raising", not mentioning decide's new exit 2 at its own call sites | skills/distil-memory/SKILL.md | BLAKE |
| [1/3] | ⚪ Low | `decide`'s double `load()` call has a narrow TOCTOU window where a corruption landing between the two reads would be misreported as exit 1 | skills/distil-memory/scripts/docket.py | BLAKE |

(The raw consolidator emitted 13 rows; the four rows describing the test-split deviation are shown merged above at [3/3], since `consolidate_findings.py` kept them separate only because their `File:` fields differed. The unmerged table is reproducible from the three `*-output-00015-c1*.txt` files.)

### Severity escalation, with evidence

Bob raised F1 at 🟡 Medium. The decision gate escalated it to 🟠 **High** after verifying it by execution rather than by reading:

```
F1:  load() raised UnicodeDecodeError (NOT QueueError)
     'utf-8' codec can't decode byte 0xff in position 26: invalid start byte
F1b: CLI `next` on an invalid-UTF-8 queue -> exit=1  stdout=''  traceback_in_stderr=True
```

Exit 1 with empty stdout is exactly what `SKILL.md` step 2 defines as "drained or capped — stop and report". A queue whose bytes are not valid UTF-8 therefore still reads as a drained queue, which is the precise failure this PRD exists to eliminate. `load()` catches `(OSError, json.JSONDecodeError)`, but `UnicodeDecodeError` subclasses `ValueError`, so it escapes that catch, escapes `main()`'s `except QueueError`, and exits 1 with a traceback.

Inherited, not careless: braid's `_load_state` (`src/agent_skills_braid/cli.py:222-225`) carries the identical catch, and the PRD instructed the implementor to copy that pattern. braid has the same hole and is out of scope here; it is a sweep candidate.

### Settled deferrals (recorded in the ledger, not reworked)

- **Test-split / three-file sweep [3/3]** — measured: `test_docket.py` is 780 lines, `test_docket_exit_codes.py` is 224. Merging them to satisfy the literal acceptance command yields a ~1004-line file, breaching the project's 800-line limit (rule R13). The split is the correct engineering call; the literal PRD text is stale. The sweep's actual purpose — proving `SKILL.md` is the whole non-test caller surface for the new exit code — still holds.
- **Pre-existing xfail [2/3]** — `test_write.py::test_an_index_that_cannot_be_read_leaves_no_memory_file_behind` belongs to a different agoge defect (`append_pointer` outside `main()`'s WriteError guard) and predates `work_start_sha` `aaf190c`. Fixing it here is scope creep. The criterion is also suite-wide over a directory this PRD only partly owns, which the repo's own create-prd rule now forbids (commit `5b1cfda`).

## Follow-up Tasks Created

1. [D1] Close the two load() corruption-diagnosis holes in docket.py (M) — 🟠 High + 🟡 — addresses F1, F2 — task 4, opus
2. [D1] Stop decide() misreporting a queue-read failure as a refused decision (S) — 🟡 — addresses F3 and Blake's TOCTOU finding — task 5, sonnet
3. [D1] Cover the untested non-list entries class, finish the SKILL.md exit-2 sweep, and trim test slop (M) — 🟡/⚪ — addresses F4, F5, F6, Blake's SKILL.md step-5 finding — task 6, sonnet

## Alice

Implementation-aware consensus lens. Confirmed by reading both `docket.py` and braid's `_load_state`, and by running the suite: `load()` raises `QueueError` for all five enumerated corruption classes with distinct messages; `main()`'s exit split is correct for `next`/`cursor`/`start`/`save`/`decide`, including the ordering fix that keeps a corrupt-queue error from being reported as a refusal; `SKILL.md` names both exits at steps 2 and 7; `CHANGELOG.md` is accurate. No hardcoded secrets, no injection risk, all functions ≤50 lines, all files ≤800 lines, no TODO/debug markers.

```
[ALICE] 🟡 Task 2's new CLI exit-code tests landed in a new file `test_docket_exit_codes.py` rather than in `test_docket.py`, so the literal acceptance criterion command (`uv run pytest skills/distil-memory/scripts/test_docket.py -q` "passes with new tests...") doesn't actually contain those tests, and PRD Success Criteria bullet 3 ("`rg -n --files-with-matches docket skills src tests` lists only SKILL.md and three test files") is now violated — the sweep returns SKILL.md plus four test files. | File: skills/distil-memory/scripts/test_docket_exit_codes.py | Task: 2
[ALICE] ⚪ PRD Success Criteria states "`uv run pytest skills/distil-memory/scripts -q` reports no failures and no xfailed tests," but the current run reports 1 xfailed (`test_write.py::test_an_index_that_cannot_be_read_leaves_no_memory_file_behind`). Verified via `git merge-base --is-ancestor` that this xfail's commit (`1a60fe0`) predates this PRD's `work_start_sha` (`aaf190c`), so it is pre-existing and unrelated. | File: skills/distil-memory/scripts/test_write.py | Task: general
```

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

Blind lens — PRD only, no diff, no file list. Found the code himself. He independently confirmed the implementation is correct on all five enumerated classes and both documented steps, then ran the PRD's own commands and found three of them do not hold as written. He alone caught the `SKILL.md` step-5 sentence and the `decide` double-load window.

```
[BLAKE] 🟡 Task 2's acceptance criteria required new `docket.main(["next"])==2`/`["cursor"])==2` tests to pass via `test_docket.py`; they were split into a separate file `test_docket_exit_codes.py`, so the literally-specified test command doesn't exercise them | File: skills/distil-memory/scripts/test_docket_exit_codes.py | Task: Split the CLI exit codes
[BLAKE] 🟡 Success Criteria's file-sweep check ("SKILL.md and three test files") returns four test files, not three | File: N/A | Task: general
[BLAKE] 🟡 Success Criteria's `uv run pytest skills/distil-memory/scripts -q` gate ("no failures and no xfailed tests") is false as run: 545 passed, 1 xfailed (pre-existing, unrelated to this PRD) | File: skills/distil-memory/scripts/test_write.py | Task: general
[BLAKE] ⚪ SKILL.md step 5 still says "`decide` and `write` both exit 1 ... instead of raising," not mentioning decide's new exit 2 for an unreadable queue at its own call sites | File: skills/distil-memory/SKILL.md | Task: State the split in SKILL.md
[BLAKE] ⚪ `decide`'s double `load()` call (once in main() to gate exit 2, once inside decide()) has a narrow TOCTOU window where a corruption landing between the two reads would be misreported as exit 1 instead of 2 | File: skills/distil-memory/scripts/docket.py | Task: Split the CLI exit codes
```

```
B1: fail
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
```

## Bob

Doubt + de-slop lens (codex), after one retry with inlined context. He produced the only two findings about the implementation itself rather than about the PRD's own text, and both were verified by execution at the decision gate.

```
[BOB] 🟡 F1: Invalid text encoding raises uncaught UnicodeDecodeError, leaving an unreadable queue with process exit 1. | File: skills/distil-memory/scripts/docket.py:50 | Task: 1
[BOB] 🟡 F2: JSON `null` is incorrectly diagnosed as an empty file; it should receive the non-dict schema error. | File: skills/distil-memory/scripts/docket.py:49 | Task: 1
[BOB] 🟡 F3: The preliminary load does not protect against a subsequent read failure inside decide(); that QueueError is still classified as refusal and returns 1. | File: skills/distil-memory/scripts/docket.py:232 | Task: 2
[BOB] 🟡 F4: Corruption fixtures omit a present, non-list `entries` value, leaving an explicitly required rejection untested. | File: skills/distil-memory/scripts/test_docket_exit_codes.py:38 | Task: 1
[BOB] 🟡 F5: The new _proposal helper exposes transcript, name, and file_text variations that none of its callers use. | File: skills/distil-memory/scripts/test_docket_exit_codes.py:10 | Task: 2
[BOB] 🟡 F6: The decide tests introduce tagged failure cases and conditional dispatch for one mocked scenario while duplicating the real-file next test. | File: skills/distil-memory/scripts/test_docket_exit_codes.py:174 | Task: 2
[BOB] ⚪ F7: Splitting the tests preserves suite coverage, but the PRD's single-file acceptance command excludes them and its three-test-file sweep expectation is now false. | File: N/A | Task: general
```

```
FIX:
- F1 — docket.py:50 — Catch UnicodeError alongside the existing exceptions; add a malformed-byte queue regression asserting exit 2.
- F2 — docket.py:49 — Detect empty text before parsing, then let parsed `null` reach the top-level schema check; test its diagnostic.
- F3 — docket.py:232 — Distinguish decision-refusal exceptions from queue-read errors and remove the preliminary read. Test a read failure during the decision.
- F4 — test_docket_exit_codes.py:38 — Add `{"cursor": 0, "entries": {}}` and assert the entries-list diagnostic and exit 2.
- F5 — test_docket_exit_codes.py:10 — Reduce the helper to `_proposal(line_no)` and construct the currently fixed fields directly.
- F6 — test_docket_exit_codes.py:174 — Parametrize the real-file test over `next` and `decide`; keep the sentinel scenario as a separate test, preserving both testing boundaries.
- F7 — N/A — Update the acceptance command to include both test modules and update the caller-sweep expectation to four test files.
VERIFY:
- (none)
KNOWN:
- (none)
```

```
R1: fail
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: fail
R10: fail
R11: pass
R12: pass
R13: pass
```

```
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass
```

No verification-check queue was written this cycle: Bob's VERIFY bucket is empty, so no finding named an exact runnable check to route.

## Carl

⚠️ Unavailable — not invoked successfully. Both Gemini backends refused before any review ran (copilot: model unavailable; native gemini: free-tier `UNSUPPORTED_CLIENT`). `carl-output-00015-c1.txt` holds only the auth traceback and was deliberately excluded from consolidation so it could not inflate the consensus denominator.

Verdict: 13 findings
Tests: 999 passed, 0 failed, 16 skipped (reused from last-verification.json at 5ef8be1)
