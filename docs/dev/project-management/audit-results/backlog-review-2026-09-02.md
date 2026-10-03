# Backlog review - agent-skills - 2026-09-02

Verdict: GO (user waived: lens A's ~200-line heuristic on 00014, 00022,
00025, 00029; see Decisions applied)

Pre-apply verdict was NO-GO (6 Blocking open; 1 systemic across all 38
PRDs). The Findings, Reshapes and Gaps sections below are the pre-apply
record; the Map and Decisions applied reflect the backlog as it stands now.

Target: `dev/local/prds/backlog/` (38 PRDs at review start, 00011-00048, all
emitted by the agoge walkthrough of `agoge-2026-08-31.md`; 31 after the
apply pass, 7 absorbed originals in `hold/`). Context: `wip/` holds 00010
(in-flight build, untouched), `done/` holds 00001-00009, `hold/` was empty,
`dev/local/discovery/` does not exist. Law: `create-prd` SKILL.md plus
`assets/minimal.md` and `assets/standard.md` as of today. Loop machinery
consulted: autopilot plugin 0.3.0 (`plan-tasks` steps 3-6,
`review-coverage-format.md`).

## Gate honesty

- Lens D (grounding) ran through six read-only subagents, one per subsystem
  group; all six returned. Every referenced file, symbol and xfail test was
  checked with `rg`/Read against master at `636d94f`. Corrections are listed
  under Non-blocking.
- The "coverage-gate block" mechanism in this skill's failure catalog is
  stale for autopilot 0.3.0: the `#### Feature:`-keyed coverage convention was
  retired (`review-coverage-format.md` checks only frontmatter, reviewer
  sections, Verdict and Tests lines). Missing Feature headings are therefore
  Non-blocking compliance, not Blocking. Missing `Acceptance:` clauses remain
  Blocking (plan-tasks step 4 copies them verbatim; without them the planner
  invents the contract).
- `check_links.py` reported 9 hits in `backlog/`/`wip/`; all are probe paths
  quoted inside fenced evidence blocks (`dev/local/tmp/marker.json`, a
  `--help` literal, a stray queue path), not citations an implementor would
  resolve. Classified Non-blocking; see Gaps for the checker improvement.
- No lens skipped. Budget/tier questions consulted plan-tasks 4.5-4.7; no PRD
  is near the 150K budget (largest was 93 lines pre-rewrite, 273 after).
- Apply pass: the 31 rewrites were produced by parallel subagents from one
  shared brief, then re-checked here. The post-rewrite lens A re-run is a
  script (`lens_a.py`, session scratchpad): template inference from headings,
  heading order against `minimal.md`/`standard.md`, `Acceptance:` on every
  task line, frontmatter field/value validity, stub and `(guess` markers,
  unbalanced braces outside code spans, line count. Result on the final tree:
  31 files, 0 findings. Prose quality and contract exactness of the rewrites
  were read by hand, not scripted; the G2 batch's own grounding corrections
  are listed under Decisions applied.
- One rewrite-agent invention survived unmarked and is left as decided:
  00019's `render(payload, { url: null })` call shape (a test helper the task
  itself defines, so the planner cannot misread it).

## Map

Post-apply state. At review start every PRD carried the `standard.md`
skeleton at `##` level only (no Capability/Feature blocks, no Repository
Structure tree, no Module blocks, no Dependency Graph, no task checklist, no
`Acceptance:` clauses, no Exit Criteria, no Critical Scenarios); root cause
is agoge `prd-emission.md` mapping packets at `##` level (upstream defect,
see Gaps). Each PRD was rewritten onto the fitting template. Frontmatter on
all: `default_model: opus`, `rework_cap: 5`; `catchup: skip` + `design:
skip` on 00021, 00024, 00032, 00033, 00034, 00035, 00036, 00038, 00047;
`design: skip` on 00029. Lines are post-rewrite; "std" is `standard.md`.

