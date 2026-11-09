---
prd: docs/dev/project-management/prds/wip/00131-crafted-template-archive-escapes-directory-v1.md
review: 2
date: 2026-10-30
head_sha: cc90677204e359229db731d212b78d4bc13360d7
codex_thread_id: 01a18b18-8e99-7e92-8f99-e4733df4144b
reviewers: alice,blake,bob
agents:
  alice: available
  blake: available
  bob: available
  carl: unavailable
dispatch_rows:
  bob: 7498f189
  carl: d043306f
---

# Review: 00131-crafted-template-archive-escapes-directory-v1 (cycle 2)

Diff range: `a5bd732a842505fb115b37e672e4e84179294909..cc90677204e359229db731d212b78d4bc13360d7`
(incremental: the rework commits of cycle 1, scoped with `--since` from the cycle-1 `head_sha`)

codex_rung_guard: not fired

pack: ok

## Review Summary

Reviewed: 4 completed tasks (2 original plan tasks, 2 cycle-1 rework tasks)
PRDs checked: 00131-crafted-template-archive-escapes-directory-v1.md

### Agent Status

- Alice: ✅ Available (consensus lens, engine `legacy`, incremental)
- Blake: ✅ Available (blind lens, PRD-only, no diff and no review history)
- Bob: ✅ Available (codex, doubt lens D1-D5 + de-slop, resumed cycle-1 thread `01a18b18`)
- Carl: ⚠️ Unavailable: gemini-run backend `copilot` model `gemini-3.8-flash` returned exit 1, "You have exceeded your monthly quota". Same monthly quota exhaustion as cycle 1, in the same calendar month, so no retry was dispatched: it would re-hit the identical quota ceiling. Exit 1, not exit 4, so Carl is still not latched unavailable for the batch.
- Eve: ⏸️ Disabled: resolved doubt reviewer is `codex` and no task was implemented by codex, so the codex doubt-roster guard did not fire.

