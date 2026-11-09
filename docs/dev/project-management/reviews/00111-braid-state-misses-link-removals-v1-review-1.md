---
prd: docs/dev/project-management/prds/wip/00111-braid-state-misses-link-removals-v1.md
review: 1
date: 2026-10-29
head_sha: 1bb1d6b73c861cbe849987af410c00ab7e7525e2
codex_thread_id: 01a1872b-16a8-7ec2-9378-44e909abcec7
reviewers: alice,blake,bob
agents:
  alice: available
  blake: available
  bob: available
  carl: unavailable
dispatch_rows:
  bob: 7025099b
  carl: 12b19b33
---

# Review: 00111-braid-state-misses-link-removals-v1

Diff range: `6091e02c41e823f3bd061434edf8bd389ffea8d0..1bb1d6b73c861cbe849987af410c00ab7e7525e2`

codex_rung_guard: not fired

pack: ok

## Review Summary

Reviewed: 1 completed task
PRDs checked: 00111-braid-state-misses-link-removals-v1.md

### Agent Status

- Alice: ✅ Available (consensus lens, legacy engine)
- Blake: ✅ Available (blind lens, PRD-only)
- Bob: ✅ Available (doubt lens, codex; D1-D5 emitted)
- Carl: ⚠️ Unavailable: gemini-run backend=copilot model=gemini-3.8-flash exited 1, "You have exceeded your monthly quota". Retried once per retry policy, same failure. Not a configuration rejection (exit 1, not exit 4), so no batch latch was recorded.
- Eve: ⏸️ Disabled: resolved doubt reviewer is `codex` and no task was implemented by codex, so the codex doubt-roster guard did not fire.

Mechanical checks: tautological-shape scan found no `[MECH]` lines across 46 test
functions in 2 files. The fail-first replay collected 0 touched tests (both test
files could not be collected against the base commit), so it produced no
evidence either way; that gap is raised as R12 below.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [1/3] | 🟠 | Removals are persisted only once per stage (after each whole `_sync_links` call returns), not "each successful removal before a later operation that can refuse". If a stage removes link A and then refuses changed path B in the same call, the BraidError discards the stage's `managed` dict and nothing is saved. Reproduced in a temp dir with two managed union skills `aa` and `bb`, both sources deleted and `bb` replaced by a real directory: sync printed `REMOVE .../skills/aa`, then `refusing to clean changed managed path: .../skills/bb`; the link `aa` is gone but `.braid-state.json` still lists `['aa', 'bb']`, which is the original defect. The same applies to the claude and kiro host stages. Only the cross-stage case (union removal, then a later host refusal) is fixed. | src/agent_skills_braid/cli.py:532 | Phase 0 | BLAKE |
| R2 | [1/3] | 🟡 | Call sites 2 and 3 of the new persistence are untested. No test shows the Claude-stage persist surviving a later Kiro-stage refusal, or that the Kiro registration and links are saved before `sync_kiro_agent` can refuse. No test checks that `written_state` stays put when `_write_state` fails mid-run. Only the union-then-Claude-refusal path and the unchanged-skip path are pinned. | tests/test_braid_check.py:1257 | 1 | ALICE |
| R3 | [1/3] | 🟡 | `assert "kept" not in state["union"]` cannot fail. The comment itself says no skill of that name was ever recorded, so it adds no signal and looks like a real check. Drop it, or assert something that binds to intent, such as `state["hosts"]["claude"]` still recording `temporary` so the changed host path stays protected. | tests/test_braid_check.py:1275 | 1 | ALICE |
| R4 | [1/3] | 🟡 | The implementation departs from the design contract. The design allows a `persist()` closure inside `run()` and no new module. The diff adds `src/agent_skills_braid/_run_stages.py` with stage helpers taking 8 to 12 positional parameters. `run()` now imports them locally to dodge a circular import, because the new module imports `_sync_links`, `_write_state`, `Mode` and `State` from `cli`. Behavior matches the design, but the split adds coupling, and the names are bound at import time, so a future `monkeypatch.setattr(cli, "_write_state", ...)` would silently miss `persist`. | src/agent_skills_braid/_run_stages.py:1013 | 1 | ALICE |
| R5 | [1/3] | 🟡 | No test covers a removal followed by a refusal inside one stage, so the R1 gap is untested. The partial-removal regression exercises only the union-then-claude ordering. | tests/test_braid_check.py:246 | Phase 0 | BLAKE |
| R6 | [1/3] | 🟡 | The "no state-write attempt for unchanged content" requirement is checked only through a POSIX `chmod 0o500` fixture, skipped on Windows. The PRD asked for portable fixtures instead. The test never spies on `_write_state`. It would pass vacuously if the suite ran as root, and it cannot prove that no write was attempted. | tests/test_braid_check.py:272 | Phase 0 | BLAKE |
| R7 | [1/3] | 🟡 | Explicit coverage is thin for state-only changes (only Kiro enrollment), first-run initialization (no dedicated test), and check/dry-run read-only controls (the new tests add none). The persistence-failure test existed before this change. | tests/test_braid_check.py:246 | Phase 0 | BLAKE |
| R8 | [1/3] | 🟡 | Empty first-run initialization can be skipped: with an empty inventory and host projection disabled, every candidate equals the loaded empty state, so no state file is created. Track whether the state file existed and force its initial write in sync mode. | src/agent_skills_braid/_run_stages.py:26 | 1 | BOB |
| R9 | [1/3] | 🟡 | Both host helpers annotate `hosts` as `dict[str, str]`, but assign link dictionaries and pass it into `State`. Change both annotations to `dict[str, dict[str, str]]`. | src/agent_skills_braid/_run_stages.py:64 | 1 | BOB |
| R10 | [1/3] | 🟡 | The partial-removal regression never seeds unaffected ownership; asserting that never-created `"kept"` is absent cannot detect accidentally discarding unrelated records. Seed a retained skill and assert its union/host ownership survives, including the refused Claude entry. | tests/test_braid_check.py:245 | 1 | BOB |
| R11 | [1/3] | 🟡 | The design still specifies a closure inside `run()` and changes confined to that function, while the implementation introduces a separate module. Update module placement and persistence ownership to describe the implemented extraction and its recorded style-limit rationale. | docs/dev/project-management/designs/00111-braid-state-misses-link-removals-v1-design.md:16 | 1 | BOB |
| R12 | [1/3] | 🟡 | Required fail-first evidence remains unresolved: replay collected zero tests. Run the two new partial-removal and read-only regressions against base `6091e02c41e8` with HEAD tests overlaid and project imports configured; confirm assertion/permission failures rather than collection errors. | tests/test_braid_check.py:245 | 1 | BOB |
| R13 | [1/3] | ⚪ | The added assertion `assert not (tmp_path / "backup").exists()` in `test_agent_edited_since_it_was_read_is_not_overwritten` is unrelated to `run()` persistence and was not asked for. It is harmless, but it is scope creep and passes against the old code. | tests/test_braid.py:599 | 1 | ALICE |
| R14 | [1/3] | ⚪ | `test_enrolling_kiro_without_any_new_links_is_still_recorded_as_a_real_change` passes against the pre-change code, because the old code always wrote state. It guards against regression only, which matches the design's "preserve" intent, so keep it. It does not satisfy fail-first. | tests/test_braid_check.py:1302 | 1 | ALICE |
| R15 | [1/3] | ⚪ | Kiro enrollment and registration are now persisted before `sync_kiro_agent` configures the agents. A failed or refused agent edit therefore leaves enrollment saved. Previously state was written only at the end. Probably benign because the next run re-detects the unconfigured agent, but it goes beyond the spec and is unrecorded. | src/agent_skills_braid/_run_stages.py:117 | Phase 0 | BLAKE |
| R16 | [1/3] | ⚪ | The test gate block shown to the reviewers carried no counts (full suite exit 1, no parsed summary), so the exit criterion could not be confirmed from it. A narrow run of `tests/test_braid.py` and `tests/test_braid_check.py` gives 61 passed. | N/A | general | BLAKE |
| R17 | [1/3] | ⚪ | The full-suite exit criterion appeared unmet in the staged results: 1 failed, 4132 passed, 9 skipped. The sweep deadline timing failure is outside this PRD's changed implementation; track it separately rather than reporting the suite as passing. | skills/sweep-fix/scripts/test_sweep_scan.py | general | BOB |

