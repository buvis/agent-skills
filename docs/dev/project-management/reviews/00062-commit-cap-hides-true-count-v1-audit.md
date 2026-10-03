# Decision Audit Log: 00062-commit-cap-hides-true-count-v1

PRD: `00062-commit-cap-hides-true-count-v1.md`
Started: 2026-09-26T12:19:11Z
Completed: 2026-09-26T12:19:11Z
Autonomous: 5  |  Deferred: 0  |  Doubts: 0

### [autonomous] 2026-09-26T12:19:11Z

**Decision**: Bob (codex, static-only sandbox) raised: Cannot statically verify runtime tests and generated-template reproducibility (low, 1/4)

**Choice**: discarded - the named checks were executed this cycle by three independent lenses with concurring results; no task created, recorded in the settled-decisions ledger so it does not return

**Rationale**: The finding names three checks: uv run pytest -q, npm --prefix skills/brief-portfolio/app test, and a fresh app build compared with assets/template.html. Alice ran all three (103 passed plus 1 pre-existing missing-registry xfail; 53 passed 0 failed; rebuilt bundle byte-identical to the committed template). Carl independently ran both suites plus diff -q against the template (match). Blake independently ran both suites. The work phase record at the same HEAD (last-verification.json, sha da66f97) agrees: 3524 passed, 0 failed, 6 skipped. This is a limitation of one lens sandbox, already answered by the panel, not a defect in the change.

### [autonomous] 2026-09-26T12:19:11Z

**Decision**: Two pack instructions conflict on who creates tasks for a converged cycle Medium/Low tail: review-work-completion step 7 creates one follow-up task per finding, while phase-review.md Tail sweep builds exactly ONE [D{cycle}] task

**Choice**: followed the Tail sweep and ran no per-finding task-add in step 7; one [D1] Tail sweep task carries all nine swept findings verbatim

**Rationale**: Running both would double-create tasks for the same findings, and the sweep Select step has no exclusion for rows step 7 already turned into tasks. The Tail sweep wins on two grounds: it is specific to the converged outcome this cycle actually took (step 7 is the generic path, also used on standalone runs and on non-converged cycles that proceed to Phase 6), and it is the newer contract, introduced with the severity bar that makes a Medium/Low-only cycle converge in the first place. Recorded rather than silently chosen because it is a real contradiction in the pack, not a judgement call the prose settles.

### [autonomous] 2026-09-26T12:19:11Z

**Decision**: engram pack exited 1 (not inside a registered repo; register it in the gita repos.csv), so this cycle had no retrieval context pack

**Choice**: proceeded with the sentinel (no pack available this cycle) substituted for PACK_FILE and PACK_FINDINGS in every prompt that takes them; recorded the failure in the review file top matter; no retry

**Rationale**: The skill permits at most one retry and forbids the pack from blocking the cycle. The failure is a deterministic configuration fact (this repository is absent from the gita registry the tool requires), so a retry would fail identically and only cost time. The pack is additive retrieval context: a review without it is degraded, not invalid, and the loss is stated in the review file rather than hidden.

### [autonomous] 2026-09-26T12:19:11Z

**Decision**: Carl proposed replacing the derive.js in-check fallback with the nullish-coalescing form; the in-check was a deliberate, documented build-phase choice (assumptions.md), so the simplification risked being an over-simplification the checklist forbids

**Choice**: accepted and swept, not rejected

**Rationale**: Checked the divergence rather than trusting either side. The nullish form preserves the documented commit_count equal to 0 boundary, because 0 nullish-coalesced is 0, and a test pins that case. The two forms differ only for null or undefined, which collect_commit_count cannot produce since it returns int(...) and a failed collector leaves the key absent entirely. On a hand-edited or corrupted data.json carrying a null count the nullish form degrades to the list length instead of silently contributing zero, which the project rule never trust external data prefers. So it is shorter and slightly more forgiving, with no documented invariant removed.

### [autonomous] 2026-09-26T12:19:11Z

**Decision**: Step 2.95's red-check (task 3, PRD 00062 tail sweep) showed all tests green both before and after Ivan's derive.js edit - the literal 'accidentally green' trigger that normally sends Tess back for another strengthen round

**Choice**: skipped the standard all-pass -> Tess-strengthen retry and proceeded straight to Ivan; verified manually during the step 2.8 quality gate that every strengthened/added assertion in Tess's diff already contains a genuine negative differentiator for the specific regression its finding named

**Rationale**: This task is a regression-pinning/test-hygiene sweep for already-correct, already-reviewed production code (converged cycle 1, zero Critical/High findings from any lens), not new-feature TDD - the tests are SUPPOSED to stay green against the current implementation. Confirmed via direct code reading, not by trusting Tess's self-report alone: the history_counts tuple-exclusion test fails if commit_count is ever added to the failure-marking tuple, the metadata-failure test's monkeypatched sentinel would raise loudly if collect_commit_count were ever called after a metadata failure, and both JS branch tests now assert on a sibling record that differentiates the commit_count-present vs commit_count-absent/matching cases. A real Tess retry would have spent budget reproducing safeguards she had already written from maximally explicit fix instructions.
