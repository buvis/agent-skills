"""The archive security matrix eval_harness/trees.py's build_template answers.

Rows A1-A7 and A12: what a crafted `git archive` tar may not do to the host,
whether or not this runtime's tarfile ships a `data_filter`. Every case runs on
both seams: the filter-present one this runtime takes, and a filter-absent one
that stands in for a Python older than 3.12, whose `extractall` knows no
`filter` keyword and applies the archive as written. Each case keeps a
sentinel directory beside the template and proves its bytes and modes are what
they were, so an escape is caught by what it did, not only by what was raised.

The archive builders and the sentinel come from test_eval_tree_links.py, so
there is one spelling of each.
"""
import io
import os
import stat
import tarfile
from pathlib import Path

import pytest

from eval_harness import trees

# `bare_ci` and `built_repo` are fixtures: pytest resolves them from this
# module's own namespace, so they have to be imported even though nothing here
# calls them.
from test_eval_tree_links import (
    DIRECTORY,
    NEEDS_SYMLINKS,
    PAYLOAD,
    _crafted_tar,
    _hide_data_filter,
    _outside_sentinel,
    _serve_archive,
    _task_start_commit,
    bare_ci,
    built_repo,
)

# A second content value, so a check that only ever sees one payload cannot
# pass by remembering it.
OTHER = ("file", b"other\n")

SEAMS = pytest.mark.parametrize("filter_support", ["with-data-filter", "without-data-filter"])


class _TarFileBeforeDataFilter(tarfile.TarFile):
    """A TarFile as Python shipped it before 3.12: `extractall` has no `filter`.

    Asked for one, it fails the way such a runtime fails. Asked without one, it
    applies the archive as written - modes, links and all - which is what a
    builder that leans on the runtime's own filter gets there.
    """

    def extractall(self, path=".", members=None, *, numeric_owner=False, **kwargs):
        if kwargs:
            raise TypeError(
                "extractall() got an unexpected keyword argument %r" % next(iter(kwargs))
            )
        super().extractall(
            path, members, numeric_owner=numeric_owner, filter=tarfile.fully_trusted_filter
        )


class _TarfileModuleBeforeDataFilter:
    """The `tarfile` module `_hide_data_filter` leaves, opening the double above."""

    def __init__(self, hidden):
        self._hidden = hidden

    def __getattr__(self, name):
        if name == "open":
            return _TarFileBeforeDataFilter.open
        return getattr(self._hidden, name)


def _select_seam(monkeypatch, filter_support: str) -> None:
    """Leave the runtime's tarfile alone, or take `data_filter` and `filter=` away."""
    if filter_support == "with-data-filter":
        return
    _hide_data_filter(monkeypatch)
    monkeypatch.setattr(trees, "tarfile", _TarfileModuleBeforeDataFilter(trees.tarfile))


def _snapshot(outside: Path) -> dict:
    """Every entry under the sentinel directory: its mode, and its bytes if a file."""
    seen = {".": stat.S_IMODE(outside.lstat().st_mode)}
    for path in sorted(outside.rglob("*")):
        status = path.lstat()
        held = path.read_bytes() if stat.S_ISREG(status.st_mode) else None
        seen[path.relative_to(outside).as_posix()] = (status.st_mode, held)
    return seen


def _appended(members: list, extra: list) -> bytes:
    """`_crafted_tar(members)`, then each (TarInfo, bytes or None) of `extra`."""
    buffer = io.BytesIO(_crafted_tar(members))
    with tarfile.open(fileobj=buffer, mode="a") as archive:
        for info, data in extra:
            if data is not None:
                info.size = len(data)
            archive.addfile(info, None if data is None else io.BytesIO(data))
    return buffer.getvalue()


def _assert_refused_on_seam(tmp_path, built_repo, monkeypatch, filter_support, bundle) -> None:
    _select_seam(monkeypatch, filter_support)
    repo = Path(built_repo["repo"])
    first = _task_start_commit(repo)
    outside = _outside_sentinel(tmp_path)
    before = _snapshot(outside)
    _serve_archive(monkeypatch, bundle)
    dest = tmp_path / "template"

    raised = None
    try:
        trees.build_template(repo, first, dest)
    except Exception as error:
        raised = error

    # Checked first: an escape that wrote outside is the worst outcome, and the
    # failure should say so rather than only that no TreeError came back.
    assert _snapshot(outside) == before, "the archive changed the outside directory"
    assert isinstance(raised, trees.TreeError), "expected a TreeError, got %r" % (raised,)
    # Refused before extraction: no half-built template left behind.
    assert list(dest.glob("*")) == []


