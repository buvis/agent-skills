# Backlog review - agent-skills - 2026-09-08

Verdict: GO (0 Blocking open; 26 PRDs in backlog after 00078 moved to hold on 2026-09-13)

Reviewed all 27 backlog PRDs end-to-end at HEAD 076b306, with 1 WIP,
30 done and 20 held PRDs as context. No discovery directory exists.
All eight lenses ran; three parallel grounding agents verified nine PRDs each.
This is a specification review: no implementation, live inference, or live
portfolio collection ran. The decision pass and the apply pass completed on
2026-09-13; see Decisions applied. 00052 remains selectable only after WIP
00051 completes, which its own premise check enforces.

## Map

READY means the artifact can run as written; non-blocking improvements are below.
00052 can run only after its explicitly required WIP producer 00051 completes.
HOLD below is a proposed disposition, not an applied move.

| # | PRD | template | lines | subsystems | depends on | verdict |
|---|---|---|---:|---|---|---|
| 00052 | Eval renderer and docs | standard | 294 | use-qwen records/report | WIP 00051 | READY |
| 00053 | Portfolio test split | minimal | 114 | brief JS/Python tests | current baseline; retarget 00054–00069 | READY |
| 00054 | Metadata non-JSON failures | minimal | 90 | brief collector | 00053 | READY |
| 00055 | Metrics timestamps | minimal | 99 | brief collector | 00053 | READY |
| 00056 | CI error reporting | minimal | 93 | brief collector | 00053; done 00026/00028 | READY |
| 00057 | Snapshot permissions | minimal | 125 | brief persistence | 00053 | READY (rewritten 2026-09-13) |
| 00058 | URL policy | minimal | 100 | brief derivation/components | 00053 | READY |
| 00059 | Torn build inputs | minimal | 97 | brief build | existing xfails | READY |
| 00060 | History append separator | minimal | 79 | brief collector | 00053; complements 00059 | READY |
| 00061 | Local facts before metadata | minimal | 89 | brief collector/history | 00053/00054/00056 | READY |
| 00062 | True commit counts | minimal | 101 | brief collector/derivation/detail | 00053/00061 | READY |
| 00063 | Missing registry diagnostic | minimal | 78 | brief collector | 00053 | READY |
| 00064 | Symlinked source candidates | minimal | 82 | braid inventory | existing real-symlink fixture | READY |
| 00065 | Bounded history retention | minimal | 81 | brief build | 00059 | READY |
| 00066 | Clipboard escaping | minimal | 80 | brief Todos | 00053; preserve 00058 | READY |
| 00067 | Remote slug parsing | minimal | 84 | brief collector | 00053 | READY |
| 00068 | Shared branch lookup | minimal | 83 | brief collector | 00053; account for 00062 | READY |
| 00069 | Announcement timing test | minimal | 95 | brief Todos/harness | 00053 | READY |
| 00071 | Publication recovery | minimal | 165 | distil writer/queue/docs | done 00015–00017 | READY (edited 2026-09-13) |
| 00072 | Judge stdin/no persistence | minimal | 94 | distil judge/tests | preserve done 00034 | READY |
| 00073 | Sweep setup and reports | minimal | 128 | sweep-fix | done 00032 | READY |
| 00074 | Tests bind their intent | minimal | 91 | distil tests | 00071; done 00017 | READY |
| 00075 | PRD grounding checker | standard | 190 | create-prd/backlog gate | done 00047; frozen checker contracts | READY (edited 2026-09-13) |
| 00076 | Atomicity/refusal tests | minimal | 135 | distil tests | done 00017; 00071/00074 | READY |
| 00077 | Queue failure diagnostics | minimal | 124 | distil queue/docs | 00071/00076; done 00015–00017 | READY (edited 2026-09-13) |
| 00078 | Through-Pi preflight | minimal | 104 | live Qwen dispatch helper | attended diagnosis; isolate from loop | HELD (moved to hold/ 2026-09-13) |
| 00079 | Survey test split | minimal | 75 | survey tests | current baseline | READY |

