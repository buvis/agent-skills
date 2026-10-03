---
default_model: opus
rework_cap: 5
---

# The Brief's gravity field gives keyboard users a bare repo name

## Problem

Each node in the landing tab's gravity field is focusable and clickable
(`skills/brief-portfolio/app/src/components/Horizon.svelte:96-97`,
`role="button" tabindex="0"`), but its whole content reaches the mouse only: the
tooltip is wired to `onmouseenter`/`onmouseleave` at lines 102-103 with no focus
counterpart, and the `aria-label` at line 98 is the bare slug while the hover
text at lines 60-61 carries the score and every reason. Severity is carried by a
CSS class alone. Source: agoge run
`dev/local/audit-results/agoge-2026-08-31.md`, finding 19 (MEDIUM, ux lane,
status unverified - the nodes never rendered in jsdom, so the markup was read
from source); decision 2026-09-02: mirror the mouse handlers on focus and
enrich the aria-label.

```
jsdom: bind:clientWidth is 0, the {#if R > 60} guard fails and
HORIZON node count: 0 - the nodes never render. The quoted markup
(role="button" tabindex="0" aria-label={slug(n.r)}, onmouseenter with no
onfocus) is read from the source, which backs nothing.
```

One correction to that evidence, verified by reading the component: the
`{#if R > 60}` guard at line 73 covers only the rings, the gate and the
chevrons. The nodes at lines 92-126 sit outside it and are empty because the
`$effect` at line 27 returns early while `w` and `h` are 0. Svelte sets those
bindings by reading `element.clientWidth` once on mount
(`node_modules/svelte/src/internal/client/dom/elements/bindings/size.js`), not
only from a ResizeObserver, so a test that gives the jsdom elements a non-zero
client size does render the nodes. This finding is testable after all.

## Solution

Add `onfocus`/`onblur` beside the mouse handlers, taking the tooltip position
from the focused node's bounding box because a focus event has no `clientX`.
Fold the score and the already-computed worst severity (`n.sev`, set at line 35)
into the `aria-label`. Then teach `smoke.test.js` to give elements a non-zero
client size so the field renders and both changes are asserted on real markup.

## Requirements

### Must have

- `aria-label` on each node reads `` `${slug(n.r)} · score ${n.sc.score} · ${n.sev}` ``,
  keeping the `·` separator the hover text already uses at line 61.
- `onfocus` shows the same `hint(n)` text `onmouseenter` shows, positioned from
  `e.currentTarget.getBoundingClientRect()` so no `NaN` reaches the tooltip
  style.
- `onblur` hides the tooltip, mirroring `onmouseleave`.
- `render()` in `smoke.test.js` takes a `clientSize` option that defines
  configurable `clientWidth` and `clientHeight` getters on that jsdom window's
  `Element.prototype` before the bundle is evaluated.
- The existing mouse handlers, `role`, `tabindex` and click behaviour are
  unchanged.

### Nice to have

- none

## Implementation

### Module: Horizon.svelte

- **Location**: `skills/brief-portfolio/app/src/components/`
- **Responsibility**: Give every node the same content on focus that it gives
  on hover.
- **Exports**: `Horizon` component, internal `hint()`

### Module: smoke.test.js

- **Location**: `skills/brief-portfolio/app/`
- **Responsibility**: Render the landing tab's primary visual, which no test
  reaches today, and assert the label and the focus tooltip.
- **Exports**: `render(payload, options)`, `node --test` cases

### Dependencies

- Horizon.svelte: No dependencies (foundation)
- smoke.test.js: Depends on [Horizon.svelte]

## Tasks

### Phase 0: Foundation

- [ ] Add the `clientSize` option to `render()` in `smoke.test.js` - Acceptance: `npm --prefix skills/brief-portfolio/app test` reports 0 failing tests with every existing `render(` call site unchanged; a new test calling `render(payload, { clientSize: { width: 900, height: 700 } })` finds `doc.querySelectorAll('main g.node').length === 1` for a one-repo payload, against 0 without the option.
- [ ] Fold the score and severity into the node `aria-label` in `Horizon.svelte:98` - Acceptance: after `npm --prefix skills/brief-portfolio/app run build` and `cp skills/brief-portfolio/app/dist/index.html skills/brief-portfolio/assets/template.html`, `npm --prefix skills/brief-portfolio/app test` passes; the new test renders a repo carrying `security: [{ kind: 'dependabot', severity: 'critical', title: 'pkg: bad', url: '' }]` with `clientSize` set and asserts `doc.querySelector('main g.node').getAttribute('aria-label')` matches `/^buvis\/demo · score \d+ · critical$/`.

### Phase 1: Core

- [ ] Add `onfocus`/`onblur` beside the mouse handlers in `Horizon.svelte:102-103` (depends on: Phase 0) - Acceptance: after the same build and copy, `npm --prefix skills/brief-portfolio/app test` passes; a new test dispatches `new doc.defaultView.FocusEvent('focus')` on `main g.node`, flushes, and asserts `doc.querySelector('.tooltip').textContent` matches `/score \d+/` and `/1 critical\/high security alert/` (the reason text `hint()` builds from `attention()`), then dispatches `new doc.defaultView.FocusEvent('blur')`, flushes, and asserts `doc.querySelector('.tooltip') === null`; the tooltip's inline `style` contains no `NaN`.

## Success Criteria

- `npm --prefix skills/brief-portfolio/app test` reports 18 passing tests and 0
  failing, up from 16.
- Rendered gravity-field nodes under test: 0 today, 1 per repo after, so the
  landing tab's primary visual stops being unexercised.
- Node content reachable without a mouse: the slug only today, the slug plus
  score plus severity plus the full reason list after.
- Human follow-up, not a task: no browser here can prove how a real screen
  reader announces the node, so the finding's status stays "fixed on source
  reading, confirmed only in jsdom".
