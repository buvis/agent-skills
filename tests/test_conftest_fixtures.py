"""Pin the host-portability fixtures the rest of the suite leans on.

Four fixtures let a test say "this file is unreadable", "home is over there" or
"this tool resolves here" once and mean the same thing on POSIX and on native
Windows. So every assertion below is written against what the host itself
reports (`shutil.which`, `Path.home()`, a raised `PermissionError`) instead of
against a path or an environment variable spelled by hand. On Windows
`%PATHEXT%` is uppercase, so a hand-spelled `rg.cmd` and the resolver's answer
differ in case while NTFS hides it; and home is never read from `HOME`, so a
check on that variable passes while `Path.home()` still points at the real
profile.

Several checks run in a fresh interpreter. A denial or a home directory that
exists only as a rebound name inside this process is not one: the consumers of
these fixtures spawn tools, and a child inherits the filesystem and the
environment, never our patched names.

Both hosts run this file. Nothing here is skipped by platform.
"""

from __future__ import annotations

import errno
import os
import shutil
import stat
import subprocess
import sys
from pathlib import Path

import pytest

PLAIN_TEXT = "alpha\nbeta\n"
# Nul, a lone CR and two bytes no text codec round-trips: a fixture that put the
# file back through text mode would corrupt this where a text compare misses it.
BINARY_BLOB = b"\x00\x01\n\r\n\xfe\xff"
# Opens argv[1] in a fresh interpreter: exits 0 when readable, non-zero when not.
CHILD_READ_SOURCE = "import sys; open(sys.argv[1], 'rb').read()"


