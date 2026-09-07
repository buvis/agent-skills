"""Tests for eval_harness/trees.py: templates, clones, hashes and manifests.

A sibling of test_eval_trees.py rather than an addition to it: that file already
stands at the size this project caps a test file at, and the trees it names are
the runner's process trees.

Two more siblings carry the rest of this module, for the same size reason:
test_eval_tree_proofs.py holds `prove_state` and test_eval_tree_patches.py holds
`snapshot` and `apply_patch`. Both take their shared helpers and capability
guards from here, so there is one spelling of each.
"""
import hashlib
import os
import re
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path

import pytest

import eval_harness_fixtures
from eval_harness import trees

# `bare_ci` and `built_repo` are fixtures: pytest resolves them from this
# module's own namespace, so they have to be imported even though nothing here
# calls them.
from eval_harness_fixture_helpers import _git, bare_ci, built_repo

IDENTITY = eval_harness_fixtures.IDENTITY

CANDIDATE_IMPL = '''"""Arithmetic the oracle test checks."""


def add(left, right):
    return sum((left, right))
'''

CANDIDATE_HELPER = "HELPER = 'a file the candidate added'\n"

EXTRA_ORACLE = '''from calc import add


def test_add_is_commutative():
    assert add(2, 3) == add(3, 2)
'''

SHA1 = re.compile(r"[0-9a-f]{40}")


def _host_makes_symlinks() -> bool:
    """Whether this host can create a symlink at all."""
    with tempfile.TemporaryDirectory() as scratch:
        target = Path(scratch) / "target.txt"
        target.write_text("target\n", encoding="utf-8")
        try:
            os.symlink("target.txt", Path(scratch) / "link.txt")
        except (OSError, NotImplementedError, AttributeError):
            return False
        return True


def _host_carries_an_executable_bit() -> bool:
    """Whether a chmod on this host leaves an executable bit behind to record."""
    with tempfile.TemporaryDirectory() as scratch:
        probe = Path(scratch) / "probe"
        probe.write_text("probe\n", encoding="utf-8")
        probe.chmod(0o755)
        return bool(probe.stat().st_mode & stat.S_IXUSR)


# Capability guards, not platform guards: the behaviour under test is the
# symlink itself, or the permission bit itself, and a host that cannot make one
# has nothing for the case to be about.
NEEDS_SYMLINKS = pytest.mark.skipif(
    not _host_makes_symlinks(),
    reason="the host cannot create a symlink at all, and a symlink is the subject here",
)
NEEDS_EXECUTABLE_BIT = pytest.mark.skipif(
    not _host_carries_an_executable_bit(),
    reason="the host keeps no executable bit, and that bit is the subject here",
)


def _git_with_input(repo: Path, payload: str, *args: str) -> str:
    """Git's stdout for a command fed `payload` on stdin."""
    done = subprocess.run(
        ["git", "-C", str(repo), *args],
        input=payload,
        capture_output=True,
        text=True,
        check=True,
        timeout=60,
    )
    return done.stdout.strip()


def _task_start_commit(repo: Path) -> str:
    """An empty commit to hand `build_template` as its `first` argument.

    The template is sealed at `<first>^`, so whatever stands committed right now
    is the tree the sealed template has to carry.
    """
    _git(repo, *IDENTITY, "commit", "--allow-empty", "-m", "the task's first commit")
    return _git(repo, "rev-parse", "HEAD")


def _commit_symlink(repo: Path, name: str, target: str) -> None:
    """Commit a symlink pointing at `target` without creating one on disk.

    Git stores a symlink as a blob holding its target text plus a `120000` index
    entry, so the whole thing can be written through git. That keeps the case
    running on a host that cannot create a symlink at all, while the tree
    `build_template` reads still carries one.
    """
    blob = _git_with_input(repo, target, "hash-object", "-w", "--stdin")
    _git(repo, "update-index", "--add", "--cacheinfo", f"120000,{blob},{name}")
    _git(repo, *IDENTITY, "commit", "-m", f"add the {name} symlink")


