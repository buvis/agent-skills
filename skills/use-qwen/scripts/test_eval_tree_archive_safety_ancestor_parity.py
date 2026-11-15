"""Five review findings against build_template's archive-extraction path:
filter detection, the ancestor-crossing rule, filter/manual parity for
permission edge cases, directory-symlink typing on the manual path, and
atomic staging cleanup on failure.

Split out as its own sibling file per the 800-line cap on
test_eval_tree_archive_safety.py; the seams, the archive builders and the
sentinel come from that module and from test_eval_tree_links.py, so there is
one spelling of each.
"""
import errno
import io
import os
import stat
import tarfile
from pathlib import Path
from unittest.mock import patch

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
    _hide_data_filter,
    _serve_archive,
    _task_start_commit,
    bare_ci,
    built_repo,
)
from test_eval_tree_archive_safety import (
    OTHER,
    SEAMS,
    _appended,
    _assert_refused_on_seam,
    _file,
    _sealed_blob,
    _seal_control,
    _select_seam,
)
from test_eval_tree_archive_safety_modes import _directory


# -- finding 1: the filter-availability predicate must be `callable(getattr(...))`


def test_build_template_falls_back_to_manual_extraction_when_data_filter_is_present_but_not_callable(
    tmp_path, built_repo, monkeypatch
):
    # Named filters can still work through tarfile's internal registry. Observe
    # the selected path directly, rather than relying on extraction to crash.
    monkeypatch.setattr(tarfile, "data_filter", "not-a-filter", raising=False)
    repo = Path(built_repo["repo"])
    first = _task_start_commit(repo)
    bundle = _crafted_tar(
        [("pkg", DIRECTORY), ("pkg/a.txt", PAYLOAD), ("pkg/b.txt", OTHER)]
    )
    _serve_archive(monkeypatch, bundle)
    dest = tmp_path / "template"

    with patch.object(trees, "_extract_without_filter", wraps=trees._extract_without_filter) as manual:
        sha = trees.build_template(repo, first, dest)
    manual.assert_called_once()

    assert sha == trees.head_sha(dest)
    assert (dest / "pkg" / "a.txt").read_bytes() == b"pwned\n"
    assert (dest / "pkg" / "b.txt").read_bytes() == b"other\n"


# -- finding 2: a blanket ancestor-crossing refusal, no safe-symlink exception


ANCESTOR_CROSSING_THROUGH_A_SAFE_LINK = [
    ("pkg", DIRECTORY), ("alias", ("sym", "pkg")), ("alias/file.txt", OTHER),
]
SAFE_LINK_WITH_NOTHING_WRITTEN_BENEATH_IT = [
    ("pkg", DIRECTORY), ("pkg/a.txt", PAYLOAD), ("alias", ("sym", "pkg")),
]


@SEAMS
def test_build_template_refuses_a_member_named_under_a_symlink_that_resolves_safely(
    tmp_path, built_repo, monkeypatch, filter_support
):
    # `alias -> pkg` escapes nowhere on its own; the refusal is about using an
    # existing symlink's name as a path *ancestor*, not about where it lands.
    _assert_refused_on_seam(
        tmp_path, built_repo, monkeypatch, filter_support,
        _crafted_tar(ANCESTOR_CROSSING_THROUGH_A_SAFE_LINK),
    )


def test_archive_vetting_refuses_a_member_named_under_a_symlink_that_resolves_safely():
    # The build above would fail anyway once it lays `alias` over the real
    # `alias/` directory `alias/file.txt` made; only the ancestor rule refuses
    # the archive before anything is written, so pin that rule on its own.
    with tarfile.open(fileobj=io.BytesIO(_crafted_tar(ANCESTOR_CROSSING_THROUGH_A_SAFE_LINK))) as archive:
        members = archive.getmembers()

    with pytest.raises(trees.TreeError, match="beneath an archive symlink"):
        trees._refuse_duplicate_or_crossing_members(members)