## Findings

### Blocking

#### B01 — 00057: platform permission contract needs its accepted scope applied

- **Lenses B/C/D; location:** [00057](../prds/backlog/00057-data-json-world-readable-v1.md),
  Solution lines 33–36, Must have lines 42–45, task line 74, Success Criteria lines 83–84.
- The task requires POSIX mode bits 0600/0700 on every host. Native Windows
  already runs the full Python suite (`.github/workflows/ci.yml:59–60,119–120`);
  `tests/test_conftest_fixtures.py:240–255` explicitly documents that chmod
  does not move those mode bits there. The criterion also precreates a file
  inside a directory it expects this same run to create.
- **Fails as: wrong-TDD lock-in / rework thrash.** A literal test cannot meet
  the platform contract. This is the still-open decision from the previous
  review, not a reversal of an accepted permission choice.
- **Fix:** choose explicitly POSIX-only protection with Windows behavior tests,
  native owner-only protection on both platforms, or HOLD. For either implementation,
  separate fresh-directory and old-snapshot rotation fixtures and include
  `write_snapshot`'s temporary files (`collect.py:447–465`) in the permission
  contract; chmod after publication leaves those files exposed. Replace the
  mandatory live BSD-stat check with fixture-based assertions; retain real-run
  observation only as an optional operational check. Keep the accepted decision
  to retain diagnostic text.
- **Decision recorded:** user selected option 2: native owner-only protection
  on both POSIX and Windows. Prepare POSIX modes plus Windows ACL requirements,
  covering temporary and final snapshots with separate fresh-directory and
  rotation tests. PRD edits remain pending the batch apply pass.

#### B02 — 00071: the new decide signature removes the existing one-read seam

- **Lenses B/C/D; location:** [00071](../prds/backlog/00071-distil-publish-recovery-v1.md),
  Module: docket.py line 121; Phase 0 recovery task line 147.
- The exact proposed signature adds `name` but drops `data=None`.
  `docket.py:124` currently accepts it, and `main()` passes `data=data`
  at line 258. The caller deliberately loads once outside the decision-refusal
  handler, keeping queue corruption at exit 2.
- **Fails as: wrong-TDD lock-in.** Literal replacement breaks CLI decisions;
  simply dropping the caller argument restores the double read pinned by
  `test_docket_exit_codes.py:244–270`.
- **Fix:** specify
  `decide(entry_id, state, file_text=None, path=None, data=None, *, name=None)`.
  Add the existing one-read regression, corrupt-queue exit 2, refused-decision
  exit 1 and stable recovery counters to the task acceptance. No queue contract
  redesign is needed.

#### B03 — 00075: an uninstalled locked crate gets two incompatible verdicts

- **Lenses B/C; location:** [00075](../prds/backlog/00075-ground-prd-claims-against-installed-code-v1.md),
  Extract claims line 46; Verify library claims line 60; Report and exit line 67.
- Claim extraction recognizes a library only when its first segment names an
  installed package. The package definition includes a locked crate only when
  its source directory exists, but the same Behavior then requires a locked
  crate without source to become non-blocking `unverified`.
- **Fails as: wrong-TDD lock-in.** On a clean host, the same absent API can
  instead become a repo-symbol `unresolved` error and block the save.
- **Fix:** classify crate identities from Cargo.lock even when source is absent;
  separately resolve source availability. Pin a fixture with a locked crate,
  no installed directory, and an absent API: one library/unverified row, exit 0.
  Keep the agreed warning-only library behavior.

#### B04 — 00077: the failure scope and CLI acceptance disagree

- **Lenses B/C/D; location:** [00077](../prds/backlog/00077-docket-never-raises-v1.md),
  Problem lines 24–25, Solution lines 37–39, tasks lines 89–100, Success Criteria lines 112–113.
