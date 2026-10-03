# Decision Audit Log: 00059-build-dies-on-torn-inputs-v1

PRD: `00059-build-dies-on-torn-inputs-v1.md`
Started: 2026-09-26T06:51:43Z
Completed: 2026-09-26T06:51:43Z
Autonomous: 7  |  Deferred: 0  |  Doubts: 0

### [autonomous] 2026-09-26T06:51:43Z

**Decision**: Stale comment at test_build_page.py:79 still describes the two strict xfail markers this PRD deleted

**Choice**: auto-fix (swept into the [D1] Tail sweep task)

**Rationale**: Review cycle 1: Medium with a clear mechanical fix, 2/4 consensus (Alice and Bob named the same comment). Swept verbatim into the single [D1] Tail sweep task.

### [autonomous] 2026-09-26T06:51:43Z

**Decision**: _load_data and _load_epics repeat the identical decode-or-exit shape; extract a two-caller _load_json_or_exit helper

**Choice**: auto-fix (swept into the [D1] Tail sweep task)

**Rationale**: Review cycle 1: Medium, behavior-preserving simplification per the review-dimensions rule. The task instruction forbids sharing one try block across both loads, not extracting a helper, and finding 3 gives that helper a third caller.

### [autonomous] 2026-09-26T06:51:43Z

**Decision**: data-prev.json is read with a bare json.loads at build.py:39, so a malformed one still crashes the build with a traceback

**Choice**: auto-fix (swept into the [D1] Tail sweep task)

**Rationale**: Review cycle 1: Medium, the finding behind Blake B14 fail. Fix is additive only (a guard plus a test), it closes the same failure class this PRD exists to close, no backlog PRD owns it (00060 covers the collect-side tear, 00065 rewrites only the history read, 00057 covers data-prev permissions), and the sweep already edits the function that reads it. Fixed now rather than deferred.

### [autonomous] 2026-09-26T06:51:43Z

**Decision**: the data.json and epics.json tests assert only a basename inside the caught SystemExit, pinning neither the decode reason nor the absence of a traceback

**Choice**: auto-fix (swept into the [D1] Tail sweep task)

**Rationale**: Review cycle 1: Medium, additive test strengthening. The PRD acceptance criterion names both stderr containing the file name and no Traceback, so the current assert is weaker than the criterion it claims to pin.

### [autonomous] 2026-09-26T06:51:43Z

**Decision**: test_a_malformed_line_outside_the_last_60_window_is_not_decoded_or_warned_about passes against the pre-change code, so it does not pin this change

**Choice**: auto-fix (swept into the [D1] Tail sweep task)

**Rationale**: Review cycle 1: Medium, raised by Bob and independently by the computed fail-first replay (mech-check), so it cannot be waved past. Alice argued it pins the retention rule the PRD explicitly preserves; Bob names a strictly better shape that keeps the no-backfill check and also fails first (one out-of-window malformed row plus one selected malformed row, asserting only the selected row warns). Strengthened rather than dismissed.

### [autonomous] 2026-09-26T06:51:43Z

**Decision**: delete the 30-line two-build comparison test as redundant with the len(history) == 1 assertion

**Choice**: discarded (recorded in the settled-decisions ledger)

**Rationale**: Review cycle 1: test_a_torn_history_line_yields_one_fewer_trend_point is the only direct pin of the PRD Must-have that the trend series has one point fewer, because it compares a healthy build against a torn one; len(history) == 1 in the sibling test proves that only implicitly. Deleting a test that binds to a stated requirement to save 30 lines is what rules/testing.md forbids, so the de-slop suggestion loses to the requirement.

### [autonomous] 2026-09-26T06:51:43Z

**Decision**: _load_history also reads data-prev.json and returns it as an unrelated tuple member, blurring the per-input loader boundary

**Choice**: auto-fix (swept into the [D1] Tail sweep task)

**Rationale**: Review cycle 1: Medium, behavior-preserving structural cleanup that pairs with finding 3, since the same prev load is the one needing a guard.
