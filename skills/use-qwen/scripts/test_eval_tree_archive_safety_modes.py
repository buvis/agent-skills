"""Row A7 of the archive security matrix: modes and owners the archive asks for.

Split from test_eval_tree_archive_safety.py for size; the seams, the sentinel
snapshot and the archive builders are that module's, so there is one spelling
of each.
"""
import os
import stat
import subprocess
import tarfile
from pathlib import Path

import pytest

from eval_harness import trees

# `bare_ci` and `built_repo` are fixtures: pytest resolves them from this
# module's own namespace, so they have to be imported even though nothing here
# calls them. `built_repo` itself depends on `bare_ci` by name.
from test_eval_tree_links import (
    DIRECTORY,
    _outside_sentinel,
    _serve_archive,
    _task_start_commit,
    bare_ci,
    built_repo,
)
from test_eval_tree_archive_safety import (
    SEAMS,
    _appended,
    _file,
    _sealed_modes,
    _select_seam,
    _snapshot,
)


def _owned_file(mode: int, uid: int, owner: str, name: str = "pkg/tool") -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.mode, info.uid, info.gid, info.uname, info.gname = mode, uid, uid, owner, owner
    return info


def _directory(name: str, mode: int) -> tarfile.TarInfo:
    info = tarfile.TarInfo(name)
    info.type, info.mode = tarfile.DIRTYPE, mode
    return info


TOOL = b"#!/bin/sh\necho tool\n"
SPECIAL_BITS = stat.S_ISUID | stat.S_ISGID
# What a sealed directory may never carry, whatever the archive asked.
UNSAFE_DIRECTORY_BITS = SPECIAL_BITS | stat.S_ISVTX | stat.S_IWGRP | stat.S_IWOTH


def _record_mode_and_owner_requests(monkeypatch) -> list:
    """Every chmod and chown asked of the OS, as (call, target, positional args).

    Read at the OS boundary as well as off the disk: some hosts (a sandboxed
    macOS among them) silently drop a setuid or setgid bit on chmod, so the
    disk alone cannot show that extraction asked for one.
    """
    requested = []
    for name in ("chmod", "fchmod", "lchmod", "chown", "fchown", "lchown"):
        real = getattr(os, name, None)
        if real is None:
            continue

        def spy(target, *args, _name=name, _real=real, **kwargs):
            requested.append((_name, target, args))
            return _real(target, *args, **kwargs)

        monkeypatch.setattr(os, name, spy)
    return requested


def _chowns_to_another_owner(requested: list) -> list:
    """The chown requests that name an owner or group other than the runner's."""
    return [(call, target, args) for call, target, args in requested
            if call.endswith("chown")
            and (args[0] not in (-1, os.getuid()) or args[1] not in (-1, os.getgid()))]


# Members off the `pkg/tool` path, so a fix keyed to the names or the depth of
# one fixed member cannot pass: a second top level, and two levels of nesting.
DIRECTORIES = ("pkg", "pkg/sub", "bin", "bin/x")
NESTED = "pkg/sub/tool"
ELSEWHERE = "bin/x/y"


def _assert_no_special_bit_or_foreign_owner_landed(dest: Path) -> None:
    for name in ("pkg/tool", NESTED, ELSEWHERE):
        status = (dest / name).lstat()
        # POSIX only: Windows reports neither owner uids nor permission bits.
        if hasattr(os, "getuid"):
            assert not status.st_mode & SPECIAL_BITS, (name, oct(status.st_mode))
            assert status.st_uid == os.getuid(), name
        assert status.st_gid == dest.stat().st_gid, name
        assert (dest / name).read_bytes() == TOOL, name
    for name in DIRECTORIES:
        folder = (dest / name).lstat().st_mode
        if hasattr(os, "getuid"):
            assert not folder & UNSAFE_DIRECTORY_BITS, (name, oct(folder))


