---
prd: docs/dev/project-management/prds/wip/00070-purge-trash-first-guarantee-v1.md
review: 1
date: 2026-10-18
head_sha: ac61b83e6f847c370f7b7b919b8106cdc9f22567
codex_thread_id: 01a1500c-fbdc-78b2-9808-82752e0e21b7
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
dispatch_rows:
  bob: d80411da
  carl: c87fa68d
---

# Review: 00070-purge-trash-first-guarantee-v1

Diff range: `71492a8941adc13be77b512ab51d27c94a3680ef..ac61b83e6f847c370f7b7b919b8106cdc9f22567`

codex_rung_guard: not fired

Context pack: failed (`engram pack` exit 1: not inside a registered repo). Degraded, not invalid — the
prompts carried the `(no pack available this cycle)` sentinel for `{PACK_FILE}` and `{PACK_FINDINGS}`.

Staging errors: none.

## Review Summary

Reviewed: 1 completed task (`Add keep guard to empty_old_trash so a run never deletes the batch it just trashed`, opus tier, implementor claude)
PRDs checked: 00070-purge-trash-first-guarantee-v1

### Agent Status

- Alice: ✅ Available (consensus lens, engine `legacy`)
- Blake: ✅ Available (blind lens, PRD-only)
- Bob: ✅ Available (doubt + de-slop lens, codex) — after one retry (inlined)
- Carl: ✅ Available (UI/design lens, gemini via copilot backend)
- Eve: ⏸️ Disabled (`doubt_reviewer: codex`, codex doubt-roster guard not fired)

Bob's first run was a lack-of-input refusal (all three retry-policy conditions held: no
`R{n}: pass` line, no severity-bearing `[BOB]` issue line, one `[BOB] ⚪ Cannot statically verify`
line). The single retry budget was spent on the inlined retry prompt
(`docs/dev/tmp/bob-prompt-00070-c1-retry.md`, 59 KB), which produced a usable review.

### Mechanical checks

- Tautological test shapes: 29 test functions checked in 2 files, no `[MECH]` lines.
- Fail-first replay: 2 touched tests ran against base `71492a8941ad`, **2 failed against base, 0
  passed**. Neither new test is tautological.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [2/4] | 🟡 | Simplification: `test_empty_trash_ages_out_old_batches_only` is 34 lines. It uses nested `seed` and `present` closures and a shared `names` dict that mutates across three seeding rounds. The PRD asked for a plain three-batch case (40, 2 and 0 days, expecting a return of 1). The extra boundary matrix (45/35/31/29/3 days) is behavior-preserving extra coverage, but it makes the test harder to read. Consider splitting the first three-batch case from the boundary sweep into two tests. | skills/purge-devtmp/scripts/test_purge_devtmp.py:126 | 1 | ALICE, BLAKE |
