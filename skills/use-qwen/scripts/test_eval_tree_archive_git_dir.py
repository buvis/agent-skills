"""Archive members that would write into the sealed template's own `.git`.

`git archive` never emits such a path, since git refuses to track one, so a
member under any `.git` component is crafted. Extracted before `git init`
reinitializes the directory, it would survive into the sealed template: an
executable `.git/hooks/post-checkout` then runs on the next checkout in any
clone, and a planted `.git/config` steers every later git call.

Split from test_eval_tree_archive_safety.py, which stands near the size this
project caps a test file at; the seams and refusal helper are that module's.
"""
import tarfile

import pytest

from eval_harness import trees

# `bare_ci` and `built_repo` are fixtures: pytest resolves them from this
# module's own namespace, so they have to be imported even though nothing here
# calls them. `built_repo` itself depends on `bare_ci` by name.
from test_eval_tree_links import DIRECTORY, PAYLOAD, bare_ci, built_repo
from test_eval_tree_archive_safety import SEAMS, _appended, _assert_refused_on_seam, _file

HOOK = b"#!/bin/sh\necho pwned > \"$HOME/pwned\"\n"

GIT_DIRECTORY_MEMBERS = [
    pytest.param([], [_file(".git/hooks/post-checkout", HOOK, 0o755)], id="hook"),
    pytest.param([], [_file(".git/config", b"[core]\n\tfsmonitor = touch pwned\n")], id="config"),
    pytest.param([(".git", DIRECTORY)], [], id="directory"),
    pytest.param([], [_file(".GIT/hooks/post-checkout", HOOK, 0o755)], id="case-alias"),
    pytest.param([("pkg", DIRECTORY), ("pkg/.git/config", PAYLOAD)], [], id="nested"),
    pytest.param([(".git", ("sym", "pkg")), ("pkg", DIRECTORY)], [], id="symlink"),
    # Spellings NTFS resolves to `.git`: a trailing dot, and the 8.3 short name.
    pytest.param([(".git.", DIRECTORY), (".git./config", PAYLOAD)], [], id="ntfs-trailing-dot"),
    pytest.param([("GIT~1", DIRECTORY), ("GIT~1/config", PAYLOAD)], [], id="ntfs-short-name"),
]


@SEAMS
@pytest.mark.parametrize("members, extra", GIT_DIRECTORY_MEMBERS)
def test_build_template_refuses_a_member_inside_a_git_directory(
    tmp_path, built_repo, monkeypatch, filter_support, members, extra
):
    _assert_refused_on_seam(
        tmp_path, built_repo, monkeypatch, filter_support, _appended(members, extra)
    )


@pytest.mark.parametrize(
    "name",
    [".git", ".git/config", ".GIT/hooks/post-checkout", "pkg/.git/config",
     ".git./config", ".git /config", "GIT~1/config"],
)
def test_archive_vetting_refuses_a_member_under_any_spelling_of_git(name):
    # On the vetting step itself: git's own path checks refuse some of these
    # later, at `git add`, but only after the archive has written into staging.
    with pytest.raises(trees.TreeError, match="git directory"):
        trees._refuse_duplicate_or_crossing_members([tarfile.TarInfo(name)])
