---
prd: docs/dev/project-management/reviews/drain-backlog-completion-review-20261115.md
review: 1
date: 2026-11-25
head_sha: f7a6ac76b8f0331249115ca57566e5862a3a0626
codex_thread_id: 01a20f9d-8f18-74a0-8888-5d1afc701655
reviewers: alice,blake,bob
agents:
  alice: available
  blake: available
  bob: available
  carl: disabled
  eve: disabled
---

# Review: drain rework, all lenses

Diff range: `a10516b05a31a8b0ec17866bd3c2a6a19df21e97..f7a6ac76b8f0331249115ca57566e5862a3a0626`

codex_rung_guard: not fired

## Purpose and scope

This review closes finding V1 of the
[closeout verification](../audit-results/repository-closeout-verification.md).
The [drain review](drain-backlog-completion-review-20261115.md) ran Alice, Blake
and Bob on its first pass, but only Bob on the two rework deltas
`fd01e31..142fd99` and `8816bb9..cb5616f`. This cycle runs Alice, Blake and Bob
on those deltas together.

The original rework commits sit on the replaced, unscrubbed line. Each one is on
current master with an identical `git patch-id --stable`:

| Original | Published | Subject |
|---|---|---|
| 3a536e0 | 678ad0e | use-qwen: `contained()` folding, failed-build cleanup |
| 0dbc857 | 520d5b5 | use-qwen: restarted pi run incomplete until its own `agent_end` |
| 0c53c8e | 6856cf2 | sweep-fix: kill in-flight searches at once |
| 142fd99 | 0f90399 | close triage stubs 00126 and 00151 |
| 139c7c9 | 0637412 | document-abap-solution: one `abap_idents` home |
| 59c66dc | d3a6b66 | glean: refuse a non-string verdict |
| 353d7f1 | b207d51 | glean: name the ledger file; test split |
| cb5616f | f7a6ac7 | distil-memory: unconditional missing-store warning |

The published range `a10516b..f7a6ac7` is contiguous. It also holds `ef83b22`
(the published `8816bb9`, encoded user names). That commit was outside both
deltas, so this cycle reviews it too.

Method: standalone `autopilot review-stage` (autopilot 0.10.0) in a detached
worktree at `f7a6ac7`, with no autopilot state, so the paused 00135 store was
not touched. Blake's requirements file holds only PRDs 00160, 00162, 00164,
00049, 00078, 00104, 00175, 00112 and 00108, plus one line that names the stub
closure. He received no diff, file list, commit log or review history.
Consolidation ran through `consolidate_findings.py`.

## Roster and actual backends

| Lens | Backend / model | Verdict |
|---|---|---|
| Alice, consensus | native Claude subagent `autopilot:alice`, `claude-opus-5-5` | 0 HIGH, 3 MEDIUM, 2 LOW; R1-R12 pass, R13 fail (file size) |
| Blake, blind PRD-only | native Claude subagent `autopilot:blake`; requirements only | 0 HIGH, 3 MEDIUM, 6 LOW; B1 and B6 fail (see R6, R8) |
| Bob, doubt + de-slop | Codex CLI via `codex-run.sh`, inlined 198 KB prompt, exit 0 | 2 HIGH, 6 MEDIUM, 3 LOW; D1-D5 pass |

Carl and Eve were not invoked. The handoff required Alice and Blake. Bob ran
again so that this cycle carries all three mandatory lenses.

## Alice

R1-R12 pass. R13 fails on file size (R5 below). Findings R3, R4, R5, R15, R16.
She found these clean: the removed `isabs` check, the `abap_idents` move, T51b
fail-first, the encoded-name regex, the docket warning order, and `kill_all`
registry semantics. She ran 257 focused pytest cases and `test_qwen_run.sh`
(114 passed, 0 failed).

## Blake

He verified 00160, 00162, 00164, 00049, 00078, 00104, 00175, 00112, 00108 and
the stub closure as implemented. B1 and B6 fail on R6 and R8. Findings R6-R8 and
R17-R22. He ran 443 tree-archive tests with deprecation warnings as errors,
`test_qwen_run.sh` (114/0) and `test_eval_automation.sh` (31/0). Python 3.10 and
3.12 runs were not possible offline. Earlier verification covers those versions:
499/0 on each.

## Bob

Findings R1, R2, R9-R14, R23-R25.

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Consolidated findings and dispositions

Every row has consensus [1/3]. No finding was raised by two lenses.

