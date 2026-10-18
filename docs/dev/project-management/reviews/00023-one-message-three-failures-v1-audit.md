# Decision Audit Log: 00023-one-message-three-failures-v1

PRD: `00023-one-message-three-failures-v1.md`
Started: 2026-10-18T09:32:54Z
Completed: 2026-10-18T09:32:54Z
Autonomous: 6  |  Deferred: 0  |  Doubts: 0

### [autonomous] 2026-10-18T09:32:54Z

**Decision**: design loadPayload() error classification for 3 fallback causes

**Choice**: loadPayload() returns {payload,error} with kinds not-built/unreadable(reason); App.svelte renders per-kind fallback; renderRaw test helper shares mount() with render()

**Rationale**: single-pass classification avoids re-reading the DOM node and matches the PRD acceptance commands exactly; 2 Claude+codex review dispatches found 0 cardinal-sin/blocker (5 non-blocker, 2 question, all recorded in the design doc review log, none requiring a fix)

### [autonomous] 2026-10-18T09:32:54Z

**Decision**: R4: the not-built smoke test passes against pre-change code (deliberate regression pin, Alice says keep it)

**Choice**: no change needed

**Rationale**: the raiser explicitly recommends keeping the test; it pins that the new unreadable branch does not swallow the not-built case, and the other two new smoke tests do demonstrate the change

### [autonomous] 2026-10-18T09:32:54Z

**Decision**: R5: derive.test.js adds coverage beyond the three tests the PRD names

**Choice**: no change needed

**Rationale**: Blake calls it test-only and harmless; the extra cases (null turns, marker inside turn text) pin real loader behaviour and removing them would reduce coverage

### [autonomous] 2026-10-18T09:32:54Z

**Decision**: PRD Success Criteria require the suite to assert that the unreadable message contains neither `build.py` nor `Re-run`, and that the three texts differ. Neither is asserted. The structural-payload test only does a regex match for `unreadable: missing transcript.turns`, so it would still pass if the sentence also advised re-running the build. Add `assert.doesNotMatch(text, /build\.py|Re-run/)` to the two unreadable tests, plus one assertion that the three rendered texts are distinct

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T09:32:54Z

**Decision**: The parser-message test in `derive.test.js` asserts `assert.match(error.reason, /JSON|Unexpected|Unterminated/)`. That is an either-or hedge that depends on the JS engine's wording. Compute the expected message with a `JSON.parse` catch, as the smoke test does, and use `assert.equal`

**Choice**: auto-fixed

**Rationale**: fixed by review-close

### [autonomous] 2026-10-18T09:32:54Z

**Decision**: `setPayloadNodeText` assigns `globalThis.document` and never restores it, so the stub leaks into every later test in the file. The run passes today because the other tests do not touch `document`. Save the previous value and restore it in an `after` hook

**Choice**: auto-fixed

**Rationale**: fixed by review-close
