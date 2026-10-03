---
prd: dev/local/prds/wip/00010-qwen38-multifile-capability-eval-v1.md
review: 1
date: 2026-09-04
head_sha: 75caf7172ed46f8d267f96157bce121815a5ff48
reviewers: alice,blake,bob,eve
agents:
  alice: available
  blake: available
  bob: available
  carl: unavailable
  eve: available
---

# Review: 00010-qwen38-multifile-capability-eval-v1

Diff range: `e87f23d9fbd8add517dbdc2b5f06fa26255f525e..75caf7172ed46f8d267f96157bce121815a5ff48`

codex_rung_guard: fired (2 codex-implemented task(s))

Context pack: unavailable. `engram pack` failed because this repository is not
registered in the configured gita registry; the failure is non-fatal.

## Review Summary

Reviewed: 13 completed tasks
PRDs checked: 00010-qwen38-multifile-capability-eval-v1.md

### Agent Status

- Alice (consensus, Claude): available
- Blake (blind, PRD-only): available
- Bob (doubt + de-slop): available through the required Claude fallback because nested Codex dispatch exited 3
- Carl (Gemini): unavailable after the required retry because nested CLI dispatch exited 3
- Eve (non-Codex doubt voice): available; activated by the Codex rung guard

Consensus engine: `legacy`. `consolidate_findings.py` produced 22 rows but did
not merge several identical defects because reviewers cited live and bundled
copies of the same artifact. The adjudicated table below merges those semantic
duplicates, retains the highest severity, and records two contract-based
refutations explicitly.

## Conclusion

The review does not validate the published 4/6 Qwen versus 6/6 Sonnet
comparison. At least tasks 4 and 6 were narrowed while same-task behavioral
files remained at post-task state; several scored retries lack a baseline from
their own dispatch tree; and the mandatory `git log -L` evidence is absent.
The multi-file experiment is therefore not decision-grade and PRD 00010 cannot
be marked complete on this cycle.

Operationally, the safe decision is unchanged but its basis is narrower:
Qwen3.8 remains qualified for guarded single-file implementation attempts, not
as a wholesale Sonnet replacement. Sonnet remains the one-shot fallback and
review authority. A separate claude-autopilot PRD now specifies enforcement of
that boundary while this evaluation is repaired or rerun.

## Consolidated Findings

| Consensus | Severity | Issue | File | Disposition |
|---|---|---|---|---|
| [4/4] | 🔴 Critical | Scored retries reuse another attempt/tree's baseline; task 4's baseline also ran in its dispatch tree. | `dev/local/tmp/00010-multifile-eval/evidence.md` | Rework task 15 |
| [4/4] | 🔴 Critical | Tasks 4 and 6 retain same-task behavioral code/tests at post-task state and therefore evaluate partially pre-solved subsets. | task 4/6 vetting artifacts | Rework task 14 |
| [2/4] | 🔴 Critical | Selected-task vetting records path-level history but not the PRD-mandated `git log -L` evidence for later-touched files. | `dev/local/tmp/00010-multifile-eval/tasks/` | Rework task 14 |
| [2/4] | 🟠 High | Task 5 scores three Required files without a correctness-observing gate, so a non-empty but wrong edit can still PASS. | task 5 vetting artifact | Rework task 14 |
| [1/4] | 🟠 High | Qwen task 2's effective run used 60 minutes while Sonnet used 40, so the reported comparison was not uniformly bounded. | report, Phase 2 | Rework task 15 |
| [1/4] | 🟠 High | The runbook's failing-baseline rule does not prove each target path exactly matches its recorded pre-task snapshot. | `skills/use-qwen/references/eval-runbook.md:61` | Rework task 16 |
| [1/4] | 🟠 High | The runbook uses one `<commit>` placeholder where multi-commit tasks require distinct first/last commits. | `skills/use-qwen/references/eval-runbook.md:71` | Rework task 16 |
| [1/4] | 🟡 Medium | C7 does not support flagging Qwen's real 1203-pass run as false merely because the separate canonical gate later failed. | task 4 Qwen audit | Rework task 17 |
| [2/4] | 🟡 Medium | Candidate/setup/task-5 bundle text contains stale, mutually contradictory eligibility and alternate statuses. | preserved bundle | Rework task 17 |
| [1/4] | 🟡 Medium | Task 2 Qwen baseline is reported as exit 1 while its `.rc` artifact records exit 2. | bundled evidence line 452 | Rework task 17 |
| [1/4] | 🟡 Medium | The report names nonexistent `*.prompt.md` artifacts instead of `*.prompt.txt`. | report line 18 | Rework task 17 |
| [1/4] | 🟡 Medium | Candidate category counts total eight while the prose says seven. | candidates line 14 | Rework task 17 |
| [2/4] | 🟡 Medium | Published guidance says “1 dropped-a-file failures.” | qwen integration line 134 | Rework task 17 |
| [1/4] | 🟡 Medium | The combined evidence log exceeds the 800-line review rubric although the PRD permits two logs. | bundled evidence | Rework task 17 |
| [1/4] | 🟡 Medium | claude-autopilot still admits two- and three-file Qwen tasks. | external plugin | Settled by follow-up PRD 00174; not current-repo rework |

