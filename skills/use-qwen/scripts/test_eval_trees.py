"""Tests for eval_harness/runner.py: bounded trees, reaping, the gate lock."""
import multiprocessing
import os
import shlex
import signal
import sys
import time
from pathlib import Path

import pytest

import eval_harness_fixtures
from eval_harness import records
from eval_harness import runner

# The last three names are fixtures: pytest resolves them from this module's own
# namespace, so they have to be imported even though nothing here calls them.
from eval_harness_fixture_helpers import (
    _engine_argv,
    _engine_env,
    _grew_within,
    _kill_process_group,
    _prompt_in,
    _start_engine,
    _stopped_growing,
    bare_ci,
    built_repo,
    pre_task_repo,
)

POSIX_ONLY = pytest.mark.skipif(
    os.name == "nt",
    reason="POSIX process groups and `bash -lc`; the Windows Job Object branch is a separate task",
)

# The marker file the contract names, relative to the run directory.
MARKER = ".gate-in-flight"

# One output line per marker the contract names, spelled the way a real run
# would print it.
TOOL_MARKERS = (
    "bash: pytest: command not found",
    "python: can't open file 'run.py': No such file or directory",
    "ModuleNotFoundError: No module named 'calc'",
    "ImportError: cannot import name 'add' from 'calc'",
    "ERROR collecting tests/test_calc.py",
    "INTERNALERROR> Traceback (most recent call last):",
    "error: could not compile `calc` due to 1 previous error",
    "'pytest' is not recognized as an internal or external command",
)
TEST_MARKERS = (
    "FAILED tests/test_calc.py::test_add",
    "E       AssertionError: 5 != -1",
    "    assert add(2, 3) == 5",
    "=== FAILURES ===",
    "test result: FAILED. 0 passed; 1 failed",
    "--- FAIL: TestAdd (0.00s)",
    "not ok 1 - adds two numbers",
)

# One run's output carrying both marker sets, in the two orders a real run
# prints them: pytest leads with the collection error, cargo reports the failing
# test before the compile error underneath it.
BOTH_MARKER_SETS = (
    "ERROR collecting tests/test_calc.py\n"
    "ModuleNotFoundError: No module named 'calc'\n"
    "FAILED tests/test_calc.py::test_add\n",
    "FAILED tests/test_calc.py::test_add\n"
    "test result: FAILED. 0 passed; 1 failed\n"
    "error: could not compile `calc` due to 1 previous error\n",
)

# Lines no case above spells out, from runs of other projects entirely. A
# lookup over the strings this suite hands out cannot answer for these.
HELD_OUT_LINES = (
    ("FAILED tests/test_other.py::test_mul", "test"),
    ("E       AssertionError: expected 6, got 9", "test"),
    ("        assert mul(2, 3) == 6", "test"),
    ("=========================== FAILURES ===========================", "test"),
    ("test result: FAILED. 12 passed; 3 failed; 0 ignored", "test"),
    ("--- FAIL: TestMultiply/negatives (0.01s)", "test"),
    ("not ok 4 - multiplies two numbers", "test"),
    ("bash: cargo: command not found", "tool"),
    ("cp: /tmp/widget.py: No such file or directory", "tool"),
    ("ModuleNotFoundError: No module named 'widget'", "tool"),
    ("ImportError: cannot import name 'mul' from 'widget'", "tool"),
    ("ERROR collecting tests/test_widget.py", "tool"),
    ("INTERNALERROR> AttributeError: 'Config' object has no attribute 'rootdir'", "tool"),
    ("error: could not find `Cargo.toml` in `/tmp/widget`", "tool"),
    ("'cargo' is not recognized as an internal or external command", "tool"),
    ("collected 12 items", "unknown"),
    ("warning: unused import: `std::io`", "unknown"),
)

