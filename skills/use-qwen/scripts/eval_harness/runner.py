"""The bounded command runner of the qwen evaluation harness: trees, reaping, the gate.

Every command a gate or an engine runs goes through this module, so nothing the
harness starts outlives the command that started it: the child is held inside a
boundary of its own, its streams land in one log (or stderr in a second one the
caller names), and the tree is killed and counted on every path. The boundary is
a process group on POSIX and a job object on Windows, whose kernel32 half lives
in its own module.
"""
import os
import signal
import subprocess
import tempfile
import time
from collections.abc import Iterator, Sequence
from contextlib import ExitStack, contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path

# Markers a line carries, never whole lines: a run names other projects' tests,
# other missing modules and other tools, and the marker is what the class reads.
TOOL_MARKERS = ("command not found", "No such file or directory", "ModuleNotFoundError",
                "ImportError", "ERROR collecting", "INTERNALERROR", "error: could not",
                "is not recognized as an internal or external command")
TEST_MARKERS = ("FAILED ", "AssertionError", "assert ", "=== FAILURES ===",
                "test result: FAILED", "--- FAIL:", "not ok ")
GATE_MARKER = ".gate-in-flight"

_FALLBACK_LINES = 40
_POLL_S = 0.02


class OrphanError(RuntimeError):
    """Raised when a command's process tree still has members after cleanup.

    `observed` is the engine_run block the engine dispatch had measured when it
    found the survivors, so the halted attempt still says what ran; a halt a
    gate or the baseline raised observed no block and leaves it None.
    """

    observed = None


class GateConcurrencyError(RuntimeError):
    """Raised when a gate starts while another gate's marker is still in flight."""


class JobAssignmentError(RuntimeError):
    """Raised when the host will not contain a child, which halts the whole run.

    Never an attempt-level discard: the process was created, so its launch is
    "started", and only "not-started" may be blamed on the harness and retried.
    A host that could not contain this child cannot contain the next one either.
    `observed` is the started block the engine dispatch attaches on the way up,
    and None from anywhere else.
    """

    reason = "job_assignment_failed"
    observed = None


class LaunchError(RuntimeError):
    """Raised when the host would not create the child: Popen itself refused, as the cause.

    The one failure from before there was a process, so the one that reads as
    a launch that never started; whatever fails after creation - the wait, the
    reap, the read - is its own error and leaves the runner as itself.
    """


@dataclass(frozen=True)
class CommandResult:
    """One command's outcome, in the shape a stored record may carry."""
    rc: int | None
    timed_out: bool
    first_failure: str | None
    failure_kind: str | None
    wall_s: float | None

    def as_json(self) -> dict:
        """Exactly the record contract's command_result keys, in its order."""
        return asdict(self)


def classify_failure(text: str) -> str:
    """Read output as a tool error, a test failure, or neither.

    Tool markers are tested first, over the whole text: a run that prints a
    failing test and a collection error is the harness's own environment
    breaking, whichever of the two the run happened to print first.
    """
    if any(marker in text for marker in TOOL_MARKERS):
        return "tool"
    if any(marker in text for marker in TEST_MARKERS):
        return "test"
    return "unknown"


def _first_failure(text: str) -> str | None:
    """The first marked line, or the first non-blank line of the last forty."""
    lines = text.splitlines()
    for line in lines:
        if classify_failure(line) != "unknown":
            return line
    for line in lines[-_FALLBACK_LINES:]:
        if line.strip():
            return line
    return None