def _outside_spelled(tmp_path: Path, text: str) -> str:
    return text.format(outside=(tmp_path / "outside").as_posix())


# -- A1: a member whose own path crosses a link that leaves the tree ---------

# The PRD's worked example. Every name is unique and `alias -> pkg` stays
# inside, but `alias/escape` is really `pkg/escape`, a link out of the tree,
# and `pkg/escape/secret.txt` writes through it. Judged name by name, nothing
# is wrong; only the landings, taken together, show the collision.
ANCESTOR_ESCAPES = [
    pytest.param(
        [("pkg", DIRECTORY), ("alias", ("sym", "pkg")),
         ("alias/escape", ("sym", "../../outside")), ("pkg/escape/secret.txt", PAYLOAD)],
        id="escaping-link-then-file-under-its-real-path",
    ),
    pytest.param(
        [("pkg", DIRECTORY), ("alias", ("sym", "pkg")),
         ("pkg/escape/secret.txt", PAYLOAD), ("alias/escape", ("sym", "../../outside"))],
        id="file-under-the-real-path-then-escaping-link",
    ),
    # Judged by its own text, every link here stays inside: `a/b/alias` reads
    # as `pkg`, `a/b/alias/escape` as `a/outside`. Only once `a/b/alias` is
    # followed to `pkg` does `escape` sit in `pkg` and climb out of the tree.
    pytest.param(
        [("a", DIRECTORY), ("a/b", DIRECTORY), ("pkg", DIRECTORY),
         ("a/b/alias", ("sym", "../../pkg")), ("a/b/alias/escape", ("sym", "../../outside")),
         ("a/b/alias/escape/secret.txt", PAYLOAD)],
        id="link-text-stays-inside-but-its-real-landing-leaves",
    ),
    pytest.param(
        [("a", DIRECTORY), ("a/b", DIRECTORY), ("pkg", DIRECTORY),
         ("a/b/alias", ("sym", "../../pkg")), ("a/b/alias/escape/secret.txt", PAYLOAD),
         ("a/b/alias/escape", ("sym", "../../outside"))],
        id="file-first-then-link-whose-real-landing-leaves",
    ),
]


@SEAMS
@pytest.mark.parametrize("members", ANCESTOR_ESCAPES)
def test_build_template_refuses_a_link_reached_through_an_ancestor_link_in_either_order(
    tmp_path, built_repo, monkeypatch, filter_support, members
):
    _assert_refused_on_seam(
        tmp_path, built_repo, monkeypatch, filter_support, _crafted_tar(members)
    )


# -- A2-A4: names and link targets that are absolute in some domain ----------

# Judged the same on every host: a Windows spelling is refused on POSIX too,
# where it would read as an odd but relative name. `{outside}` is the sentinel
# directory's own absolute path, filled in at run time.
ABSOLUTE_SPELLINGS = [
    pytest.param("{outside}/secret.txt", id="posix-absolute"),
    pytest.param("//server/share/secret.txt", id="posix-double-slash-root"),
    pytest.param("C:/outside/secret.txt", id="drive-absolute"),
    pytest.param("C:\\outside\\secret.txt", id="drive-absolute-backslash"),
    pytest.param("C:outside/secret.txt", id="drive-relative"),
    pytest.param("\\outside\\secret.txt", id="rooted-backslash"),
    pytest.param("\\\\server\\share\\secret.txt", id="unc"),
    pytest.param("\\\\?\\C:\\outside\\secret.txt", id="extended-prefix"),
    # Not only `C:`: any letter, either case, is a drive.
    pytest.param("D:/x", id="other-drive-absolute"),
    pytest.param("z:x", id="lowercase-drive-relative"),
    pytest.param("\\\\?\\D:\\x", id="extended-prefix-other-drive"),
    pytest.param("secret.txt:hidden", id="ntfs-named-stream"),
    pytest.param("pkg/secret.txt::$DATA", id="ntfs-default-stream"),
]