| # | PRD | template | lines | subsystems | depends on | verdict |
|---|---|---|---|---|---|---|
| 00011 | collected title blanks page | minimal | 113 | brief-portfolio + debrief-meeting `build.py` | - | READY |
| 00012 | dotdot bypasses trash protection | minimal | 88 | brush `trash_untracked.py` | - | READY |
| 00013 | build --dir overwrites live dashboard | minimal | 107 | brief-portfolio `build.py`, SKILL.md | - | READY |
| 00014 | braid check reports; state writes fail clean (absorbed 00039, 00040) | std | 231 | braid `cli.py` | - | READY (length waived) |
| 00015 | corrupt queue reads as drained | minimal | 95 | distil-memory `docket.py`, SKILL.md | - | READY |
| 00016 | queue lands in wrong repo | minimal | 105 | distil-memory `docket.py`, SKILL.md | - | READY |
| 00017 | malformed memory half-written | minimal | 117 | distil-memory `write.py`, `docket.py` | - | READY (scoped to what remains) |
| 00018 | brief reports collection failures honestly (absorbed 00041) | std | 187 | brief app `Brief.svelte`, `App.svelte` | - | READY |
| 00019 | storage failure blanks page | minimal | 106 | brief app `done.js`, `App.svelte` | - | READY |
| 00020 | changelog skill-presence check | minimal | 121 | `ci.yml`, new `scripts/` check | - | READY |
| 00021 | risks tile fake zero | minimal | 101 | debrief app `Brief.svelte`, template | - | READY |
| 00022 | node CI job + install docs | std | 200 | `ci.yml`, two SKILL.md | - | READY (length waived) |
| 00023 | one message three failures | minimal | 115 | both apps `derive.js`, `App.svelte` | - | READY |
| 00024 | empty copy wipes clipboard | minimal | 96 | brief app `Todos.svelte` | - | READY |
| 00025 | brief accessibility pass | std | 208 | brief app 4 components | - | READY (length waived) |
| 00026 | CI wall blank empty state | minimal | 95 | brief app `Work.svelte` | 00018 (wording) | READY |
| 00027 | horizon keyboard tooltips | minimal | 108 | brief app `Horizon.svelte` | - | READY |
| 00028 | history records fabricated zeros | minimal | 115 | `collect.py`, `derive.js` | - | READY |
| 00029 | cut v0.1.0, clean changelog (absorbed 00042) | std | 273 | `CHANGELOG.md`, `ci.yml:34`, git tag | 00020 (grandfather list) | READY (length waived) |
| 00030 | survey prunes skip dirs deep | minimal | 80 | survey `run.py` | - | READY |
| 00031 | sweep parallel with deadline | minimal | 100 | sweep-fix `sweep.py` | - | READY |
| 00032 | sweep validates --out late | minimal | 83 | sweep-fix `sweep.py` | - | READY |
| 00033 | smoke sleep becomes poll | minimal | 86 | brief app `smoke.test.js` | - | READY |
| 00034 | timeout leaks prompt to disk | minimal | 97 | distil-memory `funnel.py` | - | READY |
| 00035 | `local` name GC guard | minimal | 88 | purge-devlocal | - | READY |
| 00036 | create-skill scripts: --help and union path (absorbed 00037) | minimal | 100 | create-skill scripts | - | READY |
| 00038 | braid docs: flags and backup paths (absorbed 00043) | minimal | 116 | braid README, `cli.py` argparse | - | READY |
| 00044 | Windows CI + junction claim | std | 194 | README, `ci.yml` | - | READY |
| 00045 | survey single read and log-time trim (absorbed 00046) | minimal | 96 | survey `run.py` | 00030 | READY |
| 00047 | check_links repeated stats | minimal | 72 | review-prd-backlog script | - | READY |
| 00048 | trash_untracked preview default | minimal | 109 | brush script + 2 doc call sites | 00012 (same file) | READY |

In `hold/` (absorbed originals, not runnable): 00037, 00039, 00040, 00041,
00042, 00043, 00046.

## Findings

### Blocking

- [all 38] A/B: no task checklist and no `Acceptance:` clause anywhere; the
  only executable text is one prose paragraph under `### Phase 0`. plan-tasks
  step 4 copies `Acceptance criteria` verbatim into each task and the test
  author sees nothing else -> fails as: **wrong-TDD lock-in** (the planner
  invents the contract, the tests encode its guess, the mismatch surfaces at
  PRD-level review). Same defect also drops every `standard.md` inner section
  (Capability/Feature blocks, Repository Structure, Module blocks, Dependency
  Graph, Exit Criteria, Critical Scenarios); plan-tasks step 3 derives the
  decomposition when absent, so that half is Non-blocking compliance. Fix:
  rewrite every PRD onto a create-prd template with task lines carrying
  `Acceptance:` (options in the walkthrough: minimal for single-fix PRDs and
  standard for multi-part ones / standard for all / patch in tasks only).
