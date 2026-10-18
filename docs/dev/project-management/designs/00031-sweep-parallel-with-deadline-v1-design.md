# Design: sweep scans repos in parallel under a sweep-wide deadline

## Architecture fit

`skills/sweep-fix/scripts/sweep.py` is a single-module CLI script (no package layout, no
app framework) wired together in `main()`: `enumerate_repos` -> `scan` -> (maybe)
`verify_control` -> `render_report` -> write. This PRD touches only the `scan()` layer and
the two call sites around it (`render_report`'s failure branch, `main()`'s arg parsing). No
new module, no new architectural seam — `scan()` already isolates per-repo failures into
`failed` by catching exceptions from `_scan_repo`, which is exactly the isolation boundary a
thread pool needs (a worker that raises must not corrupt another worker's hit list; it
already returns its own error string instead of raising past `_scan_repo`).

## Module placement

All changes are edits to existing files, no new modules:

- `skills/sweep-fix/scripts/sweep.py` — `scan()` rewritten to submit `_scan_repo` calls to a
  `ThreadPoolExecutor`; new `import time`; new `DEADLINE_REASON` constant; `_positive_int`
  parameterized by flag name; `_parse_args` gains `--deadline`; `main()` passes
  `args.deadline` to `scan()`; `render_report` (via a new `_render_partial_section` helper,
  mirroring the existing `_render_suppressed_section`/`_render_failed_section` pair) emits
  the `Partial:` line.
- `skills/sweep-fix/scripts/test_sweep_scan.py` — three new tests (concurrency, ordering,
  deadline).
- `skills/sweep-fix/scripts/test_sweep_main.py` — one new test (`--deadline 0` rejection).
- `skills/sweep-fix/scripts/test_sweep_render_report.py` — one new test (`Partial:` line).
- `skills/sweep-fix/SKILL.md` — usage line at line 38 gains `[--deadline N]`.

## Interfaces & contracts

```python
DEADLINE_REASON = "sweep deadline expired"
```

```python
def scan(pattern, kind, repos, cap=20, timeout=DEFAULT_SCAN_TIMEOUT, deadline=None):
    """... (existing docstring, plus:)

    `deadline` is an optional wall-clock budget in seconds for the WHOLE sweep,
    measured with `time.monotonic()` from the first call. When set and a repo's
    future has not completed by the time its result is collected and the
    deadline has passed, that repo is recorded in `failed` under
    `DEADLINE_REASON` instead of being awaited further. A future already
    running at that point is not cancelled (ThreadPoolExecutor cannot cancel a
    running thread) and its result, if it later arrives, is discarded; a
    future not yet started (still queued behind the 8 workers) IS cancelled,
    by the post-loop `shutdown(cancel_futures=True)` call. `deadline=None` preserves exact
    current behavior (no deadline, unbounded wait per repo, timeout is the only
    bound).
    """
```

The CLI never exposes `deadline=None`: `--deadline` is a positive int defaulting to 300 with
no "disable" value (the PRD does not ask for one). `deadline=None` is reachable only from
direct `scan()` callers — `verify_control`'s internal single-repo check (deliberately
undeadlined, see Data flow) and the test suite's no-deadline cases — never from `main()`.

Body contract (the ordering and isolation guarantees the tests pin):

- Create `executor = ThreadPoolExecutor(max_workers=8)` **without** a `with` statement.
  Submit one `executor.submit(_scan_repo, repo, pattern, kind, ast_grep_error, timeout)`
  per entry in `repos`, collecting the returned `Future` objects into a list **in `repos`
  order** (so the list of futures and the list of repos share an index). The `with` form is
  deliberately rejected — see the shutdown bullet below.
- Compute `start = time.monotonic()` once, before submitting (only when `deadline is not
  None`; when `deadline is None` no monotonic call happens at all — this keeps
  `test_scan_runs_repo_searches_concurrently`, which does not patch `sweep.time.monotonic`,
  from needing to).
- Iterate the futures list **in `repos` order** (not `as_completed`), and for each:
  - if `deadline is not None` and `time.monotonic() - start >= deadline` and
    `not future.done()`: record `failed[str(_repo_cwd_and_targets(repo)[0])] =
    DEADLINE_REASON`, set a local `deadline_hit = True`, and move to the next repo without
    calling `future.result()` (never block past the deadline on an unfinished future).
  - otherwise: call `future.result()` (blocks if still running and under deadline), unpack
    `(cwd_key, repo_hits, error)`, and apply the existing cap/`suppressed`/`failed`/`hits`
    logic unchanged.