- The problem and final closure cover a record missing a required key, while
  the solution validates only `name` and `file`. The current reader also
  indexes `kind`, `transcript`, `line_no` and `evidence_text`
  (`docket.py:214–217`). Missing any still raises KeyError after the specified
  fix. The write tests also call `advance` a CLI verb; the actual verb is
  `start`, which invokes `advance()` (`docket.py:182,237–239`).
- **Fails as: rework thrash / wrong-TDD lock-in.** Narrow task tests can pass
  while PRD-level closure still fails, or tests can target a nonexistent verb.
- **Fix:** explicitly require object records with all six required keys;
  reject an invalid batch before persistence. Exercise CLI `save`, `decide`
  and `start`; use `advance()` only for the internal function. Preserve
  QueueError exit 2, decision refusal exit 1, the one-read seam, and 00071's
  new unpublished queue/store exit distinction. Alternatively explicitly narrow
  the claimed malformed-record closure to name/file and record the remaining gap.

#### B05 — 00078: investigation and live dispatch machinery are still in scope

- **Lenses B/D/E; location:** [00078](../prds/backlog/00078-qwen-preflight-probes-the-dispatch-path-v1.md),
  Solution lines 25–31, Must have lines 37–43, Phase 0 lines 78–80,
  Phase 1 lines 84–89.
- The task must discover its pinning mechanism on a live server, then invent
  the request-URL observation and one-token through-Pi contract. Installed Pi
  documents verbose startup, and routes that flag only to interactive mode
  (`dist/cli/args.js:261`, `dist/main.js:652–660` in the installed
  `@earendil-works/pi-coding-agent` package). It supplies no documented
  prompt-mode URL tracing or max-token flag matching this acceptance.
  Its resolver already prioritizes explicit provider/model
  (`dist/core/model-resolver.js:287–330,425–437`), so the historical cause
  is not established for the installed version.
- **Fails as: wrong-TDD lock-in / unattended hang / loop self-harm.**
  `qwen-run.sh:458–469` does have the curl/Pi gap, but the installed autopilot
  calls this canonical helper (`work/references/qwen-integration.md:3`).
  This is the same live-helper isolation issue already used to hold 00049.
- **Fix:** HOLD for attended diagnosis. Freeze cause, pin mechanism, URL
  observation, token bound and fake-Pi contract before returning an implementation
  PRD to the queue; run any resulting helper change in isolation, without
  dispatching it through itself. Migrate the existing test that explicitly
  forbids invoking Pi in preflight (`test_qwen_run.sh:164–167`).
  Preserve WIP 00051's wrapper/session interface. The already-labeled
  post-release operator signal is not itself a completion blocker.

### Non-blocking

- **N01 — A, template headings:** 00076 Tasks lines 101/113/123, 00077 line 103,
  00078 lines 76/82/91 and 00079 line 64 rename or omit the minimal template's
  literal Foundation/Core headings. Restore headings; keep task content and
  meaningful goals. A planner can still derive these tasks, so this is not
  a coverage-gate blocker. `model_tier_rationale` is allowed authoring metadata
  in the live create-prd skill, not an invalid field.
- **N02 — D/E, refresh moved/already-fixed context:** 00053 task line 97 should
  say “current committed baseline” rather than imply held 00044 must finish;
  its Windows infrastructure is already present. 00074 Problem lines 21–28,
  module line 67 and task line 81 should name `test_write_crash_safety.py`
  and `test_docket_cli.py`; the four crash exceptions already have exact types
  and messages. Keep those as baselines and implement only the remaining
  validator/start/unused-fixture checks. Its re-ground instruction already
  prevents forced rework. 00076 line 71's 799-line claim is now 658; its
  new-module decision remains valid. 00075 Problem line 18 points to 00047 in
  backlog even though it is now done and its cache is implemented. Update the
  path and tense. That line contains a literal `link-ok:` while explaining the
  waiver feature, so the current whole-line waiver exempts this stale pointer;
  it is a non-blocking refresh, not a dangling-citation blocker.
