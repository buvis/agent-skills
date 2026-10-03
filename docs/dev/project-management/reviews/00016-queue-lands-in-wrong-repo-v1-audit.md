# Decision Audit Log: 00016-queue-lands-in-wrong-repo-v1

PRD: `00016-queue-lands-in-wrong-repo-v1.md`
Started: 2026-09-06T00:06:55Z
Completed: 2026-09-06T00:06:55Z
Autonomous: 10  |  Deferred: 0  |  Doubts: 0

### [autonomous] 2026-09-06T00:06:55Z

**Decision**: No CHANGELOG.md entry for this fix; the default queue location changes for any save call without --queue

**Choice**: auto-fix

**Rationale**: Confirmed: rg over CHANGELOG.md finds no [Unreleased] entry mentioning --queue. The rules/changelog.md BLOCKING rule mandates an entry for feat/fix commits, and this PRD has three (8990faf, 4304e5f, a5f7ed2). Fix is purely additive, so it is auto-fixed in rework, not escalated.

### [autonomous] 2026-09-06T00:06:55Z

**Decision**: SKILL.md step 7 reads the cursor from <queue-path> but the entry count from cwd-relative dev/local/audit-results/distil-memory-queue.json

**Choice**: auto-fix

**Rationale**: Confirmed at SKILL.md:271-272. Clear mechanical fix and it defeats the PRD intent: the walkthrough still reads the queue from the cwd. Bob R4 and R9 fails both trace here.

### [autonomous] 2026-09-06T00:06:55Z

**Decision**: _proposal() is duplicated byte-for-byte between test_docket.py:11-21 and test_docket_cli.py:11-21

**Choice**: auto-fix

**Rationale**: Confirmed identical. Duplication introduced by task 1 split-hygiene. Medium at 1/4 consensus classifies as auto-fix; a shared conftest.py fixture removes it.

### [autonomous] 2026-09-06T00:06:55Z

**Decision**: Obsolete four-line comment at test_docket_cli.py:24 claims every CLI test uses cwd-derived queues without explicit paths

**Choice**: auto-fix

**Rationale**: Confirmed at test_docket_cli.py:24-27; the migrated save assertions now do the opposite. Mechanical comment fix.

### [autonomous] 2026-09-06T00:06:55Z

**Decision**: 10 touched tests pass against the pre-change code in test_docket_cli.py

**Choice**: settled-deferral

**Rationale**: Unchanged relocations from test_docket.py performed by task 1 split-hygiene; they pin pre-existing behavior by design, the replay block own documented behavior-preserving case. Recorded in the settled-decisions ledger.

### [autonomous] 2026-09-06T00:06:55Z

**Decision**: PRD Implementation section cites test_docket.py:402-727 as the home of the main() CLI tests

**Choice**: settled-deferral

**Rationale**: Stale line reference in PRD prose, not a code defect; the PRD moves to done/ at finalize. Recorded in the settled-decisions ledger.

### [autonomous] 2026-09-06T00:06:55Z

**Decision**: _save_from_proposals_dir reads proposals.json and each referenced file with unguarded read_text() calls

**Choice**: settled-deferral

**Rationale**: Confirmed pre-existing: docket.py lines 203 and 211 are unchanged by this diff. The surgical-changes rule forbids fixing adjacent pre-existing code. Recorded in the settled-decisions ledger.

### [autonomous] 2026-09-06T00:06:55Z

**Decision**: Bob could not statically verify that the reported checks pass (uv run pytest, validate_skill.py, braid --check)

**Choice**: resolved-no-action

**Rationale**: All three commands ran green at this exact HEAD 45a0adf5 per dev/local/autopilot/last-verification.json (each exit 0). Blake and Carl each independently re-ran the distil-memory suite and validate_skill.py this cycle. Not queued for verification: bob.md defines no VERIFY bucket and Eve did not run, so no checks-1.json was written.

### [autonomous] 2026-09-06T00:06:55Z

**Decision**: Alice named conftest.py as the home for the deduplicated _proposal() test helper

**Choice**: auto-fix, mechanism changed

**Rationale**: Fix the finding (the duplication) but not by her mechanism. The convention in skills/distil-memory/scripts/ is a plain <area>_test_helpers.py module imported directly: distil_test_helpers.py and funnel_test_helpers.py already sit beside these tests and are imported by eight test files, while the whole repo holds exactly one conftest.py, in a different skill. Matching the surrounding code wins over a reviewer suggested file name. Task 5 body updated to name docket_test_helpers.py.

### [autonomous] 2026-09-06T00:06:55Z
