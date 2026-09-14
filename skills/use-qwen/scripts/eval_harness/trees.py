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


def _land(links: dict[str, str], path: str, active: frozenset[str] = frozenset()) -> str:
    """Where `path` lands in a tree whose symlinks are `links` (relpath -> text).

    Followed hop by hop, each link from its own directory, the way the OS would
    walk it: a chain is judged by where it ends, not by how its text reads. A
    `..` past the root is an escape and a link met again while it is still
    being followed is a cycle; both are refused as a TreeError, and the walk
    goes no deeper than the tree has distinct links.
    """
    landing = ""
    for name in Path(path).as_posix().split("/"):
        if name == ".":
            continue
        if name == "..":
            if not landing:
                raise TreeError("%s leaves the tree" % path)
            landing = posixpath.dirname(landing)
            continue
        landing = posixpath.join(landing, name)
        if landing not in links:
            continue
        if landing in active:
            raise TreeError("%s is a link cycle" % landing)
        target = links[landing]
        if os.path.isabs(target):
            raise TreeError("%s leaves the tree: %s" % (landing, target))
        landing = _land(
            links, posixpath.join(posixpath.dirname(landing), target), active | {landing}
        )
    return landing


def _refuse_escaping_links(root: Path) -> None:
    """Refuse a tree whose symlinks reach past it, before anything copies it.

    `copytree(symlinks=True)` reproduces such a link faithfully, and a later
    write through it would reach the operator's own repository.
    """
    links = {relpath: os.readlink(path) for relpath, path in _walk(root) if path.is_symlink()}
    for relpath in links:
        _land(links, relpath)


def build_template(repo: Path, first: str, dest: Path) -> str:
    """Seal the tree before `first` at `dest` as one commit, and answer its sha.

    The commit handed in is the one sealed, never the repo's current head: work
    that landed after the task must not reach the tree the task is measured on.
    """
    bundle = _git_bytes(repo, "archive", "--format=tar", "%s^" % first)
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(bundle)) as archive:
        # Read off the archive rather than off an extracted tree: a host that
        # cannot create a symlink at all still has to refuse one that escapes,
        # and refusing here leaves no half-built template behind.
        links = {member.name: member.linkname for member in archive.getmembers() if member.issym()}
        for name in links:
            _land(links, name)
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
    """Hash each of `paths` under `root`, keyed in slash form.

    Each path is contained before it is read: a link that resolves outside the
    tree is refused, never dereferenced, so no outside bytes reach a digest.
    """
    root = Path(root)
    return {Path(relpath).as_posix(): _digest(contained(root, relpath)) for relpath in paths}


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
    """Commit everything the tree carries, edits, additions and deletions alike.

    An unchanged tree still lands a commit: an oracle overlay that rewrites
    nothing needs a sealed head of its own for the gate to rebuild against.
    """
    _git(clone, "add", "-A")
    _git(clone, *IDENTITY, "commit", "--allow-empty", "-m", message)
    return head_sha(clone)


def _changes(tokens: Iterator[str]) -> Iterator[dict]:
    """The records in a `git diff --name-status -z` stream, each status as git wrote it.

    An edit, addition or deletion is `<status> <path>`; a rename or copy is
    `<status> <old> <new>`, filed under the name the tree holds now.
    """
    for status in tokens:
        if status[0] in "RC":
            old_path = next(tokens)
            yield {"status": status, "path": next(tokens), "old_path": old_path}
        else:
            yield {"status": status, "path": next(tokens), "old_path": None}


def snapshot(clone: Path, sealed_sha: str) -> tuple[list[dict], str]:
    """Read the work in `clone` back out as a change list and a git patch.

    The intent-to-add pass is what puts an untracked file in a diff at all; the
    reset takes it back off, so reading the tree is not a change to it, even
    when a read in between fails. The patch is decoded with surrogateescape so
    that encoding it back the same way gives git's bytes exactly: a candidate's
    non-UTF-8 edit is still an observation, not an error. The change listing is
    read NUL-delimited and decoded the same way: git's text form quotes and
    escapes any name outside plain ASCII, and a path read from that form names
    nothing in the tree.
    """
    _git(clone, "add", "-N", ".")
    try:
        listing = _git_bytes(clone, "diff", "--name-status", "-z", sealed_sha)
        patch = _git_bytes(clone, "diff", "--binary", sealed_sha)
    finally:
        _git(clone, "reset", "-q")
    diff_text = patch.decode("utf-8", "surrogateescape")
    tokens = (token.decode("utf-8", "surrogateescape") for token in listing.split(b"\0")[:-1])
    return list(_changes(tokens)), diff_text


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
