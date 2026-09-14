"""Tests for the symlink chains eval_harness/trees.py vets: a link is contained
by where it resolves to, hop by hop, not by how its target text reads.

Split out of test_eval_tree_state.py, which already stands at the size this
project caps a test file at. That file keeps the single-hop cases (an absolute
target, a `../` target, a plain alias to a file); this one holds every case
where the escape, or the innocence, takes more than one link to see. The
helpers and the capability guard are spelled there and imported here, so there
is one spelling of each.
"""
import hashlib
import os
from pathlib import Path

import pytest

from eval_harness import trees

# `bare_ci`, `built_repo` and `tree_and_outside` are fixtures: pytest resolves
# them from this module's own namespace, so they have to be imported even
# though nothing here calls them.
from eval_harness_fixture_helpers import _git, bare_ci, built_repo
from test_eval_tree_state import (
    IDENTITY,
    NEEDS_SYMLINKS,
    _commit_symlink,
    _task_start_commit,
    tree_and_outside,
)

# Every chain here reads as inside the tree once its text is normalised: an
# `alias/..` collapses to the root, a `sub/alias/..` to `sub`. Only following
# each link to where it lands shows the last hop stepping past the root.
ESCAPING_CHAINS = [
    pytest.param(
        {"alias": ".", "escape": "alias/../outside"},
        id="two-hops-back-out-through-a-link-to-the-root",
    ),
    pytest.param(
        {"a": "b", "b": "..", "c": "a/x"},
        id="three-hops-through-a-link-to-a-link",
    ),
    # No hop names `..` on its own: only the whole chain, followed, leaves.
    pytest.param(
        {"a": "b", "b": ".", "c": "a/../outside"},
        id="three-hops-back-out-through-two-links-to-the-root",
    ),
    pytest.param(
        {"sub/alias": "..", "escape": "sub/alias/../outside"},
        id="back-out-through-a-link-in-a-subdirectory",
    ),
    # Deep enough that a resolver which stops counting after a few hops, and
    # waves through whatever it did not finish following, waves this through.
    pytest.param(
        {
            "a": "b",
            "b": "c",
            "c": "d",
            "d": "e",
            "e": "f",
            "f": "g",
            "g": ".",
            "escape": "a/../outside",
        },
        id="eight-hops-back-out-through-a-chain-of-links-to-the-root",
    ),
]

# Chains whose every hop stays inside, and the file the last hop lands on: a
# fix that refused a link because its target is itself a link, or names `..`
# at all, would refuse these too.
INSIDE_CHAINS = [
    pytest.param(
        {"alias": ".", "same": "alias/{impl}"},
        "{impl}",
        id="through-a-link-to-the-root",
    ),
    # The names the escaping chains use, in a chain that stays inside: a check
    # keyed on what a link is called, rather than where it lands, refuses this
    # legal tree.
    pytest.param(
        {"escape": ".", "a": "escape/pkg", "b": "a/nested.txt", "c": "b"},
        "pkg/nested.txt",
        id="under-the-names-the-escaping-chains-use",
    ),
    pytest.param(
        {"pkg-link": "pkg", "nested": "pkg-link/nested.txt"},
        "pkg/nested.txt",
        id="through-a-link-to-a-subdirectory",
    ),
    pytest.param(
        {"alias.py": "{impl}", "twice": "alias.py"},
        "{impl}",
        id="a-link-to-a-link-to-a-file",
    ),
    # A `..` in the text that lands inside: `pkg/up` climbs one level, which is
    # the root, and the chain through it ends on the file. A check that refuses
    # any link whose text names `..` refuses this legal tree.
    pytest.param(
        {"pkg/up": "..", "via": "pkg/up/{impl}"},
        "{impl}",
        id="through-a-link-in-a-subdirectory-that-climbs-back-to-the-root",
    ),
]

# Nothing stands where these point, but where they point is inside the tree.
DANGLING_LINKS = [
    pytest.param({"later": "not-created-yet.txt"}, id="a-file-not-created-yet"),
    pytest.param({"deep": "pkg/not-there/either"}, id="under-a-directory-not-there"),
]

# Each resolves to nowhere. The pair is the shape a text comparison of two
# links catches; the ring and the link to itself under a subdirectory are what
# a resolver has to follow, hop by hop and relative to the link's own
# directory, to notice.
CYCLES = [
    pytest.param({"a": "b", "b": "a"}, id="a-pair"),
    pytest.param({"a": "b", "b": "c", "c": "a"}, id="a-ring-of-three"),
    pytest.param({"sub/a": "a"}, id="a-link-to-itself-under-a-subdirectory"),
]


def _spelled(links: dict, impl: str) -> dict:
    """The link table with `{impl}` filled in with the fixture's impl path."""
    return {name: target.format(impl=impl) for name, target in links.items()}


def _lay_links(root: Path, links: dict) -> None:
    """Write each `name -> target` link under `root`, target text as given."""
    for name, target in links.items():
        where = root / name
        where.parent.mkdir(parents=True, exist_ok=True)
        os.symlink(target, where)


