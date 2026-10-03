---
prd: dev/local/prds/wip/00007-extract-memory-candidates-from-transcripts-v1.md
review: 2
date: 2026-08-30
head_sha: 0df93920261c113df87af28237c26c3dab699794
codex_thread_id: 01a05058-78fa-7f21-a9c8-fbdf3449e8d9
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00007-extract-memory-candidates-from-transcripts-v1

Diff range: `67fa8989ddd7bf6666d8b088ae3281a7f8220b11..0df93920261c113df87af28237c26c3dab699794`

codex_rung_guard: not fired

## Review Summary

Reviewed: 14 completed tasks (9 build + 5 cycle-1 rework)
PRDs checked: 00007-extract-memory-candidates-from-transcripts-v1.md
Cycle: 2 of a cap of 2 — this cycle is AT THE CAP. Consensus engine: `legacy`. Doubt reviewer: `codex` (Bob).
Scope: **incremental review** of the rework since cycle 1. 8 files changed, 1390 insertions, 840 deletions.

### Agent Status

- Alice: ✅ Available (Claude subagent, consensus lens)
- Blake: ✅ Available (Claude subagent, blind lens — PRD-only)
- Bob: ✅ Available (codex, consensus + doubt/de-slop lens; cycle-1 thread resumed via `--resume-thread`)
- Carl: ✅ Available (gemini via copilot backend)
- Eve: ⏸️ Disabled — `doubt_reviewer` resolved to `codex` and the codex doubt-roster guard did not fire (0 codex-implemented tasks; every attempt ran implementor `claude`), so the opt-in fifth lens was not activated.

### Run conditions worth recording

1. **No engram context pack, again.** `engram pack` exited 1 with `not inside a registered repo; register it in /Users/bob/.config/gita/repos.csv`. The precondition (`git rev-parse --show-toplevel`) succeeds here, so the pack was attempted and failed; the failure is deterministic and identical to cycle 1, so it was not retried. Every implementation-aware prompt received the sentinel `(no pack available this cycle)`. The review is degraded on retrieval context, not invalid. Blake never receives a pack by design.
2. **Branch-base diff is empty on this repo** (work is committed directly to `master`), so `gather-context.sh` was run with an explicit `--since 67fa898…`, which is the correct incremental range.
3. **Blake's filesystem-notes block did not apply.** `dev/local` is a real directory here and the project root's basename does not start with `.`, so neither trigger fired and no block was prepended.

## Consolidated Findings

