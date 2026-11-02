"""Row A7 of the archive security matrix: modes and owners the archive asks for.

Split from test_eval_tree_archive_safety.py for size; the seams, the sentinel
snapshot and the archive builders are that module's, so there is one spelling
of each.
"""
import os
import stat
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
from test_eval_tree_archive_safety import SEAMS, _appended, _sealed_modes, _select_seam, _snapshot


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