def _link_text(where: Path) -> str:
    return Path(os.readlink(where)).as_posix()


def _commit_file(repo: Path, relpath: str, payload: bytes) -> None:
    """Commit one regular file at `relpath`, parents made as needed."""
    where = repo / relpath
    where.parent.mkdir(parents=True, exist_ok=True)
    where.write_bytes(payload)
    _git(repo, "add", relpath)
    _git(repo, *IDENTITY, "commit", "-m", f"add {relpath}")


def _commit_links(repo: Path, links: dict) -> str:
    """Commit every link through git, then the task's first commit after them."""
    for name, target in links.items():
        _commit_symlink(repo, name, target)
    return _task_start_commit(repo)


def _template_on_disk(tmp_path: Path) -> Path:
    """A template laid out by hand: files and directories, no `.git`.

    `fresh_clone` only walks and copies, so this is all it needs. Nothing stands
    between the links a case writes here and the call: a template that went
    through `build_template` (or through tar, whose data filter rewrites link
    text on extraction) could hide an escape at that layer.
    """
    template = tmp_path / "template"
    (template / "pkg").mkdir(parents=True)
    (template / "calc.py").write_bytes(b"inside\n")
    (template / "pkg" / "nested.txt").write_bytes(b"nested\n")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "secret.txt").write_bytes(b"outside\n")
    return template


# -- build_template --------------------------------------------------------


@pytest.mark.parametrize("links", ESCAPING_CHAINS)
def test_build_template_refuses_a_link_chain_that_resolves_outside_the_tree(
    tmp_path, built_repo, links
):
    repo = Path(built_repo["repo"])
    first = _commit_links(repo, links)
    dest = tmp_path / "template"

    with pytest.raises(trees.TreeError):
        trees.build_template(repo, first, dest)

    # Refused outright: no half-built template that a later clone would take for
    # a sealed one. Nothing of the tree was extracted, not only no commit (a
    # missing `dest` globs to nothing too).
    assert list(dest.glob("*")) == []


@pytest.mark.parametrize("links", CYCLES)
def test_build_template_refuses_a_link_cycle_with_a_tree_error(tmp_path, built_repo, links):
    repo = Path(built_repo["repo"])
    first = _commit_links(repo, links)
    dest = tmp_path / "template"

    # A cycle resolves to nowhere. It is refused the way an escape is, not by
    # looping until the interpreter gives up or the OS reports too many links.
    with pytest.raises(trees.TreeError):
        trees.build_template(repo, first, dest)

    assert list(dest.glob("*")) == []


@NEEDS_SYMLINKS
@pytest.mark.parametrize("links, lands_on", INSIDE_CHAINS)
def test_build_template_seals_a_link_chain_that_stays_inside_the_tree(
    tmp_path, built_repo, links, lands_on
):
    repo = Path(built_repo["repo"])
    _commit_file(repo, "pkg/nested.txt", b"nested\n")
    spelled = _spelled(links, built_repo["impl"])
    first = _commit_links(repo, spelled)
    dest = tmp_path / "template"

    trees.build_template(repo, first, dest)

    # Sealed as the links they are, text as written: a builder that resolved a
    # chain into a copy, or rewrote its text, seals a different tree.
    for name, target in spelled.items():
        assert (dest / name).is_symlink(), name
        assert _link_text(dest / name) == target
    # And the chain still reaches the file it aliases.
    last = list(spelled)[-1]
    landing = dest / lands_on.format(impl=built_repo["impl"])
    assert (dest / last).read_bytes() == landing.read_bytes()


@NEEDS_SYMLINKS
@pytest.mark.parametrize("links", DANGLING_LINKS)
def test_build_template_seals_a_dangling_link_whose_target_stays_inside(
    tmp_path, built_repo, links
):
    repo = Path(built_repo["repo"])
    first = _commit_links(repo, links)
    dest = tmp_path / "template"

    trees.build_template(repo, first, dest)

    # Containment is about where a link points, and this one points inside a
    # tree that has not filled that spot yet. Refusing it because nothing is
    # there would refuse a legal tree.
    for name, target in links.items():
        assert (dest / name).is_symlink(), name
        assert not (dest / name).exists()
        assert _link_text(dest / name) == target


# -- fresh_clone -----------------------------------------------------------


@NEEDS_SYMLINKS
@pytest.mark.parametrize("links", ESCAPING_CHAINS)
def test_fresh_clone_refuses_a_link_chain_that_resolves_outside_the_template(
    tmp_path, links
):
    template = _template_on_disk(tmp_path)
    _lay_links(template, links)
    dest = tmp_path / "clone"

    with pytest.raises(trees.TreeError):
        trees.fresh_clone(template, dest)

    # Refused before copying: nothing of the template reached the clone.
    assert not (dest / "calc.py").exists()


@NEEDS_SYMLINKS
@pytest.mark.parametrize("links", CYCLES)
def test_fresh_clone_refuses_a_link_cycle_with_a_tree_error(tmp_path, links):
    template = _template_on_disk(tmp_path)
    _lay_links(template, links)

    with pytest.raises(trees.TreeError):
        trees.fresh_clone(template, tmp_path / "clone")


