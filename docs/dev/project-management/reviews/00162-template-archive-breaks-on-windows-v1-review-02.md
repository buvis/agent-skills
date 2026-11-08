---
prd: docs/dev/project-management/prds/wip/00162-template-archive-breaks-on-windows-v1.md
review: 2
date: 2026-11-08
head_sha: 5b42fed8794e3e28f577d5f7cd0004332d5ebffc
reviewers: alice,blake,bob,eve
agents:
  alice: available
  blake: available
  bob: available
  carl: unavailable
  eve: available
dispatch_rows:
  bob: 6748cbb8
  carl: a2cac3fc
---

# Review: 00162 Windows archive lane

Diff range: `73386d63132c1a9f10a710e8bf9bbafe593c987a..5b42fed8794e3e28f577d5f7cd0004332d5ebffc`

codex_rung_guard: not fired

**NO CRITICAL OR HIGH FINDING; ROSTER STILL DEGRADED; LANE NOT APPROVED.**
This is cycle 2, the cap cycle (cap 2). All seven cycle-1 repair targets
(R1, R2, R3, R4, R9, R10, R19) are verified resolved by Alice, Bob and Eve in
the code, and Blake's PRD-only pass found no spec gap. Nothing raised this
cycle is CRITICAL or HIGH. The cycle-2 voices raised only Low and Medium
rows, listed below with their dispositions.

The roster is not the full provider roster the handoff requires. Bob's Codex
helper and Carl's Copilot helper both exited 3 before inference with
`refusing nested dispatch (already inside a CLI agent)`. The cause is
`CODEX_SESSION_ID` set in this session's environment (the session was
launched under a Codex parent). No guard was bypassed and no marker was
unset. Bob's exact inlined doubt/de-slop prompt ran on the prescribed
fallback, native Claude Sonnet 5.5 (`autopilot:bob`), high effort. Carl did
not run. No independent-provider (Codex or Gemini) inference exists for this
cycle, so the lane is not declared approved. Bob's Codex voice and Carl's
Gemini voice are still owed against HEAD `5b42fed` (see Required next step).

Models, as installed and as run:

- Alice: `autopilot:alice`, native Claude Sonnet 5.5, effort high.
- Blake: `autopilot:blake`, native Claude Sonnet 5.5, effort high. PRD and the
  test-gate line only; the prompt forbade reading reviews, designs, ledgers
  and task files.
- Bob: `autopilot:bob` fallback, native Claude Sonnet 5.5, high effort (the
  session default; `agents/bob.md` pins no model). Codex was requested, never
  ran. No Codex thread id exists.
- Carl: requested Copilot / `gemini-3.8-flash`; not run (exit 3, same guard).
- Eve: `autopilot:eve`, Claude Fable, effort xhigh (`agents/eve.md`).

Model identities were not independently verified from transcript fields in
this session; they come from the installed agent definitions and the
dispatch parameters.

## Evidence

- Full adapter gate at HEAD `5b42fed`, Python 3.13.18 (the handoff's
  `pytest-gate.sh` command, run through `autopilot review-stage`):
  **4529 passed, 0 failed, 9 skipped**, suite run this cycle, 399 seconds.
  Log: `docs/dev/tmp/gate-00162-20261108-c2.log`. Kept separate from the
  recorded gate at `b654f15`, which also read 4529 passed, 0 failed, 9 skipped.
- Archive modules on isolated Python 3.10 and 3.12 (`uv run --isolated`, each
  its own environment), `-W error::DeprecationWarning`: the five archive
  modules plus the extracted `test_eval_tree_links_typed.py` and the
  `test_eval_tree_state.py` module, six files in total: **350 passed on 3.10**
  (46.06 s) and **350 passed on 3.12** (45.22 s). No platform skip, no xfail,
  no weakened POSIX assertion. These are macOS results, not native Windows.
- Alice: seven archive and tree modules on 3.13, deprecations as errors:
  360 passed, 0 skipped, 0 xfail. Eve: the same seven on 3.13 (360 passed,
  41.58 s) and four modules on 3.10 (113 passed). Blake: three modules on
  3.13 (103 passed).
