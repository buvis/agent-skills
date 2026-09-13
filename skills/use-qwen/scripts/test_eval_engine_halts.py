"""Tests for eval_harness/engines.py: halts after dispatch and the launch state.

The adapter cases replace what `dispatch` calls (`engines.run_bounded`) and
nothing else, so the runner the baseline and the gates go through is the real
one throughout. The run-level cases drive the real `run` driver against a copy
of the bundle `vetted` seals once per module, the way test_run_eval_harness
does; they live here because that module is at the file cap.
"""
import errno
import sys
from pathlib import Path

import pytest

import eval_harness_fixtures
import run_eval_harness
from eval_harness import engines, records, runner
from eval_harness_evidence_helpers import _read_json
from eval_harness_fixture_helpers import _engine_argv, _prompt_in

# The last three names are fixtures: pytest resolves them from this module's own
# namespace, so they have to be imported even though nothing here calls them.
from eval_harness_run_helpers import (
    OUTCOMES,
    _copy,
    _engine,
    _marker,
    _run_argv,
    _run_direct,
    scratch,
    shim,
    vetted,
)
from test_eval_engines import FAKE_IDENTITY, _dispatch_cmd

# What a runner that read the child's output and then lost it says; the
# progress log has to carry these words for the failure to be recorded.
POST_LAUNCH_MESSAGE = "simulated post-launch read failure"
CONTAINMENT_MESSAGE = "the host would not contain the child"


# -- helpers: the runner as `dispatch` sees it -------------------------------


def _post_launch_error(error):
    """An `error` wearing a refused launch's own errno and text.

    `str()` of it reads "[Errno 2] No such file or directory: '<message>'",
    which is what a launch the host refused says too: only where it was raised
    tells the two apart, so a classifier reading the words calls this
    not-started.
    """
    return error(errno.ENOENT, "No such file or directory", POST_LAUNCH_MESSAGE)


def _survive_after_the_engine(monkeypatch):
    """Run the child for real, then hand `dispatch` a tree that reports a survivor.

    Only the instance the engine dispatch is handed answers that way: the class
    is untouched, so every other command's tree still empties as it should.
    """
    real_run_bounded = runner.run_bounded

    def run_then_survive(*args, **kwargs):
        result, tree = real_run_bounded(*args, **kwargs)
        tree.survivors = lambda: True
        return result, tree

    monkeypatch.setattr(engines, "run_bounded", run_then_survive)


def _fail_after_the_child_ran(monkeypatch, error):
    """Run the child for real, then raise `error` the way a lost output read would."""
    real_run_bounded = runner.run_bounded

    def run_then_fail(*args, **kwargs):
        real_run_bounded(*args, **kwargs)
        raise _post_launch_error(error)

    monkeypatch.setattr(engines, "run_bounded", run_then_fail)


def _refuse_containment(monkeypatch):
    """Raise the runner's containment refusal; hand back the instance it will raise."""
    refusal = runner.JobAssignmentError(CONTAINMENT_MESSAGE)

    def raise_refusal(*args, **kwargs):
        raise refusal

    monkeypatch.setattr(engines, "run_bounded", raise_refusal)
    return refusal


def _dispatched_argv(tmp_path, mode="pass"):
    """The argv `_dispatch_cmd` dispatches the fake with, known before dispatch raises.

    The prompt is written first at the path `_dispatch_cmd` writes it to, so
    the argv can be compared even when nothing comes back from the call.
    """
    return _engine_argv(mode, _prompt_in(tmp_path / "prompts"))


# -- dispatch: survivors halt it ---------------------------------------------


