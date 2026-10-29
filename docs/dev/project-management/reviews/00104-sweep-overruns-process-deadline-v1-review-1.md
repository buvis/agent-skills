---
prd: docs/dev/project-management/prds/wip/00104-sweep-overruns-process-deadline-v1.md
review: 1
date: 2026-10-29
head_sha: 6ea6c5e84f1b37fa72f52f97cf6cf7169a4152ad
codex_thread_id: 01a18531-6a17-7112-9d21-33a7abe10392
reviewers: alice,blake,bob
agents:
  alice: available
  blake: available
  bob: available
  carl: unavailable
dispatch_rows:
  bob: 5e35a772
  carl: 3e6118f7
---

# Review: 00104-sweep-overruns-process-deadline-v1

Diff range: `f44d026c394648eb43f261ce0cba9fdb569d93e7..6ea6c5e84f1b37fa72f52f97cf6cf7169a4152ad`

codex_rung_guard: not fired

## Review Summary

Reviewed: 1 completed task
PRDs checked: 00104-sweep-overruns-process-deadline-v1.md
Consensus engine: legacy (single Alice subagent)
Doubt reviewer: codex (Bob); Eve not activated
Context pack: ok

### Agent Status

- Alice: ✅ Available
- Blake: ✅ Available
- Bob: ✅ Available (codex, inlined prompt 198 KB)
- Carl: ⚠️ Unavailable: gemini-run exit 1, backend copilot model gemini-3.8-flash, "You have exceeded your monthly quota". Not exit 4, so no batch latch; no retry — a monthly quota does not clear within a cycle.

### Provenance notes

- `review-stage` ran the full suite this cycle (`uv run pytest`, exit 0) but its
  parser did not recognise pytest's `========== N passed ... ==========` summary
  line, so it emitted `counts unavailable` and wrote no `last-verification.json`.
  The counts in the `Tests:` line below were read from the gate log it produced
  (`docs/dev/tmp/gate-20261029-00104-c1.log:195`). `autopilot verify` was not
  re-run: it wraps the same parser, so it would re-spend seven minutes of suite
  time and fail to parse identically. There is therefore still no
  `last-verification.json` record at this HEAD.
- Three `[MECH]` fail-first-replay rows were absorbed into the table below
  (R15-R17), per step 6.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [3/3] | 🟠 | `main()` starts its clock before `resolve_rg()`/`enumerate_repos()`, but `scan()` is given the full `args.deadline` and restarts its own clock inside the call. Setup time is therefore not deducted from the scan budget, and total wall time can reach setup plus deadline. The design doc says setup should count against `--deadline`. Pass `deadline=args.deadline - (time.monotonic() - start)` to `scan()`, clamped for the `<= 0` case, or document the setup exclusion | skills/sweep-fix/scripts/sweep.py:763 | 1 | ALICE, BLAKE, BOB |
