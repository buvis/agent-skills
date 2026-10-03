---
prd: dev/local/prds/wip/00059-build-dies-on-torn-inputs-v1.md
review: 1
date: 2026-09-26
head_sha: 95986ba86f70c801176b73658647de9c32a2c983
codex_thread_id: 01a0dc4c-c203-7510-baf1-86559a447b96
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00059-build-dies-on-torn-inputs-v1

Diff range: `4aa12015ff85c5d19ba762e2d0de2ff6cee750d6..95986ba86f70c801176b73658647de9c32a2c983`

codex_rung_guard: not fired

## Diff-scope note (read this before the findings)

Cycle 1, a **full** review of the PRD's whole work range. The range was pinned
explicitly to `state.work_start_sha..HEAD` rather than left to
`gather-context.sh`'s branch-base detection: this repo commits straight to
`master`, so that detection would have diffed `master` against a clean worktree
and handed every reviewer an empty diff. The context file therefore carries the
script's own "incremental review" label, which is a label artefact, not the
scope — a note at the top of the context file says so, and there is no prior
cycle and no prior findings to verify.

Five commits, three files: `447759f` + `9b6a33d` (task 1), `f99813a` + `608c471`
+ `95986ba` (task 2), touching `skills/brief-portfolio/scripts/build.py`,
`skills/brief-portfolio/scripts/test_build_page.py` and `CHANGELOG.md`.

pack: skipped (`engram pack` exited 1 — `not inside a registered repo; register
it in /Users/bob/.config/gita/repos.csv`). Non-fatal by contract: `{PACK_FILE}`
and `{PACK_FINDINGS}` were substituted with `(no pack available this cycle)` for
every reviewer that takes them, and Blake never receives a pack by design. The
review is degraded by the missing findings-precedent section, not invalid.

## Mechanical checks: what actually covered this diff

Computed, not judged — appended to the context file every implementation-aware
reviewer read.

- **Function sizes** (`ast`): `_load_data` 8, `_load_epics` 9, `_load_history`
  17, `main` 22 lines. All four inside the 50-line limit; `build.py` is 82 lines
  and `test_build_page.py` 219, both far inside the 800-line limit. R12/R13 rest
  on this block, not on a reviewer's count.
- **Tautological shapes**: 10 test functions checked in 1 test file, **no**
  `[MECH]` line. No constant assert, self-comparison, `A or B` hedge, swallowed
  exception, `raises(Exception)`, or assertion-free test.
- **Fail-first replay** (HEAD's test files overlaid on a `4aa12015ff85` worktree,
  `uv run pytest`): 6 touched tests ran, **5 failed** against the pre-change code,
  **1 passed** — `test_a_malformed_line_outside_the_last_60_window_is_not_decoded_or_warned_about`.
  That one is a computed `[MECH]` 🟡 finding, absorbed into the table below on
  the row Bob raised independently for the same test.

## Consolidated Findings