- **Shutdown, after the collection loop, in a `finally` block:** call
  `executor.shutdown(wait=not deadline_hit, cancel_futures=deadline_hit)`. When the deadline
  never tripped, every future was already awaited via `.result()` in the loop above, so
  `wait=True` there is a no-op (nothing left running) and this exactly matches today's
  blocking behavior. When the deadline tripped, `cancel_futures=True` drops every
  **not-yet-started** future immediately (the repos still queued behind the 8 live
  workers — the majority of the PRD's "810s worst case" scenario) without blocking;
  `wait=False` means `scan()` returns without waiting for whatever is still **running** in
  the 8 live worker slots at trip time to finish. This is the fix for the blocker a cross-model
  review raised against an earlier draft: using `with ThreadPoolExecutor(...) as executor:`
  calls `shutdown(wait=True)` on exit regardless of `deadline_hit`, which blocked `scan()`'s
  return on every already-submitted repo (including ones still queued, not just running
  ones) — up to `ceil(len(repos) / 8) * DEFAULT_SCAN_TIMEOUT` seconds of extra wait past the
  deadline, defeating the PRD's "no ceiling" complaint rather than fixing it. The explicit
  `executor`/`finally` form bounds the extra wait after a deadline trip to at most one
  subprocess-timeout wave across the ≤8 workers already running when the deadline hit, not
  one wave per remaining repo. Those ≤8 straggling threads are not daemonized and
  `concurrent.futures` registers an interpreter-exit hook that joins them before the
  **process** (not the `scan()` call) truly exits — acceptable, since they are each already
  bounded by the existing per-call `timeout` (`DEFAULT_SCAN_TIMEOUT=30` by default) and this
  matches the already-documented Risks & edge cases note on thread leakage below, which this
  bullet narrows rather than duplicates.
- `hits` therefore stays ordered by `repos` position, exactly as the serial loop produced
  it — switching the wait strategy from `as_completed` to the pre-built ordered list is
  what keeps `test_scan_orders_hits_by_registry_position_not_completion_order` passing with
  no change to its assertion.
- `_scan_repo`'s own three-tuple contract, `_repo_cwd_and_targets`, and the `ast_grep_error`
  precomputation in `scan()` (resolved once, before the loop, exactly as today) are
  untouched — the dict-entry (`{"error": ...}`) and bare-`Path` shapes both still flow
  through `_scan_repo` unchanged.

```python
def _positive_int(flag_name):
    """Return an `argparse` type-callable that parses a positive int, raising
    `argparse.ArgumentTypeError(f"{flag_name} must be a positive integer")` on
    zero, negative, or unparseable input."""
    def _parse(value):
        parsed = int(value)
        if parsed <= 0:
            raise argparse.ArgumentTypeError(f"{flag_name} must be a positive integer")
        return parsed
    return _parse
```

Call sites:

```python
parser.add_argument("--cap", type=_positive_int("--cap"), default=20)
parser.add_argument("--deadline", type=_positive_int("--deadline"), default=300)
```

(`_positive_int` becomes a factory — `_positive_int("--cap")` — rather than a type-callable
itself; every existing call site that passes `_positive_int` directly as `type=` must switch
to calling it. There is exactly one such site today, `--cap`, shown above.)

`main()`:

```python
hits, suppressed, failed = scan(args.pattern, args.kind, repos, cap=args.cap, deadline=args.deadline)
```

`render_report` gains one new line, placed above the existing `Failed:` block, built from a
new helper:

```python
def _render_partial_section(failed):
    """Lines for repos that failed specifically because the sweep-wide
    deadline expired — a subset of `failed`, rendered before the generic
    `Failed:` block. Empty list when no `failed` reason is `DEADLINE_REASON`."""
    partial_count = sum(1 for reason in failed.values() if reason == DEADLINE_REASON)
    if not partial_count:
        return []
    return [f"Partial: {partial_count} repos not scanned (sweep deadline expired)", ""]
```

`render_report` calls `lines.extend(_render_partial_section(failed))` immediately before
`lines.extend(_render_failed_section(failed))`. `_render_failed_section` is untouched — a
`DEADLINE_REASON` entry still renders in the `Failed:` block too (it IS a failure; `Partial:`
is an additional summary line, not a replacement), matching the PRD's acceptance test, which
only asserts the `Partial:` line's position relative to `Failed:`, not the absence of the
repo from `Failed:`.

`_parse_args`: add `parser.add_argument("--deadline", type=_positive_int("--deadline"),
default=300)` beside `--cap`.

`skills/sweep-fix/SKILL.md:38` usage line becomes:

```
  [--registry PATH] [--cwd PATH] [--cap N] [--deadline N] [--out PATH]
```

## Data flow

1. `main()` parses `--deadline` (default 300) into `args.deadline`, an int.
2. `main()` passes it straight through to `scan(..., deadline=args.deadline)` — no new
   plumbing beyond the one new parameter.
3. Inside `scan()`, the deadline governs how long the result-collection loop waits on each
   future (see Interfaces). It never affects submission (all repos are always submitted
   regardless of deadline) or affects `cap`/`suppressed` (orthogonal: `cap` limits per-repo
   hit volume, `deadline` limits total sweep wall-clock).
4. A repo that misses the deadline lands in `failed` with `DEADLINE_REASON`, flowing through
   the same `failed` dict `render_report` already consumes for its `Failed:` block; the new
   `Partial:` line is purely a derived summary over that same dict, computed at render time,
   not a new data channel.
5. `verify_control` in `main()` (only called when `hits` is empty) is unaffected: it runs
   its own independent `scan()` call with no `deadline` argument (keeps the default `None`),
   since the control check is a small, fast, single-repo verification that should never be
   deadline-starved by a large sweep that happened to find nothing.

## Reuse inventory

- `ThreadPoolExecutor` — stdlib (`concurrent.futures`), no new dependency. Searched for an
  existing thread-pool helper elsewhere in the repo before reaching for the stdlib directly:
  `rg -n "ThreadPoolExecutor|concurrent.futures" skills/` found no existing wrapper to reuse
  (the PRD's own reference, `collect.py`'s eight-thread pattern, lives in a different repo
  — `~/git/src/github.com/buvis/brief-portfolio` per the PRD's commit reference af1b704 —
  and brief-portfolio itself was removed per the capsule's Key Invariants note, so there is
  nothing to import from it even cross-repo). Using `ThreadPoolExecutor` directly is the
  right call: it is the stdlib's own answer and the PRD's Must-have list already assumes it
  by name.
- `time.monotonic()` — stdlib, already the pattern the PRD names for test patchability
  (`sweep.time.monotonic`); no existing monotonic-clock helper in this repo's skills (grep
  for `monotonic` and `perf_counter` across `skills/` returned no hits to reuse).
