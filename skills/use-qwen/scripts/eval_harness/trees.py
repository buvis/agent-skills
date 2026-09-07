"""The trees of the qwen evaluation harness: templates, clones, proofs, patches.

Every attempt runs in a tree of its own: a template sealed once from the commit
before the task, a fresh copy of that template per attempt, and a proof that the
copy is still what was recorded before anything runs inside it. Nothing here
trusts a path a task hands over - every write the harness makes is placed by
`contained` first, and a tree whose symlinks reach past it is refused outright.
"""
import hashlib
import io
import os
import posixpath
import shutil
import stat
import subprocess
import tarfile
from collections.abc import Iterator, Sequence
from pathlib import Path

from eval_harness.runner import CommandResult, run_bounded

# Identity and branch name on every invocation that writes history: a CI runner
# carries no global git config, and the harness must not depend on the
# operator's either.
IDENTITY = (
    "-c", "user.name=eval-harness",
    "-c", "user.email=eval-harness@local",
    "-c", "init.defaultBranch=main",
)

# Files that say a tree declares its own toolchain.
MISE_MARKERS = (".mise.toml", "mise.toml", ".tool-versions")

_GIT_TIMEOUT_S = 120
_APPLY_TIMEOUT_S = 120.0


class TreeError(RuntimeError):
    """Raised when a tree, or a path inside one, is not one the harness may use."""


def _git(root: Path, *args: str) -> str:
    """Git's stdout in `root`, trailing newlines only: porcelain's leading space stays."""
    done = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
        timeout=_GIT_TIMEOUT_S,
    )
    return done.stdout.rstrip("\n")


def _git_bytes(root: Path, *args: str) -> bytes:
    """Git's stdout in `root`, byte for byte: a patch is not a re-encoded string."""
    done = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        check=True,
        timeout=_GIT_TIMEOUT_S,
    )
    return done.stdout


def _walk(root: Path) -> Iterator[tuple[str, Path]]:
    """Every path under `root` except `.git`, as (slash-form relpath, path).

    Git's own directory rewrites itself on every command, so a walk that entered
    it would describe a tree that never matches twice.
    """
    for current, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name != ".git"]
        for name in sorted(dirnames + filenames):
            path = Path(current) / name
            yield path.relative_to(root).as_posix(), path


def _escapes(relpath: str, target: str) -> bool:
    """Whether a symlink at `relpath` pointing at `target` lands outside the tree."""
    if os.path.isabs(target):
        return True
    landing = posixpath.normpath(
        posixpath.join(posixpath.dirname(relpath), Path(target).as_posix())
    )
    return landing == ".." or landing.startswith("../")


def _refuse_escaping_links(root: Path) -> None:
    """Refuse a tree whose symlinks reach past it, before anything copies it.

    `copytree(symlinks=True)` reproduces such a link faithfully, and a later
    write through it would reach the operator's own repository.
    """
    for relpath, path in _walk(root):
        if path.is_symlink() and _escapes(relpath, os.readlink(path)):
            raise TreeError("%s leaves the tree: %s" % (relpath, os.readlink(path)))


def build_template(repo: Path, first: str, dest: Path) -> str:
    """Seal the tree before `first` at `dest` as one commit, and answer its sha.

    The commit handed in is the one sealed, never the repo's current head: work
    that landed after the task must not reach the tree the task is measured on.
    """
    bundle = _git_bytes(repo, "archive", "--format=tar", "%s^" % first)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(bundle)) as archive:
        for member in archive.getmembers():
            # Read off the archive rather than off an extracted tree: a host that
            # cannot create a symlink at all still has to refuse one that escapes,
            # and refusing here leaves no half-built template behind.
            if member.issym() and _escapes(member.name, member.linkname):
                raise TreeError("%s leaves the tree: %s" % (member.name, member.linkname))
        archive.extractall(dest)
    _git(dest, *IDENTITY, "init")
    _git(dest, "add", "-A")
    _git(dest, *IDENTITY, "commit", "-m", "sealed pre-task tree")
    return head_sha(dest)


def fresh_clone(template: Path, dest: Path) -> Path:
    """Copy the sealed template to `dest`, bytes and symlinks alike."""
    _refuse_escaping_links(Path(template))
    shutil.copytree(template, dest, symlinks=True)
    return Path(dest)


def _digest(path: Path) -> str:
    """The sha256 of the bytes at `path`, or `absent` where there are none.

    A directory has no bytes, and neither has a link to one; a link to a file
    hashes what the link reaches.
    """
    if not path.is_file():
        return "absent"
    return hashlib.sha256(path.read_bytes()).hexdigest()


def hash_paths(root: Path, paths: Sequence[str]) -> dict[str, str]:
    """Hash each of `paths` under `root`, keyed in slash form."""
    root = Path(root)
    return {Path(relpath).as_posix(): _digest(root / relpath) for relpath in paths}


