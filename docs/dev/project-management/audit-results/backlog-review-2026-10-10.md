# Backlog review - agent-skills - 2026-10-10

Verdict: GO (after the apply pass; initial verdict NO-GO, 9 Blocking)

Lenses A-H all ran. Lens D (grounding) was fanned out to four read-only
subagents (distil-memory, sweep-fix, create-prd/review-prd-backlog, survey);
all four returned. Citation resolution ran via `check_links.py`.

## Map

Verdicts below are the pre-apply ones. After the apply pass: 00069 closed
(done/), 00074 absorbed into 00076 (hold/), every remaining PRD READY.

| # | PRD | template | lines | subsystems | depends on | verdict |
|---|-----|----------|-------|------------|------------|---------|
| 00069 | announcement-window-injectable | minimal | 95 | brief-portfolio (deleted) | - | HOLD |
| 00071 | distil-publish-recovery | minimal | 169 | distil-memory write/docket/SKILL | 00015-00017 (done) | READY |
| 00072 | distil-judge-no-persistence | minimal | 94 | distil-memory funnel | 00034 (done) | FIX |
| 00073 | sweep-loud-failures | minimal | 130 | sweep-fix | 00032 (done) | FIX |
| 00074 | distil-tests-bind-intent | minimal | 92 | distil-memory tests | 00071 | RESHAPE |
| 00075 | ground-prd-claims | standard | 190 | create-prd, review-prd-backlog | - | FIX |
| 00076 | distil-tests-see-non-atomic-writes | minimal | 136 | distil-memory tests | 00017 (done), 00074 | FIX |
| 00077 | docket-never-raises | minimal | 124 | distil-memory docket | 00015-00017 (done), 00076 | FIX |
| 00079 | split-test-survey | minimal | 86 | survey tests | - | FIX |
| 00080 | frontmatter-keys-and-path-rule | minimal | 78 | create-prd, review-prd-backlog | 00075 (same files) | FIX |

Hygiene: filenames valid, sequence numbers unique across backlog/hold/done
(no discovery dir), no stray files in `backlog/`.

## Findings

### Blocking

- [00069] D/H: the whole target, `skills/brief-portfolio/`, was deleted in
  `af1b704` (superseded by the postup gem, PRD 00070), the same reason 00068
  was closed. -> fails as: stall (every task's file is absent). Fix: HOLD or close as superseded.
- [00075] D: stale grounding. Six `dev/local/` references survive the
  `cdcb888` move to `docs/dev/project-management/`: the `--glob '!dev/local/**'`
  exclusion (line 53; it no longer hides PRD prose, so the phantom-identifier
  test passes vacuously), the gate command (line 83), `dev/local/tmp/` (74),
  the fixture `tmp_path/dev/local/notes/x.md` (154), the check_links prefix
  claim and the 00047 path (18). Premise "5.5 at line 130, 5.6 at 134" is
  false (actual 132/136), so Phase 1 skip-and-reports; the 5.5 body's
  "proceed to step 5.6" pointer is never updated to 5.55. -> fails as:
  wrong-TDD lock-in + stall. Fix: re-ground the text.
- [00080] D/B: the verbatim text it pastes into create-prd and the gate is
  false against installed autopilot 0.9.0: (a) "A PRD naming a hook path, a
  security-ish path or no path at all, or carrying `design: run`, always
  runs `full` whatever the key says" - the `lane:` override is checked first
  (`lane.py:391-393`); only `lane_check.py` escalates a solo build after the
  fact, and an absent `design` (not just `design: run`) forces full;
  (b) "Every optional field falls back... (a one-line warning is logged)" -
  invalid `design_gate`/`pause_on_ambiguity`/`plan_expansion` drop silently;
  (c) fast-track is "one card of <=12 paths and <=40 goal lines at any phase
  count, else exactly two phases", not "at most two phases"; (d) the
  "needs the release carrying..." caveats and "autopilot 0.5.2" are moot at
  0.9.0. -> fails as: rework thrash (reviewers check against the plugin) and
  ships false law into the gate. Fix: correct the verbatim lines.
- [00072] B: the required one-megabyte test needs "a native-runnable fake
  claude command on each CI platform". CI runs pytest on windows-latest, and
  `judge()` passes bare `"claude"` to `subprocess.run`; CreateProcess resolves
  only `claude.exe`, so a `.cmd`/`.py` fake is unfindable without a production
  change the PRD does not specify. -> fails as: wrong-TDD lock-in / rework
  thrash. Fix: pin the mechanism.
- [00073] C/D: `test_sweep_verify_control.py:73-87`
  (`test_verify_control_warns_to_stderr_when_fallback_check_cannot_run`)
  asserts `result is None` on a failed control search, the exact behavior the
  PRD reverses; neither it nor `test_sweep_enumerate.py` (whose :67/:82 cover
  the cwd append the walk-up changes) is named. -> fails as: rework thrash
  ("fix the implementation, not the test" vs an unnamed test that must change).
  Fix: name both files and the rewrite.
- [00079] C/D: "Shared fixtures live in conftest.py" plus "No change other
  than test modules and the conftest" forbids the helper module that plain
  helpers (`_init_git_repo`, `_section_body`, `PINNED_KINDS`,
  `requires_tree_sitter`) need - conftest shares fixtures, not importable
  functions; repo idiom is `*_test_helpers.py`. Inventory path
  `dev/local/tmp/` no longer exists (`docs/dev/tmp/`). -> fails as: rework
  thrash. Fix: allow `survey_test_helpers.py`, repoint path.
- [00074] D/F: item 2 is already done (the four crash-safety tests assert
  `OSError`/`WriteError` with `match="boom"`); item 3's "start reopens that
  entry" misdescribes `advance()` (it resets `session_decided`, touches no
  entry; the observable is `next` returning None before `start` and the entry
  after, cursor unchanged). What remains is three small test edits in the same
  files 00076 rewrites. -> fails as: wrong-TDD lock-in (item 3). Reshape: merge into 00076.
