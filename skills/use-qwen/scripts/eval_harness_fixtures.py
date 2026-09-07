"""Doubles for the eval-harness tests: a git fixture repo, stubs, a fake engine.

Test-only module. Tests import it; production code never does.
"""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path

IS_WINDOWS = os.name == "nt"

FAKE_ENGINE = Path(__file__).resolve().parent / "fixtures" / "fake_engine.py"

IMPL_NAME = "calc.py"
TEST_NAME = "test_calc.py"

# Identity and branch name on every history-writing invocation: a CI runner
# carries no global git config, so nothing else can supply them.
IDENTITY = (
    "-c",
    "user.name=eval-harness",
    "-c",
    "user.email=eval-harness@local",
    "-c",
    "init.defaultBranch=main",
)

BROKEN_IMPL = '''"""Arithmetic the oracle test checks."""


def add(left, right):
    return left - right
'''

# fixtures/fake_engine.py writes this same text in its fixing modes, so the two
# spellings have to stay byte-identical; `pass` mode's test compares them.
FIXED_IMPL = '''"""Arithmetic the oracle test checks."""


def add(left, right):
    return left + right
'''

ORACLE = '''from calc import add


def test_add_returns_the_sum_of_its_arguments():
    assert add(2, 3) == 5
'''

WIDENED_ORACLE = '''from calc import add


def test_add_returns_the_sum_of_its_arguments():
    assert add(2, 3) == 5
    assert add(-4, 1) == -3
'''


def _git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return done.stdout.strip()


def build_fixture_repo(root: Path, *, change_test: bool = False) -> dict:
    """Build a repo whose base commit fails its own test and whose task commit passes.

    With `change_test` the task commit also widens the oracle, which is what
    makes a pre-task tree and a sealed tree distinguishable.
    """
    impl, oracle = root / IMPL_NAME, root / TEST_NAME
    _git(root, *IDENTITY, "init")

    impl.write_text(BROKEN_IMPL, encoding="utf-8")
    oracle.write_text(ORACLE, encoding="utf-8")
    _git(root, "add", IMPL_NAME, TEST_NAME)
    _git(root, *IDENTITY, "commit", "-m", "base: add() subtracts and the oracle says so")
    first = _git(root, "rev-parse", "HEAD")

    impl.write_text(FIXED_IMPL, encoding="utf-8")
    if change_test:
        oracle.write_text(WIDENED_ORACLE, encoding="utf-8")
    _git(root, "add", IMPL_NAME, TEST_NAME)
    _git(root, *IDENTITY, "commit", "-m", "task: make add() sum its arguments")
    last = _git(root, "rev-parse", "HEAD")

    # Commit ids, never refs: a later commit would move a ref under the caller.
    return {
        "repo": root,
        "first": first,
        "last": last,
        "impl": IMPL_NAME,
        "test": TEST_NAME,
    }


def _cmd_echo_arg(text: str) -> str:
    """Escape one `echo` argument for a batch file, so it prints verbatim.

    `%` doubles; the command metacharacters take a caret. Carets go first, or
    the ones this adds get escaped again.
    """
    escaped = text.replace("%", "%%")
    for char in "^&<>|()":
        escaped = escaped.replace(char, f"^{char}")
    return escaped


def _cmd_stub_lines(
    argv_file: Path,
    exit_code: int,
    stdout: str,
    stderr: str,
    cwd_file: Path | None,
) -> list[str]:
    """Build the `.cmd` body of an argv-recording stub.

    The shift loop keeps one argument per line; `for %%A in (%*)` would split
    "value with space" into three. Redirections lead the command so an argument
    ending in a digit is not read as a stream handle.
    """
    lines = [
        "@echo off",
        f'>"{argv_file}" type nul',
        ":loop",
        'if "%~1"=="" goto done',
        f'>>"{argv_file}" echo %~1',
        "shift",
        "goto loop",
        ":done",
    ]
    if cwd_file is not None:
        lines.append(f'>"{cwd_file}" echo %CD%')
    if stdout:
        lines.append(f"echo {_cmd_echo_arg(stdout)}")
    if stderr:
        lines.append(f"1>&2 echo {_cmd_echo_arg(stderr)}")
    lines.append(f"exit /b {exit_code}")
    return lines


def _sh_stub_lines(
    argv_file: Path,
    exit_code: int,
    stdout: str,
    stderr: str,
    cwd_file: Path | None,
) -> list[str]:
    """Build the `/bin/sh` body of an argv-recording stub."""
    target = shlex.quote(str(argv_file))
    lines = ["#!/bin/sh", f"printf '%s\\n' \"$@\" > {target}"]
    if cwd_file is not None:
        # `-P` prints the directory the kernel says the stub is in, not the
        # inherited PWD a symlinked temporary directory would spell.
        lines.append(f"pwd -P > {shlex.quote(str(cwd_file))}")
    if stdout:
        lines.append(f"printf '%s\\n' {shlex.quote(stdout)}")
    if stderr:
        lines.append(f"printf '%s\\n' {shlex.quote(stderr)} >&2")
    lines.append(f"exit {exit_code}")
    return lines


def write_argv_recording_stub(
    directory: Path,
    name: str,
    argv_file: Path,
    *,
    exit_code: int = 0,
    stdout: str = "",
    stderr: str = "",
    cwd_file: Path | None = None,
) -> Path:
    """Write a stub that records its argv, one line per argument, then answers.

    The repo-root `write_executable_stub` fixture emits a single fixed echo line
    and captures no argv, which the adapter tests need byte for byte. The
    returned path is `shutil.which`'s, so Windows `%PATHEXT%` casing is handled.

    With `cwd_file` the stub also records the directory it ran in, which is the
    only trace a caller leaves when it names its target by changing directory
    rather than by passing a path.
    """
    if IS_WINDOWS:
        lines = _cmd_stub_lines(argv_file, exit_code, stdout, stderr, cwd_file)
        stub = Path(directory) / f"{name}.cmd"
        stub.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8", newline="")
    else:
        lines = _sh_stub_lines(argv_file, exit_code, stdout, stderr, cwd_file)
        stub = Path(directory) / name
        stub.write_text("\n".join(lines) + "\n", encoding="utf-8")
        stub.chmod(0o755)
    return Path(shutil.which(name, path=str(directory)))


def fake_engine_command(mode: str) -> str:
    """The `cmd:` engine string that runs the fake engine in `mode`.

    The mode rides in the command itself, so a caller that never exports an
    environment variable still gets the named effect. The `.py` suffix routes
    the string through `sys.executable` on every platform.
    """
    return f"cmd:{FAKE_ENGINE} {mode}"
