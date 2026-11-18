# Repository closeout verification, 2026-11-18

**FAIL.** The tested archive behavior passes, but the closeout plan's history,
preservation, and review/integration evidence requirements do not all pass.
The executed plan remains in `plans/`. No production repair, history rewrite,
PR action, branch deletion, or autopilot state transition was made here.

## Tested input and method

Fresh independent Codex session, limited to Session 4. Fetched `origin` and
queried GitHub directly. Local `master`, `origin/master`, and the advertised
remote head were `5be3433cb27f4458b440837d1d8ccf114f461904`. The tracked tree
and index were clean before checks. All local results below refer to this
commit; the later verification commit changes records only.

Host: macOS 27.0.1 arm64; uv 0.13.8; default test Python 3.13.18; pytest 9.1.1;
Node 26.13.1. Focused tests also used isolated Python 3.10.22 and 3.12.16
environments with `uv run --no-project`, leaving the project environment intact.
All three installed Python builds have a callable `tarfile.data_filter`.
The tests separately remove that capability, so each runtime exercises both
the real filter and the manual extraction path.

Read the plan, execution record, preparation reports, original audit, capsule,
archive/Windows PRDs, recovery reviews, migration shipping review, drain review,
and the later 00163 and 00133 reviews. No Stage 3 or Verification handoff was
found in the tracked project-management tree or ignored `docs/dev/tmp/`.

## Findings and required closure

| ID | Failed requirement | Evidence | What closes it |
|---|---|---|---|
| V1 | Complete review and integration evidence, plan Stages 2/3 and Session 4 steps 2/3/9 | At entry, the execution record ended at 00162 finalization on November 8, with 00164/00161/00163/00044 and combined review still pending. Later reviews and merges exist, but no Stage 3 entry freezes approved trees, integration order, and remote-action decisions. The drain review records initial Alice/Blake/Bob reviews and Codex-only rework passes; it does not establish every required fresh-session and all-lens gate for the final integrated candidate. | Reconstruct Stage 2/3 from original evidence, map each reviewed source tree to the published result, and run any genuinely missing required review. Record later scope changes and PR dispositions. Do not fabricate historical approvals. |
| V2 | Preserve the entire published master history, shared rules 3/4 | The original baseline `6b52b2a` and shared base `6091e02` remain ancestors, including all 147 original published commits. However, `4103e99` (the execution record's later master tip) and `0466054` (the drain review's master base) are not ancestors of current master. The drain review explicitly records force replacement of public master with a scrubbed line. | Reconcile the later history decision and its authority with this plan. Keep custody/recovery evidence. Do not rewrite current history to satisfy an obsolete snapshot. |
| V3 | Preserve excluded PRD 00133 and its stopped state, scope and Session 4 step 11 | The original wip file is absent; 00133 is in `done/` with a November 15 completion review. The original state hash changed and the live store now targets paused 00135, 3/3 tasks. The plan was never amended. Later records describe separate work, but do not reconcile this preservation requirement. | Record the authorized later disposition and the appropriate current resume target. Do not restore old state over later work. |
| V4 | Required local shell verification, Session 4 step 8 | `test_codex_run.sh`: 11 passed, 33 failed. `test_gemini_run.sh`: 7 passed, 11 failed. Both wrappers return exit 3, `refusing nested dispatch (already inside a CLI agent)`, before reaching the test stubs. | Run those suites from a terminal outside Codex/Copilot and record counts. Keep dispatch guards enabled. Hosted shell CI is separate evidence, not a local pass. |
| V5 | Final-master Windows CI, Session 4 step 7 | At 12:17:21Z, exact-tip run 44299821325 still had Windows in progress. The other seven jobs succeeded. The watch-ci skill's 15-minute polling cap was reached. | Read the completed exact-SHA run, its Windows count/skip reasons, and the remaining job logs. Diagnose any failure through the prescribed correction/review route. |

V1-V3 concern compliance and evidence for this plan. They do not establish a
current archive defect. Later changes must be reconciled against their own
recorded authority. Session 4 cannot silently replace the original requirements.

