# Backlog review - agent-skills - 2026-09-05

Verdict: NO-GO (2 Blocking open: WIP 00015 and PRD 00057's permission scope)

Target: dev/local/prds/backlog. The original 17 PRDs were read in full,
reviewed through all eight lenses, and corrected. Another 22 PRDs arrived
during apply; all were subsequently read, grounded and reviewed as a set.
Their findings and applied corrections are in the
[supplement](backlog-review-2026-09-05-supplement.md).
The current inventory is 35 backlog, 1 WIP, 19 hold and 18 done; discovery is absent.
This is a specification review. No implementation or live evaluation ran.

The sole pending human scope choice is 00057: native owner-only access on
both hosts, explicitly POSIX-only protection, or deferral. The user already
chose the entire Python suite for 00044. WIP 00015 needs its active owner to
apply the [prepared criterion correction](backlog-review-2026-09-05-wip-handoff.md).

## Map

Counts and verdicts below describe the applied documents. READY means the
individual artifact is ready; it does not override the two open batch blockers.
Original pre-apply findings are retained below as evidence, with dispositions
in Decisions applied.

| # | PRD | template | lines | subsystems | depends on | verdict |
|---|---|---|---:|---|---|---|
| 00016 | [memory queue](../prds/backlog/00016-queue-lands-in-wrong-repo-v1.md) | minimal | 114 | memory queue | WIP 00015 | READY |
| 00017 | [memory/index transaction](../prds/backlog/00017-malformed-memory-half-written-v1.md) | minimal | 128 | memory/index transaction | 00015/00016 | READY |
| 00020 | [changelog CI](../prds/backlog/00020-changelog-skill-presence-check-v1.md) | minimal | 125 | changelog CI | 00029 deferred only | READY |
| 00021 | [debrief UI](../prds/backlog/00021-risks-tile-fake-zero-v1.md) | minimal | 104 | debrief UI | none | READY |
| 00022 | [Node CI/docs](../prds/backlog/00022-node-ci-and-install-docs-v1.md) | standard | 209 | Node CI/docs | earlier CI edits | READY |
| 00030 | [survey traversal](../prds/backlog/00030-survey-prunes-skip-dirs-deep-v1.md) | minimal | 86 | survey traversal | none | READY |
| 00032 | [sweep output validation](../prds/backlog/00032-sweep-validates-out-late-v1.md) | minimal | 88 | sweep output validation | none | READY |
| 00034 | [memory typing timeout](../prds/backlog/00034-timeout-leaks-prompt-to-disk-v1.md) | minimal | 101 | memory typing timeout | none | READY |
| 00035 | [live purge helper](../prds/hold/00035-local-name-gc-guard-v1.md) | minimal | 92 | live purge helper | isolated execution | HOLD |
| 00036 | [skill scaffolding](../prds/backlog/00036-create-skill-scripts-help-and-union-path-v1.md) | minimal | 105 | skill scaffolding | none | READY |
| 00038 | [Braid docs/help](../prds/backlog/00038-braid-docs-flags-and-backup-paths-v1.md) | minimal | 118 | Braid docs/help | none | READY |
| 00044 | [full Windows Python suite](../prds/backlog/00044-windows-ci-junction-claim-v1.md) | standard | 243 | full Windows Python suite | 00020/00022 | READY |
| 00047 | [citation cache](../prds/backlog/00047-check-links-repeated-stats-v1.md) | minimal | 76 | citation cache | none | READY |
| 00049 | [live Qwen helper](../prds/hold/00049-qwen-completion-status-v1.md) | standard | 203 | live Qwen helper | isolated execution | HOLD |
| 00050 | [attended comparison](../prds/hold/00050-qwen-ivan-capability-eval-v1.md) | standard | 265 | attended comparison | 00049/00051/00052 + calibration | HOLD |
| 00051 | [evaluation harness core](../prds/backlog/00051-qwen-eval-harness-core-v1.md) | standard | 565 | evaluation harness core | 00044; 00049 before real rounds only | READY |
| 00052 | [evaluation renderer/docs](../prds/backlog/00052-qwen-eval-harness-report-v1.md) | standard | 294 | evaluation renderer/docs | 00051 | READY |
| 00053 | [portfolio test split](../prds/backlog/00053-split-oversized-brief-suites-v1.md) | minimal | 114 | portfolio test split | 00044; migrate later locations | READY |
| 00054 | [metadata errors](../prds/backlog/00054-non-json-metadata-kills-collect-v1.md) | minimal | 90 | metadata errors | 00053 | READY |
| 00055 | [metrics timestamps](../prds/backlog/00055-bad-metrics-ts-aborts-run-v1.md) | minimal | 99 | metrics timestamps | 00053 | READY |
| 00056 | [CI collection errors](../prds/backlog/00056-ci-failure-fakes-no-ci-v1.md) | minimal | 93 | CI collection errors | 00053 | READY |
| 00057 | [snapshot access permissions](../prds/backlog/00057-data-json-world-readable-v1.md) | minimal | 84 | snapshot access permissions | 00044/00053; scope pending | FIX — human scope pending |
| 00058 | [portfolio URL policy](../prds/backlog/00058-page-links-accept-javascript-urls-v1.md) | minimal | 100 | portfolio URL policy | 00053 | READY |
| 00059 | [build input recovery](../prds/backlog/00059-build-dies-on-torn-inputs-v1.md) | minimal | 97 | build input recovery | 00053 | READY |
| 00060 | [history append](../prds/backlog/00060-torn-history-fuses-next-row-v1.md) | minimal | 79 | history append | 00053/00059 | READY |
| 00061 | [local facts/history markers](../prds/backlog/00061-meta-failure-fakes-hygiene-nags-v1.md) | minimal | 89 | local facts/history markers | 00053/00054/00056 | READY |
| 00062 | [commit counts](../prds/backlog/00062-commit-cap-hides-true-count-v1.md) | minimal | 101 | commit counts | 00053/00061 | READY |
| 00063 | [registry diagnostic](../prds/backlog/00063-missing-registry-tracebacks-v1.md) | minimal | 78 | registry diagnostic | 00053 | READY |
| 00064 | [Braid symlink inventory](../prds/backlog/00064-braid-follows-symlinked-skill-v1.md) | minimal | 82 | Braid symlink inventory | 00044 | READY |
| 00065 | [bounded history tail](../prds/backlog/00065-build-reads-whole-history-v1.md) | minimal | 81 | bounded history tail | 00059 | READY |
| 00066 | [clipboard escaping](../prds/backlog/00066-clipboard-markdown-unescaped-v1.md) | minimal | 80 | clipboard escaping | 00053/00058 preserved | READY |
| 00067 | [remote parsing](../prds/backlog/00067-remote-url-passes-query-dotdot-v1.md) | minimal | 84 | remote parsing | 00053 | READY |
| 00068 | [branch lookup](../prds/backlog/00068-redundant-branch-resolve-v1.md) | minimal | 83 | branch lookup | 00053/00062 | READY |
| 00069 | [announcement tests](../prds/backlog/00069-announcement-window-injectable-v1.md) | minimal | 95 | announcement tests | 00053 | READY |
| 00070 | [live purge retention](../prds/hold/00070-purge-trash-first-guarantee-v1.md) | minimal | 91 | live purge retention | isolated execution | HOLD |
| 00071 | [memory recovery](../prds/backlog/00071-distil-publish-recovery-v1.md) | minimal | 154 | memory recovery | 00015–00017 | READY |
| 00072 | [judge transport](../prds/backlog/00072-distil-judge-no-persistence-v1.md) | minimal | 94 | judge transport | preserve 00034/00044 | READY |
| 00073 | [sweep setup/YAML](../prds/backlog/00073-sweep-loud-failures-v1.md) | minimal | 128 | sweep setup/YAML | 00032 | READY |
| 00074 | [memory regression quality](../prds/backlog/00074-distil-tests-bind-intent-v1.md) | minimal | 91 | memory regression quality | 00017/00071 | READY |

## Findings

### Blocking

#### B01 — 00016: the migration guard invalidates itself

- **Lenses B/C/D; location:** `00016` Tasks, Phase 0, third task, lines 88–94.
- The existing-test migration runs only if a global count of
  `docket.main(["save"` is exactly seven. The preceding two tasks add save
  calls; WIP 00015 can add more. Seven is currently true, but need not be
  true when this task runs. Skipping the migration then leaves tests loading
  the cwd queue after the command moved its default to the proposals parent.
- **Fails as: rework thrash.** Fix: inventory and migrate the affected
  existing tests by behavior/name, preserve new tests and 00015 exit codes,
  and retain seven only as historical evidence. Do not skip required
  migration because unrelated tests were added.

#### B02 — 00017: deleting a failed update contradicts rollback

- **Lenses B/C/D; location:** `00017` Must have, lines 46–47, versus Success
  Criteria, lines 117–118; Phase 0 only tests a newly created memory.
- Every index failure must leave “no memory file”, while the store must also
  remain “as it was”. Existing `write_memory` overwrites an update target
  (`skills/distil-memory/scripts/write.py:48–56`); update tests already exist
  in `test_write.py`. Unconditional deletion passes the proposed new-entry
  regression while destroying a pre-existing memory and breaking retry.
- **Fails as: wrong-TDD lock-in.** Fix: remove only newly created targets;
  restore original bytes for updates, preserve the original index on
  failure, and add regressions for both new and update rollback.

#### B03 — 00020: completion requires a held successor

- **Lenses C/D/G; location:** `00020` Success Criteria, lines 119–120,
  versus Phase 0's exact fourteen-name `GRANDFATHERED` assertion.
- The success section requires 00029 to backfill the changelog and empty the
  list. 00029 is parked in `hold/` and consumes this PRD's check; it will not
  run in this batch. Requiring both fourteen entries and an empty list at
  this PRD's completion is contradictory.
- **Fails as: rework thrash.** Fix: retain the fourteen-name contract here;
  move the 00029 sentence to an explicitly deferred follow-up outside this
  PRD's success criteria. The current 47/14/33 inventory is verified.

#### B04 — 00036: negative searches forbid the tests themselves

- **Lenses B/C/D; location:** `00036` task 3, line 90, and Success Criteria,
  line 100.
- Changing printed step 3 cannot remove all `.claude/skills` references:
  `init_skill.py:9–10` has existing examples, the validator deliberately
  permits compatibility paths at `validate_skill.py:175,180`, and its tests
  contain those paths. The new negative stdout assertion also contains the
  forbidden string in its source.
- **Fails as: rework thrash.** Fix: assert the captured validation-step
  output uses the interpreter-prefixed union path; scope any source search
  to that printed statement. Preserve compatibility handling and fixtures.

#### B05 — 00038: wrapped argparse help violates the acceptance text

- **Lenses B/D; location:** `00038` Success Criteria, lines 109–111.
- “No line ... ends at a bare metavar” rejects ordinary argparse wrapping.
  Adding the five required help strings to a fresh parser in memory still
  prints `--agents-root AGENTS_ROOT` on one line and its description below.
  The same applies to the other long root options.
- **Fails as: rework thrash.** Fix: require a nonempty description for each
  named parser action, allowing continuation lines; do not require an
  unrelated formatter change.

#### B06 — 00044: four jobs conflicts with the earlier Node job

- **Lenses C/E; location:** `00044` Phase 0 acceptance, line 136, Exit
  Criteria, line 143, and Happy path, line 176; `00022` Feature: Node job.
- Current CI has `test`, `shell`, `lint`. After 00022 adds `node`, adding
  `windows` produces five jobs, so `assert len(d['jobs']) == 4` rejects the
  correct combined result.
- **Fails as: rework thrash.** Fix if retained: assert the Windows job and
  its command, and preserve the existing jobs without fixing their total.

#### B07 — 00044: the Windows job has known unsupported prerequisites

- **Lenses B/D; location:** `00044` Feature: Windows test job, lines 57–62,
  and Risks, lines 189–191.
- Checkout plus setup-uv is insufficient for the full collected suite.
  `.github/workflows/ci.yml:31–53` now installs mise, rg and ast-grep after
  real Linux failures. `test_sweep_resolvers.py:120–145` requires mise;
  lines 76–99 directly execute an extensionless `/bin/sh` fixture.
  `test_check_links.py:95–104` assumes POSIX `chmod(0)` unreadability.
  The PRD excludes platform repairs and treats them as unknown future work.
- **Fails as: rework thrash.** Recommended: HOLD this PRD until its Windows
  support scope is settled. Alternatives: include the concrete prerequisite
  and fixture-portability work, or explicitly scope the job to a portable
  Braid subset and narrow the README claim. This is code-based evidence,
  not a claim that a Windows runner was exercised during this review.

#### B08 — 00050: consumers run before their producers

- **Lenses E/G; location:** `00050` Problem Statement, lines 20–25,
  Foundation Layer, and Phase 0's first task.
- 00050 requires both 00051 `vet/run` and 00052 `render`, but ascending
  selection runs 00050 first. Neither harness implementation exists yet.
- **Fails as: order break.** Recommended: HOLD 00050 through harness
  implementation and calibration, then allocate it a free tail number and
  update references. Alternative: renumber it to 00053 now, explicitly
  resolving Q03 before admitting the resulting batch.

#### B10 — 00050/00051: the harness cannot render the required Ivan brief

- **Lenses B/C/D/G; location:** `00050` Identical constrained implementation
  briefs, lines 65–73; `00051` Task spec and Prompt rendering, lines 74–79,
  108–118.
- 00050 requires architecture/invariants, read anchors and the current Ivan
  reading budget. 00051's spec exposes none of these inputs and its TDD
  template omits them. The installed Qwen TDD reference itself has an
  Architecture slot; Ivan's role and dispatch reference add read boundaries
  and a budget. Hand-editing prompts would violate the sealed,
  harness-produced, identical-input requirement.
- **Fails as: wrong-TDD lock-in.** Fix: define explicit architecture,
  read-anchor/allowlist and reading-budget inputs in 00051, pin their
  rendering from the installed role, and have 00050 consume them. Test
  equality across engines and absence of solution/acceptance hints.

#### B11 — 00051: the harness's oracle overlay becomes candidate edits

- **Lenses B/C; location:** `00051` Attempt lifecycle, lines 138–160;
  Attempt record contract, lines 213–216; integration's `pass/noop` cases.
- The template is at `first^`; TDD overlays tests from `last`, then snapshots
  the diff against the original template SHA. Those harness-created test
  changes enter `changed`; in TDD, `stray` permits only writable paths.
  A compliant candidate therefore gets `stray-edit`, and a no-op has a
  nonempty diff. Comparing oracle hashes to the old template also rejects
  the intended overlay.
- **Fails as: wrong-TDD lock-in.** Fix: separately identify the historical
  base and the sealed dispatch snapshot after the oracle overlay. Compare
  candidate edits and oracle integrity to the latter; reconstruct gates
  from that snapshot plus only candidate changes. Include a changed-test
  fixture proving TDD pass, no-op and mutation remain distinguishable.

#### B12 — 00051: llama metadata is requested from the wrong URL and key

- **Lens D; location:** `00051` Engine adapters, lines 185–188, and its
  Phase 1 adapter-test acceptance.
- Qwen provider `baseUrl` includes `/v1` (also documented in use-qwen's
  configuration example). Appending `/props` yields `/v1/props`; the local
  llama server source registers `/props`. Its context size is
  `default_generation_settings.n_ctx`, not a top-level `n_ctx` field.
- **Fails as: wrong-TDD lock-in.** Fix: derive the server root from the
  provider API URL, request `/props`, and pin field extraction to the real
  response shape. Test with a sanitized actual-shape response and a `/v1`
  provider URL, including unavailable metadata handling.

#### B13 — 00051: no output does not prove the engine never started

- **Lenses B/C/E; location:** `00051` Attempt lifecycle, lines 148–163, and
  integration acceptance, lines 363–369; `00050` single-attempt rule.
- A helper with no identity line or output is labelled pre-launch
  `DISCARDED:harness` and retried. An engine can launch, edit, then exit
  before flushing either. Fresh trees prevent contamination but do not make
  that second trial a valid one-shot comparison; the first run can disappear
  from the effective scoreboard.
- **Fails as: wrong-TDD lock-in/goal reversal.** Fix: track an explicit
  adapter launch boundary. Retry only an error positively observed before
  process creation; any post-launch or uncertain failure remains a final
  recorded attempt. Add an edit-then-silent-exit fixture; cap a verified
  pre-launch retry at one.

#### B14 — 00051/00052/00050: producer records do not close the consumer contract

- **Lenses B/C/G; location:** `00051` Attempt record contract and Outcome
  and classification, lines 205–237; `00052` Scoreboard, lines 74–84;
  `00050` Rescue accounting, lines 121–127, and final acceptance.
- The supposedly self-contained record omits a gate-timeout indicator
  needed to re-derive `SUSPECT`, leaves nested data shapes and preparation
  failure encoding undecided, and supplies no pinned source for the
  renderer's task `kind/repo`. Baseline results are recorded but their
  admissibility is absent from the PASS predicate. The experiment also
  requires first-edit time, available usage and review effort, while the
  producer/renderer contracts only pin dispatch `wall_s` and usage-limit
  status. Independently written tests can choose incompatible schemas or
  admit a gate pass despite an invalid attempt baseline.
- **Fails as: wrong-TDD lock-in.** Fix: freeze the shared JSON shapes and
  field ownership in these PRDs before their separate test authors run:
  explicit bounded-process and baseline statuses; null rules and outcome
  precedence; task metadata in spec/run records consumed by render; timing
  and available-usage fields with null when unavailable; review effort in
  audit rows. Require baseline validity before PASS and cross-PRD fixtures
  that exercise preparation failure, baseline drift and gate timeout.

#### B15 — 00035/00049: the batch modifies helpers it executes

- **Lenses B/E; location:** `00035` Phase 0 changes `purge_devlocal.py`;
  `00049` Phase 1 changes `qwen-run.sh`.
- Installed autopilot 0.4.1 `run-autopilot/cli/loop.py:63–70,332–338,1005`
  invokes the projected purge helper on batch drain. Its Qwen integration
  invokes the shared `~/.agents/skills/use-qwen/scripts/qwen-run.sh` during
  work and preflight. Both resolve to this source repository. These are
  real batch consumers, not hypothetical overlap. 00051's standalone
  Sonnet helper does not change the plugin's separate review helper.
- **Fails as: loop self-harm.** Recommended: isolate 00035 and 00049 from
  the ordinary backlog batch, each as the final PRD in a dedicated batch
  (or HOLD for attended implementation); complete 00049 before real
  evaluation. Do not dispatch 00049 implementation through the Qwen helper
  being edited. The narrowing GC predicate is otherwise grounded and its
  existing accepted-store tests still fit.

#### B16 — WIP 00015: its suite-wide criterion requires later 00017

- **Lenses C/E/G; location:** `wip/00015` Success Criteria, line 94;
  `00017` Phase 0 index-update task.
- 00015 requires no xfailed tests anywhere under distil-memory, but
  `test_write.py:577` contains the expected failure that 00017 explicitly
  removes. The active queue-corruption work cannot meet this clause within
  its scope; its review can demand an unplanned early implementation of 00017.
- **Fails as: rework thrash/order break.** Resolution belongs to the active
  work session: limit 00015's no-xfail assertion to its docket regression,
  preserving the unrelated expected failure until 00017. This review will
  not edit WIP contents: the invoked skill explicitly forbids that. Confirm
  the active session has resolved the handoff before calling the current
  batch ready.

### Non-blocking

- **N01 — template omissions (A):** minimal PRDs 00016, 00021, 00030,
  00032, 00034, 00035, 00036 and 00047 omit `### Phase 1: Core`;
  standard PRDs 00022/00044 omit implementation `### Phase 2: Integration`.
  Their decomposition says there is no work at that layer. Add the literal
  template headings with an explicit no-work entry when touching them;
  do not invent tasks. Current plan-tasks accepts minimal requirements and
  derives decomposition; the old Feature-keyed review coverage gate has
  been retired, so no coverage-gate failure is claimed here.
- **N02 — module mapping (A/C):** 00049's graph names `Dispatch Completion
  fixtures`; 00051 names `Test fixtures` and `CHANGELOG entries`, without
  corresponding Module blocks. Its CLI and regression/fixture files also
  lack explicit module ownership. Fold those responsibilities into named
  modules while preserving all capabilities and tasks.
- **N03 — historical snapshots (D):** 00022 Success Metrics and App suite
  steps still name 16 portfolio tests and a two-file test command. Current
  package includes `smoke.a11y.test.js`; 44 tests pass. Earlier 00021 will
  also change debrief's current 47 to 48. Commands use `npm test` correctly;
  remove fixed historical totals from current success metrics.
- **N04 — reporter portability (B):** 00021/00022 refer to literal
  `# pass`/`# fail` output. This host's default reporter prints different
  summary syntax. Prefer exit status and failure counts, or explicitly
  select TAP where matching text is intended.
- **N05 — survey claim (B/D):** 00030 Solution says pruning “bounds both
  the walk and the selection”. It removes excluded subtrees but still
  enumerates eligible source files before the cap. State that remaining
  cost is proportional to eligible tree size; do not add new scope.
- **N06 — stale lifecycle statements (D/H):** 00049's final docs task,
  00050 Problem/Risks, 00051 final Risk, and 00052 Runbook feature all
  describe pending repairs to held 00010. The PRD is in `done/`; its review
  still invalidates the old scores. Correct the location/status and name
  deferred repairs explicitly without treating a lifecycle move as evidence
  the scores became valid. Never edit the completed PRD from this review.
- **N07 — output layout (C/E):** 00050 Repository Structure places
  `evidence.md/report.md` at the bundle root, while 00052 writes exclusively
  below `runs/<run-id>/`. Align the experiment tree and its comparison-prose
  destination with the renderer. Re-rendering must not silently erase that
  prose; pin its separate file or preservation rule.
- **N08 — shared skill path rule (A/H):** 00052's exact SKILL.md bullet
  uses `scripts/run_eval_harness.py`. Use the canonical
  `~/.agents/skills/use-qwen/scripts/run_eval_harness.py` when giving a
  runnable command, per repository AGENTS.md.

### Questions

- **Q01 — harness size:** retain 00051 as a single contract-dense,
  design-reviewed PRD, or split at the sealed-input/attempt-runner seam?
  It has 428 lines and seven tasks; neither length alone nor existing file
  sizes demonstrate an unsplittable 150K task. See Reshapes.
- **Q02 — audit input uniqueness:** 00052 Audit queue validates unknown
  attempts and verdict enums but leaves repeated rows for one attempt
  unspecified. Freeze one row per attempt, rejecting duplicates, or state
  another intentional replacement rule before implementing counts.
- **Q03 — calibration and an unstarted experiment:** 00050's Isolated
  single-attempt runs (lines 99–112) and Phase 0 require two attended
  calibration trials using the future harness, server restarts, and a
  recorded effort choice. No record exists. Its explicit shortfall exit
  prevents an indefinite wait, so this is not labelled an unattended hang.
  Clarify whether an unstarted record parks this PRD or completes it despite
  the later tasks requiring twelve attempts and a rendered report;
  recommended: HOLD until calibration is recorded. Also pin an operator
  attestation for the live effort level: 00051 only records a declared
  value, whereas 00050 asks to verify it. Missing prerequisites are not
  scored model failures. B09 was withdrawn into this question during triage;
  finding identifiers otherwise remain stable.

## Reshapes

- 00035 and 00049 moved with mv to hold: they edit projected helpers that
  the active autopilot batch calls. Run each as the final item of a dedicated
  batch or with an attendant; never dispatch 00049 through its own Qwen helper.
- 00050 moved with mv to hold: complete the harness and record attended
  effort calibration first. On reactivation assign an unused tail number
  above all producers and update references; its current number is not an
  executable order. Missing calibration leaves an unstarted PRD, not a
  completed empty experiment.
- 00070 was moved to hold by the concurrent author while this review
  prepared the same isolation disposition. Its live purge-helper reason is
  the same as 00035. This review preserved that move.
- 00044 stays in backlog with the user's full Python-suite choice. It now
  owns runner tools, portable fixtures, brush path safety, proposal directory
  publication and native Windows evidence. Opus/design review/catchup force
  reflect that expanded scope.
- 00051 stays cohesive and design-reviewed. Its 565 lines carry shared
  schemas and isolation contracts; actual tasks still require the planner's
  150K estimate. No line-count-only split or budget waiver was introduced.
  The contract repair necessarily grew the document despite trimming some
  redundant claims. 00052 remains a cohesive renderer/docs PRD.
- Prior explicit decisions remain: keep small 00047 independent and retain
  00022's size exception. No unrelated merge was invented.

## Gaps

- Held 00029 owns the remaining fourteen grandfathered changelog entries.
- Historical 00010 is done, but its old comparative scores remain invalid;
  no pending repair or lifecycle move is treated as validating evidence.
- Real evaluation still needs operator calibration and available engines.
  No live model was dispatched and no server was restarted during review.
- 00056 deliberately keeps the chosen current-CI warning scope. Historical
  per-field unknown CI values remain a documented limitation of the existing
  history schema; this review does not invent its migration.
- 00057's platform-permission scope is still undecided.
- No new strategic roadmap was invented. assess-evolution remains an
  optional separate assessment.

## End state after this batch

The reviewed work makes memory queues and publication failures recoverable,
improves truthful portfolio/debrief reporting, adds full Windows Python and
Node CI coverage, corrects traversal and CLI behavior, and supplies a
reproducible evaluation harness. The additional portfolio PRDs preserve
history semantics and test coverage while correcting metadata, URLs, counts
and input recovery. Live-helper changes and the calibrated comparison remain
isolated in hold. Model routing and trust are unchanged.

## Frontmatter tuning

All values parse as valid. `model_tier_rationale` is documented by the live
create-prd skill as a deliberately ignored annotation; it is not an invalid
runtime knob. No PRD contains `design_gate: user` or an unresolved task marker.

| PRD | suggestion | why |
|---|---|---|
| 00016, 00017 | applied `catchup: force` after WIP 00015 | shared queue CLI and tests are changing live |
| 00017 | applied `default_model: opus` | rollback of persisted updates and out-of-repo memory writes need judgment |
| 00030 | revisit floor rationale | traversal behavior is specified, but neither total ordering nor all implementation text is pinned |
| 00038 | record a considered prose/tier rationale | help descriptions are authored, not literal transcription |
| 00047 | retain skip flags and explicit keep-separate decision | prior review already chose this scope; cache equivalence deserves a stated tier rationale |
| 00049–00051 | retain `opus`; retain design review | process lifetime, evidence contracts and experimental judgment |
| 00052 | B14/Q02 settled; retained `sonnet` + `design: skip` | it is only transcription once its inputs and aggregation rules are exact |
| older PRDs with `rework_cap: 5` | optional return to default 2 | valid but higher than current default; not a remedy for ambiguous acceptance |

## Gate honesty and verification

- All eight lenses ran across the expanded 39-document review. Three
  read-only grounding agents returned initial and supplemental findings;
  the last five drafts were re-read and grounded after their content arrived.
  Cross-document and goal/size lenses stayed with the primary reviewer.
- Live law: create-prd and all three templates, plus installed autopilot
  0.4.1 plan-tasks steps 4–4.7. The newly landed metric rule was re-read:
  use named regressions, not mutable suite totals.
- After apply: 39 documents contain 99 tasks, each with Acceptance.
  Template heading/order, Module presence, unique Feature headings, no
  unresolved markers, no trailing whitespace, filename shape, frontmatter
  values and cross-directory numbering checks passed. No duplicate sequence
  exists. The WIP document was read but never edited.
- Final citation scan: 437 repository-wide findings, no scan errors.
  Three remain under backlog/WIP: 00053's declared inventory output and
  00016/WIP 00015's runtime queue/fixture. All are declared outputs, so no
  unresolved input citation remains. The checker and its gates were unchanged.
- Behavioral grounding included 47 passing debrief Node tests and 44
  passing portfolio Node tests at the initial snapshot, repeated-stat and
  argparse probes, and a later 1,014-test Python collection preflight.
  Subsequent commits changed source/test inventory. No broad Python pass
  or native Windows pass is claimed by this PRD-only review.
- Native Windows remains a mandatory 00044 implementation validation.
  Read-only gh authentication was verified after retrying outside the
  network sandbox; this does not prove workflow permissions or a Windows run.
- Existing-input budget screening was below roughly 103K before task text
  and future files for the initial set. This is not a final estimate:
  future harness modules and historical evaluation repos require task-level
  planning. The user's 500K session cap is a separate setting.
- git diff --check passed. This review edited only ignored PRD/review
  artifacts; tracked source changes and commits belong to concurrent work.
  It created no worktree, branch or executed plan to clean up.
- Concurrent edits were preserved: the initial whole-file patch for 00053
  refused stale content; the current changes to 00053/00061/00069 were read
  and integrated before retry. The concurrent 00070 hold move was retained.
  No PRD patch failure was silently ignored.

## Decisions applied

The user's instruction delegates routine engineering corrections and limits
questions to human intent. The full decision summary was printed before
each apply pass.

| Findings | Disposition |
|---|---|
| B01–B06 | Resolved: behavioral migration guard; prior-state rollback; deferred grandfather backfill; scoped stdout checks; wrapped help; CI jobs preserved. |
| B07 | User chose the entire Python suite. Applied to 00044, including native prerequisites and reproduced portability surfaces. |
| B08/Q03 | Resolved by holding 00050 and pinning calibration/reentry conditions. |
| B10–B14 | Resolved: Ivan input fields, post-overlay sealed baseline, correct props endpoint, verified pre-process retries, exact producer/consumer records and outcome precedence. |
| B15 | Resolved by holding 00035/00049;00070 has the same isolated disposition. |
| B16 | Open: exact replacement supplied in the WIP handoff; only its active owner applies it. |
| N01–N08 | Applied: headings, ownership, snapshot metrics/reporters, traversal limits, historical status, output layout and canonical command path. |
| Q01 | Keep 00051 cohesive with design review and actual task budgeting. |
| Q02 | Reject duplicate audit rows; validate before replacing rendered output. |
| Supplemental routine findings | Applied to18 new backlog PRDs plus a factual correction in held 00070; see supplement. 00063/00064 were grounded and retained. |
| Supplemental 00057 | Open human scope choice; its PRD is unchanged pending that answer. |

To reach GO: resolve 00057, apply the WIP criterion correction in its owning
session, and recheck the resulting inventory. Neither open blocker is waived.
The review skill explicitly says “Never touch wip/ or done/ contents”;
that is why this review prepared an owner handoff instead of editing 00015.
