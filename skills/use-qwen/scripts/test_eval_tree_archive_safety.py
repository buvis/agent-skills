"""The archive security matrix eval_harness/trees.py's build_template answers.

Rows A1-A7 and A12: what a crafted `git archive` tar may not do to the host,
whether or not this runtime's tarfile ships a `data_filter`. Every case runs on
both seams: the filter-present one this runtime takes, and a filter-absent one
that stands in for a Python older than 3.12, whose `extractall` knows no
`filter` keyword and applies the archive as written. Each case keeps a
sentinel directory beside the template and proves its bytes and modes are what
they were, so an escape is caught by what it did, not only by what was raised.

The archive builders and the sentinel come from test_eval_tree_links.py, so
there is one spelling of each. Row A7, modes and owners, lives in
test_eval_tree_archive_safety_modes.py.
"""
import io
import os
import stat
import tarfile
from datetime import datetime
from pathlib import Path

import pytest

from eval_harness import trees

# `bare_ci` and `built_repo` are fixtures: pytest resolves them from this
# module's own namespace, so they have to be imported even though nothing here
# calls them. `built_repo` itself depends on `bare_ci` by name, so removing
# the latter breaks fixture resolution even though no test parameter names it.
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


# Taken once, at import, so the stand-ins below reach the real methods even
# while `TarFile` itself carries them.
_REAL_EXTRACTALL = tarfile.TarFile.extractall
_REAL_EXTRACT = tarfile.TarFile.extract


def _before_data_filter(asked_filter: list):
    """`TarFile.extractall` and `extract` as Python shipped them before 3.12.

    Asked for a `filter`, each fails the way such a runtime fails, and the ask
    is recorded. Asked without one, it applies the archive as written - modes,
    links, owners and all - which is what a builder that leans on the
    runtime's own filter gets there. They replace the methods on the real
    `TarFile` class, so no subclass or unbound base method sidesteps them.
    """

    def refuse(call: str, kwargs: dict) -> None:
        if kwargs:
            asked_filter.append((call, sorted(kwargs)))
            raise TypeError("%s() got an unexpected keyword argument %r" % (call, next(iter(kwargs))))

    def extractall(self, path=".", members=None, *, numeric_owner=False, **kwargs):
        refuse("extractall", kwargs)
        _REAL_EXTRACTALL(
            self, path, members, numeric_owner=numeric_owner, filter=tarfile.fully_trusted_filter
        )

    def extract(self, member, path="", set_attrs=True, *, numeric_owner=False, **kwargs):
        refuse("extract", kwargs)
        _REAL_EXTRACT(
            self, member, path, set_attrs,
            numeric_owner=numeric_owner, filter=tarfile.fully_trusted_filter,
        )

    return extractall, extract


