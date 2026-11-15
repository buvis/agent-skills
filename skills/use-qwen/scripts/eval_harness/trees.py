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
import unicodedata
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

# The date every sealed template commit carries, so its sha names the tree alone.
SEAL_DATE = "2000-01-01T00:00:00+00:00"

# Files that say a tree declares its own toolchain.
MISE_MARKERS = (".mise.toml", "mise.toml", ".tool-versions")

_GIT_TIMEOUT_S = 120
_APPLY_TIMEOUT_S = 120.0


class TreeError(RuntimeError):
    """Raised when a tree, or a path inside one, is not one the harness may use."""


def _git(root: Path, *args: str, env: dict[str, str] | None = None) -> str:
    """Git's stdout in `root`, trailing newlines only: porcelain's leading space stays."""
    done = subprocess.run(
        ["git", "-C", str(root), *args],
        capture_output=True,
        text=True,
        check=True,
        timeout=_GIT_TIMEOUT_S,
        env=env,
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


def _fold(name: str) -> str:
    """`name` as a name-merging host would key it, for comparison only.

    A tar validated on one host is extracted on another, so the archive rules
    have to judge for the host that merges names. Two mergings matter: case, so
    that `A` and `a` are one place on macOS and Windows, and normalization form,
    so that the composed and decomposed spellings of `é` are one place on APFS.

    `str.lower`, not `str.casefold`: real filesystems do simple case folding,
    and APFS and NTFS both keep `straße.txt` and `strasse.txt` as two files,
    which full Unicode folding would merge. NFC rather than NFD because it is
    the composed form most sources already emit; either direction works as long
    as one is chosen and used on both sides of every comparison.

    Comparison only: no separator handling and no `.`/`..` walking. Never write
    or store the result.
    """
    return unicodedata.normalize("NFC", name).lower()


def _land(
    links: dict[str, str],
    path: str,
    active: frozenset[str] = frozenset(),
    *,
    fold: bool = False,
    crossed: set[str] | None = None,
) -> str:
    """Where `path` lands in a tree whose symlinks are `links` (relpath -> text).

    Followed hop by hop, each link from its own directory, the way the OS would
    walk it: a chain is judged by where it ends, not by how its text reads. A
    `..` past the root is an escape and a link met again while it is still
    being followed is a cycle; both are refused as a TreeError, and the walk
    goes no deeper than the tree has distinct links.

    `links` is always raw-keyed. With `fold=True` each hop is matched under
    `_fold`, the way a name-merging host walks it, so a link pointing at such an
    alias of itself is a cycle on that host. The landing returned keeps its raw
    spelling either way - a folded value is a lookup key, never a path.
    `crossed`, when given, collects the folded slot of every symlink the walk
    passes through, at any depth and inside a link target's own resolution.
    """
    keyed = {(_fold(key) if fold else key): key for key in links}
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
        probe = _fold(landing) if fold else landing
        if probe not in keyed:
            continue
        if crossed is not None:
            crossed.add(probe)
        if probe in active:
            raise TreeError("%s is a link cycle" % landing)
        target = links[keyed[probe]]
        if os.path.isabs(target) or _archive_name_escapes(target):
            raise TreeError("%s leaves the tree: %s" % (landing, target))
        landing = _land(
            links, posixpath.join(posixpath.dirname(landing), target),
            active | {probe}, fold=fold, crossed=crossed,
        )
    return landing


def _archive_name_escapes(text: str) -> bool:
    """True iff `text` (a member name or a symlink target, archive-domain
    text - never a host path) names or reaches outside a tree root under
    either the POSIX or the Windows path-reading rules.

    Refuses, independent of the host OS:
      - POSIX-absolute: starts with "/".
      - Drive-absolute: matches `^[A-Za-z]:[/\\]`  (e.g. "C:\\x", "C:/x").
      - Drive-relative: matches `^[A-Za-z]:[^/\\]` (e.g. "C:x") - no
        leading separator after the drive letter.
      - Rooted backslash: starts with "\\" but is not a UNC/extended prefix
        below.
      - UNC: starts with "\\\\" followed by a non-"?"/"." component
        (`\\\\host\\share`).
      - Extended-length prefixes: starts with "\\\\?\\" or "\\\\.\\".
      - NTFS stream-like: a path component containing ":" after position 0
        that is not the drive-letter colon already matched above (catches
        `name:stream`) - checked on EVERY path component, not only the last.
      - Any backslash at all, anywhere in the text: `"\\" in text`. `_land`
        splits only on `/`, so a name like `sub\\..\\..\\outside\\file` is
        one opaque component to it - no `/` means no `..`-climb is ever
        seen - yet on an actual Windows filesystem `\\` IS a separator, so
        the OS-level write this member eventually causes would climb for
        real. Refusing any embedded backslash outright closes this.
    Does not itself walk `..` segments - that stays `_land`'s job.
    """
    # Any backslash covers the rooted, UNC and extended-length forms; a colon
    # past the first character of a component covers both drive forms (`C:`
    # and `C:x` are components holding one) as well as an NTFS stream.
    if text.startswith("/") or "\\" in text:
        return True
    return any(":" in component[1:] for component in text.split("/"))


def _ancestor_crossing(members: Sequence[tarfile.TarInfo], links: dict[str, str]) -> None:
    """Refuse any member whose path has an archive symlink as a proper
    ancestor, judged on where that symlink itself *lands* - not on whether
    its raw name textually prefixes the member's name.

    `links` is the `{normalized member name: linkname}` map. Each symlink's own
    location is its raw name with every segment but the last resolved through
    `_land`, folded, so a chain of links earlier in its path redirects it in
    full. Every proper prefix of every member's raw name is then landed the same
    way, and the question is which symlink slots that walk crossed: a prefix
    landed under `fold=True` dereferences the link it reaches, so the landing
    alone can no longer say that it went through one.
    """
    symlink_landings: set[str] = set()
    for member in members:
        if member.issym():
            segments = member.name.split("/")
            symlink_landings.add(
                _fold(
                    posixpath.join(
                        _land(links, "/".join(segments[:-1]), fold=True), segments[-1]
                    )
                )
            )
    for member in members:
        segments = member.name.split("/")
        for end in range(1, len(segments)):
            crossed: set[str] = set()
            _land(links, "/".join(segments[:end]), fold=True, crossed=crossed)
            if crossed & symlink_landings:
                raise TreeError("%s is beneath an archive symlink" % member.name)


def _refuse_escaping_links(root: Path) -> None:
    """Refuse a tree whose symlinks reach past it, before anything copies it.

    `copytree(symlinks=True)` reproduces such a link faithfully, and a later
    write through it would reach the operator's own repository.
    """
    links = {relpath: os.readlink(path) for relpath, path in _walk(root) if path.is_symlink()}
    for relpath in links:
        _land(links, relpath)


def _refuse_duplicate_or_crossing_members(members: Sequence[tarfile.TarInfo]) -> None:
    """Refuse an archive whose extraction order a link graph cannot describe.

    A name met twice means extraction order, not the final name table, decides
    what a later write reaches, so a repeat is refused outright. Every member,
    not only the links, is then walked hop by hop, on its *own* text: a name
    normalized ahead of the walk (`alias/../outside/x` -> `outside/x`) throws
    away the very hop through `alias` that `_land` exists to judge. A hardlink
    is refused outright - unlike a symlink it names bytes directly, so there is
    no hop for `_land` to walk and no way to tell where it really points.
    Two members that land in the same place, however their names read, are as
    much a collision as one name met twice: `alias -> pkg` plus `alias/file`
    reaches the same place as `pkg/file`, and extraction order would decide
    which one wins.
    """
    names = set()
    folded = set()
    for member in members:
        if _archive_name_escapes(member.name) or (
            member.issym() and _archive_name_escapes(member.linkname)
        ):
            raise TreeError("%s names a place outside the tree" % member.name)
        if os.path.isabs(member.name):
            raise TreeError("%s is absolute" % member.name)
        if not (member.isfile() or member.isdir() or member.issym()):
            raise TreeError("%s is not a file, directory or symlink" % member.name)
        name = posixpath.normpath(member.name)
        if name in names:
            raise TreeError("%s is a duplicate member" % name)
        # A name-merging filesystem lands these two names on one file.
        if _fold(name) in folded:
            raise TreeError("%s differs from another member only in case" % name)
        names.add(name)
        folded.add(_fold(name))
    links = {posixpath.normpath(m.name): m.linkname for m in members if m.issym()}
    _refuse_colliding_landings(members, links)
    _ancestor_crossing(members, links)


def _refuse_colliding_landings(members: Sequence[tarfile.TarInfo], links: dict[str, str]) -> None:
    """Refuse two members that land in one place, or one beneath a file member."""
    landings: set[str] = set()
    files: set[str] = set()
    for member in members:
        original = member.name
        landing = _land(links, original, fold=True)
        # Walked whole, a symlink lands wherever it points; the place it takes
        # up itself is its own name, with only its parent walked.
        if member.issym():
            parent, _, last = original.rpartition("/")
            landing = posixpath.join(_land(links, parent, fold=True), last)
        if landing in landings:
            raise TreeError("%s is a duplicate member" % original)
        landings.add(landing)
        if member.isfile():
            files.add(landing)
    # A file at any ancestor of a landing: one of the two writes has to fail
    # or replace the other, whichever comes first in the archive.
    for landing in landings:
        ancestor = posixpath.dirname(landing)
        while ancestor:
            if ancestor in files:
                raise TreeError("%s is beneath a file member" % landing)
            ancestor = posixpath.dirname(ancestor)


def _safe_mode(mode: int) -> int:
    """Strip setuid, setgid, sticky, and group/other write from a file mode.

    Directory archive modes are ignored by the extractor.
    """
    return mode & ~(stat.S_ISUID | stat.S_ISGID | stat.S_ISVTX | stat.S_IWGRP | stat.S_IWOTH)


def _symlink_targets_a_directory(member: tarfile.TarInfo, members: Sequence[tarfile.TarInfo]) -> bool:
    """`os.symlink`'s `target_is_directory` only matters on Windows, where a
    link's reparse-point type is fixed at creation; the archive's own member
    graph is the only sound source for it, never the link text alone.
    """
    links = {posixpath.normpath(m.name): m.linkname for m in members if m.issym()}
    directories = {_fold(posixpath.normpath(m.name)) for m in members if m.isdir()}
    directories.add(".")
    for candidate in members:
        parent = posixpath.dirname(posixpath.normpath(candidate.name))
        while parent:
            directories.add(_fold(parent))
            parent = posixpath.dirname(parent)
    parent = posixpath.dirname(member.name)
    landing = _land(links, posixpath.join(parent, member.linkname), fold=True)
    return _fold(posixpath.normpath(landing)) in directories


def _extract_without_filter(
    archive: tarfile.TarFile, dest: Path, members: Sequence[tarfile.TarInfo]
) -> None:
    """Extract `members` into `dest` with the policy `filter="data"` applies,
    for a tarfile build with no `data_filter` at all.

    The archive's uid, gid and owner names are never read: nothing here chowns,
    whoever runs it. `members` holds no symlinks: `_lay_links_typed` lays
    them once every file and directory exists.

    Directory modes are ignored, as with `data_filter`: mkdir's default mode
    and the process umask apply, including to implicitly created parents.
    """
    for member in members:
        path = dest.joinpath(member.name)
        try:
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                path.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as source, open(path, "wb") as target:
                    shutil.copyfileobj(source, target)
                # Owner read/write is floored on, the way `filter="data"`
                # floors it, so a member mode of 0 still leaves the file one
                # `git add` can read back.
                os.chmod(path, _safe_mode(member.mode) | stat.S_IRUSR | stat.S_IWUSR)
        except OSError as cause:
            raise TreeError(f"{member.name}: {cause}") from cause


def _lay_links_typed(dest: Path, members: Sequence[tarfile.TarInfo]) -> None:
    """Create every symlink member under `dest`, in archive order, once every
    file and directory member already exists there.

    Windows types a link as a file or a directory when it is made, and tarfile
    types it as a file whatever it names; the type comes from the archive's own
    member graph. Windows also stores relative text verbatim, and a `/` in it
    leaves the link unreadable, so the text is written in host-separator form:
    separators only, every hop preserved.
    """
    for member in members:
        if not member.issym():
            continue
        path = dest.joinpath(member.name)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            os.symlink(
                member.linkname.replace("/", os.sep), path,
                target_is_directory=_symlink_targets_a_directory(member, members),
            )
        except OSError as cause:
            raise TreeError(f"{member.name}: {cause}") from cause


def _extract_bundle(bundle: bytes, staging: Path) -> list[tarfile.TarInfo]:
    """Extract the tar `bundle` into `staging`, and answer its members.

    Files and directories first, through `filter="data"` where this tarfile
    has one; the vetted links last, typed and in host-separator form.
    """
    with tarfile.open(fileobj=io.BytesIO(bundle)) as archive:
        # Read off the archive rather than off an extracted tree: a host that
        # cannot create a symlink at all still has to refuse one that escapes,
        # and refusing here leaves no half-built template behind.
        members = archive.getmembers()
        _refuse_duplicate_or_crossing_members(members)
        ordinary = [member for member in members if not member.issym()]
        if callable(getattr(tarfile, "data_filter", None)):
            try:
                archive.extractall(staging, members=ordinary, filter="data")
            except (tarfile.FilterError, OSError) as cause:
                raise TreeError("extraction failed: %s" % cause) from cause
        else:
            _extract_without_filter(archive, staging, ordinary)
    _lay_links_typed(staging, members)
    return members


def _topmost_missing_ancestor(path: Path) -> Path | None:
    """The highest directory in `path`'s chain that does not exist yet, or `None`."""
    missing = None
    probe = path
    while not probe.exists():
        missing = probe
        probe = probe.parent
    return missing


def _seal_template(staging: Path) -> str:
    """Commit the staged tree with a stable date, translating git failures."""
    dated = {**os.environ, "GIT_AUTHOR_DATE": SEAL_DATE, "GIT_COMMITTER_DATE": SEAL_DATE}
    try:
        _git(staging, *IDENTITY, "init")
        _git(staging, "add", "-A")
        _git(staging, *IDENTITY, "commit", "-m", "sealed pre-task tree", env=dated)
        return head_sha(staging)
    except (OSError, subprocess.SubprocessError) as cause:
        raise TreeError("template seal failed: %s" % cause) from cause


def build_template(repo: Path, first: str, dest: Path) -> str:
    """Seal the tree before `first` at `dest` as one commit, and answer its sha.

    The commit handed in is the one sealed, never the repo's current head: work
    that landed after the task must not reach the tree the task is measured on.

    Raises TreeError, and leaves `dest` exactly as it was, if anything - a file,
    a directory (empty or not), or a dangling symlink - already sits at `dest`
    before extraction starts.
    """
    bundle = _git_bytes(repo, "archive", "--format=tar", "%s^" % first)
    dest = Path(dest)
    if os.path.lexists(dest):
        raise TreeError(f"{dest} already exists")
    # Built and sealed beside `dest`, then renamed into place: a failure at any
    # step leaves no half-built template where the caller looks for one.
    staging = dest.parent / (dest.name + ".staging-" + os.urandom(4).hex())
    # staging.mkdir(parents=True) may create dest's absent ancestors; a
    # failed build must remove those too, or a refusal leaves them behind.
    created_ancestor = _topmost_missing_ancestor(dest.parent)
    try:
        try:
            staging.mkdir(parents=True)
        except OSError as cause:
            raise TreeError("%s could not be staged: %s" % (staging, cause)) from cause
        _extract_bundle(bundle, staging)
        sealed = _seal_template(staging)
        try:
            staging.rename(dest)
        except OSError as cause:
            raise TreeError("%s could not be published: %s" % (dest, cause)) from cause
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        if created_ancestor is not None:
            shutil.rmtree(created_ancestor, ignore_errors=True)
        raise
    return sealed


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
    outside - never a name that merely reads like one. Judged the same way
    the write-side ancestor walk is: by landing `relpath` through `root`'s own
    links map via `_land`, never by resolving the path through the OS and
    comparing prefixes, which a Windows-shaped link target (an absolute drive
    or UNC path `Path.resolve()` would leave untouched on a POSIX host) can
    walk straight past.
    """
    if os.path.isabs(relpath):
        raise TreeError("%s is absolute" % relpath)
    root = Path(root)
    links = {name: os.readlink(path) for name, path in _walk(root) if path.is_symlink()}
    landing = _land(links, relpath)
    return root / landing


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