def _entry(path: Path) -> dict:
    """One manifest entry: what the path is, what it holds, and its executable bit."""
    mode = 0o755 if path.lstat().st_mode & stat.S_IXUSR else 0o644
    if path.is_symlink():
        # The link text as written. A resolved target is an absolute path, and
        # two clones of one tree would then never describe it the same way.
        return {"type": "symlink", "sha256": None, "target": os.readlink(path), "mode": mode}
    if path.is_dir():
        return {"type": "dir", "sha256": None, "target": None, "mode": mode}
    return {"type": "file", "sha256": _digest(path), "target": None, "mode": mode}


def build_manifest(root: Path) -> dict[str, dict]:
    """Describe every path in the tree, so any later difference has a record to fail."""
    root = Path(root)
    return {relpath: _entry(path) for relpath, path in _walk(root)}


def head_sha(root: Path) -> str:
    """The commit `root` stands on."""
    return _git(root, "rev-parse", "HEAD").strip()


def prove_state(clone: Path, expected: dict, manifest: dict) -> tuple[str, list[str]]:
    """Answer whether `clone` is still the tree the records describe.

    The manifest carries the weight: `git status --porcelain` says nothing about
    an ignored file, and the two hash maps cover only the paths the task
    declared, so a stale build artefact, a rewritten shared setup file or a
    flipped mode reaches the gate unseen by everything else.
    """
    differing = set()
    for name in ("writable", "oracle"):
        recorded = expected[name]
        found = hash_paths(clone, list(recorded))
        differing.update(path for path, digest in recorded.items() if found[path] != digest)
    live = build_manifest(clone)
    differing.update(
        path for path in set(live) | set(manifest) if live.get(path) != manifest.get(path)
    )
    clean = _git(clone, "status", "--porcelain") == ""
    if clean and head_sha(clone) == expected["head_sha"] and not differing:
        return ("ok", [])
    return ("PREP_MISMATCH", sorted(differing))


def contained(root: Path, relpath: str) -> Path:
    """Place `relpath` inside `root`, or refuse it.

    This guards where a write lands, so a path the tree does not hold yet is
    legal and comes back to be written. What is refused is leaving the tree:
    an absolute path, a climb out of it, or a walk through a link that points
    outside - never a name that merely reads like one.
    """
    if os.path.isabs(relpath):
        raise TreeError("%s is absolute" % relpath)
    destination = Path(root) / relpath
    if not destination.resolve().is_relative_to(Path(root).resolve()):
        raise TreeError("%s lands outside the tree" % relpath)
    return destination


def overlay_oracle(evidence_dir: Path, clone: Path, oracle: Sequence[str]) -> None:
    """Copy the recorded oracle over the clone: the listed paths and no others."""
    for relpath in oracle:
        destination = contained(clone, relpath)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(Path(evidence_dir) / "oracle" / relpath, destination)


def commit_all(clone: Path, message: str) -> str:
    """Commit everything the tree carries, edits, additions and deletions alike."""
    _git(clone, "add", "-A")
    _git(clone, *IDENTITY, "commit", "-m", message)
    return head_sha(clone)


def _change(line: str) -> dict:
    """One `git diff --name-status` line as a record, its status left as git wrote it."""
    fields = line.split("\t")
    if fields[0][0] in "RC":
        # Filed under the name the tree holds now, remembering the one it lost.
        return {"status": fields[0], "path": fields[2], "old_path": fields[1]}
    return {"status": fields[0], "path": fields[1], "old_path": None}


def snapshot(clone: Path, sealed_sha: str) -> tuple[list[dict], str]:
    """Read the work in `clone` back out as a change list and a git patch.

    The intent-to-add pass is what puts an untracked file in a diff at all; the
    reset takes it back off, so reading the tree is not a change to it.
    """
    _git(clone, "add", "-N", ".")
    listing = _git(clone, "diff", "--name-status", sealed_sha)
    diff_text = _git_bytes(clone, "diff", "--binary", sealed_sha).decode("utf-8")
    _git(clone, "reset", "-q")
    return [_change(line) for line in listing.splitlines() if line.strip()], diff_text


def mise_trust(root: Path) -> None:
    """Trust a tree that declares its own toolchain, if this host has mise at all.

    Never raises: a host without mise still has to be able to run the suite, so
    an absent or failing tool is ignored rather than answered for.
    """
    if not any((Path(root) / marker).exists() for marker in MISE_MARKERS):
        return
    mise = shutil.which("mise")
    if mise is None:
        return
    try:
        subprocess.run(
            [mise, "trust"],
            cwd=str(root),
            capture_output=True,
            check=False,
            timeout=_GIT_TIMEOUT_S,
        )
    except (OSError, subprocess.SubprocessError):
        return


def apply_patch(clone: Path, patch: Path, *, exclude: Sequence[str] = ()) -> CommandResult:
    """Replay a patch into `clone`, leaving each excluded path as the template left it.

    One `--exclude` per entry is how "canonical minus that path" is built: the
    patch lands whole apart from that one file, which is a different thing from
    applying it all and putting the path back afterwards. Git apply refuses a
    patch that writes outside the work tree of its own accord, which is the
    containment this call needs.
    """
    argv = ["git", "apply", "--binary"]
    argv.extend("--exclude=%s" % path for path in exclude)
    argv.append(str(patch))
    result, _tree = run_bounded(argv, Path(clone), _APPLY_TIMEOUT_S)
    return result
