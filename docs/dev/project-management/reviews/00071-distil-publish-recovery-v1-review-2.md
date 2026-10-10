---
prd: docs/dev/project-management/prds/wip/00071-distil-publish-recovery-v1.md
review: 2
date: 2026-10-10
head_sha: d733c4a4b9b546048159761d136e310795349e50
codex_thread_id: 01a1257e-1369-7f72-bb91-5890df090e0f
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
dispatch_rows:
  bob: ed47466b
  carl: 24a7314d
---

# Review: 00071-distil-publish-recovery-v1

Diff range: `597b0118ce5430b68111358157da85fcde929a50..d733c4a4b9b546048159761d136e310795349e50`

codex_rung_guard: not fired

Scope: INCREMENTAL cycle-2 review of the cycle-1 rework (D-tasks 5-8). Commit 6650ccc (structure-git-repo) and d733c4a (autopilot state) sit in the range but are foreign to this PRD; reviewers were told to ignore them.

pack: failed (`engram pack` exit 1: not inside a registered repo). `{PACK_FILE}` and `{PACK_FINDINGS}` carried `(no pack available this cycle)`. Degraded on retrieval context, not invalid.

checks queue: none written (Eve did not run; Bob's VERIFY bucket is empty).

Carried-forward checks: none (no `-checks-1.json`).

Mechanical test checks: 0 tautological shapes in 112 test functions; fail-first replay ran 0 touched tests (7 files not collectable at base). No `[MECH]` rows.

Consolidation: `consolidate_findings.py` (script-side), with `--ledger` / `--ledger-dismiss BLAKE`.

R1 confirmed by the orchestrator: an update entry with `existing_text: null` overwrites the target, `append_pointer` raises an uncaught `AttributeError`, and no rollback runs (store left holding the new text).

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [1/4] | 🟠 | `write.py write` throws an uncaught `AttributeError` and leaves the store changed when an update entry has `existing_text: null`. I reproduced it with `kind: "update w"` and a null `existing_text`. The memory file was overwritten with the new text, `append_pointer` raised from `proposal.parse_frontmatter(None)`, and a traceback was printed. No rollback ran, because the pointer-stage handler catches only `OSError`, `WriteError`, `ProposalError` and `KeyError`. The spec says every failure exits 1 with a reason and the 00017 rollback is preserved. | skills/distil-memory/scripts/write.py:250 | 1 | BLAKE |
| R2 | [1/4] | 🟡 | `docket.py decide --file` with a non-UTF-8 file raises an uncaught `UnicodeDecodeError`. The handler catches `OSError` and `json.JSONDecodeError` but not `UnicodeDecodeError`, so the user gets a traceback instead of exit 1 with a reason. I reproduced it. | skills/distil-memory/scripts/docket.py:316 | 2 | BLAKE |
| R3 | [1/4] | 🟡 | SKILL.md step 7 tells the driver to show the user "why" each entry is unpublished (file missing, text differs, or pointer missing). `unpublished` prints only ids, so the driver would have to re-derive the reason with nothing in the CLI to help. | skills/distil-memory/SKILL.md:289 | 4 | BLAKE |
| R4 | [1/4] | 🟡 | F1: Duplicate-pointer tests partition matching and unrelated lines, hiding pointer placement. Replace the filtering helpers with full-index assertions and separate duplicates with an unrelated line to pin preservation of the first match’s position. | skills/distil-memory/scripts/test_write_duplicate_pointers.py:42 | 5 | BOB |
| R5 | [1/4] | ⚪ | `_read_entry` catches only `json.JSONDecodeError`, so stdin that is not valid UTF-8 raises `UnicodeDecodeError` from `sys.stdin.read()` and gives a traceback instead of exit 1 with a reason. This is the same class as the R9 fix and has no test. | skills/distil-memory/scripts/write.py:208 | 5 | ALICE |
| R6 | [1/4] | ⚪ | The new CHANGELOG line says the queue verbs "no longer load the memory-writing modules". No release ever loaded them, because the top-level import was added and removed within this unreleased PRD. The line describes a delta users never saw and should be dropped or reworded. The `--name` and `--file` clause on the same line has the same problem, since it changes behaviour of an unreleased feature. | CHANGELOG.md:100 | 6 | ALICE |
| R7 | [1/4] | ⚪ | F2: `decide` still documents recovery with “file_text and/or name,” although name-only recovery now raises `QueueError`. Document required `file_text` and optional `name`. | skills/distil-memory/scripts/docket.py:135 | 6 | BOB |

### Auto-dismissed (ledger)

- [BLAKE] 🟠 `unpublished` silently skips any kept entry whose `transcript.parent/"memory"` does not resolve to `--store` ... | File: skills/distil-memory/scripts/docket.py:215 — by design: one distil queue spans several project stores (corpus.py walks every project dir), so unpublished must route each entry to its own store; the design doc's docket.py contract makes the SKILL.md step 5 store rule executable. Blind lens cannot see the design.
- [BLAKE] 🟡 The `unpublished` listing adds a rule the spec doesn't state: only the last kept entry for a target owns it ... | File: skills/distil-memory/scripts/docket.py:221 — by design: listing a superseded earlier entry would let a re-publish revert a newer memory, and two entries for one stem would alternate forever; the design review adopted one owner per target stem.
- [BLAKE] ⚪ `decide <id> kept` with no `--file` or `--name` on an already-kept entry is refused ... | File: skills/distil-memory/scripts/docket.py:151 — by design: a bare re-decide changes nothing, and the pre-existing test_docket_cli.py refusal test pins it; the PRD's recovery edit is the --name/--file form, which is accepted.

## Alice

All ten prior findings (R1-R5, R9-R13 of cycle 1) verified resolved; no regression. Two ⚪ findings (R5, R6). R1-R13 (no R5 in the rubric): all pass.

## Blake

Six lines: R1 (🟠), R2, R3 (🟡), plus three ledger auto-dismissals (store filter, owner rule, bare re-decide). Ran the distil-memory suite: 740 passed.
B1: fail, B3: fail, B5: fail, B12: fail, B14: fail; B2, B4, B6-B11, B13, B15-B19: pass.

## Bob

Resumed cycle-1 codex thread. Findings R4 (F1), R7 (F2). FIX: F1, F2. VERIFY: none. KNOWN: none.
R1: fail; R2-R4, R6-R13: pass.
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

Backend: copilot, model gemini-3.8-flash. `[CARL] ✅ No issues found`. R1-R13 all pass. (`braid` not on his PATH.)

Verdict: 7 findings

Tests: 3556 passed, 0 failed, 6 skipped (suite run this cycle)
