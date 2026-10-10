---
prd: docs/dev/project-management/prds/wip/00071-distil-publish-recovery-v1.md
review: 1
date: 2026-10-10
head_sha: 597b0118ce5430b68111358157da85fcde929a50
codex_thread_id: 01a1257e-1369-7f72-bb91-5890df090e0f
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
dispatch_rows:
  bob: 78678747
  carl: 824f3748
---

# Review: 00071-distil-publish-recovery-v1

Diff range: `20d4d0211f05178fd2a8d1c7bd1f8bed63af7578..597b0118ce5430b68111358157da85fcde929a50`

codex_rung_guard: not fired

Scope: FULL cycle-1 review over the PRD's whole work range (`state.work_start_sha..HEAD`). Commit 23983d2 (CLAUDE.md import bridge) sits in the range but is foreign to this PRD; reviewers were told to ignore it.

pack: failed (`engram pack` exit 1: not inside a registered repo). `{PACK_FILE}` and `{PACK_FINDINGS}` carried `(no pack available this cycle)`. Degraded on retrieval context, not invalid.

checks queue: none written. Bob emitted a VERIFY bucket (F4), but `source: "bob"` is reserved by `references/output-formats.md` and Eve did not run, so F4 stays an ordinary finding (R14).

Consolidation: `consolidate_findings.py` (script-side). Two mech-check rows added by hand from the context file's fail-first replay block (R16, R17).

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [2/4] | 🟡 | `unpublished` reads `entry["transcript"]` and `entry["decision"]` before the envelope-fault handling. A hand-edited or malformed queue entry with a missing or null transcript escapes as `KeyError` or `TypeError`. The CLI only catches `WriteError` and `OSError` here, and the outer handler only catches `QueueError`, so the user gets a traceback instead of the exit-1 diagnostic the PRD requires for store failures. Fix: treat it as an envelope fault (listed) or raise `QueueError` naming the entry. Add a test. | skills/distil-memory/scripts/docket.py:205 | 3 | ALICE, BOB |
| R2 | [2/4] | ⚪ | A name-only recovery edit (`decide kept --name` with no `--file`) can leave `entry["name"]` and the frontmatter `name` in `file_text` disagreeing. A new entry's target stem then comes from the entry name, while the file carries the old name. SKILL.md always passes both. The CLI or `decide` could require `--file` with `--name` for a kept entry, or the docs could say so explicitly. This was recorded as a design question and not resolved. | skills/distil-memory/scripts/docket.py:152 | 3 | ALICE, BLAKE |
| R3 | [1/4] | 🟠 | `write.py main` still tracebacks on an entry whose name sanitises to nothing. `_target_stem` raises `proposal.ProposalError` at write.py:208, and the guard at write.py:224 catches only `WriteError`, `KeyError` and `AttributeError`. I reproduced it: stdin `{"name":"!!!","kind":"new","file_text":...}` gives a traceback, not exit 1 with a reason. This is the same class as the null-kind bug the PRD fixed, and the new `decide --name` rename path feeds it. `decide` stores any `--name` unvalidated (docket.py:160), so a bad rename passes `decide` and then crashes `write`. | skills/distil-memory/scripts/write.py:224 | 1 | BLAKE |
| R4 | [1/4] | 🟡 | docket.py now imports `proposal` and `write` at module top, so every queue verb (`next`, `decide`, `cursor`, `save`) needs PyYAML and the funnel import chain. docket.py was stdlib-only before this diff, so a missing dependency now breaks verbs that never touch a store. Simpler: import `write` and `proposal` inside `unpublished()` and compute the fault tuple there. This was recorded as a design non-blocker and not applied. | skills/distil-memory/scripts/docket.py:10 | 3 | ALICE |
| R5 | [1/4] | 🟡 | `_pointer_state` only looks at the first index line for a stem, but `dedup.parse_index` keeps the last. Stores written by the old always-append rule can hold duplicate lines for one stem. With "first stale, second current", `append_pointer` rewrites the first and leaves two lines. With "first current, second stale", `published` and `append_pointer` report current while the last-wins reader sees the stale hook. No test is seeded with a duplicate. Fix: treat a stem as current only when exactly one line matches with the current hook, and otherwise rewrite the first match and drop the rest in the same write. | skills/distil-memory/scripts/write.py:116 | 1 | ALICE |
| R6 | [1/4] | 🟡 | `docket.py unpublished` silently skips kept entries whose `Path(transcript).parent / "memory"` does not resolve to `--store` (docket.py:205). The PRD never specifies this filter. An entry whose transcript sits elsewhere is never listed, so the check can return a false empty (exit 0) for a store the user passes. The PRD says "never a false empty result". | skills/distil-memory/scripts/docket.py:205 | 2 | BLAKE |
| R7 | [1/4] | 🟡 | `unpublished` has an unrequested "only the last kept entry for a target owns it" rule (docket.py:193-212). An earlier kept entry that is unpublished but shares a target stem with a later one is hidden. The spec lists "kept entries whose intended target content or pointer is missing/mismatched" and does not mention this rule. | skills/distil-memory/scripts/docket.py:211 | 2 | BLAKE |
| R8 | [1/4] | 🟡 | `decide <id> kept` on an already-kept entry with neither `--file` nor `--name` raises `no-undecided-entry` (docket.py:154-157). The PRD says re-deciding the same state is allowed. SKILL.md:214 documents the refusal, so the code and doc agree, but both are narrower than the spec text. | skills/distil-memory/scripts/docket.py:154 | 2 | BLAKE |
| R9 | [1/4] | 🟡 | Several input faults still escape as tracebacks, against the "every failure exits 1 with a reason" responsibility. `json.loads(sys.stdin.read())` is unguarded (write.py:203). A non-dict envelope such as `null` or a list raises `TypeError`, which is not caught. In `unpublished`, a queue entry missing `decision`, `transcript` or `id` raises an uncaught `KeyError` at docket.py:203-205. | skills/distil-memory/scripts/write.py:203 | general | BLAKE |
| R10 | [1/4] | 🟡 | F1: New `_memory_text` and `_proposal` duplicate existing test builders; reuse `write_test_helpers._file_text` and `docket_test_helpers.make_proposal`. | skills/distil-memory/scripts/test_walkthrough_integration.py:92 | 4 | BOB |
| R11 | [1/4] | 🟡 | F2: `_run_write` catches `SystemExit` although its fixed valid arguments reach `write.main` paths that return integers; directly return `write.main(...)`. | skills/distil-memory/scripts/test_walkthrough_integration.py:131 | 4 | BOB |
| R12 | [1/4] | 🟡 | F3: Supersession tests leave only one owner, so they cannot detect incorrect ordering after replacing an owner. Add interleaved targets A1, B1, A2 and assert unpublished ids are B1, A2. | skills/distil-memory/scripts/test_docket_unpublished.py:141 | 3 | BOB |
| R13 | [1/4] | ⚪ | The pointer-retry integration test covers the rollback path, where the file is unlinked and the re-run rewrites it. The PRD defect-4 residue (memory file left on disk, no pointer, re-run through `write.main` for a NEW entry) is only covered as separate pieces: `write_memory` short-circuit, `append_pointer` append, and `unpublished` listing. Only the update variant goes through `main`, in test_write_cli.py:178. Add a `main`-level test for a pre-existing identical new-entry file with no pointer. | skills/distil-memory/scripts/test_walkthrough_integration.py:182 | 4 | ALICE |
| R14 | [1/4] | ⚪ | F4: Cannot statically verify: tests pass, skipped tests do not mask failures, skill validation passes, and braid reports no drift. | N/A | general | BOB |
| R15 | [1/4] | ⚪ | F6: Existing changed artifacts exceed 800 lines: both dispatch ledgers have 1,612 lines and the project capsule has 880. | N/A | general | BOB |
| R16 | [1/4] | 🟡 | 3 touched test(s) pass against the pre-change code: test_decide_dropped_on_a_kept_entry_is_refused_and_leaves_the_queue_file_untouched, test_decide_kept_on_a_kept_entry_without_a_name_or_file_text_is_refused | skills/distil-memory/scripts/test_docket.py | general | mech-check |
| R17 | [1/4] | 🟡 | 1 touched test(s) pass against the pre-change code: test_decide_kept_to_dropped_is_still_refused | skills/distil-memory/scripts/test_docket_cli.py | general | mech-check |

## Alice

Six findings (R1, R2, R4, R5, R13, plus the `proposal` loop-variable shadowing at docket.py:98, which the consolidator folded into R4's file row). R1-R13 (no R5 in the rubric): all pass.

## Blake

Six lines: R3 (🟠), R6, R7, R8, R9, and one ⚪ confirmation (atomic name+file recovery edit) folded into R2. Verified `uv run pytest skills/distil-memory/scripts -q` at 715 passed.
B1: fail, B5: fail, B10: fail, B14: fail; B2-B4, B6-B9, B11-B13, B15-B19: pass.

## Bob

Findings R1 (F5, merged), R10, R11, R12, R14, R15. FIX: F1-F3. VERIFY: F4. KNOWN: F5 (queue-schema hardening deferred in design), F6 (pre-existing oversized ledgers and capsule).
R1: fail, R3: fail, R7: fail, R10: fail, R13: fail; R2, R4, R6, R8, R9, R11, R12: pass.
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

Backend: copilot, model gemini-3.8-flash. `[CARL] ✅ No issues found`. R1-R13 all pass. (Could not run `braid --check`: not on his PATH.)

Verdict: 17 findings

Tests: 3531 passed, 0 failed, 6 skipped (reused from last-verification.json at 70c1e51)
