---
default_model: sonnet
rework_cap: 5
catchup: skip
design: skip
---

# The node smoke suite spends 77% of its time in one hardcoded sleep

## Problem

`skills/brief-portfolio/app/smoke.test.js:398` waits a fixed 1600ms of wall
clock (`await new Promise((resolve) => setTimeout(resolve, 1600))`) to outlast
the 1.5s reset timer in `Todos.svelte:61`, then asserts at lines 400-408 that
the button label reverted and the `aria-live` region is empty. That single test
costs 1617ms of a 2090ms suite, 5.36x the other 15 tests combined. The sleep is
deliberate - the comment at lines 396-397 names the trade-off - but it also
sets the failure bound at 100ms of slack, so a slow machine turns a correct
component into a red test. Source: agoge run
`dev/local/audit-results/agoge-2026-08-31.md`, finding 28 (MEDIUM, performance
lane, verified, reproduced twice); decision 2026-09-02: poll for the reverted
label with a deadline instead of sleeping past it.

```
The test took 1617.86ms and 1617.10ms of a 2090ms / 2086ms suite - 77.4% and
77.5%. The other 15 tests sum to 301.70ms. The comment at the sleep names the
tradeoff, so it was deliberate.
```

## Solution

Replace the fixed sleep with a poll: a small helper that flushes, checks the
label, and retries on an interval until it reverts, failing only at a deadline
comfortably above the component's 1500ms timer. The assertions stay exactly as
they are. No production code changes: the injectable-delay option was declined.

## Requirements

### Must have

- `smoke.test.js` gains `waitFor(predicate, { timeout = 3000, interval = 25 })`, which awaits `flush()` and the interval between checks and throws
  a named assertion error at the deadline.
- The test at lines 377-409 waits with `waitFor` instead of the 1600ms sleep,
  and its two assertions are byte-identical to today's.
- No source file under `skills/brief-portfolio/app/src/` changes, so no template
  rebuild is needed.

### Nice to have

- Clamp long `setTimeout` delays on the jsdom window inside `render()` (test-only,
  still no production change) so the component's 1500ms reset fires in
  milliseconds. This is the only route to the "suite toward ~0.5s" number: the
  poll alone cannot beat 1500ms, because that timer runs in real time.

## Implementation

### Module: smoke.test.js

- **Location**: `skills/brief-portfolio/app/`
- **Responsibility**: Wait for a rendered condition with a deadline instead of
  sleeping past a known timer.
- **Exports**: `waitFor()`, `node --test` cases

### Dependencies

- smoke.test.js: No dependencies (foundation)

## Tasks

### Phase 0: Foundation

- [ ] Add the `waitFor(predicate, options)` helper beside `render()` in `smoke.test.js` - Acceptance: `rg -n "async function waitFor" skills/brief-portfolio/app/smoke.test.js` matches exactly once, that signature defaults to `timeout = 3000` and `interval = 25`, the body throws an `Error` naming the timeout when the deadline passes, and `npm --prefix skills/brief-portfolio/app test` reports 16 passing tests and 0 failing.
- [ ] Replace the 1600ms sleep in the `aria-live region clears once the failed-copy button label has reverted` test with `await waitFor(() => button.textContent.trim() === 'copy open as markdown')` - Acceptance: `npm --prefix skills/brief-portfolio/app test` reports 16 passing tests and 0 failing; `rg -n "setTimeout\(resolve, 1600\)" skills/brief-portfolio/app/smoke.test.js` prints nothing and exits 1; the two assertions after the wait still compare the label to `copy open as markdown` and the `[aria-live="polite"]` text to `''`.

## Success Criteria

- `npm --prefix skills/brief-portfolio/app test` reports 16 passing tests and 0
  failing, with no test file added or removed.
- The `node --test` `duration_ms` for that test drops below 1600ms, from
  1617ms, and the suite total drops below 2050ms from 2090ms.
- The failure bound rises from 100ms of slack over the 1500ms timer to 1500ms,
  so a slow machine no longer reddens a correct component.
- Correction to the finding's own arithmetic, verified in
  `Todos.svelte:61`: the 1500ms reset is real wall clock inside the component,
  so polling saves roughly 117ms, not 1.6s. The report's "~0.5s suite" needs
  the nice-to-have timer clamp, which was not part of the accepted decision.

## Post-completion notes (2026-09-05)

Deferred by batch 202609040601 (cycles 1 to 3), decided 2026-09-05 in the
agoge-2026-09-05 walkthrough.

- "16 passing tests" was stale before this PRD started: the suite reported 41
  passing at cc39e7e~1. "Suite total below 2050ms" cannot be met: the suite is
  44 tests at about 4.5 s, dominated by the 2.2 s real-time test at
  `smoke.test.js:807`, which PRD 00069 now owns. The criterion this PRD
  governs, its own test under 1600 ms, is met (1617 ms to about 1524 ms). The
  create-prd metric rule now forbids pinning suite totals.
- The must-have named `waitFor(predicate, { timeout = 3000, interval = 25 })`
  while requiring the helper to await `flush()`; `flush` is a per-render
  closure, so the shipped helper takes it as a third optional option
  (`{ timeout, interval, flush }`) with both documented defaults unchanged.
  This note corrects the PRD text; the code stands.
- Commit a5d9c48 is typed `fix` but is test-only. Left as is, no CHANGELOG
  bullet (agoge-2026-09-05 finding 18, rejected: rewording a published master
  needs a force push).
