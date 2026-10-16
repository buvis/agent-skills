# Decision Audit Log: 00076-distil-tests-see-non-atomic-writes-v1

PRD: `00076-distil-tests-see-non-atomic-writes-v1.md`
Started: 2026-10-16T20:14:08Z
Completed: 2026-10-16T20:14:08Z
Autonomous: 9  |  Deferred: 0  |  Doubts: 0

### [autonomous] 2026-10-16T20:14:08Z

**Decision**: The rewritten rollback-failure assertion (`all(index_fault in line or rollback_fault in line ...)`) still passes if production appends a "rolled back" claim to the same stderr line as one of the two faults. It catches only a separate extra line. Today's messages are separate lines, so no live defect. Assert that each fault appears and that the line count equals the number of faults, or assert on a fixed phrase list

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-16T20:14:08Z

**Decision**: test_main_write_reports_both_the_pointer_error_and_the_rollback_error_when_restoring_an_updated_target_fails (the second rollback-failure test) never asserts that no restoration is claimed. Only the first rollback-failure test got the "every stderr line carries one of the two faults" check. The spec asks that the rollback-failure assertion bind "both errors reported, no restoration claimed". `"rolled back" not in` is gone from the whole directory, so the Phase 2 acceptance rg passes, but the sibling test is looser than its twin.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-16T20:14:08Z

**Decision**: The new `is_dir()` guard prints "no such directory" when `--proposals-dir` exists but is a regular file. The message is then wrong, though the exit code and the named path are right. Use a neutral "not a directory" or "cannot read" wording

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-16T20:14:08Z

**Decision**: The new is_dir() refusal line in docket.py is 105 chars. ruff E501 (limit 100) flags it. Neighbouring lines already violate it, so this is consistent with the file, but it adds one more violation.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-16T20:14:08Z

**Decision**: test_decide_reads_the_file_once counts only Path.read_text calls on the note. A second read through read_bytes(), open() or io.open() slips past it. The read-count pin is narrower than the "read exactly once" requirement implies.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-16T20:14:08Z

**Decision**: R3: atomicity module re-declares _REAL_REPLACE and _run_write

**Choice**: rejected (cycle 1)

**Rationale**: no defect; sharing a one-line constant across test modules adds coupling for no behaviour change

### [autonomous] 2026-10-16T20:14:08Z

**Decision**: R7: test_main_start_returns_zero name no longer says what it enforces

**Choice**: rejected (cycle 1)

**Rationale**: PRD Must-have forbids renaming existing tests

### [autonomous] 2026-10-16T20:14:08Z

**Decision**: R8: _save_from_proposals_dir lets UnicodeDecodeError and KeyError through as tracebacks

**Choice**: settled-deferral to PRD 00077 (cycle 1)

**Rationale**: pre-existing; record-shape refusals are PRD 00077 scope, next on this branch

### [autonomous] 2026-10-16T20:14:08Z

**Decision**: R9-R13: [MECH] touched tests pass against pre-change code

**Choice**: dismissed (cycle 1)

**Rationale**: test-only PRD pins existing correct behaviour by design; named mutants verified red by Alice, Blake and the commit bodies
