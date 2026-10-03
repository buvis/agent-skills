---
prd: dev/local/prds/wip/00055-bad-metrics-ts-aborts-run-v1.md
review: 2
date: 2026-09-21
head_sha: 5552bd16c72a206cae29e73870986657dad82934
codex_thread_id: 01a0c254-3e25-7982-8485-524424816bbf
consensus_run_id: wf_b445aa5c-9a1
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00055-bad-metrics-ts-aborts-run-v1

Diff range: `893e2df2757ecaa14b7464f91fa2ef95e4ecfd40..5552bd16c72a206cae29e73870986657dad82934`

codex_rung_guard: not fired

pack: failed (engram: "not inside a registered repo; register it in ~/.config/gita/repos.csv", twice, same
as cycle 1) — no pack available this cycle. Prompts carried the `(no pack available this cycle)` sentinel for
`{PACK_FILE}` and `{PACK_FINDINGS}`. Additive retrieval context only; the review is degraded, not invalid.

Scope: **incremental review** (cycle 2) of the cycle-1 rework — `--since 893e2df` (cycle 1's `head_sha`),
three commits, 4 files, +24/-6: 8edf35c (task 3, CHANGELOG entry), 7827ed0 (task 4 tests), 5552bd1 (task 4
fix). Every reviewer was asked to verify the five cycle-1 findings resolved and to review the scoped diff for
regressions. Bob resumed his cycle-1 codex thread (`--resume-thread`; the sidecar re-emitted the same id).

consensus_engine: shadow — the workflow leg ran this cycle (`consensus_run_id: wf_b445aa5c-9a1`), invoked via
the `dev/local/tmp/review-fanout.workflow.js` copy (byte-identical to `~/.claude/workflows/`, re-verified with
`git diff --no-index`). The 5452-byte diff was passed in full (`diff_truncated: false`). Shadow result in the
Alice section below and in `dev/local/tmp/00055-bad-metrics-ts-aborts-run-v1-consensus-shadow-2.md` (gated
with `check_review_file.py --reviewers alice`, exit 0). Non-gating.

## Review Summary

Reviewed: 4 completed tasks — tasks 1-2 (cycle 1, unchanged since), tasks 3-4 (the cycle-1 rework, this
cycle's diff). Task 3 docs-only via the micro lane (8edf35c); task 4 tests-first (7827ed0 red-check: red) then
fix (5552bd1), Pat: NO FINDINGS, 3 closures resolved.
PRDs checked: 00055-bad-metrics-ts-aborts-run-v1.md

### Agent Status

- Alice: ✅ Available (Claude subagent, consensus lens; legacy leg gates; shadow workflow ran beside her)
- Blake: ✅ Available (Claude subagent, blind/PRD-only lens; no Filesystem-notes block — `dev/local` is a real
  directory and the root is not a dot-directory)
- Bob: ✅ Available (codex, first run, exit 0, ledger row 5b5d4afe closed `ok`; resumed thread
  01a0c254-3e25-7982-8485-524424816bbf; gateguard blocked his first two `cat` calls, he re-read after
  presenting the facts; no retry, no fallback)
- Carl: ✅ Available (gemini via `backend=copilot model=gemini-3.8-flash`, exit 0, ledger row 4d88eb32
  closed `ok`; reproduced the year-0001 overflow himself, ran the skill suite, the validator, and the scoped
  `git diff` range)
- Eve: ⏸️ Disabled (codex doubt-roster guard not fired — every task attempt has `implementor: "claude"` or
  `"orchestrator"`)

Watcher subagent dispatched with the CLI reviewers (loop mode), returned `DONE` on its second run. No
retries spent this cycle.

## Consolidated Findings

`consolidate_findings.py` over ALICE, BLAKE, BOB, CARL: `✅ No issues found - all agents passed` — zero
reviewer findings. No ledger existed before this cycle, so no `--ledger` flags and no auto-dismissed section.
The two rows below were added by the carry-forward and mechanical absorption steps, not by any reviewer.

| # | Consensus | Severity | Issue | File | Task | Found By |
|---|-----------|----------|-------|------|------|----------|
| F1 | [1/4] | ⚪ Low | Queued check did not pass: `braid --check` -> exit 127 (checks-1.json entry carried forward from cycle-1 F5 "Cannot statically verify: tests, skill validation, and braid checks pass at the reviewed HEAD"). | N/A | general | verify-check |
| F2 | [1/4] | 🟡 Medium | 1 touched test(s) pass against the pre-change code: test_a_raising_skill_adherence_reader_costs_one_metric_not_the_run | skills/brief-portfolio/scripts/test_collect_pipeline.py | general | mech-check |

No 🔴 or 🟠. Every cycle-1 finding (F1 CHANGELOG, F2 overflow, F3 unpinned normalization, F4 redundant
material, F5 verification) was verified resolved by Alice explicitly and by Bob (all R and D rules pass, empty
FIX/VERIFY/KNOWN buckets on his resumed thread) and Carl (all R rules pass); Blake, blind, confirmed the
CHANGELOG entry and the overflow catch from the code alone. Bob's cycle-1 `R1/R7/R9/R10: fail` are all
`pass` this cycle.

### Carry-forward and mechanical absorption

- **Carry-forward** (`checks-1.json`, 3 entries): `uv run pytest` exit 0, the skill validator exit 0,
  `braid --check` exit 127 → F1 above. The 127 is `command not found`: `braid` is not on the headless shell's
  PATH (re-confirmed this session). The same check by absolute path, `/Users/bob/.agents/bin/braid --check`,
  exited 0 at this HEAD in the work phase (`last-verification.json`) and again this session:
  `0 linked, 76 current, 20 ignored, 0 removed, 0 backed up, 0 drift`.
- **Tautological shapes:** zero `[MECH]` lines — 41 test functions in 2 test files checked.
- **Fail-first replay** against base `893e2df`: 3 touched tests ran, 2 failed at base, 1 passed → F2 above.
  The one that passed is the test whose only change in this diff is the deletion of a three-line comment
  (cycle-1 F4); its behavior was pinned in cycle 1 (failed against `a563e06a`).
- **Mechanical facts:** `_parse_ts` 17 lines, `collect_claude_skill_adherence` 34, `collect_audit_cadence`
  32, `main` 48; collect.py 558 lines. No countable claim contradicts the block.

### Verification-check queue

Not written this cycle: Bob's VERIFY bucket is `(none)`, so `checks-2.json` has no entries.

### Follow-up tasks

None created. Both table rows are gate discards with verified reasons (F1: PATH artifact, absolute-path run
0 drift; F2: comment-only edit, behavior pinned in cycle 1) and were recorded in
`dev/local/reviews/00055-bad-metrics-ts-aborts-run-v1-ledger.json`. A task for either would re-run a check
that already passed or "fix" a test that changed no assertion.

## Alice

Consensus lens, implementation-aware (legacy subagent leg; gates the cycle). No findings; all twelve rules
pass. Verified each cycle-1 finding resolved at its line: F1 at CHANGELOG.md:64 (8edf35c, `CHANGELOG.md | 1 +`
via `git show --stat`); F2 at collect.py:275-278 (confirmed the pre-fix `astimezone` raises
`OverflowError: date value out of range` for `0001-01-01T00:00:00+01:00` and the new code catches it); F3 at
test_collect_local.py:94-100 (in-window naive adherence row, `count == 1` kept) and :247-264 (offset row →
`2026-08-14`, newer-naive-vs-older-aware pair → `2026-08-01`); F4 at test_collect_local.py:263-264 and
test_collect_pipeline.py:290-294. Re-ran `uv run pytest skills/brief-portfolio/scripts -q`: 70 passed, 4
xfailed (pre-existing strict xfails, unrelated), 0 failed. No regressions in the scoped diff.

```
[ALICE] ✅ No issues found
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

**Shadow engine observation (non-gating, `consensus_engine: shadow`, run `wf_b445aa5c-9a1`):**
`_engine: workflow — dimensions 5, raw 1, unique 1, confirmed 0, refuted 0, demoted 0, unverified 0,
diff_bytes 5452_`. Security dimension armed this cycle (5 dimensions vs 4 in cycle 1; the CHANGELOG hunk's
neighbouring `use-qwen` lines mention refusals and traversal, which trips the path/line trigger) and returned
nothing. Verdict `APPROVE`, all twelve R rules pass with notes — R2's note reaches the same reading of the
replay row as the ledger entry ("the one test passing at base is a comment-only edit"). **No divergence from
legacy Alice.** One MEDIUM advisory from the quality dimension, recorded as an observation only:

- `_parse_ts` (collect.py:275) now carries two adjacent `try/except` blocks that both `return None`; the
  behavior-preserving fold is one `try` around parse, tz/future check and `astimezone` with
  `except (ValueError, OverflowError): return None` — which is also the shape task 4's contract named. The
  implementor chose the narrower nested catch; the shadow's own R9 note confirms it is sufficient (`dt > now`
  does not raise for the overflow row, only `astimezone` does). Optionally add "or overflows during UTC
  normalization" to the docstring's None cases.

## Blake

Blind lens — PRD only, no diff, no file list, no review history. He located `_parse_ts` (collect.py:262) and
walked its contract case by case (non-string, unparseable, naive, future, and the `OverflowError` from
`astimezone` at :276-278), confirmed both readers route every `ts` through it and silently skip None
(collect.py:281, :321) inside their existing `is_file()`/`OSError`/`JSONDecodeError` guards, confirmed the
`main()` wrap at :538-542 mirrors `collect_external_section`, matched all three named tests to the acceptance
bullets, ran the skill suite (70 passed, 4 pre-existing xfailed, 0 failed), confirmed the folded LOW
(`derive.js` negative `daysAgo`) is fixed at the source with no `derive.js` change needed, found the
CHANGELOG.md:64 entry, and found no new dependencies, flags or endpoints in the 1b6eb3e..5552bd1 history.

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

Consensus + doubt/de-slop lens, codex, static-only sandbox, first run, resumed cycle-1 thread. No findings;
all twelve consensus rules and all five doubt rules pass; every bucket empty. His four cycle-1 `fail`
verdicts (R1 unpinned normalization; R7/R9/R10 the escaping overflow) are `pass` against the rework.

```
[BOB] ✅ No issues found
```

Buckets (verbatim):

```
FIX:

- (none)

VERIFY:

- (none)

KNOWN:

- (none)
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
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass
```

## Carl

Gemini via `backend=copilot`, `model=gemini-3.8-flash`. Generalist review — no frontend surface, no invented
frontend findings. He read the context, the diff and the changed regions of collect.py and both test files;
reproduced the year-0001 overflow in a scratch interpreter (confirmed `dt > now` is fine and only `astimezone`
raises); ran `uv run pytest skills/brief-portfolio/scripts -q` and the skill validator; and diffed the scoped
range himself. No issues found.

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

Verdict: 2 findings
Tests: 3438 passed, 0 failed, 6 skipped (reused from last-verification.json at 5552bd16c72a206cae29e73870986657dad82934)
