"""Tests for `trees.snapshot` and `trees.apply_patch`: reading a candidate's
work back out of a clone, and replaying it into another one.

Split out of test_eval_tree_state.py, which the rest of the module's cases
already fill to this project's cap on the size of one test file. The sealed
template and the candidate's edits are spelled there, and imported here, so
there is one spelling of each.
"""
import os
import re
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from eval_harness import trees

import eval_harness_fixtures

# The quoted-name spellings and the git argv recorder are shared with the
# evidence tests, which pin the same reading of git's path output for the seal.
from eval_harness_evidence_helpers import (
    QUOTED_LISTING,
    QUOTED_NAMES,
    _literal,
    _path_listings,
    _record_git_argv,
)

# `bare_ci` and `built_repo` are fixtures: pytest resolves them from this
# module's own namespace, so they have to be imported even though nothing here
# calls them.
from eval_harness_fixture_helpers import _git, bare_ci, built_repo
from test_eval_tree_state import _candidate_changes, _sealed_template

STATUS_LETTERS = re.compile(r"[ACDMRTUXB][0-9]{0,3}")

# Text a candidate may well leave behind, and not UTF-8: a Latin-1 comment and
# two bytes no UTF-8 sequence can start with, beside a comment that IS valid
# UTF-8 (`na\xc3\xafve` is "naïve"). No NUL, so git still diffs it as text and
# the raw bytes land in the patch as they are.
LATIN1_IMPL = (
    b"# na\xc3\xafve caf\xe9 \xff\xfe not utf-8\n"
    b"def add(left, right):\n    return left + right\n"
)


def _git_rc(repo: Path, *args: str) -> int:
    """Git's exit code for a command that is allowed to fail."""
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    ).returncode


def _write_patch(where: Path, diff_text: str) -> Path:
    """Store a patch byte for byte.

    Without `newline=""` the write turns every LF into CRLF on Windows and the
    patch stops matching the bytes it was cut from.
    """
    where.write_text(diff_text, encoding="utf-8", newline="")
    return where


def _differing_paths(left: dict, right: dict) -> list:
    """Every path the two manifests disagree about, sorted."""
    return sorted(
        path for path in set(left) | set(right) if left.get(path) != right.get(path)
    )


def _bytes_at(root: Path, relpath: str):
    """The bytes `root` holds at `relpath`, or None when it holds nothing there."""
    target = root / relpath
    return target.read_bytes() if target.is_file() else None


def _git_s_own_patch(clone: Path, sealed: str) -> bytes:
    """The bytes git itself cuts for the clone's work, index left as found.

    Untracked files are staged intent-to-add for the read, the way the snapshot
    does it, so the two patches cover the same changes.
    """
    _git(clone, "add", "-N", ".")
    try:
        return subprocess.run(
            ["git", "-C", str(clone), "diff", "--binary", sealed],
            capture_output=True,
            check=True,
            timeout=60,
        ).stdout
    finally:
        _git(clone, "reset", "-q")


@pytest.fixture
def candidate(tmp_path, built_repo):
    """A sealed template and a clone a candidate has already worked in."""
    template = _sealed_template(tmp_path, built_repo)
    clone = Path(trees.fresh_clone(template, tmp_path / "clone"))
    sealed = trees.head_sha(clone)
    _candidate_changes(clone, built_repo)
    return SimpleNamespace(template=template, clone=clone, sealed=sealed, info=built_repo)


# -- snapshot --------------------------------------------------------------


def test_snapshot_lists_what_the_candidate_added_edited_and_deleted(candidate):
    impl, oracle = candidate.info["impl"], candidate.info["test"]

    changed, diff_text = trees.snapshot(candidate.clone, candidate.sealed)

    by_path = {record["path"]: record for record in changed}
    assert set(by_path) == {impl, "helper.py", oracle}
    assert by_path[impl]["status"] == "M"
    # An untracked file only reaches a diff once it is staged as intent-to-add,
    # so a snapshot that skips that step never reports the candidate's new file.
    assert by_path["helper.py"]["status"] == "A"
    assert by_path[oracle]["status"] == "D"
    for record in changed:
        assert set(record) == {"status", "path", "old_path"}
        assert STATUS_LETTERS.fullmatch(record["status"]), record
        # `old_path` belongs to renames and copies. Every record here is an
        # edit, an addition or a deletion, which this states rather than
        # assumes; the rename case below pins the other half of the rule.
        assert record["status"][0] not in "RC", record
        assert record["old_path"] is None, record
    assert diff_text.strip(), "the snapshot carried no patch"
    # The index goes back the way it was found: the intent-to-add entries were a
    # means of reading the tree, not a change to it.
    assert _git(candidate.clone, "diff", "--cached", "--name-only") == ""