11 findings. Consensus is out of 4 active reviewers. No Critical. One finding was raised at 🟠 High and reclassified to 🟡 Medium at the gate — see Gate decisions.

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [1/4] | 🟡 Medium (raised 🟠, reclassified) | `_run_triage()` converts `TimeoutExpired` to `str(exc)`; that string includes `exc.cmd`, whose argv contains the full transcript-derived prompt, so a timeout prints slice text to stderr | skills/distil-memory/scripts/funnel.py:236 | 10 | BOB |
| [1/4] | 🟡 Medium | `test_funnel_report.py` is 655 lines — under the 800 hard cap but outside task 14's own "200-400 where practical" target for the split files | skills/distil-memory/scripts/test_funnel_report.py | 14 | ALICE |
| [1/4] | 🟡 Medium | `scan()` wraps each `(line_no, entry)` pair in a fresh one-element list on every iteration just to call `_raw_marker_hits([...])` and `assistant_only([...])`, both written for lists of entries; a per-entry helper would read more directly | skills/distil-memory/scripts/funnel.py | 13 | ALICE |
| [1/4] | 🟡 Medium | Phase 1's literal Exit Criteria command fails: the PRD names `scripts/test_funnel.py`, which no longer exists (split in `0df9392`). The three split files pass 79/79, so coverage is intact, but the literal deliverable the PRD names is gone | skills/distil-memory/scripts/test_funnel.py | Phase 1 | BLAKE |
| [1/4] | 🟡 Medium | `corpus.py`'s declared export `assert_contract(version)` does not match its actual signature `assert_contract(version, parser_module, minimum=_MIN_VERSION)`; a caller going by the terse Exports line alone would hit `TypeError` | skills/distil-memory/scripts/corpus.py | Phase 0 | BLAKE |
| [1/4] | 🟡 Medium | The reworked CLI can render `survivors: n/a` after a triage failure and now counts one match per text block, but `SKILL.md` still documents `n/a` only for dry runs and says every raw marker hit is counted | skills/distil-memory/SKILL.md:57 | general | BOB |
| [1/4] | 🟡 Medium | The streaming test detects only `list(iterator)` through `__length_hint__`; a list comprehension or tuple materialization would still buffer the transcript while passing the test, so it does not bind to the bounded-memory intent | skills/distil-memory/scripts/test_funnel_extraction.py:355 | 13 | BOB |
| [1/4] | 🟡 Medium | The three 40-line model-failure tests repeat nearly identical corpus/module/report setup and differ only by subprocess outcome and expected stderr; a shared fixture plus parametrization would be substantially simpler | skills/distil-memory/scripts/test_funnel_report.py:300 | 10 | BOB |
| [1/4] | ⚪ Low | `main()`'s docstring still says "Returns 0 on success" with no mention of the non-zero paths task 10 added (model-call failure, report-write failure) | skills/distil-memory/scripts/funnel.py | 10 | ALICE |
| [1/4] | ⚪ Low | `SKILL.md` documents only the `StaleParserError` → exit 1 path; it does not mention the two new non-zero exit paths task 10 introduced | skills/distil-memory/SKILL.md | 10 | ALICE |
| [1/4] | ⚪ Low | `_write_report` names files with second-resolution UTC timestamps and calls `write_text` unconditionally, so two runs inside the same second would silently overwrite each other's report | skills/distil-memory/scripts/funnel.py | general | BLAKE |

No finding contradicted the cycle's mechanical-facts block, so nothing was discarded on that ground.

## Cycle-1 rework verification

All 13 findings routed into cycle-1 rework tasks 10-14 were checked against the code at HEAD and are resolved. Alice verified all 13 independently; the orchestrator re-verified the four load-bearing ones directly:

- **Report anchoring.** `_report_dir()` walks `(cwd, *cwd.parents)` for a `.git` entry. Verified on disk: `skills/distil-memory/scripts/dev/` no longer exists, and `dev/local/audit-results/distil-memory-20260830T012747Z.md` is at the repo root.
- **Single parser resolution.** `main()` calls `corpus.resolve_parser()` exactly once, inside the `try/except corpus.StaleParserError`, and threads the result into `select_transcripts(..., resolved=(module, resolved_version))`.
- **Model-call and persistence failures.** `_run_triage()` catches `(RuntimeError, OSError, subprocess.TimeoutExpired)` and returns `(None, message)`; `main()` prints the report first, then the error to stderr, then guards `_write_report` with `except OSError` and returns 1. No bare `except`.
- **Counting contract and streaming.** `_raw_marker_hits` uses one `search` per text block; `scan()` iterates `_iter_entries(path)` directly with no `list(...)`.

## Gate decisions

### Verified before routing

- **Bob's 🟠 High is mechanically correct.** `subprocess.TimeoutExpired.__str__` renders `Command '%s' timed out after %s seconds` with `self.cmd` — the whole argv. Reproduced on this machine's Python 3.14.6: a prompt containing `SECRET_SLICE_TEXT_FROM_TRANSCRIPT` appears verbatim in `str(exc)`. The other two branches `_run_triage` catches do not leak: `RuntimeError(proc.stderr)` carries only the CLI's own stderr, and `OSError` carries only the missing path.

### Severity reclassification (1)

- **BOB 🟠 → 🟡 "timeout message prints slice text to stderr."** The mechanism is confirmed, but the audience assumed by the "private" framing does not exist: distil-memory is an on-demand tool the solo maintainer runs over their own transcripts, the text goes to their own terminal, and it is not persisted — the yield report written to `dev/local/audit-results/` never carries it. There is no third party, no data loss and no wrong behavior; what remains is an error message that dumps a multi-KB payload back to its owner. That is a message-hygiene defect, i.e. 🟡 Medium. **It is still fixed this cycle** — it is the first item in the tail sweep below — so the reclassification changes which route repairs it, not whether it is repaired.

