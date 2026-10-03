---
default_model: opus
model_tier_rationale: the change alters when the announcement window fires and the test polls a timing window; timing determines correctness, which the authoring rubric places at the opus floor even though the names and defaults are given
design: skip
---

# The smoke suite spends 2.2 of its 4.5 seconds sleeping through one announcement window

## Problem

`skills/brief-portfolio/app/smoke.todos.status.test.js` line 204, `A newer status
announcement survives an older one's 1500ms expiry, and still clears once its
own window elapses`, sleeps real time in three steps (500 + 1200 + 500 ms)
because the announcement window is the literal `1500` in `announce()` at
`Todos.svelte` line 58 (`outcomeTimer = setTimeout(() => (outcome = null),
1500)`), which the test cannot see or shorten; its own comment says fake timers
would mean guessing how many timers the page keeps. That one test is about
half the suite's wall clock and the floor under every timing criterion anyone
writes for it (PRD 00033's missed one included). Source: batch 202609040601
deferred item 7 (HIGH, cycle 2 of PRD 00033); decision 2026-09-05: make the
window injectable and poll.

```
node --test: the suite is 44 tests at about 4543 ms; this test alone is about
2221 ms of real sleeping; the next slowest test is under 200 ms.
```

## Solution

`Todos.svelte` reads the window once at module init:
`const ANNOUNCE_MS = globalThis.__PORTFOLIO_ANNOUNCE_MS ?? 1500`, and
`announce()` uses `ANNOUNCE_MS` instead of the literal. `render()` in
`smoke.harness.js` takes an `announceMs` option and, when given, sets
`dom.window.__PORTFOLIO_ANNOUNCE_MS = announceMs` before
`dom.window.eval(bundle)`: the harness already evaluates the bundle itself, so
a global on the window is the one channel a test has into the page. The
line-204 test renders with `{ announceMs: 40 }` and replaces its three sleeps
with `waitFor` polls using the render's `flush`. The assertions keep their
meaning: a newer announcement outlives the older one's expiry, and clears after
its own. A test-only global in production code was the option's named
drawback.

## Requirements

### Must have

- With `__PORTFOLIO_ANNOUNCE_MS` unset the built page behaves exactly as today
  (1500 ms); the existing copy-label tests pass unchanged.
- `render(payload, { announceMs })` drives the window; `render(payload)` sets
  nothing on the window.
- The line-204 test finishes in under 300 ms and still fails if the newer
  announcement is cleared by the older timer (verify by keeping the 40ms injection and temporarily removing
  clearTimeout(outcomeTimer), rebuilding, and observing the older-timer
  survival assertion fail; then restore/rebuild and record both runs).
- No other test changes.

### Nice to have

- none

## Implementation

### Module: Todos.svelte

- **Location**: `skills/brief-portfolio/app/src/components/`
- **Responsibility**: Read the announcement window from the global, default 1500.
- **Exports**: component, props unchanged

### Module: smoke.harness.js and smoke.todos.status.test.js

- **Location**: `skills/brief-portfolio/app/`
- **Responsibility**: Set the global before mounting; poll instead of sleeping.
- **Exports**: `render(payload, { url, announceMs })`, `node --test` cases

### Dependencies

- Todos.svelte: No dependencies (foundation)
- smoke.harness.js: Depends on [Todos.svelte's global]
- smoke.todos.status.test.js: Depends on [smoke.harness.js]

## Tasks

### Phase 0: Foundation

- [ ] Replace the literal with `ANNOUNCE_MS` in `Todos.svelte`, then `npm --prefix skills/brief-portfolio/app run build` and `cp skills/brief-portfolio/app/dist/index.html skills/brief-portfolio/assets/template.html` - Acceptance: `rg -n "__PORTFOLIO_ANNOUNCE_MS" skills/brief-portfolio/app/src/components/Todos.svelte skills/brief-portfolio/assets/template.html` matches both files, `rg -c "1500" skills/brief-portfolio/app/src/components/Todos.svelte` prints 1, and `npm --prefix skills/brief-portfolio/app test` reports 0 failing with no test edited.

### Phase 1: Core

- [ ] Add the `announceMs` option to `render()` and rewrite the line-204 test to poll (depends on: Phase 0) - Acceptance: the named announcement-expiry test contains no fixed await-sleep calls, located by name in `smoke.todos.status.test.js`; the `node --test` `duration_ms` for that test is under 300; removing previous-timer cancellation while retaining the short injected window makes the survival assertion fail (not merely a deadline assertion), then restoring/rebuilding makes it pass; normal expiry is also asserted (output recorded); `npm --prefix skills/brief-portfolio/app test` reports 0 failing.

## Success Criteria

- That test's `duration_ms` drops from about 2221 to under 300.
- Every other test passes unchanged, and a page built with the global unset
  keeps the 1500 ms window.
