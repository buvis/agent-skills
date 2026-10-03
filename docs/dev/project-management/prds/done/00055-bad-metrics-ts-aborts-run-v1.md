---
default_model: sonnet
model_tier_rationale: exact validation expression given, additive tests under a fake home
design: skip
consensus_engine: shadow
---

# One bad ts in the local skills metrics file aborts the run after all the GitHub work

## Problem

`collect_claude_skill_adherence` in `skills/brief-portfolio/scripts/collect.py`
sorts the `ts` values it reads from `~/.local/share/agents/metrics/skills.jsonl`;
a row whose `ts` is a number instead of a string raises `TypeError` (about line
280), and `main()` calls that reader unguarded (about line 513) after every
`gh` call has completed, so nothing is written. The sibling reader
`collect_audit_cadence` is wrapped and only WARNs, but it keeps the newest `ts`
per skill by string comparison, so `not-a-date` or `2099-01-01` wins and
`derive.js`'s `daysAgo` on a future date goes negative: that audit's nag never
fires (report finding 20, LOW, folded in here by decision). Source: agoge run
`dev/local/audit-results/agoge-2026-09-05.md`, findings 2 (HIGH, integration
lane, mocked: HOME redirected to a scratch metrics file) and 20 (LOW,
integration, mocked); decision 2026-09-05: guard the call and validate `ts` in
both readers.

```
metrics-crash.sh with one row {"skill": "x", "ts": 12345}: WARN audit_cadence:
'int' object is not subscriptable, then Traceback ... line 513, in main ...
TypeError: '<' not supported between instances of 'int' and 'str', exit 1,
output directory empty.
Rows {"ts":"not-a-date"} and {"ts":"2099-01-01T00:00:00+00:00"} produce
{'claude-checkup:audit-sessions': '2099-01-01', 'x': 'not-a-date'}.
```

## Solution

Two changes in `collect.py`. First, wrap the `collect_claude_skill_adherence`
call in `main()` the way `collect_external_section` is wrapped: on any
exception, `WARN skill_adherence: <exc>` to stderr and store `None`, so a bad
row costs one metric, not the run. Second, both readers validate each row's
`ts` through one helper, `_parse_ts(value)`: return
a timezone-aware datetime normalized to UTC when `value` is a string that
parses with datetime.fromisoformat, contains a timezone, and is not after
UTC now; otherwise return None, including naive dates/times. Catch parse/type
failures inside the helper. Rows yielding None are silently skipped. Cadence
uses parsed newest-wins comparisons; adherence retains its 30-day window. The page shows no skill-adherence tile that run and gives no hint why:
that was the option's named drawback.

## Requirements

### Must have

- A `skills.jsonl` row with a non-string `ts` no longer aborts the run: the
  run exits 0 and writes `data.json`, using the remaining valid rows.
- An unexpected reader exception costs only that metric and prints one
  `WARN skill_adherence:`; filtering a malformed row does not itself warn.
- Rows whose `ts` does not parse as ISO 8601, or lies in the future, are
  ignored by both `collect_audit_cadence` and
  `collect_claude_skill_adherence`.
- Valid rows behave exactly as today: the existing cadence and adherence tests
  pass unchanged.

### Nice to have

- none

## Implementation

### Module: collect.py

- **Location**: `skills/brief-portfolio/scripts/`
- **Responsibility**: Read the shared metrics file without trusting it.
- **Exports**: `_parse_ts()`, `collect_audit_cadence()`, `collect_claude_skill_adherence()`, `main()`

### Module: test_collect_local.py and test_collect_pipeline.py

- **Location**: `skills/brief-portfolio/scripts/` (the reader tests in test_collect_local.py, the `main()` test in test_collect_pipeline.py)
- **Responsibility**: Pin the bad-row shapes under a fake home.
- **Exports**: pytest cases

### Dependencies

- collect.py: No dependencies (foundation)
- test_collect_local.py, test_collect_pipeline.py: Depend on [collect.py]

## Tasks

### Phase 0: Foundation

- [ ] Add `_parse_ts` and use it in both readers - Acceptance: new tests `test_audit_cadence_ignores_unparseable_and_future_timestamps` and `test_skill_adherence_ignores_non_string_timestamps` point `Path.home` at a `tmp_path` (the seam the existing `main()`-level metrics test uses at `test_collect_pipeline.py:227`; the reader tests pass the file as `base`, which also works) whose `skills.jsonl` holds rows with `ts` of `12345`, `"not-a-date"`, `"2099-01-01T00:00:00+00:00"` and one valid past timestamp, plus naive date/time strings, and assert cadence reports the surviving valid day while adherence preserves its count/distinct/top schema and counts only valid rows within the last 30 days; `uv run pytest skills/brief-portfolio/scripts -q` reports 0 failing.

### Phase 1: Core

- [ ] Wrap the `collect_claude_skill_adherence` call in `main()` like `collect_external_section` (depends on: Phase 0) - Acceptance: a new test `test_a_raising_skill_adherence_reader_costs_one_metric_not_the_run` patches `collect.collect_claude_skill_adherence` to raise (the pattern the existing raising `collect_audit_cadence` test uses), runs `main()` against a fake registry, and asserts exit 0, `data.json` written, the stored value `None`, and stderr containing `WARN skill_adherence`; `uv run pytest skills/brief-portfolio/scripts -q` reports 0 failing.

## Success Criteria

- The three new tests pass; the existing cadence and adherence tests pass
  unchanged.
- The report's `metrics-crash.sh` reproduction exits 0 and writes `data.json`.