class ProcessTree:
    """Opaque handle to a child and every process it spawns.

    POSIX: the session the child leads, so a grandchild whose parent has already
    exited still carries the group id and is still reachable. A descendant that
    calls setsid of its own accord leaves the group and is out of reach: the
    handle answers for the group, not for every process the command ever begat.

    Windows: a job object the child joins while it is still suspended, so no
    descendant of it can be born outside the boundary. The job handle is held
    here until the tree has been reaped - the job kills what is left in it as
    soon as its last handle closes, so a handle let go early would kill the tree
    early, and one held past the reap would backstop the whole session rather
    than this one command.
    """

    def __init__(self, process: subprocess.Popen) -> None:
        self._process = process
        self._win32 = None
        self._job = None
        self._last_seen = True
        if os.name == "nt":
            self._contain()
            return
        # start_new_session makes the child the leader of its own group, so the
        # group id is its pid and no getpgid call can lose it to a race.
        self._pgid = process.pid

    def _contain(self) -> None:
        """Job the suspended child and then let it go; a refusal halts the run.

        The layer is imported here and reached as an attribute of the module,
        which is what keeps the platform choice a decision made at run time on
        the host that is actually running.
        """
        from eval_harness import win32
        self._win32 = win32
        try:
            self._job = win32.create_job()
            win32.assign_process(self._job, self._process.pid)
            win32.resume_process(self._process.pid)
        except win32.Win32Error as refusal:
            # The child is suspended and now uncontainable - never in the job,
            # or in it and not to be let go - so it dies here: raising past it
            # would leave it alive with nothing holding it.
            self._process.kill()
            self._process.wait()
            self.release()
            raise JobAssignmentError("the host would not contain the child") from refusal

    def release(self) -> None:
        """Let the job handle go, once: what the reap left in the job dies with it.

        Nothing is asked of the job after this. `survivors` keeps answering, from
        what the reap last saw, because the orphan question is asked once the
        tree is back in the caller's hands.
        """
        if self._job is None:
            return
        job, self._job = self._job, None
        self._win32.close_job(job)

    def terminate(self, escalate_after_s: float) -> None:
        """Kill the tree: the job in one call, or SIGTERM then SIGKILL on a group."""
        if self._win32 is not None:
            # The job ends every member at once, so there is no slow exit to
            # give a window to and nothing harsher to escalate to. A released
            # job has ended what was left in it, and is not asked again.
            if self._job is not None:
                self._win32.terminate_job(self._job)
            self._process.wait()
            return
        self._signal(signal.SIGTERM)
        if not self._emptied_within(escalate_after_s):
            self._signal(signal.SIGKILL)
        self._process.wait()

    def survivors(self) -> bool:
        """Whether any member of the tree is still there.

        Windows answers from the job's own list of member pids, which holds the
        members that are still running and nothing else; a released job is not
        asked again, so the answer is the last one the reap saw.

        EPERM never means "nobody there": it means the group has a member this
        process may not signal. On macOS an exited direct child reads that way
        until its parent collects it, and that zombie holds no port and runs no
        code - so collect it and probe again. What answers EPERM the second
        time cannot be that zombie, so it is a member that really is there.
        """
        if self._win32 is not None:
            if self._job is not None:
                self._last_seen = bool(self._win32.job_process_ids(self._job))
            return self._last_seen
        answer = self._probe()
        if answer is None:
            self._process.poll()
            answer = self._probe()
        # None here is the unsignalable member - a descendant that changed uid,
        # say. Reading it as an empty group would suppress the orphan halt this
        # module exists to raise, so it counts as a survivor.
        return answer is not False

    def _probe(self) -> bool | None:
        """Signal zero to the group: there, gone, or EPERM and unanswered."""
        try:
            os.killpg(self._pgid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            return None
        return True

    def _signal(self, number: int) -> None:
        """Signal the whole group; an empty group is the outcome that was wanted."""
        try:
            os.killpg(self._pgid, number)
        except (ProcessLookupError, PermissionError):
            pass

    def _emptied_within(self, seconds: float) -> bool:
        """Poll until the group empties, so a prompt exit waits no longer than it took."""
        deadline = time.monotonic() + seconds
        while True:
            # Collect the direct child before asking: an unreaped zombie is
            # still a member, and the answer for it is EPERM, not "nobody here".
            self._process.poll()
            if not self.survivors():
                return True
            if time.monotonic() >= deadline:
                return False
            time.sleep(_POLL_S)


@contextmanager
def _log_at(stdout_path: Path | None) -> Iterator[Path]:
    """The file the command's output is written to: the caller's, or a scratch one."""
    if stdout_path is not None:
        yield stdout_path
        return
    with tempfile.TemporaryDirectory() as scratch:
        yield Path(scratch) / "output.txt"


def _start(argv: Sequence[str], cwd: Path, env: dict[str, str] | None, log: Path,
           stderr_log: Path | None) -> subprocess.Popen:
    """Start the command inside a boundary of its own, its streams landing in `log`.

    stderr joins stdout there unless `stderr_log` names a sink of its own. A
    child the host would not create is a LaunchError chained to the refusal,
    and leaves no capture behind: a file nothing wrote to is not evidence.
    """
    boundary_kwargs = {"start_new_session": True}
    if os.name == "nt":
        from eval_harness import win32
        # Suspended rather than contained: the job assignment has to land before
        # the child's first instruction, or a grandchild is born outside the job.
        boundary_kwargs = {"creationflags": win32.CREATE_SUSPENDED}
    with ExitStack() as opened:
        stdout = opened.enter_context(open(log, "wb"))
        stderr = subprocess.STDOUT
        if stderr_log is not None:
            stderr = opened.enter_context(open(stderr_log, "wb"))
        try:
            return subprocess.Popen(list(argv), cwd=str(cwd), env=env, stdin=subprocess.DEVNULL,
                                    stdout=stdout, stderr=stderr, **boundary_kwargs)
        except OSError as refusal:
            # Closed before unlinked: Windows will not delete a file still open.
            opened.close()
            log.unlink(missing_ok=True)
            if stderr_log is not None:
                stderr_log.unlink(missing_ok=True)
            raise LaunchError("the host would not create the child: %s" % refusal) from refusal


def _exit_within(process: subprocess.Popen, timeout_s: float) -> tuple[int | None, bool]:
    """The child's exit code, or no code and a timeout when the bound ran out first."""
    try:
        return process.wait(timeout=timeout_s), False
    except subprocess.TimeoutExpired:
        return None, True


def run_bounded(argv: Sequence[str], cwd: Path, timeout_s: float, *,
                env: dict[str, str] | None = None,
                stdout_path: Path | None = None,
                stderr_path: Path | None = None,
                escalate_after_s: float = 60.0,
                settle_s: float = 5.0) -> tuple[CommandResult, ProcessTree]:
    """Run one command under a bound, then reap its whole process group.

    The bound measures the direct child: a command that exits while a descendant
    lingers has finished, and the descendant is the reap's question rather than
    the bound's. The tree is returned instead of a pid, which stops answering
    the orphan question the moment the direct child exits. Both streams land in
    the stdout log unless `stderr_path` gives stderr its own; the result's
    failure fields read the stdout log either way.
    """
    with _log_at(stdout_path) as log:
        started = time.monotonic()
        process = _start(argv, cwd, env, log, stderr_path)
        tree = ProcessTree(process)
        rc, timed_out = _exit_within(process, timeout_s)
        wall_s = time.monotonic() - started
        reap(tree, escalate_after_s=escalate_after_s, settle_s=settle_s)
        text = log.read_text(encoding="utf-8", errors="replace")
        result = CommandResult(rc=rc, timed_out=timed_out, first_failure=_first_failure(text),
                               failure_kind=classify_failure(text), wall_s=wall_s)
    return result, tree


def reap(tree: ProcessTree, *, escalate_after_s: float = 60.0,
         settle_s: float = 5.0) -> bool:
    """Kill the tree and answer whether the group emptied inside the settle window.

    The job handle goes once the answer is in, on every way out: a member the
    settle window did not see leave dies with the handle, and a tree reaped a
    second time has nothing left to release.
    """
    try:
        tree.terminate(escalate_after_s)
        deadline = time.monotonic() + settle_s
        while tree.survivors():
            if time.monotonic() >= deadline:
                return False
            time.sleep(_POLL_S)
        return True
    finally:
        tree.release()


def run_segments(segments: Sequence[str], cwd: Path, deadline_s: float, *,
                 env: dict[str, str] | None = None) -> CommandResult | None:
    """Run each segment as `bash -lc`, one deadline over the whole list.

    Each segment travels as one argv element, so no segment's text is ever read
    by this process's own shell. The list stops at the first segment that fails
    or runs out of time and answers with that segment's result; nothing to run
    is None, never a zero exit.
    """
    started = time.monotonic()
    result = None
    for segment in segments:
        remaining = deadline_s - (time.monotonic() - started)
        result, tree = run_bounded(["bash", "-lc", segment], cwd, remaining, env=env)
        if tree.survivors():
            raise OrphanError("%s: the process group still has members" % segment)
        if result.rc != 0:
            return result
    return result


def _label_in_flight(marker: Path) -> str:
    """The label a marker carries; one released mid-read still refuses the gate."""
    try:
        return marker.read_text(encoding="utf-8").strip()
    except OSError:
        return "unknown"


@contextmanager
def gate_lock(run_dir: Path, label: str) -> Iterator[None]:
    """Hold the run's one gate marker for the length of one gate.

    The marker is taken with an exclusive create, so two gates racing from
    separate processes cannot both read an absent marker and both walk in. It
    is left in place when the gate's descendants outlive it: they are what the
    next gate must not start beside.
    """
    marker = run_dir / GATE_MARKER
    try:
        held = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise GateConcurrencyError("gate in flight: %s" % _label_in_flight(marker)) from None
    try:
        os.write(held, ("%s\n" % label).encode("utf-8"))
    finally:
        os.close(held)
    survived = False
    try:
        yield
    except OrphanError:
        # Only this exit reports members still running; every other one, clean
        # or not, leaves nothing behind for the marker to guard.
        survived = True
        raise
    finally:
        if not survived:
            os.unlink(marker)