Consolidation ran via `consolidate_findings.py` with `--ledger --ledger-dismiss BLAKE`.
Its paraphrase merge folded three citations in `test_eval_tree_links.py` onto row
R1 after suffix stripping (`:266` ~ `:490` ~ `:487`). One consequence is visible
and deliberate: Alice's separate 🟡 "the comment in the renamed compat test is
false" and Blake's 🟠 "task 2 has no warning-as-error check on the compatibility
path" were merged into R1, and their text no longer appears in the table. Both
are preserved verbatim in their sections below and must be addressed with R1.
Two Blake findings were auto-dismissed against the settled-decisions ledger;
they are listed at the end of the table section.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [2/3] | 🟠 | The rework adds three refusal paths with no test. Cycle-1 R1 asked for a hardlink test and an absolute-member test, and neither exists. (1) Non-file/dir/symlink members: `rg` for LNKTYPE, hardlink, absolute and FIFO in the test file finds nothing relevant. (2) The `os.path.isabs(member.name)` refusal (trees.py:143). (3) The landing-collision refusal (`alias -> pkg` plus `alias/file`, trees.py:161), which the docstring describes and which cycle-1 R8 and R6 substance was meant to carry. Add `_crafted_tar` cases for `LNKTYPE`, an absolute name and the alias collision. `_crafted_tar` currently only builds sym/dir/file members, so it needs a kind for a hardlink. Deleting lines 145-146 or 161-163 leaves the whole suite green. | skills/use-qwen/scripts/test_eval_tree_links.py:266 | 3 | ALICE, BLAKE |
| R2 | [1/3] | 🟠 | The compatibility branch is an unfiltered fallback. When `tarfile.data_filter` is missing, `build_template` calls bare `archive.extractall(dest)`. The PRD says "without an unfiltered fallback" and "missing runtime support must never silently select unrestricted extraction". The preflight does not check modes. Setuid and setgid bits, and any ownership or mode metadata a crafted tar carries, are applied unfiltered. The preflight does reject absolute names, non-file/dir/symlink types, duplicates and escaping links, but that is not equivalent to the data filter. The fallback should be a safe equivalent such as a manual filter, or a refusal with a TreeError. | skills/use-qwen/scripts/eval_harness/trees.py:180 | 1 | BLAKE |
| R3 | [1/3] | 🟠 | The compatibility path still raises the omitted-filter DeprecationWarning, which finding 42 requires removed. I ran `uv run pytest skills/use-qwen/scripts/test_eval_tree_links.py -q -W error::DeprecationWarning` on CPython 3.12.16. Two tests failed with the exact "Python 3.14 will, by default, filter extracted tar archives" warning raised from `trees.py:183`. They were `test_build_template_seals_a_safe_tree_with_or_without_tar_data_filter[without-data-filter]` and `test_build_template_s_compatibility_path_seals_a_safe_tree_regardless_of_the_omitted_filter_warning`. | skills/use-qwen/scripts/eval_harness/trees.py:183 | 2 | BLAKE |
| R4 | [1/3] | 🟠 | Symlink ancestors still permit a containment bypass. For `pkg/`, `alias -> pkg`, `alias/escape -> ../../outside`, and `pkg/escape/secret.txt`, the map records `alias/escape`, but `_land` looks up `pkg/escape` after resolving `alias`. The escaping target is missed; content-only landing checks do not catch it. Reject members beneath archive symlinks before extraction and add this regression on both branches. | skills/use-qwen/scripts/eval_harness/trees.py:152 | 3 | BOB |
| R5 | [1/3] | 🟡 | The compatibility-branch tests cannot show a safe fallback. They only seal benign trees with the filter hidden. No test shows that the crafted attack archives are refused, or that the sentinel is untouched, with `data_filter` hidden. The PRD asks for "both filter-support branches". The refusal tests run only on the standard path. | skills/use-qwen/scripts/test_eval_tree_links.py:371 | 1 | BLAKE |
| R6 | [1/3] | 🟡 | Prior R1's required hardlink and absolute-member regressions remain absent; the new unsupported-type refusal and landing-collision check also lack tests. Add isolated refusal cases for hardlinks, special members, absolute names, and colliding content paths; exercise the compatibility branch and verify unchanged outside state. | skills/use-qwen/scripts/eval_harness/trees.py:145 | 3 | BOB |
| R7 | [1/3] | 🟡 | Prior R2 remains incomplete: the replacement compatibility test removes warning verification entirely. The proxy still delegates extraction to modern tarfile, so it does not reproduce legacy warning behavior. Mechanical replay confirms this test passes against the previous implementation. Model legacy extraction faithfully and verify successful sealing with the specific omitted-filter warning treated as an error. | skills/use-qwen/scripts/test_eval_tree_links.py:487 | 4 | BOB, mech-check |
| R8 | [1/3] | 🟡 | `originals` duplicates every `member.name` solely to zip it back onto the same members. Remove the list and iterate `for member in members`, passing `member.name` directly to `_land` and diagnostics; this preserves raw-path validation with less bookkeeping. | skills/use-qwen/scripts/eval_harness/trees.py:141 | 3 | BOB |
| R9 | [1/3] | ⚪ | The landing-collision check skips symlink members (trees.py:159). A symlink `alias/ln` and a file `pkg/ln`, with `alias -> pkg`, are both accepted although they write the same path and extraction order decides which survives. I ran it and it was accepted. It is not an escape, because each link target was already resolved through `_land`. Recording it only because the docstring promises "two members that land in the same place" are refused. | skills/use-qwen/scripts/eval_harness/trees.py:159 | 3 | ALICE |

### Auto-dismissed (ledger)

- [BLAKE] 🟡 Ancestor-crossing members are only rejected when they escape or collide. `_refuse_duplicate_or_crossing_members` accepts a member like `alias/file` under `alias -> pkg` if no other member lands on `pkg/file`. The PRD says to reject member paths whose ancestors cross symlinks. The implementation instead resolves hop by hop and refuses only escapes, cycles and landing collisions. The safe-members control at skills/use-qwen/scripts/test_eval_tree_links.py:410 does not cover this. Containment holds, but the stated rule is weaker than the spec. | File: skills/use-qwen/scripts/eval_harness/trees.py:152 — single-voice. Same defect as cycle-1 R6 (see that ledger entry); the substance is carried into R4's fix task
- [BLAKE] ⚪ Duplicate detection uses `posixpath.normpath` on the name alone. On a case-insensitive filesystem such as macOS APFS, `Escape` and `escape` collide at extraction and are not seen as duplicates. This is outside the literal spec but fits the stated risk of "duplicate normalization". | File: skills/use-qwen/scripts/eval_harness/trees.py:147 — single-voice. Nobody executed the claimed collision, so it stands as an unverified bypass vector on a case-insensitive host. Re-raise with a demonstrated case if it recurs

