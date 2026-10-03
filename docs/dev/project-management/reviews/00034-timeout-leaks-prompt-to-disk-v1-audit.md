# Decision Audit Log: 00034-timeout-leaks-prompt-to-disk-v1

PRD: `00034-timeout-leaks-prompt-to-disk-v1.md`
Started: 2026-09-06T23:59:30Z
Completed: 2026-09-06T23:59:30Z
Autonomous: 5  |  Deferred: 0  |  Doubts: 0

### [autonomous] 2026-09-06T23:59:30Z

**Decision**: [FIX] The direct timeout unit at test_funnel_distil_dedup.py:385-398 duplicates the end-to-end regression at 43-63; remove it

**Choice**: settled-deferral

**Rationale**: Cycle 1: kept the test. Not duplicate coverage - the E2E pins the message through funnel.main with the real prompt, the direct unit pins the same contract at _type_proposal own boundary with a 500-char synthetic argv the E2E cannot produce, which is the exact leak vector the PRD describes. It is also the timeout member of a trio whose other two members pin PRD Must-have #2 and cannot be removed. Both hand-verified to FAIL against base 19cbdf7. Alice reviewed the same code and judged the extra tests legitimate. Recorded in the settled-decisions ledger so Bob does not re-raise it.

### [autonomous] 2026-09-06T23:59:30Z

**Decision**: [FIX] The RuntimeError and OSError tests repeat identical setup and assertions; replace them with one parametrized test over both exception types

**Choice**: auto-fix

**Rationale**: Cycle 1: medium with a clear mechanical fix, behavior-preserving. Two 9-line tests differ only in the exception type. Swept into the converged cycle tail-sweep task [D1].

### [autonomous] 2026-09-06T23:59:30Z

**Decision**: CHANGELOG.md [Unreleased]/Fixed has no entry for this typing-timeout fix

**Choice**: auto-fix

**Rationale**: Cycle 1: rule-mandated, not discretionary. rules/changelog.md is a BLOCKING rule requiring every fix commit with a user-visible change to update CHANGELOG.md in the same commit. Verified 361d9c9 is fix(distil-memory) and touched only funnel.py. Swept into the converged cycle tail-sweep task [D1].

### [autonomous] 2026-09-06T23:59:30Z

**Decision**: [KNOWN] RuntimeError still persists raw claude stderr in dedup_error, leaving an unexamined disclosure boundary

**Choice**: settled-deferral

**Rationale**: Cycle 1: out of scope by specification. Bob filed it KNOWN himself. PRD Must-have #2 requires this branch unchanged and Must-have #4 requires the new test docstring to name it as a known unexamined boundary, which it does. Recorded in the settled-decisions ledger; a future PRD can examine the stderr path.

### [autonomous] 2026-09-06T23:59:30Z

**Decision**: [VERIFY] Cannot statically verify the mandated checks; run uv run pytest, validate_skill.py skills/distil-memory, and braid --check

**Choice**: routed to verification

**Rationale**: Cycle 1: NOT queued, for two independent reasons - it names three commands and a queue entry must be one command with no chaining, and those same three commands are already recorded in dev/local/autopilot/last-verification.json at this exact HEAD b542182 with exit 0 each. Nothing left for a runner to resolve. Eve did not run and agents/bob.md defines no VERIFY bucket, so source bob is reserved and no entry could be sourced from him regardless.