def _sealed_template(tmp_path: Path, info: dict, name: str = "template") -> Path:
    """The pre-task tree of the fixture repo, sealed as a template."""
    dest = tmp_path / name
    trees.build_template(Path(info["repo"]), str(info["last"]), dest)
    return dest


def _candidate_changes(clone: Path, info: dict) -> None:
    """One edit, one addition and one deletion: the shapes a diff has to carry."""
    (clone / info["impl"]).write_text(CANDIDATE_IMPL, encoding="utf-8")
    (clone / "helper.py").write_text(CANDIDATE_HELPER, encoding="utf-8")
    (clone / info["test"]).unlink()


# -- build_template --------------------------------------------------------


def test_build_template_seals_the_tree_before_the_task_as_one_commit(
    tmp_path, built_repo, isolate_home
):
    # No global config, no system config, no identity variables (`bare_ci`, which
    # `built_repo` carries) and a home that holds nothing: only the template
    # builder's own -c flags can name an author or a branch here.
    isolate_home(tmp_path / "home")
    repo = Path(built_repo["repo"])
    dest = tmp_path / "template"

    sha = trees.build_template(repo, str(built_repo["last"]), dest)

    assert SHA1.fullmatch(sha), sha
    assert trees.head_sha(dest) == sha
    # One commit of its own, not the source repo's history carried over.
    assert _git(dest, "rev-list", "--count", "HEAD") == "1"
    # `git add -A` left nothing behind, tracked or untracked.
    assert _git(dest, "status", "--porcelain", "--untracked-files=all") == ""
    # A named branch, not a detached HEAD: the commit was made on one.
    assert _git(dest, "rev-parse", "--abbrev-ref", "HEAD") != "HEAD"
    # The parent of the task's first commit, not the commit itself. These two
    # trees differ by exactly the fix the task exists to make.
    assert (dest / built_repo["impl"]).read_text(encoding="utf-8") == (
        eval_harness_fixtures.BROKEN_IMPL
    )
    assert (dest / built_repo["impl"]).read_text(encoding="utf-8") != (
        eval_harness_fixtures.FIXED_IMPL
    )
    # Tree ids are content addresses, so this is every path, byte and mode at
    # once: the sealed tree is the pre-task tree and nothing else.
    assert _git(dest, "rev-parse", "HEAD^{tree}") == _git(
        repo, "rev-parse", f"{built_repo['first']}^{{tree}}"
    )


def test_build_template_seals_the_commit_it_was_handed_not_the_repo_s_head(
    tmp_path, built_repo
):
    repo = Path(built_repo["repo"])
    task = str(built_repo["last"])
    later = "shipped-after-the-task.txt"
    (repo / later).write_text("landed after the task commit\n", encoding="utf-8")
    _git(repo, "add", later)
    _git(repo, *IDENTITY, "commit", "-m", "work that landed after the task commit")
    dest = tmp_path / "template"

    sha = trees.build_template(repo, task, dest)

    # The repo's head now stands past the commit being sealed, so neither `HEAD`
    # nor `HEAD^` names the tree that belongs in this template. Only the commit
    # the caller handed in does, and its parent is two steps back from the head.
    assert _git(repo, "rev-parse", "HEAD") != task
    assert _git(repo, "rev-parse", "HEAD^") == task
    assert SHA1.fullmatch(sha), sha
    assert _git(dest, "rev-parse", "HEAD^{tree}") == _git(
        repo, "rev-parse", f"{task}^^{{tree}}"
    )
    assert (dest / built_repo["impl"]).read_text(encoding="utf-8") == (
        eval_harness_fixtures.BROKEN_IMPL
    )
    # Nothing the repo grew after the task commit reaches the sealed tree.
    assert not (dest / later).exists()


