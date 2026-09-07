"""What a reader watching a publication run would see, and the competitors that
race it for the destination name.

test_proposal_publication.py drives these: the watchers record where a run's
writes land and which directory it renames onto the name, and the competitors
take the name at the two instants a run stamped the same UTC second could
arrive for it."""

import builtins
import dataclasses
import os
from pathlib import Path

import proposal


def staged_siblings(out_dir):
    """Every `<out_dir>.partial-*` directory the contract stages into. A
    published run leaves none behind, and a failed one leaves none either."""
    if not out_dir.parent.is_dir():
        return []
    return sorted(out_dir.parent.glob(f"{out_dir.name}.partial-*"))


@dataclasses.dataclass(frozen=True)
class _WriteView:
    """One mid-run observation: the path the run is about to write, the identity
    of the directory receiving it, what the final directory holds at that
    instant, and which staging siblings stand."""

    target: Path
    parent_id: tuple[int, int]
    out_dir_contents: list[str]
    staged: list[str]


def _resolved(path):
    """Symlinks resolved, so a path recorded as `/var/...` and the same
    directory known as `/private/var/...` (macOS tmp_path) compare equal."""
    return Path(os.path.realpath(path))


def _staging_root(target, reservation):
    """The `<out_dir>.partial-*` sibling that `target` sits under, or None when
    the write landed anywhere else."""
    prefix = f"{reservation.name}.partial-"
    for parent in target.parents:
        if parent.parent == reservation.parent and parent.name.startswith(prefix):
            return parent
    return None


@dataclasses.dataclass(frozen=True)
class _Watch:
    """What one watched run showed: a view per write it made through a watched
    vector, and the identity of every directory it renamed onto the
    destination."""

    views: list[_WriteView]
    publishes: list[tuple[int, int]]


def _directory_id(path):
    """`path`'s filesystem identity - the pair that tells two directories apart,
    and that follows a directory when its name changes."""
    info = os.stat(path)
    return (info.st_dev, info.st_ino)


def watch_publication(monkeypatch, out_dir):
    """A watched run: mid-run views of `out_dir`, plus the identity of every
    directory renamed onto it.

    Each view keeps WHERE a write lands, what `out_dir` holds at that instant,
    and which staging siblings exist - what a reader watching `out_dir` while
    the run is in flight would see. Those views cover the vectors
    `_patch_write_vectors` wraps and no others, so they are evidence about those
    calls rather than proof that nothing else filled `out_dir`; `publishes`
    carries the positive half, which does not depend on catching every write."""
    views = []
    publishes = []

    def record(target):
        contents = sorted(path.name for path in out_dir.iterdir()) if out_dir.is_dir() else []
        views.append(
            _WriteView(
                target=_resolved(target),
                parent_id=_directory_id(Path(target).parent),
                out_dir_contents=contents,
                staged=[path.name for path in staged_siblings(out_dir)],
            )
        )

    def record_publish(source, target):
        if _resolved(target) == _resolved(out_dir):
            publishes.append(_directory_id(source))

    _patch_write_vectors(monkeypatch, record, record_publish)
    return _Watch(views=views, publishes=publishes)


def _patch_write_vectors(monkeypatch, record, record_publish):
    """Hand the write vectors below to `record`, which is passed the path each
    write lands on, and every rename-family call to `record_publish`, which is
    passed its source and its destination.

    This list of writes is deliberately NOT called complete: a directory can
    also be filled through `os.link`, `shutil`, or a subprocess, and none of
    those pass through here. `record` gathers evidence; what proves the
    destination appeared in one step is `record_publish`."""
    _patch_file_writes(monkeypatch, record)
    _patch_renames(monkeypatch, record, record_publish)


