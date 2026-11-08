---
prd: docs/dev/project-management/prds/wip/00162-template-archive-breaks-on-windows-v1.md
review: 1
date: 2026-11-08
head_sha: 73386d63132c1a9f10a710e8bf9bbafe593c987a
reviewers: alice,blake,bob,eve
agents:
  alice: available
  blake: available
  bob: available
  carl: unavailable
  eve: available
dispatch_rows:
  bob: 2bfa16d6
  carl: f0e10492
---

# Review: 00162 Windows archive lane

Diff range: `78eec8e04e87b498acf8e1dad5002b6b642ba8e0..73386d63132c1a9f10a710e8bf9bbafe593c987a`

codex_rung_guard: not fired

**REWORK REQUIRED; degraded reviewer roster.** Three unresolved HIGH product
findings and one verified MEDIUM product finding remain. No CRITICAL finding.
This report does not approve the lane or the combined candidate. All eight
stored tasks were complete before review. This is cycle 1, with the existing
two-cycle cap preserved. No implementation changed during review, and no
follow-up tasks were created by the review skill. The next session must run
the decision gate and bounded rework before another fresh review.

The installed autopilot 0.10.0 `review-stage` runtime staged this review with
the explicit lane state and all five requested personas. The context pack
failed because the worktree is not registered with gita; the documented
no-pack sentinel was used. Alice and Blake ran in separate native Claude CLI
sessions on `claude-sonnet-5-5`, high effort. Eve ran on `claude-fable-5-1`,
high effort. Transcript model fields verified these identities. Native Task
reviewers are unavailable in this host, so isolated CLI sessions served as
the host adapter. Blake received the PRD and gate result, with explicit
instructions to exclude designs, review history, task narratives and ledgers.
Every reviewer test command used an isolated environment.

