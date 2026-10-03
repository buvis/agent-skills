---
default_model: opus
rework_cap: 5
---

# Filtering to one org still reports another org's uncollected repo

Source: agoge run `dev/local/audit-results/agoge-2026-08-31.md`, finding 37
(LOW, ux lane, verified in jsdom on real data). Decision 2026-09-02: accepted
— filter `skipped` by the selected org.

## Overview

### Problem Statement

Every number on the portfolio brief is org-scoped except `skipped`, which is
passed unfiltered: filtered to `buvis`, the header still claims `doogat/jink`
not collected — a warning about a repo not in the current view, unactionable
there.

### Target Users

An operator who works inside one org filter.

### Success Metrics

- With an org selected, the skipped line counts and names only that org's
  repos; "all orgs" shows everything as today.

## Functional Decomposition

`skipped.filter(r => org === 'all' || r.org === org)` at the pass-through in
`App.svelte`.

## Structural Decomposition

- `skills/brief-portfolio/app/src/App.svelte` (~50, ~116)

## Implementation Phases

### Phase 0: The filter

One line, test, template rebuild.

## Test Strategy

Evidence from the report, verbatim:

```
Org options: ["all orgs","buvis","doogat","tbouska"]. After clicking buvis,
the header reads 18 repos · 4 burning · … while
still claims doogat/jink not collected: true.
```

Check: jsdom test clicks an org chip and asserts the out-of-org skip is gone.

## Risks

Chosen knowingly: a skipped repo now vanishes entirely for a user who never
selects "all orgs" — they may never learn it is broken. PRD 00018's banner is
the mitigating surface for the class.
