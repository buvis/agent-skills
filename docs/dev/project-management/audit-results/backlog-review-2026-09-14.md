# Backlog review - agent-skills - 2026-09-14

Verdict: GO (0 Blocking open after the 2026-09-14 apply pass; 26 PRDs READY)

Reviewed all 26 backlog PRDs end-to-end at HEAD 33ceb50, with 1 WIP (00052,
building in a live headless session at review time), 31 done and 21 held PRDs
as context. No discovery directory exists. 25 of the 26 were reviewed on
2026-09-08 and patched on 2026-09-13 (`backlog-review-2026-09-08.md`); the
one new PRD is 00080 (created today). All eight lenses ran; three parallel
grounding agents re-verified 00053-00060, 00061-00069 and 00071-00079 against
HEAD, and the reviewer grounded 00075 and 00080 directly (including the
installed autopilot 0.5.2 plugin for 00080's plugin claims). Specification
review only: no test suite ran (a build session holds the tree), no
implementation.

## Map

| # | PRD | template | lines | subsystems | depends on | verdict |
|---|---|---|---:|---|---|---|
| 00053 | Portfolio test split | minimal | 114 | brief JS/Python tests | current baseline; retargets 00054-00069 | READY |
| 00054 | Metadata non-JSON failures | minimal | 90 | brief collector | 00053 | READY |
| 00055 | Metrics timestamps | minimal | 99 | brief collector | 00053 | READY |
| 00056 | CI error reporting | minimal | 93 | brief collector | 00053; done 00026/00028 | READY |
| 00057 | Snapshot permissions | minimal | 125 | brief persistence | 00053 | READY |
| 00058 | URL policy | minimal | 100 | brief derive/components | 00053 | READY |
| 00059 | Torn build inputs | minimal | 97 | brief build | existing xfails | READY |
| 00060 | History append separator | minimal | 79 | brief collector | 00053 | READY |
| 00061 | Local facts before metadata | minimal | 89 | brief collector/history | 00053/00054/00056 | READY |
| 00062 | True commit counts | minimal | 101 | brief collector/derive/detail | 00053/00061 | READY |
| 00063 | Missing registry diagnostic | minimal | 78 | brief collector | 00053 | READY |
| 00064 | Symlinked source candidates | minimal | 82 | braid inventory | existing xfail | READY |
| 00065 | Bounded history retention | minimal | 81 | brief build | 00059 | READY |
| 00066 | Clipboard escaping | minimal | 80 | brief Todos | 00053; preserve 00058 | READY |
| 00067 | Remote slug parsing | minimal | 89 | brief collector | 00053 | READY |
| 00068 | Shared branch lookup | minimal | 83 | brief collector | 00053; 00062 | READY |
| 00069 | Announcement timing test | minimal | 95 | brief Todos/harness | 00053 | READY |
| 00071 | Publication recovery | minimal | 165 | distil writer/queue/docs | done 00015-00017 | READY (refresh N04) |
| 00072 | Judge stdin/no persistence | minimal | 94 | distil judge/tests | preserve done 00034 | READY |
| 00073 | Sweep setup and reports | minimal | 130 | sweep-fix | done 00032 | READY |
| 00074 | Tests bind their intent | minimal | 92 | distil tests | 00071; done 00017 | READY |
| 00075 | PRD grounding checker | standard | 190 | create-prd/backlog gate | done 00047 | READY |
| 00076 | Atomicity/refusal tests | minimal | 136 | distil tests | done 00017; 00071/00074 | READY |
| 00077 | Queue failure diagnostics | minimal | 124 | distil queue/docs | 00071/00076; done 00015-00017 | READY |
| 00079 | Survey test split | minimal | 86 | survey tests | 00053 precedent | READY |
| 00080 | Pipeline frontmatter keys + Path rule | minimal | 78 | create-prd/backlog gate docs | 00075 (same files, lower number) | READY (edited 2026-09-14) |

## Findings

### Blocking

- [00080] B/C: Phase 0 task 1 and task 2 acceptances run
  `uv run pytest skills/review-prd-backlog/scripts/test_frontmatter_keys_prose.py -k ...`,
  but that file is created by the Phase 1 gate task, whose Premise says the
  file "does not exist; ... skip with a report on a mismatch". Under
  test-first work the Phase 0 test author creates the file to satisfy task 1,
  so the Phase 1 premise fails and the lens A / lens C edits plus two of the
  four tests are skipped -> fails as: stall (premise skip leaves the PRD half
  done) or rework thrash (implementer forced to choose which acceptance to
  break). Fix: Phase 0 acceptances become `rg` checks on the verbatim text
  (`rg -c 'Twelve fields are recognized'` prints 1 and
  `rg -c '^- \`(pause_on_ambiguity|plan_expansion|session_model|lane|eligibility)' skills/create-prd/SKILL.md`
  prints 5; `rg -c '^\*\*Path rule' skills/create-prd/SKILL.md` prints 1);
  drop the not-exists clause from the Phase 1 premise. (B01)
- [00080] B: the prose test contract "each key appears backticked in the lens
  A `Frontmatter:` line" and "each key opens a `- \`<key>\`` bullet" reads two
  ways. The verbatim lens A text carries `design_gate: user`,
  `pause_on_ambiguity: true` and `plan_expansion: allow` (no closing backtick
  after the key), and every create-prd bullet is `- \`key: value\``, so a
  strict `` `key` `` check fails 3 of 12 keys on one file and 12 of 12 on the
  other, while the implementer may not change either the test or the verbatim
  text -> fails as: wrong-TDD lock-in. Fix: pin the predicate: lens A line
  matches the regex `` `<key>[`:] ``; create-prd has a line matching
  `` ^- `<key>[`:] `` between the two headings. (B02)

