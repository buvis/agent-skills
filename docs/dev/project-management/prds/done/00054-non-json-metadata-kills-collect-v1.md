---
default_model: sonnet
model_tier_rationale: exact except tuple given, additive stub tests
design: skip
consensus_engine: shadow
---

# One repo answering non-JSON to the metadata call kills the whole collect

## Problem

`gh_json` in `skills/brief-portfolio/scripts/collect.py` (about line 60) runs
`gh api` and decodes the stdout with no guard, and the `except` tuple in
`collect_repo` (about line 406) that turns a metadata failure into an `errors`
entry does not include the exception types a non-JSON body raises. So when
`gh api repos/<owner>/<name>` answers with an HTML 502 page or an empty body,
the run dies with a traceback before writing anything: no `data.json`, no
`history.jsonl` row, no digest, for all 26 repos. A 403 body on the same call is
handled (the repo lands in `errors`, exit 0), so only the exception types are
missing. Source: agoge run `dev/local/audit-results/agoge-2026-09-05.md`,
finding 1 (HIGH, integration lane, status mocked: gh shim, suspected in
production); decision 2026-09-05: widen the except at the call site.

```
Shim run run.sh metanonjson (gh answering an HTML body): Traceback ...
collect.py line 60, in gh_json ... json.decoder.JSONDecodeError: Expecting
value: line 1 column 1 (char 0), exit 1, data.json: ABSENT. Empty stdout
instead: AttributeError: 'NoneType' object has no attribute 'get' at line
400. Control, a 403 body on the same call: errors=['meta: gh api: gh: HTTP
403 ...'], exit 0.
```

## Solution

Add `ValueError` (the parent of `json.JSONDecodeError`) and `AttributeError` to
the `except` tuple around the metadata call in `collect_repo`, so an undecodable
or empty body is recorded as `meta: <reason>` in the repo's `errors` and the
run continues to the next repo. No change to `gh_json`'s contract and none to
its other callers: the symptom-at-one-site option was chosen over normalising
inside `gh_json`, because `collect_ci` reads `RuntimeError` as "Actions
disabled" and PRD 00056 owns that branch.

## Requirements

### Must have

- A metadata body that is not JSON records `meta: <exception text>` in that
  repo's `errors`, and the run exits 0 with the other repos collected.
- An empty metadata body does the same instead of raising `AttributeError`.
- The existing 403 path is unchanged.

### Nice to have

- none

## Implementation

### Module: collect.py

- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: Turn every metadata failure shape into an `errors` entry.
- **Exports**: `collect_repo()`, `gh_json()`, unchanged signatures

### Module: test_collect_repo.py

- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: Pin the two new failure shapes with a `collect.run` stub.
- **Exports**: pytest cases

### Dependencies

- collect.py: No dependencies (foundation)
- test_collect_repo.py: Depends on [collect.py]

## Tasks

### Phase 0: Foundation

- [ ] Widen the `except` tuple around the metadata call in `collect_repo` to include `ValueError` and `AttributeError` - Acceptance: two new tests, `test_a_non_json_metadata_body_lands_in_errors_and_the_run_continues` and `test_an_empty_metadata_body_lands_in_errors_and_the_run_continues`, patch `collect.run` (the seam the existing gh-failure tests use) so the `gh api repos/<o>/<n>` call returns `<html>502</html>` and `""` respectively, run `collect_repo`, and assert the returned dict carries exactly one `errors` entry starting with `meta:` and no traceback escapes; an explicit metadata HTTP-403 control preserves today's `meta:` error behavior; `uv run pytest skills/brief-portfolio/scripts -q` reports 0 failing.

### Phase 1: Core

- none

## Success Criteria

- The two new tests pass, and every existing metadata-failure test passes
  unchanged.
- The report's reproduction no longer applies: with the gh shim answering an
  HTML body for one repo, `collect.py` exits 0, writes `data.json`, and that
  repo's `errors` names the decode failure.