@SEAMS
@pytest.mark.parametrize("spelling", ABSOLUTE_SPELLINGS)
def test_build_template_refuses_a_member_named_absolute_in_any_domain(
    tmp_path, built_repo, monkeypatch, filter_support, spelling
):
    name = _outside_spelled(tmp_path, spelling)
    bundle = _crafted_tar([("pkg", DIRECTORY), (name, PAYLOAD)])
    _assert_refused_on_seam(tmp_path, built_repo, monkeypatch, filter_support, bundle)


@SEAMS
@pytest.mark.parametrize("spelling", ABSOLUTE_SPELLINGS)
def test_build_template_refuses_a_link_whose_target_is_absolute_in_any_domain(
    tmp_path, built_repo, monkeypatch, filter_support, spelling
):
    target = _outside_spelled(tmp_path, spelling)
    bundle = _crafted_tar([("pkg", DIRECTORY), ("pkg/link", ("sym", target))])
    _assert_refused_on_seam(tmp_path, built_repo, monkeypatch, filter_support, bundle)


# -- A5 and A12: two members that write one place -----------------------------

# Every pair here is judged on normalized names: `./`, `//` and a climb are
# spellings, and two names that differ only in case land on one file on a
# case-insensitive filesystem.
COLLISIONS = [
    pytest.param(
        [("pkg", DIRECTORY), ("pkg/a.txt", PAYLOAD), ("pkg/other.txt", OTHER),
         ("pkg/./a.txt", OTHER)],
        id="same-file-under-a-dot-spelling-not-adjacent",
    ),
    pytest.param(
        [("pkg", DIRECTORY), ("pkg/a.txt", PAYLOAD), ("pkg/../pkg/a.txt", OTHER)],
        id="same-file-under-a-climb-spelling",
    ),
    pytest.param([("x", PAYLOAD), ("x", DIRECTORY)], id="file-then-directory"),
    pytest.param([("x", DIRECTORY), ("x", PAYLOAD)], id="directory-then-file"),
    pytest.param([("x", PAYLOAD), ("x/y.txt", OTHER)], id="file-then-file-under-it"),
    pytest.param([("x/y.txt", OTHER), ("x", PAYLOAD)], id="file-under-it-then-file"),
    pytest.param(
        [("pkg", DIRECTORY), ("alias", ("sym", "pkg")),
         ("alias/a.txt", PAYLOAD), ("pkg/a.txt", OTHER)],
        id="two-files-at-one-landing-link-path-first",
    ),
    pytest.param(
        [("pkg", DIRECTORY), ("alias", ("sym", "pkg")),
         ("pkg/a.txt", OTHER), ("alias/a.txt", PAYLOAD)],
        id="two-files-at-one-landing-real-path-first",
    ),
    # The link sits below the root, then two links chain: a check that follows
    # only a first path segment, or only one hop, misses where these land.
    pytest.param(
        [("sub", DIRECTORY), ("pkg", DIRECTORY), ("sub/alias", ("sym", "../pkg")),
         ("sub/alias/a.txt", PAYLOAD), ("pkg/a.txt", OTHER)],
        id="two-files-at-one-landing-through-a-nested-link",
    ),
    pytest.param(
        [("pkg", DIRECTORY), ("a", ("sym", "b")), ("b", ("sym", "pkg")),
         ("a/a.txt", PAYLOAD), ("pkg/a.txt", OTHER)],
        id="two-files-at-one-landing-through-a-two-link-chain",
    ),
    pytest.param(
        [("Readme.md", PAYLOAD), ("other.txt", OTHER), ("README.md", OTHER)],
        id="case-only-file-names-not-adjacent",
    ),
    pytest.param(
        [("Pkg/a.txt", PAYLOAD), ("pkg/a.txt", OTHER)], id="case-only-directory-names"
    ),
    pytest.param(
        [("./Docs/a.txt", PAYLOAD), ("docs//A.txt", OTHER)],
        id="case-collision-only-after-normalizing",
    ),
    pytest.param(
        [("pkg//b.txt", PAYLOAD), ("./pkg/b.txt", OTHER)],
        id="duplicate-only-after-normalizing",
    ),
]


@SEAMS
@pytest.mark.parametrize("members", COLLISIONS)
def test_build_template_refuses_two_members_that_land_on_one_normalized_path(
    tmp_path, built_repo, monkeypatch, filter_support, members
):
    _assert_refused_on_seam(
        tmp_path, built_repo, monkeypatch, filter_support, _crafted_tar(members)
    )


# -- A6: members that are neither a file, a directory nor a symlink ----------


