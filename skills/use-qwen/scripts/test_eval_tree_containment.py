"""Tests for process-tree containment: the guarantee, on POSIX and on Windows.

A separate module because `test_eval_trees.py` already stands at the size this
project caps a test file at.

The behavioural cases here carry no platform marker at all. Containment is a
promise about what happens to a command's descendants, not about the mechanism
underneath it, so a case that ran on POSIX only would leave the platform whose
mechanism is newest as the one the suite never exercises. The cases that reach
past the guarantee and into one platform's own machinery are the only marked
ones, and they say which machinery in their marker.
"""
import ast
import os
import subprocess
import sys
from pathlib import Path

import pytest

import eval_harness
from eval_harness import runner
from eval_harness_fixture_helpers import (
    _engine_argv,
    _engine_env,
    _grew_within,
    _prompt_in,
    _stopped_growing,
)

POSIX_ONLY = pytest.mark.skipif(
    os.name == "nt",
    reason="a statement about what a non-Windows host imports",
)

POSIX_MECHANISM = pytest.mark.skipif(
    os.name == "nt",
    reason="wires a process group by hand, which is the POSIX mechanism itself",
)

WINDOWS_ONLY = pytest.mark.skipif(
    os.name != "nt",
    reason="a failure of the Win32 job object, which exists on Windows only",
)

SCRIPTS_DIR = Path(__file__).resolve().parent

# A grandchild that appends a beat every 50 ms: a file that stops growing is the
# witness that it was killed, written by a process the tree handle never
# consulted. Its own deadline is short enough that one that escapes containment
# leaves on its own rather than outliving the test session by minutes.
BEATS = (
    "import sys, time\n"
    "deadline = time.monotonic() + 60.0\n"
    "while time.monotonic() < deadline:\n"
    "    with open(sys.argv[1], 'a', encoding='utf-8') as beats:\n"
    "        beats.write('beat\\n')\n"
    "    time.sleep(0.05)\n"
)

# A child whose first instruction spawns that grandchild. Containment that is
# arranged after the child is already running leaves exactly this window open,
# and a grandchild born inside it is outside the boundary for the rest of the
# run - so the spawn leads, before anything else the child could be doing.
#
# What follows the spawn is only proof that the grandchild reached the point of
# writing: without it an empty beat file means "spawn broken" and "kill worked"
# equally, and the case cannot tell them apart. Then the child leaves without
# an interpreter shutdown, well before the kill, so anything that contains this
# tree by walking live parent/child links has no link left to walk. The
# grandchild's streams are its own, so it never holds the command's pipe open.
SPAWNS_THEN_EXITS = (
    "import os, subprocess, sys, time\n"
    "subprocess.Popen(\n"
    "    [sys.executable, sys.argv[1], sys.argv[2]],\n"
    "    stdin=subprocess.DEVNULL,\n"
    "    stdout=subprocess.DEVNULL,\n"
    "    stderr=subprocess.DEVNULL,\n"
    ")\n"
    "deadline = time.monotonic() + 30.0\n"
    "while time.monotonic() < deadline:\n"
    "    if os.path.exists(sys.argv[2]) and os.path.getsize(sys.argv[2]) > 0:\n"
    "        break\n"
    "    time.sleep(0.01)\n"
    "os._exit(0)\n"
)

# A child whose whole life is one visible mark. If containment is arranged while
# it is suspended, the mark is never made - so the file's absence is what says
# the child never executed, and the same file's presence in the control run is
# what says the mark was reachable at all.
LEAVES_A_MARK = (
    "import sys\n"
    "with open(sys.argv[1], 'w', encoding='utf-8') as mark:\n"
    "    mark.write('ran\\n')\n"
)

# Asked in a fresh interpreter, so no other test's imports can answer for it.
# The first line is the control: it names a module the probe just imported, so a
# probe that cannot see an import at all fails instead of reporting a clean
# graph.
IMPORT_PROBE = (
    "import sys\n"
    "import eval_harness.runner\n"
    "print('runner', 'eval_harness.runner' in sys.modules)\n"
    "print('win32', 'eval_harness.win32' in sys.modules)\n"
)

# A child that can do nothing until it is let go. A real Windows child is held
# by the operating system between creation and the resume; a POSIX host cannot
# hold one that way, so the child holds itself and the fake layer's
# `resume_process` is what opens the gate. Its own deadline is what stops it
# outliving a run that never resumes it.
WAITS_FOR_RESUME = (
    "import os, sys, time\n"
    "deadline = time.monotonic() + 5.0\n"
    "while not os.path.exists(sys.argv[1]):\n"
    "    if time.monotonic() >= deadline:\n"
    "        sys.exit(1)\n"
    "    time.sleep(0.01)\n"
    "with open(sys.argv[2], 'w', encoding='utf-8') as mark:\n"
    "    mark.write('ran\\n')\n"
)