@pytest.mark.parametrize(
    "make_target",
    [
        lambda scratch: "/etc/passwd",
        lambda scratch: "../outside/secret.txt",
        # Spelled at run time, so no implementation can carry the answer: this
        # one is an absolute path that did not exist when the code was written.
        lambda scratch: str(scratch / "outside" / "x"),
    ],
    ids=["absolute-target", "target-escaping-the-tree", "absolute-target-spelled-at-run-time"],
)
def test_build_template_refuses_a_source_tree_whose_symlink_leaves_it(
    tmp_path, built_repo, make_target
):
    repo = Path(built_repo["repo"])
    _commit_symlink(repo, "escape", make_target(tmp_path))
    first = _task_start_commit(repo)
    dest = tmp_path / "template"

    with pytest.raises(trees.TreeError):
        trees.build_template(repo, first, dest)

    # Refused outright: no half-built template that a later clone would take for
    # a sealed one.
    assert not (dest / ".git").exists()


@NEEDS_SYMLINKS
def test_build_template_seals_a_symlink_that_stays_inside_the_tree(tmp_path, built_repo):
    repo = Path(built_repo["repo"])
    _commit_symlink(repo, "alias.py", built_repo["impl"])
    first = _task_start_commit(repo)
    dest = tmp_path / "template"

    sha = trees.build_template(repo, first, dest)

    # What is refused above is a link that leaves the tree, not a link: a
    # builder that refused every symlink would seal no tree that carries one.
    assert SHA1.fullmatch(sha), sha
    assert (dest / "alias.py").is_symlink()
    assert Path(os.readlink(dest / "alias.py")).as_posix() == built_repo["impl"]


# -- fresh_clone -----------------------------------------------------------


@NEEDS_SYMLINKS
def test_fresh_clone_preserves_file_bytes_and_a_relative_symlink(tmp_path, built_repo):
    repo = Path(built_repo["repo"])
    _commit_symlink(repo, "alias.py", built_repo["impl"])
    first = _task_start_commit(repo)
    template = tmp_path / "template"
    trees.build_template(repo, first, template)
    dest = tmp_path / "clone"

    where = trees.fresh_clone(template, dest)

    assert Path(where).resolve() == dest.resolve()
    impl = dest / built_repo["impl"]
    assert impl.read_bytes() == (template / built_repo["impl"]).read_bytes()
    assert b"def add" in impl.read_bytes()
    link = dest / "alias.py"
    assert link.is_symlink(), "the clone resolved the link into a copy of its target"
    # Still relative, still pointing where it pointed: a clone that rewrote the
    # link to an absolute path breaks the moment the tree is moved.
    assert Path(os.readlink(link)).as_posix() == built_repo["impl"]


# -- hash_paths ------------------------------------------------------------


def test_hash_paths_answers_absent_for_a_missing_path_and_for_a_directory(tmp_path):
    payload = b"def add(left, right):\n    return left + right\n"
    (tmp_path / "calc.py").write_bytes(payload)
    (tmp_path / "pkg").mkdir()
    nested = b"nested\n"
    (tmp_path / "pkg" / "nested.txt").write_bytes(nested)

    hashes = trees.hash_paths(tmp_path, ["calc.py", "pkg/nested.txt", "pkg", "gone.txt"])

    assert hashes["calc.py"] == hashlib.sha256(payload).hexdigest()
    assert hashes["calc.py"] == hashes["calc.py"].lower()
    # Slash form, whatever the platform spells a path with: a key written with
    # the host separator is a different key on Windows.
    assert hashes["pkg/nested.txt"] == hashlib.sha256(nested).hexdigest()
    # Absent means "no bytes to hash here", and a directory has none. A hash of
    # its listing would change with every file written beside the tree.
    assert hashes["pkg"] == "absent"
    assert hashes["gone.txt"] == "absent"
    assert set(hashes) == {"calc.py", "pkg/nested.txt", "pkg", "gone.txt"}


@NEEDS_SYMLINKS
def test_hash_paths_hashes_a_link_s_target_and_calls_a_link_to_a_directory_absent(
    tmp_path,
):
    payload = b"def add(left, right):\n    return left + right\n"
    (tmp_path / "calc.py").write_bytes(payload)
    (tmp_path / "pkg").mkdir()
    os.symlink("calc.py", tmp_path / "alias.py")
    os.symlink("pkg", tmp_path / "pkg-link", target_is_directory=True)

    hashes = trees.hash_paths(tmp_path, ["alias.py", "pkg-link"])

    assert hashes["alias.py"] == hashlib.sha256(payload).hexdigest()
    assert hashes["pkg-link"] == "absent"


