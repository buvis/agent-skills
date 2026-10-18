# Backlog review - agent-skills - 2026-10-17

Verdict: GO (after the apply pass; initial verdict NO-GO: 12 Blocking across
11 PRDs, 1 RESHAPE, 2 Questions)

Lenses A-C and E-H ran inline; lens D (grounding) fanned out to four
subagents (00023+00029, 00031+00045, 00044+00048+00070, 00049+00078+00086+00088)
plus an inline pass over 00087 and 00050. Citation resolution ran via
`check_links.py` (repo-wide run; 9 findings under `prds/backlog/`, 0 under
`prds/wip/`). Grounding resolution ran via `ground_prd.py` (exit 1: `missing`
and `unresolved` rows in 00023, 00029, 00031, 00045, 00048, 00070; 00087 and
00088 all `declared-new`; 00044, 00049, 00050, 00078, 00086 clean). Plugin
claims checked against the installed autopilot 0.9.0 (`installed_plugins.json`
and the cache agree; `eligibility` is implemented in `cli/eligibility.py`, 30 s
timeout, cwd = project root). `autopilot:plan-tasks` steps 4-4.7 consulted:
150K per-task threshold; no PRD here approaches it.

Done before the review proper: PRD 00050 was refreshed and moved from `hold/`
to `backlog/` per the handoff pasted into this session (commit `6a89a85`,
pushed): run command gained `--qwen-provider llamacpp8002`, `--qwen-model
unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL`, `--sonnet-model claude-sonnet-5-5`;
`dev/local/` paths repointed; the plugin reference named instead of a cache
path; the operator's calibration record fixed at
`docs/dev/project-management/audit-results/qwen-ivan-calibration/protocol.md`
with an `effort:` line; `eligibility:` requires 00049 in `done/` plus that
line, and exits 1 today through `cli.eligibility.evaluate` (proven with a
script file, not `python3 -c`).

## Map

Lines are pre-apply. Verdicts are pre-apply; after the apply pass 00044 sits
in `hold/` and every PRD left in `backlog/` is READY.

| # | PRD | template | lines | subsystems | depends on | verdict |
|---|-----|----------|-------|------------|------------|---------|
| 00023 | one-message-three-failures | minimal | 115 | debrief-meeting app (derive.js, App.svelte, template, smoke suite); brief-portfolio half is dead (skill deleted in af1b704) | none | FIX |
| 00029 | cut-v010-clean-changelog | standard | 273 | CHANGELOG.md, ci.yml comment, check_changelog_skills.py, local tag | 00020 (done) | FIX |
| 00031 | sweep-parallel-with-deadline | minimal | 100 | sweep-fix sweep.py + two test files + SKILL.md | none | FIX |
| 00044 | windows-ci-junction-claim | standard | 243 | ci.yml, README, conftest, brush, distil-memory, every collected test | 00020, 00022 (done) | RESHAPE -> HOLD (applied) |
| 00045 | survey-single-read-and-log-time-trim | minimal | 96 | survey run.py + split test files | 00030 (done) | FIX |
| 00048 | trash-untracked-preview-default | minimal | 109 | brush trash_untracked.py, tests, SKILL.md, report-template | 00012 (done); same file as 00044 (lower, compatible) | FIX |
| 00049 | qwen-completion-status | standard | 211 | use-qwen qwen-run.sh, run-eval.sh, two shell suites, runbook, SKILL.md | none; guard: lane worktree only | FIX |
| 00050 | qwen-ivan-capability-eval | standard | 273 | use-qwen harness evidence bundle (no code) | 00049 (backlog, lower), 00051, 00052 (done); guard: 00049 done + calibration record | READY (guard-gated) |
| 00070 | purge-trash-first-guarantee | minimal | 91 | purge-devtmp (PRD still says purge-devlocal) | none | FIX |
| 00078 | qwen-dispatch-skips-pi-extensions | minimal | 123 | use-qwen qwen-run.sh:469, test_qwen_run.sh, CHANGELOG | none; guard: lane worktree only; collides with 00049 | FIX |
| 00086 | use-qwen-budgets-survive-load | minimal | 127 | use-qwen test modules + helpers | none | READY (one wording fix) |
| 00087 | ground-prd-root-and-relative-exclusion | minimal | 147 | create-prd ground_prd.py + tests | none | FIX |
| 00088 | document-the-eval-harness-contract | minimal | 160 | use-qwen runbook § 7, SKILL.md, new drift test | none; same two docs as 00049 (different lines) | FIX |

