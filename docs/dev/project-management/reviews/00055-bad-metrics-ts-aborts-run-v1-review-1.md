---
prd: dev/local/prds/wip/00055-bad-metrics-ts-aborts-run-v1.md
review: 1
date: 2026-09-21
head_sha: 893e2df2757ecaa14b7464f91fa2ef95e4ecfd40
codex_thread_id: 01a0c254-3e25-7982-8485-524424816bbf
consensus_run_id: wf_2b0b1871-1ef
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00055-bad-metrics-ts-aborts-run-v1

Diff range: `a563e06a7fb162be60b3a67cba8be52aa46d6eab..893e2df2757ecaa14b7464f91fa2ef95e4ecfd40`

codex_rung_guard: not fired

pack: failed (engram: "not inside a registered repo; register it in ~/.config/gita/repos.csv", twice) — no
pack available this cycle. Prompts carried the `(no pack available this cycle)` sentinel for `{PACK_FILE}`
and `{PACK_FINDINGS}`. Additive retrieval context only; the review is degraded, not invalid.

Diff-scope note: this repo commits directly on `master`, so `gather-context.sh` without `--since` would diff
against `master` and produce an empty diff (established in the 00053 cycle). The run used
`--since <work_start_sha>` from the start, giving the PRD's whole work range (5 commits, 3 files, +106/-6).
The script labels that "incremental review"; the label is wrong here. This is cycle 1 and a full review.

consensus_engine: shadow — the workflow leg ran this cycle (`consensus_run_id: wf_2b0b1871-1ef`), invoked
via the `dev/local/tmp/review-fanout.workflow.js` copy (byte-identical to `~/.claude/workflows/`, verified
with `git diff --no-index`). The 7499-byte diff was passed in full (`diff_truncated: false`). Shadow result in
the Alice section below and in `dev/local/tmp/00055-bad-metrics-ts-aborts-run-v1-consensus-shadow-1.md`
(gated with `check_review_file.py --reviewers alice`, exit 0). Non-gating.

## Review Summary

Reviewed: 2 completed tasks (task 1: 1b6eb3e tests, 3f3e252 fix, 8515cb1 per-task review fix; task 2:
6fa382c tests, 893e2df fix). Both implemented by Claude (sonnet); Pat's per-task review: task 1
`medium-retry:fixed`, task 2 NO FINDINGS.
PRDs checked: 00055-bad-metrics-ts-aborts-run-v1.md

### Agent Status

- Alice: ✅ Available (Claude subagent, consensus lens; legacy leg gates; shadow workflow ran beside her)
- Blake: ✅ Available (Claude subagent, blind/PRD-only lens; no Filesystem-notes block — `dev/local` is a
  real directory and the root is not a dot-directory)
- Bob: ✅ Available (codex, first run, exit 0, ledger row fab95a0a closed `ok`; thread id captured to
  `bob-thread-00055-c1-202609210450.txt` and stamped above; no retry, no fallback)
- Carl: ✅ Available (gemini via `backend=copilot model=gemini-3.8-flash`, exit 0, ledger row 4f8219a7
  closed `ok`; 34.78 AI credits, 4m03s; ran `uv run pytest skills/brief-portfolio/scripts`, the skill
  validator, `braid --check`, `ruff check` on the three changed files, the two new reader tests and the
  new pipeline test individually, and a mixed bad/valid-row reproduction through both readers himself)
- Eve: ⏸️ Disabled (codex doubt-roster guard not fired — both task attempts have `implementor: "claude"`)

Watcher subagent dispatched with the CLI reviewers (loop mode), returned `DONE` on its third run. No
retries spent this cycle: no CLI failure, no format or verdict retry.

## Consolidated Findings

`consolidate_findings.py` over ALICE, BLAKE, BOB, CARL (no ledger on cycle 1). Five rows: one 🟠, three 🟡,
one ⚪. The script merged Alice's `CHANGELOG.md` and Bob's `CHANGELOG.md:62` citations after suffix
stripping.