7 findings, every one 🟡 Medium. **No 🔴 Critical and no 🟠 High.** Alice's ⚪
stale-comment line merged with Bob's 🟡 line for the same comment, so the merged
row carries the higher severity at [2/4].

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [2/4] | 🟡 | Stale comment: test_build_page.py:79 ("Found by an agoge run on 2026-09-05... so the strict xfail is the executable record of the defect") still describes an xfail pattern, but both xfail markers this comment was written to explain (on the history-line test and the data.json test) were deleted by this PRD's tasks. The comment now sits above a block of tests that never uses xfail, so it misleads a future reader. | skills/brief-portfolio/scripts/test_build_page.py:79 | general | ALICE, BOB |
| [1/4] | 🟡 | Duplicated decode-or-exit pattern: `_load_data` and `_load_epics` each repeat the identical `try: json.loads(...) / except json.JSONDecodeError as e: sys.exit(f"{path}: {e}")` shape. A shared `_load_json_or_exit(path)` helper (called from both, after each function's own is-file check) would remove the duplication without changing behavior or violating the task's "do not share one try block across both loads" instruction, which forbids merging the two reads into one try, not extracting a two-caller helper. | skills/brief-portfolio/scripts/build.py:20 | 2 | ALICE |
| [1/4] | 🟡 | data-prev.json is read with a bare json.loads and no try/except; a malformed/truncated data-prev.json still crashes the build with a full traceback, the same failure mode this PRD fixes for the other three inputs, but this fourth file wasn't named in the PRD's scope | skills/brief-portfolio/scripts/build.py:39 | general | BLAKE |
| [1/4] | 🟡 | FIX: The data/epics tests only inspect the caught `SystemExit` string for a basename, so they do not pin the required decode reason, one-line stderr, or absence of `Traceback`; invoke the CLI and assert the complete stderr contract for both inputs | skills/brief-portfolio/scripts/test_build_page.py:194 | 2 | BOB |
| [1/4] | 🟡 | FIX: This test passes against the pre-change implementation, so it does not pin the PRD change; include both an out-of-window malformed row and a selected malformed row, then assert only the selected row warns, making the test fail first while preserving the no-backfill check | skills/brief-portfolio/scripts/test_build_page.py:122 | 1 | BOB, mech-check |
| [1/4] | 🟡 | FIX: This 30-line two-build comparison duplicates the one-fewer-history-point assertion already established by the two-row fixture and `len(history) == 1`; delete the redundant test | skills/brief-portfolio/scripts/test_build_page.py:162 | 1 | BOB |
| [1/4] | 🟡 | FIX: `_load_history` also reads `data-prev.json` and returns it as an unrelated tuple member, obscuring the per-input loader boundary; load `prev` in `main` and have `_load_history` return only history | skills/brief-portfolio/scripts/build.py:37 | general | BOB |

Consolidation ran through `consolidate_findings.py` (exit 0, 4 agent pairs). No
ledger existed for this PRD on cycle 1, so the `--ledger`/`--ledger-dismiss`
flags were correctly omitted and nothing was auto-dismissed.

## Alice

Two findings, no CRITICAL or HIGH.

- ⚪→🟡 (merged) Stale comment at `test_build_page.py:79` still describes the
  xfail pattern whose two markers this PRD deleted.
- 🟡 `_load_data` and `_load_epics` repeat the identical decode-or-exit shape; a
  two-caller `_load_json_or_exit(path)` helper removes it without merging the two
  reads into one try block.

Verification she performed herself: read both files in full plus the diff;
confirmed the WARN text, the 1-based physical numbering (`enumerate(...,
start=1)` before the nonblank filter), the preserved tail window, both
`sys.exit(f"{path}: {exc}")` exits, and the untouched missing-epics.json
WARN-and-continue path; ran `uv run pytest
skills/brief-portfolio/scripts/test_build_page.py -q` (10 passed); confirmed via
`rg` that no `xfail` marker remains and that nothing outside the test file and
the CLI entry point calls the new helpers (R4); checked function/file sizes
against the mechanical-facts block; confirmed test-before-fix commit order for
both tasks and the `### Fixed` CHANGELOG entry under `[Unreleased]`.

On the replay row she did **not** fail R2, and gave her reason: the old
`lines[-60:]` selection already excluded the out-of-window malformed line, so
the test pins a rule the PRD explicitly calls out as preserved, and it can still
fail on a plausible regression (an off-by-one in the new tail slicing).

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
R12: pass
R13: pass

## Blake

Blind lens: PRD only, no diff, no file list, no review history, no pack. He
located the code himself, ran `uv run pytest
skills/brief-portfolio/scripts/test_build_page.py -q` (10 passed) and `uv run
pytest skills/brief-portfolio/scripts -q` (90 passed, 2 xfailed — both in
`test_collect_pipeline.py`, pre-existing PRD 00060 markers, untouched here), then
reproduced all three of the PRD report's failure modes end to end through the
real CLI in a scratch dir and cleaned it up.

He confirmed each of the three named inputs against the spec: `_load_data` and
`_load_epics` exit 1 with one line naming the file and the decode error and no
traceback; `_load_history` numbers physical lines correctly, refuses to backfill
outside the tail, and writes the page while warning about the torn line. No
remaining `xfail` markers, no new flags, no new dependencies, `main()` and the
`--dir`/`--out` defaults unchanged, no scope creep into PRD 00060's collect.py.

One gap, and it is the finding that failed a rule:

- 🟡 `data-prev.json` is read at `build.py:39` with a bare `json.loads` and no
  try/except, so a malformed one still crashes the build with a full traceback —
  the identical failure mode this PRD removes for the other three inputs. He
  notes the mitigation (collect.py writes it via write-then-atomic-rename, not
  the raw append history.jsonl uses) and that the PRD named only three inputs.

B1: pass
B2: pass
B3: pass
B4: pass
B5: pass
B6: pass
B7: pass
B8: pass
B9: pass
B10: pass
B11: pass
B12: pass
B13: pass
B14: fail
B15: pass
B16: pass
B17: pass
B18: pass
B19: pass

B14 ("no unguarded database queries or file operations") is the data-prev.json
row above. Every other rule passed; B15-B17 are vacuous for a Phase-0-only PRD.

## Bob

Doubt + de-slop lens on codex, first run, no retry needed. Five findings, all
🟡, no CRITICAL or HIGH:

- 🟡 the data/epics tests assert only a basename inside the caught `SystemExit`,
  pinning neither the decode reason nor the absence of a traceback
  (`test_build_page.py:194`);
- 🟡 `test_a_malformed_line_outside_the_last_60_window_is_not_decoded_or_warned_about`
  passes against the pre-change code, so it does not pin this change; include
  both an out-of-window and a selected malformed row and assert only the selected
  one warns (`test_build_page.py:122`) — the computed replay block raised the
  same test independently;
- 🟡 the 30-line two-build comparison duplicates the one-fewer-point assertion
  (`test_build_page.py:162`);
- 🟡 the comment at `test_build_page.py:79` still claims strict xfail markers that
  were removed;
- 🟡 `_load_history` also reads `data-prev.json` and returns it as an unrelated
  tuple member, blurring the per-input loader boundary (`build.py:37`).

R1: fail
R2: fail
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
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

Bob's R1/R2 fails are the two test-quality rows above (incomplete stderr
contract, one test that passes against base). He emitted no FIX/VERIFY/KNOWN
bucket sections — his assembled prompt carries eve.md's "Two lenses" and "Rubric
verdicts" sections only, not her bucket section — so he raised no VERIFY item and
**no verification-check queue was written this cycle** (`checks-1.json` absent by
design, not by omission).