# Two children that write down the signal they were sent, so a test can tell
# which stage of the kill reached them instead of inferring it from a clock.
# The first survives its SIGTERM, so the whole escalation window has to elapse
# before anything ends it; the second leaves the moment it arrives.
_RECORD_SIGNAL = (
    "import os, signal, sys, time\n"
    "def _record(signum, frame):\n"
    "    with open(sys.argv[1], 'a', encoding='utf-8') as seen:\n"
    "        seen.write(str(signum) + '\\n')\n"
)
_SLEEP_ON = "signal.signal(signal.SIGTERM, _record)\ntime.sleep(600)\n"
SURVIVES_SIGTERM = _RECORD_SIGNAL + _SLEEP_ON
DIES_ON_SIGTERM = _RECORD_SIGNAL + "    os._exit(0)\n" + _SLEEP_ON


def _q(value) -> str:
    """One shell word, whatever the path or payload carries."""
    return shlex.quote(str(value))


# -- classify_failure ------------------------------------------------------


@pytest.mark.parametrize("line", TOOL_MARKERS)
def test_classify_failure_reads_an_executable_or_collection_error_as_tool(line):
    assert runner.classify_failure(line) == "tool"


@pytest.mark.parametrize("line", TEST_MARKERS)
def test_classify_failure_reads_a_named_test_framework_failure_as_test(line):
    assert runner.classify_failure(line) == "test"


@pytest.mark.parametrize("text", BOTH_MARKER_SETS)
def test_classify_failure_reads_a_tool_error_as_tool_even_when_a_test_also_failed(text):
    # The same run carries both marker sets. Read as a test failure it would be
    # blamed on the engine's code; it is the harness's own environment. Which
    # marker the run happened to print first cannot decide that: pytest names
    # its collection error before the failures, cargo prints its failing test
    # before the compile error that caused it, and both are tool errors.
    assert runner.classify_failure(text) == "tool"


def test_classify_failure_reads_an_unmatched_diagnostic_as_unknown():
    assert runner.classify_failure("the runner gave up for reasons it did not print") == (
        "unknown"
    )


@pytest.mark.parametrize("line, kind", HELD_OUT_LINES)
def test_classify_failure_reads_a_line_by_its_marker_not_by_the_whole_line(line, kind):
    # A real run prints other projects' test ids, other missing modules, other
    # tools. Classification keys on the marker inside the line, so a line this
    # suite never handed the classifier is answered the same way.
    assert runner.classify_failure(line) == kind


# -- CommandResult ---------------------------------------------------------


def test_as_json_carries_exactly_the_keys_the_record_contract_accepts():
    result = runner.CommandResult(
        rc=1,
        timed_out=False,
        first_failure="FAILED tests/test_calc.py::test_add",
        failure_kind="test",
        wall_s=1.5,
    )

    data = result.as_json()

    assert set(data) == set(records.COMMAND_RESULT_KEYS)
    assert data == {
        "rc": 1,
        "timed_out": False,
        "first_failure": "FAILED tests/test_calc.py::test_add",
        "failure_kind": "test",
        "wall_s": 1.5,
    }
    # Raises RecordError unless the shape is one a stored record may carry.
    records.validate_record("command_result", data)


def test_as_json_carries_the_empty_fields_of_a_command_that_never_finished():
    # A second, differently shaped result: every field the case above filled in
    # is empty here, so a body that answers with one remembered dict is wrong
    # about all five. This is also the only shape that exercises the record
    # contract's None branches.
    result = runner.CommandResult(
        rc=None,
        timed_out=True,
        first_failure=None,
        failure_kind=None,
        wall_s=0.0,
    )

    data = result.as_json()

    assert data == {
        "rc": None,
        "timed_out": True,
        "first_failure": None,
        "failure_kind": None,
        "wall_s": 0.0,
    }
    records.validate_record("command_result", data)


def test_an_unrun_command_is_represented_as_none():
    # Nothing to run is not a zero exit: the record contract distinguishes a
    # command that never ran from one that passed.
    assert runner.run_segments([], Path.cwd(), 30.0) is None


# -- run_segments ----------------------------------------------------------


