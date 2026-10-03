---
prd: dev/local/prds/wip/00061-meta-failure-fakes-hygiene-nags-v1.md
review: 1
date: 2026-09-26
head_sha: 0b69947bd7c93d8b8788e978490a33066cff8079
codex_thread_id: 01a0dcf4-7b8d-75b1-bc4a-d17cf5e7e4e0
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00061-meta-failure-fakes-hygiene-nags-v1

Diff range: `abfe3abde5737aa541bf240c5c84449c8414d557..0b69947bd7c93d8b8788e978490a33066cff8079`

codex_rung_guard: not fired

pack: failed (engram: "not inside a registered repo; register it in ~/.config/gita/repos.csv"; retried once, same result) — `{PACK_FILE}` and `{PACK_FINDINGS}` were substituted with `(no pack available this cycle)` in every prompt that takes them. Blake never receives a pack by design.

Scope note: `gather-context.sh` with no `--since` produced an EMPTY diff, because this repo works directly on `master` and the script's default base is `master` itself. The diff was regathered with `--since <work_start_sha>`, which makes the base `abfe3ab` — the PRD's own work-start commit, i.e. exactly the full-review range `work_start_sha..HEAD` this cycle is meant to cover. The context file therefore labels the scope "incremental review"; that label is the script's, and it is wrong here. This IS the cycle-1 full review: no prior review file exists for this PRD, no prior-cycle findings were fed to any reviewer, and the diff spans all four of the PRD's commits.

## Review Summary

Reviewed: 1 completed task
PRDs checked: 00061-meta-failure-fakes-hygiene-nags-v1

### Agent Status

- Alice: ✅ Available (Claude subagent, consensus lens)
- Blake: ✅ Available (Claude subagent, blind/PRD-only lens)
- Bob: ✅ Available (codex, doubt + de-slop lens; exit 0 on the first run, no retry needed)
- Carl: ✅ Available after one retry (gemini via copilot backend, model gemini-3.8-flash)

Carl's first dispatch exited 0 but published **no reviewer text**: the run read the
context and diff, ran the suites, and then its final response was blocked by the
backend's content filter ("The model returned no content because the response was
blocked by content filtering"), leaving no `[CARL]` issue line and no `R{n}` verdicts.
Per `references/retry-policy.md` that is an unusable output, not a completed review, so
`[RETRY] carl attempt 1/1` was dispatched; the retry produced a complete review on the
same backend/model. The attempt-1 output is retained at
`dev/local/tmp/carl-output-00061-c1-attempt1.txt`. This was a runtime/content failure,
not exit 4, so Carl is **not** latched unavailable for the batch.

## Consolidated Findings

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [1/4] | ⚪ | Cannot statically verify: [VERIFY] required checks pass; run `uv run pytest skills/brief-portfolio/scripts -q`, `uv run pytest`, `uv run python3 skills/create-skill/scripts/validate_skill.py skills/brief-portfolio`, and `braid --check` | N/A | 1 | BOB |
| [1/4] | ⚪ | Cannot statically verify: [VERIFY] reproduce `demo/broken` with fresh brush and purge stamps, build the report, and confirm no brush or purge todo is derived | N/A | 1 | BOB |

### Full Consensus (4/4)

- (none)

### Majority Consensus (>50%)

- (none)

### Minority (<=50%)

- [1/4] ⚪ Cannot statically verify: required checks pass | N/A | Found by: Bob
- [1/4] ⚪ Cannot statically verify: reproduce `demo/broken` and confirm no brush/purge todo | N/A | Found by: Bob

Both rows are Bob's sandbox-limitation lines, emitted exactly as `agents/bob.md`
mandates when a criterion needs runtime verification he cannot perform. Neither
asserts a defect. Note what they are **not**: they are not queued verification
checks. The queue is written from a doubt lens's VERIFY *bucket*, and `agents/bob.md`
defines no FIX/VERIFY/KNOWN buckets (SKILL.md step 6 reserves `source: "bob"` for the
day his persona gains one). Eve did not run this cycle — `doubt_reviewer` is `codex`
and the codex doubt-roster guard did not fire — so no bucket existed to read, and no
`00061-...-checks-1.json` was written. Both stay ordinary ⚪ Low findings.

### Auto-dismissed (ledger)

Not applicable — cycle 1, no settled-decisions ledger exists yet, so
`consolidate_findings.py` ran without `--ledger`/`--ledger-dismiss`.

## Mechanical checks (computed)