| # | Consensus | Severity | Issue | File | Task | Found By |
|---|-----------|----------|-------|------|------|----------|
| F1 | [2/4] | 🟠 High | No CHANGELOG.md entry for this fix, despite the repo's binding convention (rules/changelog.md, "BLOCKING RULE... not optional") requiring one under `[Unreleased]` prefixed `**brief-portfolio**:` in the same commit as any `fix`/`feat` with a user-visible change. All 5 commits in this work range (1b6eb3e, 3f3e252, 8515cb1, 6fa382c, 893e2df) touch only collect.py/tests; CHANGELOG.md is untouched, and the existing `[Unreleased]` section has no entry describing "a bad ts row no longer aborts the run" or "skill_adherence exceptions no longer abort the run." Precedent for exactly this kind of fix exists at CHANGELOG.md:64 (a prior collect.py crash-avoidance fix that did get an entry). | CHANGELOG.md | general | Alice, Bob |
| F2 | [1/4] | 🟡 Medium | `_parse_ts("0001-01-01T00:00:00+01:00")` overflows during UTC conversion, causing both readers to discard valid metrics through their fallback handlers. Catch normalization overflow and skip that row. | skills/brief-portfolio/scripts/collect.py:275 | 1 | Bob |
| F3 | [1/4] | 🟡 Medium | Naive rejection and UTC normalization are unpinned: January’s naive fixtures lose to newer rows or fall outside the window, and every valid fixture uses UTC. | skills/brief-portfolio/scripts/test_collect_local.py:91 | 1 | Bob |
| F4 | [1/4] | 🟡 Medium | New regression tests contain redundant negative assertions and a comment paraphrasing the assertions; remove these without changing coverage. | N/A | general | Bob |
| F5 | [1/4] | ⚪ Low | Cannot statically verify: tests, skill validation, and braid checks pass at the reviewed HEAD; the context records successful execution. | N/A | general | Bob |

F1 is the cycle's one 🟠 and is why this cycle does not converge. The shadow engine's requirements and
quality dimensions raised it independently (two rows, both `verified: confirmed` by its adversarial
verifier), so it carries effectively 3-of-5 agreement. F2-F4 are Bob's alone in the gating table, but the
shadow's correctness, tests and quality dimensions each found the same defect (the overflow was confirmed
by running `_parse_ts('0001-01-01T13:59:59+14:00')`; the untested UTC normalization is its `R1: fail`; the
two dead asserts are its one MEDIUM advisory), so they are not single-voice noise.

### Carry-forward and mechanical absorption

- **Carry-forward:** none. Cycle 1; no `…-checks-0.json` exists, which is normal.
- **Tautological shapes:** zero `[MECH]` lines — 41 test functions in 2 test files checked, none flagged.
- **Fail-first replay:** 3 touched tests ran against base `a563e06a`; 3 failed there, 0 passed. Every
  new test pins this change; nothing to absorb.
- **Mechanical facts:** `_parse_ts` 14 lines, `collect_claude_skill_adherence` 34, `collect_audit_cadence`
  32, `main` 48; collect.py 555 lines. No countable claim in any finding contradicts the block.

### Verification-check queue

Written: `dev/local/reviews/00055-bad-metrics-ts-aborts-run-v1-checks-1.json`, three entries from the
doubt lane's VERIFY bucket (Bob's assembled prompt carries eve.md's FIX/VERIFY/KNOWN sections, and he
emitted the buckets; `source: "bob"` names the lane that produced them). His one VERIFY item names three
exact project verification commands, so each became its own entry against F5's text:

- F5 → `uv run pytest`
- F5 → `uv run python3 skills/create-skill/scripts/validate_skill.py skills/brief-portfolio`
- F5 → `braid --check`

All three already ran green at this HEAD in the work phase (`last-verification.json`, the `Tests:` line
below); the queue makes the rework pass's step 7 re-run them, which is where the routed ⚪ resolves.

### Follow-up tasks

Two `[D1]` tasks created via `task-add` (the routed ⚪ F5 gets none):