@SEAMS
# Every directory asks for this mode: files are not the only members whose
# mode has to be stripped, and not only a setuid/setgid one is unsafe.
@pytest.mark.parametrize("folder_mode", [0o777, 0o1777, 0o2775, 0o6777], ids=oct)
@pytest.mark.parametrize(
    "mode, as_root",
    [
        pytest.param(0o4755, False, id="setuid"),
        pytest.param(0o2755, False, id="setgid"),
        pytest.param(0o6755, False, id="setuid-and-setgid"),
        # No special bit at all: the foreign owner has to be refused on its own.
        pytest.param(0o644, False, id="foreign-owner-alone"),
        # As a root CI run: only then does tarfile chown to the archive's owner.
        pytest.param(0o644, True, id="foreign-owner-alone-as-root"),
    ],
)
def test_build_template_never_applies_setuid_setgid_or_a_foreign_owner_from_the_archive(
    tmp_path, built_repo, monkeypatch, filter_support, mode, as_root, folder_mode
):
    asked_filter = _select_seam(monkeypatch, filter_support)
    repo = Path(built_repo["repo"])
    first = _task_start_commit(repo)
    outside = _outside_sentinel(tmp_path)
    before = _snapshot(outside)
    bundle = _appended([], [(_directory(name, folder_mode), None) for name in DIRECTORIES] + [
        (_owned_file(mode, 4242, "mallory"), TOOL),
        (_owned_file(mode, 4242, "mallory", ELSEWHERE), TOOL),
        (_owned_file(0o4755, 4242, "mallory", NESTED), TOOL),
    ])
    _serve_archive(monkeypatch, bundle)
    dest = tmp_path / "template"
    if as_root and hasattr(os, "geteuid"):
        monkeypatch.setattr(os, "geteuid", lambda: 0)
    requested = _record_mode_and_owner_requests(monkeypatch)

    try:
        trees.build_template(repo, first, dest)
    except trees.TreeError:
        # Refusing the archive is one way never to apply the bits: then nothing
        # of it was extracted.
        assert list(dest.glob("*")) == []
    else:
        _assert_no_special_bit_or_foreign_owner_landed(dest)
        # Every host: the sealed tree records the mode Git can, from the archive.
        sealed = _sealed_modes(dest)
        for name, asked in (("pkg/tool", mode), (ELSEWHERE, mode), (NESTED, 0o4755)):
            assert sealed[name] == ("100755" if asked & stat.S_IXUSR else "100644"), name
    assert asked_filter == [], "the no-filter seam was asked for a filter"
    # Every chmod, whatever its target or depth.
    asked_bits = [
        (call, target, oct(args[0]))
        for call, target, args in requested
        if call.endswith("chmod") and args[0] & (SPECIAL_BITS | stat.S_ISVTX)
    ]
    assert asked_bits == [], "extraction asked the OS for setuid/setgid/sticky"
    foreign = [(call, target, args) for call, target, args in requested
               if call.endswith("chown") and 4242 in args[:2]]
    assert foreign == [], "extraction asked the OS for the archive's owner"
    assert _snapshot(outside) == before


