---
prd: dev/local/prds/wip/00052-qwen-eval-harness-report-v1.md
review: 1
date: 2026-09-20
head_sha: 7b54ffc31894ed6050d6f590c0a93a48fd5c80ec
codex_thread_id: 01a0c08f-fbb5-7b40-8e4a-732d5b6791c8
reviewers: alice,blake,bob,carl
agents:
  alice: available
  blake: available
  bob: available
  carl: available
---

# Review: 00052-qwen-eval-harness-report-v1

Diff range: `0fccf1ee0b9f863ce24904e861ba5c75c375d9e8..7b54ffc31894ed6050d6f590c0a93a48fd5c80ec` (full review, cycle 1 — `work_start_sha..HEAD`; rebuilt by hand because `gather-context.sh`'s `vs master` diff is empty on this branch since this repo commits directly to master, a known gap recorded in memory `review-phase-known-overhead`)

codex_rung_guard: not fired

(0 codex-implemented tasks — all 3 tasks in this PRD ran `implementor: "claude"`)

consensus_engine: shadow — **workflow leg did not run this cycle.** The `review-fanout` workflow file exists at `~/.claude/workflows/review-fanout.workflow.js`, but the `Workflow` tool refused the call with "scriptPath must be a script path this tool returned, or a file you can already read (the working directory or a directory you have added)" — an environment/sandbox restriction on that path, not a missing file. Per SKILL.md step 5's "Engine unavailable" fallback, the cycle fell back to legacy Alice only, which gates the cycle as normal. No `consensus_run_id` this cycle.

pack: skipped (`engram pack` exited 1 twice: "not inside a registered repo; register it in /Users/bob/.config/gita/repos.csv" — the same known, long-standing gap recorded in the project capsule, now 34 passes old)

## Summary

Reviewed: 3 completed tasks (PRD 00052, Qwen Eval Harness Report)
Task 1: Verify PRD 00051 landed and provide the render-test fixture round (completed, foundation task, no code changes)
Task 2: Implement eval_harness/report.py and the render subcommand (completed; required a full per-task-review CRITICAL-fix cycle mid-build — Pat found 7 CRITICAL contract gaps in the first pass, all fixed and delta-re-reviewed clean)
Task 3: Document the harness: runbook section 7, SKILL.md bullet, CHANGELOG (completed; per-task review NO FINDINGS)

### Agent Status
- Alice: ✅ Available (legacy leg; shadow workflow leg unavailable this cycle, see above)
- Blake: ✅ Available
- Bob: ✅ Available (first run succeeded, no retry needed)
- Carl: ✅ Available (copilot backend, gemini-3.8-flash)

## Alice

[ALICE] 🔴 render() silently accepts unknown-attempt_dir, non-VALID-attempt, missing-key, and invalid-verdict-value audit.jsonl rows (only duplicate-id and malformed-JSON are checked); confirmed by direct execution against 4 probe cases, contradicting the PRD's Audit-queue Behavior contract and its own Risks section | File: skills/use-qwen/scripts/eval_harness/report.py:54 | Task: 2
[ALICE] 🟠 render's --run-id argparse argument has no format validator (plain str), unlike run's sibling --run-id (type=_run_id → admission.check_run_id, which rejects "..", separators, non-single-directory-name ids); report.render() joins it straight into root/"runs"/run_id | File: skills/use-qwen/scripts/run_eval_harness.py:53 | Task: 2
[ALICE] 🟡 _counts_section is 53 lines (def at 236, return at 288), over the 50-line function-size limit; the per-engine tally loop and the scored/not_started/f summary are independent enough to split | File: skills/use-qwen/scripts/eval_harness/report.py:236 | Task: 2
[ALICE] 🟡 Tautological assertion hedges with `or`: either "cmd3 ... not_started" or "not_started ... cmd3" satisfies it, so the test can't fail on a regression in which side names which | File: skills/use-qwen/scripts/test_report.py:229 | Task: 2
[ALICE] 🟡 pytest.raises(Exception) is too broad — any exception (not just the malformed-JSON ValueError render is meant to raise) satisfies it | File: skills/use-qwen/scripts/test_report.py:302 | Task: 2
[ALICE] 🟡 pytest.raises(Exception) is too broad — same pattern, duplicate-attempt_dir case | File: skills/use-qwen/scripts/test_report.py:320 | Task: 2
[ALICE] 🟡 pytest.raises(Exception) is too broad — same pattern, contradictory-outcome case | File: skills/use-qwen/scripts/test_report.py:338 | Task: 2
[ALICE] 🟡 No test exercises evidence.md's per-attempt C6-shape field content (tree, dispatch argv, engine identity, captured-output byte size, baseline first-failure line, own/gate/ablation exit codes) against a real (non-INCOMPLETE) record, nor the Run/Vetting/Classification section field content — only structural properties (block counts, section order, counts recount) are tested | File: skills/use-qwen/scripts/test_report.py:1 | Task: 2

R1: fail
R2: fail
R3: pass
R4: pass
R6: pass
R7: fail
R8: pass
R9: fail
R10: pass
R11: pass
R12: fail
R13: pass

Verification performed: read report.py, records.py, run_eval_harness.py, admission.py directly; ran the full skills/use-qwen/scripts suite (2131 passed, 1 skipped — pre-existing platform-conditional skips, none from this diff); ran validate_skill.py skills/use-qwen (OK). Empirically probed the audit-queue validation contract with a throwaway probe test (reverted, tree clean): confirmed report.render() does NOT raise for an unknown attempt_dir, a non-VALID attempt, a row missing required keys, or verdict: "maybe".

## Blake

[BLAKE] 🔴 render() accepts audit.jsonl rows with an out-of-enum verdict ("maybe"), an unknown/non-existent attempt_dir, or missing required keys (claim, evidence, review_verdict, review_findings, review_effort_s) without raising or naming the line - directly contradicting the PRD's explicit required Error case ("audit.jsonl row with verdict: maybe → render exits non-zero naming the line and writes no partial files") and the Audit queue Behavior spec ("A duplicate attempt_dir, unknown/non-VALID attempt, missing/extra key, invalid value/type or malformed JSON fails render naming the line"). Reproduced directly: wrote a `{"attempt_dir": <valid id>, "verdict": "maybe", ...}` row, an unknown-attempt_dir row, and a row missing 5 required keys against the "r1" fixture round and called report.render() for each - all three completed successfully and wrote report files instead of raising. _load_audit only checks JSON-parseability and duplicate attempt_dir; it never checks the verdict/review_verdict enums, claim/evidence non-emptiness for flagged rows, review_findings type, review_effort_s type/range, or that attempt_dir names a known VALID attempt. | File: skills/use-qwen/scripts/eval_harness/report.py:54 | Task: Audit queue
[BLAKE] 🟠 The PRD's Structural Decomposition names three exports for the Report module - render(), load_audit(), count() - but only render() is a public symbol. Audit-row loading is the private _load_audit (report.py:54) and counting logic is inlined inside a private _counts_section helper (report.py:236); there is no standalone count() function at all. | File: skills/use-qwen/scripts/eval_harness/report.py:384 | Task: Evidence Rendering
[BLAKE] 🟡 render() reads run_dir/run.json unconditionally with no existence check (`json.loads((run_dir / "run.json").read_text(...))`), so a typo'd --run-id or a run that never completed `run` produces a raw FileNotFoundError traceback rather than a message naming the run-id. | File: skills/use-qwen/scripts/eval_harness/report.py:387 | Task: Evidence Rendering
[BLAKE] ✅ Runbook § 7, SKILL.md onboarding bullet, and CHANGELOG entry all match the PRD's premises, wording and placement exactly; render CLI surface (evidence_dir positional + --run-id) matches spec exactly with no extra flags. | File: N/A | Task: Documentation

B1: fail
B2: pass
B3: fail
B4: pass
B5: fail
B6: pass
B7: pass
B8: pass
B9: pass
B10: fail
B11: pass
B12: pass
B13: pass
B14: pass
B15: fail
B16: pass
B17: fail
B18: pass
B19: pass

Verification method: read eval_harness/report.py, run_eval_harness.py's render dispatch, records.py, vetting.py, test_report.py (all 26 tests pass: `uv run pytest skills/use-qwen/scripts/test_report.py -q` → 26 passed). Wrote a throwaway probe test (outside the repo, deleted afterward; `git status --porcelain` confirmed clean) driving `report.render()` against three malformed audit.jsonl rows; all three should have raised per spec, none did.

## Bob

[BOB] 🟠 F1: Audit rows lack schema and membership validation; verdict `maybe` can complete auditing, produce `f: 0`, and remove the decision-rule warning. Unknown/non-VALID rows are silently accepted. | File: skills/use-qwen/scripts/eval_harness/report.py:66 | Task: 2
[BOB] 🟠 F2: Render omits run-ID validation; absolute or traversing IDs can redirect its three writes outside the evidence directory's runs folder. | File: skills/use-qwen/scripts/run_eval_harness.py:53 | Task: 2
[BOB] 🟠 F3: Classification does not validate record schemas or directory identity. Invalid telemetry and mismatched task/engine fields can render successfully; malformed-record errors lack the offending path. | File: skills/use-qwen/scripts/eval_harness/report.py:39 | Task: 2
[BOB] 🟡 F4: Valid task directory `01-calc` is reconstructed as `1-calc`, silently omitting its existing vetting results. | File: skills/use-qwen/scripts/eval_harness/report.py:74 | Task: 2
[BOB] 🟡 F5: C6's captured-output inventory omits the wrapper.txt path and byte size, although that artifact carries dispatch identity evidence. | File: skills/use-qwen/scripts/eval_harness/report.py:159 | Task: 2
[BOB] 🟡 F6: Joining argv with spaces loses argument boundaries; paths or arguments containing spaces no longer describe the exact dispatch. | File: skills/use-qwen/scripts/eval_harness/report.py:157 | Task: 2
[BOB] 🟡 F7: Engines with no attempt directories lose every numeric count, including attempts: 0, instead of retaining the required per-engine count fields. | File: skills/use-qwen/scripts/eval_harness/report.py:241 | Task: 2
[BOB] 🟡 F8: Render tests omit required exact class/derived counts, single-engine and retry-then-incomplete cases, telemetry null/zero checks, and substantive evidence/audit-queue field assertions. | File: skills/use-qwen/scripts/test_report.py:201 | Task: 2
[BOB] 🟡 F9: The NOT_STARTED assertion hedges with `or` and uses unsupported engine cmd3; it does not pin the required zero-attempt counts. | File: skills/use-qwen/scripts/test_report.py:229 | Task: 2
[BOB] 🟡 F10: The malformed-audit test accepts any Exception instead of the intended validation error. | File: skills/use-qwen/scripts/test_report.py:311 | Task: 2
[BOB] 🟡 F11: The duplicate-audit test accepts any Exception instead of the intended validation error. | File: skills/use-qwen/scripts/test_report.py:330 | Task: 2
[BOB] 🟡 F12: The contradictory-outcome test accepts any Exception instead of the intended validation error. | File: skills/use-qwen/scripts/test_report.py:349 | Task: 2
[BOB] 🟡 F13: The specified load_audit()/count() exports are absent; counting remains embedded in the 53-line _counts_section, exceeding the function limit. | File: skills/use-qwen/scripts/eval_harness/report.py:236 | Task: 2
[BOB] 🟡 F14: _FAIL_CLASSES duplicates _CLASS_FIELD's ordered keys; use the mapping as the single failure-class roster. | File: skills/use-qwen/scripts/eval_harness/report.py:15 | Task: 2
[BOB] 🟡 F15: The runbook provides placeholders without fixture/spec preparation or accepted engine values, so a fresh session cannot run the fixture from these instructions alone. | File: skills/use-qwen/references/eval-runbook.md:105 | Task: 3
[BOB] ⚪ Cannot statically verify: the two additional shell regression suites required by Task 3 pass (F16); their results are not recorded. | File: N/A | Task: 3

FIX:
- F1 through F15 (fix descriptions in raw output dev/local/tmp/bob-output-1.txt)

VERIFY:
- F16 — Run `bash skills/use-qwen/scripts/test_qwen_run.sh` and `bash skills/use-qwen/scripts/test_eval_automation.sh`; record their exit statuses. (Already resolved: both were run by the task-3 implementor per dev/local/tmp/review-tasks-1.md, 78 passed / 24 passed — see decision-gate note below.)

KNOWN:
- (none)

R1: fail
R2: fail
R3: pass
R4: fail
R6: pass
R7: fail
R8: pass
R9: fail
R10: fail
R11: pass
R12: fail
R13: pass

D1: pass
D2: pass
D3: pass
D4: pass
D5: pass

Sandbox: static analysis only, first run succeeded (no retry needed). Full raw output: dev/local/tmp/bob-output-1.txt.

## Carl

[CARL] 🟠 Hand-written audit.jsonl input lacks validation for unknown attempt_dir, non-VALID attempt, missing/extra keys, and allowed verdict values (clean|flagged|unverifiable) | File: skills/use-qwen/scripts/eval_harness/report.py:54 | Task: 2
[CARL] 🟡 Audit.jsonl error reporting does not name the line number when validation fails | File: skills/use-qwen/scripts/eval_harness/report.py:64 | Task: 2
[CARL] 🟡 Function _counts_section is 53 lines, exceeding the 50-line limit | File: skills/use-qwen/scripts/eval_harness/report.py:236 | Task: 2
[CARL] 🟡 test_a_planned_engine_with_no_attempt_directory_is_not_started_and_not_an_attempt hedges with or: either outcome satisfies it | File: skills/use-qwen/scripts/test_report.py:229 | Task: general
[CARL] 🟡 test_render_rejects_a_malformed_audit_line_naming_it_and_leaves_output_unchanged accepts any exception via raises(Exception) | File: skills/use-qwen/scripts/test_report.py:311 | Task: general
[CARL] 🟡 test_render_rejects_a_duplicate_attempt_dir_in_audit_jsonl_naming_it accepts any exception via raises(Exception) | File: skills/use-qwen/scripts/test_report.py:330 | Task: general
[CARL] 🟡 test_render_rejects_a_contradictory_stored_outcome_via_classify_rederivation accepts any exception via raises(Exception) | File: skills/use-qwen/scripts/test_report.py:349 | Task: general
[CARL] 🟡 Simplification: extract per-engine tallies from _counts_section into a helper to reduce complexity and bring the function under 50 lines | File: skills/use-qwen/scripts/eval_harness/report.py:236 | Task: 2
[CARL] 🟡 Simplification: deduplicate baseline, canonical, and necessity formatting shared between _setup_block and _vetting_section | File: skills/use-qwen/scripts/eval_harness/report.py:118 | Task: 2

R1: fail
R2: fail
R3: pass
R4: pass
R6: pass
R7: fail
R8: pass
R9: fail
R10: pass
R11: pass
R12: fail
R13: pass

Backend: copilot, model gemini-3.8-flash. Verification: ran `uv run pytest skills/use-qwen/scripts -q` (2131 passed at the time of Carl's check), `validate_skill.py skills/use-qwen` (OK), and `run_eval_harness.py render --help`. Full raw output: dev/local/tmp/carl-output-1.txt.

## Consolidated Findings

### Full Consensus (4/4)

- [4/4] 🔴 **render() silently accepts unknown-attempt_dir, non-VALID-attempt, missing-key, and invalid-verdict-value audit.jsonl rows** — only duplicate-id and malformed-JSON are checked (`_load_audit`). Confirmed independently by direct execution (Alice and Blake each wrote throwaway probe tests, reverted after) against 4 probe cases: an audit row naming a nonexistent attempt_dir, a row auditing a non-VALID attempt, a row missing required keys, and a row with `verdict: "maybe"` (the PRD's own stated Test Strategy error case). All four rendered successfully with no error, directly contradicting the PRD's Audit-queue Behavior contract and its Risks section verbatim.
  - File: skills/use-qwen/scripts/eval_harness/report.py:54
  - Task: 2
  - Found by: Alice, Blake, Bob, Carl

### Majority/Notable

- [4/4] 🟠 **_counts_section is 53 lines (def at 236, return at 288), over the 50-line function-size limit** (Alice, Bob, Carl) — **this row also bundles a distinct finding from Blake**: the PRD's Structural Decomposition names three Report-module exports — `render()`, `load_audit()`, `count()` — but only `render()` is public; `load_audit` is the private `_load_audit` and `count()` does not exist as a standalone symbol at all (report.py:384). `consolidate_findings.py`'s citation-suffix matching merged these two genuinely different issues into one row; both are real and both need fixing.
  - File: skills/use-qwen/scripts/eval_harness/report.py:236 (line-length), :384 (missing exports)
  - Task: 2
  - Found by: Alice, Blake, Bob, Carl
- [2/4] 🟠 **render's `--run-id` argparse argument has no format validator** (plain `str`), unlike `run`'s sibling `--run-id` (`type=_run_id` → `admission.check_run_id`); `report.render()` joins it straight into `root/"runs"/run_id`.
  - File: skills/use-qwen/scripts/run_eval_harness.py:53
  - Task: 2
  - Found by: Alice, Bob
- [1/4] 🟠 F3: Classification does not validate record schemas or directory identity — invalid telemetry and mismatched task/engine fields can render successfully.
  - File: skills/use-qwen/scripts/eval_harness/report.py:39
  - Task: 2
  - Found by: Bob

### Medium/Low tail (multi-reviewer agreement the consolidation script under-counted — see note)

- 🟡 **`pytest.raises(Exception)` is too broad on all three audit-rejection tests** — should narrow to `pytest.raises(ValueError)`. Raised independently by all three implementation-aware reviewers (Alice at test_report.py:302/320/338, Bob F10-F12 at :311/330/349, Carl at :311/330/349) — a real, 3/4-reviewer-agreed defect across three tests.
  - File: skills/use-qwen/scripts/test_report.py:302,311,320,330,338,349 | Task: 2 | Found by: Alice, Bob, Carl
- 🟡 **Tautological `or`-hedge** in `test_a_planned_engine_with_no_attempt_directory_is_not_started_and_not_an_attempt`. Raised independently by Alice, Bob (F9), and Carl at test_report.py:229.
  - File: skills/use-qwen/scripts/test_report.py:229 | Task: 2 | Found by: Alice, Bob, Carl
- [1/4] 🟡 No test exercises evidence.md's per-attempt C6-shape field content against a real (non-INCOMPLETE) record. | File: skills/use-qwen/scripts/test_report.py:1 | Task: 2 | Found by: Alice
- [1/4] 🟡 render() reads run_dir/run.json unconditionally with no existence check. | File: skills/use-qwen/scripts/eval_harness/report.py:387 | Task: Evidence Rendering | Found by: Blake
- [1/4] 🟡 F4: `01-calc` reconstructed as `1-calc` (via `%d-%s`), silently omitting existing vetting results. | File: skills/use-qwen/scripts/eval_harness/report.py:74 | Task: 2 | Found by: Bob
- [1/4] 🟡 F5: wrapper.txt path/byte size omitted from the captured-output inventory. | File: skills/use-qwen/scripts/eval_harness/report.py:159 | Task: 2 | Found by: Bob
- [1/4] 🟡 F6: Joining argv with spaces loses argument boundaries. | File: skills/use-qwen/scripts/eval_harness/report.py:157 | Task: 2 | Found by: Bob
- [1/4] 🟡 F7: Engines with no attempt directories lose every numeric count field instead of retaining zeros. | File: skills/use-qwen/scripts/eval_harness/report.py:241 | Task: 2 | Found by: Bob
- [1/4] 🟡 F8: Render tests omit several required scenarios. | File: skills/use-qwen/scripts/test_report.py:201 | Task: 2 | Found by: Bob
- [1/4] 🟡 F14: _FAIL_CLASSES duplicates _CLASS_FIELD's ordered keys. | File: skills/use-qwen/scripts/eval_harness/report.py:15 | Task: 2 | Found by: Bob
- [1/4] 🟡 F15: runbook lacks fixture/spec preparation recipe — DISCARD candidate, see note below. | File: skills/use-qwen/references/eval-runbook.md:105 | Task: 3 | Found by: Bob
- [1/4] 🟡 Audit.jsonl error reporting does not name the line number — subsumed by the CRITICAL's fix. | File: skills/use-qwen/scripts/eval_harness/report.py:64 | Task: 2 | Found by: Carl
- [1/4] 🟡 Simplification: deduplicate baseline/canonical/necessity formatting. | File: skills/use-qwen/scripts/eval_harness/report.py:118 | Task: 2 | Found by: Carl
- [1/4] ⚪ Cannot statically verify shell suites pass — DISCARD, see note below. | File: N/A | Task: 3 | Found by: Bob

**Note on F15 and the ⚪ finding (Bob):** both are already resolved by evidence Bob's own sandboxed inputs did not surface. Task 3's own commit (`7b54ffc`) and its per-task verification (recorded in `dev/local/tmp/review-tasks-1.md`, which was in Bob's context) show `bash skills/use-qwen/scripts/test_qwen_run.sh` → 78 passed and `bash skills/use-qwen/scripts/test_eval_automation.sh` → 24 passed, both already run by the implementor. F15's "fixture repo" concern conflates the PRD's Exit Criteria wording (an operator preparing a real evidence directory via `vet`, documented in runbook §1-6) with pytest's internal test fixtures (`rounds`) — the runbook's own §1-6 already covers evidence-directory preparation, and §7 correctly limits itself to naming the three harness commands per its ~25-line budget. Both are discarded at the decision gate as verified-resolved / based-on-a-misunderstanding, not fixed.

### Mechanical test-check absorption

All four `[MECH]` lines from the context file's tautological-shape and fail-first-replay blocks are represented above: the `or`-hedge row and the three `raises(Exception)`-too-broad instances. The fail-first-replay's 36-test flag (`test_run_eval_harness_outcomes.py`) is informational, not a finding — those are PRD-00051's own pre-existing outcome tests, relocated (not newly written) by this PRD's task-2 commit `df71f88` to stay under the 800-line style cap.

## Follow-up Tasks Created

None here. Created by the decision gate's Phase 6 (rework), not this step — per PRD 00194 and this repo's own established precedent (PRD 00051 cycle 1: "Created by the decision gate's Phase 6 (below), not here: ... Creating them in this step as well would double-create the same work.").

Verdict: 18 findings

Tests: 3334 passed, 0 failed, 6 skipped (reused from last-verification.json at 7b54ffc31894ed6050d6f590c0a93a48fd5c80ec)
