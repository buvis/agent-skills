---
default_model: opus
rework_cap: 5
---

# sweep scans repos in parallel under a sweep-wide deadline

## Problem

`scan()` in `skills/sweep-fix/scripts/sweep.py` (defined line 292) is a plain `for repo in repos`
loop on line 319 with no concurrency and no global deadline. The per-call
`DEFAULT_SCAN_TIMEOUT = 30` (line 88) bounds one subprocess, never the sweep, so a 26-row registry
has a worst case of 27 x 30s = 810s with no ceiling and no progress signal. It is latent at 0.72s
today and lands the first time a repo sits on a slow mount or a huge tree. Source: agoge run
`docs/dev/project-management/audit-results/agoge-2026-08-31.md`, finding 26 (MEDIUM, performance
lane); decision 2026-09-02: thread pool plus a wall-clock deadline (the eight-thread `collect.py`
it was modelled on left with brief-portfolio in commit af1b704; lines re-verified 2026-10-17).

```
wall ~ sum of subprocess time at every size: 5 entries -> sum=0.69s,
wall=0.70s, wall/sum=1.01; 10 entries -> sum=1.47s, wall=1.49s,
wall/sum=1.01; 5->10 repos is 2.13x wall, reproduced at 2.06x. Real 26-row
registry: search_subprocesses=27, per_call_timeout_s=[30] on every call.
--cap 3 and the 30s per-call timeout both hold as documented; what neither
bounds is the sweep, whose worst case is 27 x 30s = 810s.
```

## Solution

Submit `_scan_repo` (`skills/sweep-fix/scripts/sweep.py:270`, signature `_scan_repo(repo, pattern, kind, ast_grep_error,
timeout)`) to a `ThreadPoolExecutor(max_workers=8)`. It already returns an isolated
`(cwd_key, hits, error)` tuple, so nothing per repo changes. Collect futures in registry order, not
completion order, so hit rows stay diffable. Add a sweep-wide deadline measured with
`time.monotonic()` (`sweep.py` imports no `time` today; add `import time` so tests can patch
`sweep.time.monotonic`): a repo whose future has not finished when the deadline passes is recorded
in `failed` under a new `DEADLINE_REASON` constant, keyed by `_repo_cwd_and_targets(repo)[0]`
(`skills/sweep-fix/scripts/sweep.py:218-228`), and
`render_report` (`skills/sweep-fix/scripts/sweep.py:465`) prints one `Partial:` line above the
`Failed:` block `_render_failed_section` emits (`skills/sweep-fix/scripts/sweep.py:402-410`).

## Requirements

### Must have
- `scan()` runs `_scan_repo` under `ThreadPoolExecutor(max_workers=8)` and keeps its
  `(hits, suppressed, failed)` return shape, its `cap` behaviour and its `suppressed` counts.
- `hits` are ordered by each repo's position in `repos`, then by `_scan_repo`'s own order.
- `scan()` takes `deadline=None` seconds; an unfinished repo lands in `failed` as
  `DEADLINE_REASON`, never dropped.
- `sweep.py` gains `--deadline`, a positive int of seconds defaulting to 300, validated by
  `_positive_int` (`skills/sweep-fix/scripts/sweep.py:500-504`), which today hardcodes the message
  `--cap must be a positive integer` and so must take the flag name it reports (a one-argument
  factory or `functools.partial`), and `main()` passes it to `scan()`.
- `render_report` emits `Partial: N repos not scanned (sweep deadline expired)` whenever a `failed` reason equals `DEADLINE_REASON`.
- `skills/sweep-fix/SKILL.md:38` lists `--deadline N` in its usage line.

### Nice to have
- none

## Implementation

### Module: sweep.py
- **Location**: `skills/sweep-fix/scripts/`
- **Responsibility**: runs the cross-repo search and renders the report
- **Exports**: `scan()`, `render_report()`, `_parse_args()`, `DEADLINE_REASON`
- New symbols: `DEADLINE_REASON`

### Module: test_sweep_scan.py
- **Location**: `skills/sweep-fix/scripts/`
- **Responsibility**: unit tests for `scan()`
- **Exports**: `test_scan_runs_repo_searches_concurrently()`, `test_scan_orders_hits_by_registry_position_not_completion_order()`, `test_scan_records_an_unfinished_repo_when_the_deadline_expires()`
- New symbols: `test_scan_runs_repo_searches_concurrently`, `test_scan_orders_hits_by_registry_position_not_completion_order`, `test_scan_records_an_unfinished_repo_when_the_deadline_expires`

### Module: test_sweep_main.py
- **Location**: `skills/sweep-fix/scripts/`
- **Responsibility**: CLI end-to-end tests
- **Exports**: `test_main_rejects_a_deadline_of_zero()`
- New symbols: `test_main_rejects_a_deadline_of_zero`

### Module: test_sweep_render_report.py
- **Location**: `skills/sweep-fix/scripts/`
- **Responsibility**: unit tests for `render_report()`
- **Exports**: `test_render_report_prints_a_partial_line_for_deadline_failures()`
- New symbols: `test_render_report_prints_a_partial_line_for_deadline_failures`

