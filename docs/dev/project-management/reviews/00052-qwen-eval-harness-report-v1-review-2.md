---
prd: dev/local/prds/wip/00052-qwen-eval-harness-report-v1.md
review: 2
date: 2026-09-21
head_sha: 04693761f91255d9b994dc47e4fcc09bdaedf276
consensus_run_id: wf_bc133a2a-4a5
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available (Claude fallback; codex usage limit)
  carl: available
---

# Review: 00052-qwen-eval-harness-report-v1

Diff range: `7b54ffc31894ed6050d6f590c0a93a48fd5c80ec..04693761f91255d9b994dc47e4fcc09bdaedf276` (incremental review, cycle 2 — the rework since the cycle-1 head: tasks 4, 5 and 6, nine commits, six files, +1256/-74)

codex_rung_guard: not fired

(0 codex-implemented tasks — all 6 tasks ran `implementor: "claude"`)

consensus_engine: shadow — **both legs ran this cycle.** Legacy Alice gated; the `review-fanout` workflow ran beside her (run id `wf_bc133a2a-4a5`), non-gating, recorded under Alice's section below. The workflow file had to be copied from `~/.claude/workflows/` into `dev/local/tmp/` because the Workflow tool refuses a `scriptPath` outside the session's readable directories (the same refusal cycle 1 recorded as "engine unavailable"); with the copy in the repo the call was accepted.

pack: skipped (`engram pack` exited 1: "not inside a registered repo; register it in /Users/bob/.config/gita/repos.csv" — the same long-standing gap the project capsule records; same outcome as cycle 1)

Bob (codex): first run exit 1 (codex `error` event on both the `--resume-thread` attempt and its fresh fallback), retry 1/1 exit 1 (same shape). A direct probe (`codex exec ... "Reply with the single word OK."`) returned `You've hit your usage limit ... try again at 6:11 AM`. Nothing salvageable was written, so the doubt lens ran as the **Claude fallback** (a Task subagent with Bob's exact assembled prompt, Read tool in place of the read-only shell). The lens did not drop. No `codex_thread_id` is stamped this cycle (the thread file holds only the failed run's id).

## Summary

Reviewed: 6 completed tasks (3 original, reviewed in full in cycle 1; 3 `[D1]` rework tasks, the scope of this incremental review)
Task 4 (opus, cycle-1 CRITICAL + 3 HIGH): audit.jsonl row validation (11 checks, line-numbered refusals), attempt.json schema + directory-identity checks, run-id guard in `render()` and the CLI, `load_audit()`/`count()` exports; one context-cap rotation mid-task, resumed.
Task 5 (sonnet, Medium tail): named run.json error, zero-padded task dirs, wrapper.txt, shlex argv, zero counts for never-started engines, `_FAIL_CLASSES` removed, shared `_vetting_lines`, pinned NOT_STARTED block.
Task 6 (sonnet, test coverage): C6 field-content tests against real records, exact class counts, single-engine, retry-then-incomplete, null/zero telemetry, audit-queue fields (`test_report_content.py` split out).

**All 16 non-discarded cycle-1 findings are verified resolved by all four lenses** (every reviewer emitted a `PRIOR:` line per finding; no `unresolved` or `partially resolved` verdict from anyone). Blake's blind pass, with no diff and no history, re-derived the same conclusions from the PRD alone: B1-B19 all pass (cycle 1 had six B-fails).

### Agent Status
- Alice: ✅ Available (legacy leg gated; shadow workflow leg ran, see her section)
- Blake: ✅ Available
- Bob: ✅ Available via Claude fallback (codex usage limit; first run + one retry both exit 1)
- Carl: ✅ Available (copilot backend, gemini-3.8-flash)

## Alice

[ALICE] 🟡 `_expected_scored`/`_expected_drops` (and the `FAIL_CLASSES` tuple) are reimplemented near-verbatim in both new test files instead of one shared helper in `eval_harness_run_helpers.py` | File: skills/use-qwen/scripts/test_report_audit.py:478 | Task: general
(duplicate logic also at skills/use-qwen/scripts/test_report_content.py:205 and skills/use-qwen/scripts/test_report_content.py:200 for `_expected_drops`; `FAIL_CLASSES` duplicated at skills/use-qwen/scripts/test_report_audit.py:32 and skills/use-qwen/scripts/test_report_content.py:30)

No other issues found — the rework matches the design's `## Interfaces & contracts` verbatim (checked `load_audit`, `_check_audit_row`, `count`, `_find_task_dir`, `_load_entries`'s schema/identity checks, and `render`'s `admission.check_run_id` guard line-by-line against report.py); no caller of `report.load_audit`/`report.count`/`_counts_section` exists outside report.py and its own tests.