## Archive acceptance map

All paths below are under `skills/use-qwen/scripts/`. The implementation is
`eval_harness/trees.py`. Each test module named here was read and executed;
crafted archives, destinations, and outside sentinels live in disposable test
directories. Refusal helpers check sentinel bytes/modes and absence of a partial
destination/staging tree, rather than merely accepting any exception.

| Contract | Implementation and regression evidence | Result |
|---|---|---|
| A1, symlink ancestor escape | `_ancestor_crossing`, `_land`; `test_eval_tree_archive_safety.py::test_build_template_refuses_a_link_reached_through_an_ancestor_link_in_either_order` | PASS, both paths |
| A2, valid files and links | `_lay_links_typed`, `_copytree_links_typed`; safety module's real-Git, binary/CRLF, directory/dangling-link and chain controls; `test_eval_tree_links_typed.py` | PASS, both paths |
| A3, traversal and cycles | `_land`; `test_eval_tree_links.py` traversal/cycle refusals and safe internal-parent controls | PASS, both paths |
| A4, absolute/native names | `_archive_name_escapes`; safety module's absolute member and link-target matrices | PASS, both paths |
| A5, duplicate/colliding names | `_refuse_duplicate_or_crossing_members`, `_refuse_colliding_landings`, `_fold`; normalized-path collision and case/Unicode alias tests | PASS, both paths |
| A6, hardlinks and special types | Explicit allowed-type predicate; safety module's hardlink/FIFO/device matrix | PASS, both paths |
| A7, mode and ownership metadata | `filter="data"`, `_extract_without_filter`, `_safe_mode`; `test_eval_tree_archive_safety_modes.py` spies on chmod/chown and checks bytes/modes | PASS, both paths |
| A8, filter availability/parity | Callable runtime capability check; `test_eval_tree_archive_safety_ancestor_parity.py` noncallable filter, restrictive modes, and valid manual directory-link controls | PASS |
| A9, failure atomicity | `build_template`, `_discard_build`; `test_eval_tree_archive_staging.py` extraction/seal failures and existing-destination controls; ancestor-parity concurrent-writer control | PASS |
| A10, warnings and translated refusals | Explicit filter/manual paths and chained `TreeError`; all focused runs used `-W error::DeprecationWarning` | PASS for covered extraction/filter/OS refusals |
| A11, contained reads and clones | `contained`, `_refuse_escaping_links`, `_read_link`; link tests and `test_eval_tree_host_links.py` | PASS locally; native Windows result recorded separately |
| A12, members beneath symlinks refused | `_ancestor_crossing`; ancestor-parity refusal plus valid standalone-symlink control | PASS, both paths |

Published integration anchors: `2357168` (00160), `540a64d` (00162),
`d2e6c66` (00164), `ee686f8` (combined archive/Windows work), and `99796b9`
(later archive tests and closure of 00165-00174). Final-tree verification also
covers subsequent repairs recorded in the drain review. Tests do not prove
every possible hostile tar is safe. Existing review limitations, including
additional `.git` aliases and untranslated malformed-tar exceptions, remain
documented in the linked reviews; this session did not expand that scope.

## Local checks

Checks ran on November 18, beginning around 12:00 UTC. Tool output contains
the observed summaries; the command/result ledger is retained under
`docs/dev/tmp/closeout-verification-20261118/`. It is a summary, not a full log.

