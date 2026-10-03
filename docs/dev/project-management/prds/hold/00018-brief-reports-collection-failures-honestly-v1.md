---
default_model: opus
rework_cap: 5
---

# The Brief names collection failures instead of rendering clean zeros

## Overview

### Problem Statement

A failed `collect_repo` appends to `repo["errors"]` and returns early
(`skills/brief-portfolio/scripts/collect.py:399-401`), leaving no `commits`,
`issues`, `prs`, `ci` or `security` key, so the Brief sums the absent keys as
zero and says nothing: on the real payload of 2026-08-29 all 25 repos had failed
to fetch and Quick wins still advised pushing commits from ahead/behind numbers
computed after the fetch died. Two smaller defects share the class:
`src/components/Brief.svelte:57-61` prints skipped repo names but drops the
`skipped` reason the payload carries, and `src/App.svelte:116` hands the Brief an
unfiltered `skipped` list while every other number is org-scoped. Naming skipped
repos is already built and covered by `smoke.test.js:194-211`. Source: agoge run
`dev/local/audit-results/agoge-2026-08-31.md`, findings 8 (HIGH, merged ux +
integration), 13 (MEDIUM, ux) and 37 (LOW, ux); decision 2026-09-02: one banner
carries fetch errors, skip reasons and a partial mark, and the skipped list
follows the org filter.

```
total repos: 25 | all with a fetch: error: true - every one carrying
"fetch: git fetch: ... Permission denied (publickey)". Text counts across all
seven tabs: "collection warning" x 0, "Permission denied" x 0, "fetch:" x 0.
Payload carries "skipped": "git remote: error: No such remote 'origin'";
skip reason in rendered Brief text: false.
After clicking buvis, still claims doogat/jink not collected: true.
```

### Target Users

The operator reading the brief as a decision surface, precisely when collection
breaks and the page looks healthiest, and who often works inside one org filter.

### Success Metrics

- Banners naming failed fetches: 0 today, 1 whenever a visible repo has errors.
- Tiles marked partial while that banner shows: 0 of 8 today, 8 of 8 after.
- Skip reasons rendered: 0 today, 1 per skipped repo.
- Out-of-org skipped repos named under a filter: 1 today, 0 after.
- Every smoke test named in the tasks below passes with 0 failing (no suite
  total pinned: create-prd metric rule, 2026-09-05).
- Work-tab lists over an absent `issues`, `prs` or `security` key: render
  "No open ..." today, "not collected this run" after.

## Functional Decomposition

### Capability: Collection-failure reporting

One surface for the class: failed fetches, skipped repos, partial aggregates.

#### Feature: Fetch-error banner

- **Description**: A banner whenever a visible repo carries errors.
- **Inputs**: The `repos` prop and each record's `errors` array.
- **Outputs**: `<p class="collectfail">` in the top `.bar` section.
- **Behavior**: Shows on `repos.some((r) => r.errors?.length)`; text carries the
  count, `could not be fetched`, `ahead/behind may be stale`, and each error's
  distinct first line.

#### Feature: Skip reasons in the banner

- **Description**: Each skipped repo shows why it was skipped.
- **Inputs**: The `skipped` prop: `owner`, `name`, `skipped`.
- **Outputs**: One line per repo reading `owner/name: reason`.
- **Behavior**: Keeps today's count and slug markup untouched so
  `smoke.test.js:194-211` still passes; appends the reason lines below it.

#### Feature: Partial aggregate marks

- **Description**: Tiles say they were computed over partial data.
- **Inputs**: The same error check as the banner.
- **Outputs**: `class="partial"` on each of the 8 `.stat` buttons.
- **Behavior**: `class:partial={repos.some((r) => r.errors?.length)}`, no number changes.

#### Feature: Work-tab "not collected" lines

- **Description**: The Work tab says when a repo's issues, PRs or security
  alerts were not collected, instead of rendering "No open issues." / "No open
  PRs." and a `Work 0` badge over an absent key.
- **Inputs**: Each repo record's `issues`, `prs` and `security` keys, absent
  when that fetch failed (`collect.py` leaves the key out and appends to
  `errors`).