@POSIX_ONLY
def test_run_segments_stops_at_the_first_non_zero_segment_and_returns_its_result(tmp_path):
    first, second, third = (tmp_path / name for name in ("first", "second", "third"))
    segments = [
        f"printf 'ran' > {_q(first)}",
        f"printf 'ran' > {_q(second)}; exit 7",
        f"printf 'ran' > {_q(third)}",
    ]

    result = runner.run_segments(segments, tmp_path, 30.0)

    assert result.rc == 7
    assert result.timed_out is False
    assert first.exists() and second.exists()
    assert not third.exists(), "the list kept running past its first failing segment"


@POSIX_ONLY
def test_run_segments_runs_every_segment_in_the_directory_it_was_given(tmp_path):
    # A gate runs inside a per-attempt clone, so where the segments stand is the
    # whole point of the `cwd` argument. Nothing else here would notice a runner
    # that ignores it: every other segment names absolute paths or cds itself.
    where = tmp_path / "attempt-clone"
    where.mkdir()

    result = runner.run_segments(["printf 'ran' > here.txt", "pwd > where.txt"], where, 30.0)

    assert result.rc == 0
    assert (where / "here.txt").read_text(encoding="utf-8") == "ran"
    # The second segment answers for itself, so a runner that honours `cwd` for
    # the first one only is caught too.
    stood_in = Path((where / "where.txt").read_text(encoding="utf-8").strip())
    assert stood_in.resolve() == where.resolve()


@POSIX_ONLY
def test_run_segments_reports_how_long_the_segments_actually_took(tmp_path):
    # One second of work under a thirty-second deadline. `wall_s` has to carry
    # the work's own duration: the floor rules out a constant zero, and the
    # ceiling rules out the deadline the segment ran under, which is the other
    # number close at hand.
    result = runner.run_segments(["sleep 1"], tmp_path, 30.0)

    assert result.rc == 0
    assert result.wall_s is not None
    assert 1.0 <= result.wall_s < 5.0, result.wall_s


@POSIX_ONLY
def test_run_segments_bounds_the_whole_list_with_one_deadline(tmp_path):
    started = time.monotonic()

    result = runner.run_segments(["sleep 1", "sleep 1"], tmp_path, 1.5)

    elapsed = time.monotonic() - started
    # A fresh 1.5 s bound per segment would let both sleeps finish, in about
    # two seconds, and report no timeout at all.
    assert result.timed_out is True
    assert elapsed < 3.0, elapsed


@POSIX_ONLY
def test_run_segments_hands_each_segment_to_bash_as_a_single_argument(tmp_path):
    written = tmp_path / "written.txt"
    victim = tmp_path / "victim"
    victim.mkdir()
    # Text that would delete a directory and split into words if the parent's
    # shell ever saw it unquoted. Only the child bash may undo the quoting.
    payload = f"a b ; rm -rf {victim} ; echo $HOME | wc -l & done"
    segment = f"printf '%s' {shlex.quote(payload)} > {_q(written)}"

    result = runner.run_segments([segment], tmp_path, 30.0)

    assert result.rc == 0
    # Split on whitespace, or spliced into the parent's command line, the
    # payload never lands here whole.
    assert written.read_text(encoding="utf-8") == payload
    assert victim.is_dir(), "the parent's shell acted on the segment's text"


@POSIX_ONLY
def test_run_segments_reports_the_first_marked_line_as_the_first_failure(tmp_path):
    segment = (
        "printf '%s\\n' 'collected 3 items' "
        "'FAILED tests/test_calc.py::test_add - AssertionError: 5 != -1' "
        "'FAILED tests/test_calc.py::test_sub'; exit 1"
    )

    result = runner.run_segments([segment], tmp_path, 30.0)

    assert result.rc == 1
    assert result.failure_kind == "test"
    assert result.first_failure.strip() == (
        "FAILED tests/test_calc.py::test_add - AssertionError: 5 != -1"
    )


