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
