---
prd: docs/dev/project-management/prds/wip/00073-sweep-loud-failures-v1.md
review: 1
date: 2026-10-11
head_sha: 6b10b9597c1061906ebb036960cdf6905efabe26
reviewers: alice,blake,bob
agents:
  alice: available
  blake: available
  bob: available
  carl: unavailable
dispatch_rows:
  bob: fe161866
  carl: 4edfade0
---

# Review: 00073-sweep-loud-failures-v1

Diff range: `03c6b601db76452d06ebd33facc85c6acebfca63..6b10b9597c1061906ebb036960cdf6905efabe26`

codex_rung_guard: not fired

Scope: FULL cycle-1 review of the PRD work range (tasks 1-4). Commit 6b10b95 is autopilot state only.

pack: failed (`engram pack` exit 1: not inside a registered repo). `{PACK_FILE}` and `{PACK_FINDINGS}` carried `(no pack available this cycle)`. Degraded on retrieval context, not invalid.

Carl: unavailable, runtime failure (exit 1, not exit 4): copilot backend (`gemini-3.8-flash`) reported "No authentication information found". Failed again on the one retry. Not latched for the batch (not an exit-4 configuration rejection).

codex_thread_id: not stamped. Bob's first run hit `sandbox-exec: sandbox_apply: Operation not permitted` and read no input; the thread-id sidecar was not written.