# -- build_manifest --------------------------------------------------------


def test_build_manifest_records_a_file_s_type_hash_and_mode_and_skips_git(tmp_path):
    payload = b"def add(left, right):\n    return left + right\n"
    (tmp_path / "calc.py").write_bytes(payload)
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg" / "nested.txt").write_bytes(b"nested\n")
    (tmp_path / ".git").mkdir()
    (tmp_path / ".git" / "HEAD").write_bytes(b"ref: refs/heads/main\n")

    manifest = trees.build_manifest(tmp_path)

    assert manifest["calc.py"] == {
        "type": "file",
        "sha256": hashlib.sha256(payload).hexdigest(),
        "target": None,
        "mode": 0o644,
    }
    assert manifest["pkg"]["type"] == "dir"
    assert manifest["pkg"]["sha256"] is None
    assert manifest["pkg"]["target"] is None
    assert manifest["pkg"]["mode"] in (0o644, 0o755)
    assert manifest["pkg/nested.txt"]["sha256"] == hashlib.sha256(b"nested\n").hexdigest()
    # Git's own directory rewrites itself on every command, so a manifest that
    # walked it would never match twice.
    assert [path for path in manifest if path == ".git" or path.startswith(".git/")] == []


@NEEDS_EXECUTABLE_BIT
def test_build_manifest_records_the_executable_bit_and_nothing_else_of_the_mode(
    tmp_path,
):
    # Nothing in either name says which of the two is runnable: the bit does.
    runnable = tmp_path / "run"
    runnable.write_bytes(b"#!/bin/sh\nexit 0\n")
    runnable.chmod(0o755)
    # A second executable, sharing neither name nor extension with the first, so
    # no rule keyed on a filename can report both.
    also_runnable = tmp_path / "calc.py"
    also_runnable.write_bytes(b"def add(left, right):\n    return left + right\n")
    also_runnable.chmod(0o755)
    inert = tmp_path / "install.sh"
    inert.write_bytes(b"#!/bin/sh\nexit 0\n")
    inert.chmod(0o644)
    private = tmp_path / "private.txt"
    private.write_bytes(b"private\n")
    private.chmod(0o600)

    manifest = trees.build_manifest(tmp_path)

    assert manifest["run"]["mode"] == 0o755
    assert manifest["calc.py"]["mode"] == 0o755
    # Read off the filesystem, not off the extension: a shell script nobody
    # marked executable is not executable, whatever it is called.
    assert manifest["install.sh"]["mode"] == 0o644
    # The executable bit only: the group and other bits a umask happens to set
    # are not part of what a tree is proved against.
    assert manifest["private.txt"]["mode"] == 0o644


@NEEDS_SYMLINKS
def test_build_manifest_records_a_symlink_by_its_raw_target_and_hashes_nothing(tmp_path):
    (tmp_path / "calc.py").write_bytes(b"def add(left, right):\n    return left + right\n")
    (tmp_path / "pkg").mkdir()
    os.symlink(os.path.join("..", "calc.py"), tmp_path / "pkg" / "alias.py")

    entry = trees.build_manifest(tmp_path)["pkg/alias.py"]

    assert entry["type"] == "symlink"
    assert entry["sha256"] is None
    # The link text as written, not where it lands: a resolved target is an
    # absolute path that differs between two clones of the same tree.
    assert not Path(entry["target"]).is_absolute()
    assert Path(entry["target"]).as_posix() == "../calc.py"


# `prove_state` has a module of its own, test_eval_tree_proofs.py, and
# `snapshot` and `apply_patch` have test_eval_tree_patches.py: this one stands
# at the size the project caps a test file at.

# -- contained -------------------------------------------------------------


@pytest.fixture
def tree_and_outside(tmp_path):
    """A tree, and a directory beside it holding files the tree names too.

    Both sides carry a `calc.py` and a name that reads like a secret, so no
    check on the spelling of a path can tell the two apart - only where the
    path lands can.
    """
    root = tmp_path / "tree"
    (root / "pkg").mkdir(parents=True)
    (root / "pkg" / "calc.py").write_bytes(b"inside\n")
    (root / "pkg" / "secret.txt").write_bytes(b"inside\n")
    (root / "passwd").write_bytes(b"inside\n")
    outside = tmp_path / "outside"
    outside.mkdir()
    for name in ("secret.txt", "passwd", "calc.py"):
        (outside / name).write_bytes(b"outside\n")
    return root, outside