| Command/check | Result |
|---|---|
| `uv run pytest -ra` | 4,939 passed, 0 failed, 12 skipped; 414.45 s; exit 0 |
| Focused archive/link/state matrix, Python 3.10.22 | 499 passed, 0 failed, 0 skipped; 64.50 s |
| Same matrix, Python 3.12.16 | 499 passed, 0 failed, 0 skipped; 64.42 s |
| Same matrix, Python 3.13.18 | 499 passed, 0 failed, 0 skipped; 63.67 s |
| Optional MCP/document integration tests, isolated Python 3.13 | 31 passed, 7 subtests passed, 0 skipped; 7.61 s; 6 warnings plus a SWIG shutdown warning |
| `uv run ruff check`; `uv run ruff format --check` | PASS; 19 files already formatted |
| `validate_skill.py` for every discovered skill | All 60 passed |
| `~/.agents/bin/braid --check` | 161 current, 20 ignored, 0 drift; all mutation counters zero |
| Node 26 `npm ci`, build, byte comparison, tests | Install/build/template comparison passed; 62 tests passed, 0 skipped |
| Dependency-list shell suite | 17 passed, 0 failed |
| Sonnet wrapper shell suite | 40 passed, 0 failed |
| Qwen automation / runner shell suites | 31 / 114 passed, 0 failed |
| Codex / Gemini wrapper shell suites | 11/33 and 7/11 passed/failed respectively; see V4 |
| `git diff --check` | PASS before report edits; repeated before commit |

Focused command: `pytest skills/use-qwen/scripts/test_eval_tree_archive_*.py
skills/use-qwen/scripts/test_eval_tree_links*.py
skills/use-qwen/scripts/test_eval_tree_host_links.py
skills/use-qwen/scripts/test_eval_tree_state.py -W error::DeprecationWarning -q -ra`.
For 3.10/3.12, prefix with `uv run --no-project --python VERSION --with pytest
--with pyyaml`; for 3.13 use `uv run`.

Optional integration pins were read from the two skill pyprojects: MCP 2.3.0,
httpx2 2.16.2, python-docx 1.2.0, PyMuPDF 2.1, PyYAML 6.0.3. That run covers
the default suite's absent optional dependencies. Warnings concern SWIG types
and the deprecated `fitz` import; no warning was suppressed.

The 12 default-suite skips are one missing MCP test module, two document
converter cases, eight survey cases requiring `tree_sitter_language_pack`,
and one Windows-only job-object case. The separate optional integration run
passes the MCP/document cases; it does not turn the original skips into passes.
The survey optional cases were not run. Native Windows must supply the job-object
coverage; its final result remains pending. There were no xfails reported in
the local Python run.

## Hosted CI and PR outcomes