def _unmatched_output(tmp_path, lines) -> "runner.CommandResult":
    """One failing command that prints `lines`, none of them carrying a marker.

    A direct argv, not a `bash -lc` segment: the runner captures stderr as well
    as stdout, and a login shell sources a profile that writes to stderr on some
    machines. Those lines would land inside the forty-line window these cases
    measure and move the answer, which is a fact about the machine and not about
    the fallback.
    """
    payload = tmp_path / "payload.txt"
    payload.write_text("\n".join(lines), encoding="utf-8")
    script = tmp_path / "print_payload.py"
    script.write_text(
        "import sys\n"
        "sys.stdout.write(open(sys.argv[1], encoding='utf-8').read())\n"
        "sys.exit(2)\n",
        encoding="utf-8",
    )

    result, tree = runner.run_bounded(
        [sys.executable, str(script), str(payload)],
        tmp_path,
        30.0,
        escalate_after_s=0.25,
        settle_s=0.5,
    )

    assert tree.survivors() is False
    return result


@POSIX_ONLY
def test_the_first_failure_falls_back_to_the_first_non_blank_line_of_the_last_forty(tmp_path):
    # Fifty lines, no marker anywhere. The last forty start at line 11, which
    # is blank, so the fallback skips it and takes line 12 - and never reaches
    # back to line 1, which is where a whole-output scan would land.
    lines = [f"noise line {number:02d}" for number in range(1, 51)]
    lines[10] = ""
    lines[11] = "the tail line"

    result = _unmatched_output(tmp_path, lines)

    assert result.rc == 2
    assert result.failure_kind == "unknown"
    assert result.first_failure.strip() == "the tail line"


@POSIX_ONLY
def test_the_fallback_window_opens_forty_lines_from_the_end(tmp_path):
    # The same fifty lines with nothing blank in them: line 11 is the answer
    # only if the window opens exactly forty lines from the end. A window one
    # line off names line 10 or line 12 instead.
    lines = [f"noise line {number:02d}" for number in range(1, 51)]

    result = _unmatched_output(tmp_path, lines)

    assert result.failure_kind == "unknown"
    assert result.first_failure.strip() == "noise line 11"


@POSIX_ONLY
def test_the_fallback_takes_the_whole_output_when_it_is_shorter_than_forty_lines(tmp_path):
    # Twelve lines: the last forty are all of them. The first is blank, so the
    # answer is the second - and there is no fortieth line to count back to.
    lines = ["", "the only line that says anything"] + [
        f"noise line {number:02d}" for number in range(3, 13)
    ]

    result = _unmatched_output(tmp_path, lines)

    assert result.failure_kind == "unknown"
    assert result.first_failure.strip() == "the only line that says anything"


# -- run_bounded: the bound and the two-stage kill -------------------------


@POSIX_ONLY
def test_the_group_kill_is_what_stops_the_heartbeat_a_parent_only_kill_does_not(tmp_path):
    loose = tmp_path / "loose" / "hb.log"
    loose.parent.mkdir(parents=True)
    engine = _start_engine("hang", tmp_path, tmp_path / "loose-attempt", loose)
    try:
        assert _grew_within(loose, 20.0), "the heartbeat child never started"

        engine.kill()  # the direct child alone, SIGKILL
        engine.wait(timeout=30)

        assert _grew_within(loose, 5.0), "the child died with its parent after all"
    finally:
        _kill_process_group(engine.pid)

    bounded = tmp_path / "bounded" / "hb.log"
    bounded.parent.mkdir(parents=True)

    result, tree = runner.run_bounded(
        _engine_argv("hang", _prompt_in(tmp_path / "bounded-prompt")),
        tmp_path,
        1.5,
        env=_engine_env("hang", tmp_path / "bounded-attempt", bounded),
        escalate_after_s=0.25,
        settle_s=1.0,
    )

    # Same fixture, same beating grandchild: what the parent-only kill above
    # could not stop, the bound's group kill does.
    assert result.timed_out is True
    assert bounded.stat().st_size > 0, "the heartbeat child never started under the bound"
    assert _stopped_growing(bounded), "the group kill never reached the grandchild"
    assert tree.survivors() is False