@NEEDS_SYMLINKS
@SEAMS
def test_build_template_seals_a_safe_symlink_with_nothing_written_beneath_it(
    tmp_path, built_repo, monkeypatch, filter_support
):
    # The accept twin of the shape above: same safe link, no member naming it
    # as an ancestor. The fix must not over-refuse the link's own presence.
    dest = _seal_control(
        tmp_path, built_repo, monkeypatch, filter_support,
        _crafted_tar(SAFE_LINK_WITH_NOTHING_WRITTEN_BENEATH_IT),
    )

    assert (dest / "pkg" / "a.txt").read_bytes() == b"pwned\n"
    assert Path(os.readlink(dest / "alias")).as_posix() == "pkg"
    assert (dest / "alias" / "a.txt").read_bytes() == b"pwned\n"


# -- finding 3: filter and manual extraction must agree on permission edges


def _build_on_both_seams(tmp_path, built_repo, monkeypatch, bundle) -> dict:
    """Run `bundle` through both seams, each into its own `dest`.

    Returns `{seam_label: (raised_or_None, dest)}` so a caller can compare the
    two outcomes directly, rather than only repeating one assertion twice.
    """
    repo = Path(built_repo["repo"])
    outcomes = {}
    for filter_support in ("with-data-filter", "without-data-filter"):
        _select_seam(monkeypatch, filter_support)
        first = _task_start_commit(repo)
        _serve_archive(monkeypatch, bundle)
        dest = tmp_path / filter_support
        raised = None
        try:
            trees.build_template(repo, first, dest)
        except Exception as error:
            raised = error
        outcomes[filter_support] = (raised, dest)
    return outcomes


@pytest.mark.parametrize("mode", [0o000, 0o200, 0o500, 0o755])
def test_build_template_extracts_children_of_a_permission_restricted_directory_on_both_seams(
    tmp_path, built_repo, monkeypatch, mode
):
    # The directory's own restrictive mode must not block writing the child
    # nested beneath it, on either extraction path.
    bundle = _appended(
        [], [(_directory("restricted", mode), None), _file("restricted/child.txt", b"nested\n")]
    )

    outcomes = _build_on_both_seams(tmp_path, built_repo, monkeypatch, bundle)

    for filter_support, (raised, dest) in outcomes.items():
        assert raised is None, (filter_support, raised)
        assert (dest / "restricted" / "child.txt").read_bytes() == b"nested\n", filter_support
    assert stat.S_IMODE(outcomes["with-data-filter"][1].joinpath("restricted").stat().st_mode) == stat.S_IMODE(
        outcomes["without-data-filter"][1].joinpath("restricted").stat().st_mode
    )


def test_build_template_handles_a_fully_restrictive_file_mode_the_same_way_on_both_seams(
    tmp_path, built_repo, monkeypatch
):
    # A file member that denies every permission, beside an ordinary sibling.
    # Whatever the two seams decide, they must decide it the same way, and a
    # refusal must surface as TreeError, never a raw subprocess exception.
    bundle = _appended(
        [("pkg", DIRECTORY)],
        [_file("pkg/locked.txt", b"locked\n", 0o000), _file("pkg/sibling.txt", b"sibling\n")],
    )

    outcomes = _build_on_both_seams(tmp_path, built_repo, monkeypatch, bundle)
    raised_with, dest_with = outcomes["with-data-filter"]
    raised_without, dest_without = outcomes["without-data-filter"]

    assert (raised_with is None) == (raised_without is None), (raised_with, raised_without)
    for raised in (raised_with, raised_without):
        if raised is not None:
            assert isinstance(raised, trees.TreeError), raised
    if raised_with is None:
        for dest in (dest_with, dest_without):
            assert (dest / "pkg" / "sibling.txt").read_bytes() == b"sibling\n"
            # Read through git, not the filesystem: the file's own mode may
            # deny even its owner a plain read afterward.
            assert _sealed_blob(dest, "pkg/locked.txt") == b"locked\n"


# -- finding 4: a directory-typed symlink on the manual (filter-absent) path


@NEEDS_SYMLINKS
def test_build_template_s_manual_path_seals_a_directory_symlink_that_reads_through_correctly(
    tmp_path, built_repo, monkeypatch
):
    _hide_data_filter(monkeypatch)
    repo = Path(built_repo["repo"])
    first = _task_start_commit(repo)
    members = [("pkg", DIRECTORY), ("pkg/a.txt", PAYLOAD), ("dir-link", ("sym", "pkg"))]
    _serve_archive(monkeypatch, _crafted_tar(members))
    dest = tmp_path / "template"

    sha = trees.build_template(repo, first, dest)

    assert sha == trees.head_sha(dest)
    assert (dest / "dir-link").is_symlink()
    assert (dest / "dir-link" / "a.txt").read_bytes() == b"pwned\n"
    assert os.readlink(dest / "dir-link") == "pkg"


