# Design: 00104-sweep-overruns-process-deadline-v1

## Architecture fit

Almost all changes land in `skills/sweep-fix/scripts/sweep.py`, the single
module backing the `sweep-fix` skill's deterministic step 2. No new files,
no new skill surface: `scan()`, `verify_control()` and `main()` keep their
names and call sequence, gaining parameters rather than new public
functions. `render_report()` is untouched (see below — the expired-budget
case reuses the existing non-zero refusal contract, so it never reaches
`render_report()`). The one change outside `sweep.py` is prose:
`skills/sweep-fix/SKILL.md` documents the shared-deadline and
unverified-refusal contract, per the PRD's own "operator instructions"
module.

## Module placement

Edits only, in `skills/sweep-fix/scripts/sweep.py`:

- New: a small process registry (`_ProcessRegistry` class) and a
  cross-platform tree-kill helper (`_kill_tree`), placed beside
  `DEFAULT_SCAN_TIMEOUT`/`DEADLINE_REASON`.
- New imports: `threading`, `signal`.
- Changed: `_run_rg`, `_scan_astgrep` (Popen instead of `subprocess.run`,
  registry-aware), `_scan_repo` (threads the registry through), `scan`
  (owns the registry, kills stragglers on deadline, waits for a clean
  shutdown), `verify_control` (accepts a `deadline` budget, distinguishes
  "ran out of time" from "could not be scanned"), `render_report` (new
  `Unverified:` section), `main` (shares one wall-clock budget across scan
  + verify, decides unverified vs. verified).

Prose, not code: `skills/sweep-fix/SKILL.md`'s `--deadline N` paragraph
gains a sentence that the deadline now also bounds control verification,
and that an expired zero-hit sweep exits 1 with a `sweep unverified: ...`
stderr line and writes no report — the same existing contract the
broken-pattern case already uses, now reached by a second cause. No
`SKILL.md` structural change; `validate_skill.py skills/sweep-fix` (already
an Exit criterion) covers structure, not this prose.

New test files, alongside the existing `test_sweep_*.py` suite:

- `skills/sweep-fix/scripts/test_sweep_scan.py` — extend with process-tree
  termination coverage (sleeping shim, descendant survival).
- `skills/sweep-fix/scripts/test_sweep_verify_control.py` — extend with
  budget-sharing and skipped-verification coverage.
- `skills/sweep-fix/scripts/test_sweep_main.py` — extend with the real-CLI
  wall-clock regression named in the PRD's Test Strategy.

## Interfaces & contracts