- Fail-first replay (staged by the runtime, base `73386d6`): 26 touched tests
  ran, 9 failed against base, 17 passed. The passing 17 are explained below
  (guards and verbatim moves).
- Carry-forward of the cycle-1 check queue: its one entry
  (`checks-1.json`, Python 3.13 safety and staging) has `result.exit` 0 and
  `rework_result.exit` 0, so nothing carries forward.
- The context pack failed (`engram pack exit 1: not inside a registered
  repo`); the no-pack sentinel was used. Degraded, not invalid.
- Consolidation: `consolidate_findings.py` ran over all four outputs for the
  `[AGENT]` issue lines. Eve's FIX/VERIFY/KNOWN bucket items and the five
  `[MECH]` lines are not issue-line shaped, so those rows were added by hand
  from the raw outputs (model-side for them only).

## Consolidated Findings

Consensus denominators use the four reviewers that ran (Carl excluded).

| Ref | Consensus | Severity | Issue | File | Found By |
|---|---|---|---|---|---|
| R1 | [3/4] | ⚪ Low | `_set_index_modes` hand-rolls a third `subprocess.run(["git","-C",...])` spelling instead of giving `_git_bytes` an `input=` parameter, only because the `_serve_archive` fake takes no keywords. **FIX** (sweep): add `input=` to `_git_bytes`, widen the fakes to `**kwargs`, call it from `_set_index_modes`. Behavior-preserving. | skills/use-qwen/scripts/eval_harness/trees.py:345 | Alice, Bob, Eve |
| R2 | [2/4] | ⚪ Low | The read side uses `_HOST_SEP` but the write side in `_lay_links_typed` and `_copytree_links_typed` uses `os.sep`; two names for one concept and nothing says the simulation depends on that. **FIX** (sweep): extend the `_HOST_SEP` comment to say it governs reading only and the write side keeps `os.sep`. | skills/use-qwen/scripts/eval_harness/trees.py:457 | Bob, Eve |
| R3 | [3/4] | ⚪ Low | With a failed cleanup the failure rides only on the original's `__context__`; Python hides it when the original was raised `from` a cause, and `raise original` overwrites an earlier implicit context. **DISCARD**: this is exactly the PRD contract ("keep the original exception as the raised error"), the tests pin it, and `__cause__` is kept. Informational. | skills/use-qwen/scripts/eval_harness/trees.py:409 | Alice, Bob, Eve |
| R4 | [2/4] | 🟡 Medium | Native Windows behavior of the host-link fixtures, the literal-backslash case and the clone round trip is inferred, not run. **VERIFY later**: the hosted `windows` job on the exact candidate after combined integration; cannot be closed by pytest on macOS (cycle-1 R23, carried). | skills/use-qwen/scripts/test_eval_tree_host_links.py:64 | Bob, Eve |
| R5 | [1/4] | 🟡 Medium | No `build_template`-level test fails the new `update-index` step: `_fail_seal_step` hooks `trees._git`, which `_set_index_modes` bypasses. **DISCARD single-voice** (the unit test `test_set_index_modes_surfaces_a_git_failure_instead_of_swallowing_it` pins the failure; cleanup itself is generic and tested). | skills/use-qwen/scripts/test_eval_tree_archive_staging.py:299 | Eve |
| R6 | [1/4] | 🟡 Medium | `test_link_text_separator_defaults_to_this_host_s_own` restates the constant's definition (`_HOST_SEP == os.sep`). **DISCARD single-voice**; it fails against base (the name is absent there). | skills/use-qwen/scripts/test_eval_tree_host_links.py:59 | Eve |
| R7 | [1/4] | 🟡 Medium | The hostile climb, multi-segment-climb and chain-escape host-link cases use a bare `pytest.raises(trees.TreeError)`, so nothing pins which check refuses. **DISCARD single-voice**; the sibling accept test fails against base and pins the repair. | skills/use-qwen/scripts/test_eval_tree_host_links.py:114 | Bob |
| R8 | [1/4] | ⚪ Low | `_member_paths_on_the_command_line` matches member names by substring against every argv part, including the `-C` value. **DISCARD single-voice**; current names do not collide. | skills/use-qwen/scripts/test_eval_tree_archive_safety_modes.py:555 | Alice |
| R9 | [1/4] | ⚪ Low | `_simulate_windows_link_text` carries a bytes branch no test exercises. **DISCARD single-voice.** | skills/use-qwen/scripts/test_eval_tree_host_links.py:29 | Eve |
| R10 | [1/4] | ⚪ Low | Module docstring says "Split from test_eval_tree_state.py" though nothing was moved. **DISCARD single-voice** (wording). | skills/use-qwen/scripts/test_eval_tree_host_links.py:9 | Eve |
| R11 | [1/4] | ⚪ Low | `_tree_modes` duplicates the already-imported `_sealed_modes`. **DISCARD single-voice.** | skills/use-qwen/scripts/test_eval_tree_archive_safety_modes.py:234 | Eve |
| R12 | [1/4] | ⚪ Low | `_ignore_filesystem_mode` repeats the three `GIT_CONFIG_*` setenv lines of the safety module. **DISCARD single-voice.** | skills/use-qwen/scripts/test_eval_tree_archive_safety_modes.py:259 | Eve |
| R13 | [1/4] | ⚪ Low | `_set_index_modes` sends paths on stdin (`-z --stdin`) where the PRD text says `--` before the paths. **DISCARD**: a documented, tested, safe departure that closes the Windows command-line cap (cycle-1 R2). | skills/use-qwen/scripts/eval_harness/trees.py:345 | Blake |
| R14 | [1/4] | ⚪ Low | `_set_index_modes` skips members git did not track. **DISCARD**: required because `--chmod` refuses untracked paths; the settled cycle-1 deferral R15 covers it. | skills/use-qwen/scripts/eval_harness/trees.py:335 | Blake |
| R15 | [1/4] | ⚪ Low | `_lay_links_typed` keeps archive order and passes the type explicitly instead of reordering links target-first. **DISCARD**: settled cycle-1 deferral R27; outcome matches the spec. | skills/use-qwen/scripts/eval_harness/trees.py:310 | Blake |
| R16 | [1/4] | ⚪ Low | A failed `os.symlink` in `_copytree_links_typed` leaves a half-copied `dest` and `fresh_clone` never calls `_remove_tree`. **DISCARD single-voice**; the old `copytree` path behaved the same and the PRD does not ask for it. | skills/use-qwen/scripts/eval_harness/trees.py:455 | Blake |
| R17 | [1/4] | ⚪ Low | `_remove_tree`'s `os.chmod(failing, stat.S_IWRITE)` follows symlinks. **DISCARD single-voice**; the PRD prescribes this call and escaping links are refused first. | skills/use-qwen/scripts/eval_harness/trees.py:424 | Blake |
| R18 | [1/4] | 🟡 Medium | `test_build_template_injected_extraction_failure_leaves_no_dest_and_siblings_untouched` hedges with `or`. **DISCARD**: line 266 predates this lane and is the settled cycle-1 deferral R20, untouched by the rework. | skills/use-qwen/scripts/test_eval_tree_archive_staging.py:266 | Eve, mech-check |
| R19 | [2/4] | 🟡 Medium | Two index-mode tests pass against the pre-change code (`test_set_index_modes_asks_git_once_per_non_empty_mode_group_with_paths_on_stdin`, `test_set_index_modes_surfaces_a_git_failure_instead_of_swallowing_it`). **DISCARD as expected**: the three non-empty params of the first fail at base; the empty-group param and the second pin PRD-mandated behavior base also had (a regression guard by design). | skills/use-qwen/scripts/test_eval_tree_archive_safety_modes.py | Bob, Eve, mech-check |
| R20 | [2/4] | 🟡 Medium | `test_build_template_cleanup_leaves_no_readonly_staging_survives` passes against base. **DISCARD as expected**: it covers the cleanup-succeeds branch; the never-lifts twin and the own-cause test pin the repair and fail at base. | skills/use-qwen/scripts/test_eval_tree_archive_staging.py | Bob, Eve, mech-check |
| R21 | [2/4] | 🟡 Medium | Eight host-link tests pass against base. **DISCARD as expected**: they are the refusal guards (base refused any backslash); the accept test and the `_HOST_SEP` default test fail at base. | skills/use-qwen/scripts/test_eval_tree_host_links.py | Bob, Eve, mech-check |
| R22 | [1/4] | 🟡 Medium | Six `test_eval_tree_links_typed.py` tests pass against base. **DISCARD as expected**: moved verbatim out of `test_eval_tree_links.py` (cycle-1 R4); the typing fix predates base. | skills/use-qwen/scripts/test_eval_tree_links_typed.py | Eve, mech-check |

