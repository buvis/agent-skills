"""Row A9 of the archive security matrix: a template appears whole or not at all.

`build_template` refuses anything already sitting at `dest` - a file, a
directory (empty or not), or a symlink, dangling or not - before extraction
starts, and leaves it as it was. A failure during extraction or during the seal
commit leaves `dest` as it was before the call (absent, here), every
pre-existing sibling of `dest` untouched, and nothing new beside them. The tree
is staged beside `dest`, never in it, so a `dest` that appears mid-build is
refused too, and a later build inherits nothing from a failed one.

Split from test_eval_tree_archive_safety.py for size; the seams, the sentinel
snapshot and the archive builders are that module's, so there is one spelling
of each.
"""
import errno
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


def _names(parent: Path) -> set:
    """Every entry in `parent`: a staging directory left behind shows here."""
    return {path.name for path in parent.iterdir()}


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


def _watch_extraction(monkeypatch, dest: Path, on_first=None) -> list:
    """Every extraction asked of tarfile, on whichever seam is in place.

    Each one notes whether anything sat at `dest` at that moment, and which
    directories had appeared beside `dest` since the watch began: a staging
    directory on the same filesystem as `dest` is one of those. `on_first`
    runs at the first extraction, before it does any work.
    """
    present = _names(dest.parent)
    seen = []
    for name in ("extractall", "extract", "extractfile"):
        real = getattr(tarfile.TarFile, name)

        def spy(self, *args, _real=real, **kwargs):
            new = [p for p in dest.parent.iterdir() if p.name not in present and p != dest]
            seen.append(
                {
                    "dest_existed": os.path.lexists(dest),
                    "staged_beside": sorted(p.name for p in new if p.is_dir()),
                }
            )
            if on_first is not None and len(seen) == 1:
                on_first()
            return _real(self, *args, **kwargs)

        monkeypatch.setattr(tarfile.TarFile, name, spy)
    return seen


def _run_out_of_space_at(monkeypatch, member_name: str) -> list:
    """Fail the write of `member_name` with ENOSPC, on either seam.

    `makefile` is where `extractall` writes a file's bytes, `extractfile` is
    where a member-by-member extraction reads them; every other member is
    extracted for real. Returns each time the failure fired.
    """
    reached = []
    for method in ("makefile", "extractfile"):
        real = getattr(tarfile.TarFile, method)

        def failing(self, member, *args, _real=real, **kwargs):
            if getattr(member, "name", member) == member_name:
                reached.append(member_name)
                raise OSError(errno.ENOSPC, os.strerror(errno.ENOSPC), member_name)
            return _real(self, member, *args, **kwargs)

        monkeypatch.setattr(tarfile.TarFile, method, failing)
    return reached


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
    asked = _watch_extraction(monkeypatch, dest)

    with pytest.raises(trees.TreeError):
        trees.build_template(repo, first, dest)

    assert asked == [], "extraction started before the existing dest was refused"
    assert _states(neighbours) == before


@SEAMS
@pytest.mark.parametrize(
    "lay",
    [
        pytest.param(_lay_file, id="file"),
        pytest.param(_lay_full_directory, id="non-empty-directory"),
    ],
)
def test_build_template_refuses_a_dest_that_appears_while_it_extracts(
    tmp_path, built_repo, monkeypatch, filter_support, lay
):
    # Something else creates dest after the up-front check: the build must not
    # publish over it, nest itself inside it, or merge into it.
    _select_seam(monkeypatch, filter_support)
    repo = Path(built_repo["repo"])
    first = _task_start_commit(repo)
    dest = tmp_path / "template"
    siblings = _lay_siblings(tmp_path)
    before = _states(siblings)
    present = _names(tmp_path)
    _serve_archive(monkeypatch, _crafted_tar(MEMBERS))
    raced = []

    def race():
        if not os.path.lexists(dest):
            lay(dest)
            raced.append(_state(dest))

    watched = _watch_extraction(monkeypatch, dest, on_first=race)

    with pytest.raises(trees.TreeError):
        trees.build_template(repo, first, dest)

    assert raced, "dest already existed when extraction started"
    assert watched[0]["staged_beside"], "the tree was not staged beside dest"
    assert _state(dest) == raced[0], "the build reached a dest that appeared mid-build"
    assert _states(siblings) == before
    assert _names(tmp_path) == present | {dest.name}, "staging was left behind"


def _name_too_long_file(monkeypatch) -> tuple:
    return MEMBERS + [("pkg/" + TOO_LONG, PAYLOAD)], None


def _name_too_long_directory(monkeypatch) -> tuple:
    return MEMBERS + [(TOO_LONG, DIRECTORY)], None


def _no_space_at_the_third_member(monkeypatch) -> tuple:
    # No name gives this one away ahead of time: only a real write fails.
    return MEMBERS, _run_out_of_space_at(monkeypatch, MEMBERS[2][0])


