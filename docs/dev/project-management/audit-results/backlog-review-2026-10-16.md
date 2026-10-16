# Backlog review - agent-skills - 2026-10-16

Verdict: GO (after the apply pass; initial verdict NO-GO, 4 Blocking)

Lenses A-H all ran inline (four PRDs, no fan-out needed). Citation
resolution ran via `check_links.py` (162 findings repo-wide, 0 under
`prds/backlog/` or `prds/wip/`). Grounding resolution ran via
`ground_prd.py` (exit 1: 7 `missing`, 29 `unresolved`, 0 `unverified` across
backlog + wip). Plugin claims were checked against the installed autopilot
0.9.0 (`installed_plugins.json` and the cache agree). `autopilot:plan-tasks`
steps 4-4.7 consulted: 150K per-task threshold; no PRD here approaches it.

## Map

Verdicts are the pre-apply ones; lines are pre-apply (post-apply: 178 / 124 /
98 / 80). After the apply pass every PRD is READY.

| # | PRD | template | lines | subsystems | depends on | verdict |
|---|-----|----------|-------|------------|------------|---------|
| 00076 | distil-tests-see-non-atomic-writes | minimal (+ Phase 2) | 176 | distil-memory tests (write, docket, walkthrough) | 00017, 00071 (both done) | FIX |
| 00077 | docket-never-raises | minimal | 125 | distil-memory docket + SKILL | 00015-00017, 00071 (done); 00076 (same test file) | FIX |
| 00079 | split-test-survey-under-the-cap | minimal | 99 | survey tests | 00053 (done) | READY |
| 00080 | recognize-pipeline-frontmatter-keys-and-the-lane-path-rule | minimal | 79 | create-prd, review-prd-backlog, CHANGELOG | 00075 (wip, edits landed) | FIX |

wip: 00075 ground-prd-claims (standard, 191 lines) - loop state `phase: done`,
file still in `wip/` (see Hygiene).

Hygiene: only `NNNNN-slug-v1.md` files in `backlog/`; 82 distinct sequence
numbers across backlog/wip/hold/done, no duplicates (no `intake/` or
`discovery/` directory exists); this report lives in `audit-results/`.

## Findings

### Blocking

- [00077] D (mechanical, 7 `missing` + 9 `unresolved`): every citation is
  skill-relative and stale after 00071 landed (`docket.py` is 349 lines now).
  `docket.py:207/:218/:223/:250/:50/:251/:30/:210-217` and `SKILL.md:203-207`
  resolve to nothing from the repo root. Actual: `_save_from_proposals_dir`
  at `skills/distil-memory/scripts/docket.py:266`, its reads at `:273` and
  `:284`, `except` at `:289`, the six indexed keys at `:276-283`,
  `_save_queue` at `:30`, the `load()` guard at `:50`, the `decide --file`
  read at `:316`, exit-code lines at `skills/distil-memory/SKILL.md:205-207`.
  The nine new test names carry no `New symbols:` line. -> fails as: stall
  (an implementor premise check trips on `docket.py` not found) and the gate's
  own grounding rule. Fix: repo-relative citations at current lines; a
  `New symbols:` line in the test_docket_refusals Module block.
- [00077] D/C: PRD 00071 (done 2026-10-10) already widened the `decide
  --file` guard to `(OSError, UnicodeDecodeError)` (`docket.py:317`) and
  removed the dead `json.JSONDecodeError` arm; `test_docket_cli.py:379`
  (`test_main_decide_with_a_non_utf8_file_returns_one_with_a_reason_and_leaves_the_queue_untouched`)
  pins it. Problem item 1 (its `--file` half), item 3, the Must-have
  "a latin-1 `decide --file` ... exit 1" and task 1's
  `test_decide_refuses_a_latin1_file` "watched red against the old code
  first" describe work that is done; the test cannot go red. -> fails as:
  rework thrash (fail-first mandate unmeetable; reviewers flag a duplicate
  test or an unmet acceptance). Fix: drop the `--file` latin-1 item
  everywhere; Solution widens the one remaining guard.
- [00076] D (mechanical, 14 `unresolved`): `test_main_decide_reads_the_queue_once`
  (Must-have Task 4, line 87) names no test; the real one is
  `test_main_decide_reads_the_queue_once_so_no_later_read_can_be_taken_for_a_refusal`
  (`test_docket_exit_codes.py:244`). The 13 new test names carry no
  `New symbols:` line. -> fails as: wrong-TDD lock-in on the misnamed mirror;
  the gate's grounding rule for the rest. Fix: full name; `New symbols:`
  lines in the three Module blocks.
- [00080] D (mechanical, 6 `unresolved`): the four new test names and the
  two keys `plan_expansion` / `session_model` in the `KEYS` tuple (line 36)
  exist nowhere in this repo until the PRD lands. -> fails as: the gate's
  grounding rule. Fix: `New symbols:` line in the backlog gate Module block.

### Non-blocking

- [00076] D: line drift after 00071 - `proposal.validate(candidate)` is at
  `test_walkthrough_integration.py:90` (PRD: 86); the three unused `capsys`
  parameters are at `test_docket_cli.py:399`, `:425`, `:450` (PRD: 251, 277,
  302 - those tests now read capsys). The eight rollback tests still sit at
  :212/260/291/340/375/412/552/584 and the file is still 658 lines.
  Dependencies says "PRD 00071 (backlog, lower number)" - it is in `done/`.
- [00077] D: Solution's "when 00071 has landed" - it has; trim.
- [00076/00077] F: both append to `test_docket_refusals.py` (497 lines
  today; ~8 and ~10 tests). Both say split near 800; no action.