| R2 | [1/3] | 🟠 | Queued searches can launch after expiry. Killing a running search frees its worker before pending futures are cancelled, and workers never check the deadline before `Popen`. Cancel pending work at expiry and check the shared deadline before launching searches. The queued-search test must check launch times against expiry, rather than against `scan()` returning. | skills/sweep-fix/scripts/sweep.py:399 | 1 | BOB |
| R3 | [3/3] | 🟠 | Windows cleanup can overrun the deadline by 30 seconds per `taskkill`: `_kill_tree()` uses `DEFAULT_SCAN_TIMEOUT`, and registry cleanup invokes it serially. Bound termination by one short cleanup budget and add Windows-branch coverage; the new lifetime regressions all skip Windows. | skills/sweep-fix/scripts/sweep.py:211 | 1 | BOB, ALICE, BLAKE |
| R4 | [2/3] | 🟡 | test_sweep_main.py grew to 1147 lines (about 870 before this diff), well past the 800-line limit. The new CLI harness (shim writer, pid helpers, `_run_cli`, three CLI tests) at lines 896-1147 should move to a new `test_sweep_main_deadline.py`, or into `sweep_test_helpers` | skills/sweep-fix/scripts/test_sweep_main.py:896 | 1 | ALICE, BOB |
| R5 | [2/3] | 🟡 | Test helpers are duplicated across files. `_write_tree_shim`, `_recorded_pids`, `_is_running`, `_still_running_after` and the `shim_pid_dir` fixture appear in test_sweep_scan.py (611-682) and test_sweep_main.py (908-981) with only small variations. `_is_running` differs: scan reaps with `waitpid`, main does not. Put one copy in the existing `sweep_test_helpers` module (fixture in a conftest) | skills/sweep-fix/scripts/test_sweep_main.py:908 | 1 | ALICE, BOB |
| R6 | [1/3] | 🟡 | `_kill_tree` runs `taskkill` on Windows with `timeout=DEFAULT_SCAN_TIMEOUT` (30s). The design asks for a short, separate timeout so a hung `taskkill` cannot stall deadline cleanup. A 30s stall would defeat the "exit within the deadline plus 2s" goal on Windows | skills/sweep-fix/scripts/sweep.py:219 | 1 | ALICE |
| R7 | [1/3] | 🟡 | Scope creep: the diff extracts `_yaml_quote` and `_render_astgrep_rule_block` into a new `sweep_rule_pack.py` and adds a sibling-module import in sweep.py. It also loosens the stdlib-only import test in test_sweep_resolvers.py to allow sibling modules. Neither is in the PRD's file list or the design doc. It looks like a size workaround to keep sweep.py under 800 lines (now 787). It works and the tests pass, but the PRD and design should name it, or it should be split into a separate change | skills/sweep-fix/scripts/sweep_rule_pack.py:1 | general | ALICE |
| R8 | [1/3] | 🟡 | The new subprocess test harness duplicates shim generation, PID discovery, polling, and cleanup across two test files. Extract shared fixture/helpers while preserving the distinct child-reaping behavior. | skills/sweep-fix/scripts/test_sweep_main.py:908 | 1 | BOB |
| R9 | [1/3] | 🟡 | New CLI regressions further expand `test_sweep_main.py` beyond the mandatory 800-line limit; the supplied function table places its final test at line 1120. Split the CLI tests into focused modules below the limit. | skills/sweep-fix/scripts/test_sweep_main.py:1120 | 1 | BOB |
| R10 | [1/3] | ⚪ | In `_ProcessRegistry.kill` and `kill_all`, a process that has already exited but is not yet unregistered can be sent `os.killpg` on its pid. That is a theoretical pid-reuse window, since the group id equals the reaped pid. It is negligible for a short window, but worth a one-line comment | skills/sweep-fix/scripts/sweep.py:264 | 1 | ALICE |
| R11 | [1/3] | ⚪ | `main()` uses a new `_verify_zero_hit_sweep` helper instead of the inline `remaining` check in the design's `main()` contract. Behavior is equivalent: exit 1, one stderr line, no report. The `except (RuntimeError, TimeoutError)` widening matches the contract. Informational only | skills/sweep-fix/scripts/sweep.py:723 | 1 | ALICE |
| R12 | [1/3] | ⚪ | `_communicate_tracked` calls `proc.communicate()` with no timeout after `_kill_tree` on a per-search timeout. If a search command's descendant leaves the killed session or group (own `setsid`, or a detached grandchild that holds the pipe), the worker blocks on pipe EOF. `scan()` then blocks in `executor.shutdown(wait=True)`. The shim tests only cover descendants that stay in the group. | skills/sweep-fix/scripts/sweep.py:288 | 1 | BLAKE |
| R13 | [1/3] | ⚪ | The worker cleanup in `scan()` runs only when `deadline_hit` is true. If the collection loop raises (for example `KeyboardInterrupt`), `finally` still calls `executor.shutdown(wait=True, cancel_futures=False)` and does not call `kill_all()`. Live searches then delay exit on that path. This is outside the stated expiry case. | skills/sweep-fix/scripts/sweep.py:499 | 1 | BLAKE |
| R14 | [1/3] | ⚪ | The Windows tree-kill path (`taskkill /F /T`, `CREATE_NEW_PROCESS_GROUP`) has no test. The real-CLI timing tests are POSIX-only (`_POSIX_SHIM` skips on `nt`). `taskkill` itself carries a 30s timeout, which could stretch cleanup. The spec's Windows-compatibility requirement is met only by code inspection. | skills/sweep-fix/scripts/sweep.py:215 | 1 | BLAKE |
| R15 | [1/3] | 🟡 | 2 touched test(s) pass against the pre-change code: test_cli_zero_hit_sweep_with_ample_deadline_verifies_control_as_before | skills/sweep-fix/scripts/test_sweep_main.py | general | mech-check |
| R16 | [1/3] | 🟡 | 2 touched test(s) pass against the pre-change code: test_run_rg_never_invokes_a_bare_rg_binary_by_name, test_sweep_module_imports_only_stdlib_modules | skills/sweep-fix/scripts/test_sweep_resolvers.py | general | mech-check |
| R17 | [1/3] | 🟡 | 4 touched test(s) pass against the pre-change code: test_scan_runs_repo_searches_concurrently, test_scan_returns_promptly_past_the_deadline_while_a_repo_still_hangs | skills/sweep-fix/scripts/test_sweep_scan.py | general | mech-check |