## Prior-cycle status (cycle-1 rows)

Verified in code at `5b42fed` by Alice, Bob and Eve independently:

- R1 cleanup masking: resolved. `build_template` re-raises the original object;
  the cleanup failure is its `__context__`; `__cause__` is untouched.
- R2 and R9 chmod argv and locale decoding: resolved. One
  `git update-index --chmod=<flag> -z --stdin` call per non-empty group, paths
  NUL-delimited on stdin, tracked names read as bytes (`utf-8`,
  `surrogateescape`). The 1,200-path test asserts no member path on any argv.
- R3 and R5 cleanup tests: resolved. `excinfo.value is original` plus the
  exact `PermissionError` context; `__cause__` survival test added.
- R4 module size: resolved. `test_eval_tree_links.py` is 728 lines; the typing
  tests moved verbatim to `test_eval_tree_links_typed.py`.
- R10 repeated `getmembers`: resolved.
- R19 host-native link text: resolved at the host-read boundary
  (`_read_link`, identity on `/` hosts). `_archive_name_escapes`, `_land` and
  the member checks are unchanged; hostile backslash forms still refuse.
- Still deferred and untouched: R7, R8, R12, R13, R15, R18, R20, R26, R27.
  R23 (native Windows) is carried as R4 above.

## Alice