```python
# -- process lifetime -----------------------------------------------------

class _ProcessRegistry:
    """Tracks in-flight Popen handles by a caller-chosen `key` (the repo's
    cwd, stringified) so an expired repo's process tree can be killed from
    outside the worker thread that owns it. Thread-safe (one `threading.Lock`
    guards the dict)."""

    def __init__(self) -> None: ...
    def register(self, key: str, proc: subprocess.Popen) -> None: ...
    def unregister(self, key: str, proc: subprocess.Popen) -> None: ...
    def kill(self, key: str) -> None:
        """Kill and discard every process registered under `key`. Safe to
        call with no processes registered (no-op). Exceptions from an
        already-dead process are swallowed."""
    def kill_all(self) -> None:
        """`kill()` every remaining key. Used once, from `scan()`'s cleanup,
        when the sweep deadline expired."""


def _kill_tree(proc: subprocess.Popen) -> None:
    """Terminate `proc` and its descendants. POSIX: `os.killpg` on the
    process group `_run_rg`/`_scan_astgrep` placed `proc` in via
    `start_new_session=True`. Windows: `taskkill /F /T /PID <pid>`
    (`creationflags=CREATE_NEW_PROCESS_GROUP` at launch), falling back to
    `proc.kill()` either way. Never raises."""


def _popen_new_group_kwargs() -> dict:
    """`{"start_new_session": True}` on POSIX, `{"creationflags":
    subprocess.CREATE_NEW_PROCESS_GROUP}` on Windows (`os.name == "nt"`).
    Shared by `_run_rg` and `_scan_astgrep` so both search tools are
    launched into a killable group the same way."""


# -- search tools: Popen instead of subprocess.run ------------------------

def _run_rg(
    args: list[str],
    cwd,
    timeout: float = DEFAULT_SCAN_TIMEOUT,
    registry: "_ProcessRegistry | None" = None,
    key: str | None = None,
) -> subprocess.CompletedProcess:
    """Same contract as today (returns a CompletedProcess, raises
    RuntimeError on an rg exit code outside {0, 1}, raises
    subprocess.TimeoutExpired on timeout) plus: launches `rg` via
    `subprocess.Popen` in its own process group, registers it under `key`
    when `registry` is given (immediately after the `Popen` call, before
    `communicate()`), and unregisters it in a `finally` block that runs
    whether `communicate()` returns normally, times out, or raises --
    so a process never stays in the registry past the call that launched
    it, and `registry.kill_all()` only ever reaches processes genuinely
    still in flight. On a timeout, kills the whole tree via `_kill_tree`
    before re-raising `TimeoutExpired` -- so a caller catching that
    exception (as `_scan_repo` already does) is guaranteed the child is
    gone, not still running. `registry`/`key` default to `None` so
    `verify_control`'s direct `_run_rg` call (no registry needed, its own
    deadline is enforced by `scan()`'s inner call plus this function's own
    `timeout`) keeps working unchanged.
    """


def _scan_astgrep(
    pattern: str,
    cwd,
    targets: list[str],
    timeout: float = DEFAULT_SCAN_TIMEOUT,
    registry: "_ProcessRegistry | None" = None,
    key: str | None = None,
) -> list[dict]:
    """Same return contract as today. Same Popen/registry/kill-on-timeout
    treatment as `_run_rg`."""


def _scan_repo(
    repo,
    pattern: str,
    kind: str,
    ast_grep_error: str | None,
    timeout: float,
    registry: "_ProcessRegistry | None" = None,
) -> tuple[str, list[dict], str | None]:
    """Same return contract as today (`(cwd_key, hits, error)`). New: passes
    `registry` and `key=str(cwd)` (the same string `_collect_scan_results`
    already builds as `cwd_key`) down into `_scan_rg`/`_scan_astgrep`."""


def _collect_scan_results(
    repos,
    futures,
    deadline,
    start,
    registry: "_ProcessRegistry | None" = None,
) -> tuple[list, bool]:
    """Same return contract as today. New: when a future is not done by the
    deadline, calls `registry.kill(cwd_key)` (if `registry` is given)
    immediately after recording the `DEADLINE_REASON` result, so the
    worker's `communicate()` unblocks right away instead of running out
    its own per-call `timeout`."""


def scan(
    pattern: str,
    kind: str,
    repos,
    cap: int = 20,
    timeout: float = DEFAULT_SCAN_TIMEOUT,
    deadline: float | None = None,
) -> tuple[list[dict], dict, dict]:
    """Same public signature and return contract as today. New: owns one
    `_ProcessRegistry` for the call, threads it through every
    `_scan_repo` dispatch and into `_collect_scan_results`. In the
    `finally` block: if the deadline was hit, `registry.kill_all()` first
    (covers any repo whose future resolved to a non-deadline failure but
    whose process somehow outlived it, and any queued-but-never-started
    future `cancel_futures` already drops), then always
    `executor.shutdown(wait=True, cancel_futures=deadline_hit)` -- `wait`
    changes from today's `not deadline_hit` to unconditional `True`,
    because killing every outstanding process first means no worker thread
    can still be blocked in a live subprocess by the time shutdown runs,
    so waiting is now always prompt instead of sometimes indefinite."""


def verify_control(
    pattern: str,
    kind: str,
    control_repo,
    control_term: str,
    deadline: float | None = None,
) -> None:
    """Same success contract as today (returns `None` on a confirmed-working
    or inconclusive control; `SystemExit(1)` with the existing broken-pattern
    stderr message when the control term is present but the pattern found
    nothing). Two behavior changes:

    1. `verify_control` takes its own `verify_start = time.monotonic()`
       reading the instant it is entered. The internal
       `scan(pattern, kind, [control_repo])` call becomes
       `scan(pattern, kind, [control_repo], deadline=deadline)`. After that
       call returns, the control-term `_run_rg` call's own timeout is
       `remaining_after_scan = deadline - (time.monotonic() - verify_start)`,
       clamped the same way the rest of this design clamps a shared budget
       (`<= 0` means skip the call and raise `TimeoutError` immediately,
       per point 2 below, rather than calling `_run_rg` with a zero/negative
       timeout), capped at `min(remaining_after_scan, DEFAULT_SCAN_TIMEOUT)`
       when positive. This is deliberately `deadline`'s *remainder* after the
       inner `scan()` call, not `deadline` itself -- the two sequential
       subprocess calls inside `verify_control` share ONE clock
       (`verify_start`), so a slow inner `scan()` call leaves correspondingly
       less of `deadline` for the control-term check, and the two calls
       together can never exceed `deadline` the way two independent
       up-to-`deadline` windows could.
    2. A failure whose reason is exactly `DEADLINE_REASON` -- either the
       inner `scan()` call recording it in `failed`, or the control-term
       `_run_rg` call raising `subprocess.TimeoutExpired` -- raises
       `TimeoutError` (builtin, not `RuntimeError`) with a
       `"sweep unverified: deadline expired before control verification "
       "could confirm the result"`-shaped message, instead of today's
       `RuntimeError`. Every other scan/search failure still raises
       `RuntimeError` exactly as today, message unchanged. `TimeoutError`
       vs. `RuntimeError` is the signal `main()` uses to tell "ran out of
       shared budget" apart from "control repo is broken" without parsing
       message strings; both still carry an already-correct
       `"sweep unverified: ..."`-prefixed message, so `main()` can
       `print(exc, file=sys.stderr)` for either without building its own
       text.
    """


def main(argv=None) -> int:
    """Same contract as today: 0 on success (a verified result, hit or
    clean), 1 with one stderr line and **no report written** on a setup
    failure or an unverified refusal. `render_report`/its signature are
    untouched -- the expired-budget case never reaches `render_report` at
    all, exactly like today's broken-pattern case. New control flow around
    the existing `scan()` / `verify_control()` pair:

        start = time.monotonic()
        hits, suppressed, failed = scan(..., deadline=args.deadline)
        remaining = args.deadline - (time.monotonic() - start)
        if not hits:
            if remaining <= 0:
                print(
                    "sweep unverified: deadline expired before control "
                    "verification could run",
                    file=sys.stderr,
                )
                return 1
            try:
                verify_control(..., deadline=remaining)
            except TimeoutError as exc:
                print(exc, file=sys.stderr)
                return 1
            except RuntimeError as exc:
                print(exc, file=sys.stderr)
                return 1

    This is a straight widening of today's existing
    `except RuntimeError as exc: print(exc, file=sys.stderr); return 1`
    block to also catch `TimeoutError` -- the budget-exhausted case is
    handled by the *same* non-zero, no-report refusal contract the PRD
    names, not a new one. `verify_control` raising `TimeoutError` (see
    below) is responsible for putting a `"sweep unverified: ..."`-prefixed
    message in the exception's own text, matching today's `RuntimeError`
    messages, so this `print(exc, ...)` needs no reason string of its own
    for that branch -- only the `remaining <= 0` branch above (which never
    calls `verify_control` at all) constructs its own message.
    `SystemExit(1)` from `verify_control` (the broken-pattern case)
    propagates unchanged -- `main()` adds no `except SystemExit` clause,
    exactly as today."""
```