- [00076] C: "The seven index/entry-failure rollback tests ... share one
  parametrized helper" - the file has eight to ten candidates (:212, 260,
  291, 340, 375, 412, 552, 584, plus :452/:630). -> fails as: rework thrash.
  Fix: list the test names.
- [00075, 00076, 00077, 00079, 00080] check_links: dangling citations to
  pre-move `dev/local/` paths (00075:14 x5, 00076:21, 00077:18, 00079:17,
  00080:10). Every target exists under `docs/dev/project-management/`.
  00075:14 and 00080:10 also put `/Users/<name>/` paths and a private
  project name into this public repo (AGENTS.md). -> fails as: stall
  (premise check on a dangling pointer). Fix: repoint.

### Non-blocking

- [00073] `main`'s `except RuntimeError` is at :584, not :581;
  `_needs_yaml_quoting` is 34 lines, not 43; the success criterion that
  `test_resolve_rg_...` "reaches main's handler" is cosmetic (it calls the
  resolver directly).
- [00077] the six indexed keys sit at `docket.py:210-217`, not 213-217; the
  `except` is at :223.
- [00080] premise `rg -c ... prints 0` - `rg -c` prints nothing on zero
  matches; line cites :88-116 -> :90-118, CHANGELOG `### Changed` :54 -> :84,
  plugin cites phase-build.md:130/:70 drifted.
- [00076/00077] near-duplicate tests: 00076
  `test_save_refuses_the_whole_batch_after_readable_records` and 00077
  `test_save_refuses_a_record_missing_evidence_text_after_readable_records`
  pin the same whole-batch refusal.
- [00076] `test_save_missing_dir_does_not_name_proposals_json` fails on
  current code (`docket.py:205,224` names proposals.json); the PRD already
  allows a minimal production fix, but does not say what the message should
  name instead (the directory is the obvious answer).
- [00071/00076/00077] `docket.py` `main` decide branch (:246-262) is edited by
  all three; no contradiction, rebase hotspot. Ascending order handles it.
- Adjacency: distil-memory PRDs (71, 72, 74, 76, 77) are interleaved with
  73 and 75. Renumbering not proposed: cross-PRD references cite numbers.