### Non-blocking

- N01 [00080] B: Success Criteria "`braid --check` passes" - warden has
  refused `braid --check` in this repo since PRD 00015 (capsule, open
  deferral), and the PRD adds no skill directory, so the link farm cannot
  change. Delete the line.
- N02 [00080] C: CHANGELOG task premise "`### Changed` at the first position
  after `## [Unreleased]`" is false read literally (`### Added` is at :10,
  `### Changed` at :54, both inside Unreleased). Reword: "the first
  `### Changed` hit follows `## [Unreleased]` and precedes the next `## [`
  heading".
- N03 [00080] A/H: six em dashes in the verbatim text (the five new bullets
  and the Path rule). The writing rule bans them and reviewers tail-sweep
  them (00038 precedent), which would make the transcribed text non-verbatim.
  No hook denies them (checked `~/.claude/hooks` and aegis). Replace with
  ` - ` or accept the mismatch with the neighbouring bullets.
- N04 [00071] D: stale citations after 00017 landed: write.py `append_pointer`
  call is at :182 inside a guarded try (not :125 outside), so defects 3 and 4
  in Problem are already fixed (`test_write_crash_safety.py:484`, `:212`);
  `write_memory` "already exists" is at write.py:76 (not :52); SKILL.md refs
  193 -> 205-207, 199-200 -> 211-214, 204-207 -> 217-220; the queue-once test
  is named `test_main_decide_reads_the_queue_once_so_no_later_read_can_be_taken_for_a_refusal`
  (`test_docket_exit_codes.py:244`; 00077 cites the short name too). The
  Solution's "pre-00017 behavior" caveat and task 1's "or retain their
  already-passing 00017 successors" keep this from forcing rework; refresh
  the text so the planner does not plan two no-op fixes.
- N05 [00055, 00057] D: seam wording: 00055 "point `Path.home` at a
  `tmp_path` (the seam the existing metrics tests use)" - the reader tests
  pass `base=`; only the `main()` test patches home (`test_collect.py:877`).
  00057 "patches `Path.replace` (the pattern at the existing
  `data-prev.json.tmp` replace test)" - that test (`test_collect.py:437-462`)
  patches `Path.write_text`; no existing test patches `Path.replace`.
- N06 [00053] D: `skills/brief-portfolio/app/smoke.browser.test.js`
  (Playwright, outside the `test` script) exists and is not named; say the
  split and the inventory exclude it.
