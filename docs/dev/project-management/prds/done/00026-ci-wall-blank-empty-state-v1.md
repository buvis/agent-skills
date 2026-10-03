---
default_model: sonnet
rework_cap: 5
design: skip
---

# The CI wall prints a heading over blank space and drops repos whose CI never arrived

## Problem

On the Work tab, Open PRs (`skills/brief-portfolio/app/src/components/Work.svelte:76`)
and Open issues (line 110) both print an explicit empty message; the CI wall at
lines 138-140 prints its heading and then nothing, because it is the only one of
the three without an `{#if length === 0}` branch. Beside two siblings that state
their empty case, blank reads as "CI is fine everywhere". It is worse than that:
`ciRows` at lines 26-30 filters on `r.ci?.length`, so a repo whose CI collection
errored, and therefore has no `ci` key at all, drops out with no trace. Source:
agoge run `dev/local/audit-results/agoge-2026-08-31.md`, finding 18 (MEDIUM, ux
lane, status mocked - synthetic empty payload); decision 2026-09-02: add the
missing empty branch and name the repos excluded because `ci` was never fetched.

```
Section bodies after each heading: "Open PRs · 0" -> "deps-bot PRs (0)
drafts No open PRs."; "Open issues · 0" -> "No open issues."; "CI wall ·
latest run per workflow on default branch" -> "". Lines 76 and 110 have an
{#if length === 0} branch; line 138 does not. ciRows filters on
r.ci?.length, so an errored repo drops out silently.
```

## Solution

Give the CI wall the branch its siblings already have, and add a line under it
naming the repos whose `ci` key is absent. `collect_repo` returns early before
it ever sets `ci` (`skills/brief-portfolio/scripts/collect.py:399-401`), so
"key absent" is exactly "never fetched", while `ci: []` means fetched and empty
and must not be reported. Reuse PRD 00018's "not collected" wording rather than
repeating its banner here.

## Requirements

### Must have

- With `ciRows.length === 0`, the CI wall section renders `No CI runs.`,
  matching the `No open issues.` shape of its sibling at line 111.
- Repos whose record has no `ci` key are named below the wall as
  `{n} not collected this run: {owner/name, ...}`.
- A repo with `ci: []` is never listed as not collected.
- The exclusion line and the empty branch are independent: a wall with rows can
  still carry the exclusion line.

### Nice to have

- none

## Implementation

### Module: Work.svelte

- **Location**: `skills/brief-portfolio/app/src/components/`
- **Responsibility**: State the CI wall's empty case and name the repos the
  wall cannot speak for.
- **Exports**: `Work` component, derived `ciRows`, derived `ciMissing`

### Module: smoke.test.js

- **Location**: `skills/brief-portfolio/app/`
- **Responsibility**: Drive the empty and never-fetched payloads through the
  Work tab.
- **Exports**: `node --test` cases

### Dependencies

- Work.svelte: No dependencies (foundation)
- smoke.test.js: Depends on [Work.svelte]
- PRD 00018: lands first and defines the "not collected" wording this section
  reuses. It owns the Brief banner; this PRD adds no banner of its own.

## Tasks

### Phase 0: Foundation

- [ ] Add the `{#if ciRows.length === 0}` branch to the CI wall section in `Work.svelte:138-140` - Acceptance: after `npm --prefix skills/brief-portfolio/app run build` and `cp skills/brief-portfolio/app/dist/index.html skills/brief-portfolio/assets/template.html`, `npm --prefix skills/brief-portfolio/app test` passes; a new test opens the Work tab on the default payload (whose repo carries no `ci` key) and asserts `doc.querySelector('main').textContent` matches `/No CI runs/`.
- [ ] Derive `ciMissing` from `r.ci === undefined` and render it below the wall in `Work.svelte` - Acceptance: after the same build and copy, `npm --prefix skills/brief-portfolio/app test` passes; the same new test asserts `main` text matches `/not collected this run/` and `/buvis\/demo/`, and a second new test with `payload.data.repos[0].ci = []` asserts `main` text matches `/No CI runs/` and does not match `/not collected this run/`.

## Success Criteria

- `npm --prefix skills/brief-portfolio/app test` reports 18 passing tests and 0
  failing, up from 16.
- Sections on the Work tab that state their empty case: 2 of 3 today, 3 of 3
  after.
- Repos silently dropped from the CI wall: 1 of 1 in the default payload today,
  0 after.
- `rg -n "length === 0" skills/brief-portfolio/app/src/components/Work.svelte`
  matches 3 times.
- Human follow-up, not a task: the evidence is a synthetic empty payload,
  because the operator's real data has CI rows and cannot reach this state.
