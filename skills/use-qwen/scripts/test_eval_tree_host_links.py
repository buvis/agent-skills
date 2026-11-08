"""Link text read back from disk in host-native form, for eval_harness/trees.py.

On Windows a link is written with `\\` separators and `os.readlink` answers
`pkg\\a.txt`. `fresh_clone` and `contained` must take that text as the host
spells it, and still refuse every form that leaves the tree.

Windows is simulated on any host: `trees._HOST_SEP` names the separator link
text uses here, and `os.readlink` answers each fixture link's real text with
`/` turned into `\\`. Split from test_eval_tree_state.py, which stands near the
size this project caps a test file at; the template and link builders are
test_eval_tree_links.py's, so there is one spelling of each.
"""
import os
from pathlib import Path

import pytest

from eval_harness import trees
from test_eval_tree_links import _extended_prefix_stripped, _lay_links, _template_on_disk

ALPHA = b"alpha\n"
IN_DIR = b"in dir\n"


def _simulate_windows_link_text(monkeypatch) -> None:
    """Make this host answer link text the way Windows does: `\\`-separated."""
    real = os.readlink

    def host_native(path, *args, **kwargs):
        text = real(path, *args, **kwargs)
        return text.replace(b"/", b"\\") if isinstance(text, bytes) else text.replace("/", "\\")

    # raising=False: the constant is this change's contract, and a tree that
    # lacks it must fail on the link text, not on the patch.
    monkeypatch.setattr(trees, "_HOST_SEP", "\\", raising=False)
    monkeypatch.setattr(os, "readlink", host_native)


def _template_with_targets(tmp_path: Path) -> Path:
    template = _template_on_disk(tmp_path)
    (template / "pkg" / "a.txt").write_bytes(ALPHA)
    (template / "dir").mkdir()
    (template / "dir" / "f.txt").write_bytes(IN_DIR)
    return template


# Tail before head, so each link is typed right on Windows too. `pkg/up` climbs
# one level and stays inside: the near miss of the refused `..\..\outside`.
INSIDE_LINKS = {"link": "pkg/a.txt", "b": "dir", "a": "b", "pkg/up": "../dir"}


def test_fresh_clone_and_contained_accept_backslash_link_text_on_a_backslash_host(
    tmp_path, monkeypatch
):
    template = _template_with_targets(tmp_path)
    _lay_links(template, INSIDE_LINKS)
    clone = tmp_path / "clone"

    with monkeypatch.context() as simulated:
        _simulate_windows_link_text(simulated)
        # The fixture itself: what the call reads back is the host-native text.
        assert os.readlink(template / "link") == "pkg\\a.txt"
        assert os.readlink(template / "pkg" / "up") == "..\\dir"
        trees.fresh_clone(template, clone)
        landed = Path(trees.contained(clone, "link"))
        through_chain = Path(trees.contained(clone, "a/f.txt"))
        climbed = Path(trees.contained(clone, "pkg/up/f.txt"))

    assert landed == clone / "pkg" / "a.txt"
    assert landed.is_relative_to(clone)
    assert through_chain.resolve() == (clone / "dir" / "f.txt").resolve()
    assert climbed.resolve() == (clone / "dir" / "f.txt").resolve()
    for name in INSIDE_LINKS:
        assert (clone / name).is_symlink(), name
    # The clone's links land on the same files the template's do.
    assert (clone / "link").read_bytes() == ALPHA
    assert (clone / "a" / "f.txt").read_bytes() == IN_DIR
    assert (clone / "pkg" / "up" / "f.txt").read_bytes() == IN_DIR
    assert (clone / "calc.py").read_bytes() == b"inside\n"


@pytest.mark.parametrize(
    "on_disk, read_back",
    [
        ("../../outside", "..\\..\\outside"),
        ("C:/x", "C:\\x"),
        ("//host/share/x", "\\\\host\\share\\x"),
        ("//?/C:/x", "\\\\?\\C:\\x"),
        ("/rooted", "\\rooted"),
        ("pkg/../../outside", "pkg\\..\\..\\outside"),
    ],
    ids=["climb", "drive-absolute", "unc", "extended-length", "rooted", "multi-segment-climb"],
)
def test_fresh_clone_and_contained_refuse_hostile_backslash_link_text_on_a_backslash_host(
    tmp_path, monkeypatch, on_disk, read_back
):
    template = _template_with_targets(tmp_path)
    _lay_links(template, {"escape": on_disk})
    clone = tmp_path / "clone"

    with monkeypatch.context() as simulated:
        _simulate_windows_link_text(simulated)
        assert _extended_prefix_stripped(os.readlink(template / "escape")) == (
            _extended_prefix_stripped(read_back)
        )
        with pytest.raises(trees.TreeError):
            trees.fresh_clone(template, clone)
        with pytest.raises(trees.TreeError):
            trees.contained(template, "escape")
        with pytest.raises(trees.TreeError):
            trees.contained(template, "escape/secret.txt")

    # Refused before copying: nothing of the template reached the clone.
    assert not (clone / "calc.py").exists()


def test_a_literal_backslash_in_link_text_is_refused_on_a_slash_host(tmp_path, monkeypatch):
    # No simulation: the on-disk text holds a real backslash. Set explicitly, so
    # the case runs the same on a host whose own separator is a backslash.
    monkeypatch.setattr(trees, "_HOST_SEP", "/", raising=False)
    template = _template_with_targets(tmp_path)
    os.symlink("pkg\\a.txt", template / "backslashed")
    os.symlink("pkg/a.txt", template / "slashed")
    clone = tmp_path / "clone"
    assert os.readlink(template / "backslashed") == "pkg\\a.txt"

    # The accept twin of the same shape: the host's own separator is taken.
    assert Path(trees.contained(template, "slashed")).read_bytes() == ALPHA
    with pytest.raises(trees.TreeError):
        trees.contained(template, "backslashed")
    with pytest.raises(trees.TreeError):
        trees.fresh_clone(template, clone)
    assert not (clone / "calc.py").exists()