- `_repo_cwd_and_targets`, `_scan_repo`, the `failed`/`suppressed`/`hits` triple, and
  `_render_failed_section`/`_render_suppressed_section` — all existing `sweep.py` functions
  reused unchanged (see Interfaces); no new parallel code path duplicates their logic.
- `_positive_int` — existing validator reused and generalized (factory), not reimplemented;
  the generalization is the minimum needed to give `--deadline` its own flag name in error
  messages, per the Must-have bullet.

nothing else found, greps tried: `rg -n "ThreadPoolExecutor|concurrent\.futures" skills/`,
`rg -n "monotonic|perf_counter" skills/`, `rg -n "deadline" skills/sweep-fix/`.

## Alternatives considered

1. **`asyncio` + `asyncio.wait_for`** instead of `ThreadPoolExecutor` + manual deadline
   polling. Rejected: `_scan_repo` wraps blocking `subprocess.run` calls; adopting asyncio
   would mean either running the subprocess calls in an executor anyway (same thread pool,
   extra event-loop layer for no benefit) or rewriting them as `asyncio.create_subprocess_exec`
   (a much larger diff touching `_scan_rg`/`_scan_astgrep`, not just `scan()`, and not
   justified by the PRD's Must-have list, which only asks for `ThreadPoolExecutor`).
2. **Smallest-diff version: `ThreadPoolExecutor` with NO deadline support**, just the
   concurrency half of the PRD. This is the minimal diff that satisfies the first Must-have
   bullet alone. The chosen design is larger because the PRD's remaining four Must-have
   bullets (the `--deadline` flag, `DEADLINE_REASON`, the `Partial:` line, the SKILL.md usage
   update) are not optional scope — they are the PRD's stated requirements, and the original
   Problem section is explicit that an unbounded-wait pool only fixes the "810s worst case"
   symptom, not the "no ceiling, no progress signal" root complaint. Shipping concurrency
   alone would leave the PRD's acceptance criteria unmet.
3. **`executor.submit(...).result(timeout=remaining)` per-future with a shrinking timeout**
   (compute `remaining = deadline - elapsed` before each `.result()` call and pass it as
   `result`'s own `timeout` kwarg, letting `concurrent.futures.TimeoutError` signal the
   deadline instead of a manual `time.monotonic()` comparison before each call). Rejected in
   favor of the explicit comparison: catching `TimeoutError` to mean "deadline expired" reads
   fine until `remaining` goes negative (deadline already passed when the loop reaches a
   later repo) — `.result(timeout=negative)` raises immediately as if size were 0, which
   happens to work but relies on an undocumented corner of the stdlib's negative-timeout
   handling rather than an explicit, readable `if elapsed >= deadline` check the PRD's test
   (`test_scan_records_an_unfinished_repo_when_the_deadline_expires`, patching
   `sweep.time.monotonic`) can drive directly.

## Risks & edge cases

- **`max_workers=8` is hardcoded**, per the PRD's own Must-have wording (no `--workers`
  flag requested). Likely next change: a `--workers N` flag mirroring `--cap`/`--deadline`,
  if a future sweep needs tuning for a much larger registry. This design does not block that
  — `max_workers=8` is a single literal in one `ThreadPoolExecutor(...)` call.
