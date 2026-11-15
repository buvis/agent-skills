"""Tests for how eval_harness/trees.py types the symlinks it lays: a link is a
directory link exactly when where it lands is a directory.

Split out of test_eval_tree_links.py, which outgrew the size this project caps
a test file at. The archive builders, the template builders and the fixtures
stay spelled there and are imported here, so there is one spelling of each.
"""
import os
from pathlib import Path

import pytest

from eval_harness import trees

# `bare_ci` and `built_repo` are fixtures: pytest resolves them from this
# module's own namespace, so they have to be imported even though nothing here
# calls `bare_ci`.
from test_eval_tree_links import (
    DIRECTORY,
    NEEDS_SYMLINKS,
    PAYLOAD,
    _crafted_tar,
    _hide_data_filter,
    _lay_links,
    _serve_archive,
    _task_start_commit,
    _template_on_disk,
    bare_ci,
    built_repo,
)


# -- symlink typing ----------------------------------------------------------

# On Windows a symlink's file/directory type is fixed when it is created, and
# CPython types it as a directory only if told so or if the target already
# exists as one. These spy on what the code asks `os.symlink` for, so they
# catch a wrong type on every host, not only where the type is enforced.


def _record_symlinks(monkeypatch) -> list:
    """Spy on `os.symlink`: every call's (link name, target text, type flag)."""
    calls = []
    real = os.symlink

    def spy(target, path, target_is_directory=False, **kwargs):
        calls.append((Path(path).name, os.fspath(target), target_is_directory))
        real(target, path, target_is_directory=target_is_directory, **kwargs)

    monkeypatch.setattr(os, "symlink", spy)
    return calls


def _host_form(text: str) -> str:
    """Archive link text as it reaches `os.symlink`: host separators."""
    return text.replace("/", os.sep)


# (directory link, directory, file link, file, dangling link, dangling target).
# The second set flips which names carry a dot (a dotted directory, a dot-free
# file and dangling target) and shares no name with the first, so neither a
# type guessed from the target's spelling nor a list of known names passes.
LINKS_BESIDE_THEIR_TARGETS = [
    pytest.param(
        ("pkg-link", "pkg", "cfg-link", "secret.txt", "nowhere-link", "nowhere"),
        id="dot-free-directory-dotted-file",
    ),
    pytest.param(
        ("docs.link", "lib.d", "license", "LICENSE", "ghost", "gone.txt"),
        id="dotted-directory-dot-free-file",
    ),
]


@NEEDS_SYMLINKS
@pytest.mark.parametrize("names", LINKS_BESIDE_THEIR_TARGETS)
def test_build_template_types_a_link_as_a_directory_whatever_its_symlink_order(
    tmp_path, built_repo, monkeypatch, names
):
    # Every link sorts before what it names: laid in member order, no target
    # exists yet when its link is made. Only the link whose landing is a
    # directory member is typed as one; a link to a file member and a link to
    # no member at all are both file-typed.
    dir_link, directory, file_link, file, dangling_link, dangling_target = names
    file_path = f"{directory}/{file}"
    _hide_data_filter(monkeypatch)
    repo = Path(built_repo["repo"])
    first = _task_start_commit(repo)
    members = [
        (dir_link, ("sym", directory)),
        (file_link, ("sym", file_path)),
        (dangling_link, ("sym", dangling_target)),
        (directory, DIRECTORY),
        (file_path, PAYLOAD),
    ]
    _serve_archive(monkeypatch, _crafted_tar(members))
    calls = _record_symlinks(monkeypatch)
    dest = tmp_path / "template"

    trees.build_template(repo, first, dest)

    # One call per link, in archive order.
    assert calls == [
        (dir_link, directory, True),
        (file_link, _host_form(file_path), False),
        (dangling_link, dangling_target, False),
    ]
    assert (dest / dir_link / file).read_bytes() == b"pwned\n"
    assert (dest / file_link).read_bytes() == b"pwned\n"
    assert (dest / dangling_link).is_symlink()
    assert not (dest / dangling_link).exists()


# Two chains, every link ahead of where its chain lands: one ends at a
# directory (both its links typed as one), one at a file (both file-typed).
# The second archive lays each chain's links tail first, so a type read off
# whatever the previous link left on disk is wrong in one order or the other;
# the third renames the directory chain.
LINK_CHAINS = [
    pytest.param(
        [
            ("a", ("sym", "b")),
            ("b", ("sym", "c")),
            ("x", ("sym", "y")),
            ("y", ("sym", "file.txt")),
            ("c", DIRECTORY),
            ("file.txt", PAYLOAD),
        ],
        {"a": True, "b": True, "x": False, "y": False},
        id="head-before-tail",
    ),
    pytest.param(
        [
            ("b", ("sym", "c")),
            ("a", ("sym", "b")),
            ("y", ("sym", "file.txt")),
            ("x", ("sym", "y")),
            ("c", DIRECTORY),
            ("file.txt", PAYLOAD),
        ],
        {"a": True, "b": True, "x": False, "y": False},
        id="tail-before-head",
    ),
    pytest.param(
        [
            ("head", ("sym", "mid")),
            ("mid", ("sym", "tree")),
            ("x", ("sym", "y")),
            ("y", ("sym", "file.txt")),
            ("tree", DIRECTORY),
            ("file.txt", PAYLOAD),
        ],
        {"head": True, "mid": True, "x": False, "y": False},
        id="head-before-tail-other-names",
    ),
]