def _bound_a_recording_child(tmp_path, source, escalate_after_s=1.0) -> tuple:
    """Bound a child that writes down each signal it is sent, and time it."""
    script = tmp_path / "child.py"
    script.write_text(source, encoding="utf-8")
    signals = tmp_path / "signals.txt"
    started = time.monotonic()

    result, tree = runner.run_bounded(
        [sys.executable, str(script), str(signals)],
        tmp_path,
        1.5,
        escalate_after_s=escalate_after_s,
        settle_s=1.0,
    )

    return result, tree, signals, time.monotonic() - started


def _signals_seen(signals: Path) -> list:
    """The signal numbers the child recorded, in the order it caught them."""
    if not signals.exists():
        return []
    return [int(line) for line in signals.read_text(encoding="utf-8").split()]


@POSIX_ONLY
def test_a_sigterm_ignoring_child_is_killed_only_after_the_escalation_window(tmp_path):
    result, tree, signals, elapsed = _bound_a_recording_child(tmp_path, SURVIVES_SIGTERM)

    assert result.timed_out is True
    # Stage one reached the child and it wrote the proof down: a kill that
    # jumps straight to SIGKILL leaves this file empty, whatever the clock says.
    assert int(signal.SIGTERM) in _signals_seen(signals), _signals_seen(signals)
    # This child survives that signal, so the whole escalation window elapses
    # before the SIGKILL that ends it. A single-stage kill returns at the
    # bound, near 1.5 s, and never reaches here.
    assert elapsed >= 2.4, elapsed
    assert elapsed < 10.0, elapsed
    assert tree.survivors() is False


@POSIX_ONLY
def test_the_escalation_window_is_the_one_the_caller_asked_for(tmp_path):
    # The same SIGTERM-surviving child, escalated four times sooner. The case
    # above waits out a one-second window; this one has to come back well before
    # that, so the wait between the two stages is the caller's parameter rather
    # than a constant that happens to satisfy the default.
    quick = tmp_path / "quick"
    quick.mkdir()

    result, tree, signals, elapsed = _bound_a_recording_child(
        quick, SURVIVES_SIGTERM, escalate_after_s=0.25
    )

    assert result.timed_out is True
    assert int(signal.SIGTERM) in _signals_seen(signals), _signals_seen(signals)
    assert elapsed < 2.4, elapsed
    assert tree.survivors() is False


@POSIX_ONLY
def test_a_child_that_dies_on_sigterm_is_not_held_for_the_escalation_window(tmp_path):
    result, tree, signals, elapsed = _bound_a_recording_child(tmp_path, DIES_ON_SIGTERM)

    assert result.timed_out is True
    # This child leaves on the signal it records, and it recorded SIGTERM: the
    # first stage is what ended it, not the SIGKILL behind it.
    assert _signals_seen(signals) == [int(signal.SIGTERM)]
    # The escalation window is a deadline for a stubborn child, not a sleep
    # every bounded command pays.
    assert elapsed < 2.4, elapsed
    assert tree.survivors() is False


@POSIX_ONLY
def test_run_bounded_leaves_both_of_the_command_s_streams_at_the_path_it_was_given(tmp_path):
    log = tmp_path / "engine-out.txt"
    # `bash: pytest: command not found` is a tool marker the contract names, and
    # a shell writes it to stderr. A runner that keeps only stdout is blind to
    # the exact failure class it exists to name, so both streams have to reach
    # the log and both have to be read when the failure is classified.
    talker = (
        "import sys\n"
        "print('collected 12 items')\n"
        "print('bash: pytest: command not found', file=sys.stderr)\n"
        "sys.exit(3)\n"
    )

    result, tree = runner.run_bounded(
        [sys.executable, "-c", talker],
        tmp_path,
        30.0,
        stdout_path=log,
        escalate_after_s=0.25,
        settle_s=0.5,
    )

    written = log.read_text(encoding="utf-8")
    assert result.rc == 3
    assert result.timed_out is False
    assert "collected 12 items" in written
    assert "bash: pytest: command not found" in written, "stderr never reached the log"
    assert result.failure_kind == "tool"
    assert result.first_failure.strip() == "bash: pytest: command not found"
    # A command that took well under a second cannot report the bound it ran
    # under: this one is the far side of the hang fixture's `wall_s >= 1.9`
    # in test_eval_tree_containment.py.
    assert result.wall_s is not None and result.wall_s < 5.0, result.wall_s
    assert tree.survivors() is False