def _select_seam(monkeypatch, filter_support: str) -> list:
    """Leave the runtime's tarfile alone, or take `data_filter` and `filter=` away.

    Returns the list of every `filter=` ask the no-filter seam refused; it
    stays empty on the filter-present seam.
    """
    asked_filter = []
    if filter_support == "with-data-filter":
        return asked_filter
    _hide_data_filter(monkeypatch)
    extractall, extract = _before_data_filter(asked_filter)
    monkeypatch.setattr(tarfile.TarFile, "extractall", extractall)
    monkeypatch.setattr(tarfile.TarFile, "extract", extract)
    return asked_filter


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
    # The escaping link's parent is reached through two links, `x/y/a -> b`
    # and `x/y/b -> ../../pkg`. By its own text `x/y/a/escape` reads as
    # `x/outside`, and one hop of its parent still leaves it at `x/outside`;
    # only the whole chain puts it at `pkg/escape`, where it climbs out.
    pytest.param(
        [("x", DIRECTORY), ("x/y", DIRECTORY), ("pkg", DIRECTORY),
         ("x/y/a", ("sym", "b")), ("x/y/b", ("sym", "../../pkg")),
         ("x/y/a/escape", ("sym", "../../outside")), ("pkg/escape/secret.txt", PAYLOAD)],
        id="escaping-link-under-a-two-link-chain-then-file",
    ),
    pytest.param(
        [("x", DIRECTORY), ("x/y", DIRECTORY), ("pkg", DIRECTORY),
         ("x/y/a", ("sym", "b")), ("x/y/b", ("sym", "../../pkg")),
         ("pkg/escape/secret.txt", PAYLOAD), ("x/y/a/escape", ("sym", "../../outside"))],
        id="file-then-escaping-link-under-a-two-link-chain",
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
    # A stream colon in a directory component, not the last one.
    pytest.param("pkg:s/a.txt", id="ntfs-stream-in-a-directory-component"),
    # No drive, no leading separator: only `\` marks this climb as one.
    pytest.param("..\\..\\outside\\secret.txt", id="backslash-relative-climb"),
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
    # The file sits at a grandparent, not the direct parent, of the other.
    pytest.param([("x", PAYLOAD), ("x/y/z.txt", OTHER)], id="file-then-file-two-levels-under-it"),
    pytest.param([("x/y/z.txt", OTHER), ("x", PAYLOAD)], id="file-two-levels-under-it-then-file"),
    # A link and a file at one landing: links are members that land too.
    pytest.param(
        [("pkg", DIRECTORY), ("alias", ("sym", "pkg")),
         ("pkg/a.txt", PAYLOAD), ("alias/a.txt", ("sym", "b.txt"))],
        id="file-then-link-at-one-landing",
    ),
    pytest.param(
        [("pkg", DIRECTORY), ("alias", ("sym", "pkg")),
         ("alias/a.txt", ("sym", "b.txt")), ("pkg/a.txt", PAYLOAD)],
        id="link-then-file-at-one-landing",
    ),
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


# -- valid-input controls: what a sound archive must still seal as written ----

# Every byte value once: NUL, a lone 0xff and broken UTF-8 sequences included,
# so a builder that decodes or re-encodes a blob anywhere cannot keep it.
BINARY = bytes(range(256))
OTHER_BINARY = b"\x00\xff\xfe\xc3\x28\r\n\x80"
CRLF = b"one\r\ntwo\r\n"
# CRLF, a bare LF and a lone CR side by side: normalizing any one of them shows.
MIXED_ENDINGS = b"crlf\r\nlf\nlone\rend"
LF = b"one\ntwo\n"


def _file(name: str, data: bytes, mode: int = 0o644) -> tuple:
    """A (TarInfo, bytes) regular file for `_appended`, with the mode given."""
    info = tarfile.TarInfo(name)
    info.mode = mode
    return info, data


def _sealed_modes(dest: Path) -> dict:
    """Each path the sealed commit holds, with the git mode it was recorded under."""
    modes = {}
    # Unquoted, so a non-ASCII path reads back as the name it was given.
    for line in trees._git(dest, "-c", "core.quotePath=false", "ls-files", "-s").splitlines():
        meta, path = line.split("\t", 1)
        modes[path] = meta.split()[0]
    return modes


def _sealed_blob(dest: Path, path: str) -> bytes:
    """The bytes the sealed commit recorded at `path`, read from git, not the disk."""
    return trees._git_bytes(dest, "cat-file", "blob", "HEAD:%s" % path)


def _seal_control(tmp_path, built_repo, monkeypatch, filter_support, bundle) -> Path:
    """Seal `bundle` on the seam asked for; answer the template, proven sealed."""
    _select_seam(monkeypatch, filter_support)
    repo = Path(built_repo["repo"])
    first = _task_start_commit(repo)
    outside = _outside_sentinel(tmp_path)
    before = _snapshot(outside)
    _serve_archive(monkeypatch, bundle)
    dest = tmp_path / "template"

    sha = trees.build_template(repo, first, dest)

    assert sha == trees.head_sha(dest)
    assert trees._git(dest, "status", "--porcelain") == ""
    assert _snapshot(outside) == before
    return dest


@SEAMS
def test_control_build_template_keeps_binary_and_crlf_blobs_byte_for_byte(
    tmp_path, built_repo, monkeypatch, filter_support
):
    blobs = {
        "data/blob.bin": BINARY,
        "data/other.bin": OTHER_BINARY,
        # Past 64 KiB: a copy through a fixed small buffer comes up short.
        "data/large.bin": BINARY * 257,
        "text/crlf.txt": CRLF,
        "text/mixed.txt": MIXED_ENDINGS,
        "text/lf.txt": LF,
    }
    bundle = _crafted_tar(
        [("data", DIRECTORY), ("text", DIRECTORY)]
        + [(path, ("file", data)) for path, data in blobs.items()]
    )

    dest = _seal_control(tmp_path, built_repo, monkeypatch, filter_support, bundle)

    assert sorted(_sealed_modes(dest)) == sorted(blobs)
    for path, data in blobs.items():
        assert (dest / path).read_bytes() == data, path
        assert _sealed_blob(dest, path) == data, path


@SEAMS
def test_control_build_template_seals_every_file_whatever_its_name_depth_or_size(
    tmp_path, built_repo, monkeypatch, filter_support
):
    # Each one is a file a filter could single out: hidden, deep, empty, a
    # non-ASCII name, a space in the name. None may be left out of the seal.
    files = {
        ".hidden": b"hidden\n",
        "pkg/.gitignore": b"*.log\n",
        "a/b/c/d.txt": b"deep\n",
        "pkg/empty.txt": b"",
        "naïve.txt": b"accented\n",
        "with space.txt": b"spaced\n",
    }
    bundle = _crafted_tar(
        [(name, DIRECTORY) for name in ("pkg", "a", "a/b", "a/b/c")]
        + [(path, ("file", data)) for path, data in files.items()]
    )

    dest = _seal_control(tmp_path, built_repo, monkeypatch, filter_support, bundle)

    assert _sealed_modes(dest) == dict.fromkeys(files, "100644")
    for path, data in files.items():
        assert (dest / path).read_bytes() == data, path
        assert _sealed_blob(dest, path) == data, path


@SEAMS
def test_control_build_template_keeps_the_executable_bit_and_only_where_it_was_set(
    tmp_path, built_repo, monkeypatch, filter_support
):
    # Two files of one shape, one executable and one not: a builder that sets
    # or drops the bit on every file gets one of the pair wrong.
    # A second pair sets the bit against the name: a guess from a dot in the
    # name, rather than from the archive's mode, gets this pair wrong.
    files = {
        "bin/run": (b"#!/bin/sh\necho run\n", 0o755),
        "bin/run.txt": (b"#!/bin/sh\necho text\n", 0o644),
        "bin/tool.sh": (b"#!/bin/sh\necho tool\n", 0o755),
        "bin/README": (b"read me\n", 0o644),
    }
    bundle = _appended(
        [("bin", DIRECTORY)],
        [_file(path, data, mode) for path, (data, mode) in files.items()],
    )

    dest = _seal_control(tmp_path, built_repo, monkeypatch, filter_support, bundle)

    assert _sealed_modes(dest) == {
        "bin/run": "100755", "bin/run.txt": "100644",
        "bin/tool.sh": "100755", "bin/README": "100644",
    }
    for path, (data, mode) in files.items():
        executable = bool((dest / path).lstat().st_mode & stat.S_IXUSR)
        assert executable == bool(mode & stat.S_IXUSR), path
        assert (dest / path).read_bytes() == data, path


@SEAMS
def test_executable_bit_survives_a_seal_where_git_ignores_the_filesystem_mode(
    tmp_path, built_repo, monkeypatch, filter_support
):
    # Git for Windows sets core.filemode=false: `git add -A` then records every
    # new file as 100644, whatever landed on disk. The sealed mode must come
    # from the archive, not from what the staging filesystem reported.
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.filemode")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "false")
    files = {
        "bin/run": (b"#!/bin/sh\necho run\n", 0o755),
        "bin/README": (b"read me\n", 0o644),
    }
    bundle = _appended(
        [("bin", DIRECTORY)],
        [_file(path, data, mode) for path, (data, mode) in files.items()],
    )

    dest = _seal_control(tmp_path, built_repo, monkeypatch, filter_support, bundle)

    assert _sealed_modes(dest) == {"bin/run": "100755", "bin/README": "100644"}


# Links that stay inside the tree, by kind. A dangling link names a path the
# tree does not hold; it is still inside, so it is sealed as written.
SAFE_LINKS = [
    ("pkg", DIRECTORY),
    ("pkg/a.txt", PAYLOAD),
    ("pkg/b.txt", OTHER),
    ("file-link", ("sym", "pkg/a.txt")),
    ("dir-link", ("sym", "pkg")),
    ("dangling-link", ("sym", "pkg/missing.txt")),
    ("pkg/up-link", ("sym", "../pkg/b.txt")),
]


@NEEDS_SYMLINKS
@SEAMS
def test_control_build_template_seals_file_directory_and_dangling_links_inside_the_tree(
    tmp_path, built_repo, monkeypatch, filter_support
):
    dest = _seal_control(
        tmp_path, built_repo, monkeypatch, filter_support, _crafted_tar(SAFE_LINKS)
    )

    assert _sealed_modes(dest) == {
        "pkg/a.txt": "100644", "pkg/b.txt": "100644", "file-link": "120000",
        "dir-link": "120000", "dangling-link": "120000", "pkg/up-link": "120000",
    }
    # The link text is what is sealed, never the bytes it reaches.
    assert _sealed_blob(dest, "file-link") == b"pkg/a.txt"
    assert _sealed_blob(dest, "dangling-link") == b"pkg/missing.txt"
    assert Path(os.readlink(dest / "dir-link")).as_posix() == "pkg"
    assert (dest / "file-link").read_bytes() == b"pwned\n"
    assert (dest / "pkg" / "up-link").read_bytes() == b"other\n"
    assert (dest / "dir-link" / "a.txt").read_bytes() == b"pwned\n"
    assert (dest / "dir-link" / "b.txt").read_bytes() == b"other\n"
    assert (dest / "dangling-link").is_symlink()
    assert not (dest / "dangling-link").exists()


# Chains of links that end inside the tree: at the root, and below it. Each
# case lists what must read through the chain and the text each link keeps.
LINK_CHAINS = [
    pytest.param(
        [("pkg", DIRECTORY), ("pkg/a.txt", PAYLOAD), ("pkg/b.txt", OTHER),
         ("a", ("sym", "b")), ("b", ("sym", "pkg")),
         ("c", ("sym", "d")), ("d", ("sym", "pkg/b.txt"))],
        {"a/a.txt": b"pwned\n", "a/b.txt": b"other\n", "c": b"other\n"},
        {"a": "b", "b": "pkg", "c": "d", "d": "pkg/b.txt"},
        id="root-chain",
    ),
    pytest.param(
        [("pkg", DIRECTORY), ("pkg/a.txt", PAYLOAD), ("pkg/b.txt", OTHER),
         ("sub", DIRECTORY), ("sub/x", ("sym", "y")), ("sub/y", ("sym", "../pkg")),
         ("sub/f", ("sym", "x/a.txt"))],
        {"sub/x/a.txt": b"pwned\n", "sub/x/b.txt": b"other\n", "sub/f": b"pwned\n"},
        {"sub/x": "y", "sub/y": "../pkg", "sub/f": "x/a.txt"},
        id="subdirectory-chain",
    ),
]


@NEEDS_SYMLINKS
@SEAMS
@pytest.mark.parametrize("members, reads, texts", LINK_CHAINS)
def test_control_build_template_seals_a_link_chain_that_ends_inside_the_tree(
    tmp_path, built_repo, monkeypatch, filter_support, members, reads, texts
):
    dest = _seal_control(
        tmp_path, built_repo, monkeypatch, filter_support, _crafted_tar(members)
    )

    for path, data in reads.items():
        assert (dest / path).read_bytes() == data, path
    for path, text in texts.items():
        assert Path(os.readlink(dest / path)).as_posix() == text, path
        assert _sealed_blob(dest, path) == text.encode(), path
    assert sorted(_sealed_modes(dest)) == sorted(["pkg/a.txt", "pkg/b.txt", *texts])


def _determinism_bundle(blob: bytes) -> bytes:
    return _appended(
        [("pkg", DIRECTORY), ("pkg/crlf.txt", ("file", CRLF))],
        [_file("pkg/blob.bin", blob), _file("pkg/run", b"#!/bin/sh\n", 0o755)],
    )


@SEAMS
def test_control_build_template_seals_identical_input_to_one_sha_and_changed_input_to_another(
    tmp_path, built_repo, monkeypatch, filter_support
):
    _select_seam(monkeypatch, filter_support)
    repo = Path(built_repo["repo"])
    first = _task_start_commit(repo)
    outside = _outside_sentinel(tmp_path)
    before = _snapshot(outside)
    shas = []
    # Each run sees a different clock in the environment: a seal dated by it,
    # rather than by the tree alone, answers a different sha each time.
    runs = [("one", BINARY, "2011-01-01T00:00:00+00:00"),
            ("two", BINARY, "2022-02-02T00:00:00+00:00"),
            ("changed", OTHER_BINARY, "2011-01-01T00:00:00+00:00")]
    for name, blob, date in runs:
        monkeypatch.setenv("GIT_AUTHOR_DATE", date)
        monkeypatch.setenv("GIT_COMMITTER_DATE", date)
        _serve_archive(monkeypatch, _determinism_bundle(blob))
        dest = tmp_path / name
        sha = trees.build_template(repo, first, dest)
        assert sha == trees.head_sha(dest)
        shas.append(sha)

    assert shas[0] == shas[1]
    assert shas[2] != shas[0]
    # Dated by the fixed constant itself: a seal dated by the wall clock can
    # still answer one sha twice within a run, but never this date.
    # Compared as instants: git spells UTC `Z` where SEAL_DATE spells `+00:00`.
    sealed = int(datetime.fromisoformat(trees.SEAL_DATE).timestamp())
    for name, _, _ in runs:
        dates = trees._git(tmp_path / name, "log", "-1", "--format=%at%n%ct")
        assert dates == "%d\n%d" % (sealed, sealed), name
    assert _snapshot(outside) == before