def test_snapshot_reports_a_rename_under_the_name_the_tree_now_holds(
    tmp_path, built_repo
):
    template = _sealed_template(tmp_path, built_repo)
    clone = Path(trees.fresh_clone(template, tmp_path / "clone"))
    sealed = trees.head_sha(clone)
    original, moved = built_repo["test"], "test_arithmetic.py"
    _git(clone, "mv", original, moved)

    changed, _ = trees.snapshot(clone, sealed)

    # One change, and it is one record: a rename read as an unrelated deletion
    # and addition would be two.
    assert len(changed) == 1, changed
    record = changed[0]
    assert set(record) == {"status", "path", "old_path"}
    assert record["status"].startswith("R"), record
    assert STATUS_LETTERS.fullmatch(record["status"]), record
    # Filed under the name the tree holds now, remembering the one it lost.
    # Recording the source path as `path` files the change under a name nothing
    # in the tree answers to, and every later lookup by path misses it.
    assert record["path"] == moved
    assert record["old_path"] == original
    assert (clone / moved).is_file()
    assert not (clone / original).exists()


def test_snapshot_reads_the_sealed_sha_it_was_given_not_the_clone_s_head(
    tmp_path, built_repo
):
    impl, oracle = built_repo["impl"], built_repo["test"]
    template = _sealed_template(tmp_path, built_repo)
    clone = Path(trees.fresh_clone(template, tmp_path / "clone"))
    sealed = trees.head_sha(clone)
    _candidate_changes(clone, built_repo)
    committed = trees.commit_all(clone, "the candidate committed its own work")

    changed, diff_text = trees.snapshot(clone, sealed)

    # The head has moved and the working tree is clean, so `git status` reports
    # nothing at all here. Only a diff against the sealed sha the caller handed
    # in can still see what the candidate did.
    assert committed != sealed
    assert _git(clone, "status", "--porcelain", "--untracked-files=all") == ""
    by_path = {record["path"]: record["status"] for record in changed}
    assert by_path == {impl: "M", "helper.py": "A", oracle: "D"}
    assert f"a/{impl}" in diff_text


def test_snapshot_keeps_a_non_utf8_edit_s_patch_byte_for_byte(candidate):
    impl = candidate.info["impl"]
    (candidate.clone / impl).write_bytes(LATIN1_IMPL)
    expected = _git_s_own_patch(candidate.clone, candidate.sealed)
    assert b"caf\xe9 \xff\xfe" in expected, "git did not diff the file as text"

    # No UnicodeDecodeError: a candidate's bytes are the candidate's bytes, and
    # a snapshot that cannot read them is an observation that never happens.
    changed, diff_text = trees.snapshot(candidate.clone, candidate.sealed)

    assert isinstance(diff_text, str)
    # Lossless, and lossless in one particular way: the text encodes back to
    # git's bytes exactly. A replacement character, a dropped byte or a Latin-1
    # decode all read fine and all cut a patch git will not apply.
    assert diff_text.encode("utf-8", "surrogateescape") == expected
    assert b"caf\xe9 \xff\xfe" in diff_text.encode("utf-8", "surrogateescape")
    # The valid UTF-8 beside the stray bytes is read as the text it is: a
    # narrower codec with the same escape hatch round-trips the bytes too, and
    # turns every character a candidate wrote into surrogates on the way.
    assert "naïve" in diff_text
    by_path = {record["path"]: record["status"] for record in changed}
    assert by_path[impl] == "M"
    assert _git(candidate.clone, "diff", "--cached", "--name-only") == ""