# -- reaping after a clean exit --------------------------------------------


@POSIX_ONLY
def test_survivors_answers_for_the_group_and_the_reap_empties_it(pre_task_repo, tmp_path):
    repo = Path(pre_task_repo["repo"])
    impl = repo / pre_task_repo["impl"]
    attempt = tmp_path / "attempt"
    attempt.mkdir(parents=True)
    heartbeat = tmp_path / "beats" / "hb.log"
    heartbeat.parent.mkdir(parents=True)

    result, tree = runner.run_bounded(
        _engine_argv("spawn-and-exit", _prompt_in(attempt)),
        repo,
        30.0,
        env=_engine_env("spawn-and-exit", attempt, heartbeat),
        escalate_after_s=0.25,
        settle_s=0.5,
    )

    assert result.rc == 0
    assert result.timed_out is False
    # The engine writes the impl file relative to wherever it is standing, and
    # this repo is checked out at the commit that still carries the broken one.
    # So the file answers the `cwd` question: a command run in the harness's own
    # directory instead of the attempt's clone never touches it.
    assert impl.read_text(encoding="utf-8") == eval_harness_fixtures.FIXED_IMPL
    # The engine exited and its background child did not, so the handle has a
    # real question to answer here. Whatever it answers, the heartbeat - the
    # group's own witness, written by a process the handle never consulted -
    # has to agree with it.
    assert tree.survivors() is _grew_within(heartbeat, 2.0)
    assert runner.reap(tree, escalate_after_s=0.25, settle_s=0.5) is True
    assert tree.survivors() is False
    assert _stopped_growing(heartbeat, 1.0), "the reap left the group beating"


@POSIX_ONLY
def test_a_clean_exit_that_leaves_a_background_child_gets_that_child_reaped(
    built_repo, tmp_path
):
    repo = Path(built_repo["repo"])
    attempt = tmp_path / "attempt"
    attempt.mkdir(parents=True)
    heartbeat = tmp_path / "beats" / "hb.log"
    heartbeat.parent.mkdir(parents=True)
    engine = " ".join(_q(part) for part in _engine_argv("spawn-and-exit", _prompt_in(attempt)))
    # The trailing sleep belongs to the engine's own parent, so the background
    # child has written before the command returns; the `cd` keeps the engine
    # in the fixture repo whatever a login profile does.
    segment = f"cd {_q(repo)} && {engine} && sleep 1"

    result = runner.run_segments(
        [segment],
        repo,
        60.0,
        env=_engine_env("spawn-and-exit", attempt, heartbeat),
    )

    # No OrphanError: a leftover child that the reap kills cleanly is not an
    # orphan halt, and the command's own result stands.
    assert result.rc == 0
    assert result.timed_out is False
    assert heartbeat.stat().st_size > 0, "the background child never started"
    assert _stopped_growing(heartbeat), "the leftover child outlived its command"


# -- gate_lock -------------------------------------------------------------

# The race below. Eight workers is enough that a lock which looks before it
# writes loses reliably, and few enough that eight interpreters still start
# inside the suite's budget. The winner holds the gate while the others are
# inside their own attempt, so a second worker taking it means the lock let it
# in and not that the first had already finished. Both waits are bounded: a
# wedged worker fails the case instead of hanging the suite.
GATE_WORKERS = 8
GATE_HOLD_S = 0.5
GATE_BARRIER_S = 20.0
GATE_JOIN_S = 30.0


def _race_for_the_gate(run_dir: str, outcome: str, label: str, barrier) -> None:
    """One worker: line up with the others, then try to take the gate."""
    verdict = "broke: the worker never reported"
    try:
        barrier.wait()
        with runner.gate_lock(Path(run_dir), label):
            time.sleep(GATE_HOLD_S)
        verdict = "took-the-gate"
    except runner.GateConcurrencyError:
        verdict = "refused"
    except Exception as blew_up:
        verdict = f"broke: {blew_up!r}"
    finally:
        # The parent reads these files and nothing else, so one lands whatever
        # happens here - a worker that dies silently is a wedged test otherwise.
        Path(outcome).write_text(verdict, encoding="utf-8")