## Mechanical checks

- Tautological test shapes: 18 test functions checked in 1 test file, no `[MECH]` line raised.
- Fail-first replay: one `[MECH]` 🟡 line — 3 touched tests pass against the pre-change code at `a5bd732a8425` (`test_build_template_seals_a_safe_tree_with_or_without_tar_data_filter`, `test_build_template_s_compatibility_path_seals_a_safe_tree_regardless_of_the_omitted_filter_warning`). Absorbed into R7, which names the same compatibility test and the same replay result; R7's finders therefore carry `mech-check`.
- Carry-forward: cycle 1 wrote no verification-check queue (`...-checks-1.json` absent), so nothing was carried forward.

## Alice

Cycle 2 incremental review of 00131, HEAD cc90677. Narrow run of `test_eval_tree_links.py`: 55 passed, 2 warnings. She did not rerun the full suite.

Prior findings, checked against the code:

- Cycle-1 R1 (hardlink and other member types): the code is fixed. A hardlink and a FIFO each raise `TreeError("... is not a file, directory or symlink")`, and an absolute name raises `TreeError("... is absolute")`. Both branches now refuse these before extraction. No test covers any of these refusals, including the `os.path.isabs` one, which cycle 1 asked for by name.
- Cycle-1 R2 (compat-path warning test): resolved. `trees.tarfile` is wrapped by `_hide_data_filter`, the test seals the tree and asserts the sha and link text, and it no longer expects the warning. It still carries a wrong comment.
- Cycle-1 R3 (tests that pass against base): resolved. The new `file-whose-own-path-crosses-a-symlink-that-is-safe-alone` case in `ANCESTOR_CROSSINGS` (test_eval_tree_links.py:310) fails at base. Base normalizes `alias/../outside/secret.txt` to `outside/secret.txt`, which passes the preflight, and then `filter="data"` raises a tarfile `FilterError`, not `TreeError`.
- Cycle-1 R4 (normalizing before `_land`): fixed in code. `_land` now walks the original `member.name` (trees.py:155). The regression covers the data-filter branch only. The refusal happens before the extract call, so branch choice does not change it.
- Cycle-1 R5 (CHANGELOG): the deferral stands. The rework did not touch CHANGELOG.md, as expected.

The `alias -> pkg` plus `alias/file` landing-collision refusal (trees.py:161) is new code from the rework; she confirmed it refuses (`alias/file is a duplicate member`).

[ALICE] 🟠 The rework adds three refusal paths with no test. Cycle-1 R1 asked for a hardlink test and an absolute-member test, and neither exists. (1) Non-file/dir/symlink members: `rg` for LNKTYPE, hardlink, absolute and FIFO in the test file finds nothing relevant. (2) The `os.path.isabs(member.name)` refusal (trees.py:143). (3) The landing-collision refusal (`alias -> pkg` plus `alias/file`, trees.py:161), which the docstring describes and which cycle-1 R8 and R6 substance was meant to carry. Add `_crafted_tar` cases for `LNKTYPE`, an absolute name and the alias collision. `_crafted_tar` currently only builds sym/dir/file members, so it needs a kind for a hardlink. Deleting lines 145-146 or 161-163 leaves the whole suite green. | File: skills/use-qwen/scripts/test_eval_tree_links.py:266 | Task: 3

[ALICE] 🟡 The comment in the renamed compat test is false. It says the omitted-filter warning does not fire on this runtime "(verified empirically)", and that "the warning text was retired once 3.14 made the default filter effective". The pytest warnings summary for this very test shows `trees.py:183: DeprecationWarning: Python 3.14 will, by default, filter extracted tar archives...`. On the pinned 3.12 the warning does fire when `data_filter` is hidden. The comment should say the warning's presence varies by runtime and the test deliberately asserts neither way. The assumptions log entry says the opposite: "real (on Python 3.13)". The ledger and the test comment now disagree. | File: skills/use-qwen/scripts/test_eval_tree_links.py:490 | Task: 4