- **N03 — D, residual remote dot segments:** 00067 Solution lines 28–35
  still parses `git@github.com:../other.git` as owner `..`, and
  `git@github.com:demo/...git` as repo `..`. Pure evaluation of its
  prescribed regex confirms both; `repo_slug()` returns captures unchanged
  (`collect.py:76`). Reject parsed owner/name equal to `.` or `..`
  and add cases, or narrow the broad traversal claim. The six explicit current
  examples pass, so this is not an unattended-loop blocker.
- **N04 — D, sweep historical overstatement:** 00073 Problem lines 20–23 says
  only the nested directory gets scanned. Registered roots remain in
  `sweep.py:145`; lines 149–150 add the nested directory alongside them.
  Correct the diagnosis to redundant/nonnormalized roots. Keep the verified
  root-normalization task.
- **N05 — H, portable public rationale:** 00075 Phase 1 task line 164 explicitly
  asks to carry a private project name into public SKILL.md prose. The standing
  repository rule requires a generic rationale. Keep source provenance in
  ignored local evidence; use “a reviewed backlog” in the authored skill.
  Its Risk line 190 also falsely says it has the highest backlog number;
  remove that claim. The gate edits are not by themselves an executing-loop
  dependency, so no mandatory renumber follows.
- **N06 — F/B, model floors and premise checks:** 00079's frontmatter and
  Solution/Task lines 23–26/66–70 promise a behavior-preserving split but use
  sonnet/design-skip; the live authoring rubric calls for opus on equivalence
  obligations. Capture an execution-time test-name multiset, bodies/markers
  and helper inventory, preserve them after the split, and skip/report
  already-completed work. 00069 and 00076 also deserve explicit timing/
  concurrency floor rationales. These are tuning/verification improvements,
  not reasons to claim a 150K planning stall.

### Questions

- **Q01 — 00075, Verify citations and repo symbols line 53:** two contracts still
  carry `(guess)`: citations without a same-line symbol check file/range
  existence, and `New symbols:` declares backticked names after an optional
  list marker. Confirm those exact rules or amend them before authoring tests.
  Clarify that the explicit “none” rule means at least one named symbol must
  occur when multiple symbols share a citing line. The current rule is concrete
  enough to implement, so guess provenance alone is not counted as a separate
  blocker.
- **Q02 — 00076, Nice to have lines 75–79 versus Phase 2 lines 123–127:**
  optional parametrization is also a checkbox task with mandatory acceptance.
  Decide whether to omit it or make it required; do not leave the implementer
  and reviewer to disagree about optional scope.

## Reshapes

- 00078 moved to `dev/local/prds/hold/` on 2026-09-13 for the B05 reasons:
  the pinning mechanism, URL observation, token bound and fake-Pi contract
  need an attended diagnosis before an implementation PRD can be requeued.
- Keep 00052 cohesive despite 294 lines: renderer, audit queue and docs share
  one record contract. The previous review explicitly retained that shape.
  Its core can be planned into audit validation, rendering and recount tasks
  without allocating unrelated PRDs.
- Keep small portfolio fixes separate: each has its own meaningful regression.
  The previous review records the same decision. No unrelated merge merely
  saves ceremony.
- No cross-backlog dependency points to a higher sequence number.
  00053 explicitly owns retargeting the later brief test locations.
  00059/00065 share the same last-60-nonblank/no-backfill contract.
  00061/00062/00068 preserve metadata-failure history and branch isolation.
  00071 precedes 00074/00076/00077 as needed.

## Gaps

- The full native Windows CI job exists, but this review did not establish
  a green native run. Held 00044 is evidence of unfinished verification, not
  an unimplemented infrastructure dependency.
- 00052's runtime prerequisite is not yet met: WIP 00051 has no attempt.py
  or entrypoint yet. Complete it before selecting 00052; its own premise check
  already requires this. Reuse the final producer validators/classifier and
  fixtures: the current producer has added vetting keys
  `inputs_sha256` and `shapes` in `records.py:11–12`. Do not freeze the
  consumer against unfinished producer prose.