@SEAMS
@pytest.mark.parametrize(
    "mode, kept",
    [
        pytest.param(0o755, 0o755, id="executable"),
        pytest.param(0o644, 0o644, id="plain"),
        pytest.param(0o777, 0o755, id="world-writable-executable"),
        pytest.param(0o666, 0o644, id="world-writable-plain"),
        pytest.param(0o1755, 0o755, id="sticky"),
    ],
)
def test_build_template_seals_a_file_with_git_archive_s_root_owner_and_keeps_its_safe_mode_bits(
    tmp_path, built_repo, monkeypatch, filter_support, mode, kept
):
    # The accept twin of the case above: `git archive` itself writes uid 0 and
    # owner `root` on every member, so ownership metadata alone cannot be a
    # reason to refuse. An ordinary mode survives sealing as written; the
    # sticky bit and group/other write are stripped, never applied.
    asked_filter = _select_seam(monkeypatch, filter_support)
    repo = Path(built_repo["repo"])
    first = _task_start_commit(repo)
    outside = _outside_sentinel(tmp_path)
    before = _snapshot(outside)
    files = ["pkg/tool", NESTED, ELSEWHERE]
    bundle = _appended(
        [(name, DIRECTORY) for name in DIRECTORIES],
        [(_owned_file(mode, 0, "root", name), TOOL) for name in files],
    )
    _serve_archive(monkeypatch, bundle)
    dest = tmp_path / "template"
    requested = _record_mode_and_owner_requests(monkeypatch)

    sha = trees.build_template(repo, first, dest)

    assert sha == trees.head_sha(dest)
    assert trees._git(dest, "status", "--porcelain") == ""
    assert sorted(trees._git(dest, "ls-files").splitlines()) == sorted(files)
    sealed = _sealed_modes(dest)
    for name in files:
        status = (dest / name).lstat()
        # POSIX only: Windows reports neither owner uids nor permission bits.
        if hasattr(os, "getuid"):
            assert stat.S_IMODE(status.st_mode) == kept, (name, oct(status.st_mode))
            assert status.st_uid == os.getuid(), name
        assert status.st_gid == dest.stat().st_gid, name
        assert (dest / name).read_bytes() == TOOL, name
        # Every host: the sealed tree records the mode Git can, from the archive.
        assert sealed[name] == ("100755" if mode & stat.S_IXUSR else "100644"), name
    assert _chowns_to_another_owner(requested) == [], "extraction asked for the archive's owner"
    assert asked_filter == [], "the no-filter seam was asked for a filter"
    assert _snapshot(outside) == before


# -- index modes reach git on stdin, not on the command line ----------------

# Windows caps a whole command line at this many characters.
WINDOWS_COMMAND_LINE_LIMIT = 32767
# Executable by the user's bit alone: 0o744 is, 0o654 (group/other only) is not.
SEAL_MODES = (0o755, 0o644, 0o744, 0o654)


def _record_git_argv(monkeypatch) -> list:
    """Every argv `trees` hands `subprocess.run`, each call still run for real."""
    calls = []
    real = trees.subprocess.run

    def spy(*args, **kwargs):
        argv = args[0] if args else kwargs["args"]
        calls.append([os.fspath(part) for part in argv])
        return real(*args, **kwargs)

    monkeypatch.setattr(trees.subprocess, "run", spy)
    return calls


def _update_index_calls(calls: list) -> list:
    return [argv for argv in calls if "update-index" in argv]


def _member_paths_on_the_command_line(calls: list, names) -> list:
    """(argv part, member name) for every member name an argv part carries."""
    return [(part, name) for argv in calls for part in argv for name in names if name in part]


def _parents(names) -> list:
    """Every directory the names sit under, shallowest first."""
    folders = set()
    for name in names:
        parts = name.split("/")
        folders.update("/".join(parts[:depth]) for depth in range(1, len(parts)))
    return sorted(folders, key=lambda folder: (folder.count("/"), folder))


def _ignore_filesystem_mode(monkeypatch) -> None:
    """Git for Windows' default: `git add` records every new file as 100644."""
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.filemode")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "false")


def _tree_modes(dest: Path) -> dict:
    """Each path the sealed HEAD tree holds, with its git mode, from `git ls-tree -r`."""
    modes = {}
    for line in trees._git(dest, "-c", "core.quotePath=false", "ls-tree", "-r", "HEAD").splitlines():
        meta, path = line.split("\t", 1)
        modes[path] = meta.split()[0]
    return modes