@SEAMS
@pytest.mark.parametrize(
    "inject",
    [
        pytest.param(_name_too_long_file, id="file-name-too-long"),
        pytest.param(_name_too_long_directory, id="directory-name-too-long"),
        pytest.param(_no_space_at_the_third_member, id="no-space-at-the-third-member"),
    ],
)
def test_build_template_injected_extraction_failure_leaves_no_dest_and_siblings_untouched(
    tmp_path, built_repo, monkeypatch, filter_support, inject
):
    _select_seam(monkeypatch, filter_support)
    repo = Path(built_repo["repo"])
    first = _task_start_commit(repo)
    dest = tmp_path / "template"
    siblings = _lay_siblings(tmp_path)
    before = _states(siblings)
    present = _names(tmp_path)
    # The members ahead of the failing one are real work already done.
    members, reached = inject(monkeypatch)
    _serve_archive(monkeypatch, _crafted_tar(members))
    watched = _watch_extraction(monkeypatch, dest)

    with pytest.raises(trees.TreeError):
        trees.build_template(repo, first, dest)

    assert reached is None or reached, "the injected write failure was never reached"
    assert watched, "extraction never started"
    for seen in watched:
        assert not seen["dest_existed"], "extraction ran with dest already in place"
        assert seen["staged_beside"], "the tree was not staged beside dest"
    assert _state(dest) == ("absent",), "a half-built template was left at dest"
    assert _states(siblings) == before
    assert _names(tmp_path) == present, "something was left beside dest"


def _subcommand(args: tuple):
    """The git subcommand in `args`, past any leading `-c key=value` pairs."""
    rest = list(args)
    while rest[:1] == ["-c"]:
        rest = rest[2:]
    return rest[0] if rest else None


def _fail_seal_step(monkeypatch, step: str, error: BaseException) -> list:
    """Make the seal's git `step` raise `error`; every other git call runs for real."""
    real = trees._git
    reached = []

    def fake(root, *args, **kwargs):
        if _subcommand(args) == step:
            reached.append(step)
            raise error
        return real(root, *args, **kwargs)

    monkeypatch.setattr(trees, "_git", fake)
    return reached


@pytest.mark.parametrize("step", ["init", "add", "commit"])
@pytest.mark.parametrize(
    "make_error",
    [
        pytest.param(
            lambda: subprocess.CalledProcessError(128, ["git"], stderr="injected failure"),
            id="git-fails",
        ),
        pytest.param(lambda: subprocess.TimeoutExpired(["git"], 120), id="git-times-out"),
        pytest.param(lambda: OSError(errno.EIO, "injected I/O error"), id="os-error"),
    ],
)
def test_build_template_injected_seal_failure_leaves_no_dest_and_siblings_untouched(
    tmp_path, built_repo, monkeypatch, step, make_error
):
    repo = Path(built_repo["repo"])
    first = _task_start_commit(repo)
    dest = tmp_path / "template"
    siblings = _lay_siblings(tmp_path)
    before = _states(siblings)
    present = _names(tmp_path)
    _serve_archive(monkeypatch, _crafted_tar(MEMBERS))
    error = make_error()
    reached = _fail_seal_step(monkeypatch, step, error)

    # The failure surfaces, as the injected error itself or as a TreeError.
    with pytest.raises((type(error), trees.TreeError)):
        trees.build_template(repo, first, dest)

    assert reached == [step], "the seal never reached the step the failure was injected at"
    assert _state(dest) == ("absent",), "a half-sealed template was left at dest"
    assert _states(siblings) == before
    assert _names(tmp_path) == present, "something was left beside dest"


# Written by a build that then runs out of space: none of it may reach the next.
DOOMED = [
    ("left", DIRECTORY),
    ("left/over.txt", PAYLOAD),
    ("leftover.txt", OTHER),
    ("doomed.txt", PAYLOAD),
]


def _fail_a_first_attempt(monkeypatch, repo: Path, first: str, dest: Path) -> None:
    """One build at `dest` that dies writing its last member, after the others."""
    reached = _run_out_of_space_at(monkeypatch, DOOMED[-1][0])
    _serve_archive(monkeypatch, _crafted_tar(DOOMED))

    with pytest.raises(trees.TreeError):
        trees.build_template(repo, first, dest)

    assert reached, "the first attempt never reached its injected failure"
    assert _state(dest) == ("absent",), "the failed first attempt left dest behind"


@SEAMS
@pytest.mark.parametrize(
    "members",
    [
        pytest.param(MEMBERS, id="nested"),
        pytest.param([("c.txt", OTHER), ("d.txt", PAYLOAD)], id="flat"),
    ],
)
@pytest.mark.parametrize("after_a_failure", [False, True], ids=["first-try", "after-a-failure"])
def test_build_template_still_seals_an_absent_dest_beside_siblings_sharing_its_prefix(
    tmp_path, built_repo, monkeypatch, filter_support, members, after_a_failure
):
    # The accept twin of the refusals above: an absent dest is built whole, and
    # neighbours whose names start like it are not mistaken for it. After a
    # failed build, the next one holds its own members and nothing else.
    _select_seam(monkeypatch, filter_support)
    repo = Path(built_repo["repo"])
    first = _task_start_commit(repo)
    dest = tmp_path / "template"
    siblings = _lay_siblings(tmp_path)
    before = _states(siblings)
    present = _names(tmp_path)
    if after_a_failure:
        _fail_a_first_attempt(monkeypatch, repo, first, dest)
    _serve_archive(monkeypatch, _crafted_tar(members))

    sha = trees.build_template(repo, first, dest)

    assert _names(tmp_path) == present | {dest.name}, "staging was left beside dest"

    assert sha == trees.head_sha(dest)
    assert trees._git(dest, "status", "--porcelain") == ""
    files = sorted(name for name, (kind, _) in members if kind == "file")
    assert sorted(trees._git(dest, "ls-files").splitlines()) == files
    for name, (kind, data) in members:
        if kind == "file":
            assert (dest / name).read_bytes() == data, name
    assert _states(siblings) == before