- [00020] D/C: Success Metrics say the check "passes on the current tree
  after the sweep-fix entry"; `rg` shows 14 skill names never appear in
  `CHANGELOG.md` (catchup-ecc, check-python-compat, digest-github-repo,
  e2e-testing, frontend-patterns, manage-agents-md, python-patterns,
  research, resolve-git-conflicts, review-deps-prs, review-with-doubt,
  rust-testing, sync-plan-issue, watch-ci). A check as specced goes red on
  the first run -> fails as: **rework thrash** (implementer pads an ignore
  list or edits the changelog, reviewer rejects either as out of scope). Fix:
  pick one of: ship a named grandfather list for the 14 and let 00029's
  roll-up retire it / backfill 14 entries inside 00020 / scope the check to
  skills added after the changelog's first entry.
- [00044] B: Phase 1 is an open-ended investigation ("whether the junction
  branch is reachable on windows-latest") whose only oracle is a GitHub
  Actions run after a push -> fails as: **unattended hang** (no in-repo
  command can settle it; the reviewer cannot verify, the implementer cannot
  finish). Fix: rewrite Phase 1 as a deterministic README edit now ("the
  junction fallback is covered only by a stubbed unit test; the Windows job
  runs the Python suite") and leave the CI-outcome reconcile as a human
  follow-up / HOLD the PRD / drop the Windows job.
- [00020, 00022, 00042, 00044] B: acceptance phrased as "CI goes red/green".
  CI runs remotely after a push; nothing in the loop can observe it -> fails
  as: **unattended hang**. Fix (rule-mandated, folded into the rewrite):
  acceptance becomes in-repo checks - the workflow parses, the new script or
  job runs locally with the same command, `npm --prefix <app> test` passes.
- [00021, 00023] B/G: `skills/debrief-meeting/app/node_modules/` is absent, so
  `npm --prefix skills/debrief-meeting/app test` cannot run until `npm
  install` fetches packages; a network install mid-loop is a warden `ask` ->
  fails as: **unattended hang**. Fix: run the install now, attended, before
  the batch / add an install task to 00021 and pre-authorize npm / HOLD the
  debrief-meeting halves.
- [00018, 00019, 00021 vs 00022] E: the three lower-numbered PRDs say their
  test is "gated by PRD 00022 (node CI job)", while 00022's own Phase 1 says
  to sequence it after 00018, 00021 and 00025-00027 (three of which are
  higher). As written the dependency points both ways -> fails as: **order
  break**. The gate is not real: every app test runs locally with `npm test`
  regardless of CI. Fix: strike the gate language (acceptance = local `npm
  test`; CI proof arrives with 00022) and delete 00022's sequencing sentence
  / swap numbers 00018 <-> 00022 and rewrite the eight cross-references /
  HOLD 00022.

### Non-blocking

Grounding corrections (lens D), all to be folded into the rewrite:

- [00017] D: partially built since the audit. `e373698`/`08dcdd9` made the
  memory-file and MEMORY.md writes atomic; `21423dc` wrapped `write_memory`
  in `except WriteError` and `decide` in `except QueueError`. Still open:
  `write_memory` never validates frontmatter before writing (`write.py:41-59`),
  `append_pointer` sits outside the guard (`write.py:125`), and both
  `docket.py` read sites are unguarded (`_save_from_proposals_dir` line 177,
  `decide --file` line 211). The xfail test still fails. Rewrite the Problem
  Statement to say what landed and scope Phases 0-1 to what remains.
- [00018] D: "name the skipped repos" is already built and tested
  (`Brief.svelte:57-61`, `smoke.test.js:194-211`); only the reason text and
  the fetch-error banner plus partial marking remain.
- [00023] D: neither app has a "fallback component"; the fallback is the
  inline `{#if !payload}` block (`brief-portfolio/app/src/App.svelte:70-74`,
  `debrief-meeting/app/src/App.svelte:61-65`).
- [00029] D: the "dangling `[Unreleased]:` link reference" does not exist
  (the only `[Unreleased]` is the heading at line 8) - strike it. Heading
  lines drifted (+5/+11 after `ed2fd2f`): `### Added` 83, `### Removed` 280,
  second `### Changed` 295, second `### Fixed` 307 (16 entries). Bullet
  baseline for the count check: 70.
- [00042] D: changelog lines drifted `264-267` -> `275-278`; `ci.yml:34`
  still says "Five skills".
- [00048] D: `_parse_args` is not a symbol; argparse is inline in `main()`
  (`trash_untracked.py:88-93`). The callers are two prose sites, not code:
  `skills/brush/SKILL.md:62` and `skills/brush/references/report-template.md:27`.
  Not loop self-harm: no hook or plugin calls the script.
- [00030, 00031, 00046] D: line drift <= 8 lines (`rglob` at `run.py:62`,
  `def scan` at `sweep.py:270` with the loop at 297, `_trim_lines_to_budget`
  at `run.py:327`).
- [00011, 00012, 00013, 00014, 00015, 00017, 00032, 00035, 00039, 00040] D:
  "on branch `agoge/authored-tests-2026-08-31`" is stale; the branch was
  merged (`636d94f`) and deleted. The tests live on master with
  `xfail(strict=True)` and still XFAIL.
- [00016] B: Risks asks for a "one-time cross-portfolio sweep" for stray
  `distil-memory-queue.json` files. Other repos are outside the write-scope
  fence; state it as a human chore outside the PRD, not a task.
- [00039] B: "one manual sweep is owed" - same treatment.
- [00029] B: "dropped or refiled per rules" needs the rule pinned so the
  implementer does not judge: bullets prefixed `**ci**`, `**tests**`,
  `**docs**` are dropped (`rules/changelog.md` exempts those types); the
  `**work**` bullet under `### Added` (line 264) moves to `### Fixed`. The
  tag `v0.1.0` is created locally; pushing it is the human's step.
- [all 38] A: Feature headings absent. Coverage gate retired in autopilot
  0.3.0, so no mechanism; fixed by the rewrite anyway.
- [00047] F: one decorator; three review surfaces will cost more than the
  work. Keep with `catchup: skip`, `design: skip`, or apply by hand outside
  the loop.
- [00012, 00048] E: same file, compatible end shapes, adjacent numbers are
  not consecutive (00012 then 00048). 00048's flag work will re-ground on the
  fixed `rel` handling via catchup; no edit needed.
- [00014, 00039, 00040, 00043] E: same file (`cli.py`), disjoint regions
  (run loop / `_write_state` / cleanup refusal / argparse). Sequential
  execution is safe; merge proposal below reduces ceremony.
- [check_links] 9 hits are fenced evidence paths (00012:34,35,70,72,73;
  00016:19; 00036:52; 00048:59; wip 00010:186). Not citations; no edit.

### Questions

- [00047] Keep as a PRD or hand-apply? (asked in the walkthrough)
- [00025] Scoped to brief-portfolio only. The debrief app already has
  `aria-current` nav; whether its filter inputs and chips need the same pass
  was not verified here (judy's lane covered both apps in the audit; the
  report raised it only for brief-portfolio). No edit proposed.

## Reshapes

Merges (same subsystem, same file, one review surface instead of two or
three; absorbed originals move to `hold/`):

- 00036 + 00037 -> 00036 "create-skill scripts: `--help` and the union path".
- 00038 + 00043 -> 00038 "braid README and `--help` document every flag and
  backup path".
- 00014 + 00039 + 00040 -> 00014 "braid check reports instead of aborting;
  state writes fail clean" (three xfail tests, three disjoint regions of
  `cli.py`).
- 00045 + 00046 -> 00045 "survey `run.py`: read each sampled file once, trim
  in log time" (00030 stays separate: correctness with its own test).
- 00042 -> 00029: the roll-up rewrites the changelog anyway; add one task for
  the `ci.yml:34` comment and the entry text.
- 00041 -> 00018: both change how the Brief reports skipped and failed repos
  in `App.svelte`/`Brief.svelte`.

No splits: nothing exceeds 93 lines or one subsystem. No renumbering unless
the 00018 <-> 00022 swap is chosen.

## Gaps

- Upstream: agoge `references/prd-emission.md` maps walkthrough packets onto
  `standard.md` at `##` level only, which produced this whole batch's
  noncompliance. Belongs in the agoge plugin repo as its own PRD; noted, not
  filed here.
- `check_links.py` flags paths inside fenced code blocks; skipping fenced
  regions would remove every false positive seen today. Belongs in the
  review-prd-backlog skill; 00047 is a perf PRD and should not absorb it.
- `skills/debrief-meeting/app/node_modules/` missing on this machine (see
  Blocking).
- 14 skills have never had a changelog entry (list under 00020). If 00020
  ships a grandfather list, 00029's roll-up is the natural place to backfill
  and empty it; otherwise the list is permanent debt.
- No producer/consumer holes: every artifact a PRD consumes exists today or
  is built by a lower-numbered PRD (after the 00022 gate text is fixed).
- No `hold/` dependencies; no overlap with wip 00010.
- Strategic: none; the batch is defect repair from a product-time audit.
  `/assess-evolution` is the place for roadmap work, not this gate.

## End state after this batch

Both dashboards stop showing fabricated zeros and blank pages (banner on
failed collection, partial marking, gaps in history, distinct parse-failure
messages, honest risks tile, storage failure notice), the brief gets a
keyboard- and screen-reader-usable pass, brush cannot be walked out of
`dev/local/` with `../` and previews by default, braid `--check` reports
every mismatch instead of aborting and never leaves a temp state file,
distil-memory refuses corrupt queues, lands the queue beside its proposals,
validates before writing and reports every CLI error, survey and sweep-fix
lose their worst latencies and validate inputs first, CI runs the node
suites and a Windows Python run, the changelog names every skill and is cut
as v0.1.0. Still lacking afterwards: the Windows junction fallback is proven
only by a stubbed unit test until a human reads the Windows job's result;
the 14 never-changelogged skills stay grandfathered unless 00029 backfills
them; one cross-portfolio sweep for stray queue files is a human chore; the
agoge emission defect remains upstream.

## Frontmatter tuning

| PRD | suggestion | why |
|---|---|---|
| 00021, 00024, 00032, 00033, 00034, 00035, 00036(+37), 00038(+43), 00047 | `catchup: skip`, `design: skip` | one-function or docs-only change; design and catchup add nothing |
| 00042 (if not merged) | `catchup: skip`, `design: skip` | comment plus one changelog line |
| 00029 | `design: skip` | editorial roll-up; no code design |
| all | keep `default_model: opus`, `rework_cap: 5` | set by emission; valid values |

## Decisions applied

Minutes, one line per finding (decision; status).

Blocking:

- [all 38] A/B no tasks / no `Acceptance:`: fitting template per PRD
  (minimal for single-fix PRDs, standard for 00014, 00018, 00022, 00025,
  00029, 00044); applied - all 31 rewritten, lens A re-run clean.
- [00020] D/C check red on first run: grandfather list of the 14 names in
  `GRANDFATHERED`, 00029 backfills and empties it; applied.
- [00044] B open-ended Phase 1: rewritten as a deterministic README edit
  ("covered only by a stubbed unit test", names the test and the
  `windows-latest` job); CI-outcome reconcile is a Risks-listed human
  follow-up; applied.
- [00020, 00022, 00042, 00044] B "CI goes red/green": rule-mandated; every
  acceptance is now an in-repo check (YAML parse via `python3 -c "import
  yaml..."`, `rg` on the workflow, local `uv run pytest` / `npm test`);
  applied.
- [00021, 00023] B missing debrief `node_modules`: install now, attended;
  applied - `npm --prefix skills/debrief-meeting/app install` run, suite
  passes (47 tests).
- [00018, 00019, 00021 vs 00022] E two-way gate: text fix, keep numbers; the
  "gated by PRD 00022" language struck from the three lower PRDs (acceptance
  is the local `npm test`), 00022's sequencing sentence deleted; applied.

Reshapes (all merges written at the lowest number, absorbed originals moved
to `hold/` with `mv`; five merge targets renamed to match the merged scope):

- 00036 + 00037 -> `00036-create-skill-scripts-help-and-union-path-v1.md`;
  applied.
- 00038 + 00043 -> `00038-braid-docs-flags-and-backup-paths-v1.md`; applied.
- 00014 + 00039 + 00040 ->
  `00014-braid-check-reports-and-state-writes-fail-clean-v1.md`; applied.
- 00045 + 00046 -> `00045-survey-single-read-and-log-time-trim-v1.md`;
  applied.
- 00042 -> 00029 (slug unchanged; one task for `ci.yml:34` and the entry
  text); applied.
- 00041 -> 00018 -> `00018-brief-reports-collection-failures-honestly-v1.md`;
  applied.
- No renumbering (the 00018 <-> 00022 swap was not chosen).

Questions:

- [00047] keep as PRD with `catchup: skip`, `design: skip`; applied.
- [00025] debrief-app scope: no edit; a debrief accessibility pass, if
  wanted, is a new PRD. 00025's rewrite also flagged `Matrix.svelte`'s fifth
  chip as out of scope.

Non-blocking, folded into the rewrites (applied unless noted):

- [00017] Problem Statement now records what `e373698`/`08dcdd9`/`21423dc`
  landed; tasks scoped to frontmatter validation, `append_pointer` guard and
  the two `docket.py` read sites.
- [00018] "name the skipped repos" recorded as already built; `collect.py`
  dropped from the file list (rewrite-agent grounding correction).
- [00023] "fallback component" replaced by the inline `{#if !payload}`
  blocks with their line numbers.
- [00027] mechanism corrected to the `$effect` early return; test is a
  rendered-DOM assertion (rewrite-agent grounding correction).
- [00029] dangling `[Unreleased]:` reference struck; heading lines and the
  70-bullet baseline updated; drop/refile rule pinned (`**ci**`, `**tests**`,
  `**docs**` bullets dropped, the `**work**` bullet moves to `### Fixed`);
  tag created locally, push is the human's step.
- [00033] "~0.5s" claim corrected to ~117ms measured saving; timer clamp
  moved under Nice to have (rewrite-agent grounding correction).
- [00042] line drift `275-278` and `ci.yml:34` "Five skills" carried into
  00029.
- [00048] `_parse_args` replaced by the inline argparse in `main()`
  (`trash_untracked.py:88-93`); the two prose call sites named.
- [00030, 00031, 00046] line drift corrected.
- [10 PRDs] stale "on branch `agoge/authored-tests-2026-08-31`" replaced by
  "on master, `xfail(strict=True)`".
- [00016, 00039] cross-portfolio queue sweep and manual braid sweep stated
  as human chores in Risks, not tasks.
- [00012/00048, 00014 group] same-file adjacency: no edit needed, recorded.
- [check_links] 9 fenced-evidence hits: no edit.
- Frontmatter tuning table applied as listed in the Map.

Apply-pass fixes found while re-checking the rewrites:

- Rewrite agents wrote `python3 -m pytest`; the repo command is `uv run
  pytest` (AGENTS.md, ci.yml). Replaced in 00011, 00013, 00014, 00028, 00038,
  00044. Remaining `pytest` mentions are `@pytest.mark.xfail`,
  `pytest.raises` and CI prose.
- 00020 and 00022 had a wrapped task line starting with `- Acceptance:`,
  which markdown renders as a nested bullet; re-wrapped.
- 40 `(guess ...)` decide-later markers across 17 PRDs (00014:4, 00015:2,
  00016:1, 00018:4, 00019:2, 00020:3, 00021:3, 00022:2, 00023:3, 00024:3,
  00026:3, 00027:1, 00028:2, 00031:3, 00033:1, 00044:1, 00048:2): user
  accepted every guessed value as decided; markers stripped, values kept.
  Behaviour-level ones now fixed: 00015 `cursor`/`start`/`save` exit 2 on an
  unreadable queue; 00016 default queue path
  `Path(proposals_dir).parent / "distil-memory-queue.json"`; 00020
  `scripts/check_changelog_skills.py`, misses on stderr + exit 1, two `lint`
  steps; 00022 `actions/setup-node@v6` at node 24; 00028 run-level gap via
  `"e": 1`; 00031 `--deadline` default 300; 00044 `uv run --python 3.13
  pytest`; 00048 `trash_dest()` helper, DRY-RUN marker on stderr. 00018's
  Risks bullet that quoted a marker was rewritten by hand afterwards.
- Length waiver (user): 00014 (231), 00022 (200), 00025 (208), 00029 (273)
  exceed lens A's ~200-line heuristic. Judged no split: each is one
  subsystem, contract-dense rather than prose-heavy (00014/00018/00029 are
  user-chosen merges; 00022/00025 are standard-template PRDs whose Feature
  blocks carry the contracts plan-tasks copies). Recorded as a waiver, not a
  pass.

Human follow-ups (outside the loop):

- `git push` failed in this session (SSH agent); master is 4 commits ahead of
  origin. Push from your own shell.
- Push the `v0.1.0` tag after 00029 runs.
- Read the first GitHub Actions run after 00020, 00022 and 00044 land; open
  a PRD for anything that only appears on a hosted runner.
- One cross-portfolio sweep for stray `distil-memory-queue.json` files
  (00016 Risks).
- Upstream: file the agoge `prd-emission.md` `##`-level mapping defect and
  the `check_links.py` fenced-block false positives (see Gaps).