- **Outputs**: One line per absent key inside the matching Work-tab list,
  worded like the CI wall's `ciMissing` line ("not collected this run"),
  naming the repo.
- **Behavior**: Mirrors the `ciMissing` block in `Work.svelte` for
  `r.issues === undefined`, `r.prs === undefined` and
  `r.security === undefined`; the `Work` badge does not count an absent key as
  zero. Added 2026-09-05 from agoge report
  `dev/local/audit-results/agoge-2026-09-05.md`, finding 8 (MEDIUM, journey +
  integration, mocked); decision: extend this PRD rather than open a second
  owner for collection-failure UI. Evidence: jsdom, shim page with
  `errors=['issues: gh api: gh: HTTP 500 ...']` and no `issues` key rendered
  `Open issues · 0` / `No open issues.`, badge `Work0`, no notice.

### Capability: Org-scoped skip list

The header org filter scopes every number on the page except this one list.

#### Feature: Org filter for skipped repos

- **Description**: The skipped list follows the selected org.
- **Inputs**: `skipped` from the payload and the `org` state.
- **Outputs**: The filtered array handed to `Brief` at line 116.
- **Behavior**: `org === 'all' ? skipped : skipped.filter((r) => r.org === org)`;
  skip records carry `org` (`collect.py:41`), so the collector is untouched.

## Structural Decomposition

### Repository Structure

```
skills/brief-portfolio/app/
├── src/App.svelte              # Maps to: Org filter for skipped repos
├── src/components/Brief.svelte # Maps to: Fetch-error banner, Skip reasons in
│                               #   the banner, Partial aggregate marks
├── src/components/Work.svelte  # Maps to: Work-tab "not collected" lines
└── smoke.test.js               # Maps to: all five features
```

### Module: Brief.svelte

- **Maps to capability**: Collection-failure reporting
- **Responsibility**: Render the banner and mark the aggregates partial.
- **Exports**:
  - `Brief` component - same props as today, none added

### Module: Work.svelte

- **Maps to capability**: Collection-failure reporting
- **Responsibility**: Say "not collected this run" for absent issue, PR and
  security keys instead of rendering an empty list.
- **Exports**:
  - `Work` component - same props as today, none added

### Module: App.svelte

- **Maps to capability**: Org-scoped skip list
- **Responsibility**: Scope `skipped` before it reaches the Brief.
- **Exports**:
  - `App` component - filtered `skipped` at line 116

### Module: smoke.test.js

- **Maps to capability**: Collection-failure reporting, Org-scoped skip list
- **Responsibility**: Hold the jsdom regressions for both capabilities.
- **Exports**:
  - `node --test` cases - four new, all existing ones unchanged

## Dependency Graph

### Foundation Layer (Phase 0)

No dependencies - built first.

- **Brief.svelte**: The banner, the reasons and the partial mark.
- **Work.svelte**: The three "not collected this run" lines.

### Core Layer (Phase 1)

- **App.svelte**: Depends on [Brief.svelte]. Filtering hides an out-of-org
  skipped repo, so the banner exists first.

### Integration Layer (Phase 2)

- none

## Implementation Phases

### Phase 0: Foundation

**Goal**: Every collection problem in the visible payload is stated with its
reason, and no aggregate over partial data reads as clean.

