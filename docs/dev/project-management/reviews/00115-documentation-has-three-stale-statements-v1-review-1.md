---
prd: docs/dev/project-management/prds/wip/00115-documentation-has-three-stale-statements-v1.md
review: 1
date: 2026-10-29
head_sha: 66173402ae768ce00ad29111b9be7f3bc54a618b
codex_thread_id: 01a18818-5c33-7772-ada9-c59ae018be7f
reviewers: alice,blake,bob
agents:
  alice: available
  blake: available
  bob: available
  carl: unavailable
dispatch_rows:
  bob: a605f943
  carl: 91424d2f
---

# Review: 00115-documentation-has-three-stale-statements-v1

Diff range: `6f6290efff73f8e5ed2006065d6cd47514a06690..66173402ae768ce00ad29111b9be7f3bc54a618b`

codex_rung_guard: not fired

## Review Summary

Reviewed: 1 completed task
PRDs checked: 00115-documentation-has-three-stale-statements-v1

The PRD is documentation-only: one CI comment, one model-registry comment, and one
README policy row. Work commit `9997d92` touches exactly those three files
(3 insertions, 2 deletions). The rest of the diff range is pipeline bookkeeping
(metrics jsonl, the PRD rename into `wip/`, and the per-PRD `meta/assumptions.md`
rewrite), which is outside the PRD's scope.

### Agent Status

- Alice: ✅ Available
- Blake: ✅ Available
- Bob: ✅ Available
- Carl: ⚠️ Unavailable: gemini-run exit 1, backend=copilot model=gemini-3.8-flash,
  "You have exceeded your monthly quota". A one-off runtime failure, not exit 4, so
  Carl is not latched unavailable for the batch. No output file was published.
- Eve: ⏸️ Disabled: resolved doubt reviewer is `codex` and no task carries a codex
  implementor, so the codex doubt-roster guard did not fire.

pack: ok

### Premises re-verified by the orchestrator

The PRD requires each premise re-checked at execution time. All three hold:

- `rg --files -g 'skills/*/scripts/test_*.sh'` lists 6 suites across 5 skills
  (use-codex, use-sonnet, use-qwen x2, use-gemini, review-deps-prs). The corrected
  comment "Five skills ship six bash suites" is accurate.
- `skills/use-qwen/scripts/default-model.txt:4` holds
  `unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL`, the model whose registry comment the diff
  corrects, so the model is in fact the shipped default and removing the
  "not yet promoted" claim is correct.
- `.braidignore` lines 26-29 list `use-codex`, `use-gemini` and `use-sonnet` under
  `# autopilot`, matching the new README row. There is exactly one autopilot row.

## Consolidated Findings

| Ref | Consensus | Severity | Issue | File | Task | Found By |
|-----|-----------|----------|-------|------|------|----------|
| R1 | [1/3] | 🟡 | The test gate reports the full suite exited 1 with no summary line, so the exit criterion "`uv run pytest` passes" is not confirmed. A comment-and-README diff cannot plausibly cause a failure, so the cause is probably pre-existing or environmental. I did not run `braid --check` or the full pytest suite. | N/A | Phase 0 | BLAKE |
| R2 | [1/3] | 🟡 | README calls the three helper skills “single-file,” although the supplied inventory identifies their scripts and shell suites. Replace “three single-file helper skills” with “three helper skills.” | README.md:297 | 1 | BOB |
| R3 | [1/3] | ⚪ | All three statements verified against current sources. CI comment now reads "Five skills ship six bash suites"; `rg --files -g "test_*.sh"` lists 6 suites across 5 skills (use-codex, use-sonnet, review-deps-prs, use-gemini, use-qwen x2). | .github/workflows/ci.yml:122 | Phase 0 | BLAKE |
| R4 | [1/3] | ⚪ | Qwen comment now says "Promoted to default - see default-model.txt". This matches skills/use-qwen/scripts/default-model.txt:4, which holds unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL, the model the comment describes. Only the comment line changed; the model entry at line 34 is untouched. | skills/use-qwen/scripts/approved-models.txt:24 | Phase 0 | BLAKE |
| R5 | [1/3] | ⚪ | The README has exactly one autopilot row, and it is consistent with .braidignore. The row says most skills are documentation copies in docs/plugin-skills/. That is true: design-solution, plan-tasks, work, review-plan, review-work-completion, review-blindly and run-autopilot all exist there. It says use-codex, use-gemini and use-sonnet are standalone compatibility copies skipped via .braidignore. That is true: .braidignore lines 26-29 list them under "# autopilot". | README.md:297 | Phase 0 | BLAKE |
| R6 | [1/3] | ⚪ | The diff (commit 9997d92) touches three files with 3 insertions and 2 deletions. It changes only a CI comment, a model-file comment and one README row. No workflow steps, approved-model records or .braidignore entries changed. The working tree has only unrelated autopilot metrics files modified. `python3 scripts/check_changelog_skills.py` ran with no output and no error. `validate_skill.py skills/use-qwen` reports valid. | N/A | Phase 0 | BLAKE |
| R7 | [1/3] | ⚪ | The README row names `~/.agents/skills` as the home of the standalone copies, while the repo source is skills/. This is the established installed-path convention and does not conflict with the row above it. Cosmetic only. | README.md:297 | Phase 0 | BLAKE |
| R8 | [1/3] | ⚪ | The required pytest gate remains unsuccessful: 1 failed, 4144 passed, 9 skipped. The supplied results identify an unrelated timing-sensitive deadline assertion; repairing it is outside this documentation task. | skills/sweep-fix/scripts/test_sweep_scan.py:511 | 1 | BOB |

