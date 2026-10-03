---
prd: dev/local/prds/wip/00032-sweep-validates-out-late-v1.md
review: 1
date: 2026-09-07
head_sha: 19cbdf76f4eef0216328d69b25ac0fb808b014da
codex_thread_id: 01a078f3-8e63-7922-86d5-a1bac31ce21a
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00032-sweep-validates-out-late-v1

Diff range: `98f15071277b8df1a01e6eece26527758d8541e4..19cbdf76f4eef0216328d69b25ac0fb808b014da`

codex_rung_guard: not fired

pack: failed (engram: "not inside a registered repo; register it in the gita repos.csv") — `{PACK_FILE}` and
`{PACK_FINDINGS}` were substituted with `(no pack available this cycle)` for every reviewer. Not retried:
the failure is a deterministic registration error, not a transient one. The review is degraded, not invalid.

Scope note: this is the **full review** of the PRD's whole work range. This repo commits PRD work directly
to `master`, so `gather-context.sh`'s branch-base detection would have yielded an empty diff;
`--since <state.work_start_sha>` was used to pin the base, which is exactly `work_start_sha..HEAD`. The
context file's own scope label therefore reads "incremental" — that label is wrong, the range is right.
There is no prior review cycle for this PRD.

## Review Summary

Reviewed: 3 completed tasks (all `completed`, `claude` implementor at `sonnet`, one attempt each)
PRDs checked: 00032-sweep-validates-out-late-v1

### Agent Status

- Alice: ✅ Available (Claude subagent, consensus lens)
- Blake: ✅ Available (Claude subagent, blind lens — PRD-only)
- Bob: ✅ Available (codex, doubt + de-slop lens; thread `01a078f3-8e63-7922-86d5-a1bac31ce21a`)
- Carl: ✅ Available (gemini-run backend=copilot model=gemini-3.8-flash)

All four lenses ran. Eve did not: the codex doubt-roster guard did not fire (no task carries
`implementor: "codex"`; all three are `claude`), and `doubt_reviewer` resolved to `codex`.

## Consolidated Findings

Six findings, all 🟡 Medium or ⚪ Low. **No Critical, no High, from any lens.**

| Consensus | Severity | Issue | File | Task | Found By |
|-----------|----------|-------|------|------|----------|
| [1/4] | 🟡 | New regression test does not pin the fix: `test_a_refused_out_path_creates_no_report_directory` passes unchanged against the pre-reorder code (mkdir already ran after the out-path fence in the old ordering too), so it doesn't verify the PRD's actual claim (zero search subprocesses before refusal) — that claim is only pinned by the sibling test that had its xfail marker removed | skills/sweep-fix/scripts/test_sweep_main.py | 3 | ALICE, mech-check |
| [1/4] | 🟡 | Pre-existing either-or hedge assertion (`assert escaping_out in message or str(target) in message`) lets the test pass regardless of which string actually appears in stderr; not introduced by this diff but flagged by the mechanical tautology scan while reviewing this file | skills/sweep-fix/scripts/test_sweep_main.py:211 | general | ALICE, mech-check |
| [1/4] | 🟡 | FIX: The new no-directory test passes against pre-change code and does not pin the required ordering before `enumerate_repos`; stub `enumerate_repos`, assert it is never called, and retain the directory assertion | skills/sweep-fix/scripts/test_sweep_main.py:253 | 3 | BOB, mech-check |
| [1/4] | 🟡 | KNOWN: The pre-existing either-or message assertion leaves half the refusal-message contract unpinned; replacing it with separate assertions is outside this PRD, whose success criteria require this test to remain unchanged | skills/sweep-fix/scripts/test_sweep_main.py:211 | general | BOB, mech-check |
| [1/4] | 🟡 | KNOWN: The changelog entry landed in `19cbdf7`, separate from fix commit `a070b8f`, violating the same-commit convention; repairing this now requires rewriting master history outside review scope | CHANGELOG.md:51 | general | BOB |
| [1/4] | ⚪ | VERIFY: Cannot statically verify required checks passed; run `uv run pytest`, `uv run python3 skills/create-skill/scripts/validate_skill.py skills/sweep-fix`, and `braid --check` | N/A | general | BOB |