### Refuted findings

- Sonnet's four `unverifiable` rows are allowed explicitly by design C7 for
  final-message-only claims that neither the external gate nor snapshot can
  confirm or contradict. They do not make the false-claim audit noncompliant.
- Keeping task 5's `app_contract/mod.rs` at current state is explicitly allowed
  by C2's measured R2 exception for that visibility-only edit. The separate
  concern about three gate-invisible Required files remains valid above.

## Follow-up Tasks Created

1. Task 14 — re-vet or replace contaminated candidates.
2. Task 15 — rerun affected engines with attempt-local baselines and a uniform bound.
3. Task 16 — harden the eval-runbook pre-task-state and multi-commit recipes.
4. Task 17 — reconcile audit, report, and preserved bundle after valid reruns.

The external routing follow-up is
`claude-autopilot/dev/local/prds/backlog/00174-align-qwen-routing-with-single-file-trust-v1.md`.

## Alice

[ALICE] 🔴 Effective retries `1-qwen-a2`, `1-sonnet-a3`, and `2-qwen-a4` reuse attempt 1’s baseline evidence; no retry-specific baseline exists, so their fresh trees were not gate-checked before dispatch as the new checklist and C5 require. Task 4 also ran its baseline inside the dispatch tree. | File: dev/local/audit-results/qwen38-vs-sonnet-multifile-2026-09-03-bundle/evidence.md | Task: 5-8
[ALICE] 🔴 Tasks 4 and 6 demote real task changes to Ancillary (`pipeline.py`/`test_pipeline.py` and `indexer/tests/mod.rs`) and leave them at post-task HEAD while excluding them from the gate. C2 explicitly disqualifies real code or test changes the gate does not need, so these are partially pre-solved trees rather than two eligible, isolated original tasks. | File: N/A | Task: 3
[ALICE] 🟡 The sole Qwen false-claim flag is unsupported by C7: the session JSONL confirms the reported 1203-pass command actually ran and passed; the canonical gate disproves overall completion, not that execution claim. This incorrectly records `<f> = 1` in the report and public scope prose, although the final scope outcome remains unchanged. | File: dev/local/audit-results/qwen38-vs-sonnet-multifile-2026-09-03-bundle/runs/4-qwen-a1.audit.md | Task: 11-13
[ALICE] 🟡 The selected slot-5 vetting artifact still identifies itself as “Alternate 1,” says it returned to reserve, and names `alt1-*` canonical copies, contradicting the manifest and report that promoted it to task 5. | File: dev/local/audit-results/qwen38-vs-sonnet-multifile-2026-09-03-bundle/tasks/5-surface-reindex-skip-warnings.vetting.md | Task: 3
[ALICE] 🟡 `evidence.md` is 1,668 lines, exceeding the 800-line file limit; the PRD permits two evidence logs, so it can be split by engine without losing preserved output. | File: dev/local/audit-results/qwen38-vs-sonnet-multifile-2026-09-03-bundle/evidence.md | Task: general

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
R13: fail

## Blake

[BLAKE] 🔴 Tasks 4, 5, and 6 were not dispatched from genuine whole-task pre-task state: task 4 leaves `pipeline.py` and `test_pipeline.py` fixed, task 5 leaves task-touched `app_contract/mod.rs` fixed and admits three Required files its gate cannot observe, and task 6 leaves `indexer/tests/mod.rs` fixed. This violates the all-touched-files revert and correlated-real-gate eligibility requirements, invalidating the published six-task comparison. | File: dev/local/tmp/00010-multifile-eval/evidence.md | Task: Phase 1/2
[BLAKE] 🔴 Fresh retry trees were not baseline-gated before re-dispatch: task 1 qwen a2 and Sonnet a3 reuse a1 baseline evidence, while task 2 qwen a4 reuses a1 evidence after interruption and two timeouts. This contradicts the new checklist's requirement to run the failing gate in every dispatch tree before trusting a re-dispatch. | File: dev/local/tmp/00010-multifile-eval/evidence.md | Task: Phase 2
[BLAKE] 🟠 None of the selected-task vetting notes records the mandated `git log --oneline -L` check; they use path-level `git log --name-only`/`--no-patch` and prose inspection instead. | File: dev/local/tmp/00010-multifile-eval/candidates.md | Task: Phase 1
[BLAKE] 🟠 Qwen task 2 is scored from a fourth launch under a raised 60-minute bound after two real 40-minute timeouts, while Sonnet's effective run used the original 40-minute bound; the published `4/6` versus `6/6` comparison therefore was not run under identical conditions. | File: dev/local/audit-results/qwen38-vs-sonnet-multifile-2026-09-03.md | Task: Phase 2
[BLAKE] 🟠 Four valid Sonnet transcripts are marked `unverifiable`, although acceptance requires every transcript to be marked clean or flagged after checking its claims against evidence; the reported zero Sonnet false claims is therefore not fully verified. | File: dev/local/tmp/00010-multifile-eval/audit.md | Task: Phase 2

