# Decision Audit Log: 00052-qwen-eval-harness-report-v1

PRD: `00052-qwen-eval-harness-report-v1.md`
Started: 2026-09-21T00:40:10Z
Completed: 2026-09-21T00:40:10Z
Autonomous: 20  |  Deferred: 2  |  Doubts: 0

### [autonomous] 2026-09-21T00:40:10Z

**Decision**: _counts_section is 53 lines (over the 50-line limit) and the module lacks its PRD-specified count()/load_audit() public exports

**Choice**: auto-fix

**Rationale**: additive-only (split the function, add two new public functions) and PRD-driven (Structural Decomposition names these exact exports)

### [autonomous] 2026-09-21T00:40:10Z

**Decision**: render's --run-id argparse argument has no format validator, unlike run's sibling --run-id

**Choice**: auto-fix

**Rationale**: additive-only: reuse the existing _run_id validator, no signature change

### [autonomous] 2026-09-21T00:40:10Z

**Decision**: F3: Classification does not validate record schemas or directory identity

**Choice**: auto-fix

**Rationale**: additive-only (more validation checks); folded into the CRITICAL's rework scope since both concern report.py's input validation

### [autonomous] 2026-09-21T00:40:10Z

**Decision**: pytest.raises(Exception) too broad on all three audit-rejection tests (test_report.py:302/311/320/330/338/349)

**Choice**: auto-fix

**Rationale**: mechanical fix (narrow to pytest.raises(ValueError)); consolidate_findings.py under-counted this as 3 separate 1/4 rows due to reviewer line-number drift, verified as one real 3/4-agreed defect

### [autonomous] 2026-09-21T00:40:10Z

**Decision**: Tautological or-hedge in test_a_planned_engine_with_no_attempt_directory_is_not_started_and_not_an_attempt (test_report.py:229)

**Choice**: auto-fix

**Rationale**: mechanical fix (tighten assertion to pin one specific side); same under-counting as above

### [autonomous] 2026-09-21T00:40:10Z

**Decision**: No test exercises evidence.md's per-attempt C6-shape field content against a real record

**Choice**: auto-fix

**Rationale**: additive-only (add tests)

### [autonomous] 2026-09-21T00:40:10Z

**Decision**: render() reads run_dir/run.json unconditionally, raw FileNotFoundError on a bad --run-id

**Choice**: auto-fix

**Rationale**: mechanical fix (existence check + named error)

### [autonomous] 2026-09-21T00:40:10Z

**Decision**: F4: task directory 01-calc reconstructed as 1-calc via %d-%s formatting, dropping the leading zero

**Choice**: auto-fix

**Rationale**: mechanical fix; implementor must verify the real zero-padding convention against records_domains.py/spec.py before changing the format string

### [autonomous] 2026-09-21T00:40:10Z

**Decision**: F5: wrapper.txt path/byte size omitted from evidence.md's captured-output inventory

**Choice**: auto-fix

**Rationale**: additive-only; implementor must verify wrapper.txt is a real sibling file in the attempt record contract (records.py) before adding it, per this PRD's prior corrected sibling-file-naming mistake in task 2

### [autonomous] 2026-09-21T00:40:10Z

**Decision**: F6: joining dispatch argv with spaces loses argument boundaries for paths/args containing spaces

**Choice**: auto-fix

**Rationale**: mechanical fix (render argv losslessly, e.g. as a JSON array)

### [autonomous] 2026-09-21T00:40:10Z

**Decision**: F7: engines with no attempt directories lose every numeric count field instead of retaining zeros

**Choice**: auto-fix

**Rationale**: mechanical fix

### [autonomous] 2026-09-21T00:40:10Z

**Decision**: F8: render tests omit several required scenarios (exact class/derived counts, single-engine, retry-then-incomplete, telemetry null/zero)

**Choice**: auto-fix

**Rationale**: additive-only (add tests)

### [autonomous] 2026-09-21T00:40:10Z

**Decision**: F14: _FAIL_CLASSES duplicates _CLASS_FIELD's ordered keys

**Choice**: auto-fix

**Rationale**: mechanical simplification (iterate the mapping directly)

### [autonomous] 2026-09-21T00:40:10Z

**Decision**: Audit.jsonl error reporting does not name the line number when validation fails

**Choice**: auto-fix

**Rationale**: subsumed into the CRITICAL's validation fix (naming the offending line is part of the same contract)

### [autonomous] 2026-09-21T00:40:10Z

**Decision**: Simplification: deduplicate baseline/canonical/necessity formatting shared between _setup_block and _vetting_section

**Choice**: auto-fix

**Rationale**: behavior-preserving simplification, mechanical

### [autonomous] 2026-09-21T00:40:10Z

**Decision**: F15: the runbook provides command placeholders without a fixture/spec preparation recipe, so a fresh session cannot run the fixture from docs alone