- **Tautological test shapes**: 15 test functions checked in 1 test file; **no `[MECH]` lines**. No new or changed test has a shape that cannot fail.
- **Fail-first replay** (HEAD's touched tests against `abfe3abde573`): 1 touched test ran, **1 failed against base**, 0 passed, 0 files uncollectable. The new test genuinely pins the change; it is not tautological.
- **Function/file sizes** (from `ast`): `collect_repo` 45 lines, `run_collectors` 6 lines — both under the 50-line limit. No function in the changed files exceeds it.

No finding contradicts this block, so nothing was discarded under the
contradicts-computed-facts rule.

## Alice

[ALICE] ✅ No issues found

Alice read the whole of `collect_repo`, `history_counts`, `run_collectors` and all
four moved collectors, and confirmed none of the four takes a `branch` parameter —
which is what makes "needs no default branch" true rather than asserted. She
confirmed the split comment at `skills/brief-portfolio/scripts/collect.py:435-436`,
the `history_counts` tuple edit and its explanatory comment at
`skills/brief-portfolio/scripts/collect.py:382-388`, and logic-traced both
acceptance-named unchanged tests. She ran `uv run pytest skills/brief-portfolio/scripts -q`
(95 passed, 2 pre-existing agoge xfails, 0 failed) and checked the CHANGELOG entry
placement at `CHANGELOG.md:71`.

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

[BLAKE] ✅ No issues found

Blake got the PRD only and found the code himself. Beyond confirming the reorder and
the split comment, his blind pass added the one check no other lens made: he followed
the fix through to the consumer, `skills/brief-portfolio/app/src/lib/derive.js:267`
and `:325`, and confirmed `derive.js` already reads `r.brush_last_run` /
`r.purge_last_run` straight off the repo record — so the collect-side fix alone
closes the false-nag requirement with no front-end change needed. He also verified
the diff footprint commit by commit (`8e41aea`, `159d981`, `0bb5d9a`, `0b69947`):
no unrelated files, no new dependencies, no new flags, `collect_repo()`'s signature
unchanged.

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

Doubt + de-slop lens, codex (read-only sandbox), exit 0 on the first run.

[BOB] ⚪ Cannot statically verify: [VERIFY] required checks pass; run `uv run pytest skills/brief-portfolio/scripts -q`, `uv run pytest`, `uv run python3 skills/create-skill/scripts/validate_skill.py skills/brief-portfolio`, and `braid --check` | File: N/A | Task: 1
[BOB] ⚪ Cannot statically verify: [VERIFY] reproduce `demo/broken` with fresh brush and purge stamps, build the report, and confirm no brush or purge todo is derived | File: N/A | Task: 1

Bob raised no correctness finding and no slop finding. His de-slop lens specifically
did not flag the `run_collectors` extraction as over-abstraction, which is the call
that mattered here: the helper has two real callers in the same function, and it
exists to hold `collect_repo` under the 50-line limit.

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
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

## Carl

Gemini via copilot backend, model `gemini-3.8-flash`, after one retry (see Agent Status).

[CARL] ✅ No issues found

Carl ran the widest command set of the panel: the brief-portfolio suite, the full
`uv run pytest`, `validate_skill.py skills/brief-portfolio`, `braid --check`, and
`tests/test_braid.py`; he read the changed code plus all three affected test files,
checked the four commits with `git show`, counted file lines with `wc -l`, and grepped
for `TODO|FIXME|XXX` (no matches) and for `xfail` in `test_collect_pipeline.py`
(confirming the 2 xfails are pre-existing and unrelated). The diff has no frontend
surface, so he reviewed as a generalist and invented no frontend findings.

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

## Decision gate dispositions (cycle 1)

Both findings are ⚪ Low, so neither blocks convergence. Their dispositions are
recorded in `state.autonomous_decisions`, in
`dev/local/reviews/00061-meta-failure-fakes-hygiene-nags-v1-ledger.json`, and (for the
deferral) in `state.deferred_decisions` and the batch deferred JSON.

1. **Discarded — already verified at the reviewed HEAD.** Bob's "required checks pass"
   line is his sandbox note that he could not execute, not a defect claim. All four
   named checks are green at `0b69947`: `last-verification.json` records that exact sha
   with `uv run pytest -q` exit 0 (3463 passed, 0 failed, 6 skipped),
   `validate_skill.py skills/brief-portfolio` exit 0, `braid --check` exit 0 — and Alice
   and Carl each re-ran them live this cycle. Nothing was left to run.

2. **Deferred to batch end — the named check needs a harness this repo does not contain.**
   Bob's second line asks for a `demo/broken` reproduction. `demo/broken` and the
   metadata-failing gh shim appear **nowhere** in this repo: a whole-tree `rg` finds no
   occurrence, while a `collect_purge_devlocal` control search over the same scope returns
   3 files, so the search pattern itself works. They were an ad-hoc rig in the 2026-09-05
   agoge run that raised finding 9. Running it as named would mean building two scratch
   repos, a gh shim and a full collect-and-derive pass — net-new QA scaffolding for a Low
   finding, duplicating the agoge product-QA lane the batch runs after the drain.

   **What is proven instead, and what is not.** Proven: the new test pins that all four
   local keys are set when metadata fails, and the fail-first replay shows that test fails
   against base, so the behavior is genuinely pinned; Blake confirmed
   `derive.js:267` and `:325` read `r.brush_last_run` / `r.purge_last_run` straight off the
   record, so present keys cannot render as "never". **Not proven:** the end-to-end report
   reproduction was not executed. This is deferred rather than discarded precisely so that
   unexecuted criterion stays visible at batch end instead of being reported as verified.

## Follow-up Tasks Created

None, and no tail sweep ran. After the discard and the deferral above, zero actionable
Medium/Low findings remain, which is the Tail sweep's documented skip condition (its
selection excludes discarded findings and anything already in `deferred_decisions`).
No `[D1]` task was created; `state.rework_task_ids` stays empty.

Verdict: 2 findings
Tests: 3463 passed, 0 failed, 6 skipped (reused from last-verification.json at 0b69947bd7c93d8b8788e978490a33066cff8079)
