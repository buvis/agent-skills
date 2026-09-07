"""Tests for eval_harness_fixtures.py: the repo builder, the stub, the command."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import eval_harness_fixtures

# The last three names are fixtures: pytest resolves them from this module's own
# namespace, so they have to be imported even though nothing here calls them.
from eval_harness_fixture_helpers import (
    MODES,
    _assert_lines,
    _dirty,
    _git,
    _in_repo,
    _neutralise_git_env,
    _rel,
    _resolve,
    _run_engine,
    _run_fixture_tests,
    _script_path,
    _show,
    _task_impl,
    _written_impl,
    bare_ci,
    built_repo,
    pre_task_repo,
)


# -- build_fixture_repo ----------------------------------------------------


def test_builds_two_commits_on_a_named_branch_with_no_ambient_git_config(
    tmp_path, monkeypatch, isolate_home
):
    # No global config, no system config, no identity variables and a home that
    # holds nothing: only the builder's own -c flags can name an author here.
    _neutralise_git_env(monkeypatch, tmp_path)
    isolate_home(tmp_path / "home")
    root = tmp_path / "fixture"
    root.mkdir()

    info = eval_harness_fixtures.build_fixture_repo(root)

    assert set(info) == {"repo", "first", "last", "impl", "test"}
    repo = Path(info["repo"])
    assert (repo / ".git").exists()
    assert repo == root
    assert _git(repo, "rev-parse", "--abbrev-ref", "HEAD") == "main"
    assert _git(repo, "log", "-1", "--format=%an") == "eval-harness"
    assert _git(repo, "log", "-1", "--format=%ae") == "eval-harness@local"
    history = _git(repo, "rev-list", "--reverse", "HEAD").split()
    assert len(history) == 2
    assert [_resolve(repo, info["first"]), _resolve(repo, info["last"])] == history
    # Commit ids, not refs. `main~1` resolves to the same commit today and to a
    # different one the moment anybody commits, which silently moves both
    # handles under a caller that only ever holds this dict.
    assert re.fullmatch(r"[0-9a-f]{40}", str(info["first"])), info["first"]
    assert re.fullmatch(r"[0-9a-f]{40}", str(info["last"])), info["last"]
    assert _in_repo(info, "impl").is_file()
    assert _in_repo(info, "test").is_file()
    assert _in_repo(info, "impl") != _in_repo(info, "test")

    pinned = [_resolve(repo, info["first"]), _resolve(repo, info["last"])]
    _git(
        repo,
        "-c",
        "user.name=later",
        "-c",
        "user.email=later@local",
        "commit",
        "--allow-empty",
        "-m",
        "work that lands after the fixture was built",
    )
    assert [_resolve(repo, info["first"]), _resolve(repo, info["last"])] == pinned


def test_the_oracle_test_fails_at_the_base_commit_and_passes_at_the_task_commit(
    built_repo,
):
    repo = Path(built_repo["repo"])

    _git(repo, "checkout", "--detach", str(built_repo["first"]))
    # Present at the base commit, so its failure is a real assertion failing and
    # not pytest finding nothing to collect (exit 5).
    assert _in_repo(built_repo, "test").is_file()
    base = _run_fixture_tests(repo)
    # Exit 1 is "tests ran and failed". A collection error (a base impl that is
    # not even importable) exits 2 and would prove nothing about the oracle.
    assert base.returncode == 1, base.stdout + base.stderr
    assert re.search(r"\b\d+ failed\b", base.stdout), base.stdout

    _git(repo, "checkout", "--detach", str(built_repo["last"]))
    task = _run_fixture_tests(repo)
    assert task.returncode == 0, task.stdout


def test_leaves_the_oracle_test_untouched_by_the_task_commit_by_default(built_repo):
    repo = Path(built_repo["repo"])
    first, last = str(built_repo["first"]), str(built_repo["last"])

    assert _show(repo, first, _rel(built_repo, "impl")) != _show(
        repo, last, _rel(built_repo, "impl")
    )
    assert _show(repo, first, _rel(built_repo, "test")) == _show(
        repo, last, _rel(built_repo, "test")
    )


def test_change_test_also_edits_the_oracle_in_the_task_commit(tmp_path, bare_ci):
    root = tmp_path / "changed"
    root.mkdir()

    info = eval_harness_fixtures.build_fixture_repo(root, change_test=True)

    repo = Path(info["repo"])
    first, last = str(info["first"]), str(info["last"])
    # Both views exist and differ, which is what makes a pre-task tree and a
    # sealed tree distinguishable for the harness.
    assert _show(repo, first, _rel(info, "test")) != _show(
        repo, last, _rel(info, "test")
    )
    assert _show(repo, first, _rel(info, "impl")) != _show(
        repo, last, _rel(info, "impl")
    )
    # The edit has to change what the oracle checks. A new comment or a blank
    # line leaves the two views telling the harness exactly the same thing.
    sealed = _assert_lines(_show(repo, last, _rel(info, "test")))
    assert sealed, "the sealed oracle asserts nothing"
    assert sealed != _assert_lines(_show(repo, first, _rel(info, "test")))
    assert _run_fixture_tests(repo).returncode == 0


# -- write_argv_recording_stub ---------------------------------------------


def test_records_every_argument_one_per_line_including_one_with_a_space(
    tmp_path, run_resolved_tool
):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    argv_file = tmp_path / "argv.txt"

    stub = eval_harness_fixtures.write_argv_recording_stub(
        bin_dir, "recorder", argv_file
    )
    done = run_resolved_tool(stub, ["recorder", "--flag", "value with space", "-x"])

    assert done.returncode == 0
    assert argv_file.read_text(encoding="utf-8").splitlines() == [
        "--flag",
        "value with space",
        "-x",
    ]


def test_returns_the_path_the_name_resolver_reports(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()

    stub = eval_harness_fixtures.write_argv_recording_stub(
        bin_dir, "resolvable", tmp_path / "argv.txt"
    )

    resolved = shutil.which("resolvable", path=str(bin_dir))
    assert resolved is not None
    assert stub == Path(resolved)


def test_exits_with_the_given_code_and_writes_the_given_streams(
    tmp_path, run_resolved_tool
):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    argv_file = tmp_path / "argv.txt"

    stub = eval_harness_fixtures.write_argv_recording_stub(
        bin_dir,
        "noisy",
        argv_file,
        exit_code=3,
        stdout="engine said hello",
        stderr="engine warned",
    )
    done = run_resolved_tool(stub, ["noisy", "one"])

    assert done.returncode == 3
    assert "engine said hello" in done.stdout
    assert "engine warned" in done.stderr
    assert "engine said hello" not in done.stderr
    assert "engine warned" not in done.stdout
    # A failing stub still records what it was called with.
    assert argv_file.read_text(encoding="utf-8").splitlines() == ["one"]


def test_keeps_an_apostrophe_in_the_streams_and_the_argv_path_intact(
    tmp_path, run_resolved_tool
):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    # An apostrophe is ordinary English ("didn't") and a legal path character on
    # both platforms. Interpolated raw, each one closes the quoting the stub
    # body opened around it, so the stub breaks when it is written, not here.
    argv_dir = tmp_path / "bob's runs"
    argv_dir.mkdir()
    argv_file = argv_dir / "argv.txt"

    stub = eval_harness_fixtures.write_argv_recording_stub(
        bin_dir,
        "apostrophe",
        argv_file,
        stdout="engine didn't stop",
        stderr="engine didn't warn",
    )
    done = run_resolved_tool(stub, ["apostrophe", "--who", "bob's flag"])

    assert done.returncode == 0
    assert done.stdout.splitlines() == ["engine didn't stop"]
    assert done.stderr.splitlines() == ["engine didn't warn"]
    assert argv_file.read_text(encoding="utf-8").splitlines() == [
        "--who",
        "bob's flag",
    ]


# -- fake_engine_command ---------------------------------------------------

# The effect each mode is named for, told apart by what it leaves behind. No
# one mode's outcome passes another's check: `pass` rewrites the impl and turns
# the suite green, `noop` leaves the tree clean and exits 0, `exit1` leaves it
# clean and exits 1, `drop` dirties the tree but spares the path carrying the
# fix. A command that quietly ran one default mode fails the other three.


def _check_pass_effect(info: dict, done: subprocess.CompletedProcess) -> None:
    assert done.returncode == 0, done.stderr
    assert _written_impl(info) == _task_impl(info)
    assert _run_fixture_tests(Path(info["repo"])).returncode == 0


def _check_noop_effect(info: dict, done: subprocess.CompletedProcess) -> None:
    assert done.returncode == 0, done.stderr
    assert done.stdout.strip(), "noop still owes a final message"
    assert _dirty(Path(info["repo"])) == []
    assert _run_fixture_tests(Path(info["repo"])).returncode != 0


def _check_drop_effect(info: dict, done: subprocess.CompletedProcess) -> None:
    assert done.returncode == 0, done.stderr
    touched = _dirty(Path(info["repo"]))
    assert touched, "drop wrote nothing at all"
    assert _rel(info, "impl") not in touched
    assert _run_fixture_tests(Path(info["repo"])).returncode != 0


def _check_exit1_effect(info: dict, done: subprocess.CompletedProcess) -> None:
    assert done.returncode == 1
    assert _dirty(Path(info["repo"])) == []


NAMED_EFFECTS = {
    "pass": _check_pass_effect,
    "noop": _check_noop_effect,
    "drop": _check_drop_effect,
    "exit1": _check_exit1_effect,
}


@pytest.mark.parametrize("mode", sorted(NAMED_EFFECTS))
def test_names_the_fake_engine_script_as_a_cmd_engine(pre_task_repo, tmp_path, mode):
    command = eval_harness_fixtures.fake_engine_command(mode)

    assert command.startswith("cmd:")
    script = _script_path(command)
    # Absolute, because the engine is run with its cwd set to the fixture repo.
    assert script.is_absolute()
    assert script.is_file()
    assert script.name == "fake_engine.py"
    assert script.parent.name == "fixtures"
    # One command per mode, and the mode has to ride in the command itself: a
    # caller that never exports FAKE_ENGINE_MODE still gets the named effect.
    commands = {
        other: eval_harness_fixtures.fake_engine_command(other) for other in MODES
    }
    assert len(set(commands.values())) == len(MODES), commands

    repo = Path(pre_task_repo["repo"])
    done = _run_engine(
        mode, repo, tmp_path / "attempt", tmp_path / "beat.txt", mode_in_env=False
    )

    NAMED_EFFECTS[mode](pre_task_repo, done)