**Consolidation under-merged, recorded loudly.** `consolidate_findings.py` ran clean (exit 0, script-side,
not model-side), but it left rows 1 and 3 separate and rows 2 and 4 separate even though each pair is one
defect. Rows 1/3 name the same test but different file strings (`…test_sweep_main.py` vs
`…test_sweep_main.py:253`); rows 2/4 share the exact file string `…:211` and were still not folded. The
true consensus is therefore **2/4 for "the new test does not pin the reorder"** and **2/4 for "the `:211`
either-or hedge"**, not the 1/4 the table shows. Nothing downstream changes — both are Medium either way,
and Medium never blocks convergence — but the printed counts understate agreement and should not be quoted
as-is.

### Mechanical checks absorbed

Both `[MECH]` lines from the context file's computed blocks matched existing rows, so neither added a row;
`mech-check` was appended to the finders of every row naming the same test:

- Tautological shapes: `test_main_refuses_relative_out_that_escapes_cwd_repo_via_dotdot` hedges with `or`
  (`test_sweep_main.py:211`) → rows 2 and 4.
- Fail-first replay: `test_a_refused_out_path_creates_no_report_directory` passes against the pre-change
  code → rows 1 and 3.

Replay coverage caveat: the replay ran **1** touched test. It did not replay
`test_an_out_path_outside_the_cwd_repo_is_refused_before_any_repo_is_scanned`, whose only change was the
removal of a decorator, so the block's silence about that test is a scope limit of the tool, not evidence
about it.

### Verification-check queue

**No queue file written this cycle** (`…-checks-1.json` deliberately absent). The queue is fed from a doubt
lens's VERIFY bucket, and `source: "bob"` is reserved: `agents/bob.md` defines no FIX/VERIFY/KNOWN buckets
(this cycle's assembly appended only Eve's "Two lenses" and "Rubric verdicts" sections, per the skill's own
substitution table), and Eve did not run. Bob's ⚪ row above carries `VERIFY:` in its own text but is not a
bucket item, so nothing sources from it. An absent queue file means no checks and is never an error.

Separately, that ⚪ item is already answered: all three commands it names ran at this exact HEAD and exited
0 (see `Tests:` below and `dev/local/autopilot/last-verification.json`).

## Alice

Two findings, both 🟡. She confirmed the reorder itself is correct and located the real pin for the ordering
claim (the de-xfailed sibling test), which is what makes finding 1 an observation about test *placement*
rather than a defect in the change.

```
[ALICE] 🟡 New regression test does not pin the fix: `test_a_refused_out_path_creates_no_report_directory` passes unchanged against the pre-reorder code (mkdir already ran after the out-path fence in the old ordering too), so it doesn't verify the PRD's actual claim (zero search subprocesses before refusal) — that claim is only pinned by the sibling test that had its xfail marker removed | File: skills/sweep-fix/scripts/test_sweep_main.py | Task: 3
[ALICE] 🟡 Pre-existing either-or hedge assertion (`assert escaping_out in message or str(target) in message`) lets the test pass regardless of which string actually appears in stderr; not introduced by this diff but flagged by the mechanical tautology scan while reviewing this file | File: skills/sweep-fix/scripts/test_sweep_main.py:211 | Task: general
```

Verdicts: R1 pass, **R2 fail**, R3 pass, R4 pass, R6 pass, R7 pass, R8 pass, R9 pass, R10 pass, R11 pass,
R12 pass, R13 pass.

## Blake (blind lens — PRD only)

Clean. He located the code himself from the spec alone and confirmed every Must-have: `_resolve_report_path`
and `cwd_path` above the `try:` block, `mkdir` still after `render_report`, refusal message and
`SystemExit(1)` byte-for-byte unchanged, xfail marker gone, new test matching the spec's exact assertions,
CHANGELOG entry present.

```
[BLAKE] ✅ No issues found
```

Verdicts: B1–B19 all pass (19 of 19).

