---
default_model: sonnet
rework_cap: 5
design: skip
---

# The portfolio brief conveys tab, control and toggle state to sighted mouse users only

## Overview

### Problem Statement

Three gaps hide state from anyone not looking at colour. The seven nav buttons
at `skills/brief-portfolio/app/src/App.svelte:80-86` carry no `aria-current`,
`aria-selected` or `role`, and the `<nav>` has no label, so only the `active`
CSS class marks the current view. The Repos toolbar at
`skills/brief-portfolio/app/src/components/Repos.svelte:37-38` gives its filter
input nothing but a placeholder, which vanishes on typing, and its sort
`<select>` no name at all. The toggle chips at `Todos.svelte:72`,
`Work.svelte:69`, `Work.svelte:72` and the header org chip at `App.svelte:88-98`
carry no `aria-pressed` and never change their label. Source: agoge run
`dev/local/audit-results/agoge-2026-08-31.md`, findings 16 (MEDIUM, ux), 17
(MEDIUM, ux) and 36 (LOW, ux); decision 2026-09-02: one accessibility pass,
with the sibling's nav markup for 16, `aria-label` on both controls for 17, and
`aria-pressed` only for 36.

```
(16) <button class="svelte-1n46o8q active">Brief</button>, and for all seven
buttons ariaCurrent: null, ariaSelected: null, role: null; the <nav> has
role: null and no aria-label. The sibling app already does it right.
(17) <input placeholder="filter repos... ( / )"> -> id: "" aria-label: null
labels: 0; <select> -> id: "" aria-label: null labels: 0.
(36) before clicking: [{text:'hide done', pressed:null, cls:'chip'}, ...];
after: aria-pressed now: null | class now: chip active.
```

### Target Users

Screen-reader, keyboard and high-contrast users of the portfolio brief. The
sibling `skills/debrief-meeting/app/src/App.svelte:72-79` already ships the
correct nav markup and is out of scope here.

### Success Metrics

- Nav buttons exposing `aria-current="page"`: 0 today, exactly 1 after (the
  active tab), and it moves on click.
- `<nav>` elements with an accessible name on the Brief: 0 today, 1 after.
- Repos toolbar controls with an accessible name: 0 of 2 today, 2 of 2 after.
- Toggle chips exposing `aria-pressed`: 0 of 4 today, 4 of 4 after.
- `npm --prefix skills/brief-portfolio/app test` grows from 16 to 19 passing
  tests, 0 failing.

## Functional Decomposition

### Capability: Tab state exposure

The seven-tab nav is the only thing that says which view is on screen.

#### Feature: Named nav with a current-tab marker

- **Description**: The nav carries a name and the active tab announces itself.
- **Inputs**: The `tab` state.
- **Outputs**: `<nav aria-label="Sections">` at `App.svelte:80`, and
  `aria-current="page"` on the active button only.
- **Behavior**: `aria-current={tab === id ? 'page' : undefined}` at
  `App.svelte:82`, both copied from `debrief-meeting/app/src/App.svelte:72-79`.

### Capability: Named toolbar controls

The Repos tab's filter and sort are the only way into a 25-repo list.

#### Feature: Named filter input and sort select

- **Description**: Both controls keep a name once the placeholder is gone.
- **Inputs**: None; static markup.
- **Outputs**: `aria-label="Filter repos"` at `Repos.svelte:37` and
  `aria-label="Sort repos"` at `Repos.svelte:38`.
- **Behavior**: Attributes only; placeholder and option text stay as they are.

### Capability: Toggle state exposure

Four chips filter what the page shows, and their on/off state is colour-only.

#### Feature: Pressed state on toggle chips

- **Description**: Each toggle chip reports whether it is on.
- **Inputs**: `hideDone` (Todos), `showDeps` and `showDrafts` (Work), `org`
  (App header).
- **Outputs**: `aria-pressed="true"` or `"false"` on each of the four chips.
- **Behavior**: `aria-pressed={hideDone}`, `aria-pressed={showDeps}`,
  `aria-pressed={showDrafts}` and `aria-pressed={org !== 'all'}`, each mirroring
  that chip's `class:active` expression. `drafts` starts on, so it renders
  `"true"` on mount.

## Structural Decomposition

### Repository Structure

```
skills/brief-portfolio/app/
├── src/App.svelte                  # Maps to: Named nav with a current-tab
│                                   #   marker, Pressed state on toggle chips
├── src/components/Repos.svelte     # Maps to: Named filter input and sort select
├── src/components/Todos.svelte     # Maps to: Pressed state on toggle chips
├── src/components/Work.svelte      # Maps to: Pressed state on toggle chips
└── smoke.test.js                   # Maps to: all three features
```

### Module: App.svelte

- **Maps to capability**: Tab state exposure, Toggle state exposure
- **Responsibility**: Label the nav, mark the current tab, report the org chip.
- **Exports**:
  - `App` component - nav at lines 80-86, org chip at 88-98

### Module: Repos.svelte