- [00080] D: line cites drifted after 00075 landed: create-prd § Optional
  frontmatter fields `:90-118` -> `:96-124`, Metric rule `:86` -> `:92`;
  gate `Frontmatter:` `:67` -> `:68`, `Functional <-> structural` `:88` ->
  `:89`, tuning line `:84` -> `:85`; CHANGELOG `### Changed` `:84` -> `:91`.
  Every premise is pattern-based and verified to hold today (three/one/one
  hits, no key present, Metric rule once, no Path rule).
- [wip 00075] D (not editable here): Test Strategy names
  `test_fenced_blocks_and_frontmatter_are_not_scanned` and
  `test_a_directory_argument_expands_to_its_markdown_files`; the shipped
  suite covers them under other names
  (`test_fenced_block_yields_no_claims_and_keeps_line_numbers`,
  `test_frontmatter_symbol_is_not_scanned_and_lines_count_from_original_text`,
  `test_cli_directory_argument_expands_non_recursively_to_sorted_md_files`),
  so Success Metric 1 ("every scenario ... is a named test") is not literally
  met; `skills/create-prd/SKILL.md:80` drifted to `:84`.
- Hygiene: 00075 sits in `wip/` while `state.json` records `phase: done`,
  `next_phase: done` (review 2 converged `cap_deferred` 2026-10-11, 13
  deferred rows). This is the documented mid-Phase-9 shape (run-autopilot
  SKILL.md § Batch-identity rollover): the next session routes to
  `phase-done.md` and performs the verified move before selecting from
  `backlog/`. No gate action; noted so the batch's first session is not
  misread as "working 00075 again".

### Questions

- none beyond the fix choices above.

## Reshapes

- none. Sizes 79-176 lines, one subsystem each, distil-memory pair adjacent.

## Gaps

- `CHANGELOG.md` has one `## [Unreleased]` heading and two sets of
  `### Added` / `### Changed` / `### Fixed` under it (second `### Added` at
  :364, added 2026-08-26 in f8e91be2); the repo has no tags. 00077 and 00080
  append under the first set, so they are unaffected, but a release cut would
  split wrong. No PRD.
- Carried from 2026-10-10: the `dev/local` -> `docs/dev/project-management`
  half-migration outside the backlog (`check_links.py` reports 162 dangling
  citations in `designs/`, `meta/`, `reviews/`, `audit-results/`). No PRD.
- `hold/` holds 25 parked PRDs; outside this gate.

## End state after this batch

distil-memory's crash-safety, rollback and refusal suites bind to the
behaviour they claim (00076) and the docket CLI exits with a reason on every
undecodable input, bad batch shape and failed queue write (00077); survey's
suite drops under the 800-line cap with a measured equivalence (00079);
create-prd and this gate recognise all twelve pipeline frontmatter keys and
the Path rule, pinned by a prose test (00080). Still lacking: the CHANGELOG
structure, the dev/local citation cleanup, and the parked `hold/` work.

## Frontmatter tuning

| PRD | suggestion | why |
|-----|-----------|-----|
| 00076 | none | opus + rework_cap 3 + catchup force fit the timing tests |
| 00077 | none | sonnet, exact tuples and messages given |
| 00079 | none | opus for the equivalence obligation, design skip |
| 00080 | none | sonnet, skip/skip, verbatim text |

## Decisions applied

1. 00077 citations - every cite repointed repo-relative at today's lines
   (`_save_from_proposals_dir` :266-294, `load` :42-61, `--file` read
   :316-317, `_save_queue` :30-34, six keys :276-283, SKILL.md :205-207);
   `New symbols:` line with the nine new tests. Applied.
2. 00077 done item - the `decide --file` latin-1 half of Problem 1, Problem 3,
   its Must-have clause and `test_decide_refuses_a_latin1_file` dropped;
   routes renumbered to three; Solution widens the proposals-dir guard only
   and credits 00071 for the `--file` guard; Dependencies name 00071. Applied.
3. 00076 grounding - mirror renamed to
   `test_main_decide_reads_the_queue_once_so_no_later_read_can_be_taken_for_a_refusal`;
   `New symbols:` lines in the test_write_atomicity (6) and
   test_docket_refusals (8) Module blocks; the existing-suites block creates
   no new test, so it got none. Applied.
4. 00080 grounding - `New symbols:` line in the backlog gate Module block
   (four tests, `plan_expansion`, `session_model`); the explanatory note sits
   on its own line because the checker's comma-split glues a trailing
   parenthetical onto the last token. Applied.
5. Low batch - 00076 lines 86 -> 90, 251/277/302 -> 399/425/450, rollback
   premise re-dated after 00071, Dependencies say 00071 is done; 00077
   "when 00071 has landed" trimmed; 00080 cites :90-118 -> :96-124, :86 ->
   :92, :67 -> :68, :88 -> :89, :84 -> :85, CHANGELOG :84 -> :91. Applied.
6. 00075 in wip - left to the batch's first session (phase-done routing).
   No action.

Post-apply checks: `ground_prd.py` over `prds/backlog/` exits 0 (0 blocking,
0 unverified, 58 declared-new); `check_links.py` reports 0 dangling citations
under `prds/backlog/` or `prds/wip/`; lens A re-walked on 00076, 00077 and
00080 - all minimal-template headings present in order, every task carries
`Acceptance:`, no stub markers; largest PRD 178 lines. Surprise test: the
00077 item that 00071 had already shipped (finding 2) was not in the
2026-10-10 review.