- Preserve earlier explicit residuals: partial CI failures can still yield
  history f=0; diagnostics remain visible in UI/stderr by decision; held
  collection-failure UI and real evaluation/calibration work remain outside
  this batch.
- Every fix PRD names a regression requirement; no new strategic PRD is
  justified by this readiness review alone.

## End state after this batch

After the blockers are resolved, the batch adds computed eval evidence,
resilient portfolio collection/building, safer links and clipboard output,
true commit counts, bounded history retention, recoverable memory publication,
judge calls that do not re-enter their own corpus, stronger refusal/atomicity
tests, explicit sweep failures, and smaller test files. Braid rejects symlinked
source entries. A grounding checker becomes shared authoring/review machinery,
with its warning-versus-blocking behavior fixed first. The live Qwen route
investigation and the held-work residuals remain separately owned.

## Frontmatter tuning

| PRD | suggestion | why |
|---|---|---|
| 00052 | keep settled sonnet/design-skip; consider catchup force after 00051 | final producer layout has evolved |
| 00057 | decide only after platform scope | native ACL work changes the size/tier materially |
| 00069 | opus floor | timing determines correctness under the live authoring rubric |
| 00075 | keep opus/design-run/catchup-force | multi-consumer predicates and contracts |
| 00076 | opus floor, catchup force | adversarial atomicity/rollback timing and intervening recovery edits |
| 00077 | catchup force | consumes 00071 and 00076 changes to queue/tests |
| 00078 | HOLD, then reclassify the frozen spec | mechanism is not transcription |
| 00079 | opus floor; consider design run | explicit test-equivalence obligation and helper grouping |

## Verification and limits

- Every backlog PRD was read fully before findings were generated.
- Filename pattern, cross-bucket numbering, task Acceptance clauses,
  frontmatter fields/values, feature uniqueness and template headings checked.
  No stray files or duplicate sequences. All tasks have Acceptance clauses;
  all frontmatter values are recognized and valid.
- Ran `python3 ~/.agents/skills/review-prd-backlog/scripts/check_links.py --root . --json`.
  The only reported backlog/WIP result was 00053's declared future inventory
  output, correctly exempted. No scan errors. Other report/done/hold citation
  findings are outside this gate's target. Direct grounding found 00075's stale
  00047 path, but its citing line contains the literal `link-ok:` waiver, so
  it is correctly excluded from Blocking counts (N02).
- Grounding agents covered 00052–00060, 00061–00069 and 00071–00079. All
  completed, no failed or skipped lens. Local CLI help verified the judge flag
  and Pi's available diagnostics. No historical model measurement was rerun.
- Budget/tier rules read from installed autopilot 0.5.1 plan-tasks steps
  4–4.7: 150K normal per-task estimate, 55K fixed overhead, and a tier floor
  that cannot demote the classifier. These are planning estimates, not the
  user's separate 500K session cap. A conservative current URL-task file set
  is about 113K including fixed overhead before the small PRD/task text;
  no demonstrated indivisible over-budget task was found.
- No full test suite ran: no production code or skill text changed.
  The pre-existing dirty `skills/use-qwen/scripts/test_eval_engines.py`
  was left untouched. No WIP/done contents or execution state were edited.

## Decisions applied

Decision pass 2026-09-08 (B01) and 2026-09-13 (the rest); apply pass 2026-09-13.