def test_contained_returns_the_path_a_relative_spelling_names(tree_and_outside):
    root, _ = tree_and_outside

    inside = trees.contained(root, "pkg/calc.py")

    assert Path(inside).read_bytes() == b"inside\n"
    assert Path(inside).resolve() == (root / "pkg" / "calc.py").resolve()


@pytest.mark.parametrize(
    "relpath",
    ["pkg/not-created-yet.py", "tests/test_extra.py"],
    ids=["under-a-directory-that-exists", "under-a-directory-that-does-not"],
)
def test_contained_answers_for_a_destination_the_tree_does_not_hold_yet(
    tree_and_outside, relpath
):
    root, _ = tree_and_outside

    destination = Path(trees.contained(root, relpath))

    # This guards where a write lands, and a write lands on a path that is not
    # there yet: `overlay_oracle` creates the parents it needs. Containment is
    # about where a path points, so refusing every path the tree does not
    # already hold would refuse the only calls that need guarding.
    assert not destination.exists()
    assert destination.resolve() == (root / relpath).resolve()
    assert destination.resolve().is_relative_to(root.resolve())


@pytest.mark.parametrize("name", ["secret.txt", "passwd", "calc.py"])
def test_contained_refuses_an_absolute_path(tree_and_outside, name):
    root, outside = tree_and_outside

    with pytest.raises(trees.TreeError):
        trees.contained(root, str(outside / name))


@pytest.mark.parametrize(
    "relpath",
    [
        "../outside/secret.txt",
        "pkg/../../outside/passwd",
        "../outside/calc.py",
    ],
    ids=[
        "climbs-from-the-root",
        "climbs-back-out-of-a-subdirectory",
        "reaches-a-name-the-tree-carries-too",
    ],
)
def test_contained_refuses_a_path_that_climbs_out_of_the_tree(tree_and_outside, relpath):
    root, _ = tree_and_outside

    with pytest.raises(trees.TreeError):
        trees.contained(root, relpath)


@pytest.mark.parametrize("relpath", ["pkg/secret.txt", "passwd", "pkg/calc.py"])
def test_contained_accepts_an_in_tree_path_that_a_refused_one_also_names(
    tree_and_outside, relpath
):
    root, _ = tree_and_outside

    # Every one of these names appears in a path refused above. What is refused
    # there is leaving the tree, so a guard reading names instead of locations
    # locks the tree's own files out.
    assert Path(trees.contained(root, relpath)).read_bytes() == b"inside\n"


@NEEDS_SYMLINKS
def test_contained_refuses_a_path_that_crosses_a_symlink_out_of_the_tree(
    tree_and_outside,
):
    root, outside = tree_and_outside
    os.symlink(str(outside), root / "escape", target_is_directory=True)

    # Every component of this path is an ordinary name; the escape is the link.
    with pytest.raises(trees.TreeError):
        trees.contained(root, "escape/secret.txt")


# -- overlay_oracle --------------------------------------------------------