def test_build_template_seals_a_thousand_paths_with_none_on_a_git_update_index_command_line(
    tmp_path, built_repo, monkeypatch
):
    # Git ignores the disk's mode here, so every executable bit has to be set
    # through the index: the seal cannot get the modes right without asking git.
    _ignore_filesystem_mode(monkeypatch)
    repo = Path(built_repo["repo"])
    first = _task_start_commit(repo)
    files = {
        f"src/package_{i % 10:02d}/module_{i % 50:02d}/ordinary_source_file_{i:04d}.py":
            SEAL_MODES[i % len(SEAL_MODES)]
        for i in range(1200)
    }
    bundle = _appended(
        [(folder, DIRECTORY) for folder in _parents(files)],
        [_file(name, b"# %s\n" % name.encode(), mode) for name, mode in files.items()],
    )
    _serve_archive(monkeypatch, bundle)
    dest = tmp_path / "template"
    calls = _record_git_argv(monkeypatch)

    trees.build_template(repo, first, dest)

    asked = list(calls)
    updates = _update_index_calls(asked)
    # Both groups set through the index, from stdin; a bare `--refresh` sets nothing.
    chmods = sorted(part for argv in updates for part in argv if part.startswith("--chmod="))
    assert chmods == ["--chmod=+x", "--chmod=-x"], updates
    _assert_each_sets_one_mode_from_nul_delimited_stdin(updates)
    # Any git command: `git add --chmod -- <paths>` carries them as surely.
    assert _member_paths_on_the_command_line(asked, files) == []
    longest = max(len(subprocess.list2cmdline(argv)) for argv in asked)
    assert longest < WINDOWS_COMMAND_LINE_LIMIT, longest
    assert _tree_modes(dest) == {
        name: "100755" if mode & stat.S_IXUSR else "100644" for name, mode in files.items()
    }


def _git_run(root: Path, *args: str) -> bytes:
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, check=True).stdout


def _index_modes(root: Path) -> dict:
    """Each tracked path with its index mode, read as bytes from `ls-files --stage -z`."""
    modes = {}
    for entry in _git_run(root, "ls-files", "--stage", "-z").split(b"\0"):
        if entry:
            meta, path = entry.split(b"\t", 1)
            modes[path.decode("utf-8")] = meta.split()[0].decode("ascii")
    return modes


BYSTANDER = "bystander.txt"


def _staged_with_inverted_modes(root: Path, files: dict) -> None:
    """A repo tracking `files` plus a bystander, each index mode the opposite of its archive mode.

    The bystander is tracked as 100755 and is no member at all, so it must be
    left alone. Inverted, a mode left untouched is wrong either way.
    """
    root.mkdir()
    _git_run(root, "init", "-q")
    _git_run(root, "config", "core.filemode", "false")
    for name in [*files, BYSTANDER]:
        (root / name).parent.mkdir(parents=True, exist_ok=True)
        (root / name).write_bytes(b"#!/bin/sh\necho %s\n" % name.encode())
    _git_run(root, "add", "-A")
    starts_executable = [name for name, mode in files.items() if not mode & stat.S_IXUSR]
    _git_run(root, "update-index", "--chmod=+x", "--", *starts_executable, BYSTANDER)


def _members(files: dict, directories=()) -> list:
    members = []
    for name in directories:
        members.append(_directory(name, 0o755))
    for name, mode in files.items():
        info = tarfile.TarInfo(name)
        info.mode = mode
        members.append(info)
    return members


def _expected_index(files: dict) -> dict:
    expected = {name: "100755" if mode & stat.S_IXUSR else "100644" for name, mode in files.items()}
    return {**expected, BYSTANDER: "100755"}


