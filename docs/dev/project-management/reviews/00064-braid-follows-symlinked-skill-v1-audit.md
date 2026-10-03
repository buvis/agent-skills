# Decision Audit Log: 00064-braid-follows-symlinked-skill-v1

PRD: `00064-braid-follows-symlinked-skill-v1.md`
Started: 2026-09-26T15:09:28Z
Completed: 2026-09-26T15:09:28Z
Autonomous: 3  |  Deferred: 0  |  Doubts: 0

### [autonomous] 2026-09-26T15:09:28Z

**Decision**: Symlink guard lands after the pre-existing is_dir() check, not before it as the PRD contract states verbatim (Alice+Bob, 2/4, medium; Bob fails R9 on it)

**Choice**: auto-fix - swept by the converged cycle single [D1] Tail sweep task

**Rationale**: Medium with a clear mechanical fix: move the two guard lines above the existing name/is_dir condition. Behaviourally equivalent today - Alice, Blake and Bob each traced symlink-to-dir, symlink-to-non-dir and broken-symlink and agree the outcome is identical either way - so it does not block convergence. Worth fixing anyway: the PRD names the position verbatim in both its Solution section and the task acceptance criterion, and for a PRD whose whole point is not following symlinks, not calling is_dir() through the link at all is strictly closer to the intent than skipping afterwards.

### [autonomous] 2026-09-26T15:09:28Z

**Decision**: Cannot statically verify: uv run pytest tests -q reports zero failures (Bob, 1/4, low)

**Choice**: routed to verification - queued as the command: uv run pytest tests -q, in dev/local/reviews/00064-braid-follows-symlinked-skill-v1-checks-1.json (source bob)

**Rationale**: A Medium/Low finding whose named check is one exact runnable command is routed, not auto-fixed and not tasked: the check runs inside the tail sweep work phase step-7 verification pass, where a task would have re-run the same suite anyway. Bob is sandboxed and cannot execute, so this is a lens limit rather than a defect. Already answered live this cycle: Alice ran the braid test file (12 passed, 3 xfailed), Blake ran the tests dir (155 passed, 0 failed), Carl ran the full suite, and the recorded work-phase run at this same HEAD reports 3474 passed, 0 failed.

### [autonomous] 2026-09-26T15:09:28Z

**Decision**: Cannot statically verify: the dry-run reproduction emits no WOULD LINK line for the symlinked skill (Bob, 1/4, low)

**Choice**: discarded with a verified reason - resolved this cycle by live evidence, no task and no deferral

**Rationale**: Not queued: the check needs scratch-tree setup plus a stdout assertion, which is not the single-runnable-command shape the verification queue accepts, so it could not be routed. Resolved rather than dropped: Alice and Blake each executed the PRD reproduction independently in separate scratch trees this same cycle, and both report the symlinked skill absent from the dry-run output (Blake counted 76 WOULD LINK lines, none naming evil or outside; exit 0, nothing written). The assertion Bob could not make statically was made twice, live, and is recorded in the review file. Appended to the settled-decisions ledger so it is not re-argued.