- **Maps to capability**: Named toolbar controls
- **Responsibility**: Name the filter input and the sort select.
- **Exports**:
  - `Repos` component - toolbar at lines 36-45

### Module: Todos.svelte

- **Maps to capability**: Toggle state exposure
- **Responsibility**: Report the `hide done` chip's pressed state.
- **Exports**:
  - `Todos` component - chip at line 72

### Module: Work.svelte

- **Maps to capability**: Toggle state exposure
- **Responsibility**: Report the `deps-bot PRs` and `drafts` chips' state.
- **Exports**:
  - `Work` component - chips at lines 69 and 72

### Module: smoke.test.js

- **Maps to capability**: Tab state exposure, Named toolbar controls, Toggle
  state exposure
- **Responsibility**: Assert the rendered attributes for all three findings.
- **Exports**:
  - `node --test` cases - three new, all existing ones unchanged

## Dependency Graph

### Foundation Layer (Phase 0)

No dependencies - built first.

- **App.svelte**: The sibling's nav markup, and the header chip's pressed state.

### Core Layer (Phase 1)

- **Repos.svelte**: Depends on [App.svelte]. Reached through the fixed nav.
- **Todos.svelte**: Depends on [App.svelte]. Same.
- **Work.svelte**: Depends on [App.svelte]. Same.

### Integration Layer (Phase 2)

- none

## Implementation Phases

### Phase 0: Foundation

**Goal**: The nav says what it is and which view is current.

**Tasks**:

- [ ] Add `aria-label="Sections"` to the `<nav>` and `aria-current={tab === id ? 'page' : undefined}` to the tab buttons in `App.svelte:80-86` (no deps) - Acceptance: after `npm --prefix skills/brief-portfolio/app run build` and `cp skills/brief-portfolio/app/dist/index.html skills/brief-portfolio/assets/template.html`, `npm --prefix skills/brief-portfolio/app test` passes; a new test asserts `doc.querySelector('header nav').getAttribute('aria-label') === 'Sections'`, that exactly 1 of the 7 `header nav button` elements has `getAttribute('aria-current') === 'page'` and its text starts with `Brief`, and that after clicking the `Work` tab exactly 1 button carries it and its text starts with `Work`.

**Exit Criteria**: `rg -n "aria-current" skills/brief-portfolio/app/src/App.svelte`
matches, and `npm --prefix skills/brief-portfolio/app test` reports 17 passing
tests and 0 failing.

### Phase 1: Core

**Goal**: Every named control and every toggle reports itself without colour.

**Tasks**:

- [ ] Add `aria-label="Filter repos"` and `aria-label="Sort repos"` at `Repos.svelte:37-38` (depends on: Phase 0) - Acceptance: after `npm --prefix skills/brief-portfolio/app run build` and `cp skills/brief-portfolio/app/dist/index.html skills/brief-portfolio/assets/template.html`, `npm --prefix skills/brief-portfolio/app test` passes; a new test opens the Repos tab and asserts `doc.querySelector('main input').getAttribute('aria-label') === 'Filter repos'` and `doc.querySelector('main select').getAttribute('aria-label') === 'Sort repos'`.
- [ ] Add `aria-pressed` to the four toggle chips in `Todos.svelte:72`, `Work.svelte:69`, `Work.svelte:72` and `App.svelte:88-98` (depends on: Phase 0) - Acceptance: after the same build and copy, `npm --prefix skills/brief-portfolio/app test` passes; a new test asserts the Todo tab's `hide done` chip reads `aria-pressed="false"` and `"true"` after one click; the Work tab's two `main .filters button.chip` elements read `"false"` (deps-bot) and `"true"` (drafts) on mount; and the header chip `header .filter button.chip` reads `"false"` on mount and `"true"` after clicking it and then the `buvis` chip in `header .pop`.

**Exit Criteria**: `npm --prefix skills/brief-portfolio/app test` reports 19
passing tests and 0 failing, and `rg -n "aria-pressed"
skills/brief-portfolio/app/src` matches 4 times.

## Test Strategy

### Critical Scenarios

- **Happy path**: mount, then click through Brief, Repos, Work and Todo → Expected: one `aria-current="page"` at all times, both Repos controls named, all four chips exposing `aria-pressed`.
- **Edge case**: the `drafts` chip, which starts on → Expected: `aria-pressed="true"` on first render, before any click.
- **Error case**: a chip whose state changes without a rebuild of `assets/template.html` → Expected: the new tests fail, because the suite renders the built template, not the sources.

## Risks

- **Bundling three findings**: a reviewer accepts all three or unpicks the
  commit. Accepted knowingly when the pass was approved; the three tasks are
  separable, one per finding.
- **`aria-label` leaves the sighted case**: a user who has typed over the
  placeholder still has no visible label, and `aria-pressed` leaves the `drafts`
  chip's wording ambiguous for everyone. Both were declined for now; visible
  labels and state-dependent wording stay open.
- **A fifth chip is out of scope**: `Matrix.svelte:40` carries the same `hide
  done` chip and was not named in findings 16, 17 or 36. It is left alone here
  rather than folded in silently.
