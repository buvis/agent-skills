"""Tests for what the bounded runner leaves behind when containment goes wrong.

A separate module because `test_eval_tree_containment.py` already stands at the
size this project caps a test file at; it lends this one its Windows-branch
fakes instead.

Three promises, each about what is left behind. A resume the host refuses ends
the held child and halts the run under the containment name, never as a bare
Win32 failure. The job handle is released once per tree on every path out of
`run_bounded`, so kill-on-close backstops this attempt rather than the whole
session. A gate whose body reports survivors keeps its marker, because the
marker is what stops the next gate from starting beside them.

One more, about what the released tree still knows. `run_segments` asks
`survivors()` after `run_bounded` has returned, when the handle is already gone,
so the tree answers from what the reap last saw and never asks the released job
again. The fake refuses any call on a released job the way kernel32 would, so a
use after release fails on this host and not only on Windows.

No case carries a platform marker: the Windows branch is driven through a fake
layer on whichever host this is, exactly as the containment module does it.
"""
import os
import subprocess
import sys

import pytest

import eval_harness
from eval_harness import runner
from test_eval_tree_containment import (
    WAITS_FOR_RESUME,
    _ModuleWithOverrides,
    _RecordingWin32,
)

# The resume-waiting child, with one more witness: a child that is never let go
# and never killed leaves on its own deadline, and says so on the way out. That
# file is what tells "killed while held" apart from "left to give up", which the
# exit code alone cannot on every platform.
GIVES_UP_IF_NEVER_RESUMED = (
    "import os, sys, time\n"
    "deadline = time.monotonic() + 5.0\n"
    "while not os.path.exists(sys.argv[1]):\n"
    "    if time.monotonic() >= deadline:\n"
    "        with open(sys.argv[3], 'w', encoding='utf-8') as gave_up:\n"
    "            gave_up.write('gave up\\n')\n"
    "        sys.exit(1)\n"
    "    time.sleep(0.01)\n"
    "with open(sys.argv[2], 'w', encoding='utf-8') as mark:\n"
    "    mark.write('ran\\n')\n"
)

# The resume-waiting child that then sits past the bound, so the run has to
# time out and the reap has to do the ending. Its own sleep is what stops a
# tree nothing killed from outliving the test.
LINGERS_AFTER_RESUME = WAITS_FOR_RESUME + "time.sleep(3.0)\n"


class _OwningWin32(_RecordingWin32):
    """The recording fake, extended with the job's release and a resume that can fail.

    `create_job` hands out a fresh object each time, so the release can be
    matched to the very job it was asked for rather than to any string.
    `terminate_job` ends the real child the way the job would on Windows, so a
    runner that kills through the job rather than through the `Popen` is not
    failed for the fake's sake; with `member_survives` set it leaves the job's
    pid list non-empty, which is a member the kill did not reach. `close_job`
    records the release, and every job call after it fails with
    ERROR_INVALID_HANDLE, exactly what kernel32 answers on a closed handle.
    """

    def __init__(self, gate, mark) -> None:
        super().__init__(gate, mark)
        self.refuse_resume = False
        self.member_survives = False
        self.jobs = []
        self.closed = []
        self.members = set()
        self.process = None

    def create_job(self, *args):
        self.calls.append("create_job")
        job = object()
        self.jobs.append(job)
        return job

    def assign_process(self, job, pid):
        self._refuse_if_released("AssignProcessToJobObject", job)
        super().assign_process(job, pid)
        # Only a pid the assignment accepted is a member: a refused child was
        # never in the job, so the job's kill cannot reach it.
        self.members.add(pid)

    def resume_process(self, *args):
        if self.refuse_resume:
            self.calls.append("resume_process")
            raise self.Win32Error("ResumeThread", 6)
        super().resume_process(*args)

    def terminate_job(self, job):
        self._refuse_if_released("TerminateJobObject", job)
        self.calls.append("terminate_job")
        if self.process is not None and self.process.pid in self.members:
            self.process.kill()
        if not self.member_survives:
            self.live = False

    def job_process_ids(self, job):
        self._refuse_if_released("QueryInformationJobObject", job)
        return super().job_process_ids(job)

    def close_job(self, job):
        self.calls.append("close_job")
        self.closed.append(job)

    def _refuse_if_released(self, call: str, job) -> None:
        # Recorded before it is refused, so a runner that swallows the refusal
        # still leaves the use-after-release in `calls` for the assertions.
        if job in self.closed:
            self.calls.append(call)
            raise self.Win32Error(call, 6)


