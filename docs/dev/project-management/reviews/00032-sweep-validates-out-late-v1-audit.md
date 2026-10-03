# Decision Audit Log: 00032-sweep-validates-out-late-v1

PRD: `00032-sweep-validates-out-late-v1.md`
Started: 2026-09-06T23:11:04Z
Completed: 2026-09-06T23:11:04Z
Autonomous: 6  |  Deferred: 0  |  Doubts: 0

### [autonomous] 2026-09-06T23:11:04Z

**Decision**: New regression test does not pin the fix: test_a_refused_out_path_creates_no_report_directory passes against pre-change code

**Choice**: settled-deferral

**Rationale**: Cycle 1. The reorder IS pinned by test_an_out_path_outside_the_cwd_repo_is_refused_before_any_repo_is_scanned (test_sweep_main.py:469-483), which stubs sweep.scan and asserts scans == [] and failed against pre-change code (hence its strict-xfail). The new test guards a different, PRD-mandated invariant: a refused run creates no directory. Ledger: 00032-sweep-validates-out-late-v1-ledger.json

### [autonomous] 2026-09-06T23:11:04Z

**Decision**: BOB FIX: stub enumerate_repos in the new no-directory test and assert it is never called

**Choice**: settled-deferral

**Rationale**: Cycle 1. Duplicates the existing pin at test_sweep_main.py:469-483 one call earlier in the same file; the review checklist forbids adding redundant coverage.

### [autonomous] 2026-09-06T23:11:04Z

**Decision**: Pre-existing either-or hedge assertion at test_sweep_main.py:211 lets the test pass regardless of which string appears in stderr

**Choice**: settled-deferral

**Rationale**: Cycle 1. Pre-existing and out of scope: the PRD Success Criteria require this test to pass unchanged so the fence and its message are untouched. Suggested as a separate backlog PRD in the review file.

### [autonomous] 2026-09-06T23:11:04Z

**Decision**: BOB KNOWN: the either-or message assertion leaves half the refusal-message contract unpinned

**Choice**: settled-deferral

**Rationale**: Cycle 1. Same defect and same resolution as the ALICE :211 row; the doubt lens filed it KNOWN with the identical out-of-scope justification.

### [autonomous] 2026-09-06T23:11:04Z

**Decision**: BOB KNOWN: changelog entry landed in 19cbdf7, separate from fix commit a070b8f

**Choice**: settled-deferral

**Rationale**: Cycle 1. The CHANGELOG entry exists and is correct; only the commit boundary differs. The sole remedy is rewriting published master history, disproportionate to a process slip with no user-visible effect.

### [autonomous] 2026-09-06T23:11:04Z

**Decision**: BOB VERIFY: cannot statically verify that pytest, validate_skill.py and braid --check pass

**Choice**: discarded

**Rationale**: Cycle 1. Already answered by recorded fact: last-verification.json records all three commands at sha 19cbdf76f4eef0216328d69b25ac0fb808b014da (the reviewed HEAD), each exit 0, 1090 passed / 0 failed / 5 skipped. Carl re-ran the sweep-fix subset and both skill checks live during this cycle; all passed. Not queued: no eligible doubt-lens VERIFY bucket exists this cycle (Eve did not run, source bob is reserved).