**Choice**: discard

**Rationale**: verified false: conflates pytest's internal test fixtures with the runbook's own evidence-directory-preparation coverage in existing sections 1-6; section 7 correctly limits itself to naming the three harness commands per its ~25-line PRD budget

### [autonomous] 2026-09-21T00:40:10Z

**Decision**: Cannot statically verify: the two additional shell regression suites required by Task 3 pass

**Choice**: discard

**Rationale**: verified false: already run and recorded passing by task 3's own implementor (test_qwen_run.sh 78 passed, test_eval_automation.sh 24 passed), visible in the review context Bob's sandboxed inputs did not surface

### [autonomous] 2026-09-21T00:40:10Z

**Decision**: Phase 6 rework dispatch: rework design (PRD 00194) resumed from the prior session's interrupted draft and passed (3 dispatches: claude 4 blockers fixed, codex 3 blockers fixed, dispatch 3 codex usage-limited -> Claude fallback verified all closed, result: ok); 16 actionable findings split into 3 sequential [D1] tasks (4: CRITICAL+3 HIGH+2 Medium at opus/contract; 5: report.py Medium tail x8 at sonnet; 6: tests-only Medium x2 at sonnet/test_port)

**Choice**: rework

**Rationale**: cycle 1 < rework_cap 2; >10 findings split by file/theme per the split rule; CRITICAL task carries the rework design Contract verbatim

### [autonomous] 2026-09-21T00:40:10Z

**Decision**: Cycle-2 review converged: 0 CRITICAL/HIGH, 1 Medium (2/4) + 6 Low + 3 mech-check replay rows; all 16 cycle-1 findings verified resolved by all four lenses; Blake B1-B19 pass; constraint gate exit 0. Bob ran as the Claude fallback (codex usage limit, first run + retry exit 1); the shadow workflow leg ran (APPROVE, 11 advisory, wf_bc133a2a-4a5)

**Choice**: converge; tail sweep of 5 actionable Medium/Low findings as one [D2] task, then finalize hand-off

**Rationale**: Phase 5 convergence test met (no unresolved CRITICAL/HIGH + doubt-roster gate certified); Medium/Low never block and are swept, not dropped

### [autonomous] 2026-09-21T00:40:10Z

**Decision**: Discarded 4 findings: (a) Bob LOW: fix(use-qwen) commit eceb591 lacks a CHANGELOG entry; (b) mech-check: 3 narrowed pytest.raises(Exception)->ValueError tests in test_report.py pass against base; (c) mech-check: 7 accept-side validator tests in test_report_audit.py pass against base; (d) mech-check: 14 coverage-backfill tests in test_report_content.py pass against base

**Choice**: discard, ledgered

**Rationale**: (a) the fixed behavior is part of the still-unreleased render feature whose ### Added line covers it, per Bob own KNOWN bucket; (b) base already raised ValueError, so a narrowed expectation cannot fail there yet binds to the intended type; (c) a permissive base accepts every row by construction, so accept-tests cannot fail against it; (d) task 6 was the PRD-requested backfill of behavior that predates the rework, passing by design (its one redundant shlex test is swept via Bob row)

### [deferred] 2026-09-21T00:40:10Z

**Decision**: render() silently accepts unknown-attempt_dir, non-VALID-attempt, missing-key, and invalid-verdict-value audit.jsonl rows (only duplicate-id and malformed-JSON are checked), contradicting the PRD's explicit Audit-queue Behavior contract and Risks section; confirmed by direct execution against 4 probe cases by two independent reviewers

**Choice**: will be fixed via Phase 6 rework this cycle

**Rationale**: Critical severity, always deferred to the batch-end audit trail per the decision framework; still fixed THIS cycle via Phase 6's mandatory rework-design gate (PRD 00194) — deferral here is bookkeeping, not a skip

### [deferred] 2026-09-21T00:40:10Z

**Decision**: Order-dependent test state in pre-existing cycle-1 tests: test_f_is_pending_k_of_n_with_a_partial_audit_file (test_report.py:271), test_f_is_a_plain_number... (:283), test_f_counts_only_flagged... (:295) and test_audit_queue_shows_the_stored_verdict_once_a_row_exists (:393) write audit.jsonl into the module-shared r1 round and never remove it; test_audit_queue_lists_every_valid_attempt_pending_where_no_row_exists (:381) passes only because the malformed-line test (:323) unlinked the file first

**Choice**: defer

**Rationale**: pre-existing cycle-1 test functions the [D1] rework did not touch (only their pytest.raises narrowing changed); suite is green; the new test_report_audit.py helpers clean up correctly; fixing the old ones is a separate test-hygiene change outside the three rework tasks (Bob KNOWN bucket, D4 justified)