[ALICE] ⚪ The landing-collision check skips symlink members (trees.py:159). A symlink `alias/ln` and a file `pkg/ln`, with `alias -> pkg`, are both accepted although they write the same path and extraction order decides which survives. I ran it and it was accepted. It is not an escape, because each link target was already resolved through `_land`. Recording it only because the docstring promises "two members that land in the same place" are refused. | File: skills/use-qwen/scripts/eval_harness/trees.py:159 | Task: 3

R1: fail
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

[BLAKE] 🟠 The compatibility branch is an unfiltered fallback. When `tarfile.data_filter` is missing, `build_template` calls bare `archive.extractall(dest)`. The PRD says "without an unfiltered fallback" and "missing runtime support must never silently select unrestricted extraction". The preflight does not check modes. Setuid and setgid bits, and any ownership or mode metadata a crafted tar carries, are applied unfiltered. The preflight does reject absolute names, non-file/dir/symlink types, duplicates and escaping links, but that is not equivalent to the data filter. The fallback should be a safe equivalent such as a manual filter, or a refusal with a TreeError. | File: skills/use-qwen/scripts/eval_harness/trees.py:180 | Task: 1

[BLAKE] 🟠 The compatibility path still raises the omitted-filter DeprecationWarning, which finding 42 requires removed. I ran `uv run pytest skills/use-qwen/scripts/test_eval_tree_links.py -q -W error::DeprecationWarning` on CPython 3.12.16. Two tests failed with the exact "Python 3.14 will, by default, filter extracted tar archives" warning raised from `trees.py:183`. They were `test_build_template_seals_a_safe_tree_with_or_without_tar_data_filter[without-data-filter]` and `test_build_template_s_compatibility_path_seals_a_safe_tree_regardless_of_the_omitted_filter_warning`. | File: skills/use-qwen/scripts/eval_harness/trees.py:183 | Task: 2

[BLAKE] 🟠 Task 2 has no check that treats the omitted-filter warning as an error on the compatibility path. Only the data_filter path is covered, at skills/use-qwen/scripts/test_eval_tree_links.py:462. The compatibility-path test makes no warning assertion. Its comment says the warning does not fire on this runtime, "verified empirically". That is false: it fires on 3.12.16, as shown above. The comment misleads. | File: skills/use-qwen/scripts/test_eval_tree_links.py:487 | Task: 2

[BLAKE] 🟡 Ancestor-crossing members are only rejected when they escape or collide. `_refuse_duplicate_or_crossing_members` accepts a member like `alias/file` under `alias -> pkg` if no other member lands on `pkg/file`. The PRD says to reject member paths whose ancestors cross symlinks. The implementation instead resolves hop by hop and refuses only escapes, cycles and landing collisions. The safe-members control at skills/use-qwen/scripts/test_eval_tree_links.py:410 does not cover this. Containment holds, but the stated rule is weaker than the spec. | File: skills/use-qwen/scripts/eval_harness/trees.py:152 | Task: 1

[BLAKE] 🟡 The compatibility-branch tests cannot show a safe fallback. They only seal benign trees with the filter hidden. No test shows that the crafted attack archives are refused, or that the sentinel is untouched, with `data_filter` hidden. The PRD asks for "both filter-support branches". The refusal tests run only on the standard path. | File: skills/use-qwen/scripts/test_eval_tree_links.py:371 | Task: 1

[BLAKE] ⚪ Duplicate detection uses `posixpath.normpath` on the name alone. On a case-insensitive filesystem such as macOS APFS, `Escape` and `escape` collide at extraction and are not seen as duplicates. This is outside the literal spec but fits the stated risk of "duplicate normalization". | File: skills/use-qwen/scripts/eval_harness/trees.py:147 | Task: 1

