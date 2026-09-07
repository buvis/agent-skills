"""Host-portability fixtures for the whole suite.

Lives at the repository root so pytest injects it into every collected test
under `testpaths`, including each `skills/*/scripts/` tree, without any
sys.path or import plumbing.
"""

from __future__ import annotations

import builtins
import errno
import io
import os
import shutil
import subprocess
from pathlib import Path

import pytest

IS_WINDOWS: bool = os.name == "nt"


@pytest.fixture
def write_executable_stub():
    """Write a runnable stub and hand back the path the name resolver reports.

    The path comes from `shutil.which`, never hand-spelled: on Windows the
    resolver appends the extension verbatim from `%PATHEXT%`, which is
    uppercase by default, so a hand-spelled `rg.cmd` and the resolver's
    `rg.CMD` differ in case while NTFS hides the mismatch.
    """

    def write(directory: Path, name: str, body: str) -> Path:
        if IS_WINDOWS:
            stub = directory / f"{name}.cmd"
            stub.write_text(f"@echo off\r\necho {body}\r\n", encoding="utf-8", newline="")
        else:
            stub = directory / name
            stub.write_text(f"#!/bin/sh\necho {body}\n", encoding="utf-8")
            stub.chmod(0o755)
        resolved = shutil.which(name, path=str(directory))
        assert resolved is not None, f"nothing named {name!r} resolves inside {directory}"
        return Path(resolved)

    return write


@pytest.fixture
def isolate_home(monkeypatch):
    """Point this process and every child it spawns at `path` as home.

    `ntpath.expanduser` ignores `HOME` entirely - it reads `USERPROFILE`, then
    `HOMEDRIVE` plus `HOMEPATH` - so setting `HOME` alone is a silent no-op on
    Windows and `Path.home()` still lands on the real profile.
    """

    def isolate(path: Path) -> None:
        monkeypatch.setenv("HOME", str(path))
        if IS_WINDOWS:
            drive, tail = os.path.splitdrive(str(path))
            monkeypatch.setenv("USERPROFILE", str(path))
            monkeypatch.setenv("HOMEDRIVE", drive)
            monkeypatch.setenv("HOMEPATH", tail)

    return isolate


def _deny_by_wrapping(monkeypatch):
    """Refuse the filesystem call vectors for armed paths, the Windows branch.

    Permission bits cannot revoke a read there, so the denial sits at the
    Python call boundary and reaches this process only.
    """
    armed: list[str] = []
    real_io_open = io.open
    real_builtins_open = builtins.open
    real_open = os.open
    real_listdir = os.listdir
    real_scandir = os.scandir
    real_stat = os.stat
    real_lstat = os.lstat
    real_mkdir = os.mkdir

    def normalise(path) -> str | None:
        try:
            raw = os.fspath(path)
        except TypeError:
            return None
        if isinstance(raw, bytes):
            raw = os.fsdecode(raw)
        return os.path.normcase(os.path.abspath(raw))

    def refused(path, inside_only: bool) -> str | None:
        target = normalise(path)
        if target is None:
            return None
        for root in armed:
            if target.startswith(root + os.sep) or (target == root and not inside_only):
                return target
        return None

    def guard(real, inside_only: bool = False):
        def wrapper(path=".", *args, **kwargs):
            # Built from the normalised path, so the refusal text is identical
            # whether the caller passed a `str` or a `Path`.
            target = refused(path, inside_only)
            if target is not None:
                raise PermissionError(errno.EACCES, os.strerror(errno.EACCES), target)
            return real(path, *args, **kwargs)

        return wrapper

    # `io.open` is what `Path.open`, and so `Path.read_text`, resolves at call
    # time; `builtins.open` is a separate binding for plain call sites; `os.open`
    # is the descriptor-level call underneath both. `listdir` and `scandir` are
    # both wrapped because which one `Path.iterdir` uses changed in 3.13, and
    # both 3.10 and 3.13 are in the matrix. `stat` and `lstat` deny only paths
    # strictly inside an armed directory, so a child's `is_file()` refuses while
    # the armed path itself still reports that it exists.
    monkeypatch.setattr(io, "open", guard(real_io_open))
    monkeypatch.setattr(builtins, "open", guard(real_builtins_open))
    monkeypatch.setattr(os, "open", guard(real_open))
    monkeypatch.setattr(os, "listdir", guard(real_listdir))
    monkeypatch.setattr(os, "scandir", guard(real_scandir))
    monkeypatch.setattr(os, "stat", guard(real_stat, inside_only=True))
    monkeypatch.setattr(os, "lstat", guard(real_lstat, inside_only=True))
    monkeypatch.setattr(os, "mkdir", guard(real_mkdir))

    def deny(path: Path):
        root = normalise(path)
        armed.append(root)
        if os.path.isdir(root):
            # Fail here rather than let a test go green on the wrong branch.
            with pytest.raises(PermissionError):
                os.stat(os.path.join(root, "denial-self-check"))
        return lambda: armed.remove(root)

    return deny


@pytest.fixture
def deny_access(monkeypatch):
    """Arm a path so reads refuse; the returned callable lifts the denial again.

    Reads of an armed path raise `PermissionError` while the path still reports
    that it exists - unreadable and missing are different states. On POSIX the
    permission bits are revoked, so the kernel enforces the refusal across a
    process boundary too.
    """
    if IS_WINDOWS:
        yield _deny_by_wrapping(monkeypatch)
        return

    restore: list[tuple[Path, int]] = []

    def deny(path: Path):
        target = Path(path)
        mode = target.stat().st_mode & 0o7777
        restore.append((target, mode))
        target.chmod(0o000)
        return lambda: target.chmod(mode)

    yield deny
    # Restore unconditionally, so tmp_path cleanup can still unlink the tree.
    for target, mode in restore:
        target.chmod(mode)


@pytest.fixture
def run_resolved_tool():
    """Run the executable at `resolved`, handing `argv` to the child.

    On POSIX `executable=` keeps `argv[0]` a label the caller chose. The same
    argument sets `lpApplicationName` on Windows, where CreateProcess refuses a
    `.cmd`, and there is no `argv[0]` dispatch to preserve there anyway.
    """

    def run(resolved: Path, argv: list[str]) -> subprocess.CompletedProcess:
        if IS_WINDOWS:
            return subprocess.run(
                [str(resolved), *argv[1:]], capture_output=True, text=True, check=False
            )
        return subprocess.run(
            argv, executable=str(resolved), capture_output=True, text=True, check=False
        )

    return run
