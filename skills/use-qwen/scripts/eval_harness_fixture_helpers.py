"""Shared helpers and fixtures for the eval_harness_fixtures test modules."""
import contextlib
import json
import os
import re
import shlex
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