def _clone_with_quoted_names(tmp_path, built_repo) -> tuple:
    """A clone whose sealed tree holds three quoted names under `lib/` and
    whose candidate added the four top-level ones; answers (clone, sealed).

    Each file's body is its own, so no deletion pairs with an addition as a
    rename git found on its own. The control at the end: git's default
    listing does quote every one of these, so a snapshot that takes that
    listing literally files them as `"caf\\303\\251.py"`, `"tab\\there.py"`
    and the like, names nothing in the tree answers to.
    """
    template = _sealed_template(tmp_path, built_repo)
    clone = Path(trees.fresh_clone(template, tmp_path / "clone"))
    (clone / "lib").mkdir()
    sealed_names = [f"lib/{name}" for name in QUOTED_NAMES[:3]]
    for name in sealed_names:
        (clone / name).write_text(f"# {name}\n", encoding="utf-8")
    _git(clone, "add", "--", *_literal(sealed_names))
    _git(clone, *eval_harness_fixtures.IDENTITY, "commit", "-q", "-m", "seal: add quoted names")
    sealed = trees.head_sha(clone)
    for name in QUOTED_NAMES:
        (clone / name).write_text(f"# {name}\n", encoding="utf-8")
    _git(clone, "add", "-N", "--", *_literal(QUOTED_NAMES))
    try:
        listed = _git(clone, "diff", "--name-only", "--", *_literal(QUOTED_NAMES))
    finally:
        _git(clone, "reset", "-q")
    assert listed == QUOTED_LISTING.rstrip("\n")
    return clone, sealed


@pytest.mark.skipif(os.name == "nt", reason="a TAB in a filename is not legal on Windows")
def test_snapshot_lists_every_change_to_a_file_git_would_quote_under_its_real_name(
    tmp_path, built_repo, monkeypatch
):
    clone, sealed = _clone_with_quoted_names(tmp_path, built_repo)
    # One sealed name to edit, one to delete and one to move to a fourth.
    edited, deleted, moved, target = (f"lib/{name}" for name in QUOTED_NAMES)
    (clone / edited).write_text("# edited\n", encoding="utf-8")
    (clone / deleted).unlink()
    _git(clone, "mv", "--", moved, target)
    recorded = _record_git_argv(monkeypatch)

    changed, _ = trees.snapshot(clone, sealed)

    # The path bytes, not the quoted text: the listing the snapshot asks git
    # for is NUL-delimited, the one form that carries a name as it is.
    # Unquoting the text by hand covers the escapes its author thought of.
    listings = _path_listings(recorded)
    assert listings, "the snapshot never asked git for the changed paths"
    for argv in listings:
        assert "-z" in argv, argv
    by_path = {record["path"]: record for record in changed}
    assert len(changed) == len(by_path), changed
    # Every status, not only an addition: the edit, the deletion and both ends
    # of the rename are filed under the names the tree holds.
    rename = by_path.pop(target)
    assert rename["status"].startswith("R"), rename
    assert STATUS_LETTERS.fullmatch(rename["status"]), rename
    assert rename == {"status": rename["status"], "path": target, "old_path": moved}
    assert by_path == {
        **{name: {"status": "A", "path": name, "old_path": None} for name in QUOTED_NAMES},
        edited: {"status": "M", "path": edited, "old_path": None},
        deleted: {"status": "D", "path": deleted, "old_path": None},
    }
    for name in (*QUOTED_NAMES, edited, target):
        assert (clone / name).is_file(), name
    assert not (clone / deleted).exists()
    assert not (clone / moved).exists()


@pytest.mark.parametrize(
    "step, failure",
    [
        ("the-change-listing", subprocess.CalledProcessError(128, ["git"])),
        ("the-binary-diff", subprocess.CalledProcessError(128, ["git"])),
        # Not git's own refusal but the run itself giving up: a cleanup that
        # catches one exception type and re-raises leaves the index dirty here.
        ("the-binary-diff", subprocess.TimeoutExpired(["git"], 1)),
    ],
    ids=["the-change-listing", "the-binary-diff", "the-binary-diff-timing-out"],
)
def test_snapshot_resets_the_index_even_when_the_diff_step_raises(
    candidate, monkeypatch, step, failure
):
    real_git, real_git_bytes = trees._git, trees._git_bytes

    def refuse(*args, **kwargs):
        raise failure

    def refusing(real):
        def wrapper(root, *args):
            # Only the `--name-status` read fails; the intent-to-add pass and
            # the reset still reach git, so what is left in the index is the
            # snapshot's own doing. Both helpers are wrapped: which one cuts
            # the listing is the snapshot's business, not this case's.
            if "--name-status" in args:
                raise failure
            return real(root, *args)

        return wrapper

    if step == "the-change-listing":
        monkeypatch.setattr(trees, "_git", refusing(real_git))
        monkeypatch.setattr(trees, "_git_bytes", refusing(real_git_bytes))
    else:
        monkeypatch.setattr(trees, "_git_bytes", refuse)

    with pytest.raises(type(failure)):
        trees.snapshot(candidate.clone, candidate.sealed)

    # The intent-to-add entries were a means of reading the tree. Whichever of
    # the two reads fails must not leave them behind: the next command in this
    # clone would find files staged that no one staged.
    assert _git(candidate.clone, "diff", "--cached", "--name-only") == ""