### Module: SKILL.md
- **Location**: `skills/sweep-fix/`
- **Responsibility**: documents the sweep invocation, usage line at line 38
- **Exports**: the `sweep.py` usage line

### Dependencies
- sweep.py: No dependencies (foundation)
- test_sweep_scan.py: Depends on [sweep.py]
- test_sweep_main.py: Depends on [sweep.py]
- test_sweep_render_report.py: Depends on [sweep.py]
- SKILL.md: Depends on [sweep.py]

## Tasks

### Phase 0: Foundation

- [ ] Replace the serial loop in `scan()` with `ThreadPoolExecutor(max_workers=8)`, submitting one `_scan_repo` per repo and reading results back in `repos` order - Acceptance: `rg -n "ThreadPoolExecutor\(max_workers=8\)" skills/sweep-fix/scripts/sweep.py` matches one line inside `scan`; `uv run pytest skills/sweep-fix/scripts -q` reports 0 failed and 0 errors.
- [ ] Add `test_scan_runs_repo_searches_concurrently` to `skills/sweep-fix/scripts/test_sweep_scan.py`, monkeypatching `sweep._scan_repo` with a stub that waits on a shared `threading.Barrier(3, timeout=5)` before returning - Acceptance: `uv run pytest "skills/sweep-fix/scripts/test_sweep_scan.py::test_scan_runs_repo_searches_concurrently" -q` passes, and a serial `scan()` makes the barrier raise BrokenBarrierError, so the test binds to overlap rather than to a clock reading.
- [ ] Add `test_scan_orders_hits_by_registry_position_not_completion_order`, monkeypatching `sweep._scan_repo` so the last repo returns first - Acceptance: for a three-repo registry passed in order the test asserts `[h["repo"] for h in hits] == [str(repo_a), str(repo_b), str(repo_c)]`, and `uv run pytest "skills/sweep-fix/scripts/test_sweep_scan.py::test_scan_orders_hits_by_registry_position_not_completion_order" -q` passes.
- [ ] Add `import time` (absent today), the `deadline` parameter and the `DEADLINE_REASON` constant to `sweep.py`, then add `test_scan_records_an_unfinished_repo_when_the_deadline_expires` monkeypatching `sweep.time.monotonic` with a stub whose second reading is past the expiry - Acceptance: the test asserts `failed[str(repo_b)] == sweep.DEADLINE_REASON` and that `hits` still holds the finished repo's rows; `uv run pytest "skills/sweep-fix/scripts/test_sweep_scan.py::test_scan_records_an_unfinished_repo_when_the_deadline_expires" -q` passes.
- [ ] Emit the `Partial:` line from `render_report` when any `failed` reason is `DEADLINE_REASON`, give `_positive_int` the flag name it reports (today it hardcodes `--cap`; `test_main_rejects_cap_of_zero` and `test_main_rejects_negative_cap` at `skills/sweep-fix/scripts/test_sweep_main.py:425-452` only assert `cap` in the output, so they keep passing), add `--deadline` to `_parse_args` with that validator bound to `--deadline` and `default=300`, pass it into `scan()` from `main()`, and add `--deadline N` to `skills/sweep-fix/SKILL.md:38` - Acceptance: `test_main_rejects_a_deadline_of_zero` (modelled on `test_main_rejects_cap_of_zero`) asserts `sweep.main(argv + ["--deadline", "0"])` raises `SystemExit` with stderr containing `--deadline must be a positive integer`; `rg -n -- "--deadline" skills/sweep-fix/SKILL.md` matches line 38; `uv run pytest skills/sweep-fix/scripts -q` reports 0 failed and 0 errors.
- [ ] Add `test_render_report_prints_a_partial_line_for_deadline_failures` to `skills/sweep-fix/scripts/test_sweep_render_report.py`, passing a `failed` mapping with two `DEADLINE_REASON` entries and one other reason - Acceptance: the test asserts the report holds `Partial: 2 repos not scanned (sweep deadline expired)` on a line above the `Failed:` line, and `uv run pytest "skills/sweep-fix/scripts/test_sweep_render_report.py::test_render_report_prints_a_partial_line_for_deadline_failures" -q` passes.

## Success Criteria

- `uv run pytest skills/sweep-fix/scripts -q` reports 0 failed and 0 errors.
- `scan()` over three repos whose stubbed `_scan_repo` blocks on a three-party barrier completes
  instead of raising, proving overlap without timing a clock.
- Two `sweep.main` runs over the same fixture registry, each with an explicit `--out` (a default
  name that already exists is suffixed `-2` by `_resolve_report_path`,
  `skills/sweep-fix/scripts/sweep.py:521-545`), write
  byte-identical reports, so ordering did not become completion-dependent.
- `rg -n "DEADLINE_REASON" skills/sweep-fix/scripts/sweep.py` matches the constant, the `failed`
  write in `scan`, and the `Partial:` branch in `render_report`.