## Bob (doubt + de-slop lens, codex)

Four findings: one FIX, two KNOWN (his own out-of-scope calls), one VERIFY.

```
[BOB] 🟡 FIX: The new no-directory test passes against pre-change code and does not pin the required ordering before `enumerate_repos`; stub `enumerate_repos`, assert it is never called, and retain the directory assertion | File: skills/sweep-fix/scripts/test_sweep_main.py:253 | Task: 3
[BOB] 🟡 KNOWN: The pre-existing either-or message assertion leaves half the refusal-message contract unpinned; replacing it with separate assertions is outside this PRD, whose success criteria require this test to remain unchanged | File: skills/sweep-fix/scripts/test_sweep_main.py:211 | Task: general
[BOB] 🟡 KNOWN: The changelog entry landed in `19cbdf7`, separate from fix commit `a070b8f`, violating the same-commit convention; repairing this now requires rewriting master history outside review scope | File: CHANGELOG.md:51 | Task: general
[BOB] ⚪ VERIFY: Cannot statically verify required checks passed; run `uv run pytest`, `uv run python3 skills/create-skill/scripts/validate_skill.py skills/sweep-fix`, and `braid --check` | File: N/A | Task: general
```

Consensus verdicts: R1 **fail**, R2 **fail**, R3 pass, R4 pass, R6 pass, R7 pass, R8 pass, R9 pass, R10
pass, R11 pass, R12 pass, R13 pass.

Doubt-rubric verdicts:

```
D1: pass
D2: pass
D3: pass
D4: pass
D5: pass
```

## Carl (gemini via copilot, gemini-3.8-flash)

Clean. He executed the checks rather than reading them: `uv run pytest skills/sweep-fix/scripts -q`,
both named tests individually, `validate_skill.py skills/sweep-fix`, `braid --check`, and
`pytest -rs` for skip/xfail reporting. No frontend surface in this change, so he reviewed as a generalist
and explicitly declined to invent frontend findings.

```
[CARL] ✅ No issues found
```

Verdicts: R1 pass, R2 pass, R3 pass, R4 pass, R6 pass, R7 pass, R8 pass, R9 pass, R10 pass, R11 pass,
R12 pass, R13 pass.

## R2 disagreement, resolved

Alice and Bob failed R2 ("no new or changed test is tautological"); Blake and Carl passed the equivalent
ground. Both failures rest on one true fact — the new `test_a_refused_out_path_creates_no_report_directory`
passes against the pre-change code — and both then infer the reorder is unpinned. That inference is wrong,
and the code says so:

`test_an_out_path_outside_the_cwd_repo_is_refused_before_any_repo_is_scanned`
(`test_sweep_main.py:469-483`) monkeypatches `sweep.scan` and asserts `scans == []`. Before the reorder,
`_resolve_report_path` ran *after* `scan`, so `scan` was called and that assertion failed — which is
precisely why the test shipped as `@pytest.mark.xfail(strict=True)` and why removing the marker (task 2)
was safe only once task 1 landed. The reorder is pinned, by a test that does fail against pre-change code.

Bob's proposed fix — stub `enumerate_repos` in the new test and assert it is never called — would duplicate
that existing pin one call earlier in the same file. The new test's own job is different and was specified
verbatim by the PRD: guard the invariant that a refused run creates **no directory**, which the reorder
could plausibly have broken by moving `mkdir`. A guard for an invariant that held before and after correctly
passes on both sides; that is what a guard is. The fail-first replay block says as much itself
("a behavior-preserving refactor's tests pass by design, so weigh the PRD's intent").

## Verdict and tests

Verdict: 6 findings

Tests: 1090 passed, 0 failed, 5 skipped (reused from last-verification.json at 19cbdf76f4eef0216328d69b25ac0fb808b014da)

The reused record is the work phase's own mandatory run at this same HEAD: `uv run pytest` exit 0,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/sweep-fix` exit 0, and
`braid --check` exit 0. No suite was run inside this review cycle. Carl independently re-ran the
sweep-fix subset and the two skill checks during his review; all passed.