wip: empty. hold: empty (placeholder dotfile only). done: 57 PRDs.

Hygiene: only `NNNNN-slug-v1.md` files plus the 1-byte `.migration-placeholder`
dotfile in `backlog/` (every prds dir has one; `selection.py` picks only
`^\d{5}-` `.md` files, so it is not a selection break); 70 distinct sequence
numbers across backlog/done, no duplicates (no `intake/` or `discovery/`
directory exists); this report lives in `audit-results/`. Main-checkout
`autopilot/state.json` (gitignored) is stale from batch 202610100952 (`phase:
build`, `prd: 00075` now in done/, minted stubs 00084/00085 deleted); target
resolution reads wip/ then backlog/, so no selection break, but the batch id
will not roll over.

CI at `43f9600` (run 39020685948, in progress at review time; 39017441631 at
`4cbec5f` complete): Ubuntu `test (3.10)` and `test (3.13)` red on
`skills/glean/scripts/test_glean.py::test_local_dirs_never_surface_as_candidates`
(passes on macOS); `windows` red with 63 failures / 3735 passed / 29 skipped
(braid 13, braid_check 7, ground_prd 2, distil-memory 9 CRLF diffs, glean 2,
sweep-fix 2 `os.geteuid`, use-qwen ~27 incl. symlink OSError 22 and the two
module budgets at 83 s / 71 s). No PRD covers the glean red.

## Findings

### Blocking

- [B1][00023] A/D: the brief-portfolio half is dead - `af1b704` deleted the
  skill, so Tasks 1-3's `rg`/`npm` over `skills/brief-portfolio/...` exit 2 and
  the `{ payload, error }` loader has shipped nowhere (`derive.js:8-17` still
  reads `catch {` returning null). -> fails as: stall. Also the Metric rule:
  Tasks 4-5 and Success Criteria pin `# pass 19` / `# pass 50`; the
  debrief-meeting suite is 48 today, not 47. -> fails as: rework thrash. "six
  assertions" becomes three. Fix: rescope to debrief-meeting only; name the
  three new tests, never a suite total.
- [B2][00029] D: every premise and count is stale. Headings today
  (`rg -n "^#{2,3} " CHANGELOG.md`): 8, 10 Added, 91 Changed, 104 Fixed, 370
  Added, 576 Removed, 591 Changed, 603 Fixed - eight, with `### Added` now
  doubled too; bullets 176 (PRD: 70); excluded-scope bullets seven at 75, 501,
  552, 564, 569, 571, 634 (PRD: six at 205...); `**work**` at 560 under the
  second `### Added` (PRD: 264); ci.yml comment at `:122` (PRD: `:34`). Phase 0
  task 1 says "stop if the heading set differs" - it differs, so the PRD stops
  at its first task. -> fails as: stall. Fix: premises by shape (more than one
  heading per type), counts as execution-time arithmetic (N today - excluded +
  14 backfilled + 1 Removed entry), line numbers only as "today".
- [B3][00029] H/E: Phase 2 deletes `## [Unreleased]` (`rg -c "Unreleased"`
  exits 1, `rg -c "^## "` prints 1). `rules/changelog.md` is a BLOCKING rule
  that files every feat/fix entry under `[Unreleased]`, and nine later PRDs
  (00031, 00045, 00048, 00049, 00070, 00078, 00086, 00087, 00088) carry such
  entries; 00078's acceptance even reads "between `### Fixed` and the next
  `## [` heading", which only exists once 0.1.0 is cut. -> fails as: goal
  reversal (every later implementor re-creates the heading). Fix: cut 0.1.0
  beneath an empty `## [Unreleased]`; `^## ` prints 2.
