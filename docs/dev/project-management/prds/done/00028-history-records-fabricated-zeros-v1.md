---
default_model: sonnet
rework_cap: 5
design: skip
---

# Trend history permanently records fabricated zero counts for repos whose collection failed

## Problem

`history_counts` in `skills/brief-portfolio/scripts/collect.py:345-354` reads
every field with `.get(key, [])`, so a repo whose GitHub metadata call failed
(`collect_repo` returns early at line 401 with `errors` and no data keys) is
appended to `history.jsonl` at lines 508-511 as a complete all-zero observation
with no error marker. The file is append-only, so the Brief's trend sparkline
plots a fabricated dip no later run can correct, and every failed collection
adds another false point. The run-level `skipped` count does not cover it: such
a repo is not "skipped", it stays in `repos`, so `historySeries`
(`skills/brief-portfolio/app/src/lib/derive.js:396-402`) marks the run complete
and `Brief.svelte:25` plots it. This is the one collection-failure finding that
is permanent rather than recomputed each run. Source: agoge run
dev/local/audit-results/agoge-2026-08-31.md, finding 20 (MEDIUM, integration
lane); decision 2026-09-02: accepted, emit an error marker and have the
sparkline treat it as a gap.

```
The written row:
{"at": "2026-08-31T02:00:42+00:00", "skipped": 1, "repos": {"acme/widget":
{"c":0,"i":0,"p":0,"a":0,"f":0,"d":0,"ah":0,"w":0,"b":0,"s":0,"u":0}}}
smoke.test.js filters history rows lacking a skipped key as incomplete runs;
a row for a failed repo passes that filter.
```

## Solution

Change both sides in one PRD so no half-marked row can exist. Collector: when a
repo carries `errors` and none of the keys `history_counts` reads (`commits`,
`issues`, `prs`, `security`, `ci`, `local`, `prds`, `stars`,
`unreleased_commits`), add `"e": 1` to its history record beside the counts, so
a partial failure that still collected data stays unmarked. Chart: a run whose
`repos` map holds any `e`-marked entry is not plottable as real data, so
`historySeries` reports it as `incomplete`. `Brief.svelte` needs no change, its existing
`.filter((h) => !h.incomplete)` then drops the point exactly as it drops a run
with skipped repos.

## Requirements

### Must have
- A repo with `errors` and no collected data keys is written to
  `history.jsonl` with `"e": 1` beside its counts.
- A repo that collected data keeps its record unchanged, with no `e` key, even
  when it carries a non-fatal error such as a fetch timeout.
- `historySeries` marks a run incomplete when any repo entry in it carries `e`,
  and keeps its current behaviour for `skipped`.
- Old rows without `e` keep reading as complete runs: the change adds a key and
  never reinterprets an existing one.

### Nice to have
- none

## Implementation

### Module: collector
- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: build each repo's history record and append the run row
- **Exports**: `history_counts()`, `main()`

### Module: collector tests
- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: rules `collect.py` must hold, including the history row
- **Exports**: `test_history_counts_marks_a_repo_with_errors_and_no_data`, `test_history_counts_leaves_a_partial_failure_unmarked`, `test_main_history_row_marks_the_repo_whose_metadata_call_failed` (all new)

### Module: history derivation
- **Location**: `skills/brief-portfolio/app/src/lib/`
- **Responsibility**: turn `history.jsonl` rows into plottable trend points
- **Exports**: `historySeries()`

### Module: app suites
- **Location**: `skills/brief-portfolio/app/`, `skills/brief-portfolio/app/src/lib/`
- **Responsibility**: unit assertions on `historySeries` and the rendered trend label
- **Exports**: new assertions in `derive.test.js`, new test in `smoke.test.js`

### Module: built template
- **Location**: `skills/brief-portfolio/assets/`
- **Responsibility**: the pre-built app the smoke suite mounts
- **Exports**: `template.html`, a build artifact with no exports

