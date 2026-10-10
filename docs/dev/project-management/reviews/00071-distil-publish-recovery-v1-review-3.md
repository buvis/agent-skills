---
prd: docs/dev/project-management/prds/wip/00071-distil-publish-recovery-v1.md
review: 3
date: 2026-10-10
head_sha: 3aa00e22654197801b7f2fed2525fb671334522b
codex_thread_id: 01a1257e-1369-7f72-bb91-5890df090e0f
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
dispatch_rows:
  bob: 2dd62e0a
  carl: d426988c
---

# Review: 00071-distil-publish-recovery-v1

Diff range: `d733c4a4b9b546048159761d136e310795349e50..3aa00e22654197801b7f2fed2525fb671334522b`

codex_rung_guard: not fired

Scope: INCREMENTAL cycle-3 review of the cycle-2 rework (D-tasks 9-12, commits 6ce23a6..5c15799). Commits e3fb4bf, 088f117 and 3aa00e2 are autopilot state only.

pack: failed (`engram pack` exit 1: not inside a registered repo). `{PACK_FILE}` and `{PACK_FINDINGS}` carried `(no pack available this cycle)`. Degraded on retrieval context, not invalid.

checks queue: none written (Eve did not run; Bob's VERIFY bucket is empty).

Carried-forward checks: none (no `-checks-2.json`).

Mechanical test checks: 0 tautological shapes in 45 test functions; fail-first replay ran 1 touched test, 1 failed against base, 0 passed (2 files not collectable at base). No `[MECH]` rows.

Consolidation: `consolidate_findings.py` (script-side), with `--ledger` / `--ledger-dismiss BLAKE`.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [1/4] | 🟡 | `unpublished` adds an "owner" rule the PRD never specifies. For each target only the last kept entry is checked, and any earlier kept entry for the same target is never listed, even if it was never published. It is a defensible reading (a later update supersedes an earlier keep), but it is invented contract. A kept-but-superseded entry stays invisible forever | skills/distil-memory/scripts/docket.py:213 | 2 | BLAKE |
| R2 | [1/4] | 🟡 | `decide` refuses a name-only recovery edit ("a name-only recovery edit ... is refused: pass the note file too"). The PRD allows `--file` and `--name` on a kept entry and says nothing about refusing `--name` alone. It is an extra rule, and SKILL.md documents it at skills/distil-memory/SKILL.md:228 | skills/distil-memory/scripts/docket.py:154 | 2 | BLAKE |
| R3 | [1/4] | 🟡 | Step 7’s new diagnostic recipe differs from `published()`: it uses unsanitised names and omits duplicate pointers. With matching file text and two current pointers, an entry is listed but none of the documented reasons applies. Reuse the writer’s target and pointer rules, including hook normalization and duplicate detection. | skills/distil-memory/SKILL.md:289 | 10 | BOB |
| R4 | [1/4] | ⚪ | `_save_queue` is not wrapped in the `decide` CLI path. A write failure on the queue file (read-only directory, full disk) would raise a traceback instead of exiting with a reason. `decide` writes `name` and `file_text` together in memory and saves once, so the change is all-or-nothing and the queue is not corrupted. This predates the PRD and is outside its stated scope | skills/distil-memory/scripts/docket.py:30 | general | BLAKE |

### Auto-dismissed (ledger)

- [BLAKE] 🟡 `unpublished` silently skips every kept entry whose `Path(transcript).parent / "memory"` does not resolve to `--store` ... | File: skills/distil-memory/scripts/docket.py:216 — by design: one distil queue spans several project stores (corpus.py walks every project dir), so unpublished must route each entry to its own store; the design doc's docket.py contract makes the SKILL.md step 5 store rule executable. Blind lens cannot see the design.
- [BLAKE] ⚪ The PRD says "re-deciding the same state is allowed". A bare `decide <id> kept` ... still raises `no-undecided-entry` ... | File: skills/distil-memory/scripts/docket.py:152 — by design: a bare re-decide changes nothing, and the pre-existing test_docket_cli.py refusal test pins it; the PRD's recovery edit is the --name/--file form, which is accepted.

## Alice

All seven cycle-2 findings (R1-R7) verified resolved in code with tests; no regression. `[ALICE] ✅ No issues found`. Ran distil-memory suite: 743 passed. R1-R13 (no R5 in the rubric): all pass.

## Blake

Five lines: three 🟡 and two ⚪; two auto-dismissed by the ledger (store filter, bare re-decide). R1 (owner rule) is the cycle-2 settled deferral re-raised in new words. Ran distil-memory suite: 743 passed; validate_skill valid.
B1: fail, B6: fail; B2-B5, B7-B19: pass.

## Bob

Resumed the cycle-1/2 codex thread. One finding (R3). FIX: SKILL.md step 7 diagnostic recipe. VERIFY: none. KNOWN: none.
R9: fail; R1-R4, R6-R8, R10-R13: pass.
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

Backend: copilot, model gemini-3.8-flash. `[CARL] ✅ No issues found`. R1-R13 all pass. (`braid` not on his PATH.)

Verdict: 4 findings

Tests: 3559 passed, 0 failed, 6 skipped (reused from last-verification.json at 5c15799)