B1: pass
B2: fail
B3: fail
B4: pass
B5: pass
B6: pass
B7: pass
B8: fail
B9: fail
B10: pass
B11: pass
B12: fail
B13: fail
B14: pass
B15: pass
B16: pass
B17: pass
B18: fail
B19: pass

## Bob

[BOB] 🟠 Valid retries were scored using earlier attempts’ baseline results; task 1 qwen a2/Sonnet a3 and task 2 qwen a4 reuse a1 baselines, violating the new rule to gate every dispatch tree before dispatch | File: dev/local/audit-results/qwen38-vs-sonnet-multifile-2026-09-03-bundle/evidence.md:228 | Task: general
[BOB] 🟠 Tasks 4 and 6 leave same-task behavioral files at post-task state as “Ancillary”; task 6 explicitly leaves answer-revealing indexer tests in the tree, so these are not genuine clean pre-task evaluations | File: dev/local/audit-results/qwen38-vs-sonnet-multifile-2026-09-03-bundle/tasks/6-cap-frontmatter-size.vetting.md:62 | Task: 3
[BOB] 🟠 Task 5 declares three Required files gate-invisible and scores them only for non-empty edits; incorrect edits can therefore receive PASS, so Sonnet’s 6/6 and task-5 eligibility are not established by a real gate | File: dev/local/audit-results/qwen38-vs-sonnet-multifile-2026-09-03-bundle/tasks/5-surface-reindex-skip-warnings.vetting.md:184 | Task: 3
[BOB] 🟡 The preserved bundle contradicts its final report: candidates says all seven prospects remain eligible, setup files mark tasks 3/4/6 disqualified and the alternate unusable, and task 5’s vetting still calls it an alternate | File: dev/local/audit-results/qwen38-vs-sonnet-multifile-2026-09-03-bundle/candidates.md:36 | Task: 12
[BOB] 🟡 Task 2’s qwen baseline is logged as exit 1 in evidence while the preserved `2-qwen-a1.baseline.rc` records exit 2, violating the exact-evidence requirement | File: dev/local/audit-results/qwen38-vs-sonnet-multifile-2026-09-03-bundle/evidence.md:452 | Task: 6
[BOB] ⚪ The newly published scope paragraph says “1 dropped-a-file failures”; singularize the noun | File: docs/plugin-skills/work/references/qwen-integration.md:134 | Task: 13

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

## Eve

[EVE] 🔴 Selected tasks were narrowed while original task-touched files stayed post-task, so task 4’s prompt names `pipeline.py` but neither reverts nor scores it | File: dev/local/tmp/00010-multifile-eval/tasks/4-record-raw-source-sha.vetting.md:73 | Task: Phase 1 candidate vetting
[EVE] 🔴 Later-touched files were vetted with path-level logs and prose inspection, not the mandated `git log -L` evidence | File: dev/local/tmp/00010-multifile-eval/tasks/1-repoint-bim-doc-callers.vetting.md:60 | Task: Phase 1 history vetting
[EVE] 🔴 Several scored effective attempts reuse baseline evidence from another tree instead of checking the actual dispatch tree immediately before re-dispatch | File: dev/local/tmp/00010-multifile-eval/evidence.md:228 | Task: Phase 2 comparative dispatch
[EVE] 🟠 The new checklist treats a failing gate as proof that every target file is at genuine pre-task state, which does not detect partial contamination | File: skills/use-qwen/references/eval-runbook.md:61 | Task: Phase 0 isolation safety
[EVE] 🟠 The new revert recipe uses one `<commit>` as both task end and task start, so it cannot correctly restore multi-commit tasks | File: skills/use-qwen/references/eval-runbook.md:71 | Task: Phase 0 isolation safety
[EVE] 🟠 Four valid Sonnet transcripts remain `unverifiable`, despite the acceptance requirement that each transcript be resolved clean or flagged | File: dev/local/tmp/00010-multifile-eval/audit.md:38 | Task: Phase 2 false-claim audit
[EVE] 🟡 The report points to nonexistent `*.prompt.md` files; prompts are `*.prompt.txt` | File: dev/local/audit-results/qwen38-vs-sonnet-multifile-2026-09-03.md:18 | Task: Phase 3 report
[EVE] 🟡 Published guidance has a singular/plural defect: “1 dropped-a-file failures” | File: docs/plugin-skills/work/references/qwen-integration.md:134 | Task: Phase 3 scope documentation
[EVE] 🟡 The candidate inventory says seven prospects but its category counts total eight | File: dev/local/tmp/00010-multifile-eval/candidates.md:14 | Task: Phase 1 candidate survey
[EVE] 🟡 Measured single-file scope remains unenforced because autopilot still routes two- and three-file tasks to Qwen | File: skills/use-qwen/SKILL.md:69 | Task: Deferred classifier alignment

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

Verdict: 15 findings
Tests: 969 passed, 1 failed, 5 skipped (reused from last-verification.json at 75caf7172ed46f8d267f96157bce121815a5ff48; sole failure is an unrelated live-memory YAML file outside this PRD)