- **A repo whose future never completes (deadlocked subprocess) still leaks a running
  thread past `scan()`'s return**, now bounded to the interpreter-exit join rather than
  `scan()`'s own return: `executor.shutdown(wait=False, cancel_futures=True)` (Interfaces)
  means `scan()` itself no longer blocks on it, but `concurrent.futures` registers an
  atexit hook that joins every pool thread before the **process** exits, so a truly hung
  `_scan_repo` call (not just slow — actually stuck, e.g. a subprocess ignoring its own
  `timeout` due to an OS-level hang) still blocks process exit, just not the `scan()` call
  that reports the deadline. This is a pre-existing risk class (`_run_rg`'s own `timeout=`
  already bounds the subprocess, and `subprocess.run(..., timeout=...)` reliably kills the
  child on timeout on every platform this ships to), not a new one this design introduces,
  and `DEFAULT_SCAN_TIMEOUT=30` already bounds each individual call far below any plausible
  `--deadline` default of 300s. Documented here, not fixed, because the PRD's Must-have list
  does not ask for thread cancellation and the existing per-call `timeout` is the real
  backstop.
- **Likely next change #2**: a `--workers` flag (above).
- **Likely next change #3**: surfacing partial-sweep repos as a distinct exit code (today
  `main()` always returns 0 when the sweep itself ran, regardless of `failed`/`Partial:`
  content) so a CI caller can distinguish "clean sweep" from "sweep hit its deadline." Out
  of scope here — the PRD's acceptance criteria only test the report's content and
  `scan()`'s return shape, not `main()`'s exit code.
- **Byte-identical report ordering across two separate `sweep.main` runs** (the PRD's third
  Success Criterion) depends on `hits` staying ordered by `repos` position regardless of
  which repo's future resolves first — this is exactly what collecting futures in a
  pre-built, `repos`-ordered list (rather than `as_completed`) guarantees; nothing about
  concurrency introduces nondeterminism into the rendered report as long as that ordering
  discipline holds.

## Test strategy outline

- `test_scan_runs_repo_searches_concurrently` (fail-first, binds to overlap not timing): stub
  `sweep._scan_repo` to block on a shared `threading.Barrier(3, timeout=5)` before returning;
  a serial implementation deadlocks the barrier (`BrokenBarrierError` after its own timeout),
  a concurrent one releases it. Three repos, no `deadline` passed (keeps the `None` path
  exercised).
- `test_scan_orders_hits_by_registry_position_not_completion_order`: stub `_scan_repo` so the
  LAST repo's call returns first (e.g. via a short `time.sleep` differential or an
  `threading.Event` the first-called stub waits on); assert `[h["repo"] for h in hits] ==
  [str(repo_a), str(repo_b), str(repo_c)]` for a three-repo registry passed in that order.
- `test_scan_records_an_unfinished_repo_when_the_deadline_expires`: monkeypatch
  `sweep.time.monotonic` with a stub returning an increasing sequence whose second read is
  past `start + deadline`; make the targeted repo's future stay pending by patching
  `ThreadPoolExecutor.submit` itself (NOT `_scan_repo` — `submit()` always wraps whatever
  its target callable returns in a fresh outer `Future` of its own, so patching
  `_scan_repo`'s return value cannot produce a still-pending `Future`; only replacing
  `submit` directly can hand `scan()` a `concurrent.futures.Future()` the test holds and
  controls) to return a bare, never-resolved `Future()` for the targeted repo while
  delegating to the real, unpatched `submit` for every other repo in the same `scan()` call
  (so the already-finished-repo assertion below has a real result to check) — this is the
  one implementable shape: a stub that
  submits to the real pool and then blocks forever on a `threading.Event` the test never
  sets would make `scan()`'s new `executor.shutdown(wait=False, cancel_futures=True)` return
  promptly (that path is what this test proves), but the still-blocked worker thread would
  then hang the test **process** at interpreter exit, since `concurrent.futures` registers
  an atexit join on every pool thread regardless of `shutdown(wait=False)` — a real thread
  must never be left blocked forever in a test. Assert `failed[str(repo_b)] ==
  sweep.DEADLINE_REASON` and that `hits` still holds the already-finished repo's rows
  (proving partial results survive a deadline cutoff).