**Tasks**:
- [ ] Render the fetch-error banner in `Brief.svelte` when any visible repo carries `errors` (no deps) - Acceptance: after `npm --prefix skills/brief-portfolio/app run build` and `cp skills/brief-portfolio/app/dist/index.html skills/brief-portfolio/assets/template.html`, `npm --prefix skills/brief-portfolio/app test` passes; a new smoke test with two repos whose `errors` are `["fetch: Permission denied (publickey)"]` and `["meta: HTTP 404"]` asserts `doc.querySelector('main').textContent` matches `/2 repos could not be fetched/`, `/ahead\/behind may be stale/`, `/Permission denied \(publickey\)/` and `/HTTP 404/`.
- [ ] Render one reason line per skipped repo inside the same banner (no deps) - Acceptance: after the same build and copy, `npm --prefix skills/brief-portfolio/app test` passes; a new smoke test with `skipped: [{owner:'acme', name:'gadget', org:'acme', path:'/tmp/acme/gadget', skipped:"git remote: error: No such remote 'origin'"}]` asserts `main` text matches `/acme\/gadget/` and `/No such remote 'origin'/`, and the existing test `Brief tab names repos it could not collect this run` passes unchanged.
- [ ] Mark all 8 aggregate stat tiles partial while the banner shows (no deps) - Acceptance: after the same build and copy, `npm --prefix skills/brief-portfolio/app test` passes; a new smoke test asserts `doc.querySelectorAll('main .stat.partial').length === 8` for a payload with one errored repo and `=== 0` for the default payload.
- [ ] Render a "not collected this run" line in `Work.svelte` for each absent `issues`, `prs` or `security` key, mirroring the `ciMissing` block (no deps) - Acceptance: after the same build and copy, `npm --prefix skills/brief-portfolio/app test` passes; a new smoke test `Work tab says issues were not collected instead of rendering an empty list` mounts one repo whose record carries `errors: ['issues: gh api: gh: HTTP 500 Internal Server Error']` and no `issues` key, opens the Work tab, and asserts its text matches `/issues.*not collected this run/`, does not match `/No open issues\./`, and that the `Work` badge does not read `0` for that payload; the existing `No CI runs.` and `ciMissing` tests pass unchanged.

**Exit Criteria**: the four new Phase 0 smoke tests pass,
`npm --prefix skills/brief-portfolio/app test` reports 0 failing, and
`rg -n "could not be fetched" skills/brief-portfolio/assets/template.html`
matches.

### Phase 1: Core

**Goal**: A filtered view warns only about repos in that view.

**Tasks**:
- [ ] Filter `skipped` by the selected org in `App.svelte` before passing it to `Brief` at line 116 (depends on: Phase 0) - Acceptance: after `npm --prefix skills/brief-portfolio/app run build`, `cp skills/brief-portfolio/app/dist/index.html skills/brief-portfolio/assets/template.html` and `npm --prefix skills/brief-portfolio/app test`, a new smoke test with repos in orgs `buvis` and `doogat` plus `skipped: [{owner:'doogat', name:'jink', org:'doogat', path:'/tmp/doogat/jink', skipped:'no remote'}]` asserts `main` text matches `/doogat\/jink/` on mount, then clicks `header .filter button.chip` and the `header .pop button.chip` reading `buvis`, and asserts `main` text no longer matches `/doogat\/jink/`.

**Exit Criteria**: the org-filter smoke test passes and
`npm --prefix skills/brief-portfolio/app test` reports 0 failing.

## Test Strategy

### Critical Scenarios

- **Happy path**: no repo carries `errors` and nothing is skipped → Expected: no banner, no `.stat.partial`, the 16 existing tests unchanged.
- **Edge case**: every visible repo failed with the same reason → Expected: one banner, count equal to the repo count, the reason printed once.
- **Error case**: a skipped repo in another org while a filter is active → Expected: absent from the Brief text, in-org failures still reported.
- **Error case**: a repo whose issues fetch failed (no `issues` key, an `errors` entry) → Expected: the Work tab's issues list says "not collected this run" and never "No open issues."; the badge does not count it as zero.

## Risks

- **A skipped repo vanishes under a filter**: an operator who never selects "all
  orgs" may never learn a repo is broken. Accepted knowingly (finding 37's named
  drawback); the banner lands first as the mitigating surface.
- **Decided contract values**: the banner class, the reason-line format and the
  partial class had no source value and were fixed at review. Each is asserted
  by a test the same task writes, so renaming one costs one test edit.
- **Stale template**: the suite renders `assets/template.html`, so a source
  change without the rebuild leaves the tests green against old markup. Every
  task names the rebuild and copy before the test command.
- **Overlap with PRD 00026**: finding 18's "name unfetched repos" half lives on
  the Work tab. This PRD owns the wording; 00026 reuses it.
