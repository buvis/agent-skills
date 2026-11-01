"""Row A9 of the archive security matrix: a template appears whole or not at all.

`build_template` refuses anything already sitting at `dest` - a file, a
directory (empty or not), or a symlink, dangling or not - before extraction
starts, and leaves it as it was. A failure during extraction or during the seal
commit leaves `dest` as it was before the call (absent, here) and every
pre-existing sibling of `dest` untouched.

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
    NEEDS_SYMLINKS,
    PAYLOAD,
    _crafted_tar,
    _outside_sentinel,
    _serve_archive,
    _task_start_commit,
    bare_ci,
    built_repo,
)
from test_eval_tree_archive_safety import OTHER, SEAMS, _select_seam, _snapshot

MEMBERS = [("pkg", DIRECTORY), ("pkg/a.txt", PAYLOAD), ("b.txt", OTHER)]
# Longer than any one path component a host filesystem takes, so the OS itself
# refuses the write: extraction fails partway, after the members before it.
TOO_LONG = "x" * 300


def _state(path: Path):
    """What sits at `path`, without following it: a symlink is its own text."""
    if path.is_symlink():
        return ("symlink", os.readlink(path))
    if path.is_dir():
        return ("dir", _snapshot(path))
    if path.exists():
        return ("file", path.read_bytes(), stat.S_IMODE(path.lstat().st_mode))
    return ("absent",)


def _lay_siblings(parent: Path) -> list:
    """Neighbours of `parent / "template"`, two of them sharing its name's prefix."""
    outside = _outside_sentinel(parent)
    previous = parent / "template.prev"
    previous.write_bytes(b"previous template\n")
    older = parent / "template-old"
    (older / "pkg").mkdir(parents=True)
    (older / "pkg" / "a.txt").write_bytes(b"older tree\n")
    return [outside, previous, older]


def _states(paths: list) -> dict:
    return {path.name: _state(path) for path in paths}


def _lay_file(dest: Path) -> None:
    dest.write_bytes(b"not a template\n")


def _lay_empty_directory(dest: Path) -> None:
    dest.mkdir()


def _lay_full_directory(dest: Path) -> None:
    # `pkg/a.txt` is an archive member too: a merge would overwrite it.
    (dest / "pkg").mkdir(parents=True)
    (dest / "pkg" / "a.txt").write_bytes(b"stale\n")
    (dest / "keep.txt").write_bytes(b"keep\n")


def _lay_dangling_symlink(dest: Path) -> None:
    os.symlink("missing-target", dest)


def _lay_symlink_to_a_directory(dest: Path) -> None:
    linked = dest.parent / "linked"
    linked.mkdir()
    (linked / "held.txt").write_bytes(b"held\n")
    os.symlink("linked", dest)


def _record_extraction(monkeypatch) -> list:
    """Every extraction asked of tarfile, on whichever seam is in place."""
    asked = []
    for name in ("extractall", "extract", "extractfile"):
        real = getattr(tarfile.TarFile, name)

        def spy(self, *args, _name=name, _real=real, **kwargs):
            asked.append(_name)
            return _real(self, *args, **kwargs)

        monkeypatch.setattr(tarfile.TarFile, name, spy)
    return asked


@SEAMS
@pytest.mark.parametrize(
    "lay",
    [
        pytest.param(_lay_file, id="file"),
        pytest.param(_lay_empty_directory, id="empty-directory"),
        pytest.param(_lay_full_directory, id="non-empty-directory"),
        pytest.param(_lay_dangling_symlink, id="dangling-symlink", marks=NEEDS_SYMLINKS),
        pytest.param(_lay_symlink_to_a_directory, id="symlink-to-a-directory", marks=NEEDS_SYMLINKS),
    ],
)
def test_control_build_template_refuses_existing_dest_and_leaves_it_untouched(
    tmp_path, built_repo, monkeypatch, filter_support, lay
):
    _select_seam(monkeypatch, filter_support)
    repo = Path(built_repo["repo"])
    first = _task_start_commit(repo)
    dest = tmp_path / "template"
    lay(dest)
    neighbours = _lay_siblings(tmp_path) + [dest] + sorted(tmp_path.glob("linked"))
    before = _states(neighbours)
    _serve_archive(monkeypatch, _crafted_tar(MEMBERS))
    asked = _record_extraction(monkeypatch)

    with pytest.raises(trees.TreeError):
        trees.build_template(repo, first, dest)

    assert asked == [], "extraction started before the existing dest was refused"
    assert _states(neighbours) == before