@NEEDS_SYMLINKS
def test_build_template_s_manual_path_passes_target_is_directory_from_the_archive_s_own_graph(
    tmp_path, built_repo, monkeypatch
):
    # `os.symlink`'s `target_is_directory` only affects Windows, so the host
    # filesystem cannot show whether it was computed right; spy on the call
    # itself instead. Two links of the same shape, one landing on a directory
    # member and one on a file member, so a constant True or False fails.
    _hide_data_filter(monkeypatch)
    repo = Path(built_repo["repo"])
    first = _task_start_commit(repo)
    members = [
        ("pkg", DIRECTORY), ("pkg/a.txt", PAYLOAD),
        ("dir-link", ("sym", "pkg")), ("file-link", ("sym", "pkg/a.txt")),
        ("root-link", ("sym", ".")), ("implicit-link", ("sym", "implicit")),
        ("implicit/nested/b.txt", OTHER), ("chain-link", ("sym", "implicit-link")),
    ]
    _serve_archive(monkeypatch, _crafted_tar(members))
    dest = tmp_path / "template"
    calls = {}
    real_symlink = os.symlink

    def spy(src, dst, *, target_is_directory=False):
        calls[Path(dst).name] = target_is_directory
        return real_symlink(src, dst, target_is_directory=target_is_directory)

    monkeypatch.setattr(os, "symlink", spy)

    trees.build_template(repo, first, dest)

    assert calls == {
        "dir-link": True, "file-link": False, "root-link": True,
        "implicit-link": True, "chain-link": True,
    }


# -- finding 5: a failure never leaves staging or created parent directories


def test_build_template_leaves_no_staging_or_parent_directories_after_a_refused_archive(
    tmp_path, built_repo, monkeypatch
):
    repo = Path(built_repo["repo"])
    first = _task_start_commit(repo)
    # A duplicate member name: refused by `build_template` itself, after it
    # would have had to create `dest`'s absent parent chain to stage into.
    bundle = _crafted_tar([("x", PAYLOAD), ("x", DIRECTORY)])
    _serve_archive(monkeypatch, bundle)
    dest = tmp_path / "a" / "b" / "c" / "template"
    before = sorted(path.name for path in tmp_path.iterdir())
    assert "a" not in before

    with pytest.raises(trees.TreeError):
        trees.build_template(repo, first, dest)

    assert not dest.exists()
    assert not (tmp_path / "a").exists()
    assert not (tmp_path / "a" / "b").exists()
    assert not (tmp_path / "a" / "b" / "c").exists()
    # Nothing new sits beside the chain either: no sibling staging directory.
    after = sorted(path.name for path in tmp_path.iterdir())
    assert after == before


def test_build_template_wraps_a_staging_mkdir_failure_as_treeerror_and_cleans_up_created_ancestors(
    tmp_path, built_repo, monkeypatch
):
    # The failure this time is the staging mkdir itself, not a later refusal
    # inside the try: its own OSError must still surface as TreeError, and
    # any ancestor directories it created along the way must still be gone.
    repo = Path(built_repo["repo"])
    first = _task_start_commit(repo)
    _serve_archive(monkeypatch, _crafted_tar([("pkg", DIRECTORY)]))
    dest = tmp_path / "a" / "b" / "template"
    before = sorted(path.name for path in tmp_path.iterdir())
    assert "a" not in before
    real_mkdir = os.mkdir

    def failing_mkdir(path, *args, **kwargs):
        if ".staging-" in os.fspath(path):
            raise OSError(errno.EACCES, "injected staging mkdir failure")
        return real_mkdir(path, *args, **kwargs)

    monkeypatch.setattr(os, "mkdir", failing_mkdir)

    with pytest.raises(trees.TreeError):
        trees.build_template(repo, first, dest)

    assert not dest.exists()
    assert not (tmp_path / "a").exists()
    after = sorted(path.name for path in tmp_path.iterdir())
    assert after == before
