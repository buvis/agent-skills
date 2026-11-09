# Decision Audit Log: 00117-four-scripts-ignore-help-v1

PRD: `00117-four-scripts-ignore-help-v1.md`
Started: 2026-10-29T16:26:22Z
Completed: 2026-10-29T16:26:22Z
Autonomous: 4  |  Deferred: 0  |  Doubts: 0

### [autonomous] 2026-10-29T16:26:22Z

**Decision**: `test_help_flag_does_not_create_any_output_artifact` passes against the pre-change code, and the fail-first replay flags it. It only lists an empty `tmp_path` before and after, so it cannot tell help from a survey. The old `run.py` also writes nothing, so a regression that wrote a file on help is the only way it could fail. Pin it instead by running `-h` in a directory with a source file and asserting stdout has no brief, which is already covered. Alternatively, drop it and the "artifact" comment, which wrongly says the brief goes "anywhere" other than stdout.

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-29T16:26:22Z

**Decision**: Cycle 1 converged with 17 findings, none critical or high: R1 (tautological test_help_flag_does_not_create_any_output_artifact, raised by Alice and confirmed by the fail-first replay) swept into tail-sweep task 2

**Choice**: tail sweep: 1 finding, 1 task

**Rationale**: no unresolved CRITICAL/HIGH and the doubt-roster constraint gate certified, so the review-rework loop converged; the medium/low tail is swept rather than dropped

### [autonomous] 2026-10-29T16:26:22Z

**Decision**: R2-R14: thirteen single-voice medium/low rows (Consensus [1/3]) from Alice, Bob and Blake, including Blake's six clean-bill observations

**Choice**: discarded

**Rationale**: single-voice: the Phase 5 classification rule discards a medium or low raised by one reviewer, never a task; each is appended to the settled-decisions ledger so a re-raise is auto-dismissed

### [autonomous] 2026-10-29T16:26:22Z

**Decision**: R15-R17: the fail-first replay reports that the three review-helper test files' preservation tests pass against the pre-change code

**Choice**: discarded

**Rationale**: behavior-preserving: these are the PRD's own normal-invocation and error-behavior preservation tests, so passing against base is the designed shape the replay block documents, not unpinned behavior