@SEAMS
@pytest.mark.parametrize(
    "failing",
    [
        pytest.param(("pkg/" + TOO_LONG, PAYLOAD), id="file-name-too-long"),
        pytest.param((TOO_LONG, DIRECTORY), id="directory-name-too-long"),
    ],
)
def test_build_template_injected_extraction_failure_leaves_no_dest_and_siblings_untouched(
    tmp_path, built_repo, monkeypatch, filter_support, failing
):
    _select_seam(monkeypatch, filter_support)
    repo = Path(built_repo["repo"])
    first = _task_start_commit(repo)
    dest = tmp_path / "template"
    siblings = _lay_siblings(tmp_path)
    before = _states(siblings)
    # The members ahead of the failing one are real work already done.
    _serve_archive(monkeypatch, _crafted_tar(MEMBERS + [failing]))

    with pytest.raises(trees.TreeError):
        trees.build_template(repo, first, dest)

    assert _state(dest) == ("absent",), "a half-built template was left at dest"
    assert _states(siblings) == before


def _subcommand(args: tuple):
    """The git subcommand in `args`, past any leading `-c key=value` pairs."""
    rest = list(args)
    while rest[:1] == ["-c"]:
        rest = rest[2:]
    return rest[0] if rest else None


def _fail_seal_step(monkeypatch, step: str) -> list:
    """Make the seal's git `step` fail; every other git call runs for real."""
    real = trees._git
    reached = []

    def fake(root, *args, **kwargs):
        if _subcommand(args) == step:
            reached.append(step)
            raise subprocess.CalledProcessError(128, ["git", step], stderr="injected failure")
        return real(root, *args, **kwargs)

    monkeypatch.setattr(trees, "_git", fake)
    return reached


@pytest.mark.parametrize("step", ["init", "add", "commit"])
def test_build_template_injected_seal_failure_leaves_no_dest_and_siblings_untouched(
    tmp_path, built_repo, monkeypatch, step
):
    repo = Path(built_repo["repo"])
    first = _task_start_commit(repo)
    dest = tmp_path / "template"
    siblings = _lay_siblings(tmp_path)
    before = _states(siblings)
    _serve_archive(monkeypatch, _crafted_tar(MEMBERS))
    reached = _fail_seal_step(monkeypatch, step)

    # The failure surfaces, as the injected git error or as a TreeError.
    with pytest.raises((subprocess.CalledProcessError, trees.TreeError)):
        trees.build_template(repo, first, dest)

    assert reached == [step], "the seal never reached the step the failure was injected at"
    assert _state(dest) == ("absent",), "a half-sealed template was left at dest"
    assert _states(siblings) == before


@SEAMS
@pytest.mark.parametrize(
    "members",
    [
        pytest.param(MEMBERS, id="nested"),
        pytest.param([("c.txt", OTHER), ("d.txt", PAYLOAD)], id="flat"),
    ],
)
def test_build_template_still_seals_an_absent_dest_beside_siblings_sharing_its_prefix(
    tmp_path, built_repo, monkeypatch, filter_support, members
):
    # The accept twin of the refusals above: an absent dest is built whole, and
    # neighbours whose names start like it are not mistaken for it.
    _select_seam(monkeypatch, filter_support)
    repo = Path(built_repo["repo"])
    first = _task_start_commit(repo)
    dest = tmp_path / "template"
    siblings = _lay_siblings(tmp_path)
    before = _states(siblings)
    _serve_archive(monkeypatch, _crafted_tar(members))

    sha = trees.build_template(repo, first, dest)

    assert sha == trees.head_sha(dest)
    assert trees._git(dest, "status", "--porcelain") == ""
    files = sorted(name for name, (kind, _) in members if kind == "file")
    assert sorted(trees._git(dest, "ls-files").splitlines()) == files
    for name, (kind, data) in members:
        if kind == "file":
            assert (dest / name).read_bytes() == data, name
    assert _states(siblings) == before