def test_only_one_of_several_processes_racing_for_the_gate_takes_it(tmp_path):
    # "Gates run one at a time" is a guarantee between processes, so the case
    # has to be one. Every other gate case here is sequential and single
    # process, which a lock that checks for the marker and then writes it
    # satisfies completely - while two real gates, seeing no marker in the same
    # instant, both walk through it.
    context = multiprocessing.get_context("spawn")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    outcomes = tmp_path / "outcomes"
    outcomes.mkdir()
    barrier = context.Barrier(GATE_WORKERS, timeout=GATE_BARRIER_S)
    workers = [
        context.Process(
            target=_race_for_the_gate,
            args=(str(run_dir), str(outcomes / f"{index}.txt"), f"gate-{index}", barrier),
        )
        for index in range(GATE_WORKERS)
    ]

    for worker in workers:
        worker.start()
    try:
        for worker in workers:
            worker.join(timeout=GATE_JOIN_S)
    finally:
        for worker in workers:
            if worker.is_alive():
                worker.kill()

    verdicts = sorted(path.read_text(encoding="utf-8") for path in outcomes.iterdir())
    assert len(verdicts) == GATE_WORKERS, verdicts
    assert verdicts.count("took-the-gate") == 1, verdicts
    assert verdicts.count("refused") == GATE_WORKERS - 1, verdicts
    assert not (run_dir / MARKER).exists(), "the gate that won kept its marker"


def test_gate_lock_refuses_a_second_gate_and_names_the_one_in_flight(tmp_path):
    with runner.gate_lock(tmp_path, "ablate"):
        marker = tmp_path / MARKER
        assert "ablate" in marker.read_text(encoding="utf-8")

        with pytest.raises(runner.GateConcurrencyError) as refused:
            with runner.gate_lock(tmp_path, "baseline"):
                pytest.fail("a second gate ran while the first was in flight")

        # The gate in flight is the one the message has to name, not whichever
        # label the harness happens to run first.
        assert "ablate" in str(refused.value)
        assert marker.exists(), "the refused gate removed a marker it never took"

    assert not (tmp_path / MARKER).exists(), "the gate kept its marker after finishing"


def test_gate_lock_refuses_a_gate_whose_marker_another_process_left(tmp_path):
    # Nothing holds a gate in this interpreter: the only evidence is the file,
    # which is where the guarantee has to live for a second process to see it.
    marker = tmp_path / MARKER
    marker.write_text("ablate\n", encoding="utf-8")

    with pytest.raises(runner.GateConcurrencyError) as refused:
        with runner.gate_lock(tmp_path, "gate"):
            pytest.fail("a gate ran while another process held the marker")

    assert "ablate" in str(refused.value)
    assert marker.read_text(encoding="utf-8") == "ablate\n", (
        "the refused gate wrote over a marker it never took"
    )


def test_gate_lock_releases_its_marker_when_the_gate_s_own_work_raises(tmp_path):
    with pytest.raises(RuntimeError):
        with runner.gate_lock(tmp_path, "gate"):
            raise RuntimeError("the command inside the gate blew up")

    assert not (tmp_path / MARKER).exists(), "a failed gate held its lock forever"
    # And the next gate is not locked out by the one that failed.
    with runner.gate_lock(tmp_path, "own"):
        assert "own" in (tmp_path / MARKER).read_text(encoding="utf-8")


@POSIX_ONLY
def test_a_command_inside_a_gate_can_read_the_marker_and_the_gate_releases_it_after(
    tmp_path,
):
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    seen = tmp_path / "seen.txt"

    with runner.gate_lock(run_dir, "baseline"):
        result = runner.run_segments(
            [f"cat {_q(run_dir / MARKER)} > {_q(seen)}"], tmp_path, 30.0
        )

    assert result.rc == 0
    assert "baseline" in seen.read_text(encoding="utf-8")
    assert not (run_dir / MARKER).exists()