@pytest.mark.parametrize(
    "files",
    [
        # `bin/run` and `bin/run.txt` share a prefix and sit in opposite groups.
        pytest.param({"bin/run": 0o755, "bin/run.txt": 0o644}, id="one-of-each"),
        pytest.param({"bin/run": 0o755, "tools/build": 0o700}, id="executable-only"),
        pytest.param({"bin/run.txt": 0o644, "notes": 0o654}, id="plain-only"),
        pytest.param({}, id="no-members"),
    ],
)
def test_set_index_modes_asks_git_once_per_non_empty_mode_group_with_paths_on_stdin(
    tmp_path, monkeypatch, files
):
    staging = tmp_path / "staging"
    _staged_with_inverted_modes(staging, files)
    # A directory member carrying an exec bit is not a regular file: no mode to set.
    members = _members(files, directories=sorted({n.split("/")[0] for n in files if "/" in n}))
    calls = _record_git_argv(monkeypatch)

    trees._set_index_modes(staging, members)

    asked_all = list(calls)
    updates = _update_index_calls(asked_all)
    assert _index_modes(staging) == _expected_index(files)
    # Any git command, not only update-index: `git add --chmod -- <paths>` is
    # the same command line under another name.
    assert _member_paths_on_the_command_line(asked_all, [*files, BYSTANDER]) == []
    non_empty = 0
    for flag, executable in (("--chmod=+x", True), ("--chmod=-x", False)):
        group = [n for n, mode in files.items() if bool(mode & stat.S_IXUSR) == executable]
        non_empty += bool(group)
        asked = [argv for argv in updates if flag in argv]
        assert len(asked) == (1 if group else 0), (flag, asked)
    # One process per group, never one per file, and each one reads stdin.
    assert len(updates) == non_empty, updates
    _assert_each_sets_one_mode_from_nul_delimited_stdin(updates)


def _assert_each_sets_one_mode_from_nul_delimited_stdin(updates: list) -> None:
    for argv in updates:
        assert "--stdin" in argv and "-z" in argv, argv
        assert len([part for part in argv if part in ("--chmod=+x", "--chmod=-x")]) == 1, argv


def test_set_index_modes_surfaces_a_git_failure_instead_of_swallowing_it(tmp_path):
    staging = tmp_path / "not-a-repo"
    staging.mkdir()
    (staging / "run").write_bytes(b"#!/bin/sh\n")

    with pytest.raises(subprocess.CalledProcessError) as raised:
        trees._set_index_modes(staging, _members({"run": 0o755}))

    assert Path(os.fsdecode(raised.value.cmd[0])).name in {"git", "git.exe"}, raised.value.cmd

    # The listing succeeds here and only the mode change fails: a held index
    # lock leaves `ls-files` reading, but refuses every `update-index`.
    files = {"bin/run": 0o755, "bin/run.txt": 0o644}
    staging = tmp_path / "locked"
    _staged_with_inverted_modes(staging, files)
    (staging / ".git" / "index.lock").write_bytes(b"")

    with pytest.raises(subprocess.CalledProcessError) as raised:
        trees._set_index_modes(staging, _members(files, directories=["bin"]))

    assert "update-index" in [os.fsdecode(part) for part in raised.value.cmd], raised.value.cmd


# -- non-ASCII names under a legacy Windows code page -----------------------


def _forcing_legacy_code_page(real, seen: list):
    """`subprocess.run` as a legacy Windows code page answers: text decoded as CP1252."""

    def run(*args, **kwargs):
        seen.append(args[0] if args else kwargs["args"])
        if any(kwargs.get(key) for key in ("text", "universal_newlines", "encoding", "errors")):
            kwargs["encoding"] = "cp1252"
        return real(*args, **kwargs)

    return run


def test_set_index_modes_keeps_the_exec_bit_of_a_non_ascii_name_under_a_cp1252_codec(
    tmp_path, monkeypatch
):
    files = {
        "café.sh": 0o755,
        "naïve/tool.sh": 0o755,
        "run.sh": 0o755,
        # Non-ASCII and plain, sharing `caf` and `naïve/` with an executable.
        "café.txt": 0o644,
        "naïve/notes.txt": 0o600,
    }
    root = tmp_path / "staging"
    _staged_with_inverted_modes(root, files)
    seen = []

    with monkeypatch.context() as patched:
        patched.setattr(trees.subprocess, "run", _forcing_legacy_code_page(subprocess.run, seen))
        trees._set_index_modes(root, _members(files, directories=["naïve"]))

    assert seen, "trees never ran git through subprocess.run"
    assert _index_modes(root) == _expected_index(files)
    # Any git command: names on a command line meet the same code page.
    argvs = [[os.fsdecode(os.fspath(part)) for part in argv] for argv in seen]
    assert _member_paths_on_the_command_line(argvs, [*files, BYSTANDER]) == []
