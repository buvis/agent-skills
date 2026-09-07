"""Tests for eval_harness_fixtures.py and fixtures/fake_engine.py: the doubles."""
import contextlib
import json
import os
import re
import shlex
import shutil
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

import eval_harness_fixtures


IS_WINDOWS = os.name == "nt"

# The mode selector is named in the contract. The attempt directory and the
# heartbeat path are contract too ("read from environment variables, so a test
# can point them anywhere") but the contract never spells their names, so this
# suite pins them here. Both are pointed somewhere the engine cannot reach by
# guessing: at a directory that is neither its cwd nor the prompt file's parent.
MODE_ENV = "FAKE_ENGINE_MODE"
ATTEMPT_DIR_ENV = "FAKE_ENGINE_ATTEMPT_DIR"
HEARTBEAT_ENV = "FAKE_ENGINE_HEARTBEAT"

# Every mode that runs to completion under a pipe: the two child-spawning modes
# would hold the pipe open for their grandchild's 600 s, so they get their own
# tests with the streams redirected to files.
COMPLETING_MODES = [
    "pass",
    "noop",
    "stray",
    "drop",
    "mutate-test",
    "vacuous",
    "exit1",
]

MODES = COMPLETING_MODES + ["hang", "spawn-and-exit", "silent-edit"]

# Names git reads for an identity, so the builder's own -c flags are the only
# possible source of one while these are unset.
AMBIENT_GIT_IDENTITY = (
    "GIT_AUTHOR_NAME",
    "GIT_AUTHOR_EMAIL",
    "GIT_COMMITTER_NAME",
    "GIT_COMMITTER_EMAIL",
    "EMAIL",
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
)


# -- helpers: the fixture repo ---------------------------------------------


def _neutralise_git_env(patch, scratch: Path) -> None:
    """Leave git with no config and no identity, the way a CI runner does."""
    patch.setenv("GIT_CONFIG_GLOBAL", str(Path(scratch) / "absent.gitconfig"))
    patch.setenv("GIT_CONFIG_NOSYSTEM", "1")
    for name in AMBIENT_GIT_IDENTITY:
        patch.delenv(name, raising=False)


def _git(repo, *args: str) -> str:
    """Git's stdout, trailing newlines only: porcelain's leading space survives."""
    done = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return done.stdout.rstrip("\n")


def _in_repo(info: dict, key: str) -> Path:
    """The absolute path of `info[key]`, whether it is stored relative or not."""
    return Path(info["repo"]) / Path(info[key])


def _rel(info: dict, key: str) -> str:
    """The repo-relative, slash-form spelling of `info[key]`, for git commands."""
    return _in_repo(info, key).relative_to(Path(info["repo"])).as_posix()


def _show(repo, ref: str, rel: str) -> str:
    return _git(repo, "show", f"{ref}:{rel}")


def _resolve(repo, ref: str) -> str:
    return _git(repo, "rev-parse", f"{ref}^{{commit}}")


def _dirty(repo) -> list:
    """Every path the working tree changed or added, tracked or not."""
    listing = _git(repo, "status", "--porcelain", "--untracked-files=all")
    # `XY<space>PATH`: split off the status field rather than slicing a fixed
    # width, so a path is never trimmed by a column that moved.
    entries = (line.split(maxsplit=1) for line in listing.splitlines() if line.strip())
    return sorted(fields[1] for fields in entries if len(fields) == 2)


def _task_impl(info: dict) -> str:
    """The impl file exactly as the task commit spells it."""
    return _show(Path(info["repo"]), str(info["last"]), _rel(info, "impl"))


def _written_impl(info: dict) -> str:
    """The impl file as it sits in the working tree right now."""
    return _in_repo(info, "impl").read_text(encoding="utf-8").rstrip("\n")


def _assert_lines(source: str) -> list:
    """The assertions a test file makes, whitespace-normalised."""
    return [
        " ".join(line.split())
        for line in source.splitlines()
        if re.match(r"\s*assert\b", line)
    ]