### Settled deferrals (3)

- **BLAKE 🟡 "PRD Exit Criteria names `scripts/test_funnel.py`, which no longer exists."** The split was mandated by cycle 1: the file was 799 lines against this repo's 800-line hard cap, one line from breaking it, and Alice raised that as a finding. The PRD's Structural Decomposition was written before that cap bound. Substance is intact — all 79 funnel tests pass across the three files — and editing a wip PRD's spec to match the code is the wrong direction. Recorded so the divergence is visible in the PRD's completion record rather than silently absorbed.
- **BLAKE 🟡 "`assert_contract(version)` export line vs the two-argument signature."** The PRD's own Behavior prose for this feature requires the extra parameter ("The check also asserts the imported parser exposes what this skill calls, so a rename in the other repo surfaces as a named failure"), and the design doc signed `assert_contract(version, parser_module, minimum=_MIN_VERSION)` verbatim. The terse Module Exports line is a summary of the same feature, not a competing contract. Giving `parser_module` a default would let the function silently re-resolve the parser, which is exactly the double-resolution defect cycle 1 fixed.
- **ALICE 🟡 "`test_funnel_report.py` is 655 lines."** Under the 800 hard cap. Cycle 1 already carried this forward knowingly after splitting a 799-line file into three. The file is one coherent surface (every `main()` and `render_yield` test); a third split would fragment it to satisfy a soft target, and the churn is not worth it.

### Discarded (1)

- **BLAKE ⚪ "`_write_report` same-second overwrite."** Speculative. This is an on-demand tool whose runs take seconds to minutes (the recorded real run read 122 transcripts), so two completed runs landing inside one UTC second is not a reachable state. Blake himself rates the likelihood low. Adding a uniquifier is error handling for a scenario that cannot occur.

### Routed to the tail sweep (7 findings → 1 task)

The cycle converged on the severity bar (no unresolved Critical or High), so the remaining actionable Medium/Low findings are swept in one `[D2]` task rather than opening another review cycle:

1. Sanitize the `TimeoutExpired` message so slice text never reaches stderr (BOB, reclassified 🟡)
2. Extract a per-entry helper so `scan()` stops wrapping each entry in a singleton list (ALICE 🟡)
3. `SKILL.md`: document per-text-block counting and the `survivors: n/a`-after-failure path (BOB 🟡)
4. Make the streaming test bind to bounded-memory intent, not to `__length_hint__` (BOB 🟡)
5. Parametrize the three duplicated model-failure tests (BOB 🟡)
6. `main()` docstring: state the non-zero exit paths (ALICE ⚪)
7. `SKILL.md`: document the two new non-zero exit paths (ALICE ⚪) — merged with item 3, same file

Seven findings is under the scope alarm's threshold of 10 and under the sweep's split rule, so one task carries them all.

## Alice

Consensus lens, implementation-aware. Verified all 13 prior findings against the code at HEAD and ran both suites herself: `skills/distil-memory/scripts` 106 passed, whole repo 547 passed / 5 skipped (identifying the 5 as the pre-existing `skills/survey` `tree_sitter_language_pack` skips). She reported no settled decision contradicted by current code.

- 🟡 `test_funnel_report.py` is 655 lines — outside task 14's own 200-400 target for the split files. | File: skills/distil-memory/scripts/test_funnel_report.py | Task: 14
- 🟡 `scan()` wraps each `(line_no, entry)` pair in a fresh one-element list per iteration to call helpers written for lists. | File: skills/distil-memory/scripts/funnel.py | Task: 13
- ⚪ `main()`'s docstring still says "Returns 0 on success" with no mention of the new non-zero paths. | File: skills/distil-memory/scripts/funnel.py | Task: 10
- ⚪ `SKILL.md` documents only the `StaleParserError` → exit 1 path, not the two new non-zero exits. | File: skills/distil-memory/SKILL.md | Task: 10

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