def test_halts_the_dispatch_when_the_engine_tree_still_has_members(tmp_path, monkeypatch):
    # The run itself finished clean (exit 0, the fake's whole protocol), and
    # that is what the halt carries: the block measured before the survivors
    # were found, not a block that pretends nothing ran.
    _survive_after_the_engine(monkeypatch)
    argv = _dispatched_argv(tmp_path)

    with pytest.raises(runner.OrphanError) as caught:
        _dispatch_cmd(tmp_path, monkeypatch, eval_harness_fixtures.fake_engine_command("pass"))

    observed = caught.value.observed
    records.validate_record("engine_run", observed)
    assert observed["launch"] == "started"
    assert observed["argv"] == argv
    assert observed["exit"] == 0


def test_orphans_after_the_engine_halt_the_run(tmp_path, vetted, shim, monkeypatch):
    root = _copy(vetted.root, tmp_path.resolve() / "bundle")
    run = root / "runs" / "halt"
    _survive_after_the_engine(monkeypatch)

    rc = _run_direct(root, "halt", [_engine(shim, "pass"), _engine(shim, "noop")], "description")

    where = run / "1-cmd1-a1"
    record = _read_json(where / "attempt.json")
    halt = (run / "progress.log").read_text(encoding="utf-8").splitlines()[-1].split()
    headers, ids = _marker(run / "halted.txt")
    assert rc == 2
    assert (halt[0], Path(halt[1]).name, halt[2]) == ("HALTED:orphans", "1-cmd1-a1", "engine")
    assert headers == {
        "reason": "HALTED:orphans", "attempt": "1-cmd1-a1", "command": "engine", "attempts": "1",
    }
    assert ids == ["1-cmd1-a1"]
    assert not (run / "complete.txt").exists()
    assert not (run / "1-cmd2-a1").exists()
    records.validate_record("attempt", record)
    # The block the halt carried is the block the record keeps: the run it
    # measured before the survivors were found, exit 0 and all, dispatched
    # with the engine's own argv ending in this attempt's prompt.
    assert record["engine_run"]["launch"] == "started"
    assert record["engine_run"]["argv"][0] == sys.executable
    assert record["engine_run"]["argv"][-1] == str(where / "prompt.txt")
    assert record["engine_run"]["exit"] == 0
    assert record["engine_run"]["identity"] == FAKE_IDENTITY
    assert record["engine_run"]["completion"] == "complete"
    # Nothing ran after the halt: the gates were never reached.
    assert all(gate is None for gate in record["gates"].values())
    # A valid run whose evidence was never observed is SUSPECT, not discarded.
    assert record["outcome"] == "SUSPECT"
    assert record["outcome"] in OUTCOMES
    assert records.classify(record) == (record["outcome"], record["class"])
    assert run_eval_harness.main(["verify", str(root)]) == 0


# -- dispatch: not-started is a refusal before creation only -----------------


def test_runner_raises_launch_error_for_a_child_the_host_would_not_create(tmp_path):
    # The binary is not there, so no process was ever created: that is the one
    # failure the runner names as a launch error, chained to the host's own
    # refusal, and it leaves no capture file where the child's output would
    # have gone.
    log = tmp_path / "log.txt"

    with pytest.raises(runner.LaunchError) as caught:
        runner.run_bounded([str(tmp_path / "no-such-engine")], tmp_path, 5.0, stdout_path=log)

    assert isinstance(caught.value, RuntimeError)
    assert isinstance(caught.value.__cause__, OSError)
    assert not log.exists()


def test_runner_names_a_launch_error_for_a_file_the_host_will_not_execute(tmp_path):
    # The file is there but is no program: the host still refuses to create
    # the child, with a different errno than a missing file. Whatever the host
    # says, a refusal at creation is the launch error, so a runner that names
    # only the missing-file refusal leaves this one to read as started.
    not_a_program = tmp_path / "engine.txt"
    not_a_program.write_text("not a program\n", encoding="utf-8")
    log = tmp_path / "log.txt"

    with pytest.raises(runner.LaunchError) as caught:
        runner.run_bounded([str(not_a_program)], tmp_path, 5.0, stdout_path=log)

    assert isinstance(caught.value.__cause__, OSError)
    assert not log.exists()