1. `[D1] Add the CHANGELOG [Unreleased] > Fixed entry for the 00055 brief-portfolio fixes` (S) — 🟠
   2/4 consensus — addresses F1 (task id 3)
2. `[D1] Harden _parse_ts against astimezone OverflowError, pin naive rejection and UTC normalization,
   trim redundant test material` (S) — 🟡 — addresses F2, F3, F4 (task id 4)

## Alice

Consensus lens, implementation-aware (legacy subagent leg; gates the cycle). One 🟠 finding (F1). All
twelve consensus rules pass. Verified `_parse_ts` against the PRD contract (non-string, unparseable,
naive, future → None), both readers' silent skip at collect.py:299 and :343, the `main()` wrap at :535
matching `collect_external_section`'s WARN shape, and that the front end already tolerates
`skill_adherence: null` (`app/smoke.harness.js:21`, `template.html`). Ran
`uv run pytest skills/brief-portfolio/scripts -q` herself (70 passed / 4 xfailed / 0 failed). Noted, not
flagged: `_parse_ts` re-reads the clock per row; the PRD fixes the one-argument signature, so that is as
specified.

```
[ALICE] 🟠 No CHANGELOG.md entry for this fix, despite the repo's binding convention (rules/changelog.md, "BLOCKING RULE... not optional") requiring one under `[Unreleased]` prefixed `**brief-portfolio**:` in the same commit as any `fix`/`feat` with a user-visible change. All 5 commits in this work range (1b6eb3e, 3f3e252, 8515cb1, 6fa382c, 893e2df) touch only collect.py/tests; CHANGELOG.md is untouched, and the existing `[Unreleased]` section has no entry describing "a bad ts row no longer aborts the run" or "skill_adherence exceptions no longer abort the run." Precedent for exactly this kind of fix exists at CHANGELOG.md:64 (a prior collect.py crash-avoidance fix that did get an entry). | File: CHANGELOG.md | Task: general
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

**Shadow engine observation (non-gating, `consensus_engine: shadow`, run `wf_2b0b1871-1ef`):**
`_engine: workflow — dimensions 4, raw 8, unique 8, confirmed 2, refuted 0, demoted 0, unverified 0,
diff_bytes 7499_`. Security dimension not armed (no security-ish path or line in the diff). Verdict
`CHANGES_REQUESTED` on two 🟠 rows that are the same CHANGELOG finding worded twice (requirements and
quality dimensions; the dedup key is file+evidence and their evidence strings differ), both confirmed by
Victor. Rubric: `R1: fail` (the UTC normalization added in 8515cb1 has no test: every fixture is `+00:00`,
so a `return dt` mutant passes), all others pass. **Divergence from legacy Alice:** same 🟠 verdict on the
CHANGELOG; Alice passed R1 where the shadow failed it — the gating table's F3 is the same gap and task 4
closes it. Six advisory notes: three overlap the gating table (F2 overflow, correctness, LOW, with the
concrete `except (ValueError, OverflowError)` fix; F3 UTC normalization, tests, MEDIUM; F4 dead asserts,
quality, MEDIUM) and three the gating table lacks, recorded as observations only:

- LOW (quality): the single-use `now` local in `collect_claude_skill_adherence` (collect.py:285) splits
  `cutoff = datetime.now(timezone.utc) - timedelta(days=30)` into two lines for no reader.
- LOW (quality): neither reader's docstring mentions the new `ts` filter (collect.py:319 and the adherence
  docstring's ISO-8601 line).
- MEDIUM (tests): no `main()`-level test with a bad-`ts` row under a fake home pins the PRD's own
  reproduction and its "filtering does not warn" clause end to end; the unit tests pin the readers and the
  pipeline test pins the wrap, but nothing drives `main()` over a malformed row and asserts no
  `WARN skill_adherence`.

## Blake

Blind lens — PRD only, no diff, no file list, no review history. He located the code himself, read
`_parse_ts` (collect.py:262) and both readers, confirmed the `main()` wrap at collect.py:535-539 mirrors
`collect_external_section`, matched all three named tests to the acceptance bullets (each pins the PRD's
reproduction rows), ran `uv run pytest skills/brief-portfolio/scripts -q` (70 passed / 4 xfailed, the
xfails pre-existing and unrelated), and found no new imports, flags or dependencies. From git history he
noted `parse_ts(ts, now)` was introduced and then simplified to the PRD's `_parse_ts(ts)` in a follow-up
commit. Same per-row clock note as Alice, not filed.

```
[BLAKE] ✅ No issues found
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