# Every name the containment path reaches for on the Windows side: the flag the
# child is created with, the five job calls, the resume, and the failure they
# raise.
WIN32_SURFACE = (
    "CREATE_SUSPENDED",
    "Win32Error",
    "create_job",
    "assign_process",
    "terminate_job",
    "job_process_ids",
    "close_job",
    "resume_process",
)


def _spawning_child(tmp_path) -> tuple:
    """A command that leaves a beating grandchild behind, and that beat file."""
    beater = tmp_path / "beater.py"
    beater.write_text(BEATS, encoding="utf-8")
    child = tmp_path / "child.py"
    child.write_text(SPAWNS_THEN_EXITS, encoding="utf-8")
    heartbeat = tmp_path / "beats" / "hb.log"
    heartbeat.parent.mkdir(parents=True)
    return [sys.executable, str(child), str(beater), str(heartbeat)], heartbeat


def _module_level_names(source: str) -> set:
    """Every name a module binds at its top level, read rather than imported."""
    names = set()
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            names.update(t.id for t in node.targets if isinstance(t, ast.Name))
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            names.add(node.target.id)
    return names


class _FakeWin32Error(Exception):
    """The Windows layer's failure, in the shape the runner has to catch."""

    def __init__(self, call: str, code: int) -> None:
        super().__init__("%s failed: %d" % (call, code))
        self.call = call
        self.code = code


class _RecordingWin32:
    """A stand-in for the Windows layer that records what the runner asks of it.

    The runner reaches these as attributes of an imported module, so a fake put
    where that import looks is enough to drive the Windows branch on any host.
    `resume_process` opens the gate the child is waiting on, which is as close as
    a POSIX host gets to a child the operating system was holding.
    """

    # Deliberately not the real 0x4: the flag has to come from the module that
    # defines it, and a constant written into the runner by hand would pass a
    # test that only looked for 0x4.
    CREATE_SUSPENDED = 0x00A00000
    Win32Error = _FakeWin32Error

    def __init__(self, gate: Path, mark: Path) -> None:
        self.calls = []
        self.creation_flags = 0
        self.mark_at_assign = None
        self.live = True
        self.refuse = False
        self._gate = gate
        self._mark = mark

    def create_job(self, *args):
        self.calls.append("create_job")
        return "job"

    def assign_process(self, job, pid):
        self.calls.append("assign_process")
        self.mark_at_assign = self._mark.exists()
        if self.refuse:
            raise _FakeWin32Error("AssignProcessToJobObject", 5)

    def resume_process(self, *args):
        self.calls.append("resume_process")
        self._gate.write_text("go\n", encoding="utf-8")

    def terminate_job(self, *args):
        self.calls.append("terminate_job")
        self.live = False

    def job_process_ids(self, *args):
        self.calls.append("job_process_ids")
        return [4242] if self.live else []

    def close_job(self, *args):
        self.calls.append("close_job")


class _ModuleWithOverrides:
    """A module with some names replaced and every other one still the real thing."""

    def __init__(self, module, **overrides) -> None:
        self._module = module
        self._overrides = overrides

    def __getattr__(self, name: str):
        if name in self._overrides:
            return self._overrides[name]
        return getattr(self._module, name)


def _recording_popen(fake: _RecordingWin32):
    """A `Popen` that records the creation flags and then drops them.

    POSIX refuses `creationflags` outright and Windows would hold the child for
    real, so neither host can run this wiring with the flag left in place. What
    the runner asked for is recorded, and the child is started without it.
    """
    real = subprocess.Popen

    def _popen(*args, **kwargs):
        fake.creation_flags = kwargs.pop("creationflags", 0)
        fake.calls.append("popen")
        return real(*args, **kwargs)

    return _popen


def _drive_windows_branch(monkeypatch, tmp_path) -> tuple:
    """Point the runner at a fake Windows layer, whichever host this is.

    The platform the runner reads is the only thing lied to, and the lie is kept
    in that module's own globals: `pathlib`, `tempfile` and pytest itself keep
    seeing the host they are really on, which a patched `os.name` would not.
    """
    child = tmp_path / "child.py"
    child.write_text(WAITS_FOR_RESUME, encoding="utf-8")
    gate = tmp_path / "resumed"
    mark = tmp_path / "mark.txt"
    fake = _RecordingWin32(gate, mark)
    monkeypatch.setitem(sys.modules, "eval_harness.win32", fake)
    monkeypatch.setattr(eval_harness, "win32", fake, raising=False)
    monkeypatch.setattr(runner, "os", _ModuleWithOverrides(os, name="nt"))
    monkeypatch.setattr(
        runner, "subprocess",
        _ModuleWithOverrides(subprocess, Popen=_recording_popen(fake)),
    )
    return fake, [sys.executable, str(child), str(gate), str(mark)], mark


