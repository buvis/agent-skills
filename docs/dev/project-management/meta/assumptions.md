# Assumptions ledger — PRD 00031-sweep-parallel-with-deadline-v1

## 1: Parallelize scan() with ThreadPoolExecutor(max_workers=8)

- The stubs take `(repo, *args, **kwargs)` instead of the exact 5-argument signature, so the later `deadline` task does not break them.
- The stub returns the documented `(cwd_key, hits, error)` tuple with `cwd_key = str(repo)`, and hit dicts shaped like `_build_hit` output (`repo`, `file`, `line`, `snippet`, `lang`).
- The ordering test uses a sleep difference to keep completion order deterministic. A correct implementation passes regardless of timing; only the chance of catching a completion-order bug depends on it.
- With `deadline=None`, a slow repo must land in hits, not in `failed` (PRD Must-have: an unfinished repo goes to `failed` only under a deadline).
- A 1.0s slow repo against `timeout=0.2` is enough to catch a join-timeout exploit; it cannot catch every possible join timeout without an unbounded sleep.
- Patching `subprocess.run` for the concurrency test is allowed even though the task text says to patch `sweep._scan_repo`, because the real exploit required running the barrier through the real `_scan_repo` path.
- The PRD-listed test `test_scan_records_an_unfinished_repo_when_the_deadline_expires` belongs to the separate deadline task (task 4) and is out of scope for task 1.
- (Ivan) The deadline, `--deadline` CLI flag, `Partial:` line and SKILL.md usage-line parts of the design belong to a later task with their own tests, so left out of task 1's implementation.
- (Ivan) Letting a `_scan_repo` exception escape `scan()` is acceptable, as before and as the tests allow; not turned into a `failed` entry.

## 4: Add deadline param, DEADLINE_REASON constant, and the deadline-expiry test

- (Tess) `scan()` will keep passing the repo as the first positional argument to `executor.submit(_scan_repo, repo, ...)`, and will keep using `sweep.ThreadPoolExecutor` and reading `time.monotonic` through the module (`import time`), not `from time import monotonic`.
- (Tess) The deadline value of 5s used in the within-deadline test is arbitrary; any value well under the real-clock sleeps used works.
- (Tess, strengthening) "Inside a try/finally: release.set()" wraps the `scan()` call, not the worker — a `finally` inside the worker would only run after its own wait already timed out.
- (Tess, strengthening) A correct implementation starts the deadline clock when `scan()` is entered (or at submit time); the added budget-from-start test carries ~0.3s of margin around that.
- (Ivan) Waiting on a future with `timeout=remaining` (the sweep's time left) counts as "awaiting" under the deadline — needed to pass the hung-repo-returns-promptly test, since a plain unbounded `future.result()` would not.
- (Ivan) An error-entry repo (`{cwd, error}`) still queued when the deadline passes is keyed by `str(repo["cwd"])`, matching the key `_scan_repo` already gives it.

## 5: Wire --deadline through the CLI and render the Partial: line

- (Tess) The new deadline-rejection test sits next to the existing `--cap` rejection tests in test_sweep_main.py; no placement was specified.
- (Ivan) When a just-added test (`test_main_passes_deadline_through_to_scan`, no-flag half) contradicted the PRD/design (`--deadline` default 300, always passed to `scan()`), the PRD and design doc were treated as authoritative and the test's `is None` assertion was flagged as the defect — fixed in a follow-up commit to `== 300`, confirmed against `docs/dev/project-management/prds/wip/00031-sweep-parallel-with-deadline-v1.md` and its design doc.