def _process_keeping_popen(fake: _OwningWin32):
    """A `Popen` that drops the creation flags and keeps the child it started.

    The child is what the assertions ask afterwards - whether it was waited on -
    and what the fake's `terminate_job` ends, so it lives on the fake.
    """
    real = subprocess.Popen

    def _popen(*args, **kwargs):
        fake.creation_flags = kwargs.pop("creationflags", 0)
        fake.calls.append("popen")
        fake.process = real(*args, **kwargs)
        return fake.process

    return _popen


def _drive_owning_windows_branch(
    monkeypatch, tmp_path, source: str = WAITS_FOR_RESUME
) -> tuple:
    """`_drive_windows_branch`, with the fake that owns a job and keeps its child."""
    child = tmp_path / "child.py"
    child.write_text(source, encoding="utf-8")
    gate = tmp_path / "resumed"
    mark = tmp_path / "mark.txt"
    fake = _OwningWin32(gate, mark)
    monkeypatch.setitem(sys.modules, "eval_harness.win32", fake)
    monkeypatch.setattr(eval_harness, "win32", fake, raising=False)
    monkeypatch.setattr(runner, "os", _ModuleWithOverrides(os, name="nt"))
    monkeypatch.setattr(
        runner, "subprocess",
        _ModuleWithOverrides(subprocess, Popen=_process_keeping_popen(fake)),
    )
    return fake, [sys.executable, str(child), str(gate), str(mark)], mark


def test_a_resume_the_host_refuses_ends_the_held_child_and_halts_the_run_as_a_containment_failure(
    tmp_path, monkeypatch
):
    # The child is already in the job when the resume fails, so a run that let
    # the Win32 failure out would leave it held forever with no attempt record
    # to say so. The halt has to travel under the containment name the harness
    # already stops on, and the child has to be gone before it does.
    fake, argv, mark = _drive_owning_windows_branch(
        monkeypatch, tmp_path, GIVES_UP_IF_NEVER_RESUMED
    )
    gave_up = tmp_path / "gave_up.txt"
    fake.refuse_resume = True

    returned = None
    with pytest.raises(runner.JobAssignmentError) as halt:
        returned = runner.run_bounded(
            argv + [str(gave_up)], tmp_path, 30.0, stdout_path=tmp_path / "out.log",
            escalate_after_s=0.25, settle_s=1.0,
        )

    assert returned is None, "the child nobody could resume came back as a scoreable result"
    assert halt.value.reason == "job_assignment_failed"
    cause = halt.value.__cause__ or halt.value.__context__
    assert isinstance(cause, fake.Win32Error), "the Win32 failure was swallowed"
    assert cause.call == "ResumeThread"
    # Killed and waited on, rather than abandoned: an abandoned child has no
    # exit code yet, and one merely waited on leaves through its own deadline
    # and says so.
    assert fake.process.returncode is not None, "the held child was never waited on"
    assert not gave_up.exists(), "the child ran out its own deadline instead of being killed"
    assert len(fake.jobs) == 1
    assert fake.closed == fake.jobs, "the job was not released, or not the one created"
    assert fake.calls[-1] == "close_job", "the job was still used after its handle was released"


def test_a_job_assignment_the_host_refuses_still_releases_the_job(tmp_path, monkeypatch):
    # The job exists before the assignment fails, so the setup-failure path owns
    # a handle too. Exactly one release, of that handle, and nothing asked of
    # the job after it. The child was never in that job, so releasing it ends
    # nothing: the child has to be killed and waited on in its own right.
    fake, argv, mark = _drive_owning_windows_branch(
        monkeypatch, tmp_path, GIVES_UP_IF_NEVER_RESUMED
    )
    gave_up = tmp_path / "gave_up.txt"
    fake.refuse = True

    with pytest.raises(runner.JobAssignmentError):
        runner.run_bounded(
            argv + [str(gave_up)], tmp_path, 30.0, stdout_path=tmp_path / "out.log",
            escalate_after_s=0.25, settle_s=1.0,
        )

    assert fake.process.returncode is not None, "the held child was never waited on"
    assert not gave_up.exists(), "the child ran out its own deadline instead of being killed"
    assert len(fake.jobs) == 1
    assert fake.closed == fake.jobs, "the job was not released, or not the one created"
    assert fake.calls[-1] == "close_job", "the job was still used after its handle was released"


