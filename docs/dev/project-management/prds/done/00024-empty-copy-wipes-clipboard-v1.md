---
default_model: sonnet
rework_cap: 5
catchup: skip
design: skip
---

# Copying an empty follow-up list wipes the clipboard and claims success

## Problem

`copy()` in `skills/brief-portfolio/app/src/components/Todos.svelte:51-67`
never checks how many items are open, and neither the bar button (line 73) nor
the per-group buttons (line 83) are ever disabled. With zero open follow-ups it
writes an empty string to the clipboard, destroying whatever the user had there,
then reports `✓ copied` in the button label and through the `aria-live` region
at line 112. The count is already on screen: line 71 renders `0 open
follow-ups` immediately left of the button, and line 26 holds `openCount`.
Source: agoge run `dev/local/audit-results/agoge-2026-08-31.md`, finding 15
(MEDIUM, ux lane, status mocked - jsdom clipboard stub); decision 2026-09-02:
early return with a distinct status, plus disabled buttons.

```
Real payload with all 118 todos checked off: count text: "0 open follow-ups",
copy button disabled? false, click -> clipboard received: [""],
button label: "✓ copied", aria-live: "✓ copied". Empty portfolio, same result.
```

## Solution

Return early from `copy()` when the filtered `open` list is empty, recording the
declining button's label in a new `nothing` state that clears after 1500ms like
`copied` and `failed` do. Fold it into the `status` derivation at line 27 so the
live region announces the truth. Bind `disabled={openCount === 0}` on the bar
button and the per-group buttons, so the whole-list case is unreachable by
click and the per-group case reports itself.

## Requirements

### Must have

- `copy(items, label)` performs no `navigator.clipboard.writeText` and no
  `fallbackCopy` when `items.filter((t) => !done.has(t.id))` is empty.
- The declined copy sets `nothing = label` and clears it after 1500ms,
  matching the existing `copied` and `failed` timers.
- The `aria-live` region at line 112 reads `nothing to copy` for a
  declined copy, never `✓ copied`.
- The per-group button at line 83 reads `nothing` while declined.
- The bar button (line 73) and the per-group buttons (line 83) carry
  `disabled={openCount === 0}`.

### Nice to have

- none

## Implementation

### Module: Todos.svelte

- **Location**: `skills/brief-portfolio/app/src/components/`
- **Responsibility**: Decline a copy with nothing open, say so, and disable the
  controls when the whole list is done.
- **Exports**: `Todos` component, internal `copy()`, `status`

### Module: smoke.test.js

- **Location**: `skills/brief-portfolio/app/`
- **Responsibility**: Hold the clipboard-stub regressions for both the empty
  list and the fully-done group.
- **Exports**: `node --test` cases

### Dependencies

- Todos.svelte: No dependencies (foundation)
- smoke.test.js: Depends on [Todos.svelte]

## Tasks

### Phase 0: Foundation

- [ ] Add the early return, the `nothing` state and its `status` branch to `copy()` in `Todos.svelte` - Acceptance: after `npm --prefix skills/brief-portfolio/app run build` and `cp skills/brief-portfolio/app/dist/index.html skills/brief-portfolio/assets/template.html`, `npm --prefix skills/brief-portfolio/app test` passes; a new test with `prds: { backlog: ['Ship it.'], wip: [], done_count: 0 }` (two todos: one `soon`, one `later`) stubs `navigator.clipboard.writeText` and `doc.execCommand` to push into a `writes` array, ticks the checkbox in the `soon` section, clicks that section's `button.chip.mini`, and asserts `writes.length === 0`, the button text is `nothing`, and the `[aria-live="polite"]` element reads `nothing to copy`.
- [ ] Bind `disabled={openCount === 0}` on the bar button and the per-group buttons in `Todos.svelte` - Acceptance: after the same build and copy, `npm --prefix skills/brief-portfolio/app test` passes; a new test with `prds: { backlog: [], wip: [], done_count: 0 }` and `brush_last_run` set to `new Date().toISOString()` (zero todos) asserts the `copy open as markdown` button has `disabled === true`, that `button.click()` leaves the recording `writes` array at length 0, and that the `[aria-live="polite"]` element reads `""`.

## Success Criteria

- `npm --prefix skills/brief-portfolio/app test` reports 18 passing tests and 0
  failing, up from 16.
- Clipboard writes on an empty or fully-done list drop from 1 (an empty string)
  to 0.
- `rg -n "disabled=\{openCount === 0\}" skills/brief-portfolio/app/src/components/Todos.svelte`
  matches twice.
- A group whose items are all done, inside a list that still has open items
  elsewhere, keeps an enabled button: `openCount` is the whole-list count, as
  finding 15 specified. The early return is what makes that click honest.
- Human follow-up, not a task: the evidence is a jsdom clipboard stub, so
  real-browser clipboard behaviour on the declined path stays unconfirmed.