# -- apply_patch -----------------------------------------------------------


def test_snapshot_s_patch_reapplies_on_a_fresh_clone(candidate, tmp_path):
    impl, oracle = candidate.info["impl"], candidate.info["test"]

    _, diff_text = trees.snapshot(candidate.clone, candidate.sealed)
    patch = _write_patch(tmp_path / "candidate.patch", diff_text)
    replay = Path(trees.fresh_clone(candidate.template, tmp_path / "replay"))

    # A patch is what git calls a patch. Git reads this one before the harness
    # does: an internal format only this module can apply would round-trip
    # through its own reader and never be a patch anybody else could use.
    assert diff_text.startswith("diff --git ")
    for path in (impl, "helper.py", oracle):
        assert f"a/{path}" in diff_text, path
    assert _git_rc(replay, "apply", "--check", "--binary", str(patch)) == 0

    started = time.monotonic()
    result = trees.apply_patch(replay, patch)
    elapsed = time.monotonic() - started

    assert result.rc == 0
    assert result.timed_out is False
    # Running a command costs time, so a run that reports none of it is
    # reporting a placeholder. Two attempts both costing zero cannot be told
    # apart, and the number is stored to be compared.
    assert result.wall_s is not None
    assert 0 < result.wall_s <= elapsed + 1, result.wall_s
    # Every path, hash and mode: the replayed tree is the candidate's tree.
    assert (
        _differing_paths(
            trees.build_manifest(replay), trees.build_manifest(candidate.clone)
        )
        == []
    )


@pytest.mark.parametrize(
    "kind", ["a-file-the-candidate-edited", "one-it-added", "one-it-deleted"]
)
def test_apply_patch_leaves_the_one_excluded_path_as_the_template_left_it(
    candidate, tmp_path, kind
):
    excluded = {
        "a-file-the-candidate-edited": candidate.info["impl"],
        "one-it-added": "helper.py",
        "one-it-deleted": candidate.info["test"],
    }[kind]
    _, diff_text = trees.snapshot(candidate.clone, candidate.sealed)
    patch = _write_patch(tmp_path / "candidate.patch", diff_text)
    whole = Path(trees.fresh_clone(candidate.template, tmp_path / "whole"))
    minus_one = Path(trees.fresh_clone(candidate.template, tmp_path / "minus-one"))

    applied = trees.apply_patch(whole, patch)
    ablated = trees.apply_patch(minus_one, patch, exclude=[excluded])

    assert applied.rc == 0
    assert ablated.rc == 0
    sealed_bytes = _bytes_at(candidate.template, excluded)
    # Excluded means the patch never reached it: what the template held there
    # still stands, and where the template held nothing, nothing stands.
    # Applying the whole patch and putting the path back afterwards is a
    # different thing, and a wrong one: it cannot un-create a file the patch
    # added, and it has nothing to put back for one the patch deleted.
    assert _bytes_at(minus_one, excluded) == sealed_bytes
    # The exclusion is what made the difference: the whole patch does change
    # this path, so the ablation is what tells the two trees apart.
    assert _bytes_at(whole, excluded) != sealed_bytes
    # "Canonical minus that path": the rest of the patch still lands, so the two
    # trees differ in exactly the excluded file.
    assert _differing_paths(
        trees.build_manifest(whole), trees.build_manifest(minus_one)
    ) == [excluded]


def test_apply_patch_reports_a_patch_the_tree_will_not_take(candidate, tmp_path):
    impl = candidate.info["impl"]
    _, diff_text = trees.snapshot(candidate.clone, candidate.sealed)
    patch = _write_patch(tmp_path / "candidate.patch", diff_text)
    moved_on = Path(trees.fresh_clone(candidate.template, tmp_path / "moved-on"))
    (moved_on / impl).write_text(
        "def add(left, right):\n    return 0\n", encoding="utf-8"
    )

    # The patch was cut against bytes this tree no longer holds, so git refuses
    # it outright and nothing lands.
    assert _git_rc(moved_on, "apply", "--check", "--binary", str(patch)) != 0
    result = trees.apply_patch(moved_on, patch)

    # A refusal reported as success is a tree recorded as the candidate's that
    # the candidate's own work never reached.
    assert result.rc != 0
    assert result.timed_out is False
    assert result.first_failure is not None