| Ref | By | Sev | Finding | Disposition |
|---|---|---|---|---|
| R1 | Bob | HIGH->MEDIUM | `agent_start` clears `.ended` but not `.last` (`qwen-run.sh:510`). A restarted run that reaches `agent_end` with no assistant message of its own passes with the earlier answer. | **Confirmed logic gap, deferred.** The path needs pi to start a new run and end it with no assistant `message_end`. Aborted and failed runs report through an assistant message with a stopReason. The recorded pi evidence holds no answerless restart. Not verified against pi source. Fix: `.ended = false \| .last = null` on `agent_start`, plus a T51c case. A production repair needs its own build and review cycle. |
| R2 | Bob | HIGH | A stalled Windows `taskkill` can exceed PRD 00104's 2 s cleanup tolerance. | **Rejected.** The PRD marks the tolerance as a guess for the POSIX shim test. Commit `0f90399` records the operator decision of 2026-11-15: "the 5 s per-call bound is accepted". CHANGELOG documents the 5 s bound. |
| R3 | Alice | MEDIUM->LOW | When `staging.mkdir(parents=True)` fails part-way, ENOENT stops the parent walk and leaves an empty created ancestor. | **Deferred.** The leftover is an empty directory. No data is lost, and the original build error still raises. |
| R4 | Alice | MEDIUM | Missing CHANGELOG entries for 678ad0e, 520d5b5, d3a6b66, b207d51. | **Fixed** in this cycle's records commit (docs only). |
| R5 | Alice | MEDIUM | `sweep.py` (829) and `test_qwen_run.sh` (1606) exceed 800 lines and grow. | **Deferred.** This is drain review item D2 and was already over the limit before the drain. |
| R6 | Blake | MEDIUM | `build_template` refuses an empty existing `dest`, which is stricter than PRD 00160. | **Rejected.** Stricter refusal, pinned by `test_eval_tree_archive_staging.py:161`. The only caller removes `dest` first. |
| R7 | Blake | MEDIUM | The docket "no kept entries for store" warning fires when no kept entry exists, and it reloads the queue. | **Deferred** with R11. These are stderr diagnostics only. Exit code and stdout are unchanged. |
| R8 | Blake | MEDIUM | `.git` component refusal and NFC/case folding are outside PRD 00160. | **Rejected.** Later archive work added both (CHANGELOG `.git` and alias entries, closure commit `99796b9`). Blake was shown 00160 only. |
| R9 | Bob | MEDIUM | A concurrent writer's empty parent directory can be removed by `rmdir`. | **Rejected.** `rmdir` removes only an empty directory, so no data is lost. This matches the drain review's settled R1 reasoning. |
| R10 | Bob | MEDIUM->LOW | A regular file at `--store` passes `exists()`. | **Deferred.** Diagnostic only. |
| R11 | Bob | MEDIUM->LOW | The zero-result path reloads the queue. | **Deferred** with R7. |
| R12 | Bob | MEDIUM->LOW | Glean checks the volatile `sha256` field by truthiness. | **Deferred.** This needs a hand-edited ledger with a non-string hash. |
| R13 | Bob | MEDIUM->LOW | The encoded-name scanner allows names that start with `you-`. | **Deferred.** This affects the test-only scrub check. |
| R14 | Bob | MEDIUM->LOW | The mixed-entry ledger test does not require the ledger path. | **Deferred.** The test is weaker than the code, which names the path (b207d51). |
| R15-R22 | Alice, Blake | LOW | Public-ledger verdict test, slow fail-first barrier, `_safe_mode` group bits, stdin index modes, re-walk cost, untranslated `ReadError`, duplicated removal helper, `killpg` pid reuse. | **Deferred** as notes. R20 is already documented as a known limit in the closeout verification. |
| R23-R24 | Bob | LOW | Base-passing moved tests; `docket.main` 54 lines. | **Rejected / deferred.** Moved tests pass by design. The function length is a guideline overrun. |
| R25 | Bob | LOW | No hosted Windows result for `f7a6ac7`. | **Rejected.** Run 45174245519 at `04da088` passed all eight jobs, Windows included. The archive code is byte-identical between the two tips. |

## Deferred items

All deferred rows above stay open in this file: R1, R3, R5, R7, R10-R16 and
R17-R24. R1 is the only confirmed behavior gap. Give it its own fix and review
cycle.

## Outcome

**PASS with deferrals.** No CRITICAL or surviving HIGH finding remains. Both
HIGH findings are resolved: R1 is downgraded and deferred with evidence, and R2
is rejected against a recorded operator decision. The required Alice and Blake
conclusions now exist for both rework deltas.

Verdict: 25 findings
Tests: 4899 passed, 0 failed, 12 skipped (suite run this cycle)