### Dependencies
- collector: No dependencies (foundation)
- history derivation: No dependencies (foundation)
- collector tests: Depends on [collector]
- built template: Depends on [history derivation]
- app suites: Depends on [built template]

## Tasks

### Phase 0: Foundation

- [ ] In `skills/brief-portfolio/scripts/collect.py`, have `history_counts` add `"e": 1` to its returned dict when `repo.get("errors")` is non-empty and none of `commits`, `issues`, `prs`, `security`, `ci`, `local`, `prds`, `stars`, `unreleased_commits` is a key of `repo` - Acceptance: `uv run pytest skills/brief-portfolio/scripts/test_collect.py -q` exits 0, and a new `test_history_counts_marks_a_repo_with_errors_and_no_data` asserts `history_counts({"owner": "acme", "name": "widget", "errors": ["meta: gh: not authenticated"]})["e"] == 1`.
- [ ] Add `test_history_counts_leaves_a_partial_failure_unmarked` to `skills/brief-portfolio/scripts/test_collect.py`: a repo carrying `errors` of `["fetch: timeout"]` plus a `commits` key gets no marker - Acceptance: `uv run pytest skills/brief-portfolio/scripts/test_collect.py::test_history_counts_leaves_a_partial_failure_unmarked -q` reports `1 passed`, and the test asserts `"e" not in history_counts({"errors": ["fetch: timeout"], "commits": []})`.
- [ ] Add `test_main_history_row_marks_the_repo_whose_metadata_call_failed` to `skills/brief-portfolio/scripts/test_collect.py`, reusing the existing `run_collector` helper (its `make_fake_run` fails every `gh` call, which is exactly the metadata failure) - Acceptance: `uv run pytest skills/brief-portfolio/scripts/test_collect.py::test_main_history_row_marks_the_repo_whose_metadata_call_failed -q` reports `1 passed`, and the test reads the last line of `history.jsonl` and asserts `row["repos"]["acme/alpha"]["e"] == 1`.
- [ ] In `skills/brief-portfolio/app/src/lib/derive.js`, change `historySeries`'s `incomplete` to `(h.skipped ?? 0) > 0 || Object.values(h.repos ?? {}).some((c) => c.e)` and extend `derive.test.js` with a row whose single repo carries `e: 1` - Acceptance: `npm --prefix skills/brief-portfolio/app test` reports `# fail 0`, and `derive.test.js` asserts `historySeries([{ at: 'd1', repos: { 'o/r': { i: 1, e: 1 } } }])[0].incomplete === true`.
- [ ] Rebuild the template: `npm --prefix skills/brief-portfolio/app run build`, then copy `skills/brief-portfolio/app/dist/index.html` over `skills/brief-portfolio/assets/template.html` - Acceptance: `rg --count-matches "__PORTFOLIO_PAYLOAD__" skills/brief-portfolio/assets/template.html` prints `1`, and `rg --count-matches "open items across" skills/brief-portfolio/assets/template.html` prints `1`.
- [ ] Add `Brief tab trend sparkline skips a run where a repo failed to collect` to `skills/brief-portfolio/app/smoke.test.js`, modelled on the existing four-row trend test at lines 357-375 with a fifth row `{ at: ..., repos: { 'o/r': { i: 0, e: 1 } } }` - Acceptance: `npm --prefix skills/brief-portfolio/app test` reports `# fail 0`, names the new test as passing, and its `# pass` total is 17 (16 today plus this one); the new test asserts the trend label still reads `open items across 3 briefs`.

## Success Criteria

- A collector run where one repo's metadata call fails appends a row whose entry
  for that repo carries `"e": 1` and whose other repos carry no `e` key.
- `historySeries` returns `incomplete: true` for that row, so the sparkline
  plots one fewer point instead of a zero.
- `uv run pytest skills/brief-portfolio/scripts/test_collect.py -q` exits 0
  and `npm --prefix skills/brief-portfolio/app test` reports `# fail 0`.
- Rows already in the operator's `history.jsonl` stay as they are: the
  historical window remains wrong, which is a known limit of this fix, not a
  regression to chase.