def test_a_child_that_outlives_the_bound_is_killed_with_the_tree_on_every_platform(
    tmp_path,
):
    # The `hang` fixture: a parent that sits past the bound while a child of its
    # own beats. Killing the parent alone leaves that child beating, so the beat
    # file answers for the whole tree rather than for the process the runner
    # holds a handle to.
    heartbeat = tmp_path / "beats" / "hb.log"
    heartbeat.parent.mkdir(parents=True)

    result, tree = runner.run_bounded(
        _engine_argv("hang", _prompt_in(tmp_path / "prompt")),
        tmp_path,
        2.0,
        env=_engine_env("hang", tmp_path / "attempt", heartbeat),
        escalate_after_s=0.25,
        settle_s=1.0,
    )

    assert result.timed_out is True
    assert heartbeat.stat().st_size > 0, "the beating grandchild never started"
    assert _stopped_growing(heartbeat), "the grandchild outlived the terminated tree"
    # The handle and the witness have to agree: a `survivors()` that answers
    # from the direct child alone says False here whether or not the grandchild
    # is still beating, and the line above is what tells those apart.
    assert tree.survivors() is False
    assert runner.reap(tree, escalate_after_s=0.25, settle_s=1.0) is True


def test_a_grandchild_of_a_parent_that_exits_at_once_is_still_reachable_to_the_reap(
    tmp_path,
):
    argv, heartbeat = _spawning_child(tmp_path)

    result, tree = runner.run_bounded(
        argv, tmp_path, 30.0, escalate_after_s=0.25, settle_s=1.0
    )

    assert result.rc == 0
    assert result.timed_out is False
    # The child waited for this before leaving, so an empty file is a broken
    # spawn and nothing else.
    assert heartbeat.stat().st_size > 0, "the grandchild never started"
    assert runner.reap(tree, escalate_after_s=0.25, settle_s=1.0) is True
    assert tree.survivors() is False
    assert _stopped_growing(heartbeat), "the kill never reached the grandchild"


@POSIX_MECHANISM
def test_a_tree_that_is_still_beating_reads_as_a_survivor_until_it_is_reaped(tmp_path):
    # Every case that goes through `run_bounded` asks the handle after the reap
    # has already emptied the tree, where "nobody left" is the true answer and a
    # handle that always said so would pass. This one holds a live tree first,
    # so both answers have to be earned. The group is wired by hand because
    # `run_bounded` never hands one back unreaped.
    argv, heartbeat = _spawning_child(tmp_path)
    process = subprocess.Popen(
        argv, cwd=str(tmp_path), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, start_new_session=True,
    )
    tree = runner.ProcessTree(process)

    # The beats are a process the handle never consulted saying it is alive.
    assert _grew_within(heartbeat, 2.0) is True, "the grandchild never started"
    assert tree.survivors() is True

    assert runner.reap(tree, escalate_after_s=0.25, settle_s=1.0) is True
    assert tree.survivors() is False
    assert _stopped_growing(heartbeat), "the kill never reached the grandchild"