checks queue: none written (Bob's VERIFY bucket is empty; Eve did not run).

Carried-forward checks: none (cycle 1).

Mechanical test checks: 2 tautological `or`-hedge shapes (test_sweep_main.py:212, test_sweep_render_report.py:701), absorbed into rows R2 and R5 as `mech-check`. Fail-first replay found touched tests passing against base in three files, added as rows R13-R15. Alice judged these deliberate guards or refactor-equivalence pins (see her notes), so they stay 🟡 for the decision gate.

Consolidation: `consolidate_findings.py` (script-side), no ledger (cycle 1). Bob's output was normalized before consolidation: the codex `-o` file carried the echoed prompt (including a template example line `[BOB] 🟠 Missing error handling strategy` that is not a finding), so it was trimmed to his final answer, and his `- [BOB]` bullet prefix was stripped so the lines match the issue format.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [2/3] | 🟡 | `enumerate_repos` uses `Path(cwd).absolute()`, which does not normalise `..`. For `--cwd ../repo/sub`, `_git_root` walks the textual parents (`/x/y/../repo`, `/x/y/..`, `/x/y`, ...), not the real ancestors. It can return a non-normalised root like `/x/y/../repo` that never equals the registry row `/x/repo`. The repo is then scanned twice and may show as a registry gap, which is the bug this task fixes, and it can also pick up a `.git` from a lexical parent that is not a real ancestor. Replace with `Path(os.path.abspath(cwd))`, which normalises `..` without following symlinks, and add a `..` cwd test. | skills/sweep-fix/scripts/sweep.py:151 | 2 | ALICE, BOB |
| R2 | [2/3] | 🟡 | The shapes block flags `assert escaping_out in message or str(target) in message` as an either-or hedge. It is pre-existing (blame 2026-08-29), not introduced by this diff, but the file is touched here. Pin one outcome. | skills/sweep-fix/scripts/test_sweep_main.py:212 | general | ALICE, BOB, mech-check |
| R3 | [1/3] | 🟡 | YAML quoting is not literally `json.dumps(value, ensure_ascii=True)`. A new helper `_yaml_quote` calls `json.dumps(ensure_ascii=False)` and then escapes every non-`isprintable()` character by hand. The behavior is valid and tested, and DEL and U+0085 are handled correctly (plain `ensure_ascii=True` leaves DEL raw, so the PRD's premise was wrong). It still conflicts with "replace both helpers with json.dumps" and leaves a new hand-rolled 10-line escaper. Printable non-ASCII is emitted raw rather than ASCII-escaped. | skills/sweep-fix/scripts/sweep.py:413 | 3 | BLAKE |
| R4 | [1/3] | 🟡 | `resolve_ast_grep` can still raise something other than `RuntimeError` (sweep.py:69-74). `subprocess.run(["mise", "which", ...], timeout=30)` can raise `TimeoutExpired`, and an OSError is possible too. Neither is caught by main's `except RuntimeError` (sweep.py:566), so this setup failure ends in a traceback instead of a one-line exit 1. Narrow, but the PRD's goal is that every setup failure takes the diagnostic path. | skills/sweep-fix/scripts/sweep.py:69 | 1 | BLAKE |
| R5 | [1/3] | 🟡 | Mechanical check flags an existing either-or assertion in `test_render_report_how_to_proceed_states_fixes_apply_only_in_invoking_repo`. Assert the required invoking-repo restriction directly. | skills/sweep-fix/scripts/test_sweep_render_report.py:701 | general | BOB, mech-check |
| R6 | [1/3] | 🟡 | The awkward-scalar and broad-corpus tests duplicate the same rendering, parsing, and four assertions. Combine their parameter sets into one round-trip test, retaining descriptive case IDs and all values. | skills/sweep-fix/scripts/test_sweep_render_report.py:616 | 3 | BOB |
| R7 | [1/3] | ⚪ | `skills/sweep-fix/SKILL.md` step 2 describes `main()` but does not say that an unusable scan tool, registry or control repo now exits 1 with one stderr line and no report. The caller now has a new failure mode to handle. Add one sentence. | skills/sweep-fix/SKILL.md:41 | 1 | ALICE |
| R8 | [1/3] | ⚪ | `registry.open()` on an unreadable file raises `PermissionError`, which is not a `RuntimeError`, so it escapes `main` as a traceback. A registry that is a directory reads as "registry not found". The PRD only requires the missing case, so this is a gap in the same bug class (setup faults that surface as tracebacks), not a defect in the delivered scope. Consider catching `OSError` at the open and re-raising it as `RuntimeError`. | skills/sweep-fix/scripts/sweep.py:155 | 1 | ALICE |
| R9 | [1/3] | ⚪ | The registry guard is only `is_file()` (sweep.py:152). An unreadable registry (PermissionError) or a non-UTF-8 registry (UnicodeDecodeError) still gives a raw traceback at `registry.open()` (sweep.py:155). The PRD only required the missing-file case. | skills/sweep-fix/scripts/sweep.py:155 | 1 | BLAKE |
| R10 | [1/3] | ⚪ | The default-report collision check is check-then-act. `exists()` runs in `_resolve_report_path` (sweep.py:524) and the later `write_text` (sweep.py:579) overwrites unconditionally. Two concurrent same-reason sweeps could still clobber each other. This is not the sequential case the PRD requires. | skills/sweep-fix/scripts/sweep.py:524 | 4 | BLAKE |
| R11 | [1/3] | ⚪ | When a sweep runs from a subdirectory, the repo scan covers the whole repo, but the default report path is still built under the resolved `--cwd` subdirectory, not the git root (sweep.py:557-558). The PRD does not specify this, so it is flagged, not failed. cwd walk-up also uses `.absolute()` while main passes the unresolved `args.cwd`, so a symlinked cwd (for example /tmp versus /private/tmp) may not dedupe against a registered real path. | skills/sweep-fix/scripts/sweep.py:151 | 2 | BLAKE |
| R12 | [1/3] | ⚪ | The report-path tests live in a seventh file, `test_sweep_report_path.py`. The PRD's test module list names six files. The test the PRD names exists and passes. This is a minor structural deviation (later commits moved the tests there on purpose). | skills/sweep-fix/scripts/test_sweep_report_path.py:25 | 4 | BLAKE |
| R13 | [1/3] | 🟡 | 3 touched test(s) pass against the pre-change code: test_a_sweep_does_not_need_the_scan_tool_of_the_other_kind, test_an_invalid_out_is_refused_before_the_scan_tool_is_resolved | skills/sweep-fix/scripts/test_sweep_main.py | general | mech-check |
| R14 | [1/3] | 🟡 | 109 touched test(s) pass against the pre-change code: test_render_report_astgrep_rule_block_contains_expected_fields, test_rendered_rule_block_round_trips_every_awkward_scalar +103 more | skills/sweep-fix/scripts/test_sweep_render_report.py | general | mech-check |
| R15 | [1/3] | 🟡 | 3 touched test(s) pass against the pre-change code: test_an_explicit_out_naming_an_existing_report_is_returned_unsuffixed, test_a_same_reason_report_from_another_day_leaves_todays_path_unsuffixed, test_a_relative_explicit_out_naming_an_existing_report_is_returned_unsuffixed | skills/sweep-fix/scripts/test_sweep_report_path.py | general | mech-check |

## Alice

Implementation-aware consensus lens. 1 🟡, 3 ⚪ (rows R1, R2, R7, R8). Notes: the replay's base-passing tests are deliberate guards or refactor-equivalence pins (the other-kind-tool test, the invalid-out-before-resolve test, the three explicit-out-unsuffixed tests, the YAML round-trip corpus), each able to fail under a wrong implementation; the `_yaml_quote` deviation is documented and justified by the astral round-trip; function and file sizes are within limits.

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

Blind lens (PRD only). Ran `uv run pytest skills/sweep-fix/scripts -q`: 245 passed, 0 failing. All six defects fixed. 2 🟡, 4 ⚪ (rows R3, R4, R9, R10, R11, R12). B1-B19: all pass.

## Bob

Doubt + de-slop lens (codex), after one retry (inlined). The first run failed to read any input (`sandbox-exec: sandbox_apply: Operation not permitted`) and emitted all-fail R verdicts. The retry ran on `bob-prompt-00073c1-20261011-retry.md` with context and diff inlined. 4 🟡 (rows R1, R2, R5, R6). FIX bucket = those four; VERIFY: (none); KNOWN: (none).

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

## Carl

Unavailable this cycle: exit 1 on both the first run and the retry, copilot backend not authenticated ("No authentication information found"). No output consolidated.

Verdict: 15 findings
Tests: 3707 passed, 0 failed, 6 skipped (reused from last-verification.json at 052ada6)