- [B4][00031] C/D: acceptance expects `--deadline must be a positive integer`
  but `_positive_int` (`sweep.py:500-504`) hardcodes `--cap must be a positive
  integer`; the task never says to parametrise it. -> fails as: wrong-TDD
  lock-in. `sweep.py` has no `import time`, so the prescribed
  `monkeypatch.setattr(sweep.time.monotonic)` raises AttributeError. -> same.
  `_resolve_report_path` (`:521-545`) suffixes a colliding default `--out` with
  `-2`, so "byte-identical reports" needs an explicit `--out`. Drift: `scan`
  :292, loop :319, `DEFAULT_SCAN_TIMEOUT` :88, `_scan_repo` :270,
  `_render_failed_section` :402-410, `render_report` :465, `_parse_args` :507,
  `main` :548 (scan call :571); `collect.py` is gone with brief-portfolio, so
  "mirroring collect.py:494" dangles. No `New symbols:` lines for the four new
  tests and `DEADLINE_REASON`. `Partial:` render test belongs in
  `test_sweep_render_report.py`, which the PRD never names.
- [B5][00044] B/D/F: seven of nine task outputs are already on master -
  `jobs.windows` (`ci.yml:59-120`, `uv run --python 3.13 pytest`, PYTHONUTF8,
  capability probe, no suppression; pinned by `tests/test_ci_workflow.py`),
  `.gitattributes` `*.sh text eol=lf`, testpaths tests/skills/scripts, root
  `conftest.py` fixtures (`write_executable_stub`, `isolate_home`,
  `deny_access`, `run_resolved_tool`), brush `as_git_rel`/`normalise_rel`,
  `proposal.py` publication. "CI runs Python tests only on Ubuntu" is false. What
  remains is Phase 2: a green `windows` run (today 63 failures across seven
  subsystems the PRD never names; "Fix additional Windows failures ... in this
  PRD" is unbounded) plus README `:27` doubled backslash and `:218-221`
  junction claim; the Ubuntu matrix is red too (glean), so "the existing Ubuntu
  matrix is green" cannot be met either. The Phase 2 task needs a push -> CI ->
  `gh` polling loop. -> fails as: stall (plan-tasks cannot bound the fix list)
  and unattended hang (waiting on hosted runners). Tree also names
  `skills/purge-devlocal/scripts/test_purge_devlocal.py` (gone) and
  `survey/scripts/test_survey.py` (split by 00079). RESHAPE: HOLD for an
  attended run (recommended) - see Reshapes.
- [B6][00045] D: 00079 split `test_survey.py` into `test_survey.py` (380
  lines), `test_survey_brief.py` (437; `test_brief_within_5120_byte_limit` at
  :71), `test_survey_scan.py` (249), `survey_test_helpers.py`, `conftest.py`;
  the Phase 1 task targets
  `test_survey.py::test_brief_within_5120_byte_limit`, which no longer collects.
  -> fails as: stall. The eight direct call sites are now `test_survey.py`
  127, 163, 192, 231, 265, 285, 337, 374; the regex-fallback test is at :252
  (lambda :263). `_extract_file_symbols` (`run.py:153`) calls the regex
  extractor a second time at `:168` for `.go` files - a third read the PRD's
  `.py`-only fixture cannot catch. -> fails as: rework thrash (reviewer finds
  the `.go` read). Drift: `read_text` at :138 (`_extract_tree_sitter` :133),
  :178 (`_extract_file_symbols_regex` :175), :240 (`_compute_error_style`
  :228, sample :229-234); `_trim_lines_to_budget` :338, pop loop :346-347,
  cleanup :348-349; `_BRIEF_BUDGET` :23; `_survey` :367. 00030 is done. No
  `New symbols:` line.
- [B7][00048] D: the trash root is `docs/dev/tmp/.trash`
  (`trash_untracked.py:91`, manifest `:102`), not `dev/local/.trash`; the
  acceptance assertions on `repo / "dev/local/.trash"` pass vacuously. ->
  fails as: wrong-TDD lock-in. The sibling is `skills/purge-devtmp/scripts/
  purge_devtmp.py:220` `DRY-RUN (use --apply)`; its `--apply` (`:195`) has no
  help text, so "matching purge_devlocal.py:481-485" is false. Drift: parser
  :108-114, `relocate()` call :132, `note_manifest()` :133, call sites
  `skills/brush/SKILL.md:63` and `report-template.md:27`. 00012 done. No
  `New symbols:` line.
- [B8][00070] D: the skill was renamed purge-devtmp in the 2026-09-30 rewrite
  (`b3a61f9`); `skills/purge-devlocal/` holds only untracked `__pycache__`.
  Every named symbol is gone: `test_zero_day_retention_does_not_delete_todays_
  own_fresh_stamp`, `test_empty_trash_ages_out_old_batches_only`,
  `test_trashes_design_of_done_prd`, the `run()` helper. Today:
  `purge_devtmp.py` `empty_old_trash(store, now, days)` :143-158 (no `keep`),
  `process_store` trash :172, call :177, batch :162, `--empty-trash-days`
  `type=float, default=30` :198; `test_purge_devtmp.py` (105 lines) uses
  `args(**overrides)` :10-19, `repo_store(tmp_path)` :22, `age(path, days)`
  :29, `gc.process_store("repo", store, args(apply=True), now)` :86. The bug
  itself reproduces at HEAD. -> fails as: stall. Fix: retitle/repath; write
  the test in the current idiom; the PRD must add the ages-out test it cites
  as existing.
- [B9][00078 x 00049] E: both rewrite `qwen-run.sh:469`
  `ARGS=(--provider "$PROVIDER" --model "$MODEL" --mode "$OUTPUT_MODE")`.
  00049 (lower, drains first) moves dispatch onto pi's JSON transport and may
  reshape that line; 00078's premise is the exact text, so it fails and 00078
  skips on every drain. -> fails as: order break (silent never-runs). Fix:
  00078 premise by pattern (`rg -c '^ARGS=\(--provider '` prints 1, no
  `no-extensions`), edit = append inside the array; one sentence in 00049
  Phase 1 keeping the single `ARGS=(--provider ...)` array as the shared pi
  argument list. 00078's CHANGELOG acceptance holds once B3 is applied.
- [B10][00088] D: the verbatim `run` usage line (Phase 1 doc block) omits
  seven live options - `--alternate`, `--retry-discarded {harness-only,none}`,
  `--server-reasoning-effort`, `--qwen-provider`, `--qwen-model`,
  `--sonnet-model`, `--usage-limit-cmd` (`run_eval_harness.py:61-67`); `_admit`
  refuses qwen/sonnet without three of them (`attempt.py:199-202`), so the
  "written contract" cannot run the engines it compares, and 00050's command
  uses all of them. `run` exits 2 when halted (`attempt.run` docstring :149),
  unsaid. The drift test guards `vet` flags only. -> fails as: rework thrash.
  Fix: add the options and exit codes to the block; add
  `test_runbook_names_every_run_flag`.
- [B11][00087, 00088] citation (mechanical): `00087:144-145` and `00088:157-158`
  cite the deleted hold stubs by filename ("are gone from hold/") - dangling
  by design, needs `link-ok:`. Both also cite ledger keys (`bac71612d738`,
  `6b0e4ec95f8f`; `04e47608c859`, `76ce2353c7fd`) that exist in neither
  deferred ledger (control: `op_id` found). -> fails as: stall on a premise
  check. Fix: waiver token; cite the entries by issue text.
- [B12][00087] B/H: `test_cli_exits_two_when_cargo_lock_is_unreadable` is
  specified as `chmod 0o000` plus `pytest.skip` when `os.geteuid() == 0`:
  `os.geteuid` is Unix-only (the exact AttributeError now failing two sweep-fix
  tests on the Windows job) and `chmod(0)` denies nothing on Windows. The repo
  idiom is the root `conftest.py` `deny_access(path)` fixture (:144-169,
  platform-aware, auto-restore). -> fails as: goal reversal against 00044's
  Windows gate. Fix: use `deny_access`.

### Non-blocking

- [N1][00023, 00029, 00031, 00044, 00045, 00048, 00049] D: Problem sections
  cite `dev/local/audit-results/...` and `dev/local/reviews/...`; `cdcb888`
  moved the tree to `docs/dev/project-management/`. Prose only; `ground_prd.py`
  reports them as `missing`.
- [N2][00029] C/G: Dependency Graph lists `changelog` under both Foundation
  and Integration (cosmetic); "all 47 directories" is 50 tracked skill dirs
  today; CHANGELOG names `brief-portfolio` on 31 lines and `af1b704` removed
  the skill with no `### Removed` entry - the changelog rule mandates one, and
  it belongs to this PRD's "Changelog completeness" capability.
- [N3][00049] D: `dev/local` paths (N1); `test_eval_automation.sh` holds T1-T9
  registry/scoring tests only (no retry fixture) and its pi stub records no
  argv or call count, so the Phase 2 "invoked exactly once" fixture needs a
  counting stub - say so; the runbook has no incomplete-attempts section yet
  (new text; § 6 item 1 is the hook); installed pi is 0.80.10.
- [N4][00086] D: "the longer sleep costs no run time" - sleeps are killed at
  the bound, so each bounded segment costs about 2 s more (4 s instead of 2 s).
- [N5][00050] A/F: 273 lines; the three phases are one pipeline (seal -> run
  -> report) so no split, prose tax only. `check_links.py` flags lines 6, 113,
  208 (the calibration record) and 156 (`qwen-ivan-<run-id>/`, the PRD's own
  output tree): the first three exist only once the guard is meant to pass,
  the last is a declared output - not findings; no `link-ok:` on the
  frontmatter line because it is a shell command.
- [N6][00044] frontmatter `catchup: force` and `design: run` are right for the
  scope if it stays; see Reshapes.
- [N7] hygiene: stale main `state.json` and the untracked
  `skills/purge-devlocal/` cache leftovers (see Hygiene above).

### Questions

- [Q1][00050] Which Sonnet model id to pin? The wrapper's default is the alias
  `sonnet` (which the harness would record as the identity); `claude-sonnet-5-5`
  is pinned provisionally as the API id that alias resolves to today.
- [Q2][00044] HOLD, or rescope to the measured Phase 2? (RESHAPE card.)

## Reshapes

- 00044 -> HOLD (proposed). The structure it specifies has shipped; what is
  left is an attended loop (push, wait for hosted Windows, fix 63 failures in
  seven subsystems, repeat) that no unattended session can bound. Alternative:
  rescope to Phase 2 with the failure list split per subsystem into separate
  PRDs (braid/braid_check 20, distil-memory CRLF 9, use-qwen 27, glean 2,
  sweep-fix 2, ground_prd 2) and keep 00044 as the README + final-run PRD
  behind an `eligibility:` guard that checks `gh run list` for a green
  `windows` job.

## Gaps

- master is red on Ubuntu (glean `test_local_dirs_never_surface_as_candidates`,
  environment-dependent: passes on macOS) and no PRD covers it. Recommend a
  small fix PRD before the drain; every PRD's final `uv run pytest` gate runs
  locally, so the drain itself survives it.
- The Windows job's 63 failures are covered only by 00044 (RESHAPE); 00087's
  B12 would have added one more.
- CHANGELOG has no Removed entry for brief-portfolio (folded into 00029, N2).
- Every fix-type PRD here ships its regression test (checked: 00023, 00031,
  00045, 00048, 00070, 00087, 00088, 00049, 00078; 00086 is test-only).
- Strategic: five PRDs on use-qwen (00049, 00078, 00086, 00088, 00050) drain
  consecutively, which is the right adjacency; 00049 and 00078 run only in a
  lane worktree (eligibility), 00050 only after 00049 is done and the operator
  has calibrated. `/assess-evolution` is not needed for this set.

## End state

With every PRD done: v0.1.0 cut beneath an empty `[Unreleased]`, one section
per type, 14 grandfathered skills named, brief-portfolio recorded as removed;
sweep scans in parallel under a deadline; survey reads each file once and
trims in log time; brush previews by default; purge-devtmp never empties the
batch it just filled; qwen-run.sh reports truthful completion and dispatches
without extensions; qualification is one-shot; the harness runbook matches the
CLI and a test holds it there; the use-qwen budgets survive load; ground_prd
exits 2 on a bad root and cannot confirm a PRD's own symbols; the Qwen-vs-Sonnet
Ivan experiment has its evidence bundle (once calibrated). Left open: the
Windows job (00044 on hold) and the glean Ubuntu red (no PRD).

## Frontmatter tuning

All keys on all 13 PRDs are recognized. Suggestions: 00023 `design: skip`
(one app, exact tests, no design choice left). 00044 if rescoped: keep
`catchup: force`, add an `eligibility:` guard on a green `windows` job.

## Decisions applied

Cards (two): 00044 -> HOLD (user); 00050 keeps `--sonnet-model
claude-sonnet-5-5` (user). Everything else was applied under the standing
authorization as routine reversible PRD text fixes, no card.

- 00044: `git mv` to `prds/hold/`; parking note in the Problem Statement
  naming the shipped structure and the 63-failure attended loop.
- 00023 (B1, N1): rewritten for debrief-meeting only; loader, shell, template
  and suite modules point at that app; three named tests plus a `renderRaw`
  helper with a `New symbols:` line; no suite totals; source path repointed.
- 00029 (B2, B3, N1, N2): premises by shape (any doubled `###` heading);
  counts as N0 - E, + 14, + 15, with the 2026-10-17 numbers recorded as
  "today"; Phase 2 keeps an empty `## [Unreleased]` above `## [0.1.0]`
  (`^## ` prints 2); new Feature "Removed-skill entry" and a Phase 1 task for
  the brief-portfolio Removed bullet; ci.yml `:122-124`; 50 directories;
  Integration-layer label; source path repointed.
- 00031 (B4, N1): `_positive_int` must take the flag name it reports (the
  cap tests keep passing); `import time` added to the deadline task; explicit
  `--out` in the byte-identical criterion; `collect.py` reference dropped;
  current line numbers; `New symbols:` on four modules; new
  `test_sweep_render_report.py` module and task for the `Partial:` line;
  BrokenBarrierError un-backticked (stdlib).
- 00045 (B6, N1): test targets split across `test_survey.py` and
  `test_survey_brief.py` (00079); the `.go` merge read named in Problem,
  Solution, Must-have, task 2 and the single-read fixture; eight call sites
  and all line numbers current; `New symbols:` lines; 00030 and 00079 done.
- 00048 (B7, N1): `docs/dev/tmp/.trash` everywhere; the sibling is
  `purge_devtmp.py:220` and its `--apply` has no help; `SKILL.md:63`; current
  parser and relocate lines; `New symbols:`; dependency note on 00012 (done)
  and 00044 (hold).
- 00070 (B8): title, paths and symbols on purge-devtmp; fixture idiom
  `repo_store`, `age`, `args(apply=True, empty_trash_days=0)`; two new tests
  (zero-day keep, ages-out window) with `New symbols:`; commit hash plain.
- 00049 (B9, N1, N3): `dev/local` paths repointed; Phase 1 keeps the one
  `ARGS=(--provider ...)` array for 00078; Phase 2 names the counting stub
  `test_eval_automation.sh` lacks and the runbook and SKILL.md sections 00088
  touches; pi 0.80.10 recorded.
- 00078 (B9, B3): premise by pattern (`rg -c '^ARGS=\(--provider '` prints
  1); edit = append `--no-extensions` inside the array; CHANGELOG acceptance
  under `[Unreleased]` in the 00029 shape.
- 00086 (N4): the longer sleep costs about 2 s per bounded segment.
- 00087 (B11, B12): ledger entries cited by ref and text; the unreadable
  `Cargo.lock` test uses the root `deny_access` fixture, no `chmod`, no
  `os.geteuid`; `link-ok:` on the deleted-stub line.
- 00088 (B10, B11): the `run` usage line carries all seven extra options; the
  `run` paragraph states the engine-flag refusals, what each option does and
  the 0/1/2 exit codes; fourth drift test `test_runbook_names_every_run_flag`
  (Must-have, Module, task, Success Criteria); ledger entries cited by text;
  `link-ok:` on the deleted-stub line.
- 00050: no edit (user confirmed the pinned Sonnet id).
- Not applied: 00023 `design: skip` (suggestion only); no PRD for the glean
  Ubuntu red (recommend one before the drain; the local gate is unaffected).

Re-checks after the apply pass: lens A on every touched PRD (template
headings present and in order, every `#### Feature:` unique, every task line
carries `Acceptance:`, counts match per file); `ground_prd.py` over backlog +
wip exits 0 (0 blocking, 0 unverified; the first re-run flagged 25 rows the
edits themselves had introduced, bare file citations and backticked commit
hashes, all fixed: citations are repo-relative and sit on the line of the
symbol they ground, hashes are plain text); `check_links.py` leaves only the
five 00050 rows named under N5. Post-apply lines: 00023 115, 00029 313,
00031 118, 00045 110, 00048 114, 00049 221, 00050 273, 00070 91, 00078 127,
00086 128, 00087 151, 00088 175; 00044 251 in hold.

Open for the operator (outside this gate): calibrate the 00050 effort level
and write `audit-results/qwen-ivan-calibration/protocol.md`; drain 00049 and
00078 in a lane worktree, one after the other, so 00050's guard can pass; a
fix PRD for the glean Ubuntu red; the Windows loop behind 00044.
