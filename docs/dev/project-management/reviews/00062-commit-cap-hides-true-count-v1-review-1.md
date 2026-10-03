---
prd: dev/local/prds/wip/00062-commit-cap-hides-true-count-v1.md
review: 1
date: 2026-09-26
head_sha: da66f97e72c6e2793e3cf7811a28842be68823ad
codex_thread_id: 01a0dd75-6b08-7423-b3c5-071372069447
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00062-commit-cap-hides-true-count-v1

Diff range: `0b69947..da66f97` (`work_start_sha..HEAD`, the PRD's whole work
range; cycle 1, so this is a full review). One path was excluded from the
reviewer diff: `skills/brief-portfolio/assets/template.html`, a committed
minified vite build artifact whose 4-line diff is ~200KB. Alice and Carl each
verified it independently by rebuilding and diffing instead of reading it.

codex_rung_guard: not fired

pack: failed (`engram pack` exited 1: "not inside a registered repo; register it
in the gita repos.csv"). No retry: the failure is a deterministic
configuration fact, not a transient one. `{PACK_FILE}` and `{PACK_FINDINGS}`
were substituted with `(no pack available this cycle)` in every prompt that
takes them. The review is degraded by the missing retrieval context, not
invalid.

## Review Summary

Reviewed: 2 completed tasks
PRDs checked: 00062-commit-cap-hides-true-count-v1

### Agent Status

- Alice: ✅ Available (consensus lens, ran both suites and a rebuild+diff)
- Blake: ✅ Available (blind lens, PRD-only, located the code himself)
- Bob: ✅ Available (codex, doubt + de-slop lens, static-only sandbox)
- Carl: ✅ Available (gemini, frontend & design lens, ran both suites and a rebuild+diff)
- Eve: ⏸️ Disabled (the codex doubt-roster guard did not fire — no task was
  implemented by codex, so she is not activated; `doubt_reviewer` is `codex`)

Consensus engine: `legacy` (one Alice subagent; no `review-fanout` workflow run,
so no `consensus_run_id`).

## Consolidated Findings

No 🔴 Critical and no 🟠 High finding from any lens. Ten findings, all 🟡 Medium
or ⚪ Low.

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [2/4] | 🟡 | Four `aggregate()` unit tests live in `smoke.repos.test.js` (smoke.repos.test.js:90-111) rather than the idiomatic `src/lib/derive.test.js`; this follows the task's own file list verbatim (not a defect), flagging per the build note for a future cleanup pass | skills/brief-portfolio/app/smoke.repos.test.js | 2 | ALICE, BOB |
| [1/4] | 🟡 | `test_history_row_commit_field_falls_back_to_the_list_length_without_a_count` and `test_a_failed_metadata_call_leaves_commit_count_absent` pass against the pre-change code (confirmed by the context's fail-first replay block), so neither pins new behavior on its own | skills/brief-portfolio/scripts/test_collect_pipeline.py | 1 | ALICE, mech-check |
| [1/4] | 🟡 | Three JS tests have the same shape and aren't covered by either replay script (JS wasn't replayed): `aggregate falls back to commits.length for a repo with no commit_count key` (smoke.repos.test.js:95), `RepoDetail renders a plain commit count when commit_count matches the list length` (smoke.repos.test.js:160), and `RepoDetail and the Brief headline fall back to commits.length when commit_count is absent` (smoke.repos.test.js:175) all produce the same output on pre-change code as on this diff | skills/brief-portfolio/app/smoke.repos.test.js | 2 | ALICE |
| [1/4] | 🟡 | FIX: Two Python tests pass against the pre-change code, while the specified count-only error-marker state remains untested; strengthen the fallback test to assert `c` and `e`, and use a `collect_commit_count` sentinel in the metadata test | skills/brief-portfolio/scripts/test_collect_pipeline.py:448 | 1 | BOB |
| [1/4] | 🟡 | FIX: Three new JS compatibility tests pass unchanged against the pre-change implementation; fold their assertions into changed-behavior cases so every test binds the regression | skills/brief-portfolio/app/smoke.repos.test.js:95 | 2 | BOB |
| [1/4] | 🟡 | FIX: The fixed 2020 commit date with a 3650-day inclusion window will age into failure; derive the old timestamp relative to now and use stable 60/120-day windows | skills/brief-portfolio/scripts/test_collect_pipeline.py:366 | 1 | BOB |
| [1/4] | 🟡 | FIX: The capped-list test duplicates the new `_serve_git_from_tmp_repos` setup; call the helper and retain only the `MAX_COMMITS` override | skills/brief-portfolio/scripts/test_collect_pipeline.py:328 | 1 | BOB |
| [1/4] | 🟡 | Simplify commit_count fallback: replace ('commit_count' in r ? r.commit_count : (r.commits?.length ?? 0)) with r.commit_count ?? (r.commits?.length ?? 0) | skills/brief-portfolio/app/src/lib/derive.js:116 | 2 | CARL |
| [1/4] | ⚪ | Cannot statically verify: runtime tests and generated-template reproducibility; VERIFY with `uv run pytest -q`, `npm --prefix skills/brief-portfolio/app test`, and a fresh app build followed by comparison with `assets/template.html` | N/A | general | BOB |
| [1/4] | ⚪ | Move mid-file import { aggregate } to top of file with existing imports | skills/brief-portfolio/app/smoke.repos.test.js:88 | 2 | CARL |

`consolidate_findings.py` merged one pair of citations that matched only after
suffix stripping (`smoke.repos.test.js` ~ `smoke.repos.test.js:80`), which is
how row 1 reached [2/4]. It did **not** merge rows 2 and 4, nor rows 3 and 5,
although each pair describes one defect; their wordings diverged too far. The
decision gate treats each pair as ONE decision — see the ledger below.

### Mechanical test checks

The two computed blocks were appended to every implementation-aware prompt.

- **Tautological test shapes:** 41 test functions checked across 2 Python test
  files, **no** `[MECH]` line — no assert is constant, self-comparing, or an
  either-or hedge.
- **Fail-first replay** (`uv run python -m pytest`, base `0b69947`): 7 touched
  tests ran, **5 failed against base, 2 passed**. Its one `[MECH]` 🟡 line names
  `test_history_row_commit_field_falls_back_to_the_list_length_without_a_count`
  and `test_a_failed_metadata_call_leaves_commit_count_absent`. That line is
  absorbed into row 2 above, whose finders therefore read `ALICE, mech-check`.
- **Both blocks cover Python only.** The JS suite (`smoke.repos.test.js`, run by
  `node --test`) was replayed by neither script. Rows 3 and 5 are Alice's and
  Bob's *reading*-based equivalents for JS, not a computed result — recorded
  here so the difference in evidence strength is visible.

### Verification-check queue

**No queue file was written for this cycle.** Eve did not run (the codex
doubt-roster guard did not fire), and `agents/bob.md` emits `[BOB]` issue lines
plus `R{n}` verdicts with no FIX/VERIFY/KNOWN buckets, so `source: "bob"` is
reserved and no entry may be sourced from him. Bob's ⚪ row above is a sandbox
limitation, not a queued check; it is resolved by this cycle's own reviewer
evidence (see the ledger) rather than deferred to the work phase.

## Alice

Consensus lens, implementation-aware. Ran the checks rather than reading only:

- `uv run pytest skills/brief-portfolio/scripts -q` → 103 passed, 1 xfailed (the
  pre-existing missing-registry xfail; this PRD's own xfail marker is gone and
  the test now passes as a normal case).
- `npm --prefix skills/brief-portfolio/app test` → 53 passed, 0 failed.
- `npm --prefix skills/brief-portfolio/app run build` then
  `diff dist/index.html skills/brief-portfolio/assets/template.html` →
  byte-identical, confirming the committed template matches source and the
  style-only rename in `da66f97` did not drift it.
- Read `collect_commit_count` (collect.py:88), `history_counts`
  (collect.py:378-397, confirming the forbidden failure-marking tuple at
  collect.py:393-395 was left untouched), and `collect_repo`'s wiring
  (collect.py:461-462). All match the task's verbatim contract.
- Confirmed with `rg` that `Repos.svelte`, `Horizon.svelte` and `Activity.svelte`
  deliberately keep using the capped `commits?.length` (PRD: "the digest and the
  activity tab remain partial by decision"), so no caller was missed.

Her three findings are rows 1, 2 and 3 above. Her own judgement on them: none
are blocking, because the flagged tests pin explicitly-mandated
fallback/boundary preservation rather than incidental laziness — 5 of 7 Python
tests and all 4 non-fallback JS tests do fail against pre-change code.

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

Blind lens: PRD only, no diff, no file list, no task list. He located the code
himself and ran both suites independently.

[BLAKE] ✅ No issues found

His verification, for the record (not findings): `collect_commit_count` added as
specified (collect.py:88) and wired as its own guarded `run_collectors` entry
(collect.py:462); a failing count leaves the key absent and records
`commit_count: <reason>` in `errors` via the shared formatter (collect.py:426);
a failed metadata call leaves it absent too (collect.py:459); `history_counts`
reads `repo.get("commit_count", len(repo.get("commits", [])))` (collect.py:383);
the xfail marker is gone and the test passes (test_collect_pipeline.py:328);
`RepoDetail.svelte:15` renders `of … shown` only when `commit_count > shown`;
`derive.js:116` uses an `in`-check so `commit_count: 0` is trusted rather than
treated as missing; all three required smoke tests exist with the specified
assertions (smoke.repos.test.js:143, :160, :175); 103 passed / 1 xfailed and
53/53 respectively; the template artifact was regenerated in the same commit
series; out-of-scope surfaces stayed out (`write_digest` at collect.py:477 and
`Activity.svelte:11` still use the capped list); no new dependencies, flags,
auth or rate-limiting surface.

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
B14: pass
B15: pass
B16: pass
B17: pass
B18: pass
B19: pass

## Bob

Doubt + de-slop lens, codex, static-only sandbox. Five 🟡 FIX findings and one
⚪ sandbox line (rows 4-9 above). Three of his claims were checked against the
code by the decision gate before classification, and **all three are
confirmed**:

- The 2020 fixture date (`_make_mixed_age_repo`, test_collect_pipeline.py:366)
  combined with the 3650-day assertions at :390 and :393 does age into failure:
  3650 days after 2020-01-01 falls at the end of 2029, after which the two old
  commits drop out of the wide window and both assertions flip. Not urgent, but
  a dated assumption with no need to be dated.
- `test_a_capped_commit_list_still_carries_the_true_commit_count`
  (test_collect_pipeline.py:333-342) hand-rolls a `fake_run` and a `gh_json`
  stub that are behaviourally identical to `_serve_git_from_tmp_repos`
  (test_collect_pipeline.py:350-363) for a repo directory named `busy`. Roughly
  ten lines are removable by calling the helper and keeping only the
  `MAX_COMMITS` override. Definition order does not matter — Python resolves the
  helper at call time.
- The count-only error-marker state is genuinely untested. `history_counts`'s
  failure-marking tuple deliberately excludes `commit_count` (the task's
  verbatim "Do not add" term, which the build phase enforced by reverting the
  implementor's addition), so a repo whose `commit_count` succeeded while every
  other collector failed is still marked `e: 1`. `dev/local/meta/assumptions.md`
  already records that no test pins either behaviour. This is the cycle's most
  valuable finding: it is the one deliberate contract decision the build phase
  left unpinned.

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

Bob's R1/R2 fails are the only failing rule verdicts in the cycle, and they are
the same two facts as rows 4 and 5: some new tests do not fail against
pre-change code. Both are swept (below), not dismissed.

## Carl

Frontend & design lens, gemini. Backend: copilot; the runner reported success on
its first attempt with no native fallback. He read `RepoDetail.svelte`,
`Brief.svelte`, `App.svelte`, `Repos.svelte`, `Activity.svelte`, `Icon.svelte`,
`derive.js` and `derive.test.js`, ran both suites, ran
`npm run build` plus `diff -q` against the committed template (match), ran
`validate_skill.py` and `braid --check`, and probed his own simplification
proposal with a small `node -e` equivalence check before filing it.

[CARL] 🟡 Simplify commit_count fallback: replace ('commit_count' in r ? r.commit_count : (r.commits?.length ?? 0)) with r.commit_count ?? (r.commits?.length ?? 0) | File: skills/brief-portfolio/app/src/lib/derive.js:116 | Task: 2
[CARL] ⚪ Move mid-file import { aggregate } to top of file with existing imports | File: skills/brief-portfolio/app/smoke.repos.test.js:88 | Task: 2

He raised no accessibility, responsive-behaviour, contrast or focus finding
against the changed `RepoDetail` heading, and no visual-consistency finding
against the Brief headline tile.

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

## Decision gate

Convergence test: **no unresolved 🔴 Critical and no unresolved 🟠 High**, so the
cycle converges and the rework cap (`cycle 1`, `rework_cap 2`) is irrelevant.
Medium and Low findings never block convergence; they are swept, not dropped.

Nine of the ten rows are swept into one `[D1] Tail sweep` task (rows 1-8 and
10). One row is discarded with a verified reason (row 9). Each overlapping pair
was merged into a single decision:

- rows 2 + 4 → one decision (the two Python tests that pass against base, plus
  Bob's concrete strengthening: assert `c` **and** `e`, and stub
  `collect_commit_count` as a sentinel in the metadata test).
- rows 3 + 5 → one decision (the three JS fallback/boundary tests).
- rows 1 + 10 → one decision (moving the four `aggregate()` unit tests to
  `src/lib/derive.test.js` also removes the mid-file import).

**Row 9 discarded, not deferred.** Bob's `⚪ Cannot statically verify` line names
three checks: `uv run pytest -q`, `npm --prefix skills/brief-portfolio/app test`,
and a fresh app build compared against `assets/template.html`. All three were
executed **this cycle**, by three independent lenses with concurring results:
Alice (103 passed/1 xfailed, 53 passed, byte-identical rebuild), Carl (both
suites, `diff -q` match) and Blake (both suites). It is a sandbox limitation of
one lens, already answered by the panel, so it creates no task and is recorded
in the ledger so it does not return next cycle.

**Row 8 accepted** rather than rejected as over-simplification. `r.commit_count ?? (r.commits?.length ?? 0)`
preserves the documented `commit_count: 0` boundary (`0 ?? x` is `0`, and a test
pins it), diverges from the current `in`-check only for `null`/`undefined`
values that `collect_commit_count`'s `int(...)` cannot produce, and on a
hand-edited or corrupted `data.json` carrying `commit_count: null` it degrades
to the list length instead of silently contributing zero — which the project's
"never trust external data" rule prefers.

**Reconciliation recorded.** `review-work-completion` step 7 would create one
follow-up task per finding, while this gate's Tail sweep builds exactly ONE
`[D{cycle}]` task for a converged cycle's Medium/Low tail. Running both would
double-create. The sweep wins: it is the path a converged cycle takes and it is
specific to this outcome, so no per-finding `task-add` ran in step 7.

Nothing was routed to verification (no queue file this cycle, see above), and
nothing was discarded for contradicting the computed mechanical facts — no
finding made a countable claim that block covers.

Verdict: 10 findings
Tests: 3524 passed, 0 failed, 6 skipped (reused from last-verification.json at da66f97)