- N07 [00072, 00073, 00077] D: line drift only: funnel.py `judge` def at :174
  (`subprocess.run` at :178); sweep.py `except RuntimeError` at :584 (not
  :581) and `_needs_yaml_quoting` is 34 lines (not 43); docket.py `advance()`
  def at :158 (`:182` is the `start` parser). Harmless.
- N08 [00080] D/E: three of the five new keys (`plan_expansion`,
  `session_model`, `lane`) and the Path rule document semantics from
  claude-autopilot PRDs 00189/00200/00204-00206 that are not in the installed
  plugin (0.5.2 has `cli/eligibility.py` and `pause_on_ambiguity`; no
  `cli/lane.py`). The verbatim text says which release each needs, so the
  docs are honest, but their numbers (15 tasks / 3.0x / 8 planned / 2 dirs;
  12 paths / two phases) are frozen before that code exists. Re-verify at the
  gate after that batch lands. An `eligibility:` line testing for
  `cli/lane.py` in the plugin cache would defer 00080 until then, at the cost
  of leaving the two live keys undocumented meanwhile. Observation, no edit
  proposed.

### Questions

- none open. N08 is recorded as an observation; the author's text already
  states the release dependency.

## Reshapes

- None. 00075 and 00080 edit the same two SKILL.md files and CHANGELOG.md;
  00075 runs first (lower number) and 00080's premises are content-anchored
  (`rg` on heading and rule text), so 00075's insertions (step 5.55, a
  `New symbols:` paragraph after step 3 line 80, a step 1 bullet, a
  Dependencies line) do not disturb 00080's anchors (the frontmatter section,
  the Metric rule, lens A line, lens C line). Not renumbered for adjacency:
  00076/00077/00079 between them are unrelated and the cost is one cold
  batch cache.
- 00065 still depends on 00059 (lower number, both backlog): order holds.
- 00074, 00076, 00077 follow 00071 as their text requires.

## Gaps

- 00080's three future keys are consumed from another repo's unbuilt PRDs
  (N08). Nothing in this backlog produces them; nothing should.
- 00076 and 00077 both add to `test_docket_refusals.py`, which already exists
  at 497 lines (not new); both carry "split if it nears 800".
- Every fix PRD names a regression test. No strategic gap warrants
  `/assess-evolution` from this pass.

## End state after this batch

The portfolio brief collects and builds through torn inputs, flaky GitHub
calls and hostile URLs, counts commits truthfully, protects its snapshot on
both platforms, and its two oversized suites are split. Braid drops symlinked
source entries. distil-memory can recover a publication that failed, never
re-ingests its own judge transcripts, and its crash-safety and refusal suites
observe real renames. sweep-fix fails loudly on setup errors. survey's suite
is under the cap. create-prd gains a grounding gate (00075) and documents the
full pipeline frontmatter plus the lane Path rule (00080), and this gate
recognises the same twelve keys. Still outside: the held Qwen and Windows
work, and the autopilot release that gives the three future keys meaning.

## Frontmatter tuning

| PRD | suggestion | why |
|---|---|---|
| 00080 | keep `catchup: skip`, `design: skip`, `sonnet` | pure transcription with exact text; the rg/regex fixes above keep it so |
| 00071 | keep `catchup: force` | its Problem list predates 00017; the session must re-ground |

## Verification and limits