def _read_in_child(path: Path) -> subprocess.CompletedProcess[str]:
    """Try to read `path` from a process that never imported our conftest."""
    return subprocess.run(
        [sys.executable, "-c", CHILD_READ_SOURCE, str(path)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_stub_path_matches_the_resolvers_answer(tmp_path: Path, write_executable_stub) -> None:
    """The stub's path is what the name resolver reports, not what we spelled."""
    directory = tmp_path / "bin"
    directory.mkdir()
    stub = write_executable_stub(directory, "rg", "fake-rg-alpha")
    resolved = shutil.which("rg", path=str(directory))
    assert resolved is not None, f"nothing named rg resolves inside {directory}"
    assert stub == Path(resolved)


def test_stub_wins_name_lookup_once_on_path(
    tmp_path: Path, monkeypatch, write_executable_stub
) -> None:
    directory = tmp_path / "bin"
    directory.mkdir()
    stub = write_executable_stub(directory, "rg", "fake-rg-alpha")
    monkeypatch.setenv("PATH", str(directory) + os.pathsep + os.environ.get("PATH", ""))
    found = shutil.which("rg")
    assert found is not None, f"{directory} leads PATH but rg does not resolve there"
    assert Path(found) == stub


def test_stub_runs_and_prints_its_body(tmp_path: Path, write_executable_stub) -> None:
    """The stub is a real executable, not a file that merely has the right name.

    Naming it list-form runs on both hosts: POSIX honours the executable bit,
    and Windows starts the command interpreter for a `.bat` or `.cmd`.
    """
    directory = tmp_path / "bin"
    directory.mkdir()
    stub = write_executable_stub(directory, "rg", "fake-rg-alpha")
    completed = subprocess.run([str(stub)], capture_output=True, text=True, check=False)
    assert "fake-rg-alpha" in completed.stdout


def test_home_points_at_the_isolated_directory(tmp_path: Path, isolate_home) -> None:
    home = tmp_path / "home"
    home.mkdir()
    isolate_home(home)
    assert Path.home() == home


def test_tilde_expands_to_the_isolated_directory(tmp_path: Path, isolate_home) -> None:
    home = tmp_path / "home"
    home.mkdir()
    isolate_home(home)
    assert os.path.expanduser("~") == str(home)


def test_isolated_home_reaches_a_child_process(tmp_path: Path, isolate_home) -> None:
    """A child inherits the environment, so the environment must be moved.

    This is also the one check that tells the hosts apart: POSIX reads `HOME`
    and Windows reads `USERPROFILE`, and a fixture that writes the wrong one
    leaves the child pointing at the real profile.
    """
    home = tmp_path / "home"
    home.mkdir()
    isolate_home(home)
    completed = subprocess.run(
        [sys.executable, "-c", "import pathlib; print(pathlib.Path.home())"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip() == str(home)


def test_armed_file_refuses_every_read_call_site(tmp_path: Path, deny_access) -> None:
    """Every documented route must refuse, including the one below `io`.

    The four Python-level routes all bottom out in `io.open`, so a single
    interception point satisfies all of them. `os.open` is the descriptor-level
    call the others are built on, and a consumer that reaches for it must get
    the same refusal.
    """
    secret = tmp_path / "secret.txt"
    secret.write_text(PLAIN_TEXT, encoding="utf-8")
    deny_access(secret)
    with pytest.raises(PermissionError):
        secret.read_text(encoding="utf-8")
    with pytest.raises(PermissionError):
        secret.read_bytes()
    with pytest.raises(PermissionError), open(secret, encoding="utf-8") as handle:
        handle.read()
    with pytest.raises(PermissionError), secret.open(encoding="utf-8") as handle:
        handle.read()
    with pytest.raises(PermissionError):
        os.open(secret, os.O_RDONLY)


def test_armed_file_still_reports_that_it_exists(tmp_path: Path, deny_access) -> None:
    """Unreadable and missing are different states, and consumers read the gap."""
    secret = tmp_path / "secret.txt"
    secret.write_text(PLAIN_TEXT, encoding="utf-8")
    deny_access(secret)
    with pytest.raises(PermissionError):
        secret.read_bytes()  # the denial really is in force
    assert secret.exists()


def test_armed_file_stays_unreadable_to_a_child_process(tmp_path: Path, deny_access) -> None:
    """How far the denial reaches is what the hosts disagree about.

    On POSIX the file's own permission bits are revoked, the kernel enforces
    them, and the refusal therefore crosses a process boundary: a fresh
    interpreter that never imported our conftest still cannot read the file.
    The bystander read is the control there - it proves the probe works and
    that arming did not simply break every child.

    On Windows those bits cannot revoke a read at all, so the denial sits at
    the Python call boundary and reaches this process only. The contract there
    is the in-process refusal, so that is what gets asserted; spawning a child
    would only measure a boundary the mechanism was never built to cross.
    """
    secret = tmp_path / "secret.txt"
    secret.write_text(PLAIN_TEXT, encoding="utf-8")
    if os.name == "nt":
        deny_access(secret)
        with pytest.raises(PermissionError), open(secret, encoding="utf-8") as handle:
            handle.read()
        assert secret.exists(), "the armed file must refuse to open, not go missing"
        return
    bystander = tmp_path / "bystander.txt"
    bystander.write_text(PLAIN_TEXT, encoding="utf-8")
    deny_access(secret)
    control = _read_in_child(bystander)
    assert control.returncode == 0, f"the probe itself is broken: {control.stderr}"
    attempt = _read_in_child(secret)
    assert attempt.returncode != 0, f"a fresh interpreter still read {secret}"


def test_armed_directory_refuses_a_childs_stat(tmp_path: Path, deny_access) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    child = vault / "child.txt"
    child.write_text(PLAIN_TEXT, encoding="utf-8")
    allow = deny_access(vault)
    with pytest.raises(PermissionError):
        child.is_file()
    allow()
    assert child.is_file(), "the child must exist, or refusing to stat it proves nothing"


def test_armed_directory_refuses_listing(tmp_path: Path, deny_access) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    (vault / "child.txt").write_text(PLAIN_TEXT, encoding="utf-8")
    allow = deny_access(vault)
    with pytest.raises(PermissionError):
        list(vault.iterdir())
    allow()
    assert [entry.name for entry in vault.iterdir()] == ["child.txt"]


def test_armed_directory_still_reports_that_it_exists(tmp_path: Path, deny_access) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    allow = deny_access(vault)
    with pytest.raises(PermissionError):
        list(vault.iterdir())  # the denial really is in force
    assert vault.exists()
    allow()


def test_armed_directory_refuses_creation_inside_it(tmp_path: Path, deny_access) -> None:
    vault = tmp_path / "vault"
    vault.mkdir()
    allow = deny_access(vault)
    with pytest.raises(PermissionError):
        (vault / "new.txt").write_text("nope", encoding="utf-8")
    allow()
    (vault / "new.txt").write_text("written", encoding="utf-8")
    assert (vault / "new.txt").read_text(encoding="utf-8") == "written"


def test_lifting_denial_restores_the_original_bytes(tmp_path: Path, deny_access) -> None:
    secret = tmp_path / "secret.bin"
    secret.write_bytes(BINARY_BLOB)
    allow = deny_access(secret)
    with pytest.raises(PermissionError):
        secret.read_bytes()
    allow()
    assert secret.read_bytes() == BINARY_BLOB
    with open(secret, "rb") as handle:
        assert handle.read() == BINARY_BLOB


def test_lifting_denial_restores_the_original_permission_mode(tmp_path: Path, deny_access) -> None:
    """A private file must not come back wider than it went in.

    The file starts at `0o600`, so a restore that writes a fixed `0o644` hands
    it back world-readable. On Windows the mode does not move at all, which
    makes the same equality the right assertion on both hosts.
    """
    secret = tmp_path / "secret.bin"
    secret.write_bytes(BINARY_BLOB)
    os.chmod(secret, 0o600)
    before = stat.S_IMODE(secret.stat().st_mode)
    allow = deny_access(secret)
    with pytest.raises(PermissionError):
        secret.read_bytes()  # the denial really is in force
    allow()
    assert stat.S_IMODE(secret.stat().st_mode) == before


def test_arming_one_path_leaves_others_readable(tmp_path: Path, deny_access) -> None:
    armed = tmp_path / "armed.bin"
    armed.write_bytes(BINARY_BLOB)
    bystander = tmp_path / "bystander.bin"
    bystander.write_bytes(BINARY_BLOB)
    allow = deny_access(armed)
    with pytest.raises(PermissionError):
        armed.read_bytes()  # the denial really is in force
    assert bystander.read_bytes() == BINARY_BLOB
    allow()
    assert bystander.read_bytes() == BINARY_BLOB


def test_refusal_carries_the_permission_denied_errno(tmp_path: Path, deny_access) -> None:
    secret = tmp_path / "secret.txt"
    secret.write_text(PLAIN_TEXT, encoding="utf-8")
    deny_access(secret)
    with pytest.raises(PermissionError) as refusal:
        secret.read_bytes()
    assert refusal.value.errno == errno.EACCES


def test_refusal_text_matches_for_str_and_path_args(tmp_path: Path, deny_access) -> None:
    """Consumer tests compare refusal text across two separately raised errors."""
    secret = tmp_path / "secret.txt"
    secret.write_text(PLAIN_TEXT, encoding="utf-8")
    deny_access(secret)
    with pytest.raises(PermissionError) as first, open(str(secret), encoding="utf-8") as handle:
        handle.read()
    with pytest.raises(PermissionError) as second, open(secret, encoding="utf-8") as handle:
        handle.read()
    assert str(first.value)
    assert str(first.value) == str(second.value)


def test_resolved_tool_run_captures_the_stubs_output(
    tmp_path: Path, write_executable_stub, run_resolved_tool
) -> None:
    directory = tmp_path / "bin"
    directory.mkdir()
    stub = write_executable_stub(directory, "rg", "fake-rg-alpha")
    completed = run_resolved_tool(stub, ["rg", "--version"])
    assert isinstance(completed, subprocess.CompletedProcess)
    assert completed.returncode == 0
    assert isinstance(completed.stdout, str), "output must come back as text, not bytes"
    assert "fake-rg-alpha" in completed.stdout


def test_resolved_path_beats_a_path_lookup_of_argv0(
    tmp_path: Path, monkeypatch, write_executable_stub, run_resolved_tool
) -> None:
    """`argv[0]` is a label. What runs is the executable at the resolved path."""
    chosen_dir = tmp_path / "chosen"
    chosen_dir.mkdir()
    decoy_dir = tmp_path / "decoy"
    decoy_dir.mkdir()
    chosen = write_executable_stub(chosen_dir, "rg", "body-from-chosen")
    decoy = write_executable_stub(decoy_dir, "rg", "body-from-decoy")
    monkeypatch.setenv("PATH", str(decoy_dir) + os.pathsep + os.environ.get("PATH", ""))
    on_path = shutil.which("rg")
    assert on_path is not None and Path(on_path) == decoy, "PATH must resolve rg to the decoy"
    completed = run_resolved_tool(chosen, ["rg"])
    assert "body-from-chosen" in completed.stdout
    assert "body-from-decoy" not in completed.stdout


def test_resolved_tool_run_starts_a_process_and_passes_the_rest_of_argv(run_resolved_tool) -> None:
    """The output has to be computed by the child, not assembled by the caller.

    The interpreter running this suite is the one executable both hosts are
    guaranteed to have, and it reports back what it was actually handed. No
    part of `--version 42` exists on disk to be copied out of a file.
    """
    completed = run_resolved_tool(
        Path(sys.executable),
        ["python", "-c", "import sys; print(sys.argv[1], 6 * 7)", "--version"],
    )
    assert completed.returncode == 0
    assert "--version" in completed.stdout, "the arguments after argv[0] never reached the child"
    assert "42" in completed.stdout, "nothing computed the output, so nothing ran"


def test_running_a_file_that_is_not_executable_raises(tmp_path: Path, run_resolved_tool) -> None:
    """A launch failure must surface, not be reported back as a clean run.

    Both hosts refuse this: POSIX cannot exec a file with no executable bit,
    and Windows rejects it as not a valid application. `PermissionError` is an
    `OSError`, so the broader class covers both answers.
    """
    plain = tmp_path / "not-a-tool.txt"
    plain.write_text(PLAIN_TEXT, encoding="utf-8")
    os.chmod(plain, 0o644)
    with pytest.raises(OSError):
        run_resolved_tool(plain, ["not-a-tool"])
