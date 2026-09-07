"""Tests for fixtures/fake_engine.py: its working-tree effects and protocol."""
import json
from pathlib import Path

import pytest

# The last four names are fixtures: pytest resolves them from this module's own
# namespace, so they have to be imported even though nothing here calls them.
from eval_harness_fixture_helpers import (
    COMPLETING_MODES,
    _assert_lines,
    _dirty,
    _git,
    _grew_within,
    _in_repo,
    _kill_process_group,
    _moments_in,
    _prompt_in,
    _rel,
    _run_engine,
    _run_fixture_tests,
    _start_engine,
    _stopped_growing,
    _strings_in,
    _task_impl,
    _terminal_event,
    _values_for,
    _written_impl,
    bare_ci,
    built_repo,
    pre_task_repo,
    protocol_runs,
)


# -- fake_engine: working-tree effects -------------------------------------


def test_pass_mode_turns_the_fixture_test_green_without_touching_the_oracle(
    pre_task_repo, tmp_path
):
    repo = Path(pre_task_repo["repo"])
    oracle = _in_repo(pre_task_repo, "test").read_text(encoding="utf-8")
    assert _run_fixture_tests(repo).returncode != 0, "the base tree was already green"

    done = _run_engine("pass", repo, tmp_path / "attempt", tmp_path / "beat.txt")

    assert done.returncode == 0
    # The impl the task commit itself carries, not any text that happens to
    # satisfy the oracle's current expected value.
    assert _written_impl(pre_task_repo) == _task_impl(pre_task_repo)
    assert _run_fixture_tests(repo).returncode == 0
    assert _in_repo(pre_task_repo, "test").read_text(encoding="utf-8") == oracle


def test_noop_mode_changes_nothing_and_exits_zero_with_a_final_message(
    pre_task_repo, tmp_path
):
    repo = Path(pre_task_repo["repo"])

    done = _run_engine("noop", repo, tmp_path / "attempt", tmp_path / "beat.txt")

    assert done.returncode == 0
    assert done.stdout.strip(), "noop still owes a final message"
    assert _dirty(repo) == []
    assert _run_fixture_tests(repo).returncode != 0


def test_stray_mode_writes_the_impl_and_a_file_outside_the_writable_set(
    pre_task_repo, tmp_path
):
    repo = Path(pre_task_repo["repo"])

    done = _run_engine("stray", repo, tmp_path / "attempt", tmp_path / "beat.txt")

    assert done.returncode == 0
    touched = _dirty(repo)
    impl = _rel(pre_task_repo, "impl")
    assert impl in touched
    assert [path for path in touched if path != impl], "stray wrote nothing stray"
    assert _written_impl(pre_task_repo) == _task_impl(pre_task_repo)
    assert _run_fixture_tests(repo).returncode == 0


def test_drop_mode_leaves_the_load_bearing_impl_untouched(pre_task_repo, tmp_path):
    repo = Path(pre_task_repo["repo"])
    before = _in_repo(pre_task_repo, "impl").read_text(encoding="utf-8")

    done = _run_engine("drop", repo, tmp_path / "attempt", tmp_path / "beat.txt")

    assert done.returncode == 0
    # It works, it just skips the one path that carries the fix: an engine that
    # writes nothing at all is a noop, not a drop.
    touched = _dirty(repo)
    assert touched, "drop wrote nothing at all"
    assert _rel(pre_task_repo, "impl") not in touched
    assert _in_repo(pre_task_repo, "impl").read_text(encoding="utf-8") == before
    assert _run_fixture_tests(repo).returncode != 0


def test_mutate_test_mode_rewrites_the_oracle_so_its_own_run_is_green(
    pre_task_repo, tmp_path
):
    repo = Path(pre_task_repo["repo"])
    before = _in_repo(pre_task_repo, "test").read_text(encoding="utf-8")

    done = _run_engine("mutate-test", repo, tmp_path / "attempt", tmp_path / "beat.txt")

    assert done.returncode == 0
    assert _in_repo(pre_task_repo, "test").read_text(encoding="utf-8") != before
    assert _run_fixture_tests(repo).returncode == 0


def test_vacuous_mode_rewrites_the_oracle_so_it_asserts_nothing(pre_task_repo, tmp_path):
    repo = Path(pre_task_repo["repo"])
    before = _in_repo(pre_task_repo, "test").read_text(encoding="utf-8")

    done = _run_engine("vacuous", repo, tmp_path / "attempt", tmp_path / "beat.txt")

    assert done.returncode == 0
    rewritten = _in_repo(pre_task_repo, "test").read_text(encoding="utf-8")
    assert rewritten != before
    assert not _assert_lines(rewritten), rewritten
    # Green even once the broken base impl is put back: it tests nothing at all.
    _git(repo, "checkout", "--", _rel(pre_task_repo, "impl"))
    assert _run_fixture_tests(repo).returncode == 0


def test_exit1_mode_edits_nothing_and_exits_one(pre_task_repo, tmp_path):
    repo = Path(pre_task_repo["repo"])

    done = _run_engine("exit1", repo, tmp_path / "attempt", tmp_path / "beat.txt")

    assert done.returncode == 1
    assert _dirty(repo) == []