## Carl

Ran on backend `copilot`, model `gemini-3.8-flash`, exit 0, non-empty output. He
read the diff and both files, ran `uv run pytest
skills/brief-portfolio/scripts/test_build_page.py -vv`, `uv run pytest
skills/brief-portfolio -q`, `uv run pytest skills/brief-portfolio -rxX`, the
skill validator and `braid --check`, and checked the remaining `xfail` matches
and the SKILL.md prose.

[CARL] ✅ No issues found

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
R12: pass
R13: pass

The diff has no frontend surface, so he reviewed as a generalist and did not
invent frontend findings.

## Reviewer run notes

- Every lens ran. `consensus` (Alice), `blind` (Blake), `doubt` (Bob), `ui`
  (Carl) all `done`; no reviewer failed, none was skipped, no retry was spent.
  Carl was **not** batch-skipped (`state.batch.unavailable_reviewers` absent) and
  succeeded on his first dispatch this cycle.
- Eve did not run, and correctly so: `codex_rung_guard: not fired` — both tasks
  carry `implementor: "claude"`, so the codex doubt-roster guard's predicate is
  false and she stays the opt-in fifth lens. `state.doubt_reviewer` is `codex`.
- `consensus_engine` is `legacy`, so Alice's leg was the single Task subagent;
  no workflow ran and no `consensus_run_id` exists.
- The headless Watcher held the session open for both CLI reviewers and returned
  `DONE` once each published its output.
- Both CLI dispatch rows are closed `--outcome ok` in the dispatch ledger
  (`bob` b9ad4cbf, `carl` 3f91c617).

## Review Summary

Reviewed: 2 completed tasks (2/2), PRD 00059-build-dies-on-torn-inputs-v1.

### Agent Status

- Alice: ✅ Available
- Blake: ✅ Available
- Bob: ✅ Available
- Carl: ✅ Available
- Eve: ⏸️ Disabled: codex doubt-roster guard not fired (no codex-implemented task)

### Consolidated Findings by consensus

**Majority-of-none — no full consensus row.** Highest consensus is [2/4].

- [2/4] 🟡 stale xfail comment | `test_build_page.py:79` | Alice, Bob
- [1/4] 🟡 duplicated decode-or-exit shape | `build.py:20` | Alice
- [1/4] 🟡 data-prev.json read unguarded | `build.py:39` | Blake
- [1/4] 🟡 data/epics tests pin only a basename | `test_build_page.py:194` | Bob
- [1/4] 🟡 out-of-window test passes against base | `test_build_page.py:122` | Bob, mech-check
- [1/4] 🟡 30-line trend test called redundant | `test_build_page.py:162` | Bob
- [1/4] 🟡 `_load_history` also loads data-prev | `build.py:37` | Bob

### What the PRD itself asked for

Every Must-have is met, and three of the four were verified live by a reviewer
who had never seen the diff:

- a torn `history.jsonl` builds the page, warns once naming the physical line,
  and drops exactly one trend point;
- a truncated `data.json` exits non-zero with one named line and no traceback;
- an invalid `epics.json` exits the same way;
- both named `xfail` markers are gone, and `rg -n "xfail"
  skills/brief-portfolio/scripts/test_build_page.py` matches neither test name
  (only the stale prose comment, which is finding 1).

### Follow-up Tasks Created

None created here. Task creation for this converged cycle is owned by the
decision gate's **Tail sweep**, which builds ONE `[D1] Tail sweep` task carrying
every swept finding verbatim, rather than seven per-finding tasks that would
fix the same lines twice.

Verdict: 7 findings
Tests: 3458 passed, 0 failed, 6 skipped (reused from last-verification.json at 95986ba86f70c801176b73658647de9c32a2c983)