Directly inspected [run 44299821325](https://github.com/buvis/agent-skills/actions/runs/44299821325)
at the exact tested SHA. At **2026-11-18T12:17:21Z**, Linux 3.10, Linux 3.13,
lint, shell, Node, and both optional integration jobs had succeeded.
Windows remained **in_progress**, with no conclusion. The workflow therefore
has no final green result in this report. `gh run view --job ... --log`
refused access until the whole run completes, so hosted test counts and
Windows skip reasons remain unverified. Earlier green runs do not substitute
for this exact-tip result.

Applied the portable `watch-ci` skill at `~/.agents/skills/watch-ci/SKILL.md`:
"Timeout after 15 minutes. If still running, report status and stop polling."
Polling stopped at that cap. No remote job was cancelled or restarted.

| PR | Direct GitHub result | Final code and disposition |
|---|---|---|
| [#17](https://github.com/buvis/agent-skills/pull/17) | Merged November 9; head `3f5023dd96adcef3b950e0ee6c60cd84691b86f6`; merge `d36828806bcf3da69dcdce03f02c8500a4001078` | All seven skills present. Body records owner-confirmed MIT and follow-up 00175. The shipping review documents the renumbering from 00159; 00175 is now done. Do not revert the body to 00159, which now owns braid retirement. |
| [#15](https://github.com/buvis/agent-skills/pull/15) | Closed by Renovate November 16 at 07:22:28Z; no merge commit; last head `d74d47b660121c5e64a7682489b5416dec4debd1` | Requested setup-uv 10.3.3 is present in all four uses, pinned at `68559e99cc807c1eb7e9238fd43a15bba460eec2`, through `645f7e8` / PR #32. Closed/superseded, not merged. |
| [#16](https://github.com/buvis/agent-skills/pull/16) | Merged November 16; head `018b5515207e75504db28ed4e5ce3cc0a9a32d83`; merge `dd3a44d3bde98cf446ab2f310e46fdb1bca7adc2` | CI selects Node 26; local build/freshness/tests pass. |

Windows residue 00163 is in `done/`; its port note distinguishes superseded
tasks 1/3 from implemented tasks 2/4. `c8f582a` fixes the manifest append,
`3e3a9e7` adds Windows `-ra`, and `4ddcc5a` records closure after native CI.
The reviewed gate-parser adjustment is separate at `49bd5c8`.

## Ancestry, recovery, and hygiene

Measured before report writes at the tested SHA:

- The preserved range `02a1423..6091e02` still contains exactly 147 commits.
  Both `6091e02` and `6b52b2a` are ancestors of master (exit 0).
  Later tips `4103e99` and `0466054` return exit 1; see V2.
- Searching all local branches, remote branches, and all refs for the private
  `skill-migration-bundle-plan.md` history returned zero commits.
- All 60 files in `.git/recovery-20261030/` match the original preservation
  manifest. None is tracked. Of the original 62 preserved entries, the other
  two are the changed state and missing wip 00133 file, as described in V3.
- Current state SHA-256 is
  `b85891ca366ab722724026706b262a5984dfc6ea5419186deea2f5581ac9d108`.
  Done PRD 00133 SHA-256 is
  `c855857ae32ee63b46ee07891930877dee860a2ab79e961f9d66f45f8a149f10`.
- Two worktrees remain: the canonical checkout and
  `~/git/src/worktrees/agent-skills/retire-braid` at
  `92ee7f9ca29de6f22dfa10a904020947314e7812`. Both were clean. The latter is
  unrelated active preparation and was left alone. No closeout worktree remains.
- Origin advertises only `master`. Local retained branches are
  `custody/00111-braid-state-misses-link-removals-v1` at `2921bc0`,
  `custody/00135-raw-reviewer-evidence` at `0466054`, and
  `feature/retire-braid` at `92ee7f9`, besides master. This matches the updated
  capsule's cleanup disposition. No stashes exist.

## Additional follow-up

`npm audit --json` returned exit 1: six high-severity dependency entries arise
from the picomatch ReDoS advisory
[GHSA-fc5q-39xc-vjpf](https://github.com/advisories/GHSA-fc5q-39xc-vjpf).
Affected entries are picomatch, fdir, tinyglobby, vite,
vite-plugin-singlefile, and @sveltejs/vite-plugin-svelte. This is six dependency
entries, not six distinct advisories. Prepare a separate tested dependency fix;
do not apply the suggested force/downgrade automatically. npm also reports the
unapproved optional fsevents install script. The build used the existing policy.
Vite used its default Svelte configuration because no explicit config exists.

## Corrective handoff

1. Open this repository in a fresh closeout reconciliation session.
2. Read this report, the closeout plan, and the execution record.
3. Preserve current master, custody branches, recovery files, and active worktrees.
4. Reconcile V1 through V3 against original approvals and later completion records.
5. Record the actual integration order, reviewed trees, PR outcomes, and changed preservation requirements.
6. Run any missing mandatory reviews in fresh sessions with every required lens.
7. Run both V4 shell suites from a terminal outside Codex and Copilot.
8. Keep nested-dispatch guards enabled.
9. Record a separate dependency-repair task for the npm advisory.
10. Resolve V5 from the completed exact-SHA CI result and job logs.
11. Commit the corrected closeout evidence through the permitted normal route.
12. Hand off to a fresh Session 4 verification session.
13. Archive the plan only after that verification passes.

Related evidence: [execution record](repository-closeout-execution.md),
[migration shipping review](skill-migration-ship-review-2026-11-09.md),
[drain review](../reviews/drain-backlog-completion-review-20261115.md),
[00163 review](../reviews/00163-windows-suite-residual-failures-v1-review-1.md),
and [00133 review](../reviews/00133-transcript-judge-inherits-tools-v1-review-1.md).