| Finding | User choice | Apply status |
|---|---|---|
| B01 / 00057 | Option 2: protect snapshots on both POSIX and Windows | Applied: PRD rewritten (opus, design run); `protect_owner_only` helper, POSIX `os.open` 0600 temporaries plus chmod, Windows `icacls` owner-only, out dir 0700/(OI)(CI)F on creation only, fail-loud exit 1 on protection failure; four fixture tests with a platform-branching `assert_owner_only`, no live stat gate |
| B02 / 00071 | Option 1: preserve `data=None`, add keyword-only `name` | Applied: signature `decide(entry_id, state, file_text=None, path=None, data=None, *, name=None)`; Must have and task acceptance pin the one-read seam, corrupt-queue exit 2, refused-decision exit 1 |
| B03 / 00075 | Option 1: classify library claims from Cargo.lock; source presence decides ok/unverified | Applied: "known packages" wording on lines 46/60, `test_a_locked_crate_without_source_is_unverified_not_unresolved` in task 2 and Test Strategy |
| B04 / 00077 | Option 1: validate all six record keys, reject before persisting, CLI verb `start` not `advance` | Applied: Solution, Must have, tasks and Success Criteria; new tests for a non-object record and a missing `evidence_text` behind readable records; `test_start_reports_a_failed_queue_write`; one-read seam and 00071 exit distinction preserved |
| B05 / 00078 | Option 1: HOLD for attended diagnosis | Applied: `mv` to `dev/local/prds/hold/` |
| Q01 / 00075 | Option 1: confirm both rules, strip `(guess)`, any-symbol-in-range rule explicit | Applied on line 53 |
| Q02 / 00076 | Option 1: parametrization and re-bind become Must have; Phase 2 renamed "Test hygiene" | Applied |
| N03 / 00067 | Accepted: reject owner/repo equal to `.` or `..`, add cases | Applied: Solution, Must have (four rejected shapes), task |
| N06 / 00079 | Accepted: opus floor, design run, test multiset/helper inventory equivalence acceptance | Applied: frontmatter, Must have, new inventory task, `Phase 1: Core` none |
| N06 / 00069, 00076, 00077 | Accepted: opus floor on 00069/00076; catchup force on 00076/00077 | Applied with rewritten tier rationales |
| N06 / 00052 | Accepted: catchup force | Applied |
| N01 | Template headings | Applied: 00076 Phase 0/1 restored, 00077 Phase 1: Core, 00079 Phase 0: Foundation plus Phase 1: Core; 00078 untouched (held) |
| N02 | Stale context | Applied: 00053 baseline wording; 00074 now names `test_write_crash_safety.py` (lines 29/54/79/104) and `test_docket_cli.py` (start test line 122, unused capsys lines 251/277/302) and treats already-bound cases as baseline; 00076 line count 658; 00075 cites done 00047 |
| N04 | Sweep diagnosis | Applied: 00073 item 2 describes the redundant non-normalized root |
| N05 | Portable rationale | Applied: 00075 Phase 1 task uses a generic rationale; false highest-number claim removed |

### Apply-pass verification (2026-09-13, HEAD 076b306)

- Lens A re-run on 00052, 00053, 00057, 00067, 00069, 00071, 00073, 00074,
  00075, 00076, 00077, 00079: every task line carries `Acceptance:` (counts
  match per file), minimal-template headings present in order, no `{...}`,
  TBD or `(guess)` markers remain (the one `{path}` hit in 00073 line 61 is an
  f-string inside a code span), frontmatter fields and values all recognized,
  every file under 200 lines (largest: 00075 at 190).
- `check_links.py --root . --json` on backlog/WIP: only 00053 line 97 and
  00079 line 69, both inventory files those PRDs declare they will create;
  exempt forward references. No dangling citation.
- Grounding re-checked for the edits: `docket.py:124` signature and `:258`
  caller; `docket.py:213-217` six indexed keys; `write.py:178` catches only
  `WriteError`/`KeyError` while `test_write_crash_safety.py:630` covers the
  missing key, so 00071's null-`kind` task stands; `collect.py:447-465`
  temporaries and `:506-507` mkdir; `sweep.py:145-150` root handling;
  `.github/workflows/ci.yml:59-60` Windows job; `test_conftest_fixtures.py:18`.
- Lifecycle: backlog holds 26 PRDs, hold holds 21 including 00078; wip and
  done untouched; the pre-existing dirty test file untouched.
- Not run: the test suites (no code changed) and `braid --check` (no skill
  text changed).