### Questions

- none beyond the fix choices above.

## Reshapes

- Merge 00074 into 00076 (same files, same theme, 00074 shrank to three
  edits after 00017).
- HOLD 00069 (target deleted).

## Gaps

- Half-migration: the `dev/local` -> `docs/dev/project-management` move left
  stale references beyond the backlog: `meta/project-capsule.md` Key
  Invariants still names `dev/local/meta/`, and check_links reports dangling
  paths in `designs/`, `meta/agoge-profile.md` and `audit-results/`. No PRD
  covers it.
- `hold/` holds 24 PRDs, several waiting on a human decision (e.g. 00057).
  Outside this gate; worth a separate walk.

## End state after this batch

distil-memory gets executable recovery, a judge that no longer pollutes its
own corpus, a docket CLI that never tracebacks, and tests that bind to intent;
sweep-fix fails loud; create-prd gains a grounding gate and the full
frontmatter key list, and the backlog gate runs the same check; survey's suite
drops under the cap. Still lacking: the dev/local path cleanup outside the
backlog, and the parked `hold/` work.

## Frontmatter tuning

| PRD | suggestion | why |
|-----|-----------|-----|
| 00079 | `design: skip` | mechanical move with an inventory equivalence check; the design phase adds little |
| 00080 | none | sonnet + skip/skip fits |

## Decisions applied

1. 00069 - closed as superseded, moved to `done/` with a closure note. Applied.
2. 00075 - every `dev/local/` repointed (search glob now `!docs/dev/**`, gate
   command, fixture, tmp path, check_links prefix, 00047 path); premises match
   headings by pattern, not line; step 5.5's "proceed to step 5.6" pointer is
   updated to 5.55 with its own acceptance check; dev_local test renamed
   working_docs. Applied.
3. 00080 - verbatim lines rewritten to autopilot 0.9.0 (`lane.py` classify
   order, `frontmatter.py` warn/silent split, fast-track card limits from
   `lane.py:45-46,340-364`, plan-expansion thresholds verified in
   `policy.py`); release caveats and 0.5.2 dropped. Applied.
4. 00072 - test wraps `funnel.subprocess.run`, swapping argv[0] for
   `[sys.executable, fake_claude.py]`; no production change; positional
   consumers in test_funnel_main.py listed. Applied.
5. 00073 - `test_sweep_verify_control.py` and `test_sweep_enumerate.py` named;
   the `result is None` test rewritten and renamed
   `test_verify_control_raises_when_the_fallback_check_cannot_run` behind a
   premise (line 85; success-case asserts at 19/33 stay). Applied.
6. 00079 - `survey_test_helpers.py` allowed for plain helpers, fixtures in
   conftest, ambiguous tests stay in `test_survey.py`, inventory covers all
   three file kinds, path `docs/dev/tmp/`. Applied.
7. 00074 - merged into 00076 (items 5-7; item 2 dropped as already done;
   start/advance restated). 00074 moved to `hold/` as absorbed. Applied.
8. 00076 - rollback set selected by rule with an execution-time premise
   (eight tests at 2026-10-10), final set reported in the commit body. Applied.
9. Citations - in-home links repointed to `docs/dev/project-management/`;
   00075/00080 cross-repo cites rewritten as prose with `link-ok:`, no
   personal paths or private project name. Applied.
10. Low batch - 00073 line drift (:584, 34 lines, cosmetic criterion
    dropped); 00077 keys :210-217 and except :223; 00080 premise uses "no
    match" and cites :90-118 / :84; 00076/00077 dedupe (00076 keeps a
    partial-save probe, missing-dir message names the directory);
    00079 `design: skip`. Applied.

Post-apply checks: `check_links.py` reports 0 dangling citations under
`prds/backlog/`; all seven minimal-template PRDs carry the 10 template
headings, 00075 carries every standard-template heading; largest PRD 190
lines. Deferred (no PRD yet): the dev/local half-migration outside the
backlog (capsule Key Invariants, designs/, meta/agoge-profile.md) - recorded
under Gaps above.
