---
default_model: sonnet
rework_cap: 5
design: skip
---

# A localStorage failure blanks the whole brief with no message

## Problem

`skills/brief-portfolio/app/src/App.svelte:28` calls `pruneDone(...)` during
component init, which reaches `localStorage.getItem` at
`skills/brief-portfolio/app/src/lib/done.js:5`. The throw lands before any
render, so even the `{#if !payload}` fallback never mounts and the page is
white with an empty console. The product ships as one HTML file opened from
disk, and mainstream browsers throw `SecurityError` from `localStorage` when the
user blocks site data. Both smoke suites pin `url: 'https://example.org/'`
(`smoke.test.js:44-47`), so the failing origin is the one case the tests
exclude. Source: agoge run `dev/local/audit-results/agoge-2026-08-31.md`,
finding 9 (HIGH, ux lane, status mocked - jsdom opaque-origin stand-in, real
browser trigger rate unmeasured); decision 2026-09-02: wrap the two storage
helpers and show a persistence notice.

```
Same file, same payload, two mounts: with url: 'https://example.org/' ->
rendered chars: 2518; with jsdom's default opaque origin ->
thrown at eval: localStorage is not available for opaque origins,
jsdomErrors: [], rendered chars: 0, visible text: "".
```

## Solution

Wrap the two statements in `done.js` in try/catch: `loadDone` returns an empty
`Set`, `saveDone` becomes a no-op, and both record that storage is unusable. The
same catch also absorbs a corrupt stored value, which `JSON.parse` would
otherwise throw on. `App.svelte` reads the flag once after the `pruneDone` call
and renders a one-line notice above the tabs. No error boundary: that broader
option was declined, this is the narrow fix.

## Requirements

### Must have

- `loadDone()` returns an empty `Set` instead of throwing when `localStorage` is
  unreachable.
- `saveDone()` returns without throwing when `localStorage` is unreachable.
- `done.js` exposes `isStorageBlocked()`, true once either helper has
  caught.
- With storage blocked the page renders the header, the tabs and the Brief tab,
  plus a one-line notice reading `Checked state will not persist: this browser
  is blocking local storage.`.
- `smoke.test.js`'s `render()` takes the jsdom `url` as an option so a test can
  mount on the default opaque origin.

### Nice to have

- none

## Implementation

### Module: done.js

- **Location**: `skills/brief-portfolio/app/src/lib/`
- **Responsibility**: Hold checked-todo state, and survive a browser that
  refuses storage.
- **Exports**: `loadDone()`, `saveDone()`, `pruneDone()`, `isStorageBlocked()`

### Module: App.svelte

- **Location**: `skills/brief-portfolio/app/src/`
- **Responsibility**: Render the persistence notice when storage is blocked.
- **Exports**: `App` component

### Module: smoke.test.js

- **Location**: `skills/brief-portfolio/app/`
- **Responsibility**: Mount the app on the opaque origin the suite excludes
  today and assert the page still renders.
- **Exports**: `render(payload, options)`, `node --test` cases

### Dependencies

- done.js: No dependencies (foundation)
- App.svelte: Depends on [done.js]
- smoke.test.js: Depends on [done.js, App.svelte]

## Tasks

### Phase 0: Foundation

- [ ] Wrap the `localStorage` calls in `done.js:5-6` in try/catch and add `isStorageBlocked()` - Acceptance: a new `node --test` case in `skills/brief-portfolio/app/smoke.test.js` sets `globalThis.localStorage = { getItem() { throw new Error('SecurityError') }, setItem() { throw new Error('SecurityError') } }`, then `await import('./src/lib/done.js')`, and asserts `loadDone().size === 0`, that `saveDone(new Set(['x']))` does not throw, and `isStorageBlocked() === true`, restoring the previous global in a `finally`; `npm --prefix skills/brief-portfolio/app test` passes with 17 tests.
- [ ] Give `smoke.test.js`'s `render()` an options argument that controls the jsdom `url` - Acceptance: `render(payload, { url: null })` omits the `url` option from the `JSDOM` constructor and `render(payload)` still passes `url: 'https://example.org/'`; `npm --prefix skills/brief-portfolio/app test` reports 0 failing tests with every existing `render(` call site unchanged.

### Phase 1: Core

- [ ] Render the persistence notice in `App.svelte` when `isStorageBlocked()` is true (depends on: Phase 0) - Acceptance: after `npm --prefix skills/brief-portfolio/app run build` and `cp skills/brief-portfolio/app/dist/index.html skills/brief-portfolio/assets/template.html`, `npm --prefix skills/brief-portfolio/app test` passes; a new test mounting with the jsdom default opaque origin asserts `doc.querySelector('h1').textContent.trim() === 'Portfolio Brief'`, `doc.querySelector('main').textContent.trim().length > 0`, and `doc.body.textContent` matches `/will not persist/`.

## Success Criteria

- `npm --prefix skills/brief-portfolio/app test` reports 18 passing tests and 0
  failing, up from 16.
- The opaque-origin mount renders more than 0 characters, against `rendered
  chars: 0` today.
- `rg -n "url: 'https://example.org/'" skills/brief-portfolio/app/smoke.test.js`
  still matches, so every existing test keeps its real origin.
- Human follow-up, not a task: which real browsers throw here is unconfirmed,
  so the jsdom opaque origin stays a stand-in for blocked site data.

## Post-completion notes (2026-09-05)

- The "18 passing tests, up from 16" criterion was stale at review: the suite
  reported 20 passing, 0 failing, because two extra regression tests pin the
  task 2 `render(payload, { url })` contract. The named tests supersede the
  count. Deferred by batch 202609040601 (cycle 1, consensus 2/3), decided
  2026-09-05 in the agoge-2026-09-05 walkthrough: record here, and the
  create-prd metric rule now forbids pinning suite totals.
