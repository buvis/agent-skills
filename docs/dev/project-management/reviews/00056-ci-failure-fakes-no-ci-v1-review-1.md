---
prd: dev/local/prds/wip/00056-ci-failure-fakes-no-ci-v1.md
review: 1
date: 2026-09-21
head_sha: bea6d4caf5fa6262325e7f7d3195845df45d66d9
codex_thread_id: 01a0c297-5194-7752-a675-cf5dc294dfa9
consensus_run_id: wf_d832483c-707
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00056-ci-failure-fakes-no-ci-v1

Diff range: `5552bd16c72a206cae29e73870986657dad82934..bea6d4caf5fa6262325e7f7d3195845df45d66d9`

codex_rung_guard: not fired

pack: failed (engram: "not inside a registered repo; register it in ~/.config/gita/repos.csv"; the CSV has
26 rows and none names agent-skills, so the failure is deterministic and no retry was spent) — no pack
available this cycle. Prompts carried the `(no pack available this cycle)` sentinel for `{PACK_FILE}` and
`{PACK_FINDINGS}`. Additive retrieval context only; the review is degraded, not invalid.

Diff-scope note: this repo commits directly on `master`, so `gather-context.sh` without `--since` diffs
against `master` and produced an empty diff on the first run (0 lines). The run was repeated with
`--since <work_start_sha>` (5552bd1), giving the PRD's whole work range (3 commits, 3 files, +52/-2). The
script labels that "incremental review"; the label was corrected in the context file. This is cycle 1 and
a full review.

consensus_engine: shadow — the workflow leg ran this cycle (`consensus_run_id: wf_d832483c-707`). The
harness refused the `~/.claude/workflows/review-fanout.workflow.js` path (outside the working
directories), so the script was copied to `dev/local/tmp/review-fanout-00056-c1.workflow.js` and invoked
from there (one retry, engine class 3 avoided). The 4773-byte diff was passed in full
(`diff_truncated: false`). Shadow result in the Alice section below and in
`dev/local/tmp/00056-ci-failure-fakes-no-ci-v1-consensus-shadow-1.md` (gated with
`check_review_file.py --reviewers alice`, exit 0). Non-gating.

## Review Summary

Reviewed: 1 completed task (task 1: 51454df tests, d786ac6 fix, bea6d4c CHANGELOG). Implemented by
Claude (sonnet), lean pipeline, `self_deslop: skipped:trivial`, style gate clean.
PRDs checked: 00056-ci-failure-fakes-no-ci-v1.md

### Agent Status

- Alice: ✅ Available (Claude subagent, consensus lens; legacy leg gates; shadow workflow ran beside her)
- Blake: ✅ Available (Claude subagent, blind/PRD-only lens; no Filesystem-notes block — `dev/local` is a
  real directory and the root is not a dot-directory)
- Bob: ✅ Available (codex, first run, exit 0, ledger row de549b75 closed `ok`; thread id captured to
  `bob-thread-00056-c1.txt` and stamped above; no retry, no fallback)
- Carl: ✅ Available (gemini via `backend=copilot model=gemini-3.8-flash`, exit 0, ledger row b1cc7359
  closed `ok`; 9.83 AI credits, 1m20s; ran `uv run pytest skills/brief-portfolio/scripts -q`, the
  test file with `-vv`, and the skill validator himself)
- Eve: ⏸️ Disabled (codex doubt-roster guard not fired — the one task attempt has `implementor: "claude"`)

Watcher subagent dispatched with the CLI reviewers (loop mode), returned `DONE` on its second run. No
retries spent this cycle: no CLI failure, no format or verdict retry.

## Consolidated Findings

`consolidate_findings.py` over ALICE, BLAKE, BOB, CARL (no ledger on cycle 1). Six rows, none 🔴/🟠:
three 🟡, three ⚪. The script merged Alice's ⚪ and Bob's 🟡 KNOWN on `test_collect_repo.py:187` into one
row at the higher severity, and Bob's two "Cannot statically verify" lines (both `File: N/A`) into one.