| R2 | [1/4] | 🟡 | Scope creep: the diff carries a formatter-style rewrite of glean.py and test_glean.py (82 and 64 changed lines). It has nothing to do with PRD 00070: `re.I` becomes `re.IGNORECASE`, trailing commas are added, and calls are re-wrapped. These are the pre-existing uncommitted edits that `git status` shows and the project capsule says were "left untouched". They should be committed or reverted separately, not under the purge-devtmp task. | skills/glean/scripts/glean.py:37 | 1 | ALICE |
| R3 | [1/4] | 🟡 | Unrelated glean formatting expands `cmd_scan` to 54 lines, exceeding the 50-line limit. Restore its previous formatting and omit unrelated glean formatting changes. | skills/glean/scripts/glean.py:191 | general | BOB |
| R4 | [1/4] | ⚪ | The new `empty_old_trash` signature line is 91 characters. The reformatted glean.py in this same diff wraps at 88, so the repo style is inconsistent. This is cosmetic. | skills/purge-devtmp/scripts/purge_devtmp.py:143 | 1 | ALICE |
| R5 | [1/4] | ⚪ | The last assertion of the test (days=0 with keep=today's batch, return 0) is the only direct unit pin of "keep spares an expired batch" for `empty_old_trash`. It is buried at the end of a long sequence. A short dedicated test, or a comment naming it, would make that intent explicit. | skills/purge-devtmp/scripts/test_purge_devtmp.py:157 | 1 | ALICE |
| R6 | [1/4] | ⚪ | Implementation matches the spec. `empty_old_trash(store, now, days, keep=None)` skips `batch.name == keep` at the top of its loop, so the kept batch is skipped whatever its age. `process_store` passes `keep=batch`, and the signature of `process_store` is unchanged. | skills/purge-devtmp/scripts/purge_devtmp.py:150 | 1 | BLAKE |
| R7 | [1/4] | ⚪ | I could not re-run the fail-first claim against the old code. Git history shows the test commit cf78053 landed before the fix commit b8318eb, which is consistent with the zero-day test failing first. A CHANGELOG entry was added in 530affd. `uv run pytest skills/purge-devtmp/scripts -q` gives 10 passed, 0 failed, with 2 unrelated pytest tmpdir cleanup warnings. | N/A | 1 | BLAKE |
| R8 | [1/4] | ⚪ | The kept batch is spared by exact name match only. Under `--empty-trash-days 0`, yesterday's batch is still deleted. That is the intended window semantics, not a defect. | skills/purge-devtmp/scripts/purge_devtmp.py:156 | general | BLAKE |

**Consolidator note (merge warning).** `consolidate_findings.py` reported:
`row 1 merged citations that matched only after suffix stripping:
test_purge_devtmp.py:126 ~ :107 ~ :125`. R1 therefore shows `[2/4] ALICE, BLAKE`, but Blake's two
lines at `:107` and `:125` were **approvals** ("extra coverage, not scope creep"), not restatements
of Alice's readability finding. R1's real support is 1/4. The table is left exactly as the script
emitted it; this note is the correction rather than a hand-edit.

No CRITICAL (🔴) and no HIGH (🟠) finding was raised by any lens.

## Alice

Consensus lens, `consensus_engine: legacy`, single Task subagent. Findings R1, R2, R4, R5 above.

Checks she ran:
- `uv run pytest skills/purge-devtmp/scripts -q` → 10 passed, 0 failed, 0 skipped.
- Confirmed the fail-first replay block shows both new tests fail against base.
- Confirmed `keep` defaults to `None`, is matched by name regardless of age, and that
  `process_store` passes `keep=batch`; the test's `now` and the batch name are consistent, so the
  test cannot flake at midnight.
- Confirmed `empty_old_trash` has no other callers, and that the CHANGELOG entry is present.
- Did not run the full suite.

Verdicts: R1 pass, R2 pass, R3 pass, R4 pass, R6 pass, R7 pass, R8 pass, R9 pass, R10 pass,
R11 pass, R12 pass, R13 pass.

## Blake

Blind lens — PRD only, no diff, no file list, no history. He located the code himself. No
Filesystem-notes block was added (the project root is not a dot-directory and
`docs/dev/project-management` is not a symlink). Findings R6, R7, R8 above, plus the two approval
lines that the consolidator folded into R1.

His summary: the implementation matches the spec; the tests exceed the spec's acceptance text with
additive coverage; `uv run pytest skills/purge-devtmp/scripts -q` gives 10 passed, 0 failed.

Verdicts: B1 pass, B2 pass, B3 pass, B4 pass, B5 pass, B6 pass, B7 pass, B8 pass, B9 pass,
B10 pass, B11 pass, B12 pass, B13 pass, B14 pass, B15 pass, B16 pass, B17 pass, B18 pass,
B19 pass.

## Bob

Doubt + de-slop lens (codex), after one retry (inlined). Finding R3 above.

```
FIX:
- Unrelated formatting introduces a function-size violation — skills/glean/scripts/glean.py:191 — Restore the previous formatting in both glean files.
VERIFY:
- (none)
KNOWN:
- (none)
```

Verdicts: R1 pass, R2 pass, R3 pass, R4 pass, R6 pass, R7 pass, R8 pass, R9 pass, R10 pass,
R11 pass, R12 fail, R13 pass.

Doubt-rubric verdicts: D1 pass, D2 pass, D3 pass, D4 pass, D5 pass.

R12 (`Function sizes respect the 50-line limit`) fails only on `skills/glean/scripts/glean.py`,
which is outside this PRD's change set — the same uncommitted drift Alice flagged as R2.

## Carl

UI/design lens (gemini). `[CARL] ✅ No issues found`.

He read the context and the full diff, ran `uv run pytest skills/purge-devtmp/scripts -q`,
`git status --short`, `git log -n 5 --oneline`, `git diff <base>..HEAD --stat`, the two changed
source files, an `empty_old_trash` search across the repo,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/purge-devtmp`, and
`uv run braid --check`.

Verdicts: R1 pass, R2 pass, R3 pass, R4 pass, R6 pass, R7 pass, R8 pass, R9 pass, R10 pass,
R11 pass, R12 pass, R13 pass.

## Verification-check queue

None. The doubt lens's VERIFY bucket was `- (none)`, so no
`00070-purge-trash-first-guarantee-v1-checks-1.json` was written.

Verdict: 8 findings
Tests: 3940 passed, 0 failed, 9 skipped (suite run this cycle)