- Every backlog PRD was read fully before findings were generated.
- Mechanical lens A: 26 files all `NNNNN-{slug}-v1.md`; sequence numbers
  unique across backlog/wip/done/hold (no discovery dir; 00005 unused, no
  duplicates); task lines equal `Acceptance:` counts in every file (rg -c);
  no `{...}`, TBD, TODO, `???` or `(guess)` markers (the one `{...}` hit is
  00058's `href={...}` code); frontmatter keys seen: `default_model`,
  `model_tier_rationale`, `design`, `catchup`, `rework_cap`, all valid;
  `#### Feature:` headings only in 00075, unique; every file under 200 lines
  (largest 00075 at 190).
- `check_links.py --root . --json` on backlog/wip: only 00053 line 97 and
  00079 line 69, both inventory files those PRDs declare they will create;
  exempt forward references.
- Human-in-the-loop sweep (`ask the user`, `user confirms`, `manually`,
  `decide later`, `during implementation`): no hits.
- 00080 plugin claims verified in autopilot 0.5.2: `phase-build.md:70`
  (eligibility gate, project root, 30 s) and `:130` (`pause_on_ambiguity`);
  `cli/eligibility.py` (shell=True, 30 s); `cli/frontmatter.py` recognises
  the four enums, `rework_cap`, and the two exact-value opt-ins, drops
  unknown keys silently and warns on invalid values (matches the verbatim
  closing line); no `cli/lane.py`. Cited skill lines all exact today:
  create-prd 80/86/88/90/116/130/134, review-prd-backlog 23/46/67/84/88,
  CHANGELOG 8/10/54. `validate_skill.py` caps SKILL.md at 500 lines as a
  warning only (create-prd is 250).
- Grounding agents covered 00053-00060, 00061-00069, 00071-00079; all three
  completed. No PRD is already implemented on HEAD (last brief-portfolio
  code commit 2026-09-05; distil-memory changes since are 00017's rollback,
  covered by N04). Runtime numbers (00068 process counts, 00069 timings,
  00079's historical line counts) were not re-measured.
- Not run: test suites (a headless build of 00052 holds the tree),
  `braid --check` (warden-refused; no skill text changed).

## Decisions applied

Decision and apply pass 2026-09-14, HEAD 33ceb50.

| Finding | User choice | Apply status |
|---|---|---|
| B01 / 00080 | Option 1: rg-anchored Phase 0 | Applied: task 1 accepts on `rg -c 'Twelve fields are recognized'` = 1 and the five-bullet `rg -c` = 5; task 2 on `rg -c '^\*\*Path rule'` = 1; Phase 1 premise no longer requires the test file to be absent |
| B02 / 00080 | Option 1: pin the regex | Applied: test 1 uses `` re.search("`" + key + "[`:]", line) `` on the lens A line; test 2 uses `` re.search("^- `" + key + "[`:]", line) `` between the two headings |
| N01 / 00080 | Accepted | Applied: `braid --check` success criterion removed |
| N02 / 00080 | Accepted | Applied: CHANGELOG premise reworded (first `### Changed` hit after `## [Unreleased]`, before the next `## [`; `### Added` between them expected); rg pattern widened to `^## \[` |
| N03 / 00080 | Accepted | Applied: seven em dashes replaced with ` - ` (five bullets, Path rule, lens A line) |
| N04 / 00071 (+00077) | Accepted | Applied: Problem items 3-4 marked fixed by 00017 with the crash-window residue kept, citations refreshed (write.py:182/:76, SKILL.md 205-207/211-214/217-220), queue-once test cited by its real name in 00071 task 2 and both 00077 sites |
| N05 / 00055, 00057 | Accepted | Applied: seam parentheticals now name `test_collect.py:877` and `:437-462` (`Path.write_text`) |
| N06 / 00053 | Accepted | Applied: Solution and inventory task exclude `smoke.browser.test.js` |
| N07 / 00072, 00073, 00077 | Rejected (cosmetic) | Not applied; noted here as the durable record |
| N08 / 00080 | Observation | No edit; re-verify the three future-key bullets at the gate after the autopilot batch carrying PRDs 00189/00200/00204-00206 lands |

### Apply-pass verification (2026-09-14, HEAD 33ceb50)

- Lens A re-run on 00053, 00055, 00057, 00071, 00077, 00080: task lines
  equal `Acceptance:` counts (5/5, 2/2, 2/2, 4/4, 3/3, 4/4); minimal-template
  headings present in order on 00080; frontmatter fields and values all
  recognized; no `{...}`, TBD, TODO, `(guess)` or em dash remains in 00080;
  every file under 200 lines (00071 now 169, 00053 115, 00080 78).
- `check_links.py --root . --json` on backlog/WIP: only 00053 line 98 and
  00079 line 69, both declared inventory outputs; exempt forward references.
- No WIP, done, hold or execution-state file was touched; the 00052 build
  session's dirty use-qwen files were left alone.
- Not run: test suites (no code changed), `braid --check` (no skill text
  changed).