| # | Consensus | Severity | Issue | File | Task | Found By |
|---|-----------|----------|-------|------|------|----------|
| F1 | [2/4] | 🟡 Medium | `test_a_403_on_actions_runs_still_reads_as_actions_disabled` passes against pre-change code too (mech fail-first replay), since old and new code both return `ci: []` for a 403 message; it pins the PRD-required preserved-behavior branch, not the new re-raise path, so this is informational only, not a rework item | skills/brief-portfolio/scripts/test_collect_repo.py:187 | 1 | Alice, Bob, mech-check |
| F2 | [1/4] | 🟡 Medium | FIX: Changelog claims rate-limit 403 failures now produce warnings, but the required regex still swallows every HTTP 403. Remove that claim. | CHANGELOG.md:64 | 1 | Bob |
| F3 | [1/4] | 🟡 Medium | FIX: The HTTP 404 allowlist branch has no test; removing `404` from the regex would leave both new tests passing. Add a 404 preservation case asserting `ci == []` and empty errors. | skills/brief-portfolio/scripts/test_collect_repo.py:187 | 1 | Bob |
| F4 | [1/4] | ⚪ Low | PRD 00056 task checkbox is unchecked and the PRD file is still in wip/ despite the implementation being complete and tested, which could cause downstream automation (this repo's own PRD-lifecycle rules) to treat the work as unfinished | dev/local/prds/wip/00056-ci-failure-fakes-no-ci-v1.md | general | Blake |
| F5 | [1/4] | ⚪ Low | Cannot statically verify: tests pass (VERIFY: run `uv run pytest skills/brief-portfolio/scripts -q` and `npm --prefix skills/brief-portfolio/app test`, including unchanged history and CI-wall tests); repository checks pass (VERIFY: run `uv run pytest`, `uv run python3 skills/create-skill/scripts/validate_skill.py skills/brief-portfolio`, and `braid --check`) | N/A | 1 | Bob |
| F6 | [1/4] | ⚪ Low | Cannot statically verify: end-to-end success criterion (VERIFY: repeat the one-repo HTTP 500 Actions shim reproduction; confirm `1 with warnings` and the built Work tab names the repo as "not collected this run") | N/A | 1 | Bob |

No 🔴 Critical and no 🟠 High findings. F2 and F3 are Bob's alone in the gating table, but the shadow
engine raised both independently (F2 from its requirements AND correctness dimensions, F3 from its tests
dimension), so neither is single-voice noise. The Medium/Low tail is handled by the decision gate (ledger
dismissals for the PRD-settled rows, one `[D1]` Tail sweep task for the rest), not carried into another
review cycle.

### Carry-forward and mechanical absorption

- **Carry-forward:** none. Cycle 1; no `…-checks-0.json` exists, which is normal.
- **Tautological shapes:** zero `[MECH]` lines — 13 test functions in 1 test file checked, none flagged.
- **Fail-first replay:** 2 touched tests ran against base `5552bd16`; 1 failed there (the 500 test, as the
  PRD requires), 1 passed: `test_a_403_on_actions_runs_still_reads_as_actions_disabled`. That `[MECH]`
  line names the same test file and test as F1, so `mech-check` was appended to F1's finders rather than
  adding a row. Every reviewer who addressed it (Alice, Bob, the shadow's rubric lane) reads it the same
  way: the PRD names this test as the 403 preservation control, so passing on both sides of the change is
  its purpose.
- **Mechanical facts:** `collect_ci` 14 lines, `_gh_alerts` 9, `collect_repo` 47, `main` 48; collect.py
  560 lines, test_collect_repo.py 216 lines. No countable claim in any finding contradicts the block.

### Verification-check queue

Written: `dev/local/reviews/00056-ci-failure-fakes-no-ci-v1-checks-1.json`, five entries from the doubt
lane's VERIFY items (Bob's assembled prompt carries eve.md's "Two lenses" and "Rubric verdicts" sections;
he tagged his lines FIX / KNOWN / VERIFY inline rather than as bucket sections; `source: "bob"` names the
lane that produced them, as in the 00054 and 00055 cycles). Each exact project verification command in
F5 became its own entry against F5's text:

- F5 → `uv run pytest skills/brief-portfolio/scripts -q`
- F5 → `npm --prefix skills/brief-portfolio/app test` (a real `package.json` script: `node --test ...`)
- F5 → `uv run pytest`
- F5 → `uv run python3 skills/create-skill/scripts/validate_skill.py skills/brief-portfolio`
- F5 → `braid --check`

Three of the five already ran green at this HEAD in the work phase (`last-verification.json`, the
`Tests:` line below); Alice, Blake and Carl each ran the skill suite themselves this cycle (72 passed /
4 xfailed / 0 failed, the xfails pre-existing agoge 2026-09-05 markers). The queue makes the sweep's
step 7 re-run them, which is where the routed ⚪ resolves.

Not queued (command shape), stays an ordinary finding: F6 ("repeat the one-repo HTTP 500 Actions shim
reproduction") is a procedure over an audit-results shim, not one project verification command.

### Follow-up tasks

None created here. Task creation for this converged cycle is owned by the decision gate's **Tail sweep**
(`run-autopilot/references/phase-review.md` Phase 5), which builds ONE `[D1]` task from the actionable
Medium/Low findings. Creating them here as well would double-create the same work.

## Alice

Consensus lens, implementation-aware (legacy subagent leg; gates the cycle). One ⚪ finding (F1, merged up
to 🟡 by Bob's row). All twelve consensus rules pass. Verified the new `except` mirrors `_gh_alerts`
exactly (`re` already imported at collect.py:10, signature unchanged), traced `collect_repo`'s per-key
loop at collect.py:437-451 (raised exception → `errors.append(f"ci: {e}")`, `repo["ci"]` never assigned),
confirmed the tests reuse the `collect.run` seam and assert exactly the acceptance criteria, ran
`uv run pytest skills/brief-portfolio/scripts -q` herself (72 passed / 4 xfailed / 0 failed, xfails
confirmed unrelated via `-rx`), found no other caller or doc referencing `collect_ci` / `actions/runs`,
and confirmed the diff is scoped to the three named files with the CHANGELOG bullet under
`[Unreleased] > Fixed`.

```
[ALICE] ⚪ `test_a_403_on_actions_runs_still_reads_as_actions_disabled` passes against pre-change code too (mech fail-first replay), since old and new code both return `ci: []` for a 403 message; it pins the PRD-required preserved-behavior branch, not the new re-raise path, so this is informational only, not a rework item | File: skills/brief-portfolio/scripts/test_collect_repo.py:187 | Task: 1
[ALICE] ✅ No blocking issues found
```

```
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
```

**Shadow engine observation (non-gating, `consensus_engine: shadow`, run `wf_d832483c-707`):**
`_engine: workflow — dimensions 5, raw 5, unique 5, confirmed 0, refuted 0, demoted 0, unverified 0,
diff_bytes 4773_`. Security dimension armed (the diff's `Forbidden` test message trips the
security-ish line regex); it raised nothing. Verdict `APPROVE`, zero blocking, all twelve rubric rules
pass. **No divergence from legacy Alice** on verdict or rubric. Five advisory notes: three overlap the
gating table (F2 CHANGELOG parenthetical, raised twice — requirements MEDIUM and correctness LOW — with
the concrete fix "drop 'or a rate-limit 403'"; F3 404 branch untested, tests LOW, with a parametrize
fix) and two the gating table lacks, recorded as observations only:

- LOW (quality): the `HTTP (403|404)` swallow is now duplicated verbatim between `collect_ci`
  (collect.py:154) and `_gh_alerts` (collect.py:172-175); a shared 2-line predicate would touch
  `_gh_alerts` outside this PRD's scope, and the PRD explicitly chose "mirroring `_gh_alerts`", so the
  lane itself marks deferral as a valid answer.
- LOW (tests): the 500 test asserts only `startswith("ci:")` and never pins that the original gh message
  is carried into the `ci:` entry (the sibling `test_collect_repo_records_meta_http_403_without_raising`
  asserts `str(exc) in errors[0]`); the PRD contract is "records `ci: <message>`".

The R9 rubric note observes the regex has no trailing boundary (`HTTP 4030` would match), identical to
the `_gh_alerts` pattern the PRD mandates mirroring; not a real HTTP code, not raised.

## Blake

Blind lens — PRD only, no diff, no file list, no review history. He located the code himself, read
`collect_ci` (collect.py:151-164) and `_gh_alerts` (:167-175), traced `collect_repo`'s
`except Exception` at :448-451, matched both named tests to the acceptance bullets verbatim, ran
`uv run pytest skills/brief-portfolio/scripts -q` (72 passed / 4 xfailed, the xfails pre-existing and
unrelated), confirmed `history_counts` (:371-387) is untouched and still reads `repo.get("ci", [])`,
confirmed the page side (`app/src/components/Work.svelte:31` computes `ciMissing`, :141-142 renders
"No CI runs." only when `ciRows` is empty, :159-164 the coexisting "not collected this run" line),
confirmed `re` was already imported, and diffed both commits (`git show d786ac6`, `51454df`) for scope
creep — none. One ⚪ process observation (F4). All nineteen blind rules pass.

```
[BLAKE] ⚪ PRD 00056 task checkbox is unchecked and the PRD file is still in wip/ despite the implementation being complete and tested, which could cause downstream automation (this repo's own PRD-lifecycle rules) to treat the work as unfinished | File: dev/local/prds/wip/00056-ci-failure-fakes-no-ci-v1.md | Task: general
```

```
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
```

## Bob

Consensus + doubt/de-slop lens, codex, static-only sandbox, first run. Six raw lines (two FIX, one KNOWN,
three "Cannot statically verify" VERIFY), consolidated into F1-F3, F5, F6. All five doubt rules pass.
Consensus rules: `R1: fail` (the 404 branch is untested — F3) and `R2: fail` (the 403 test passes at
base — F1, which he himself files as KNOWN: "changing that behavior merely to satisfy fail-first is
outside scope"). Alice, Carl and the shadow's rubric lane passed both; the gate settles F1 by the PRD
and the sweep closes F3, so they are re-evaluated by the sweep's own verification rather than argued
here.

```
[BOB] 🟡 FIX: Changelog claims rate-limit 403 failures now produce warnings, but the required regex still swallows every HTTP 403. Remove that claim. | File: CHANGELOG.md:64 | Task: 1
[BOB] 🟡 FIX: The HTTP 404 allowlist branch has no test; removing `404` from the regex would leave both new tests passing. Add a 404 preservation case asserting `ci == []` and empty errors. | File: skills/brief-portfolio/scripts/test_collect_repo.py:187 | Task: 1
[BOB] 🟡 KNOWN: Mechanical replay reports the new 403 test passes against pre-change code. It protects behavior explicitly preserved by the PRD; changing that behavior merely to satisfy fail-first is outside scope. | File: skills/brief-portfolio/scripts/test_collect_repo.py:187 | Task: 1
[BOB] ⚪ Cannot statically verify: tests pass (VERIFY: run `uv run pytest skills/brief-portfolio/scripts -q` and `npm --prefix skills/brief-portfolio/app test`, including unchanged history and CI-wall tests). | File: N/A | Task: 1
[BOB] ⚪ Cannot statically verify: repository checks pass (VERIFY: run `uv run pytest`, `uv run python3 skills/create-skill/scripts/validate_skill.py skills/brief-portfolio`, and `braid --check`). | File: N/A | Task: 1
[BOB] ⚪ Cannot statically verify: end-to-end success criterion (VERIFY: repeat the one-repo HTTP 500 Actions shim reproduction; confirm `1 with warnings` and the built Work tab names the repo as "not collected this run"). | File: N/A | Task: 1
```

```
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
```

## Carl

Gemini via `backend=copilot`, `model=gemini-3.8-flash`. Generalist review — the diff has no frontend
surface, and he did not invent frontend findings. He read the context, the diff, the changed regions of
collect.py (:145-185, :410-460) and test_collect_repo.py (:1-60, :150-205); ran the skill suite, the
test file with `-vv`, and the skill validator. No issues found.

```
[CARL] ✅ No issues found
```

```
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
```

Verdict: 6 findings
Tests: 3440 passed, 0 failed, 6 skipped (reused from last-verification.json at bea6d4caf5fa6262325e7f7d3195845df45d66d9)