## Alice

Consensus lens, implementation-aware. Five findings, all 🟡 or ⚪ (R2, R3, R4,
R13, R14). Narrow run of `tests/test_braid.py tests/test_braid_check.py`: 61
passed. `cli.py` is 772 lines; every function is under the 50-line limit per the
mechanical-facts block.

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

Blind lens, PRD-only. One 🟠 (R1, reproduced in a temp dir), three 🟡 (R5, R6,
R7), two ⚪ (R15, R16).

Confirmed as met: the writer is atomic (`os.replace`) with a BraidError
diagnostic; the skip-identical-write logic in `make_persist` is gated on
`Mode.SYNC`, so check and dry-run stay read-only; the state format and
`STATE_VERSION` are unchanged; refusal for changed paths and the user-owned link
protections are unchanged; `_run_stages.py` is a refactor split, not a new
feature.

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
B15: pass
B16: pass
B17: pass
B18: pass
B19: pass

## Bob

Doubt lens (codex), rubric D1-D5 plus de-slop.

FIX: R8, R9, R10, R11 (all 🟡).
VERIFY: R12 — fail-first replay evidence unresolved. Not queued: the finding
names a procedure (overlay HEAD tests on a base worktree, configure project
imports), not one runnable command line, so it stays an ordinary finding per the
queue's command-shape rule.
KNOWN: R17 (⚪).

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
R12: pass
R13: pass

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

Carl: unavailable (copilot backend, model gemini-3.8-flash, exit 1: "You have
exceeded your monthly quota"). Retried once; same failure. No UI/frontend lens
this cycle. The diff is Python CLI code with no frontend surface, so the
coverage loss is small.

## Notes on the test gate

The suite run during staging exited 1 on
`skills/sweep-fix/scripts/test_sweep_scan.py::test_scan_returns_promptly_past_the_deadline_while_a_repo_still_hangs`,
a timing-sensitive test outside this PRD's changed files. Re-run in isolation:
29 passed. A full re-run of the gate at the same HEAD then exited 0 with
4133 passed, 9 skipped — so the staged failure was a parallel-timing flake, not
a regression from this work. `braid --check` at this HEAD: 0 linked, 131
current, 20 ignored, 0 removed, 0 backed up, 0 configured, 0 drift. The PRD's
exit criterion is met. R16 and R17 are superseded by this measurement.

Verdict: 17 findings
Tests: 4133 passed, 0 failed, 9 skipped (suite run this cycle)