def test_runner_names_a_launch_error_when_the_capture_cannot_be_opened(tmp_path):
    # The capture is opened before the child is created, so a capture the host
    # will not open is a failure from before there was a process, too: the
    # launch never started, and it must not read as a started run that lost
    # its output.
    log = tmp_path / "no-such-dir" / "log.txt"

    with pytest.raises(runner.LaunchError) as caught:
        runner.run_bounded([sys.executable, "-c", "print('ran')"], tmp_path, 5.0,
                           stdout_path=log)

    assert isinstance(caught.value.__cause__, OSError)
    assert not log.exists()


def test_runner_lets_a_failure_after_the_child_ran_out_as_itself(tmp_path, monkeypatch):
    # The child was created and ran to its exit; what failed came after, in the
    # reap. That is not the launch's failure and must not wear its name, and
    # the capture the child wrote is evidence a runner may not delete on the
    # way out.
    def fail_in_the_reap(tree, **kwargs):
        raise _post_launch_error(PermissionError)

    monkeypatch.setattr(runner, "reap", fail_in_the_reap)
    log = tmp_path / "log.txt"

    with pytest.raises(OSError) as caught:
        runner.run_bounded([sys.executable, "-c", "print('ran')"], tmp_path, 5.0,
                           stdout_path=log)

    assert not isinstance(caught.value, runner.LaunchError)
    assert POST_LAUNCH_MESSAGE in str(caught.value)
    assert log.read_text(encoding="utf-8").splitlines() == ["ran"]


def test_dispatch_reads_not_started_off_the_runner_not_off_the_disk(tmp_path, monkeypatch):
    # The interpreter argv[0] names is right there on disk, and the runner
    # still says the child was never created: the runner's word is the whole
    # signal. A dispatch that probes the disk instead calls this started.
    def refuse_to_create(*args, **kwargs):
        raise runner.LaunchError("the host would not create the child")

    monkeypatch.setattr(engines, "run_bounded", refuse_to_create)
    argv = _dispatched_argv(tmp_path)

    result = _dispatch_cmd(tmp_path, monkeypatch, eval_harness_fixtures.fake_engine_command("pass"))
    run = result["run"]

    records.validate_record("engine_run", run)
    assert Path(argv[0]).exists()
    assert run["launch"] == "not-started"
    assert run["argv"] == argv
    assert run["final_message_bytes"] is None
    assert not (result["attempt"] / "out.txt").exists()


@pytest.mark.parametrize("error", [PermissionError, FileNotFoundError, OSError],
                         ids=["permission-denied", "file-not-found", "plain-oserror"])
def test_records_a_started_run_when_the_runner_fails_after_creating_the_child(
        tmp_path, monkeypatch, error):
    # The runner raised an OSError of the very kind a refused launch raises,
    # wearing a refused launch's own errno and words, but not from the launch:
    # a classifier keyed on the exception's kind or on its message would call
    # this not-started and let the harness retry a run that happened. The
    # block says it started, measured nothing, and the failure is written down
    # where the attempt keeps its progress.
    def fail_after_launch(*args, **kwargs):
        raise _post_launch_error(error)

    monkeypatch.setattr(engines, "run_bounded", fail_after_launch)
    argv = _dispatched_argv(tmp_path)

    result = _dispatch_cmd(tmp_path, monkeypatch, eval_harness_fixtures.fake_engine_command("pass"))
    run = result["run"]

    records.validate_record("engine_run", run)
    assert run["launch"] == "started"
    assert run["argv"] == argv
    assert run["exit"] is None
    assert run["timed_out"] is False
    assert run["wall_s"] is None
    assert run["identity"] is None
    assert run["completion"] == "unknown"
    assert run["usage_limit"] == "unchecked"
    assert run["usage"] == dict.fromkeys(records.USAGE_KEYS)
    progress = (result["attempt"] / "progress.log").read_text(encoding="utf-8").splitlines()
    assert any(POST_LAUNCH_MESSAGE in line for line in progress)