Bob and Carl's helpers both returned exit 3 before inference: `refusing nested
dispatch (already inside a CLI agent)`. No guard was bypassed and neither
route was retried unchanged. Bob's exact inlined doubt/de-slop prompt ran via
the prescribed Anthropic fallback, `claude-sonnet-5-5`, high effort. The
design-document block was excluded from his inlined context for the doubt
lens. Carl's requested backend/model was Copilot / `gemini-3.8-flash`; it did
not run. No Codex thread ID exists. Both failed CLI dispatch rows were closed
as errors. No independent provider reviewer inference ran in this cycle.
Repeat the full roster from a host that supports the permitted dispatches
after rework; do not treat this degraded cycle as lane approval.

## Evidence

- Full adapter gate at the reviewed SHA, Python 3.13.18: **4511 passed,
  0 failed, 9 skipped**, 380.84 seconds. The installed verifier wrote its
  record while the source tree was clean. Log:
  `docs/dev/tmp/gate-00162-20261108.log`.
- Five archive modules on isolated Python 3.10 and 3.12, with
  `-W error::DeprecationWarning`: **342 passed each**, 48.06 and 48.04 seconds.
  Evidence: `docs/dev/tmp/00162-python-matrix-20261108.md`.
- Alice independently passed 157 tests on Python 3.13 with deprecations as
  errors. Blake and Eve each passed the staging module on Python 3.10
  (39 tests); Eve also passed all five modules on Python 3.12 (342 tests).
- Eve's explicit Python 3.13 safety/staging follow-up passed **179 tests**
  with deprecations as errors in 20.26 seconds; check queue result is exit 0.
- `docs/dev/tmp/probe-00162-review.py` reproduced cleanup error masking,
  a 44,043-character Windows command line for 1,000 ordinary paths, and a
  non-ASCII executable name remaining `100644` when subprocess text decoding
  uses CP1252. These are local simulations, not native Windows runs.
- A separate read-back probe replaced `os.readlink` output `pkg/a.txt` with
  `pkg\a.txt`; `fresh_clone` raised `TreeError` before copying. `_land`
  passes that raw text to `_archive_name_escapes`, which rejects backslashes.
- The command-line finding is supported by Microsoft's
  [CreateProcessW contract](https://learn.microsoft.com/en-us/windows/desktop/api/processthreadsapi/nf-processthreadsapi-createprocessw),
  which limits a command line to 32,767 characters including its terminator.
- Live braid check from main: 140 current, 20 ignored, zero drift. Running
  the lane against live configuration encountered duplicate source names;
  a disposable lane-only configuration then synced and checked successfully:
  80 current, 20 ignored, zero drift. No live links changed.
- `git diff --check` passed. No source or test changes were made. AST
  measurement puts `build_template` at lines 330–376: **47 lines**, refuting
  Alice's 95-line claim.

## Consolidated Findings

The installed consolidator ran over all four completed outputs. The table
below retains its original R1–R18 identities, corrects citations, and adds
Eve's bucket-only findings and every mechanical row. Duplicate findings remain
visible with explicit dispositions. Mechanical evidence does not count as an
additional model vote. Raw outputs remain in
`docs/dev/tmp/<persona>-output-00162-20261108.txt`.

| Ref | Consensus | Severity | Issue | File | Found By |
|---|---|---|---|---|---|
| R1 | [4/4] | 🟠 High | Cleanup failure replaces the original build exception. **FIX**: preserve the original as the raised exception, with cleanup failure chained. | skills/use-qwen/scripts/eval_harness/trees.py:373 | Alice, Blake, Bob, Eve |
| R2 | [3/4] | 🟠 High | Unbounded path argv exceeds the Windows process limit. **FIX**: send NUL-delimited paths through stdin, preserving one call per mode group. | skills/use-qwen/scripts/eval_harness/trees.py:327 | Alice, Bob, Eve |
| R3 | [3/4] | 🟡 Medium | New cleanup tests accept either exception order and broad exception classes. **FIX with R1**: assert original-error identity and separately assert the cleanup cause. Absorbs mechanical flags at lines 408 and 433. | skills/use-qwen/scripts/test_eval_tree_archive_staging.py:408 | Alice, Bob, Eve, mech-check |
| R4 | [2/4] | 🟡 Medium | Link test module grew to 933 lines. **FIX**: extract the new typing tests with shared fixtures retained. | skills/use-qwen/scripts/test_eval_tree_links.py:933 | Alice, Bob |
| R5 | [1/4] | 🟠 High | Twin cleanup test does not enforce the PRD's exception order. **DISCARD duplicate of R3**, not a separate unresolved HIGH. | skills/use-qwen/scripts/test_eval_tree_archive_staging.py:416 | Blake |
| R6 | [1/4] | 🟡 Medium | Clone symlink failures are not wrapped as TreeError. **DISCARD**: no uniform clone-error type is specified; the former copytree path also surfaced filesystem errors. No demonstrated behavioral regression. | skills/use-qwen/scripts/eval_harness/trees.py:422 | Alice |
| R7 | [1/4] | 🟡 Medium | Cleanup does not repair POSIX read-only parent directories. **DEFER hardening**: normal extraction/git staging does not create such directories; clarify any broader task prose when repairing R1. | skills/use-qwen/scripts/eval_harness/trees.py:388 | Alice |
| R8 | [1/4] | 🟡 Medium | Cleanup retries every rmtree error with chmod, including unrelated failures. **DEFER hardening**; R1 must preserve the original exception for these failures too. | skills/use-qwen/scripts/eval_harness/trees.py:388 | Blake |
| R9 | [2/4] | 🟡 Medium | Locale-decoded tracked names can mismatch archive Unicode names and silently skip chmod. **FIX**: use byte output with explicit UTF-8/surrogateescape decoding; CP1252 probe reproduced the lost bit. | skills/use-qwen/scripts/eval_harness/trees.py:320 | Bob, Eve |
| R10 | [2/4] | ⚪ Low | Manual extraction calls getmembers again despite an existing members list. **FIX adjacent to rework**; downgraded from MEDIUM because getmembers is cached and this is redundancy, not a runtime defect. | skills/use-qwen/scripts/eval_harness/trees.py:361 | Bob, Eve |
| R11 | [1/4] | ⚪ Low | Claimed 95-line build_template function. **DISCARD**: AST proves 47 lines, within the rubric limit. | skills/use-qwen/scripts/eval_harness/trees.py:330 | Alice |
| R12 | [1/4] | ⚪ Low | Two cleanup-test names are awkward. **DEFER cosmetic naming**; improve while changing those tests if useful. | skills/use-qwen/scripts/test_eval_tree_archive_staging.py:391 | Alice |
| R13 | [1/4] | ⚪ Low | Internal helper names/signatures differ across PRD, design and code. **DEFER documentation reconciliation**; exported signatures are unchanged and the implementation decision is recorded. | skills/use-qwen/scripts/eval_harness/trees.py:379 | Alice |
| R14 | [1/4] | ⚪ Low | PRD names _remove_staging while code names _remove_tree. **DISCARD duplicate of R13**. | skills/use-qwen/scripts/eval_harness/trees.py:379 | Blake |
| R15 | [1/4] | ⚪ Low | Ignored archive members are excluded from the chmod groups. **DEFER inherited seal-contract gap**: git add -A already omitted such members before this lane; preserve the guard against chmod on untracked paths until that contract is resolved. | skills/use-qwen/scripts/eval_harness/trees.py:321 | Blake |
| R16 | [1/4] | ⚪ Low | POSIX parent-directory permissions are not repaired. **DISCARD duplicate of R7**. | skills/use-qwen/scripts/eval_harness/trees.py:388 | Bob |
| R17 | [1/4] | 🟡 Medium | Fifty touched mode/owner cases pass against base. **DISCARD as expected backfill**: Phase 2 preserves POSIX assertions; the separate core.filemode=false regression pins the product fix. Absorbs the mechanical modes replay row. | skills/use-qwen/scripts/test_eval_tree_archive_safety_modes.py:140 | Bob, mech-check |
| R18 | [1/4] | ⚪ Low | Prefix helper is imported inside a test to avoid a circular import. **DEFER test organization**; no incorrect result demonstrated. | skills/use-qwen/scripts/test_eval_tree_state.py:569 | Bob |
| R19 | [1/4] | 🟠 High | Host-native link text containing backslashes is rejected by containment readers. **FIX** the host-read/archive-input boundary with regression coverage; preserve hostile archive-input refusal. | skills/use-qwen/scripts/eval_harness/trees.py:303 | Eve |
| R20 | [1/4] | 🟡 Medium | Existing staging test hedges with reached-is-None-or-reached; older exception alternatives also remain. **DEFER inherited test hardening**: line 266 predates this lane. This retains the first mechanical tautology flag. | skills/use-qwen/scripts/test_eval_tree_archive_staging.py:266 | Eve, mech-check |
| R21 | [1/4] | 🟡 Medium | Seven touched link cases pass against base. **DISCARD as expected host-neutral backfill**: prefix fixtures already pass on POSIX; Phase 0 typing regressions are distinct. | skills/use-qwen/scripts/test_eval_tree_links.py | mech-check |
| R22 | [1/4] | 🟡 Medium | Three touched state cases pass against base. **DISCARD as expected host-neutral backfill**: normalization preserves existing POSIX fixture behavior. | skills/use-qwen/scripts/test_eval_tree_state.py | mech-check |
| R23 | [1/4] | 🟡 Medium | Native Windows behavior still needs exact-candidate CI. **VERIFY later** after combined integration and the existing push/dispatch approvals; not queued as a local check. | skills/use-qwen/scripts/eval_harness/trees.py:303 | Eve |
| R24 | [1/4] | ⚪ Low | Explicit Python 3.13 deprecation-error check requested for safety/staging modules. **RESOLVED**: 179 passed, exit 0; exact isolated command and result are in the check queue. | skills/use-qwen/scripts/test_eval_tree_archive_staging.py | Eve |
| R25 | [1/4] | ⚪ Low | The non-executable chmod group is often redundant. **DISCARD as mandated behavior**: the PRD explicitly requires both groups. | skills/use-qwen/scripts/eval_harness/trees.py:325 | Eve |
| R26 | [1/4] | ⚪ Low | Generic rmtree callback assumes a single-argument callable and may mishandle open/scandir errors. **DEFER with R8**: unreadable directories are outside normal staging construction. | skills/use-qwen/scripts/eval_harness/trees.py:390 | Eve |
| R27 | [1/4] | ⚪ Low | Links retain archive order instead of target-first order. **DEFER specification reconciliation**: explicit type from full-chain landing supplies the required Windows type without depending on creation order. | skills/use-qwen/scripts/eval_harness/trees.py:296 | Eve |

## Repair constraints and adjudication

R19 is not resolved by lane 00164 at `b8db11f`: that lane additionally converts
clone link text, but does not change `_land`'s raw-text rejection. Eve's proposed
remedy to drop native-separator conversion conflicts with 00164's recorded
native Windows chain failure. Preserve that evidence and normalize host-read
text at an appropriate boundary, retaining archive-domain escape rejection.
Do not simply relax `_archive_name_escapes` or remove Windows typing assertions.
Prove the repaired build/clone/read-through sequence on both filter seams and
retain POSIX assertions. Review the later combined archive tree separately.

The R1 design narrative contradicts the PRD. The PRD wins: re-raise the original
error, retain cleanup details as a cause, and change the tests to pin that
identity. Eve's suggestion to narrow the twin test to either PermissionError
or the original type is insufficient by itself; it must assert the original
exception object. These are coordinator adjudications, not edits to reviewer
output or acceptance criteria.

Bob's Unicode VERIFY prose did not name an exact runnable command, so it was
not queued. The coordinator resolved it with the retained CP1252 probe.
R23 cannot be resolved by rerunning pytest on macOS; native hosted evidence
remains required. No remote action was taken.

The deferred rows above remain durable here for the decision gate; they are
not new cap-overflow records or invented task completion. Original archive
reviews, held 00160, its 29 deferred rows and ledger keys remain unchanged.
Archive repair `3d65a2f` remains the future archive integration input. PRD
00133 and its main store remain untouched.

## Alice

Native Claude Sonnet 5.5, high effort; usable consensus review. Her cleanup and
argv findings are supported. The function-size claim is rejected by AST data.
Her raw rubric verdicts are retained; rejecting that finding does not rewrite
her output.

R1: pass
R2: fail
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: fail
R10: pass
R11: pass
R12: fail
R13: fail

## Blake

Native Claude Sonnet 5.5, high effort; PRD-only blind review. Found the
cleanup-contract failure independently. B1 and B5 fail; B2–B4 and B6–B19 pass.
Full output: `docs/dev/tmp/blake-output-00162-20261108.txt`.

## Bob

Codex dispatch refused before inference. Native Claude Sonnet 5.5 ran the exact
inlined prompt at high effort. Found the cleanup, argv, test, file-size and
encoding gaps. FIX/VERIFY/KNOWN buckets and all doubt verdicts are present.
The raw D3 verdict does not make his vague Unicode check a queueable command.

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

Unavailable: Copilot / gemini-3.8-flash helper exited 3 at its nested-dispatch
guard, before inference. No batch-permanent-unavailability latch was written:
exit 3 is not exit 4. Carl is excluded from the completed-review denominator.

## Eve

Native Claude Fable 5.1, high effort. Seven FIX, two VERIFY, four KNOWN items
were all absorbed above, including the separator/containment incompatibility.
Both lenses and the five doubt rules were retained. No implementation task
used Codex in this lane, so the guard did not fire; Eve ran because the handoff
explicitly required her.

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

Verdict: 27 findings
Tests: 4511 passed, 0 failed, 9 skipped (suite run this cycle)