Blind lens — PRD only, no diff, no file list, no design doc, no review history. Located the code himself, ran `test_corpus.py` (27) and the three `test_funnel_*.py` (79), ran the create-skill validator, and inspected the produced dry-run report. He found no Critical or High, and explicitly confirmed no scope creep (flags match the spec exactly), no new external dependencies, and none of slices 00008/00009 leaking in.

- 🟡 Phase 1's literal Exit Criteria command fails: the PRD names `scripts/test_funnel.py`, which no longer exists. | File: skills/distil-memory/scripts/test_funnel.py | Task: Phase 1 — **settled deferral, see Gate decisions**
- 🟡 `assert_contract(version)` export line does not match the two-argument signature. | File: skills/distil-memory/scripts/corpus.py | Task: Phase 0 — **settled deferral, see Gate decisions**
- ⚪ `_write_report` same-second overwrite. | File: skills/distil-memory/scripts/funnel.py | Task: general — **discarded, see Gate decisions**

B1: pass
B2: pass
B3: fail
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

`consolidate_findings.py` was run with `--ledger --ledger-dismiss BLAKE`; no Blake finding matched a settled ledger entry, so nothing was auto-dismissed. B3's fail is the `assert_contract` signature finding above.

## Bob

Doubt + de-slop lens, codex, cycle-1 thread resumed. Static analysis only (sandbox). He raised the cycle's only High and three Mediums, and produced complete FIX/VERIFY/KNOWN buckets with all five doubt-rubric verdicts passing.

- 🟠 `_run_triage()` converts `TimeoutExpired` to `str(exc)`, whose `exc.cmd` carries the full transcript-derived prompt. | File: skills/distil-memory/scripts/funnel.py:236 | Task: 10 — **reclassified 🟡, fixed in the tail sweep**
- 🟡 `SKILL.md` still documents `n/a` only for dry runs and says every raw marker hit is counted. | File: skills/distil-memory/SKILL.md:57 | Task: general
- 🟡 The streaming test detects only `list(iterator)` through `__length_hint__`. | File: skills/distil-memory/scripts/test_funnel_extraction.py:355 | Task: 13
- 🟡 The three 40-line model-failure tests repeat nearly identical setup; a fixture plus parametrization would be simpler. | File: skills/distil-memory/scripts/test_funnel_report.py:300 | Task: 10

### Doubt-lens buckets

```
FIX:
- Timeout errors disclose transcript text — funnel.py:236 — catch subprocess.TimeoutExpired separately and emit a sanitized message containing only the timeout duration; test that the slice text and command are absent from stderr.
- Public documentation is stale after rework — SKILL.md:57 — document per-text-block counting and that model-call failure also renders survivors: n/a, writes the known counts, reports stderr, and exits non-zero.
- Streaming test has materialization false negatives — test_funnel_extraction.py:355 — replace the __length_hint__ mechanism with an iterator that verifies the first entry is processed before the second is yielded.
- Failure-path tests duplicate setup — test_funnel_report.py:300 — extract the common transcript/parser setup into a fixture and parametrize RuntimeError, missing-binary, and timeout outcomes.
VERIFY:
- (none)
KNOWN:
- (none)
```

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

Bob's R1/R2 fails correspond to his two test-quality findings (the `__length_hint__` streaming test and the duplicated failure-path tests); both are in the tail sweep. Alice and Carl, who executed the suites, both pass R1 and R2.

## Carl

Gemini via the copilot backend, generalist on this diff (no frontend surface). He read the diff and the context file, ran `uv run pytest` himself, checked file and function sizes against the mechanical-facts block, and confirmed a clean working tree.

- [CARL] ✅ No issues found

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

## Follow-up Tasks Created

1. [D2] Tail sweep: sanitize the timeout message, simplify `scan()`, refresh SKILL.md, and strengthen two tests (M) - 🟡/⚪ - addresses the 7 swept findings above

Verdict: 11 findings
Tests: 547 passed, 0 failed, 5 skipped