def _special(kind: bytes, linkname: str) -> tarfile.TarInfo:
    info = tarfile.TarInfo("pkg/special")
    info.type, info.linkname = kind, linkname
    if kind in (tarfile.CHRTYPE, tarfile.BLKTYPE):
        info.devmajor, info.devminor = 1, 3
    return info


SPECIAL_MEMBERS = [
    pytest.param(tarfile.LNKTYPE, "pkg/a.txt", id="hardlink-to-a-file-inside"),
    pytest.param(tarfile.LNKTYPE, "../outside/secret.txt", id="hardlink-to-a-file-outside"),
    pytest.param(tarfile.FIFOTYPE, "", id="fifo"),
    pytest.param(tarfile.CHRTYPE, "", id="character-device"),
    pytest.param(tarfile.BLKTYPE, "", id="block-device"),
]


@SEAMS
@pytest.mark.parametrize("kind, linkname", SPECIAL_MEMBERS)
def test_build_template_refuses_a_hardlink_fifo_or_device_member(
    tmp_path, built_repo, monkeypatch, filter_support, kind, linkname
):
    bundle = _appended(
        [("pkg", DIRECTORY), ("pkg/a.txt", PAYLOAD)], [(_special(kind, linkname), None)]
    )
    _assert_refused_on_seam(tmp_path, built_repo, monkeypatch, filter_support, bundle)


# -- A7: modes and owners the archive asks for ---------------------------------


def _owned_file(mode: int, uid: int, owner: str) -> tarfile.TarInfo:
    info = tarfile.TarInfo("pkg/tool")
    info.mode, info.uid, info.gid, info.uname, info.gname = mode, uid, uid, owner, owner
    return info


TOOL = b"#!/bin/sh\necho tool\n"
SPECIAL_BITS = stat.S_ISUID | stat.S_ISGID


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
    """The chown requests that name an owner other than the user running this."""
    return [(call, target, args) for call, target, args in requested
            if call.endswith("chown") and args[0] not in (-1, os.getuid())]


@SEAMS
@pytest.mark.parametrize(
    "mode",
    [
        pytest.param(0o4755, id="setuid"),
        pytest.param(0o2755, id="setgid"),
        pytest.param(0o6755, id="setuid-and-setgid"),
        # No special bit at all: the foreign owner has to be refused on its own.
        pytest.param(0o644, id="foreign-owner-alone"),
    ],
)
def test_build_template_never_applies_setuid_setgid_or_a_foreign_owner_from_the_archive(
    tmp_path, built_repo, monkeypatch, filter_support, mode
):
    _select_seam(monkeypatch, filter_support)
    repo = Path(built_repo["repo"])
    first = _task_start_commit(repo)
    outside = _outside_sentinel(tmp_path)
    before = _snapshot(outside)
    bundle = _appended([("pkg", DIRECTORY)], [(_owned_file(mode, 4242, "mallory"), TOOL)])
    _serve_archive(monkeypatch, bundle)
    dest = tmp_path / "template"
    requested = _record_mode_and_owner_requests(monkeypatch)

    try:
        trees.build_template(repo, first, dest)
    except trees.TreeError:
        # Refusing the archive is one way never to apply the bits: then nothing
        # of it was extracted.
        assert list(dest.glob("*")) == []
    else:
        status = (dest / "pkg" / "tool").lstat()
        assert not status.st_mode & SPECIAL_BITS, oct(status.st_mode)
        assert status.st_uid == os.getuid()
        assert status.st_gid == dest.stat().st_gid
        assert (dest / "pkg" / "tool").read_bytes() == TOOL
    asked_bits = [
        (call, target, oct(args[0]))
        for call, target, args in requested
        if call.endswith("chmod") and args[0] & SPECIAL_BITS
    ]
    assert asked_bits == [], "extraction asked the OS for setuid/setgid"
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
    _select_seam(monkeypatch, filter_support)
    repo = Path(built_repo["repo"])
    first = _task_start_commit(repo)
    outside = _outside_sentinel(tmp_path)
    before = _snapshot(outside)
    bundle = _appended([("pkg", DIRECTORY)], [(_owned_file(mode, 0, "root"), TOOL)])
    _serve_archive(monkeypatch, bundle)
    dest = tmp_path / "template"
    requested = _record_mode_and_owner_requests(monkeypatch)

    sha = trees.build_template(repo, first, dest)

    assert sha == trees.head_sha(dest)
    assert trees._git(dest, "status", "--porcelain") == ""
    assert trees._git(dest, "ls-files").splitlines() == ["pkg/tool"]
    status = (dest / "pkg" / "tool").lstat()
    assert stat.S_IMODE(status.st_mode) == kept, oct(status.st_mode)
    assert status.st_uid == os.getuid()
    assert (dest / "pkg" / "tool").read_bytes() == TOOL
    assert _chowns_to_another_owner(requested) == [], "extraction asked for the archive's owner"
    assert _snapshot(outside) == before