@NEEDS_SYMLINKS
@pytest.mark.parametrize("links, lands_on", INSIDE_CHAINS)
def test_fresh_clone_copies_a_link_chain_that_stays_inside_the_template(
    tmp_path, links, lands_on
):
    template = _template_on_disk(tmp_path)
    spelled = _spelled(links, "calc.py")
    _lay_links(template, spelled)
    dest = tmp_path / "clone"

    trees.fresh_clone(template, dest)

    for name, target in spelled.items():
        assert (dest / name).is_symlink(), name
        assert _link_text(dest / name) == target
    # The chain still lands on the file it aliases, in the clone as in the
    # template.
    last = list(spelled)[-1]
    landing = template / lands_on.format(impl="calc.py")
    assert (dest / last).read_bytes() == landing.read_bytes()


@NEEDS_SYMLINKS
@pytest.mark.parametrize("links", DANGLING_LINKS)
def test_fresh_clone_copies_a_dangling_link_whose_target_stays_inside(tmp_path, links):
    template = _template_on_disk(tmp_path)
    _lay_links(template, links)
    dest = tmp_path / "clone"

    trees.fresh_clone(template, dest)

    for name, target in links.items():
        assert (dest / name).is_symlink(), name
        assert not (dest / name).exists()
        assert _link_text(dest / name) == target


# -- hash_paths ------------------------------------------------------------


@NEEDS_SYMLINKS
@pytest.mark.parametrize(
    "links, listed",
    [
        ({"escape": "../outside/secret.txt"}, "escape"),
        ({"alias": ".", "escape": "alias/../outside/secret.txt"}, "escape"),
        ({"vault": "../outside"}, "vault/secret.txt"),
        (
            {"a": "b", "b": "c", "c": "d", "d": "e", "e": ".", "escape": "a/../outside/secret.txt"},
            "escape",
        ),
    ],
    ids=[
        "a-link-out-of-the-tree",
        "two-hops-out-through-a-link-to-the-root",
        "a-path-through-a-link-to-an-outside-directory",
        "six-hops-out-through-a-chain-of-links-to-the-root",
    ],
)
def test_hash_paths_refuses_a_listed_path_that_resolves_outside_the_root(
    tree_and_outside, links, listed
):
    root, outside = tree_and_outside
    _lay_links(root, links)
    assert (outside / "secret.txt").read_bytes() == b"outside\n"

    # Refused, not hashed: a digest of the outside file is a record of bytes
    # the tree never held, and reading them is the leak.
    with pytest.raises(trees.TreeError):
        trees.hash_paths(root, [listed])


@NEEDS_SYMLINKS
@pytest.mark.parametrize("through", ["a-file", "a-directory"])
def test_hash_paths_refuses_a_link_with_an_absolute_target_before_reading_it(
    tree_and_outside, through
):
    root, outside = tree_and_outside
    # Spelled at run time, and with no `..` in it: a guard that looks for a
    # climb in the link text has nothing to find here.
    if through == "a-file":
        _lay_links(root, {"escape": str(outside / "secret.txt")})
        listed = "escape"
    else:
        _lay_links(root, {"vault": str(outside)})
        listed = "vault/secret.txt"
    assert (outside / "secret.txt").read_bytes() == b"outside\n"
    # Unreadable from here on: a guard that reads the bytes before deciding
    # raises PermissionError instead of the refusal, and a guard that never
    # decides hashes nothing either way.
    (outside / "secret.txt").chmod(0o000)
    try:
        with pytest.raises(trees.TreeError):
            trees.hash_paths(root, [listed])
    finally:
        (outside / "secret.txt").chmod(0o644)


@NEEDS_SYMLINKS
def test_hash_paths_still_hashes_the_tree_s_own_files_beside_a_link_that_leaves_it(
    tree_and_outside,
):
    root, _ = tree_and_outside
    _lay_links(root, {"escape": "../outside/secret.txt", "alias": ".", "same": "alias/passwd"})
    inside = hashlib.sha256(b"inside\n").hexdigest()

    hashes = trees.hash_paths(root, ["passwd", "pkg/calc.py", "same"])

    # The escaping link stands in the tree but is not listed: what is refused
    # is reading through it, not the tree it sits in. And a chain that lands
    # inside is still followed to the bytes it reaches.
    assert hashes == {"passwd": inside, "pkg/calc.py": inside, "same": inside}


@NEEDS_SYMLINKS
def test_hash_paths_hashes_a_listed_link_by_where_it_lands_not_by_what_it_is_called(
    tree_and_outside,
):
    root, _ = tree_and_outside
    # The same link names, and the same listed paths, as the refused cases
    # above; only where the links land differs.
    _lay_links(root, {"escape": "passwd", "vault": "pkg"})
    inside = hashlib.sha256(b"inside\n").hexdigest()

    hashes = trees.hash_paths(root, ["escape", "vault/secret.txt"])

    # Where a path lands is the whole of the decision: a check keyed on the
    # spelling of a name refuses a tree's own files.
    assert hashes == {"escape": inside, "vault/secret.txt": inside}
