---
default_model: sonnet
model_tier_rationale: one regex edit with the exact character class, additive tests
design: skip
---

# `?` and `/../` in a remote URL pass into gh api paths and page hrefs

## Problem

`REMOTE_RE` in `skills/brief-portfolio/scripts/collect.py` (line 18,
`github\.com[:/]([^/]+)/(.+?)(?:\.git)?/?$`) captures the repo name with `.+?`,
so an origin of `git@github.com:demo/repo?x=1.git` yields
`gh api repos/demo/repo?x=1` and an `href` of `https://github.com/demo/repo?x=1`,
and `git@github.com:demo/repo/../other.git` walks the API path. Requires
control of the local `.git/config`, so someone who can do this can do worse
already. Source: agoge run `dev/local/audit-results/agoge-2026-09-05.md`,
finding 22 (LOW, security lane, status mocked: logging gh shim); decision
2026-09-05: tighten the name group and skip-stub the repo otherwise.

```
Logging shim calls.log: ["api", "repos/demo/repo?x=1"], ["api",
"repos/demo/repo/../other"]; page hrefs and digest headings carry the same.
```

## Solution

Change the two capture groups to `([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)` so
owner and name admit only the characters GitHub allows, and reject a parsed
owner or name equal to `.` or `..` (the character class alone still admits
`git@github.com:../other.git` as owner `..` and `git@github.com:demo/...git`
as repo `..`). An origin that does not match, or whose owner or name is a dot
segment, takes the path a missing remote takes today (the repo lands under
`skipped` with a reason); the current no-match branch in repo_slug already raises a RuntimeError
consumed by collect_repo's skipped-stub handling. Re-check and preserve it;
only add it if absent, with reason `remote: not a github slug: <url>`. A
legitimate remote shape outside that set (none known on GitHub) is skipped
with a reason; that was the option's named drawback.

## Requirements

### Must have

- `git@github.com:demo/repo?x=1.git` and `git@github.com:demo/repo/../other.git`
  do not match `REMOTE_RE`; `git@github.com:../other.git` and
  `git@github.com:demo/...git` are rejected as dot-segment owner or name; in all
  four cases `collect_repo` records the repo as skipped with a reason instead of
  calling gh.
- `git@github.com:demo/repo.git`, `https://github.com/demo/repo`,
  `https://github.com/demo/repo.git/` and `https://github.com/demo/my.repo-2`
  still parse to their owner and name.

### Nice to have

- none

## Implementation

### Module: collect.py

- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: Parse only well-formed GitHub slugs out of a remote.
- **Exports**: `REMOTE_RE`, unchanged callers

### Module: test_collect_repo.py

- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: Pin the accepted and rejected shapes.
- **Exports**: pytest cases

### Dependencies

- collect.py: No dependencies (foundation)
- test_collect_repo.py: Depends on [collect.py]

## Tasks

### Phase 0: Foundation

- [ ] Tighten both capture groups in `REMOTE_RE`, reject `.` and `..` as owner or name, and make sure the no-match branch skips the repo - Acceptance: a new parametrised test `test_remote_re_accepts_github_slugs_and_rejects_query_and_dotdot` covers the four accepted and four rejected shapes above, and a second test `test_an_unparseable_remote_is_skipped_before_any_gh_call` patches `collect.run` (the `make_fake_run` pattern) to return the hostile remote for `git remote get-url origin` and to raise on any `gh` call, runs `collect_repo`, and asserts the repo is skipped with a reason and no `gh` call was made; `uv run pytest skills/brief-portfolio/scripts -q` reports 0 failing.

### Phase 1: Core

- none

## Success Criteria

- The new tests pass; every existing remote-parsing test passes unchanged.
- The report's logging shim records no `api` call carrying `?` or `/../`.