def test_overlay_oracle_copies_the_recorded_oracle_over_the_clone(tmp_path, built_repo):
    template = _sealed_template(tmp_path, built_repo)
    clone = Path(trees.fresh_clone(template, tmp_path / "clone"))
    evidence = tmp_path / "evidence"
    (evidence / "oracle" / "tests").mkdir(parents=True)
    (evidence / "oracle" / built_repo["test"]).write_text(
        eval_harness_fixtures.WIDENED_ORACLE, encoding="utf-8"
    )
    (evidence / "oracle" / "tests" / "test_extra.py").write_text(
        EXTRA_ORACLE, encoding="utf-8"
    )
    # Stored beside the oracle but not listed as part of it.
    (evidence / "oracle" / "tests" / "test_unlisted.py").write_text(
        "# no task declared this file\n", encoding="utf-8"
    )

    trees.overlay_oracle(evidence, clone, [built_repo["test"], "tests/test_extra.py"])

    assert (clone / built_repo["test"]).read_text(encoding="utf-8") == (
        eval_harness_fixtures.WIDENED_ORACLE
    )
    # Nothing under `tests/` stood in the sealed tree, so the copy had to make it.
    assert (clone / "tests" / "test_extra.py").read_text(encoding="utf-8") == EXTRA_ORACLE
    # The listed paths and no others: copying the whole oracle directory would
    # drag this one in and judge the candidate against a test nobody declared.
    assert not (clone / "tests" / "test_unlisted.py").exists()
    # The overlay replaces the oracle and leaves the rest of the tree alone.
    assert (clone / built_repo["impl"]).read_text(encoding="utf-8") == (
        eval_harness_fixtures.BROKEN_IMPL
    )


# -- commit_all ------------------------------------------------------------


def test_commit_all_commits_every_change_and_returns_the_new_head(tmp_path, built_repo):
    template = _sealed_template(tmp_path, built_repo)
    clone = Path(trees.fresh_clone(template, tmp_path / "clone"))
    sealed = trees.head_sha(clone)
    _candidate_changes(clone, built_repo)

    sha = trees.commit_all(clone, "what the candidate left behind")

    assert SHA1.fullmatch(sha), sha
    assert sha != sealed
    assert trees.head_sha(clone) == sha
    # Edited, added and deleted alike: nothing is left uncommitted.
    assert _git(clone, "status", "--porcelain", "--untracked-files=all") == ""
    assert _git(clone, "log", "-1", "--format=%s") == "what the candidate left behind"


# -- mise_trust ------------------------------------------------------------


@pytest.mark.parametrize("marker", [".mise.toml", "mise.toml", ".tool-versions"])
def test_mise_trust_trusts_a_tree_that_carries_a_mise_config(tmp_path, monkeypatch, marker):
    root = tmp_path / "tree"
    root.mkdir()
    (root / marker).write_text("python 3.12.0\n", encoding="utf-8")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    argv_file = tmp_path / "argv.txt"
    cwd_file = tmp_path / "cwd.txt"
    eval_harness_fixtures.write_argv_recording_stub(
        bin_dir, "mise", argv_file, cwd_file=cwd_file
    )
    monkeypatch.setenv("PATH", str(bin_dir))

    trees.mise_trust(root)

    assert argv_file.is_file(), "mise never ran for a tree that declares its tools"
    argv = argv_file.read_text(encoding="utf-8").splitlines()
    assert argv[:1] == ["trust"]
    # In the tree: the directory the command ran in is the tree itself, not
    # whatever directory the harness happened to be standing in. A trust granted
    # somewhere else is a trust the tree never got.
    ran_in = Path(cwd_file.read_text(encoding="utf-8").strip())
    assert ran_in.resolve() == root.resolve(), (argv, ran_in)


def test_mise_trust_leaves_a_tree_that_declares_no_tools_alone(tmp_path, monkeypatch):
    root = tmp_path / "tree"
    root.mkdir()
    (root / "calc.py").write_text("def add(left, right):\n    return 0\n", encoding="utf-8")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    argv_file = tmp_path / "argv.txt"
    eval_harness_fixtures.write_argv_recording_stub(bin_dir, "mise", argv_file)
    monkeypatch.setenv("PATH", str(bin_dir))

    trees.mise_trust(root)

    assert not argv_file.exists(), "mise ran in a tree that never asked to be trusted"


def test_mise_trust_does_not_raise_when_mise_is_absent_from_the_path(tmp_path, monkeypatch):
    root = tmp_path / "tree"
    root.mkdir()
    (root / ".mise.toml").write_text("[tools]\npython = '3.12'\n", encoding="utf-8")
    empty = tmp_path / "empty-bin"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    assert shutil.which("mise") is None, "this host still resolves mise somehow"

    # A host without mise still has to be able to run the whole suite, so an
    # absent tool is not an error: the call answers with nothing at all.
    assert trees.mise_trust(root) is None