def test_silent_edit_mode_fixes_the_impl_with_no_identity_and_no_final_message(
    pre_task_repo, tmp_path
):
    repo = Path(pre_task_repo["repo"])
    attempt = tmp_path / "attempt"

    done = _run_engine("silent-edit", repo, attempt, tmp_path / "beat.txt")

    assert done.returncode == 0
    assert done.stdout.strip() == ""
    assert "Using engine" not in done.stderr
    assert _written_impl(pre_task_repo) == _task_impl(pre_task_repo)
    assert _run_fixture_tests(repo).returncode == 0
    # The transcript is the only place the truncation shows.
    assert set(_values_for(_terminal_event(attempt), "stop_reason")) == {"length"}


# -- fake_engine: the child that outlives its parent -----------------------


def test_hang_mode_keeps_its_child_beating_until_the_process_group_is_killed(
    pre_task_repo, tmp_path
):
    repo = Path(pre_task_repo["repo"])
    # Not "beat.txt", not beside the attempt directory: the only way this file
    # can grow is the engine reading FAKE_ENGINE_HEARTBEAT.
    heartbeat = tmp_path / "beats" / "hb.log"
    heartbeat.parent.mkdir(parents=True)
    engine = _start_engine("hang", repo, tmp_path / "attempt", heartbeat)
    try:
        assert _grew_within(heartbeat, 20.0), "the heartbeat child never started"
        assert engine.poll() is None, "hang exited instead of sleeping past the bound"

        engine.kill()  # the parent alone
        engine.wait(timeout=30)

        assert _grew_within(heartbeat, 5.0), "the child died with its parent"
    finally:
        _kill_process_group(engine.pid)

    assert _stopped_growing(heartbeat), "the child survived the process-group kill"


def test_spawn_and_exit_mode_returns_at_once_and_leaves_its_child_beating(
    pre_task_repo, tmp_path
):
    repo = Path(pre_task_repo["repo"])
    attempt = tmp_path / "attempt"
    heartbeat = tmp_path / "beat.txt"
    engine = _start_engine("spawn-and-exit", repo, attempt, heartbeat)
    try:
        assert engine.wait(timeout=30) == 0
        # The child is still writing after its parent has been reaped.
        assert _grew_within(heartbeat, 10.0)
        assert _written_impl(pre_task_repo) == _task_impl(pre_task_repo)
        assert _run_fixture_tests(repo).returncode == 0
        assert "Using engine 'cmd:spawn-and-exit'" in (attempt / "err.txt").read_text(
            encoding="utf-8"
        )
        assert (attempt / "out.txt").read_text(encoding="utf-8").strip()
    finally:
        _kill_process_group(engine.pid)


# -- fake_engine: the observable protocol ----------------------------------


@pytest.mark.parametrize("mode", COMPLETING_MODES)
def test_reads_the_prompt_file_it_is_handed(pre_task_repo, tmp_path, mode):
    # Every mode is handed a prompt, so every mode has to open it: one mode that
    # reads the file cannot answer for the modes that ignore theirs.
    repo = Path(pre_task_repo["repo"])
    attempt = tmp_path / mode / "attempt"
    marker = f"prompt-echo-4f2c9a-{mode}"
    prompt = _prompt_in(tmp_path / mode / "prompts", f"fix the failing test [{marker}]\n")

    done = _run_engine(mode, repo, attempt, tmp_path / mode / "beat.txt", prompt)

    assert done.returncode == (1 if mode == "exit1" else 0), done.stderr
    # The marker exists only inside the file's text, never in its name or path,
    # so it can only reach the report by being read.
    reported = done.stdout + (attempt / "session.jsonl").read_text(encoding="utf-8")
    assert marker in reported, reported


@pytest.mark.parametrize("mode", COMPLETING_MODES)
def test_writes_the_engine_identity_to_stderr(protocol_runs, mode):
    runs, _ = protocol_runs
    done, _attempt = runs[mode]

    assert f"Using engine 'cmd:{mode}'" in done.stderr
    assert "Using engine" not in done.stdout


@pytest.mark.parametrize("mode", COMPLETING_MODES)
def test_writes_its_final_message_to_stdout(protocol_runs, mode):
    runs, _ = protocol_runs
    done, _attempt = runs[mode]

    message = done.stdout.strip()
    assert message
    # One sentence cannot honestly report both a fix and a mode that edited
    # nothing, so no two modes may share a final message.
    twins = [
        other
        for other in COMPLETING_MODES
        if other != mode and runs[other][0].stdout.strip() == message
    ]
    assert not twins, f"{mode} says what {twins} say: {message!r}"


@pytest.mark.parametrize("mode", COMPLETING_MODES)
def test_writes_one_terminal_end_turn_session_event(protocol_runs, mode):
    runs, (started, ended) = protocol_runs
    done, attempt = runs[mode]

    event = _terminal_event(attempt)

    assert "assistant" in json.dumps(event)
    assert set(_values_for(event, "stop_reason")) == {"end_turn"}
    assert [usage for usage in _values_for(event, "usage") if isinstance(usage, dict)]
    # A stamp from the run, not a frozen literal: it lands inside the window the
    # runs were made in, give or take a couple of seconds of clock slack.
    moments = _moments_in(event)
    assert any(started - 2 <= moment <= ended + 2 for moment in moments), (
        moments,
        started,
        ended,
    )
    assert done.stdout.strip() in {text.strip() for text in _strings_in(event)}
