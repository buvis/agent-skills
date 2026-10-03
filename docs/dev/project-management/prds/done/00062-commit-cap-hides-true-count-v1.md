---
default_model: sonnet
model_tier_rationale: exact git command and rendering strings given, the authored xfail binds the key name
design: skip
---

# Busy repos read as exactly "200 commits" and the Brief headline undercounts the portfolio

## Problem

`collect_commits` in `skills/brief-portfolio/scripts/collect.py` truncates
`git log` at `MAX_COMMITS = 200` (line 20, lines 79-84) and nothing records the
true total, so RepoDetail says "200 commits" for a repo with 717 and the Brief
headline sums the truncated lists: off by 572 today, and the gap grows with
activity, so a reader comparing weeks sees a plateau at 200 that is not real.
Source: agoge run `dev/local/audit-results/agoge-2026-09-05.md`, finding 10
(MEDIUM, journey lane, verified against the live collect); decision 2026-09-05:
collect a `commit_count` next to the capped list. Strict xfail landed on master
in a550262; it binds to the `commit_count` key name.

```
Live collect: data.json total 839 commits, three repos capped at 200; git
rev-list --count --since="60 days ago" origin/master gives buvis/cellar 717,
buvis/gems 252, doogat/ddb 203. jsdom mount of the live page: Brief 839
commits, RepoDetail for buvis/cellar What happened · 200 commits.
```

## Solution

Keep collect_commits(path, branch, days) returning its capped list. Add
collect_commit_count(path, branch, days), returning the integer from
`git rev-list --count --since=<window> origin/<default-branch>`. Wire it into
collect_repo as a separately guarded commit_count collector, storing that
integer at repo["commit_count"]. A failure leaves the key absent and adds
`commit_count: <reason>` to errors; metadata failure leaves it absent too. In the page, `RepoDetail` renders `<n> commits` when
`commit_count` is at most `commits.length` and `<commits.length> of
<commit_count> shown` otherwise; derive.js aggregate supplies the Brief headline by summing `commit_count`, falling
back to `commits.length` for a record without it so a `data-prev.json` from an
older run still renders. Each history.repos[slug].c switches to that repo's
commit_count (falling back to its commits length if absent) so the trend reflects real activity; rows written before this
change stay capped, which the sparkline tolerates. The list itself stays
capped: the digest and the activity tab remain partial by decision.

## Requirements

### Must have

- Every successfully counted repo carries the true commit_count for the
  window/default branch, whether or not the list was capped. Missing counts
  retain the existing list-length fallback; failed new counts carry a warning.
- RepoDetail shows "200 of 717 shown" for a capped repo and "<n> commits" for
  an uncapped one.
- The Brief headline equals the sum of `commit_count` over visible repos.
- The xfail marker on
  `test_a_capped_commit_list_still_carries_the_true_commit_count` is deleted.

### Nice to have

- none

## Implementation

### Module: collect.py

- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: Record the true count next to the capped list.
- **Exports**: `collect_commits()` unchanged list, new `collect_commit_count()`, top-level repo.commit_count and per-repo history c

### Module: Brief.svelte, RepoDetail.svelte and derive.js

- **Location**: `skills/brief-portfolio/app/src/components/` and `src/lib/derive.js`
- **Responsibility**: Aggregate and render the true count and the cap.
- **Exports**: components, props unchanged

### Module: test_collect_pipeline.py and smoke.repos.test.js

- **Location**: `skills/brief-portfolio/scripts/` and `skills/brief-portfolio/app/`
- **Responsibility**: Pin the key and the two renderings.
- **Exports**: pytest and `node --test` cases

### Dependencies

- collect.py: No dependencies (foundation)
- components: Depends on [collect.py's key]
- tests: Depends on [collect.py, components]

## Tasks

### Phase 0: Foundation

- [ ] Add collect_commit_count and its guarded collect_repo wiring, then map each per-repo history c field to the new count with the pinned fallback - Acceptance: delete the `xfail` marker on `test_a_capped_commit_list_still_carries_the_true_commit_count`; it passes, and a new test `test_history_row_commit_field_uses_the_true_count` asserts each history.repos[slug].c equals that repo's commit_count, using two repos with different counts; absent-count and failing-count cases retain fallback and warning behavior; `uv run pytest skills/brief-portfolio/scripts -q` reports 0 failing.

### Phase 1: Core

- [ ] Render the count in `RepoDetail.svelte` and update the sum in derive.js aggregate consumed by `Brief.svelte`, then `npm --prefix skills/brief-portfolio/app run build` and `cp skills/brief-portfolio/app/dist/index.html skills/brief-portfolio/assets/template.html` (depends on: Phase 0) - Acceptance: a new smoke test `RepoDetail says how many commits are shown when the list is capped` mounts a repo with 2 commits listed and `commit_count: 717` and asserts the detail text matches `/2 of 717 shown/` and the Brief headline matches `/717 commits/`; a second case with `commit_count` equal to the list length matches `/2 commits/`; a record without `commit_count` renders today's numbers; `npm --prefix skills/brief-portfolio/app test` reports 0 failing.

## Success Criteria

- The authored test passes without its marker; the two new tests pass.
- Re-running the report's live mount shows a Brief headline equal to the
  `rev-list` totals and RepoDetail for buvis/cellar reading "200 of 717 shown".