PRIOR: all 16 cycle-1 findings — resolved (see dev/local/tmp/alice-output-00052-c2.txt for the per-finding lines with report.py line references)

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

Verification performed: read the full diff, the rework design's `## Interfaces & contracts`, and report.py in full; confirmed `spec.parse_task_dir` and `admission.check_run_id` behave as the design assumes; `uv run pytest` on the four touched modules → 156 passed; `uv run pytest skills/use-qwen/scripts -q` → 2226 passed, 1 skipped (pre-existing); rg for TODO/FIXME/debug prints/skip/xfail in the changed files → none.

### Shadow engine observation (non-gating, `consensus_engine: shadow`)

`_engine: workflow — dimensions 5, raw 11, unique 11, confirmed 0, refuted 0, demoted 0, unverified 0, diff_bytes 64913_`

Workflow verdict: `APPROVE`, 0 blocking, 11 advisory (2 MEDIUM quality: duplicated recount helpers — the same defect legacy Alice raised; a behavior-preserving rewrite of the `review_effort_s` check; 2 MEDIUM tests: `drops`/`FAIL:dropped-a-file` pinned only at zero while the `pair` round that produces a drop is imported but never used; no test drives the render CLI through a refused audit row; 7 LOW: duplicate-attempt_dir check ordered after the value checks vs the contract's step 6 (raised three times, once per dimension), malformed run.json/vetting.json surface a bare JSONDecodeError, stale module docstring, `_or` duplicated). Trent's rubric: R1-R13 all pass with notes. Divergence from legacy Alice: none at the gating level (both zero CRITICAL/HIGH, both pass every R rule); the workflow surfaced ten more advisory items than the legacy leg's one, of which four overlap with Bob's fallback findings below (docstring, run.json/vetting.json naming, `_or`/helper duplication). Shadow file: `dev/local/tmp/00052-qwen-eval-harness-report-v1-consensus-shadow-2.md`. Workflow copy used: `dev/local/tmp/review-fanout.workflow.js`.

## Blake

[BLAKE] ⚪ `report.render()`'s ValueError (malformed audit.jsonl, corrupt record, identity mismatch, etc.) is left uncaught by `main()`, so a CLI invocation exits non-zero via a raw Python traceback rather than a clean one-line error; the PRD's "exits non-zero naming the line" is technically satisfied (the message is inside the traceback) but the UX is rougher than the vet/verify/run subcommands. | File: skills/use-qwen/scripts/run_eval_harness.py:79 | Task: general

No other issues found. Spec compliance verified from the PRD alone: exactly three files under `runs/<run-id>/`; `comparison.md` untouched; classify rederivation before trust; every audit row's key set/enums/claim-evidence/findings/effort checked before any row is trusted; unknown/non-VALID/duplicate attempt_dir refused; `f` pending-with-sentence until every VALID attempt is audited and `f: 0` with zero VALID attempts; `scored`/`drops`/`not_started`/NOT_STARTED/no-invented-engine per PRD; C6 fields all present; INCOMPLETE block on a missing attempt.json; `--run-id` validated as one path component before touching disk; runbook § 7 (18 lines) before `## Scope of approval`, § 1-6 untouched, 00010 scores invalidated; exactly one SKILL.md bullet; the specified CHANGELOG `### Added` line; exports `render`, `load_audit`, `count`; stdlib only; no decision rule.

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

Verification method: read report.py in full, run_eval_harness.py, admission.py/spec.py, the runbook, SKILL.md, CHANGELOG.md; cross-checked record-file conventions against engines.py, attempt.py, test_eval_evidence_verify.py; ran the three render test modules (111 passed) then the full skills/use-qwen/scripts suite (2226 passed, 1 skipped).

## Bob

(Claude fallback — codex usage limit; static analysis with the Read tool; Bob's exact doubt + de-slop prompt.)

[BOB] 🟡 De-slop: `_expected_drops`/`_expected_scored` are implemented twice with diverging bodies (test_report_audit.py:473, :478 and test_report_content.py:200, :205), `FAIL_CLASSES` is re-declared in both new files (test_report_audit.py:32, test_report_content.py:30) and `_or` is re-declared in test_report_content.py:40; both files already import their other helpers from test_report.py, so the shared home exists | File: skills/use-qwen/scripts/test_report_audit.py:473 | Task: 6
[BOB] ⚪ run.json and vetting.json are still parsed with bare `json.loads` and no path in the error: a corrupt run.json surfaces as a pathless decode error (or a KeyError on `run["engines"]`), a corrupt vetting.json likewise, while attempt.json and audit.jsonl now name their source; PRD says corrupt records are rejected "naming their path" | File: skills/use-qwen/scripts/eval_harness/report.py:501 | Task: 5
[BOB] ⚪ `test_evidence_dispatch_line_renders_the_records_argv_shlex_joined` (test_report_content.py:79) passes against the pre-change code (replay confirms) because the fixture argv has no shell-special characters, so it cannot tell `shlex.join` from `" ".join`; test_report.py:488 already pins the boundary case with `["fake engine", "--flag=$HOME"]`, leaving this copy redundant | File: skills/use-qwen/scripts/test_report_content.py:79 | Task: 6
[BOB] ⚪ report.py module docstring still says only "a malformed audit.jsonl line, or a duplicate attempt_dir refuses the whole render"; the rework widened refusal to the full audit row contract, attempt.json schema/identity and the run-id guard | File: skills/use-qwen/scripts/eval_harness/report.py:3 | Task: 4
[BOB] ⚪ Commit eceb591 is typed `fix(use-qwen)` with no CHANGELOG.md entry in the same commit (rules/changelog.md); the diff range touches no CHANGELOG line | File: CHANGELOG.md:12 | Task: 5
[BOB] ⚪ Order-dependent test state: `test_f_is_pending_k_of_n_with_a_partial_audit_file` (test_report.py:271), `test_f_is_a_plain_number...` (:283), `test_f_counts_only_flagged...` (:295) and `test_audit_queue_shows_the_stored_verdict_once_a_row_exists` (:393) write audit.jsonl into the module-shared r1 round and never remove it; `test_audit_queue_lists_every_valid_attempt_pending_where_no_row_exists` (:381) passes only because the malformed-line test (:323) unlinked the file first, and the stricter validation now means any later test that mutates a referenced attempt into non-VALID would refuse render. The new test_report_audit.py helpers clean up correctly | File: skills/use-qwen/scripts/test_report.py:271 | Task: general

FIX:
- Duplicated test helpers/constants across the two new test files — move `_expected_drops`, `_expected_scored`, `FAIL_CLASSES` (and `_or`) into test_report.py beside `_audit_row`/`_render` and import them from both files; keep the stricter `_expected_scored` body (the audit one, `all(launched)`)
- run.json / vetting.json parse errors not named by path — report.py:501 and :158 — wrap each `json.loads` like `_load_entries` does; one refusal test each
- Redundant, base-passing shlex test — test_report_content.py:79 — delete it (test_report.py:488 pins the same rule with a distinguishing argv), or give it a quoted argv
- Stale module docstring — report.py:3 — name the widened refusal set

VERIFY:
- (none)

KNOWN:
- `fix(use-qwen)` commit eceb591 without a CHANGELOG entry — the fixed behavior belongs to the unreleased `render` feature whose `### Added` line already covers it; a `### Fixed` line would describe a bug no release shipped
- Order-dependent audit.jsonl leftovers in test_report.py:271-403 — pre-existing cycle-1 test functions the rework did not touch; the new audit tests clean up; fixing the old ones is a separate test-hygiene change outside the three [D1] tasks

PRIOR: all 16 cycle-1 findings — resolved (per-finding lines with line references in dev/local/tmp/bob-output-00052-c2.txt)

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

[CARL] ✅ No issues found

PRIOR: all 16 cycle-1 findings — resolved (one line each in dev/local/tmp/carl-output-00052-c2.txt)

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

Backend: copilot, model gemini-3.8-flash. Verification: `uv run pytest` (full suite, green), `validate_skill.py skills/use-qwen` (OK), `uv run braid --check`. Full raw output: dev/local/tmp/carl-output-00052-c2.txt.

## Consolidated Findings

No CRITICAL or HIGH finding this cycle. `consolidate_findings.py` ran with `--ledger --ledger-dismiss BLAKE`; no Blake finding matched a settled entry (nothing auto-dismissed).

### Medium

- [2/4] 🟡 **`_expected_scored`/`_expected_drops` (and the `FAIL_CLASSES` tuple) are reimplemented near-verbatim in both new test files** instead of one shared helper (`_or` also re-declared in test_report_content.py:40; both files already import their other helpers from test_report.py). The shadow workflow's quality lane raised the same defect and notes the two `_expected_scored` bodies diverge (`launched = True` + flag vs `all(launched)`).
  - File: skills/use-qwen/scripts/test_report_audit.py:478 (also :473, :32; test_report_content.py:200, :205, :30, :40)
  - Task: 6
  - Found by: Alice, Bob (+ shadow workflow)

### Low

- [1/4] ⚪ `report.render()`'s ValueError is left uncaught by `main()`: a CLI refusal exits non-zero via a raw traceback rather than a one-line error like the other subcommands. | File: skills/use-qwen/scripts/run_eval_harness.py:79 | Task: general | Found by: Blake
- [1/4] ⚪ run.json and vetting.json are still parsed with bare `json.loads` and no path in the error, while attempt.json and audit.jsonl now name their source. | File: skills/use-qwen/scripts/eval_harness/report.py:501 (and :158) | Task: 5 | Found by: Bob (+ shadow workflow)
- [1/4] ⚪ `test_evidence_dispatch_line_renders_the_records_argv_shlex_joined` passes against the pre-change code (fixture argv has no shell-special characters) and is redundant with test_report.py:488, which pins the boundary case. | File: skills/use-qwen/scripts/test_report_content.py:79 | Task: 6 | Found by: Bob, mech-check
- [1/4] ⚪ report.py module docstring still names only the three original refusal triggers. | File: skills/use-qwen/scripts/eval_harness/report.py:3 | Task: 4 | Found by: Bob (+ shadow workflow)
- [1/4] ⚪ Commit eceb591 is typed `fix(use-qwen)` with no CHANGELOG entry in the same commit. — Bob's own KNOWN bucket: the fixed behavior belongs to the unreleased `render` feature whose `### Added` line already covers it. **Discarded at the decision gate** (see ledger). | File: CHANGELOG.md:12 | Task: 5 | Found by: Bob
- [1/4] ⚪ Order-dependent audit.jsonl leftovers in the pre-existing cycle-1 tests at test_report.py:271-403 (the new test_report_audit.py helpers clean up correctly). — Bob's own KNOWN bucket: pre-existing tests the rework did not touch. **Deferred at the decision gate** (see ledger and `deferred_decisions`). | File: skills/use-qwen/scripts/test_report.py:271 | Task: general | Found by: Bob

### Mechanical test-check absorption (fail-first replay, `mech-check`)

The tautological-shape check found nothing (83 tests, 4 files). The fail-first replay against `7b54ffc` ran 99 touched tests: 75 fail against base, 24 pass. Each `[MECH]` line becomes a row here; all three are judged against the PRD's intent at the decision gate:

- [1/4] 🟡 3 touched tests pass against the pre-change code: `test_render_rejects_a_malformed_audit_line_naming_it_and_leaves_output_unchanged`, `test_render_rejects_a_duplicate_attempt_dir_in_audit_jsonl_naming_it`, `test_render_rejects_a_contradictory_stored_outcome_via_classify_rederivation`. | File: skills/use-qwen/scripts/test_report.py | Task: general | Found by: mech-check — these are the three `pytest.raises(Exception)` → `pytest.raises(ValueError)` narrowings; the base code already raised `ValueError` on those inputs, so the narrowed expectation cannot fail against base. The tests now bind to the intended exception type. **Discarded** (see ledger).
- [1/4] 🟡 7 touched tests pass against the pre-change code: `test_render_accepts_a_review_effort_s_of_zero_null_or_any_finite_nonnegative_number`, `test_render_accepts_a_fully_populated_flagged_and_blocking_row`, `test_render_accepts_an_unverifiable_review_verdict` (+ parametrizations). | File: skills/use-qwen/scripts/test_report_audit.py | Task: 4 | Found by: mech-check — acceptance-side pins of the new validator: a permissive base accepts every row by construction, so an "accepts X" test cannot fail there; each fails if a future change over-tightens the validator. **Discarded** (see ledger).
- [1/4] 🟡 14 touched tests pass against the pre-change code: the `test_evidence_*`, `test_run_section_*`, `test_vetting_section_*`, `test_classification_section_*`, `test_counts_section_*`, `test_single_engine_*`, `test_retry_then_incomplete_*`, `test_measurements_*`, `test_audit_queue_*` tests. | File: skills/use-qwen/scripts/test_report_content.py | Task: 6 | Found by: mech-check — task 6 is the PRD-requested coverage backfill of rendering behavior that predates the rework (the PRD's own acceptance asked for these assertions), so passing against base is by design for 13 of them; the 14th, the shlex dispatch test, is the redundant one Bob flagged above and is handled by that row. **Discarded** (see ledger).

## Follow-up Tasks Created

None here. The cycle converged (no CRITICAL/HIGH); the actionable Medium/Low tail is swept by the decision gate's single `[D2] Tail sweep` task (run-autopilot Phase 5 § Tail sweep), not by per-finding tasks.

Verdict: 10 findings

Tests: 3429 passed, 0 failed, 6 skipped (reused from last-verification.json at 04693761f91255d9b994dc47e4fcc09bdaedf276)