@pytest.mark.parametrize(
    ("source", "timeout_s", "timed_out", "member_survives"),
    [
        pytest.param(WAITS_FOR_RESUME, 30.0, False, False, id="completed"),
        pytest.param(LINGERS_AFTER_RESUME, 1.0, True, False, id="timed_out"),
        pytest.param(WAITS_FOR_RESUME, 30.0, False, True, id="a_member_survives"),
    ],
)
def test_the_job_handle_is_released_once_after_the_reap_and_not_again_by_a_second_reap(
    tmp_path, monkeypatch, source, timeout_s, timed_out, member_survives
):
    # Kill-on-close is the backstop for a tree the reap missed, and it fires
    # when the handle closes: one held until the harness exits backstops the
    # whole session rather than this attempt. So the release follows the reap,
    # once, whatever the reap answered, and a later reap of the same tree has
    # nothing left to release. Between the kill and the release the reap has to
    # ask the job whether it emptied: a reap that never asks can never report
    # the member it missed, and the orphan halt never fires for a Windows tree.
    fake, argv, mark = _drive_owning_windows_branch(monkeypatch, tmp_path, source)
    fake.member_survives = member_survives

    result, tree = runner.run_bounded(
        argv, tmp_path, timeout_s, stdout_path=tmp_path / "out.log",
        escalate_after_s=0.25, settle_s=1.0,
    )

    assert result.timed_out is timed_out
    assert mark.exists(), "the child never ran, so nothing here was contained"
    assert len(fake.jobs) == 1
    assert fake.closed == fake.jobs, "the job was not released, or not the one created"
    terminated = fake.calls.index("terminate_job")
    released = fake.calls.index("close_job")
    assert terminated < released, "the job was released before the tree was reaped"
    assert "job_process_ids" in fake.calls[terminated:released], (
        "the reap never asked the job whether it had emptied"
    )
    assert fake.calls[-1] == "close_job", "the job was still used after its handle was released"

    # The released tree still answers the orphan question, which `run_segments`
    # asks only now, from what the reap last saw: the job is gone and is not
    # asked again.
    assert tree.survivors() is member_survives
    assert fake.calls[-1] == "close_job", "the tree asked a job whose handle was released"

    assert runner.reap(tree, escalate_after_s=0.25, settle_s=1.0) is (not member_survives)
    assert fake.calls.count("close_job") == 1, "a second reap released the handle again"
    assert fake.calls[-1] == "close_job", "a second reap used a job whose handle was released"


def test_gate_lock_keeps_its_marker_when_an_orphan_error_escapes_and_drops_it_otherwise(
    tmp_path,
):
    # An OrphanError says the gate's descendants are still alive. The marker is
    # what stops the next gate from starting beside them, so the exception that
    # reports survivors is the one exit that must leave it in place. Every other
    # exit, clean or not, has nothing left behind to guard.
    marker = tmp_path / runner.GATE_MARKER

    with pytest.raises(runner.OrphanError):
        with runner.gate_lock(tmp_path, "vet"):
            assert marker.exists()
            raise runner.OrphanError("2 processes survived the reap")

    assert marker.exists(), "the marker was released while the gate's descendants still ran"
    with pytest.raises(runner.GateConcurrencyError):
        with runner.gate_lock(tmp_path, "run"):
            pass
    assert marker.exists(), "the refused gate took the surviving gate's marker with it"

    marker.unlink()
    with runner.gate_lock(tmp_path, "run"):
        assert marker.exists()
    assert not marker.exists(), "a clean exit left the marker behind"

    with pytest.raises(ValueError):
        with runner.gate_lock(tmp_path, "run"):
            raise ValueError("not about survivors")
    assert not marker.exists(), "an exception that reports no survivors left the marker behind"

    # The halt a gate really raises when the host will not contain a child: a
    # sibling of OrphanError, not a kind of it. Nothing of that gate's is left
    # running, so nothing of its marker's may be left either.
    with pytest.raises(runner.JobAssignmentError):
        with runner.gate_lock(tmp_path, "run"):
            raise runner.JobAssignmentError("the host would not contain the child")
    assert not marker.exists(), "a containment halt with no survivors left the marker behind"
