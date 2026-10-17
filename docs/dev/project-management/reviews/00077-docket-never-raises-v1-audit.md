# Decision Audit Log: 00077-docket-never-raises-v1

PRD: `00077-docket-never-raises-v1.md`
Started: 2026-10-17T07:41:52Z
Completed: 2026-10-17T07:41:52Z
Autonomous: 10  |  Deferred: 0  |  Doubts: 0

### [autonomous] 2026-10-17T07:41:52Z

**Decision**: plan: where 00077 tests live and task ordering

**Choice**: new test_docket_never_raises.py; task 2 blocked_by task 1; refusals worded `invalid proposals schema in <path>: ... position <i>` (0-based, mirrors _check_entry)

**Rationale**: test_docket_refusals.py is 746 lines and the PRD says split near 800; tasks 1 and 2 share docket.py and the new test module

### [autonomous] 2026-10-17T07:41:52Z

**Decision**: CHANGELOG placement: PRD put the entry in task 3, but rules/changelog.md blocks a fix commit without one

**Choice**: added the distil-memory Fixed bullets in the task 1 and task 2 fix commits; task 3 only edited SKILL.md and verified the CHANGELOG

**Rationale**: blocking changelog rule; same user-visible result

### [autonomous] 2026-10-17T07:41:52Z

**Decision**: R1+R2: a six-key record whose `file` is not a string (null or a number) still raises TypeError at `proposals_dir / record["file"]`; `transcript` and `line_no` types also unchecked

**Choice**: auto-fix via tail sweep: `_check_batch` also refuses wrong-typed record values naming the position; regression tests added

**Rationale**: Medium, additive validation at the boundary plus tests; inside the PRD success criterion that no route prints a traceback (review cycle 1)

### [autonomous] 2026-10-17T07:41:52Z

**Decision**: R3: tests do not pin whole-batch validation before sibling reads (an interleaved implementation would also pass)

**Choice**: auto-fix via tail sweep: add a test with a missing first sibling and a later record missing `evidence_text`, asserting the schema error for position 2 wins and no queue is written

**Rationale**: Medium, additive test binding to the PRD contract that validation runs before any sibling read (review cycle 1)

### [autonomous] 2026-10-17T07:41:52Z

**Decision**: R4: `_save_queue` leaves a `.tmp` file behind when `tmp.write_text` fails before the rename

**Choice**: auto-fix via tail sweep: unlink the temp file on OSError and re-raise, with a regression test

**Rationale**: Low, three-line additive cleanup; the queue-bytes-unchanged contract is unaffected (review cycle 1)

### [autonomous] 2026-10-17T07:41:52Z

**Decision**: R5: the nine new tests live in test_docket_never_raises.py, not the PRD-named test_docket_refusals.py

**Choice**: discard; ledgered as discarded so Blake's re-raise is auto-dismissed next cycle

**Rationale**: PRD-sanctioned: the PRD module note says split if it nears 800 lines, the module is 746 lines, and the plan-time decision above chose a new module; all nine spec-named tests exist (review cycle 1)

### [autonomous] 2026-10-17T07:41:52Z

**Decision**: `save --proposals-dir` still raises a traceback when a record has all six keys but a wrong-typed `file`. A `file` of `null` or a number reaches `proposals_dir / record["file"]` and raises TypeError, which the `(OSError, ValueError)` guard does not catch. I reproduced it with `file: null`: TypeError at docket.py:300, no exit code. This falls just outside the PRD's literal "six keys present" contract but inside its success criterion that the route prints no traceback. Suggested fix: have `_check_batch` also require `isinstance(record["file"], str)` and refuse with a message such as `the record at position {i} has a file that is not a string`. Add a test for it.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-17T07:41:52Z

**Decision**: A record with the right keys but a non-string `file` (for example `"file": 5` or `null`) still raises an uncaught TypeError at `proposals_dir / record["file"]` (I reproduced the traceback). The spec's goal is that none of these routes print a traceback, though its named cases cover only missing keys, so this is a gap in the spirit of the spec. `transcript` and `line_no` types also go unchecked, and a non-string `transcript` can fail later in `slice_key`/`save`.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-17T07:41:52Z

**Decision**: Tests do not pin whole-batch validation before sibling reads: the later-invalid-record test supplies every sibling, so validation interleaved with reads would also pass. Add a case with an unreadable first sibling and a later malformed record; assert the later record's schema error wins and no queue is written.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-17T07:41:52Z

**Decision**: Failure before the rename can leave a `.tmp` queue file behind: `_save_queue` has no cleanup if `tmp.write_text` partially writes. The queue itself is unchanged, so this meets "queue bytes unchanged" and is only residue.

**Choice**: auto-fixed

**Rationale**: fixed by review-close
