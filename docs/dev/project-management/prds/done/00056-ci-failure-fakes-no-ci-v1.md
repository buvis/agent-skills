---
default_model: sonnet
model_tier_rationale: exact regex and branch given, additive stub tests
design: skip
consensus_engine: shadow
---

# A failed CI fetch is reported as "No CI runs" with zero warnings

## Problem

`collect_ci` in `skills/brief-portfolio/scripts/collect.py` (about lines
151-155) catches every `RuntimeError` from the `actions/runs` call as "Actions
disabled" and returns `[]`, so a 500 or a rate-limit 403 leaves `ci: []`, no
entry in the repo's `errors`, a history row with `"f": 0`, and the Work tab's
CI wall says "No CI runs." A red wall goes green on the morning GitHub is flaky,
and the "fix failing CI" todo disappears. The page side is already done: PRD
00026 renders "not collected this run" when the `ci` key is absent, so only the
collector needs to stop faking the key. By contrast `_gh_alerts` swallows only
403/404, and a 500 there lands in `errors`. Source: agoge run
`dev/local/audit-results/agoge-2026-09-05.md`, finding 3 (HIGH, integration
lane, status mocked: gh shim); decision 2026-09-05: re-raise unless the message
matches HTTP 403 or 404.

```
Shim exits 1 with gh: HTTP 500: Internal Server Error (.../actions/runs):
run prints 1 repos, 0 skipped, 0 with warnings; data.json has errors=[]
ci=[]; history row "f": 0; page shows No CI runs. and RepoDetail has no
"Collection warnings" section.
```

## Solution

In `collect_ci`, keep the "Actions disabled" swallow only when the
`RuntimeError` message matches `re.search(r"HTTP (403|404)", str(exc))`,
mirroring `_gh_alerts`; otherwise re-raise so `collect_repo` records
`ci: <message>` in `errors` and leaves the `ci` key absent, which the CI wall
already renders as "not collected this run". The string match hard-codes two
HTTP codes; that was the option's named drawback (a typed `GhHttpError` was
declined as overlapping PRD 00054).

## Requirements

### Must have

- An `actions/runs` failure other than HTTP 403/404 leaves no `ci` key on the
  repo and adds one `errors` entry starting with `ci:`.
- HTTP 403 and 404 on that call still yield `ci: []` with no error (Actions
  disabled).
- Preserve the existing history partial-failure contract from PRD 00028.
  This change fixes current CI fields and warnings; history still lacks a
  per-field unknown marker, so its f value can remain 0 when CI is unavailable.
  Do not alter history schema or its existing partial-failure regression here.

### Nice to have

- none

## Implementation

### Module: collect.py

- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: Distinguish "Actions disabled" from "fetch failed".
- **Exports**: `collect_ci()`, unchanged signature

### Module: test_collect_repo.py

- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: Pin both branches with a `collect.run` stub.
- **Exports**: pytest cases

### Dependencies

- collect.py: No dependencies (foundation)
- test_collect_repo.py: Depends on [collect.py]

## Tasks

### Phase 0: Foundation

- [ ] Narrow the swallow in `collect_ci` to HTTP 403/404 and re-raise everything else - Acceptance: new tests `test_a_500_on_actions_runs_lands_in_errors_and_leaves_ci_absent` and `test_a_403_on_actions_runs_still_reads_as_actions_disabled` patch `collect.run` (the seam the existing gh-failure tests use) to raise `RuntimeError("gh: HTTP 500: Internal Server Error (https://api.github.com/repos/demo/repo/actions/runs)")` and the 403 equivalent for the runs call, run `collect_repo`, and assert `"ci" not in repo` with one `errors` entry starting `ci:` for the 500, and `repo["ci"] == []` with no error for the 403; `uv run pytest skills/brief-portfolio/scripts -q` reports 0 failing.

### Phase 1: Core

- none

## Success Criteria

- The two new tests pass; the existing CI-wall and history-row tests pass
  unchanged.
- The report's shim reproduction prints `1 with warnings`, and the built
  page names that repo as "not collected this run". Preserve the existing
  global empty-state text when all repos lack CI; the explanation may coexist with it.