Every row was raised by exactly one of the three reviewers. No CRITICAL and no
HIGH was raised by any lens.
Rows R3-R7 are Blake's all-clear confirmations, which the consolidator parses as
rows because they use the issue-line shape; they report no defect.

## Alice

[ALICE] ✅ No issues found

Checked against current sources: the CI comment matches the 6-suite/5-skill
inventory; `default-model.txt` names the model whose registry comment changed, and
the model id lines are untouched; the README row's claims about
`docs/plugin-skills/` and `.braidignore` are both true and there is no duplicate
row. Alice re-ran the full suite independently at this HEAD: **4145 passed, 9
skipped, 0 failed** — the staged gate's "exit 1, counts unavailable" does not
reproduce. She did not run `braid --check`, `check_changelog_skills.py` or the
`validate_skill.py` run. The remaining diff entries are pipeline bookkeeping and
out of the PRD's scope. No test functions changed, so the tautology and fail-first
checks do not apply.

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

Blake found all three statements correct against the current sources and confirmed
the diff changes only comments and one README row, with no workflow step,
approved-model record or `.braidignore` entry touched. He ran
`check_changelog_skills.py` (clean) and `validate_skill.py skills/use-qwen`
(valid). His one 🟡 (R1) is that the staged test-gate line left `uv run pytest`
unconfirmed; he explicitly did not run the suite himself. His full findings are
rows R1 and R3-R7 above.

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

FIX:
- [BOB] 🟡 README calls the three helper skills “single-file,” although the supplied inventory identifies their scripts and shell suites. Replace “three single-file helper skills” with “three helper skills.” | File: README.md:297 | Task: 1

VERIFY:
- (none)

KNOWN:
- [BOB] ⚪ The required pytest gate remains unsuccessful: 1 failed, 4144 passed, 9 skipped. The supplied results identify an unrelated timing-sensitive deadline assertion; repairing it is outside this documentation task. | File: skills/sweep-fix/scripts/test_sweep_scan.py:511 | Task: 1

R1: pass
R2: pass
R3: pass
R4: pass
R6: pass
R7: pass
R8: pass
R9: fail
R10: pass
R11: pass
R12: pass
R13: pass

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

Bob's VERIFY bucket is empty, so no verification-check queue was written for this
cycle.

## Test gate note

The `review-stage` gate run at this HEAD reported `1 failed, 4144 passed, 9
skipped` (log `docs/dev/tmp/gate-00115-c1.log`). The single failure is
`skills/sweep-fix/scripts/test_sweep_scan.py:511`, a timing-sensitive assertion
that a 0.3s sweep deadline expires for exactly one of three repos; under the load
of four concurrent reviewers it expired for all three. Alice's independent rerun at
the same HEAD passed clean (4145 passed, 0 failed), so the failure is a load-
sensitive flake, not a defect this diff introduced. It is recorded here rather than
left to read as green; the flake itself is out of this docs-only PRD's scope.

## Follow-up Tasks Created

None. Every finding is single-voice Medium or Low, which the decision gate discards
rather than turning into a task; all eight are recorded in
`00115-documentation-has-three-stale-statements-v1-ledger.json` with the reason each
was settled.

Verdict: 8 findings
Tests: none (docs-only)
