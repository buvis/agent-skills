---
prd: docs/dev/project-management/prds/wip/00014-braid-check-reports-and-state-writes-fail-clean-v1.md
review: 1
date: 2026-10-05
head_sha: d5d256256cbd6388d655bdb308bcb74945c36bfb
codex_thread_id: 01a10bf4-26a4-7133-9c2a-9d55d1b92135
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00014-braid-check-reports-and-state-writes-fail-clean-v1

Diff range: `73a095373aa931dbad95e432c69d75184a3ddc1e..4e2de33a6ebc533101b01478336f1923ec0968e4`

codex_rung_guard: not fired

scope: the work is one commit on `master`, `4e2de33`. HEAD at review time was `d5d2562`, two commits
later (`bf4f8d2`, a convert-to-icon feature, and `d5d2562`, the PRD's move from hold to wip). Both are
unrelated and were excluded: `gather-context.sh --since 73a0953` diffs against the work tree, so its
diff file was regenerated as `git diff 73a0953 4e2de33` and the context's changed-file block corrected
to the four files of that commit. Neither later commit touches `src/agent_skills_braid/cli.py`,
`tests/test_braid.py` or `README.md`, so reviewers reading the tree saw the reviewed code.

standalone: this PRD never ran under autopilot. `docs/dev/project-management/autopilot/state.json`
exists but belongs to a different PRD (00068, phase `review`, cycle 1), so it was neither read for
this review's tasks, lenses or guards nor written. Consequences, each by the skill's standalone rules:
no task records (the context lists the PRD's own five tasks, all folded into `4e2de33`), no
`task-add`, no verification-check queue, no lens roster stamp, no doubt-verdict record, no contract
card or session brief (writing them would overwrite 00068's). The codex doubt-roster guard had no
attempts record for this PRD to consult, hence `not fired`; who implemented `4e2de33` is not recorded
anywhere this review could read.

pack: failed (`engram pack` exited 1: "not inside a registered repo; register it in
~/.config/gita/repos.csv"). The registry was checked and does not list this repo, so the one
permitted retry was skipped as pointless. Every prompt that takes `{PACK_FILE}` or `{PACK_FINDINGS}`
received the sentinel `(no pack available this cycle)`. Degraded, not invalid.

## Review Summary

Reviewed: the PRD's 5 tasks, delivered as 1 commit (`4e2de33`)
PRDs checked: 00014-braid-check-reports-and-state-writes-fail-clean-v1

### Agent Status

- Alice: ✅ Available (Claude subagent, consensus lens)
- Blake: ✅ Available (Claude subagent, blind lens, PRD-only)
- Bob: ✅ Available (codex, doubt lens D1-D5 plus de-slop, first run, no retry needed)
- Carl: ✅ Available (gemini via `copilot` backend, model `gemini-3.8-flash`, generalist; no frontend surface)

Eve did not run: `doubt_reviewer` is absent from the PRD frontmatter (resolves to `codex`) and the
guard did not fire.

## Consolidated Findings

Consolidated by `consolidate_findings.py` (script, not model-side). 14 rows.

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [3/4] | 🟡 | tests/test_braid.py is now 801 lines (about 712 before this commit), over the 800-line limit; the commit pushed it over. Move the three drift-reporting groups (orphan, hand-changed, state-write tests) to a new tests/test_braid_check.py, reusing the helpers via a conftest or import | tests/test_braid.py:801 | 5 | ALICE, BOB, CARL |
| [3/4] | 🟡 | `run` grew from 71 to 85 lines (limit 50) and `_sync_links` from 58 to 62. Most of the growth is the `previous_claude`/`previous_kiro` locals plus the `orphan_scans` list built inline in `run`. Extract a small helper (for example `_orphan_scan_plan(...)`, or pass `previous` into one helper) so `run` does not grow further; the scan lists are also built in Mode.SYNC and never used there | src/agent_skills_braid/cli.py:528 | 4 | ALICE, BOB, CARL |
| [3/4] | 🟡 | Verdict on the declared deviation: it is better than the PRD wording, not a defect. The code resolves only `target.parent` and re-appends `target.name` (cli.py:459). The PRD's full `_resolved(target)` follows the last hop. Concrete case where they differ: after the state is lost, a Claude-root link `skills/temporary -> <agents>/skills/temporary` still has its union link in place. Full resolution follows that union link into `<source>/skills/temporary`, which is outside the owner root (the union), so the Claude orphan would go unreported. Yet `test_check_leaves_the_orphan_link_it_reports_on_disk` requires both the union and the Claude orphan to be reported, so literal PRD wording could not satisfy the PRD's own test. A second case: a union link to a source skill later replaced by a symlink to elsewhere is still caught by parent-resolution, and missed by full resolution. I found no case where the deviation produces a false positive: a link aimed outside every owner root is classified identically, and the negative test pins it. Update the PRD wording or leave the code comment at cli.py:457 as the record | src/agent_skills_braid/cli.py:459 | 4 | ALICE, BLAKE, BOB |
| [2/4] | 🟡 | The orphan scan's new behaviour is only partly pinned. Positive tests cover Mode.CHECK on the union and Claude roots only. Mode.DRY_RUN orphan reporting has no test, so changing the gate `settings.mode is not Mode.SYNC` to `is Mode.CHECK` would pass the suite. A Kiro-root orphan is never asserted positively either; the Kiro scan is covered only by the `drift == 0` line added to the plugin-owned test. Add a DRY_RUN case (parametrize the orphan test over DRY_RUN and CHECK) and one Kiro orphan case | tests/test_braid.py:303 | 5 | ALICE, BOB |
| [2/4] | ⚪ | `_write_state`: when the failure is that `path.parent` is a regular file (`mkdir` raises FileExistsError), the `finally` `temporary.unlink(missing_ok=True)` raises NotADirectoryError, because `missing_ok` only swallows FileNotFoundError (confirmed by running it). That replaces the BraidError with a raw traceback, which is the defect this PRD fixes, in a narrow case. Move `mkdir` before the `try`, or catch OSError around the unlink | src/agent_skills_braid/cli.py:413 | 1 | ALICE, BLAKE |
| [1/4] | 🟠 | FIX: Cleanup can mask the intended BraidError: if the temporary path is a directory, both write_text and finally-unlink fail, and entrypoint emits a traceback. Catch cleanup OSError explicitly, preserve the write failure, and test this case. | src/agent_skills_braid/cli.py:413 | 1 | BOB |
| [1/4] | 🟡 | The orphan scan also covers the enrolled Kiro skills root (`orphan_scans.append((kiro.root / "skills", [union_root], ...))`). The spec names only `<agents-root>/skills` and `<claude-root>/skills` as scanned roots. On Kiro-enrolled machines this adds MISMATCH ORPHAN lines and drift counts the PRD never defined, and no test covers it. | src/agent_skills_braid/cli.py:595 | Phase 2 | BLAKE |
| [1/4] | 🟡 | FIX: Documentation says sync refuses hand-replaced recorded links generally, but that applies only to stale names; desired names are backed up and relinked. Qualify the description with “no longer desired,” including the corresponding changelog claim. | README.md:210 | 2 | BOB |
| [1/4] | 🟡 | Duplicate setup in test_check_reports_a_hand_changed_managed_path_instead_of_aborting can reuse change_a_managed_path_by_hand | tests/test_braid.py:359 | 2 | CARL |
| [1/4] | ⚪ | `_report_orphan_links` tests `path.is_symlink()`, so an orphan NTFS junction (the Windows fallback that `_points_to` and `_remove_owned_link` handle) is never reported. The PRD and README say "symlink", so this is a documented limit, not a spec breach; mention it in the README if it is intended | src/agent_skills_braid/cli.py:452 | 4 | ALICE |
| [1/4] | ⚪ | The failed-state-write test checks only for a `BraidError` and no leftover `.tmp` file. The spec's error case also requires `entrypoint()` to exit 2 with the `braid: cannot write Braid state ...` message, and that path has no regression test. | tests/test_braid.py:412 | 0 | BLAKE |
| [1/4] | ⚪ | Orphan scan has no test in `Mode.DRY_RUN`. `_report_orphan_links` also calls `os.readlink` and `iterdir` without OSError handling, which would escape `entrypoint()` as a traceback. `path.is_symlink()` is false for Windows junctions, so junction orphans go undetected. | src/agent_skills_braid/cli.py:451 | 2 | BLAKE |
| [1/4] | ⚪ | KNOWN: Replay reports four passing-before tests: outside-root exclusion, wanted-link exclusion after state loss, sync refusal, and Kiro clean-state checking. These intentionally preserve existing behavior, so retain them; they do not satisfy the rubric’s literal fail-first requirement. | tests/test_braid.py:324 | general | BOB, mech-check |
| [1/4] | ⚪ | Cannot statically verify: VERIFY that `uv run pytest tests -q` passes with no failures, skips, xfails, or xpasses at the reviewed commit. | N/A | 5 | BOB |

No 🔴 Critical. One 🟠 High (single reviewer at that severity), seven 🟡 Medium, six ⚪ Low.

Where the table misleads, because the consolidator matches on file and wording:

- **Rows 5 and 6 are one defect.** Alice, Blake and Bob each found that the `finally` unlink in
  `_write_state` can raise and replace the `BraidError`. Real agreement is 3/4. They split on
  severity: Bob 🟠, Alice and Blake ⚪.
- **Row 3 merged opposite conclusions under Alice's wording.** Alice and Blake (and Carl, in prose
  above his issue lines) judge the deviation better than the PRD text. Bob agrees for the Claude and
  Kiro projections but raised a 🟡 FIX for the union scan: a union link aimed at a symlink that sits
  inside a source's `skills/` and leads outside is reported as an orphan, where the PRD's full
  resolution would leave it alone. His line is in his section below.
- **Row 1 absorbed Bob's duplicate-setup line, row 9 is Carl's copy of it.** Reusing
  `change_a_managed_path_by_hand` in the older hand-changed test is 2/4 (Bob, Carl) and is also their
  proposed way under the 800-line limit.
- **Row 12 repeats row 4's DRY_RUN gap.** The missing DRY_RUN orphan test is 3/4 (Alice, Bob, Blake).
- **Row 13 carries the mechanical replay finding** (`mech-check` appended to its finders, see below).
- **Row 14 is answered by this cycle's suite run** (see `Tests:`); nothing remains to verify.

## Mechanical checks (computed)

- Tautological shapes: none flagged across 39 test functions in `tests/test_braid.py`.
- Fail-first replay, base `73a0953`, run from a checkout of `4e2de33` so the later commits stayed out:
  7 touched tests ran, 3 failed against the pre-change code and 4 passed.

  `[MECH] 🟡 4 touched test(s) pass against the pre-change code: test_check_ignores_a_link_pointing_outside_every_source_root, test_check_after_a_lost_state_file_reports_the_state_not_the_wanted_links, test_sync_refuses_to_remove_a_hand_changed_managed_path, test_kiro_gets_every_skill_including_those_ignored_for_claude | File: tests/test_braid.py | Task: general`

  Absorbed into row 13. All four pin a limit of the fix, not the fix: the first is the negative test
  the PRD itself orders, the second and fourth guard against the scan reporting wanted links, the
  third pins "sync keeps the hard refusal". Alice and Bob both read them as guard tests to keep. The
  three tests that carry the fixes (orphan reported, hand-changed path reported, state write fails
  clean) do fail against the old code.
- Function sizes (from `ast`): `_write_state` 10 lines, `_report_orphan_links` 22, `_sync_links` 62
  (58 before), `run` 85 (71 before). File sizes: `cli.py` 782 lines, `tests/test_braid.py` 801.

## Orchestrator verification

Two contested claims were run, not just read (throwaway script against the code at HEAD):

- **State-write cleanup.** The PRD's own error case (state path is a directory) gives `BraidError`
  and no temp file. Two other failures still escape as a raw exception: the state path's parent is a
  regular file (`NotADirectoryError` from the `finally` unlink), and the temp path is itself a
  directory (`PermissionError` from the same unlink, temp left behind). Confirmed.
- **Ownership predicate.** Four link shapes, PRD wording (resolve the full target) against the code
  (resolve the target's parent, keep the last name):

  | Link | PRD wording | Code |
  |------|-------------|------|
  | union link to a source skill (live or dangling) | owned | owned |
  | Claude link to a union link that still exists (live or dangling) | **not owned** | owned |
  | union link to a symlink inside a source's `skills/` that leads outside | not owned | **owned** |
  | union link to a symlink outside every source that leads into one | owned | **not owned** |

  Row 2 is the one that matters: under the PRD's literal wording a Claude-root orphan is missed
  whenever its union link is still on disk, which is the PRD's own two-orphan scenario. Rows 3 and 4
  are the residue Bob points at. Confirmed.
- **README wording (row 8).** Read from `_sync_links`: a hand-replaced path whose name is still
  wanted goes through the first loop, prints `MISMATCH <path> -> <target>` and is backed up and
  relinked by sync. `MISMATCH CHANGED` and the sync refusal apply only to a recorded name that is no
  longer wanted. Bob's reading is right. Confirmed by reading, not run.

## Alice

[ALICE] 🟡 tests/test_braid.py is now 801 lines (about 712 before this commit), over the 800-line limit; the commit pushed it over. Move the three drift-reporting groups (orphan, hand-changed, state-write tests) to a new tests/test_braid_check.py, reusing the helpers via a conftest or import | File: tests/test_braid.py:801 | Task: 5
[ALICE] 🟡 `run` grew from 71 to 85 lines (limit 50) and `_sync_links` from 58 to 62. Most of the growth is the `previous_claude`/`previous_kiro` locals plus the `orphan_scans` list built inline in `run`. Extract a small helper (for example `_orphan_scan_plan(...)`, or pass `previous` into one helper) so `run` does not grow further; the scan lists are also built in Mode.SYNC and never used there | File: src/agent_skills_braid/cli.py:528 | Task: 4
[ALICE] 🟡 The orphan scan's new behaviour is only partly pinned. Positive tests cover Mode.CHECK on the union and Claude roots only. Mode.DRY_RUN orphan reporting has no test, so changing the gate `settings.mode is not Mode.SYNC` to `is Mode.CHECK` would pass the suite. A Kiro-root orphan is never asserted positively either; the Kiro scan is covered only by the `drift == 0` line added to the plugin-owned test. Add a DRY_RUN case (parametrize the orphan test over DRY_RUN and CHECK) and one Kiro orphan case | File: tests/test_braid.py:303 | Task: 5
[ALICE] ⚪ `_write_state`: when the failure is that `path.parent` is a regular file (`mkdir` raises FileExistsError), the `finally` `temporary.unlink(missing_ok=True)` raises NotADirectoryError, because `missing_ok` only swallows FileNotFoundError (confirmed by running it). That replaces the BraidError with a raw traceback, which is the defect this PRD fixes, in a narrow case. Move `mkdir` before the `try`, or catch OSError around the unlink | File: src/agent_skills_braid/cli.py:413 | Task: 1
[ALICE] ⚪ `_report_orphan_links` tests `path.is_symlink()`, so an orphan NTFS junction (the Windows fallback that `_points_to` and `_remove_owned_link` handle) is never reported. The PRD and README say "symlink", so this is a documented limit, not a spec breach; mention it in the README if it is intended | File: src/agent_skills_braid/cli.py:452 | Task: 4
[ALICE] ⚪ Verdict on the declared deviation: it is better than the PRD wording, not a defect. (Full text in row 3 of the table.) | File: src/agent_skills_braid/cli.py:459 | Task: 4

Checks she ran: `uv run pytest tests/test_braid.py -q` gave 52 passed with no xfail, xpass or skip
(the PRD's "15 passed" is stale: the file gained Kiro tests after the PRD was written).
`rg -c xfail tests/test_braid.py` prints 1. `braid --check` appears only in prose, with no file under
`bin/`, `.github/` or `skills/`, so the exit-code change from 2 to 1 has no in-repo caller.

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
R12: fail
R13: fail

## Blake

Blind lens: his prompt held the PRD, the blind rubric and the output format, nothing else.

[BLAKE] 🟡 The orphan scan also covers the enrolled Kiro skills root (`orphan_scans.append((kiro.root / "skills", [union_root], ...))`). The spec names only `<agents-root>/skills` and `<claude-root>/skills` as scanned roots. On Kiro-enrolled machines this adds MISMATCH ORPHAN lines and drift counts the PRD never defined, and no test covers it. | File: src/agent_skills_braid/cli.py:595 | Task: Phase 2
[BLAKE] ⚪ The ownership predicate departs from the spec text. It resolves only the link target's parent and keeps the last component (`_resolved(target.parent) / target.name`) instead of calling `_resolved` on the whole target. The code comment gives the reason: a claude link whose union link is still live would otherwise resolve into the source tree and escape the union owner root. The result is more accurate than the literal spec, which would miss claude orphans, but it is an undocumented deviation from "`_resolved` it". | File: src/agent_skills_braid/cli.py:459 | Task: Phase 2
[BLAKE] ⚪ The failed-state-write test checks only for a `BraidError` and no leftover `.tmp` file. The spec's error case also requires `entrypoint()` to exit 2 with the `braid: cannot write Braid state ...` message, and that path has no regression test. | File: tests/test_braid.py:412 | Task: 0
[BLAKE] ⚪ Orphan scan has no test in `Mode.DRY_RUN`. `_report_orphan_links` also calls `os.readlink` and `iterdir` without OSError handling, which would escape `entrypoint()` as a traceback. `path.is_symlink()` is false for Windows junctions, so junction orphans go undetected. | File: src/agent_skills_braid/cli.py:451 | Task: 2
[BLAKE] ⚪ The `finally: temporary.unlink(missing_ok=True)` in `_write_state` is not itself guarded. An OSError there (for example a permission failure) would replace the `BraidError` with a raw traceback. This is the exact shape the spec prescribes, so it is a residual risk, not a deviation. | File: src/agent_skills_braid/cli.py:413 | Task: 0

He found the code unaided and confirmed all three capabilities, the xfail count of 1, and no in-repo
caller of the exit code. His one failing rule is B6 (scope creep), for the Kiro scan.

B1: pass
B2: pass
B3: pass
B4: pass
B5: pass
B6: fail
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

Codex, first run, exit 0, no retry. Doubt lens and de-slop lens carried.

[BOB] 🟠 FIX: Cleanup can mask the intended BraidError: if the temporary path is a directory, both write_text and finally-unlink fail, and entrypoint emits a traceback. Catch cleanup OSError explicitly, preserve the write failure, and test this case. | File: src/agent_skills_braid/cli.py:413 | Task: 1
[BOB] 🟡 FIX: Parent-only resolution correctly preserves projection ownership, but misclassifies union links: union/own → source/skills/alias → outside is reported despite resolving outside every source. Fully resolve source targets; retain the deliberate union-hop boundary for projections, with regression tests. | File: src/agent_skills_braid/cli.py:459 | Task: 4
[BOB] 🟡 FIX: Positive orphan tests cover only CHECK for union/Claude. Add DRY_RUN and enrolled-Kiro cases asserting exact reports, drift counts, and unchanged links; the added Kiro clean-state assertion never exercises orphan reporting. | File: tests/test_braid.py:303 | Task: 5
[BOB] 🟡 FIX: The hand-changed-path regression duplicates setup already provided by change_a_managed_path_by_hand. Reuse that helper; this also brings the 801-line test file below the rubric’s 800-line limit without removing coverage. | File: tests/test_braid.py:359 | Task: 2
[BOB] 🟡 FIX: Documentation says sync refuses hand-replaced recorded links generally, but that applies only to stale names; desired names are backed up and relinked. Qualify the description with “no longer desired,” including the corresponding changelog claim. | File: README.md:210 | Task: 2
[BOB] ⚪ KNOWN: _sync_links and run remain 62 and 85 lines. Both exceeded 50 before this change; broad decomposition is outside this defect-fix scope, although R12 remains unmet. | File: src/agent_skills_braid/cli.py:464 | Task: general
[BOB] ⚪ KNOWN: Replay reports four passing-before tests: outside-root exclusion, wanted-link exclusion after state loss, sync refusal, and Kiro clean-state checking. These intentionally preserve existing behavior, so retain them; they do not satisfy the rubric’s literal fail-first requirement. | File: tests/test_braid.py:324 | Task: general
[BOB] ⚪ Cannot statically verify: VERIFY that `uv run pytest tests -q` passes with no failures, skips, xfails, or xpasses at the reviewed commit. | File: N/A | Task: 5

R1: fail
R2: fail
R3: pass
R4: pass
R6: pass
R7: fail
R8: pass
R9: fail
R10: fail
R11: pass
R12: fail
R13: fail
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

Gemini through the `copilot` backend, model `gemini-3.8-flash`, exit 0. No frontend surface in this
diff, so he reviewed as a generalist. In prose above his issue lines he judged the deviation "strictly
better than the PRD's wording" for the Claude and Kiro projections; he raised no line for it.

[CARL] 🟡 Duplicate setup in test_check_reports_a_hand_changed_managed_path_instead_of_aborting can reuse change_a_managed_path_by_hand | File: tests/test_braid.py:359 | Task: 2
[CARL] 🟡 Function run is 85 lines, exceeding the 50-line limit | File: src/agent_skills_braid/cli.py:528 | Task: 4
[CARL] 🟡 Function _sync_links is 62 lines, exceeding the 50-line limit | File: src/agent_skills_braid/cli.py:464 | Task: 2
[CARL] ⚪ File size: tests/test_braid.py is 801 lines, exceeding the 800-line limit | File: tests/test_braid.py:801 | Task: general

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
R12: fail
R13: fail

## Follow-up Tasks Created

None. This is a standalone run with no autopilot state for this PRD, so the findings are reported
here and to the operator, not written as tasks.

## Triage

The three capabilities the PRD asks for are all present and each has a test that fails against the old
code. Nothing found is a wrong result in the common path; the findings are a narrow leftover of the
state-write defect, a spec deviation to ratify, a scope extension, and test, size and wording gaps.

Settled by a standing rule, so fixed without asking (queued for the rework commit):

- Orphan scan in `--dry-run` has no test (rows 4, 12): every new behavior ships with a test.
- `tests/test_braid.py` at 801 lines (rows 1, 9): the 800-line file limit. Reuse
  `change_a_managed_path_by_hand` in the older test; if the added tests push it back over, move the
  drift-reporting tests to their own file.
- Row 14: answered by the suite run below. No action.

Needing the operator's call, walked one at a time: the state-write cleanup (rows 5, 6), the
ownership-predicate deviation (row 3), the Kiro-root scan (row 7, which also decides whether a Kiro
orphan test is owed), the size of `run` and `_sync_links` (row 2), and one bundle of low items (rows
8, 10, 11, 13).

## Walkthrough minutes

Walked with the operator on 2026-10-05, one finding at a time. Nothing was deferred or rejected;
every fix below is queued for one rework commit, which this file is the record of.

| # | Finding (table rows) | Decision | Status |
|---|----------------------|----------|--------|
| 1 | State-write cleanup can still traceback (5, 6) | Guard the temp delete so it can never replace the `BraidError`; test both confirmed cases (parent is a regular file, temp path is a directory). The wider "catch `OSError` in `entrypoint()`" option was not chosen. | queued |
| 2 | Ownership predicate resolves the target's parent (3) | Keep the code. Amend the PRD's "Ownership predicate" behavior to describe parent resolution and why (full resolution misses a Claude-root orphan whose union link still exists). Bob's hybrid was not chosen; the two exotic link shapes stay as they are. | queued |
| 3 | Kiro root scanned, PRD names two roots (7) | Keep the scan. Add the Kiro root to the PRD's orphan-scan inputs and add one test that plants a Kiro orphan. | queued |
| 4 | `run` 85 lines, `_sync_links` 62 (2) | Move the orphan-scan list building out of `run()` into one helper. `_sync_links` is left alone; both stay over the 50-line limit, accepted for this PRD. | queued |
| 5a | README and changelog overstate the sync refusal (8) | Say "no longer wanted" where `MISMATCH CHANGED` and the refusal are described. | queued |
| 5b | Exit 2 and the `braid:` message untested (11) | Add a CLI-level assertion for exit status 2 and the `braid: cannot write Braid state` line. | queued |
| 5c | Orphaned NTFS junctions not reported (10, 12) | Add one README sentence stating the limit. No code change. | queued |
| 5d | `readlink` and `iterdir` unguarded in the scan (12) | Turn an `OSError` there into a `BraidError`. | queued |
| 6 | Four touched tests pass on the old code (13, mech-check) | Kept by design: they are guard tests for the fix's limits, one of them ordered by the PRD. Put to the operator, no objection. | no action |
| 7 | Orphan scan untested in `--dry-run` (4, 12) | Rule-mandated (every new behavior ships with a test): run the orphan test in both read-only modes. | queued |
| 8 | `tests/test_braid.py` at 801 lines, duplicate setup (1, 9) | Rule-mandated (800-line limit): reuse `change_a_managed_path_by_hand` in the older test. Items 1, 3, 5b and 7 add tests, so also move the drift-reporting tests to their own file to stay under the limit. | queued |
| 9 | "Cannot statically verify" the suite (14) | Answered by this cycle's run, see `Tests:`. | closed |

The rework changes code, so it gets its own review cycle from a fresh session: `--since d5d2562`
(this file's `head_sha`) scopes it to what landed after this review: the rework, plus this file's
own two commits.

Verdict: 14 findings
Tests: 3434 passed, 0 failed, 6 skipped (suite run this cycle)
