---
default_model: opus
rework_cap: 5
---

# sweep scans repos in parallel under a sweep-wide deadline

## Problem

`scan()` in `skills/sweep-fix/scripts/sweep.py` (defined line 270) is a plain `for repo in repos`
loop on line 297 with no concurrency and no global deadline, while `collect.py` fans the same
registry out over eight threads at `skills/brief-portfolio/scripts/collect.py:494`. The per-call
`DEFAULT_SCAN_TIMEOUT = 30` (line 83) bounds one subprocess, never the sweep, so a 26-row registry
has a worst case of 27 x 30s = 810s with no ceiling and no progress signal. It is latent at 0.72s
today and lands the first time a repo sits on a slow mount or a huge tree. Source: agoge run
dev/local/audit-results/agoge-2026-08-31.md, finding 26 (MEDIUM, performance lane); decision
2026-09-02: thread pool plus a wall-clock deadline.

```
wall ~ sum of subprocess time at every size: 5 entries -> sum=0.69s,
wall=0.70s, wall/sum=1.01; 10 entries -> sum=1.47s, wall=1.49s,
wall/sum=1.01; 5->10 repos is 2.13x wall, reproduced at 2.06x. Real 26-row
registry: search_subprocesses=27, per_call_timeout_s=[30] on every call.
--cap 3 and the 30s per-call timeout both hold as documented; what neither
bounds is the sweep, whose worst case is 27 x 30s = 810s.
```

## Solution

Submit `_scan_repo` to a `ThreadPoolExecutor(max_workers=8)`, mirroring `collect.py:494`. It
already returns an isolated `(cwd_key, hits, error)` tuple, so nothing per repo changes. Collect
futures in registry order, not completion order, so hit rows stay diffable. Add a sweep-wide
deadline measured with `time.monotonic()`: a repo whose future has not finished when the deadline
passes is recorded in `failed` under a new `DEADLINE_REASON` constant, keyed by
`_repo_cwd_and_targets(repo)[0]`, and `render_report` prints one `Partial:` line above `Failed:`.

## Requirements

### Must have
- `scan()` runs `_scan_repo` under `ThreadPoolExecutor(max_workers=8)` and keeps its
  `(hits, suppressed, failed)` return shape, its `cap` behaviour and its `suppressed` counts.
- `hits` are ordered by each repo's position in `repos`, then by `_scan_repo`'s own order.
- `scan()` takes `deadline=None` seconds; an unfinished repo lands in `failed` as
  `DEADLINE_REASON`, never dropped.
- `sweep.py` gains `--deadline`, a positive int of seconds
  defaulting to 300, validated
  by the existing `_positive_int`, and `main()` passes it to `scan()`.
- `render_report` emits `Partial: N repos not scanned (sweep deadline expired)` whenever a `failed` reason equals `DEADLINE_REASON`.
- `skills/sweep-fix/SKILL.md:38` lists `--deadline N` in its usage line.

### Nice to have
- none

## Implementation

### Module: sweep.py
- **Location**: `skills/sweep-fix/scripts/`
- **Responsibility**: runs the cross-repo search and renders the report
- **Exports**: `scan()`, `render_report()`, `_parse_args()`, `DEADLINE_REASON`

### Module: test_sweep_scan.py
- **Location**: `skills/sweep-fix/scripts/`
- **Responsibility**: unit tests for `scan()`
- **Exports**: `test_scan_runs_repo_searches_concurrently()`, `test_scan_orders_hits_by_registry_position_not_completion_order()`, `test_scan_records_an_unfinished_repo_when_the_deadline_expires()`

### Module: test_sweep_main.py
- **Location**: `skills/sweep-fix/scripts/`
- **Responsibility**: CLI end-to-end tests
- **Exports**: `test_main_rejects_a_deadline_of_zero()`

### Module: SKILL.md
- **Location**: `skills/sweep-fix/`
- **Responsibility**: documents the sweep invocation, usage line at line 38
- **Exports**: the `sweep.py` usage line

### Dependencies
- sweep.py: No dependencies (foundation)
- test_sweep_scan.py: Depends on [sweep.py]
- test_sweep_main.py: Depends on [sweep.py]
- SKILL.md: Depends on [sweep.py]

## Tasks

### Phase 0: Foundation

- [ ] Replace the serial loop in `scan()` with `ThreadPoolExecutor(max_workers=8)`, submitting one `_scan_repo` per repo and reading results back in `repos` order - Acceptance: `rg -n "ThreadPoolExecutor\(max_workers=8\)" skills/sweep-fix/scripts/sweep.py` matches one line inside `scan`; `uv run pytest skills/sweep-fix/scripts -q` reports 0 failed and 0 errors.
- [ ] Add `test_scan_runs_repo_searches_concurrently` to `skills/sweep-fix/scripts/test_sweep_scan.py`, monkeypatching `sweep._scan_repo` with a stub that waits on a shared `threading.Barrier(3, timeout=5)` before returning - Acceptance: `uv run pytest "skills/sweep-fix/scripts/test_sweep_scan.py::test_scan_runs_repo_searches_concurrently" -q` passes, and a serial `scan()` makes the barrier raise `BrokenBarrierError`, so the test binds to overlap rather than to a clock reading.
- [ ] Add `test_scan_orders_hits_by_registry_position_not_completion_order`, monkeypatching `sweep._scan_repo` so the last repo returns first - Acceptance: for a three-repo registry passed in order the test asserts `[h["repo"] for h in hits] == [str(repo_a), str(repo_b), str(repo_c)]`, and `uv run pytest "skills/sweep-fix/scripts/test_sweep_scan.py::test_scan_orders_hits_by_registry_position_not_completion_order" -q` passes.
- [ ] Add the `deadline` parameter and the `DEADLINE_REASON` constant to `sweep.py`, then add `test_scan_records_an_unfinished_repo_when_the_deadline_expires` monkeypatching `sweep.time.monotonic` with a stub whose second reading is past the expiry - Acceptance: the test asserts `failed[str(repo_b)] == sweep.DEADLINE_REASON` and that `hits` still holds the finished repo's rows; `uv run pytest "skills/sweep-fix/scripts/test_sweep_scan.py::test_scan_records_an_unfinished_repo_when_the_deadline_expires" -q` passes.
- [ ] Emit the `Partial:` line from `render_report` when any `failed` reason is `DEADLINE_REASON`, add `--deadline` to `_parse_args` with `type=_positive_int, default=300`, pass it into `scan()` from `main()`, and add `--deadline N` to `skills/sweep-fix/SKILL.md:38` - Acceptance: `test_main_rejects_a_deadline_of_zero` asserts `sweep.main(argv + ["--deadline", "0"])` raises `SystemExit` with stderr containing `--deadline must be a positive integer`; `rg -n -- "--deadline" skills/sweep-fix/SKILL.md` matches line 38; `uv run pytest skills/sweep-fix/scripts -q` reports 0 failed and 0 errors.

## Success Criteria

- `uv run pytest skills/sweep-fix/scripts -q` reports 0 failed and 0 errors.
- `scan()` over three repos whose stubbed `_scan_repo` blocks on a three-party barrier completes
  instead of raising, proving overlap without timing a clock.
- Two `sweep.main` runs over the same fixture registry write byte-identical reports, so ordering
  did not become completion-dependent.
- `rg -n "DEADLINE_REASON" skills/sweep-fix/scripts/sweep.py` matches the constant, the `failed`
  write in `scan`, and the `Partial:` branch in `render_report`.