# -- the accept twin of every refusal above ----------------------------------

# Each member here shares a shape with a refused case and differs where it
# matters: `C` and `server` are plain directory names, not a drive or a share;
# `Readme.md` and `Readme.txt` differ in more than case; `./pkg/a.txt` is a
# spelling no other member shares; `alias -> pkg` carries `pkg/escape` with
# no link out of the tree behind it.
NEAR_MISSES = [
    ("pkg", DIRECTORY),
    ("./pkg/a.txt", PAYLOAD),
    ("pkg/b.txt", OTHER),
    ("Readme.md", PAYLOAD),
    ("Readme.txt", OTHER),
    ("C", DIRECTORY),
    ("C/outside", DIRECTORY),
    ("C/outside/secret.txt", PAYLOAD),
    ("server", DIRECTORY),
    ("server/share.txt", OTHER),
    ("link", ("sym", "C/outside/secret.txt")),
    ("alias", ("sym", "pkg")),
    ("pkg/escape", DIRECTORY),
    ("pkg/escape/secret.txt", OTHER),
]


@NEEDS_SYMLINKS
@SEAMS
def test_build_template_seals_members_that_only_resemble_the_refused_ones(
    tmp_path, built_repo, monkeypatch, filter_support
):
    _select_seam(monkeypatch, filter_support)
    repo = Path(built_repo["repo"])
    first = _task_start_commit(repo)
    outside = _outside_sentinel(tmp_path)
    before = _snapshot(outside)
    _serve_archive(monkeypatch, _crafted_tar(NEAR_MISSES))
    dest = tmp_path / "template"

    sha = trees.build_template(repo, first, dest)

    assert sha == trees.head_sha(dest)
    assert trees._git(dest, "status", "--porcelain") == ""
    assert sorted(trees._git(dest, "ls-files").splitlines()) == sorted([
        "pkg/a.txt", "pkg/b.txt", "Readme.md", "Readme.txt", "C/outside/secret.txt",
        "server/share.txt", "link", "alias", "pkg/escape/secret.txt",
    ])
    assert (dest / "pkg" / "a.txt").read_bytes() == b"pwned\n"
    assert (dest / "pkg" / "b.txt").read_bytes() == b"other\n"
    assert (dest / "Readme.md").read_bytes() == b"pwned\n"
    assert (dest / "Readme.txt").read_bytes() == b"other\n"
    assert (dest / "server" / "share.txt").read_bytes() == b"other\n"
    assert Path(os.readlink(dest / "link")).as_posix() == "C/outside/secret.txt"
    assert (dest / "link").read_bytes() == b"pwned\n"
    assert (dest / "alias" / "escape" / "secret.txt").read_bytes() == b"other\n"
    assert _snapshot(outside) == before


@SEAMS
def test_build_template_seals_a_real_git_archive_as_the_tree_before_the_task(
    tmp_path, built_repo, monkeypatch, filter_support
):
    # No crafted archive: what `git archive` really writes for a real repo. A
    # builder that refuses every archive it was not shown in a test fails here.
    _select_seam(monkeypatch, filter_support)
    repo = Path(built_repo["repo"])
    first = _task_start_commit(repo)
    outside = _outside_sentinel(tmp_path)
    before = _snapshot(outside)
    dest = tmp_path / "template"

    sha = trees.build_template(repo, first, dest)

    assert sha == trees.head_sha(dest)
    assert trees._git(dest, "status", "--porcelain") == ""
    # One tree id: the same paths, bytes and modes as the commit before `first`.
    assert trees._git(dest, "rev-parse", "HEAD^{tree}") == trees._git(
        repo, "rev-parse", "%s^^{tree}" % first
    )
    assert trees._git(dest, "ls-files") != ""
    assert _snapshot(outside) == before
