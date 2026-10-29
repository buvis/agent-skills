---
prd: docs/dev/project-management/prds/wip/00104-sweep-overruns-process-deadline-v1.md
review: 2
date: 2026-10-29
head_sha: 376d5cb6c79d88a1f53188910ade67deda6da016
codex_thread_id: 01a18531-6a17-7112-9d21-33a7abe10392
reviewers: alice,blake,bob
agents:
  alice: available
  blake: available
  bob: available
  carl: unavailable
dispatch_rows:
  bob: 30a411e7
  carl: cc8363c6
---

# Review: 00104-sweep-overruns-process-deadline-v1

Diff range: `6ea6c5e84f1b37fa72f52f97cf6cf7169a4152ad..376d5cb6c79d88a1f53188910ade67deda6da016`

codex_rung_guard: not fired

## Review Summary

Reviewed: 3 completed tasks (incremental review of cycle-1 rework)
PRDs checked: 00104-sweep-overruns-process-deadline-v1.md
Consensus engine: legacy (single Alice subagent)
Doubt reviewer: codex (Bob); Eve not activated
Context pack: ok
Carl: unavailable this cycle (gemini-run backend copilot, exit 1: "You have exceeded your monthly quota"). Quota failure, not exit 4 - no batch latch, Carl stays eligible next cycle.

Note on the `Tests:` line: `review-stage`'s gate run exited 0 but its summary-line parser returned
`counts unavailable`. The counts below are read verbatim from the gate log it wrote
(`docs/dev/tmp/gate-20261029-c2.log:197`), not from a second suite run. This parser miss is the same
pre-existing defect flagged in cycle 1.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [2/3] | 🟡 | `test_sweep_main.py` is still 896 lines, over the 800-line limit. R4 was only half-resolved: the new CLI harness moved out, but the file was already about 870 lines before the diff and was never brought under 800. Move another group of tests, for example the scan-tool-unresolvable and control-failure tests, into a second module. The file also ends with a stray pointer comment, "moved to test_sweep_main_deadline.py", that should go once the split is final | skills/sweep-fix/scripts/test_sweep_main.py:872 | 3 | ALICE, BOB |
| R2 | [1/3] | 🟠 | R1's fix (setup time deducted from the scan budget) has no test that fails without it. The rework loosened `test_main_passes_deadline_through_to_scan` and `test_main_passes_remaining_deadline_into_verify_control` to `== pytest.approx(5, abs=0.5)` plus `<= 5`. The old code, which passed exactly `args.deadline`, satisfies both. Reverting `_scan_deadline_after_setup` to `return args.deadline` leaves all 38 tests in the two main test files green. Nothing exercises the deduction or the `max(..., 0)` clamp. Add a test that makes setup consume measurable time (a monkeypatched slow `enumerate_repos`) and asserts the deadline passed to `scan()` is smaller by about that amount, and 0 when setup exhausts the budget | skills/sweep-fix/scripts/test_sweep_main.py:592 | 2 | ALICE |
| R3 | [1/3] | 🟠 | Windows cleanup remains outside the required bound: changing each `taskkill` timeout from 30 seconds to 5 still exceeds the 2-second cleanup allowance for one hung call, and serial calls multiply that delay. Implement one shared cleanup budget and test multiple processes with a stalled termination command; the new test only checks the timeout constant. | skills/sweep-fix/scripts/sweep.py:94 | 2 | BOB |
| R4 | [1/3] | 🟡 | `test_sweep_main_deadline.py` imports `_is_running` and never uses it. `_is_running` appears only on the import line, and the file uses `_still_running_after` instead. Remove the import | skills/sweep-fix/scripts/test_sweep_main_deadline.py:15 | 3 | ALICE |
| R5 | [1/3] | 🟡 | The R2 timing test got weaker. It now asserts that no launch happens later than `expiry + 0.5`, where it used to assert none after `scan()` returned. A queued search freed by a kill starts within milliseconds of expiry, so this assertion cannot catch the bug it targets. It passed with the `_scan_repo` check removed. Only the deterministic `_scan_repo` test pins R2. Tighten the slack to about 0.1s, or drop the timing assertion and rely on the deterministic test | skills/sweep-fix/scripts/test_sweep_scan.py:1238 | 2 | ALICE |
| R6 | [1/3] | 🟡 | Setup-budget regressions remain unpinned: the amended assertions accept exactly 5 and 300, so passing the original full deadline still satisfies them. Simulate setup consuming a known budget and assert the exact remainder; also cover setup exhausting the budget without launching searches. | skills/sweep-fix/scripts/test_sweep_main.py:567 | 2 | BOB |
| R7 | [1/3] | 🟡 | The extraction leaves unused `_is_running` imports in both test modules; polling and teardown now use it through the shared helpers and fixture. Remove both unused imports. | skills/sweep-fix/scripts/test_sweep_main_deadline.py:15, skills/sweep-fix/scripts/test_sweep_scan.py:16 | 3 | BOB |
| R8 | [1/3] | ⚪ | R3's fix bounds each `taskkill` at 5s, but `_ProcessRegistry.kill_all` still kills serially. Eight stuck workers could still cost up to 40s on Windows. One 5s call already exceeds the 2s cleanup tolerance, and the review asked for one short cleanup budget. This only matters if `taskkill` hangs, so I'd accept it, or give `kill_all` a total deadline | skills/sweep-fix/scripts/sweep.py:272 | 2 | ALICE |
| R9 | [1/3] | ⚪ | The spec names `skills/sweep-fix/scripts/test_sweep_main.py` for the real-CLI elapsed-time regression, but it lives in a separate file, `test_sweep_main_deadline.py`, split out to stay under the file-size limit. Coverage is intact; only the path differs from the spec's file list. | skills/sweep-fix/scripts/test_sweep_main_deadline.py:106 | general | BLAKE |
| R10 | [1/3] | ⚪ | `_kill_tree` can call `killpg` on a pid whose process already exited and was reaped, because `registry.kill` runs from another thread before `unregister`. A recycled process-group id is theoretically possible but very unlikely. | skills/sweep-fix/scripts/sweep.py:224 | general | BLAKE |