Consolidation note: `consolidate_findings.py` merged R1's three citations after
suffix stripping (`sweep.py:763 ~ :760 ~ :75 ~ :737`). The merge is correct on
substance — all three lenses describe the same unbudgeted-setup defect — but
Blake's `:75` line (the unbounded pre-scan `resolve_ast_grep`/`mise which` call)
and Bob's `:737` line were folded into Alice's wording and lose their own
specifics. Both are facets of R1 and are fixed by the same change.

Consensus cells corrected by the decision gate: `consolidate_findings.py` left
four duplicates unmerged because their `File` cells cite different lines of the
same defect, so each was scored as single-voice. The gate folded them and
raised the surviving row's Consensus and Found By:

- R3 absorbs R6 (same `taskkill` 30s timeout, cited at `:211` and `:219`) and
  R14 (the same Windows branch being untested) → three voices, BOB, ALICE, BLAKE.
- R4 absorbs R9 (the same test_sweep_main.py 800-line violation, cited at
  `:896` and `:1120`) → two voices, ALICE, BOB.
- R5 absorbs R8 (the same duplicated subprocess test harness, both at `:908`)
  → two voices, ALICE, BOB.

The absorbed rows R6, R8, R9 and R14 keep their table rows for traceability and
are dispositioned `discard` with reason "duplicate of R{n}". Without this
correction all four would have been single-voiced away, and `review-close`
correctly refused the first findings batch that tried to make a single-voice
medium a task (`refused: single_voice_fix`, R4).

## Alice

Implementation-aware consensus lens. Five 🟡 and two ⚪ findings, no 🔴/🟠 of her
own beyond the shared R1 (which she rated 🟡; Bob rated it 🟠 and the
consolidator kept the higher severity).

Verification she ran: `uv run pytest skills/sweep-fix/scripts` passes (294
passed, 32.7s). She did not run the pre-change code herself, so the fail-first
claim rests on the context block's replay (15 of 23 touched tests fail at base).
The tests that pass at base are the behavior-preserving ones the PRD wants kept,
plus `test_scan_returns_promptly_past_the_deadline_while_a_repo_still_hangs` and
`test_scan_runs_repo_searches_concurrently`, which were adapted to the Popen
launch path. The pinning tests are the new grandchild-kill scan tests, the two
CLI tests and the verify_control shared-clock tests; all have cleanup fixtures
that kill leftover shims on failure.

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
R13: fail

## Blake

Blind lens, spec-only. One 🟡 and four ⚪ findings. He located the code himself,
ran the three named test files (83 passed), and confirmed `validate_skill.py
skills/sweep-fix` reports valid. He did not run `braid --check`, and did not
verify the claim that the timing regression fails against the prior code.

What he verified as holding:

- `main` passes `args.deadline` to `scan`; `_verify_zero_hit_sweep` skips
  verification when no budget remains and raises `TimeoutError`; `main` turns
  that into a `sweep unverified: ...` stderr line, exit 1, and no report.
- `verify_control` receives only the remaining budget and shares it between its
  scan and its control-term search.
- Searches launch in their own session or process group, tracked by a
  `_ProcessRegistry` that closes after `kill_all()`; a process registered after
  expiry is killed immediately, so there is no register-after-kill window.
- Queued futures are cancelled at expiry; completed results are collected in
  repo order, so deterministic ordering and per-repo hit caps are kept;
  incomplete repos are reported under `DEADLINE_REASON`.
- Hits present means a report is written with the `Partial:` line and control
  verification is not run.
- The real-CLI regressions at `test_sweep_main.py:1039`, `:1074` and `:1120`
  cover the sleeping-shim timing bound, the unverified exit-1 path and the
  retained successful-control case.
- `skills/sweep-fix/SKILL.md:41` documents the shared deadline, the `Partial:`
  line and the unverified refusal.

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

Doubt lens (codex, static-only sandbox, inlined prompt). Three 🟠 and two 🟡
findings in FIX; VERIFY and KNOWN both empty, so no verification-check queue was
written for this cycle.

FIX: R1 (setup time not charged to the scan budget), R2 (queued searches can
launch after expiry), R3 (Windows `taskkill` cleanup can overrun by 30s per
call), R8 (duplicated subprocess test harness), R9 (test_sweep_main.py over the
800-line limit).

VERIFY: (none)

KNOWN: (none)

R1: fail
R2: pass
R3: fail
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

Not run. `gemini-run.sh` exited 1 with "You have exceeded your monthly quota"
(backend copilot, model gemini-3.8-flash, request id
580C:9D9FE:B45C7FA:BE9B4C2:6AE29C0D). No output file was published beyond a
zero-byte `-o` stub, which was not consolidated. Exit 1 is a runtime failure,
not the exit-4 permanent-unavailability case, so Carl is not latched for the
batch and will be tried again next cycle.

Verdict: 17 findings
Tests: 4087 passed, 9 skipped (suite run this cycle)