@POSIX_ONLY
def test_importing_the_runner_on_a_non_windows_host_never_imports_the_win32_layer():
    # The Windows containment layer ships on every platform and is imported on
    # one. Present but unimported is the whole claim, so the case asserts both
    # halves: a deleted module would otherwise satisfy the import graph.
    assert (SCRIPTS_DIR / "eval_harness" / "win32.py").is_file(), (
        "the Windows containment layer is not in the package"
    )

    probe = subprocess.run(
        [sys.executable, "-c", IMPORT_PROBE],
        cwd=str(SCRIPTS_DIR),
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert probe.returncode == 0, probe.stderr
    assert probe.stdout.split() == ["runner", "True", "win32", "False"], probe.stdout


def test_the_windows_layer_defines_every_name_the_containment_path_calls():
    # Read, never imported: `ctypes.WinDLL` does not exist off Windows, so no
    # host but that one can ask the module itself. This says the surface is
    # there and nothing at all about whether it works - the cases below are
    # what exercise it - so an empty file fails here and passes nowhere else.
    source = (SCRIPTS_DIR / "eval_harness" / "win32.py").read_text(encoding="utf-8")

    defined = _module_level_names(source)

    missing = [name for name in WIN32_SURFACE if name not in defined]
    assert not missing, "the Windows layer never defines %s" % missing


def test_the_windows_branch_puts_the_child_in_a_job_before_it_can_execute(
    tmp_path, monkeypatch
):
    # Windows containment is arranged around a child that cannot run yet, and
    # the order is most of the guarantee: job, then assignment, then release.
    # A fake layer drives it here, so the wiring is exercised on the host this
    # suite actually runs on rather than only on the one it cannot reach.
    fake, argv, mark = _drive_windows_branch(monkeypatch, tmp_path)

    result, tree = runner.run_bounded(
        argv, tmp_path, 30.0, stdout_path=tmp_path / "out.log",
        escalate_after_s=0.25, settle_s=1.0,
    )

    assert result.rc == 0
    assert mark.exists(), "the child never ran, so nothing here was contained"
    assert fake.calls.index("create_job") < fake.calls.index("assign_process")
    assert fake.calls.index("popen") < fake.calls.index("assign_process")
    assert fake.calls.index("assign_process") < fake.calls.index("resume_process")
    assert fake.mark_at_assign is False, "the child ran before it joined the job"
    assert fake.creation_flags & fake.CREATE_SUSPENDED == fake.CREATE_SUSPENDED, (
        "the child was not created suspended"
    )
    assert "terminate_job" in fake.calls, "the tree was killed some other way"
    # The handle is released once the reap has answered, so what survivors()
    # says afterwards is the reap's own verdict; the live pid-list reading is
    # pinned in test_eval_runner_containment.py, where the fake refuses any
    # call against a released job.
    assert tree.survivors() is False


def test_a_job_assignment_the_host_refuses_halts_the_run_on_either_platform(
    tmp_path, monkeypatch
):
    # The same halt the Windows-only case below asserts, driven by the fake
    # layer, so the name the failure travels under has coverage on the host the
    # suite runs on instead of only on the one it has never reached.
    fake, argv, mark = _drive_windows_branch(monkeypatch, tmp_path)
    fake.refuse = True

    returned = None
    with pytest.raises(runner.JobAssignmentError) as halt:
        returned = runner.run_bounded(
            argv, tmp_path, 30.0, stdout_path=tmp_path / "out.log",
            escalate_after_s=0.25, settle_s=1.0,
        )

    # A result handed back is an attempt-level outcome, and a host that cannot
    # contain one child cannot contain the next one either.
    assert returned is None, "the uncontainable child came back as a scoreable result"
    assert halt.value.reason == "job_assignment_failed"
    # The child is held until the resume, which a halted run never reaches.
    assert not mark.exists(), "the child executed before the run was halted"
    cause = halt.value.__cause__ or halt.value.__context__
    assert isinstance(cause, fake.Win32Error), "the Win32 failure was swallowed"
    assert cause.call == "AssignProcessToJobObject"
    assert cause.code == 5


@WINDOWS_ONLY
def test_a_host_that_cannot_contain_the_child_halts_the_run_instead_of_returning_it(
    tmp_path, monkeypatch
):
    # Imported here rather than at module scope: the layer exists on Windows only,
    # and the case above is the one that says so.
    from eval_harness import win32

    child = tmp_path / "child.py"
    child.write_text(LEAVES_A_MARK, encoding="utf-8")
    mark = tmp_path / "mark.txt"
    argv = [sys.executable, str(child), str(mark)]

    # The control: contained normally, this command does leave its mark. Without
    # it, a child script too broken to write anything would prove containment
    # just as convincingly as a child that never got to run.
    control, tree = runner.run_bounded(
        argv, tmp_path, 30.0, escalate_after_s=0.25, settle_s=1.0
    )
    assert control.rc == 0
    assert mark.read_text(encoding="utf-8").strip() == "ran"
    assert runner.reap(tree, escalate_after_s=0.25, settle_s=1.0) is True
    mark.unlink()

    def _refuse(job, pid):
        raise win32.Win32Error("AssignProcessToJobObject", 5)

    monkeypatch.setattr(win32, "assign_process", _refuse)

    returned = None
    with pytest.raises(runner.JobAssignmentError) as halt:
        returned = runner.run_bounded(
            argv, tmp_path, 30.0, escalate_after_s=0.25, settle_s=1.0
        )

    # A result handed back is an attempt-level outcome, and a host that cannot
    # contain one child cannot contain the next one either.
    assert returned is None, "the uncontainable child came back as a scoreable result"
    assert halt.value.reason == "job_assignment_failed"
    # The child was killed while still suspended, so its own first instruction
    # never ran. An exception raised after it had already run would satisfy the
    # `raises` above and still be the escape this case exists to catch.
    assert not mark.exists(), "the child executed before the run was halted"
    cause = halt.value.__cause__ or halt.value.__context__
    assert isinstance(cause, win32.Win32Error), "the Win32 failure was swallowed"
    assert cause.call == "AssignProcessToJobObject"
    assert cause.code == 5