### Auto-dismissed (ledger)

- [BLAKE] ⚪ After killing a timed-out search, `_communicate_tracked` calls `proc.communicate()` with no timeout. A descendant that escaped the process group (for example via its own `setsid`) and kept the pipe open would hang the worker and delay exit. The normal shim and rg cases are covered. | File: skills/sweep-fix/scripts/sweep.py:290 — single-voice; a search command that deliberately escapes its own session is outside the PRD's stated scope, which covers subprocess trees created by a search command

## Alice

Prior findings R1 to R5 are fixed in the code, but R4 (the 800-line limit) is only half-fixed. The new tests don't pin R1. `uv run pytest skills/sweep-fix/scripts` gave 296 passed.

- R1 (setup time): fixed. `main()` passes `_scan_deadline_after_setup(args, start)` to `scan()`; `_verify_zero_hit_sweep` reuses the same `start`, so scan and control share one clock.
- R2 (queued searches launching after expiry): fixed. `_scan_repo` returns `DEADLINE_REASON` before any Popen once the deadline has passed.
- R3 (30s `taskkill`): mostly fixed. `KILL_TREE_TIMEOUT = 5` replaces the 30s, with a test for the Windows branch.
- R4/R5 (split and dedupe): CLI tests moved to `test_sweep_main_deadline.py`, helpers into `sweep_test_helpers.py` and `conftest.py`. `test_sweep_main.py` is still 896 lines.

Mutation checks in a temp copy (`/tmp/alice-mut-c2`): reverting `_scan_deadline_after_setup` to `return args.deadline` leaves all 38 tests in the two main test files green; removing the `_scan_repo` deadline check fails only `test_scan_repo_never_launches_a_search_once_its_own_deadline_has_expired`.

Findings: R2, R1, R4, R5, R8 in the table above.

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
R13: fail

## Blake

No spec violations. Three Low-severity findings. The sweep-fix tests pass (296 in `skills/sweep-fix/scripts`), and `validate_skill.py skills/sweep-fix` reports valid. Blake did not run `braid --check`, and did not check that the CLI timing regression fails against the prior code.

Verified: one shared budget across scan and control verification; `TimeoutError("sweep unverified: ...")` on an exhausted budget with exit 1 and no report; mid-verification expiry; child-tree cleanup via session/process group with `killpg` (POSIX) and `taskkill /T` (Windows); late-register kill after registry close; `cancel_futures=True`; preserved result ordering, hit caps, `Partial:`/`Failed:` reporting; documented behavior in `skills/sweep-fix/SKILL.md:41-49`.

Findings: R9, R10 in the table above, plus one ledger-dismissed low.

B1: pass
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

FIX: R3, R6, R1, R7 in the table above.
VERIFY: (none)
KNOWN: (none)

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
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

Carl: unavailable (gemini backend copilot returned exit 1, monthly quota exceeded). No output produced; not consolidated.

Verdict: 10 findings
Tests: 4089 passed, 9 skipped (suite run this cycle)