## Data flow

1. `main()` starts one wall-clock reading (`start = time.monotonic()`)
   **immediately after argument parsing, before `resolve_rg()`/
   `resolve_ast_grep()` and `enumerate_repos()` run** -- i.e. at the very
   top of the existing `try:` block, before its first line. This counts
   setup time (including `enumerate_repos()`'s own bounded `git ls-files`
   call for the buvis bare-repo entry) against `--deadline`, consistent
   with `--deadline`'s existing documented meaning as "a wall-clock budget
   for the whole sweep" (SKILL.md), not just the scan portion of it. Today
   this reading lives only inside `scan()`, started after that same setup
   already ran.
2. `scan()` runs exactly as before from the caller's point of view, except
   every repo's `rg`/`ast-grep` subprocess is now launched into its own
   process group and tracked in a registry local to that `scan()` call.
   `_collect_scan_results` kills a repo's tree the instant its future
   misses the deadline, instead of only marking it failed and walking
   away; `scan()`'s `finally` sweeps any stragglers and then waits
   (bounded, because nothing can still be running a live subprocess) for
   every worker thread to actually finish, so the executor — and, once
   `main()` returns, the interpreter — never idles on a reaped-but-still-
   blocked thread.
3. `main()` computes `remaining` from the one `start` reading after `scan()`
   returns. If `hits` is non-empty, verification never runs (unchanged).
   If `hits` is empty and `remaining <= 0`, verification is skipped
   outright — no new subprocess, no fresh unbounded window — and `main()`
   takes the existing non-zero refusal path directly (stderr line, exit 1,
   no report written). If `remaining > 0`, `verify_control` runs bounded
   by `remaining`, itself calling `scan()` again (one more repo, the
   control repo) under the same kill-on-expiry machinery, so a slow
   control scan cannot overrun the shared budget either.