def _run_fixture_tests(repo) -> subprocess.CompletedProcess:
    """Run the fixture repo's own `python -m pytest`, leaving no cache behind."""
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env.pop("PYTEST_ADDOPTS", None)
    env.pop("PYTEST_CURRENT_TEST", None)
    return subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"],
        cwd=str(repo),
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )


# -- helpers: the fake engine ----------------------------------------------


def _script_path(command: str) -> Path:
    """The fake engine script named inside a `cmd:` engine string."""
    assert command.startswith("cmd:"), command
    marker = "fake_engine.py"
    assert marker in command, command
    end = command.index(marker) + len(marker)
    return Path(command[len("cmd:") : end])


def _command_argv(command: str) -> list:
    """The argv a `cmd:` engine string names, whole, on the current platform."""
    assert command.startswith("cmd:"), command
    tokens = shlex.split(command[len("cmd:") :], posix=not IS_WINDOWS)
    if IS_WINDOWS:
        tokens = [token.strip('"') for token in tokens]
    assert tokens, command
    if tokens[0].lower().endswith(".py"):
        tokens = [sys.executable, *tokens]
    return tokens


def _engine_argv(mode: str, prompt: Path) -> list:
    # The whole command, not just the script inside it: whatever selects the
    # mode has to travel in the string the caller was handed.
    command = eval_harness_fixtures.fake_engine_command(mode)
    return [*_command_argv(command), str(prompt)]


def _engine_env(mode, attempt_dir: Path, heartbeat: Path) -> dict:
    env = dict(os.environ)
    env.pop(MODE_ENV, None)
    if mode is not None:
        env[MODE_ENV] = mode
    env[ATTEMPT_DIR_ENV] = str(attempt_dir)
    env[HEARTBEAT_ENV] = str(heartbeat)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _prompt_in(directory: Path, text: str = "make the failing test pass\n") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    prompt = directory / "prompt.md"
    prompt.write_text(text, encoding="utf-8")
    return prompt


def _run_engine(
    mode, repo, attempt_dir, heartbeat, prompt=None, *, mode_in_env=True
) -> subprocess.CompletedProcess:
    attempt_dir.mkdir(parents=True, exist_ok=True)
    return subprocess.run(
        _engine_argv(mode, prompt if prompt is not None else _prompt_in(attempt_dir)),
        cwd=str(repo),
        env=_engine_env(mode if mode_in_env else None, attempt_dir, heartbeat),
        capture_output=True,
        text=True,
        timeout=120,
    )


def _start_engine(mode, repo, attempt_dir, heartbeat) -> subprocess.Popen:
    """Start the engine in its own process group, streams redirected to files."""
    attempt_dir.mkdir(parents=True, exist_ok=True)
    argv = _engine_argv(mode, _prompt_in(attempt_dir))
    grouping = (
        {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
        if IS_WINDOWS
        else {"start_new_session": True}
    )
    with open(attempt_dir / "out.txt", "wb") as out, open(
        attempt_dir / "err.txt", "wb"
    ) as err:
        return subprocess.Popen(
            argv,
            cwd=str(repo),
            env=_engine_env(mode, attempt_dir, heartbeat),
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=err,
            **grouping,
        )


def _kill_process_group(pid: int) -> None:
    """Kill every process still in the group the engine was started in."""
    if IS_WINDOWS:
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(pid)],
            capture_output=True,
            check=False,
            timeout=60,
        )
        with contextlib.suppress(OSError):
            os.kill(pid, signal.CTRL_BREAK_EVENT)
        return
    with contextlib.suppress(ProcessLookupError):
        os.killpg(pid, signal.SIGKILL)


def _size(path: Path) -> int:
    return path.stat().st_size if path.exists() else 0


def _grew_within(path: Path, seconds: float) -> bool:
    start = _size(path)
    deadline = time.monotonic() + seconds
    while time.monotonic() < deadline:
        if _size(path) > start:
            return True
        time.sleep(0.05)
    return False


def _stopped_growing(path: Path, window: float = 1.5) -> bool:
    time.sleep(0.3)  # let any write already in flight land
    settled = _size(path)
    time.sleep(window)
    return _size(path) == settled