Native Claude Sonnet 5.5, high effort. Three Low rows; every cycle-1 target
verified resolved; no regression found. Seven archive and tree modules passed
on 3.13 with deprecations as errors (360 passed).

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

Native Claude Sonnet 5.5, high effort, PRD and test-gate line only. Five Low
rows that each note the code matches the spec outcome; cause-by-cause audit
found every PRD requirement implemented. Full output:
`docs/dev/tmp/blake-output-00162-20261108-c2.txt`. Blake could not run
Python 3.10 or 3.12; those rows rest on this session's runs above.

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

Codex dispatch refused before inference (exit 3, nested-dispatch guard). The
exact inlined prompt (design-document block excluded, PRD-only context) ran on
the Claude fallback, `autopilot:bob`, Sonnet 5.5, high effort. Six Low rows,
two FIX, one VERIFY, three KNOWN; no regression. This is not an independent
provider voice.

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

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

Unavailable: Copilot / `gemini-3.8-flash` helper exited 3 at its
nested-dispatch guard (`CODEX_SESSION_ID` set), before inference. Not exit 4,
so no batch latch was written. Carl is excluded from the completed-review
denominator. Dispatch row `a2cac3fc` closed as an error.

## Eve

Native Claude Fable, effort xhigh. Eight FIX, one VERIFY, seven KNOWN items
(sixteen input findings, D5 count holds), all absorbed above. The prior-cycle
repair targets were each checked against the code and pass. Both lenses and the
five doubt rules were retained. No implementation task used Codex in this lane,
so the guard did not fire; Eve ran because the handoff required her.

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

Verdict: 22 findings
Tests: 4529 passed, 0 failed, 9 skipped (suite run this cycle)