def test_a_post_launch_read_failure_is_a_started_run_that_is_never_retried(
        tmp_path, vetted, shim, monkeypatch):
    # The child really ran before the runner lost its output, so the attempt
    # is final under harness-only retry: there is no a2, and its validity is
    # anything but the harness's own fault.
    root = _copy(vetted.root, tmp_path.resolve() / "bundle")
    run = root / "runs" / "late"
    _fail_after_the_child_ran(monkeypatch, PermissionError)

    rc = run_eval_harness.main(_run_argv(root, "late", [_engine(shim, "pass")], "description",
                                         "--retry-discarded", "harness-only"))

    record = _read_json(run / "1-cmd1-a1" / "attempt.json")
    assert rc == 0
    assert _marker(run / "complete.txt")[1] == ["1-cmd1-a1"]
    assert not (run / "1-cmd1-a2").exists()
    assert record["engine_run"]["launch"] == "started"
    assert record["validity"] != "DISCARDED:harness"


# -- dispatch: a containment refusal after creation --------------------------


def test_reraises_a_containment_refusal_with_the_created_run_observed(tmp_path, monkeypatch):
    # The child was created and then the host would not contain it: the halt
    # that follows carries a started block with the engine's own argv, so the
    # attempt written from it does not say the launch never happened.
    refusal = _refuse_containment(monkeypatch)
    argv = _dispatched_argv(tmp_path)

    with pytest.raises(runner.JobAssignmentError) as caught:
        _dispatch_cmd(tmp_path, monkeypatch, eval_harness_fixtures.fake_engine_command("pass"))

    assert caught.value is refusal
    assert caught.value.reason == "job_assignment_failed"
    observed = caught.value.observed
    records.validate_record("engine_run", observed)
    assert observed["launch"] == "started"
    assert observed["argv"] == argv
    assert observed["exit"] is None
    assert observed["timed_out"] is False
    assert observed["wall_s"] is None
    assert observed["identity"] is None
    assert observed["completion"] == "unknown"
    assert observed["final_message_bytes"] is None
    assert observed["usage_limit"] == "unchecked"
    assert observed["usage"] == dict.fromkeys(records.USAGE_KEYS)


def test_a_containment_refusal_after_creation_halts_with_a_started_run(
        tmp_path, vetted, shim, monkeypatch):
    root = _copy(vetted.root, tmp_path.resolve() / "bundle")
    run = root / "runs" / "jobs"
    _refuse_containment(monkeypatch)

    rc = _run_direct(root, "jobs", [_engine(shim, "pass"), _engine(shim, "noop")], "description")

    where = run / "1-cmd1-a1"
    record = _read_json(where / "attempt.json")
    headers, ids = _marker(run / "halted.txt")
    assert rc == 2
    assert headers == {
        "reason": "HALTED:job_assignment_failed", "attempt": "1-cmd1-a1", "command": "engine",
        "attempts": "1",
    }
    assert ids == ["1-cmd1-a1"]
    records.validate_record("attempt", record)
    assert record["engine_run"]["launch"] == "started"
    # The engine's own argv, whole: the shim in `pass` mode is dispatched
    # through the interpreter with this attempt's prompt, and nothing else.
    assert record["engine_run"]["argv"] == [sys.executable, str(shim), "pass",
                                            str(where / "prompt.txt")]
    assert record["validity"] != "DISCARDED:harness"
    assert records.classify(record) == (record["outcome"], record["class"])
    assert not (run / "1-cmd2-a1").exists()
    assert run_eval_harness.main(["verify", str(root)]) == 0


@pytest.mark.parametrize("halt", [runner.OrphanError, runner.JobAssignmentError],
                         ids=["orphans", "job-assignment"])
def test_a_halt_raised_outside_the_engine_dispatch_observed_nothing(halt):
    # Only the engine dispatch measured a block to attach; raised anywhere
    # else, the same exceptions carry none.
    assert halt("x").observed is None