- `test_main_rejects_a_deadline_of_zero` (modelled on `test_main_rejects_cap_of_zero` at
  `skills/sweep-fix/scripts/test_sweep_main.py:425`): `sweep.main(argv + ["--deadline",
  "0"])` raises `SystemExit` with nonzero code, writes no report, and stderr/stdout contains
  `--deadline must be a positive integer`.
- `test_render_report_prints_a_partial_line_for_deadline_failures`: call `render_report`
  directly with a `failed` dict holding two `DEADLINE_REASON` entries and one other reason
  string; assert the rendered text contains `Partial: 2 repos not scanned (sweep deadline
  expired)` on a line strictly before the `Failed:` line (`report.index("Partial:") <
  report.index("Failed:")`).
- Regression guard: `test_main_rejects_cap_of_zero` and `test_main_rejects_negative_cap`
  (existing, `skills/sweep-fix/scripts/test_sweep_main.py:425-452`) must keep passing
  unmodified — they only assert the substring `"cap"` in combined stdout+stderr, which the
  parameterized `_positive_int("--cap")` message (`"--cap must be a positive integer"`)
  still satisfies.
- Full-suite gate: `uv run pytest skills/sweep-fix/scripts -q` — 0 failed, 0 errors.

## Review log

- non-blocker: `resolve_rg()`'s `@functools.lru_cache()` is called concurrently from up to 8 worker threads once sweep runs `kind="rg"` under the pool (unlike `resolve_ast_grep`, pre-resolved once before the loop today). `lru_cache` only serializes the cache-dict write, not the wrapped call, so several first-call workers can redundantly run `shutil.which("rg")` before the cache settles. Harmless (idempotent, no correctness impact) — not fixed, recorded per the calibration rule.
- non-blocker: a `DEADLINE_REASON` repo is double-counted in the rendered report: once in the new `Partial:` summary line, again as an indistinguishable row in the existing `Failed:` block. This is the design's deliberate choice (the PRD's acceptance test only pins the `Partial:` line's position relative to `Failed:`, not exclusivity) — recorded so it isn't mistaken for an oversight later.
- dispatch 1 (claude): cardinal-sin 0, blocker 0, non-blocker 2, question 0
- dispatch 2: codex unavailable (`sandbox_apply: Operation not permitted` reading both
  required files; returned "unassessed", unparseable as findings) — Claude fallback used.
- question (resolved): the CLI never exposes `--deadline`'s `None`/unbounded mode; added a
  sentence to Interfaces confirming this is intentional, not an oversight.
- dispatch 2 (claude-fallback): cardinal-sin 0, blocker 2 (both fixed — `scan()`'s executor
  no longer uses a `with` block that forces `shutdown(wait=True)` regardless of the
  deadline; the deadline test's "blocks on an Event never set" stub option was removed from
  the Test strategy section), non-blocker 0, question 1 (resolved above)
- dispatch 3: codex unavailable again (same `sandbox_apply: Operation not permitted`
  file-read failure; returned only unverifiable "question" hedges) — Claude fallback used.
  Incidentally, codex's hedged output correctly flagged, without reading either file, that
  patching `_scan_repo`'s return value cannot produce a still-pending `Future` (`submit()`
  always wraps the callable's return in its own fresh outer `Future`); fixed the Test
  strategy wording to patch `ThreadPoolExecutor.submit` directly, ahead of dispatch 3's
  formal verification pass.
- non-blocker: the `scan()` docstring's "its future is not cancelled" parenthetical is a
  blanket claim that is only true for already-running futures; a not-yet-started future for
  a repo still queued when the deadline trips IS subsequently cancelled by the `finally`
  block's `cancel_futures=True`. Qualified the docstring to say so.
- question (resolved): the Test strategy bullet for the deadline test didn't say what the
  patched `ThreadPoolExecutor.submit` stub does for repos other than the targeted one,
  risking an implementor patching every call and leaving `hits` empty. Added the clause:
  the stub delegates to the real `submit` for every repo except the targeted one.
- dispatch 3 (claude-fallback): both original blockers verified CLOSED, no new cardinal
  sins or blockers; cardinal-sin 0, blocker 0, non-blocker 1 (fixed), question 1 (resolved)
result: ok