What he found satisfied: duplicate-member and reversed-order refusal with parametrized crafted-archive tests and an outside sentinel; preserved escaping-chain and cycle refusal; benign link sealing; a TreeError raised before `init` with `dest` left empty; the `filter="data"` path, which is warning-free. A run of the file without `-W error` passed 55 tests apart from the two failures above.

B1: fail
B2: pass
B3: pass
B4: pass
B5: pass
B6: pass
B7: pass
B8: pass
B9: pass
B10: fail
B11: pass
B12: pass
B13: pass
B14: fail
B15: fail
B16: pass
B17: pass
B18: pass
B19: pass

## Bob

FIX:

- [BOB] 🟠 Symlink ancestors still permit a containment bypass. For `pkg/`, `alias -> pkg`, `alias/escape -> ../../outside`, and `pkg/escape/secret.txt`, the map records `alias/escape`, but `_land` looks up `pkg/escape` after resolving `alias`. The escaping target is missed; content-only landing checks do not catch it. Reject members beneath archive symlinks before extraction and add this regression on both branches. | File: skills/use-qwen/scripts/eval_harness/trees.py:152 | Task: 3
- [BOB] 🟡 Prior R1's required hardlink and absolute-member regressions remain absent; the new unsupported-type refusal and landing-collision check also lack tests. Add isolated refusal cases for hardlinks, special members, absolute names, and colliding content paths; exercise the compatibility branch and verify unchanged outside state. | File: skills/use-qwen/scripts/eval_harness/trees.py:145 | Task: 3
- [BOB] 🟡 Prior R2 remains incomplete: the replacement compatibility test removes warning verification entirely. The proxy still delegates extraction to modern tarfile, so it does not reproduce legacy warning behavior. Mechanical replay confirms this test passes against the previous implementation. Model legacy extraction faithfully and verify successful sealing with the specific omitted-filter warning treated as an error. | File: skills/use-qwen/scripts/test_eval_tree_links.py:487 | Task: 4
- [BOB] 🟡 `originals` duplicates every `member.name` solely to zip it back onto the same members. Remove the list and iterate `for member in members`, passing `member.name` directly to `_land` and diagnostics; this preserves raw-path validation with less bookkeeping. | File: skills/use-qwen/scripts/eval_harness/trees.py:141 | Task: 3

VERIFY:

- (none)

KNOWN:

- (none)

R1: fail
R2: fail
R3: pass
R4: fail
R6: pass
R7: fail
R8: pass
R9: fail
R10: fail
R11: pass
R12: pass
R13: pass

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

Carl: unavailable (gemini-run backend `copilot`, model `gemini-3.8-flash`, exit 1: "You have exceeded your monthly quota"). No output file was published; nothing was consolidated for him. Not exit 4, so Carl is not latched unavailable for the batch.

## Decision gate (cycle 2)

Not converged: R1, R2, R3 and R4 are unresolved HIGH findings, and none of them
matches a settled deferral. No CRITICAL row, so no rework design and no
`cap_critical` stall applies.

`state.cycle` is 2 and `state.rework_cap` is 2, so `cycle >= cap`: the rework
cap is reached and this is the loop-mode cap-out path, which defers rather than
pausing. `autopilot cap-check --review-file ...-review-2.md --previous
...-review-1.md` exited 0 and classified all four HIGH rows `"regression":
false`, so the `cap_regression` stall does not apply either.

Every unresolved finding of this cycle — the four HIGH rows and the five
medium/low rows the cap-out leaves with no rework pass — is recorded in
`state.deferred_decisions` as a `cap-overflow` record carrying its ref,
severity, consensus, file and reason. Nine records in total. No task was
created; the PRD proceeds to the finalize session as converged-with-deferrals
and the findings stay visible at batch end.

Safety checks: issue count fell from 12 to 9, so the steady-cycle row does not
fire. Follow-ups are under 10, so no scope alarm. Carl's second consecutive
quota failure is the transient-reviewer row: logged, cycle completed on the
three remaining lenses.

Verdict: 9 findings
Tests: 4253 passed, 9 skipped (suite run this cycle at cc90677, exit 0; counts read from docs/dev/tmp/gate-00131-c2.log because the verify parser does not recognise this pytest summary form)