@NEEDS_SYMLINKS
@pytest.mark.parametrize("members, typed_as_directory", LINK_CHAINS)
def test_build_template_types_a_link_chain_through_directory_as_a_directory(
    tmp_path, built_repo, monkeypatch, members, typed_as_directory
):
    # `a -> b -> c`, `c` a directory, both links ahead of it: a landing worked
    # out from `a`'s own text alone sees `b`, not a directory, and types `a`
    # as a file. `x -> y -> file.txt` ends at a file, so neither is a
    # directory link however the chain is followed.
    _hide_data_filter(monkeypatch)
    repo = Path(built_repo["repo"])
    first = _task_start_commit(repo)
    _serve_archive(monkeypatch, _crafted_tar(members))
    calls = _record_symlinks(monkeypatch)
    dest = tmp_path / "template"

    trees.build_template(repo, first, dest)

    # One call per link, in archive order.
    assert calls == [
        (name, target, typed_as_directory[name])
        for name, (kind, target) in members
        if kind == "sym"
    ]
    for name, is_directory in typed_as_directory.items():
        assert (dest / name).is_dir() == is_directory, name
    assert (dest / "x").read_bytes() == b"pwned\n"


@NEEDS_SYMLINKS
def test_fresh_clone_links_typed_as_a_directory_where_the_template_s_target_is_one(
    tmp_path, monkeypatch
):
    template = _template_on_disk(tmp_path)
    # Each chain's tail is laid first so the template's own links are typed
    # right on Windows too. `a -> b -> pkg` and `z -> y -> pkg` run opposite
    # ways in name order: whichever order the clone lays links in, one chain's
    # head comes before its tail, so a type read off the clone's half-built
    # state (rather than the template's layout) gets that head wrong.
    links = {
        "pkg-link": "pkg",
        "b": "pkg",
        "a": "b",
        "y": "pkg",
        "z": "y",
        "calc-link": "calc.py",
        "nowhere-link": "nowhere",
    }
    typed_as_directory = {
        "pkg-link": True,
        "b": True,
        "a": True,
        "y": True,
        "z": True,
        "calc-link": False,
        "nowhere-link": False,
    }
    _lay_links(template, links)
    calls = _record_symlinks(monkeypatch)
    dest = tmp_path / "clone"

    trees.fresh_clone(template, dest)

    # The clone asks for the type itself, from the template's own layout,
    # rather than leaving it to whatever exists at the moment of the copy.
    assert sorted(calls) == sorted(
        (name, target, typed_as_directory[name]) for name, target in links.items()
    )
    # The directory the links run through is copied as a plain directory, and
    # every link stays a link.
    assert (dest / "pkg").is_dir() and not (dest / "pkg").is_symlink()
    for name in links:
        assert (dest / name).is_symlink(), name
    for name in ("pkg-link", "a", "z"):
        assert (dest / name / "nested.txt").read_bytes() == b"nested\n"
    assert (dest / "calc-link").read_bytes() == b"inside\n"
    assert not (dest / "nowhere-link").exists()


@NEEDS_SYMLINKS
def test_fresh_clone_writes_chain_link_text_in_host_separator_form(
    tmp_path, monkeypatch
):
    # `same`'s text holds a `/`: on Windows a link written with `/` does not
    # resolve through the chain, so the clone must spell it for the host.
    template = _template_on_disk(tmp_path)
    links = {"alias": ".", "same": "alias/calc.py"}
    _lay_links(template, links)
    calls = _record_symlinks(monkeypatch)
    dest = tmp_path / "clone"

    trees.fresh_clone(template, dest)

    # Exactly one call per link, typed from the template, text in host form:
    # no extra link planted anywhere, none typed wrong.
    assert sorted(calls) == sorted(
        [("alias", ".", True), ("same", _host_form("alias/calc.py"), False)]
    )
    for name in links:
        assert (dest / name).is_symlink(), name
    assert os.readlink(dest / "same") == _host_form("alias/calc.py")
    assert (dest / "same").read_bytes() == b"inside\n"
    # The rest of the template survives the clone.
    assert (dest / "calc.py").read_bytes() == b"inside\n"
    assert (dest / "pkg" / "nested.txt").read_bytes() == b"nested\n"