def _patch_file_writes(monkeypatch, record):
    """Hand every call below that can create a file to `record`, which is passed
    the path the write lands on."""
    real_write_text = Path.write_text
    real_path_open = Path.open
    real_builtin_open = builtins.open
    real_os_open = os.open

    def is_write(mode):
        return any(flag in str(mode) for flag in "wxa+")

    def watched_write_text(self, *args, **kwargs):
        record(self)
        return real_write_text(self, *args, **kwargs)

    def watched_path_open(self, mode="r", *args, **kwargs):
        if is_write(mode):
            record(self)
        return real_path_open(self, mode, *args, **kwargs)

    def watched_builtin_open(file, mode="r", *args, **kwargs):
        if is_write(mode) and isinstance(file, (str, bytes, os.PathLike)):
            record(os.fsdecode(file))
        return real_builtin_open(file, mode, *args, **kwargs)

    def watched_os_open(path, flags, *args, **kwargs):
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT):
            record(path)
        return real_os_open(path, flags, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", watched_write_text)
    monkeypatch.setattr(Path, "open", watched_path_open)
    monkeypatch.setattr(builtins, "open", watched_builtin_open)
    monkeypatch.setattr(os, "open", watched_os_open)


def _patch_renames(monkeypatch, record, record_publish):
    """Hand every rename-family call to `record`, which is passed the path the
    call lands on, and to `record_publish`, which is passed its source and its
    destination."""
    real_replace = os.replace
    real_rename = os.rename

    def watched_replace(src, dst, *args, **kwargs):
        record(dst)
        record_publish(src, dst)
        return real_replace(src, dst, *args, **kwargs)

    def watched_rename(src, dst, *args, **kwargs):
        record(dst)
        record_publish(src, dst)
        return real_rename(src, dst, *args, **kwargs)

    monkeypatch.setattr(os, "replace", watched_replace)
    monkeypatch.setattr(os, "rename", watched_rename)


def assert_never_built_in_place(watch, out_dir, published=None):
    """The destination appeared in one step.

    The decisive half is positive and vector-blind: the directory a reader ends
    up with IS the directory the run staged, moved onto the name by exactly one
    rename. A run that fills the destination entry by entry - through os.link, a
    copy, a subprocess, anything - leaves the reservation's own directory
    standing under that name, and no count of watched writes can hide that.

    The watched writes are then evidence on top: each landed inside a staging
    sibling while `out_dir` stood empty, and for a run that published those
    staged writes are exactly the files the reader ends up seeing. Timing alone
    would not be enough - a run can leave `out_dir` empty at the one instant it
    writes a decoy file into a sibling - so the destination of each write is
    checked too."""
    _assert_published_in_one_rename(watch, published)
    _assert_writes_landed_in_staging(watch, out_dir, published)


def _assert_published_in_one_rename(watch, published):
    """The directory a reader ends up with is the directory the run staged,
    moved onto the name by one rename - and a failed run moved nothing onto
    the name at all."""
    if published is None:
        assert not watch.publishes, "a run that failed still moved a directory onto the destination"
        return
    assert len(watch.publishes) == 1, (
        f"the destination must appear in one rename, {len(watch.publishes)} landed on it"
    )
    assert _directory_id(published) == watch.publishes[0], (
        "the published directory is not the directory that was renamed onto "
        "the name, so it was filled entry by entry and a reader could see it "
        "half full"
    )


def _assert_writes_landed_in_staging(watch, out_dir, published):
    """Every watched write landed inside a staging sibling while `out_dir` stood
    empty, and a published run's files are exactly those staged writes."""
    views = watch.views
    assert views, (
        "no write was observed: the run must write through Path.write_text, "
        "Path.open, the builtin open, or os.open"
    )
    # Every mid-run view of out_dir is empty: the reservation and nothing more.
    assert [view.out_dir_contents for view in views] == [[] for _ in views]
    # ...and a staging sibling was standing at each of them, so the files were
    # really built elsewhere rather than merely cleaned up afterwards.
    assert all(view.staged for view in views)

    reservation = _resolved(out_dir)
    staged_writes = set()
    write_roots = set()
    for view in views:
        # The publishing rename moves the staging directory onto the
        # reservation: the one write whose target IS the final directory.
        if view.target == reservation:
            continue
        assert reservation not in view.target.parents, (
            f"{view.target.name} was written straight into the final directory"
        )
        root = _staging_root(view.target, reservation)
        assert root is not None, f"{view.target} was written outside the run's staging sibling"
        staged_writes.add(view.target.relative_to(root))
        write_roots.add(view.parent_id)
    if published is None:
        return
    # Every published file is one of those staged writes, so the staging
    # directory held the run's real content rather than a decoy beside it.
    assert staged_writes == {Path(entry.name) for entry in published.iterdir()}
    # ...and the directory those writes landed in is the very directory the
    # reader now has, so the run moved the directory it filled rather than
    # renaming an empty stand-in onto the name and filling it afterwards.
    assert write_roots == {_directory_id(published)}, (
        "the published directory is not the directory the run wrote its files into"
    )


def watch_reservation(monkeypatch, out_dir):
    """Every directory the run creates, paired with whether the reservation on
    `out_dir` was standing at that moment. Proves the reservation was taken
    before staging was attempted, so releasing it later is a real release."""
    attempts = []
    real_mkdir = Path.mkdir

    def watched_mkdir(self, *args, **kwargs):
        attempts.append((Path(self), out_dir.is_dir()))
        return real_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", watched_mkdir)
    return attempts


class _ForcedOs:
    """The real `os` module with `name` forced to another host's value.

    write_proposals reads `os.name` at call time to choose the call it publishes
    with, so forcing that name is the only way to drive the branch this host does
    not take. The override stays inside the binding write_proposals reads:
    assigning to `os.name` on the module itself would be read by pathlib too,
    which picks WindowsPath over PosixPath from that same attribute, and every
    path the test built afterwards would be parsed for the wrong host."""

    def __init__(self, name):
        self.name = name

    def __getattr__(self, attribute):
        # Resolved on every access, so a call another helper patched on the real
        # module - os.replace, os.rename - is the one the run reaches.
        return getattr(os, attribute)


def publish_branch(monkeypatch, os_name):
    """Send write_proposals down `os_name`'s publish branch, or leave it on this
    host's own branch when `os_name` is None."""
    if os_name is not None:
        monkeypatch.setattr(proposal, "os", _ForcedOs(os_name))


def run_competitor_at_the_reservation(monkeypatch, out_dir, competitor):
    """Run `competitor` at the instant the first writer holds the reservation on
    `out_dir` and has staged nothing yet - where a second run stamped the same
    UTC second arrives. Its outcome is recorded rather than raised, so the first
    writer runs on undisturbed, and the reservation is looked at once more right
    afterwards: a loser that takes down the name it failed to claim is the
    defect, and by the end of the run nothing tells that apart from a name it
    never touched."""
    outcome = {}
    real_mkdir = Path.mkdir

    def watched_mkdir(self, *args, **kwargs):
        created = real_mkdir(self, *args, **kwargs)
        if Path(self) == out_dir and not outcome:
            outcome["ran"] = True
            try:
                outcome["published"] = competitor()
            except OSError as error:
                outcome["error"] = error
            outcome["reservation_stood"] = out_dir.is_dir()
        return created

    monkeypatch.setattr(Path, "mkdir", watched_mkdir)
    return outcome


# The file a competing run publishes once it holds the name, and its bytes: a
# loser that removes either has removed somebody else's published proposals.
CLAIMED_FILE = "the-other-runs-proposal.md"
CLAIMED_TEXT = "the run that took the name published this\n"


def claim_the_name_at_publication(monkeypatch, out_dir):
    """Let a competing run take `out_dir` at the instant this run publishes onto
    it, through either call a publish can go through.

    Taking it needs the name to be free, and on the windows branch it is: the
    reservation is released immediately before the rename. `claimed` records
    that it really was free, so a run publishing onto a name it still holds
    fails the test rather than quietly skipping the race it was meant to lose."""
    claim = {}

    def claiming(publish):
        def claim_first(src, dst, *args, **kwargs):
            if not claim and _resolved(dst) == _resolved(out_dir):
                claim["attempted"] = True
                out_dir.mkdir(parents=True)
                (out_dir / CLAIMED_FILE).write_text(CLAIMED_TEXT)
                claim["claimed"] = True
            return publish(src, dst, *args, **kwargs)

        return claim_first

    monkeypatch.setattr(os, "replace", claiming(os.replace))
    monkeypatch.setattr(os, "rename", claiming(os.rename))
    return claim


def take_the_name_the_moment_the_run_looks(monkeypatch, out_dir):
    """Hand `out_dir` to a competing run the first time this run looks at that
    name while it is still free.

    A second run stamped the same UTC second cannot be timed from a test, so the
    look itself is the trigger. A run that decides from what it saw leaves a
    window between the look and the claim, and this drops a competitor squarely
    into it; a run that claims the name in one exclusive step never looks, so it
    never opens a window. Pathlib's two looks are covered, `Path.exists` and
    `Path.is_dir`, which is what an implementation written on `Path` reaches
    for."""
    taken = {}
    real_exists = Path.exists
    real_is_dir = Path.is_dir

    def take_the_name(path):
        if taken or _resolved(path) != _resolved(out_dir) or os.path.lexists(out_dir):
            return
        taken["looked_at"] = str(path)
        out_dir.mkdir(parents=True)
        (out_dir / CLAIMED_FILE).write_text(CLAIMED_TEXT)

    def watched_exists(self, *args, **kwargs):
        answer = real_exists(self, *args, **kwargs)
        take_the_name(self)
        return answer

    def watched_is_dir(self, *args, **kwargs):
        answer = real_is_dir(self, *args, **kwargs)
        take_the_name(self)
        return answer

    monkeypatch.setattr(Path, "exists", watched_exists)
    monkeypatch.setattr(Path, "is_dir", watched_is_dir)
    return taken