def _terminal_event(attempt_dir: Path) -> dict:
    session = attempt_dir / "session.jsonl"
    assert session.is_file(), f"no session.jsonl under {attempt_dir}"
    lines = [
        line for line in session.read_text(encoding="utf-8").splitlines() if line.strip()
    ]
    assert lines, "session.jsonl carries no event"
    return json.loads(lines[-1])


def _values_for(node, key: str) -> list:
    """Every value stored under `key` anywhere inside a decoded JSON node."""
    found = []
    if isinstance(node, dict):
        for name, value in node.items():
            if name == key:
                found.append(value)
            found.extend(_values_for(value, key))
    elif isinstance(node, list):
        for item in node:
            found.extend(_values_for(item, key))
    return found


def _strings_in(node) -> list:
    if isinstance(node, str):
        return [node]
    if isinstance(node, dict):
        return [text for value in node.values() for text in _strings_in(value)]
    if isinstance(node, list):
        return [text for item in node for text in _strings_in(item)]
    return []


def _numbers_in(node) -> list:
    if isinstance(node, bool):
        return []
    if isinstance(node, (int, float)):
        return [node]
    if isinstance(node, dict):
        return [value for item in node.values() for value in _numbers_in(item)]
    if isinstance(node, list):
        return [value for item in node for value in _numbers_in(item)]
    return []


ISO_STAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|[+-]\d{2}:?\d{2})?"
)


def _epochs_for(stamp: str) -> list:
    """Epoch seconds an ISO-8601 stamp can mean: as written, UTC, or local."""
    text = stamp.replace("Z", "+00:00").replace("z", "+00:00")
    try:
        moment = datetime.fromisoformat(text)
    except ValueError:
        return []
    if moment.tzinfo is not None:
        return [moment.timestamp()]
    return [moment.replace(tzinfo=timezone.utc).timestamp(), moment.timestamp()]


def _moments_in(event: dict) -> list:
    """Every moment the event carries, in epoch seconds: ISO stamps and epochs."""
    moments = []
    for text in _strings_in(event):
        for match in ISO_STAMP.finditer(text):
            moments.extend(_epochs_for(match.group(0)))
    moments.extend(float(value) for value in _numbers_in(event) if value > 1_000_000_000)
    return moments


# -- fixtures --------------------------------------------------------------


@pytest.fixture
def bare_ci(tmp_path, monkeypatch):
    """Every test builds its repo the way a runner with no git config would."""
    _neutralise_git_env(monkeypatch, tmp_path)


@pytest.fixture
def built_repo(tmp_path, bare_ci):
    root = tmp_path / "fixture"
    root.mkdir()
    return eval_harness_fixtures.build_fixture_repo(root)


@pytest.fixture
def pre_task_repo(built_repo):
    """The fixture repo checked out at the base commit: the engine's input."""
    _git(built_repo["repo"], "checkout", "--detach", str(built_repo["first"]))
    return built_repo


@pytest.fixture(scope="module")
def protocol_runs(tmp_path_factory):
    """One completed run per mode, shared by the three protocol assertions.

    The prompt file is written outside the attempt directory, so an engine that
    reads its attempt directory from anywhere but the variable writes its
    transcript where no assertion below will find it.
    """
    root = tmp_path_factory.mktemp("protocol") / "fixture"
    root.mkdir()
    with pytest.MonkeyPatch.context() as patch:
        _neutralise_git_env(patch, root.parent)
        info = eval_harness_fixtures.build_fixture_repo(root)
    _git(info["repo"], "checkout", "--detach", str(info["first"]))
    prompt = _prompt_in(tmp_path_factory.mktemp("prompts"))
    runs = {}
    started = time.time()
    for mode in COMPLETING_MODES:
        attempt = tmp_path_factory.mktemp(f"attempt-{mode}")
        done = _run_engine(mode, info["repo"], attempt, attempt / "beat.txt", prompt)
        runs[mode] = (done, attempt)
    return runs, (started, time.time())


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
