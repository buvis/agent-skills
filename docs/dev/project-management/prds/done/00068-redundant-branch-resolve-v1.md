---
default_model: sonnet
model_tier_rationale: two signature edits with the exact call to hoist, one additive counting test
design: skip
---

# collect.py spawns one redundant git rev-parse per repo

> **Closed as superseded, 2026-10-07.** The work landed (`eacc795`, `8786bf2`, `746efc8`), but
> `af1b704` then removed the whole brief-portfolio skill (superseded by the postup gem, PRD 00070)
> before the completion review was recorded. The 2026-09-26 cycle-1 review session ran all four
> reviewers and drafted two rework tasks (a CHANGELOG entry, stronger tests), then died before
> writing its review file. Both are moot with the code gone and were dropped by decision.

## Problem

`collect_branches` (line 190) and `collect_local` (line 364) in
`skills/brief-portfolio/scripts/collect.py` each run
`git rev-parse --abbrev-ref HEAD` to learn the current branch, so every repo
costs 19 subprocesses of which one is a repeat: 26 registered repos spend 26
extra processes out of 494 per run. No budget is stated; observation only.
Source: agoge run `dev/local/audit-results/agoge-2026-09-05.md`, finding 24
(LOW, performance lane, status mocked: gh canned, git real); decision
2026-09-05: resolve the current branch once.

```
In-process counter on collect.run: 1 repo = 19 calls (7 gh, 12 git), 3 repos
= 57; git rev-parse --abbrev-ref appears 2 per repo.
```

## Solution

Resolve `current` once in `collect_repo`, where the default branch is already
known, and pass it to both collectors as a new trailing parameter:
`collect_branches(path, branch, current)` and
`collect_local(path, branch, current)`. Two signatures change; that was the
option's named drawback, and their production call sites and direct-test callers must be updated.
Keep the shared lookup inside error isolation: on failure, omit only branches
and local and append their usual prefixed errors, while other collectors
continue. A metadata-failed/skipped repo never reaches this lookup.

## Requirements

### Must have

- One `git rev-parse --abbrev-ref HEAD` for each repo whose metadata succeeds.
- The `branches` and `local` records are identical to today's for the same
  repo.

### Nice to have

- none

## Implementation

### Module: collect.py

- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: Ask git for the current branch once.
- **Exports**: `collect_branches(path, branch, current)`, `collect_local(path, branch, current)`, `collect_repo()`

### Module: test_collect_repo.py

- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: Count the call.
- **Exports**: pytest cases

### Dependencies

- collect.py: No dependencies (foundation)
- test_collect_repo.py: Depends on [collect.py]

## Tasks

### Phase 0: Foundation

- [ ] Hoist the `rev-parse` into `collect_repo` and thread `current` through both signatures, updating every existing test that calls either collector directly - Acceptance: a new test `test_collect_repo_resolves_the_current_branch_once` wraps `collect.run` with a recording stub (the `make_fake_run` pattern) and asserts `["git", "rev-parse", "--abbrev-ref", "HEAD"]` appears exactly once for one eligible repo; a raising shared lookup leaves other collected fields intact and records branches/local errors without escaping; `rg -c "abbrev-ref" skills/brief-portfolio/scripts/collect.py` prints 1; `uv run pytest skills/brief-portfolio/scripts -q` reports 0 failing.

### Phase 1: Core

- none

## Success Criteria

- The new test passes; the `branches` and `local` tests pass with only their
  call sites updated.
- The same fixture makes one fewer current-branch lookup per eligible repo
  than the immediately preceding implementation. Do not pin a total process
  count: earlier 00062 adds its own count lookup.