4. `verify_control`'s `TimeoutError` and `RuntimeError` are both caught by
   the same widened `except` in `main()` and take the same action it
   already takes for `RuntimeError` today: print the exception's message
   to stderr, exit 1, write no report. The two exception types exist only
   so `verify_control` itself can distinguish "ran out of shared budget"
   from "control repo is broken" when constructing its message; `main()`
   does not need to tell them apart to act. `render_report` is never
   reached in this path, exactly as it is never reached by today's
   broken-pattern `SystemExit(1)`.

## Reuse inventory

- `DEADLINE_REASON` (existing module constant) is reused as the exact
  sentinel distinguishing "ran out of time" from "could not be scanned" at
  both the per-repo (`_collect_scan_results`/`failed`) and the whole-sweep
  (`verify_control`/`TimeoutError`) level — no second sentinel is
  introduced.
- `ThreadPoolExecutor`/`wait` (already imported from
  `concurrent.futures`) stay the concurrency primitive; nothing about the
  worker-pool shape changes, only what happens to a worker's subprocess
  when its repo's deadline passes.
- `os.name == "nt"` is the existing Windows-detection idiom already used
  by `resolve_ast_grep`'s caller context and by this repo's test suite
  (`test_sweep_scan.py`'s `if os.name == "nt":` branch); the new
  `_popen_new_group_kwargs`/`_kill_tree` helpers follow the same idiom
  rather than introducing `platform.system()` or similar.
- Greps tried before concluding no existing cross-platform process-tree
  kill helper exists in this repo to reuse: `rg -i "process.?group|killpg|CREATE_NEW_PROCESS_GROUP|taskkill" skills/` and
  `rg "def _kill|terminate.*tree|kill.*tree" skills/` — both return only
  this PRD's own target file (none yet) and unrelated hits in other
  skills' own subprocess helpers (none providing tree-kill). No helper to
  reuse; the registry/kill helpers are new, minimal, and scoped to this
  module only.

## Alternatives considered

1. **(Smallest diff) Lower every per-call `timeout` to the remaining
   deadline instead of adding process-group tracking.** Rejected as
   insufficient: `subprocess.run(timeout=...)` already kills the *direct*
   child on its own timeout, but not a grandchild the search tool itself
   spawns (the PRD's explicit "subprocess trees created by a search
   command" requirement), and it does nothing for the deadline-expiry path
   in `_collect_scan_results`, which today only stops *waiting* on a
   future — it never signals the still-running thread/subprocess at all.
   This alternative would still leave `scan()`'s `executor.shutdown(wait=
   not deadline_hit, ...)` escaping without reaping, which is the PRD's
   core complaint ("running workers and search processes remain alive and
   delay interpreter exit").
2. **Daemonize the worker threads instead of killing subprocesses.**
   `ThreadPoolExecutor` offers no public daemon-thread knob, and even if
   it did, a daemon thread abandoning a live `rg`/`ast-grep` process would
   leak that process (and any of its own children) as an orphan — it
   would make the *Python* process exit promptly while leaving exactly the
   runaway subprocess tree the PRD is about. Rejected: it hides the
   symptom (interpreter delay) without fixing the cause (processes outlive
   their deadline).
3. **(Chosen) Process-group-scoped `Popen` + a small kill registry, shared
   deadline budget threaded into `verify_control`.** Costs one new class
   (`_ProcessRegistry`, ~20 lines), one kill helper, and converting two
   `subprocess.run` call sites to `Popen`/`communicate`. In exchange it
   satisfies both Must-haves directly: searches are actually terminated at
   expiry (not just abandoned), and verification can never grant a fresh
   unbounded window. The extra size buys a correctness guarantee
   (`_kill_tree` reaches descendants, not just the immediate child) that
   alternative 1 cannot provide with any timeout value.

## Risks & edge cases

- **Cancellation racing with a result landing at the same instant.**
  `_collect_scan_results` already decides "done or not" with one
  `wait([future], timeout=...)` call per repo; the kill-on-expiry call
  added here fires only in the branch where that call just reported "not
  done," so a future that completes a microsecond later is still read via
  `future.result()` on the *next* repo's loop iteration never — this repo
  is already recorded as `DEADLINE_REASON` and not revisited, matching
  today's documented behavior (a repo that finishes right after its
  deadline check still loses its hits). No new race is introduced; the
  existing one (acknowledged in `_collect_scan_results`'s docstring) is
  unchanged.
- **Windows process-tree kill is a `taskkill` subprocess call, which can
  itself fail or hang.** Bounded with its own short timeout inside
  `_kill_tree`, wrapped in a bare `except Exception: pass` followed by an
  unconditional `proc.kill()` fallback, so a `taskkill` failure degrades to
  today's single-process kill rather than raising out of cleanup code.
- **A grandchild that re-parents out of its process group (e.g. calls its
  own `setsid()`) survives `os.killpg`.** Not a realistic concern for
  `rg`/`ast-grep` themselves, only for a hypothetical future search tool
  invoked indirectly; accepted as a known limitation of the
  process-group approach rather than a reason to redesign around it now.
- **A control repo that is itself slow enough to need the full `remaining`
  budget leaves no slack for the control-term fallback `_run_rg` call.**
  Accepted: `verify_control`'s `timeout=min(deadline, DEFAULT_SCAN_TIMEOUT)`
  bound already caps that second call well under most `remaining` values;
  the edge case where `remaining` itself is under a second is exactly the
  case `TimeoutError` is designed to report as unverified, not silently
  pass.
- **Likely next changes this design should not box in:** (1) a per-repo
  (rather than whole-sweep) deadline, which the registry/kill plumbing
  supports unchanged since kills are already addressed by repo key; (2)
  surfacing *which* repos were still running at expiry (today's `Failed:`
  section with `DEADLINE_REASON` already carries this, unchanged by this
  PRD); (3) reusing `_kill_tree`/`_ProcessRegistry` for a future deadline
  on `verify_control`'s control-term check specifically, which the
  `timeout=` parameter already on `_run_rg` makes a small follow-up, not a
  redesign.

## Test strategy outline

- **`test_sweep_scan.py`**: a new section mirroring the existing deadline
  tests, using a sleeping *subprocess* shim (not a monkeypatched Python
  function, so the test exercises the real `Popen`/kill path) that spawns
  a grandchild process the shim itself waits on — assert that after
  `scan(..., deadline=...)` returns, neither the shim nor its grandchild
  is still alive (poll `/proc` on POSIX or a sentinel file the shim
  deletes before exiting, matching the existing `write_executable_stub`
  fixture idiom already used by `test_scan_reports_a_hung_search_as_a_
  failed_repo_without_blocking`). Keep the existing monkeypatch-based
  deadline tests unchanged (they test the result-collection contract, not
  process lifetime) and add the new ones alongside.
- **`test_sweep_verify_control.py`**: extend with (a) a zero-hit sweep
  where `deadline` leaves no `remaining` budget — assert `verify_control`
  raises `TimeoutError`, not `RuntimeError`, and that no `_run_rg` call for
  the control term happens (monkeypatch it to raise if called); (b) a
  zero-hit sweep with ample remaining budget — assert today's behavior
  (confirmed clean, or `SystemExit(1)` on a genuinely broken pattern) is
  unchanged; (c) the inner `scan()` call itself hitting its passed-through
  `deadline` — assert `TimeoutError`, reusing `DEADLINE_REASON` as the
  fixture's injected failure reason.
- **`test_sweep_main.py`**: the PRD's own named regression — the real CLI
  subprocess, a search shim sleeping 10s, `--deadline 3`, asserting the
  **outer `main()` subprocess's own measured wall time** (not just
  `scan()`'s return) is under 5s (3s deadline + 2s cleanup tolerance). Add
  two zero-hit cases: (a) `--deadline` large enough to leave budget —
  unchanged exit-0/report-written behavior, matching today's existing
  successful-control-check test; (b) `--deadline` small enough that no
  budget remains after the scan — assert exit code 1, a `sweep unverified:
  ...` line on stderr, and **no report file written** (list the output
  dir before/after, or capture `--out`'s target and assert it does not
  exist), reusing the existing setup-error tests' assertion shape for "no
  report on failure."
- No `render_report`/`test_sweep_render_report.py` changes: its contract
  is unchanged.
- `skills/sweep-fix/SKILL.md`'s prose change has no dedicated test beyond
  the Exit-criteria `validate_skill.py` structural check; its content is
  reviewed, not asserted.
- Run order for review: the PRD's named acceptance command,
  `uv run pytest skills/sweep-fix/scripts/test_sweep_scan.py skills/sweep-fix/scripts/test_sweep_verify_control.py skills/sweep-fix/scripts/test_sweep_main.py`.

## Review log

- non-blocker: control-term `_run_rg` timeout is capped at `DEFAULT_SCAN_TIMEOUT`
  (30s) even when `remaining` is much larger, so a merely-slow (not actually
  budget-exhausted) control repo can report "deadline expired" when the sweep
  budget was mostly untouched. Accepted as-is: the user-visible outcome
  ("unverified") is correct either way, and distinguishing the message text
  for this case is not worth the complexity.
- question: whether `_run_rg`/`_scan_astgrep` unregister themselves from
  `_ProcessRegistry` on the normal (non-timeout) completion path. Resolved in
  the Interfaces & contracts section above: registration is scoped per-call
  (register before launch, unregister in a `finally` after `communicate()`
  returns, success or failure), so `kill_all()` only ever iterates processes
  still in flight when the deadline fires; an already-finished call is never
  in the registry to be re-killed.
dispatch 1 (claude): cardinal-sin 0, blocker 2, non-blocker 1, question 1
dispatch 2 (claude-fallback): cardinal-sin 0, blocker 1, non-blocker 1, question 1
dispatch 3 (codex): cardinal-sin 0, blocker 0, non-blocker 0, question 0