Consensus + doubt/de-slop lens, codex, static-only sandbox, first run. Five findings (F1-F5), all five
doubt rules pass. Consensus rules: `R1: fail` (UTC normalization and naive rejection unpinned — F3),
`R7: fail`, `R9: fail`, `R10: fail` (all three the overflow — F2: a parseable row escapes the helper as an
uncaught exception and costs the metric, contrary to the PRD's "catch parse/type failures inside the
helper"). Alice and Carl passed all four; task 4 closes both gaps, so they are re-evaluated next cycle
rather than argued here.

```
[BOB] 🟡 `_parse_ts("0001-01-01T00:00:00+01:00")` overflows during UTC conversion, causing both readers to discard valid metrics through their fallback handlers. Catch normalization overflow and skip that row. | File: skills/brief-portfolio/scripts/collect.py:275 | Task: 1
[BOB] 🟡 Naive rejection and UTC normalization are unpinned: January’s naive fixtures lose to newer rows or fall outside the window, and every valid fixture uses UTC. | File: skills/brief-portfolio/scripts/test_collect_local.py:91 | Task: 1
[BOB] 🟡 New regression tests contain redundant negative assertions and a comment paraphrasing the assertions; remove these without changing coverage. | File: N/A | Task: general
[BOB] 🟡 The user-visible timestamp filtering and failure recovery lack the required `**brief-portfolio**:` changelog entry. | File: CHANGELOG.md:62 | Task: general
[BOB] ⚪ Cannot statically verify: tests, skill validation, and braid checks pass at the reviewed HEAD; the context records successful execution. | File: N/A | Task: general
```

Buckets (verbatim):

```
FIX:

- UTC conversion overflow — skills/brief-portfolio/scripts/collect.py:275 — catch `OverflowError` inside `_parse_ts`; add a regression combining the boundary timestamp with valid rows.
- Missing temporal coverage — skills/brief-portfolio/scripts/test_collect_local.py:91 — test recent naive dates/times independently and nonzero offsets crossing UTC midnight and the 30-day cutoff.
- Redundant test material — skills/brief-portfolio/scripts/test_collect_local.py:246 and skills/brief-portfolio/scripts/test_collect_pipeline.py:292 — delete the two inequalities already implied by equality and the three-line comment repeating the test.
- Missing changelog entry — CHANGELOG.md:62 — document malformed/future timestamp filtering and continued report generation after reader failure under `[Unreleased]` → `Fixed`.

VERIFY:

- Recorded runtime checks — run `uv run pytest`, `uv run python3 skills/create-skill/scripts/validate_skill.py skills/brief-portfolio`, and `braid --check` at the reviewed HEAD.

KNOWN:

- (none)
```

```
R1: fail
R2: pass
R3: pass
R4: pass
R6: pass
R7: fail
R8: pass
R9: fail
R10: fail
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
surface, and he did not invent frontend findings. He read the context, the diff, the PRD, the changed
regions of collect.py and both test files, and CHANGELOG.md; ran the skill suite, the validator,
`braid --check`, `ruff check` on the changed files, the three new tests individually, and a scratch
reproduction feeding mixed bad and valid rows through both readers. He also checked `fromisoformat`'s
handling of a trailing `Z` under the project interpreter. No issues found. (He read CHANGELOG.md and ran
`scripts/check_changelog_skills.py` without raising F1; Alice and Bob did.)

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

Verdict: 5 findings
Tests: 3438 passed, 0 failed, 6 skipped (reused from last-verification.json at 893e2df2757ecaa14b7464f91fa2ef95e4ecfd40)
