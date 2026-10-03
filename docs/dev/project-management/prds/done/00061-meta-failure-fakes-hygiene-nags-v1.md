---
default_model: sonnet
model_tier_rationale: exact collector list and ordering given, one additive stub test
design: skip
---

# A repo whose metadata call fails gets "never brushed" and "purge never run" todos

## Problem

`collect_repo` in `skills/brief-portfolio/scripts/collect.py` returns early
when `gh api repos/<o>/<n>` fails, before the purely local collectors run, so
`brush_last_run` and `purge_last_run` are absent and `derive.js` reads absent as
"never": the page nags for hygiene passes that happened yesterday, and the repo
jumps the attention ranking on a false reason. Source: agoge run
`dev/local/audit-results/agoge-2026-09-05.md`, finding 9 (MEDIUM, journey lane,
status mocked: gh shim); decision 2026-09-05: run the branch-free local
collectors before the metadata call.

```
Two scratch repos both brushed and purged on 2026-09-04; shim fails meta for
demo/broken: Todo tab Run /purge-devlocal never run ... demo/broken and Run a
/brush hygiene pass never brushed ... demo/broken; Brief broken 11 never
brushed; demo/repo shows neither.
```

## Solution

Move the four collectors that need no default branch (`prds`,
`changelog_unreleased`, `brush_last_run`, `purge_last_run`) above the metadata
call in `collect_repo`, so their keys are set before any early return. The two
that need the default branch (`branches`, `local`) stay after it. The collector
list is now split in two places; that was the option's named drawback, so one
comment at the split states the rule: needs no default branch, runs before
metadata. Also preserve failed-metadata history semantics: history_counts
adds e:1 when an errors entry starts with meta:, even if the newly collected
local keys exist. Keep the existing generic no-data rule and leave partial
CI failures unmarked, as required by 00056/done00028.

## Requirements

### Must have

- A repo whose metadata call fails still carries `prds`,
  `changelog_unreleased`, `brush_last_run` and `purge_last_run` in `data.json`.
- A repo whose metadata call succeeds produces a record identical to today's
  (same key set and values).
- A metadata failure still has history e:1; local facts do not manufacture
  known-zero remote history counts. Preserve the named existing history regression.
- No brush or purge nag appears for a repo that was brushed and purged, whether
  or not its metadata call failed.

### Nice to have

- none

## Implementation

### Module: collect.py

- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: Collect local facts before asking GitHub anything.
- **Exports**: `collect_repo()`, unchanged signature

### Module: test_collect_repo.py

- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: Pin the key set on the metadata-failure path.
- **Exports**: pytest cases

### Dependencies

- collect.py: No dependencies (foundation)
- test_collect_repo.py: Depends on [collect.py]

## Tasks

### Phase 0: Foundation

- [ ] Reorder the collectors in `collect_repo` - Acceptance: a new test `test_a_failed_metadata_call_still_collects_the_local_hygiene_stamps` builds a `tmp_path` repo with a `dev/local/audit-results/brush-report.md` carrying a `generated:` line and a dated `dev/local/.trash/<date>/` directory, patches `collect.gh_json` to raise `RuntimeError("gh: HTTP 500")` (the seam the existing metadata tests use), runs `collect_repo`, and asserts the returned dict has `brush_last_run`, `purge_last_run`, `prds` and `changelog_unreleased` set and one `errors` entry starting `meta:`; `test_main_history_row_marks_the_repo_whose_metadata_call_failed` still passes, an explicit local-facts-plus-meta-error case has e:1, and `test_history_counts_leaves_a_partly_fetched_repo_unmarked` remains unchanged; the existing `collect_repo` success-path tests pass unchanged; `uv run pytest skills/brief-portfolio/scripts -q` reports 0 failing. (link-ok: the brush report path is a fixture created under tmp_path.)

### Phase 1: Core

- none

## Success Criteria

- The new test passes; every existing `collect_repo` test passes unchanged.
- The report's reproduction shows no brush or purge todo for `demo/broken`.
