"""Tests for proposal.write_proposals(): the run directory it reserves, the
files and manifests it publishes, and the rollback it leaves behind when a
write fails."""

import builtins
import dataclasses
import errno
import json
import os
from pathlib import Path

import proposal
import pytest

_VALID_NAME = "cache-eviction-rule"
_VALID_DESCRIPTION = "Redis evicts idle sessions after ten minutes"
_VALID_APPLY = "Set the session TTL above ten minutes for long imports."


def _body(apply_line=_VALID_APPLY):
    text = "Redis drops idle sessions once they pass the TTL.\n\n**Why:** long imports die halfway.\n"
    if apply_line is not None:
        text += f"\n**How to apply:** {apply_line}\n"
    return text


def _memory_file(
    *,
    name=_VALID_NAME,
    description=_VALID_DESCRIPTION,
    memory_type="project",
    include_metadata=True,
    apply_line=_VALID_APPLY,
):
    lines = ["---"]
    if name is not None:
        lines.append(f'name: "{name}"')
    if description is not None:
        lines.append(f'description: "{description}"')
    if include_metadata:
        lines.append("metadata:")
        lines.append("  node_type: memory")
        if memory_type is not None:
            lines.append(f"  type: {memory_type}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + _body(apply_line)


@pytest.fixture
def evidence(tmp_path):
    transcript = tmp_path / "session.jsonl"
    transcript.write_text('{"type": "assistant"}\n')
    return proposal.Evidence(
        transcript=transcript,
        line_no=7,
        text="we measured the cache hit rate at 91 percent",
    )


_MARKER = "measured"


def _filler(total):
    """`total` characters of prose with no repeating substring, so "this window
    reached offset N" is a real assertion rather than a filler coincidence."""
    return " ".join(f"w{index:04d}" for index in range(total // 6 + 2))[:total]


def _text_with_marker_at(offset, total, marker=_MARKER):
    base = _filler(total)
    return base[:offset] + marker + base[offset + len(marker) :]


# A run directory name in the shape the run stamps: UTC, second resolution. The
# parent is deliberately absent so the reservation has to create it.
_RUN_DIR_NAME = "proposals-20260830T120000Z"

# Longer than NAME_MAX (255) on every filesystem this runs on, and made only of
# characters sanitise_name keeps, so the stem survives whole and the failure
# lands where the file is written rather than earlier.
_UNWRITEABLE_NAME = "n" * 300

_PROPOSAL_RECORD_FIELDS = {
    "name",
    "kind",
    "transcript",
    "line_no",
    "evidence_text",
    "existing_text",
    "dedup_error",
    "file",
}


@dataclasses.dataclass(frozen=True)
class _Discard:
    """The smallest stand-in for the Discard record: the three fields
    discards.json is specified to carry. Discard's own module does not exist
    yet, and write_proposals only ever reads these three."""

    transcript: Path
    line_no: int
    reason: str


def _run_dir(tmp_path):
    return tmp_path / "runs" / _RUN_DIR_NAME


def _named(evidence, name, description=_VALID_DESCRIPTION, **kwargs):
    """A proposal whose frontmatter `name` is `name` - the value that becomes
    both the filename stem and the `name` field in proposals.json."""
    return proposal.Proposal(
        file_text=_memory_file(name=name, description=description), evidence=evidence, **kwargs
    )


def _staged_siblings(out_dir):
    """Every `<out_dir>.partial-*` directory the contract stages into. A
    published run leaves none behind, and a failed one leaves none either."""
    if not out_dir.parent.is_dir():
        return []
    return sorted(out_dir.parent.glob(f"{out_dir.name}.partial-*"))


def _read_json(published, filename):
    return json.loads((published / filename).read_text())


def _by_name(records):
    return {record["name"]: record for record in records}


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


def _watch_publication(monkeypatch, out_dir):
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
                staged=[path.name for path in _staged_siblings(out_dir)],
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
    real_write_text = Path.write_text
    real_path_open = Path.open
    real_builtin_open = builtins.open
    real_os_open = os.open
    real_replace = os.replace
    real_rename = os.rename

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

    def watched_replace(src, dst, *args, **kwargs):
        record(dst)
        record_publish(src, dst)
        return real_replace(src, dst, *args, **kwargs)

    def watched_rename(src, dst, *args, **kwargs):
        record(dst)
        record_publish(src, dst)
        return real_rename(src, dst, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", watched_write_text)
    monkeypatch.setattr(Path, "open", watched_path_open)
    monkeypatch.setattr(builtins, "open", watched_builtin_open)
    monkeypatch.setattr(os, "open", watched_os_open)
    monkeypatch.setattr(os, "replace", watched_replace)
    monkeypatch.setattr(os, "rename", watched_rename)


def _assert_never_built_in_place(watch, out_dir, published=None):
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
    if published is None:
        assert not watch.publishes, "a run that failed still moved a directory onto the destination"
    else:
        assert len(watch.publishes) == 1, (
            f"the destination must appear in one rename, {len(watch.publishes)} landed on it"
        )
        assert _directory_id(published) == watch.publishes[0], (
            "the published directory is not the directory that was renamed onto "
            "the name, so it was filled entry by entry and a reader could see it "
            "half full"
        )

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
    if published is not None:
        # Every published file is one of those staged writes, so the staging
        # directory held the run's real content rather than a decoy beside it.
        assert staged_writes == {Path(entry.name) for entry in published.iterdir()}
        # ...and the directory those writes landed in is the very directory the
        # reader now has, so the run moved the directory it filled rather than
        # renaming an empty stand-in onto the name and filling it afterwards.
        assert write_roots == {_directory_id(published)}, (
            "the published directory is not the directory the run wrote its files into"
        )


def _watch_reservation(monkeypatch, out_dir):
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


def test_write_proposals_publishes_a_markdown_file_per_proposal_and_returns_the_directory(
    evidence, monkeypatch, tmp_path
):
    first = _named(evidence, "cache-eviction-rule")
    second = _named(evidence, "Signing Key Rotation")
    out_dir = _run_dir(tmp_path)
    watch = _watch_publication(monkeypatch, out_dir)

    published = proposal.write_proposals([first, second], [], out_dir)

    # The directory a reader sees appears in one step, holding everything: it is
    # the staged directory renamed onto the name, no view taken while the run was
    # writing showed a partly filled out_dir, and every file it now holds was
    # written into the staging sibling instead.
    _assert_never_built_in_place(watch, out_dir, published)
    assert published == out_dir
    # The whole published surface, so a leftover staging file inside it fails here.
    assert sorted(path.name for path in published.iterdir()) == [
        "cache-eviction-rule.md",
        "discards.json",
        "proposals.json",
        "signing-key-rotation.md",
    ]
    assert (published / "cache-eviction-rule.md").read_text() == first.file_text
    assert (published / "signing-key-rotation.md").read_text() == second.file_text
    assert not _staged_siblings(out_dir)


def test_proposals_json_records_each_proposal_with_its_evidence_and_published_file(
    evidence, tmp_path
):
    candidate = _named(evidence, "cache-eviction-rule", dedup_error="the index would not parse")
    out_dir = _run_dir(tmp_path)

    published = proposal.write_proposals([candidate], [], out_dir)

    records = _read_json(published, "proposals.json")
    assert len(records) == 1
    record = records[0]
    assert set(record) == _PROPOSAL_RECORD_FIELDS
    assert record["name"] == "cache-eviction-rule"
    assert record["kind"] == proposal.NEW
    assert record["transcript"] == str(evidence.transcript)
    assert record["line_no"] == evidence.line_no
    assert record["evidence_text"] == evidence.text
    assert record["existing_text"] is None
    assert record["dedup_error"] == "the index would not parse"
    # `file` names the proposal's file inside the published directory; joining
    # tolerates either a bare filename or an absolute path.
    assert (published / record["file"]).read_text() == candidate.file_text


def test_proposals_json_carries_existing_text_for_an_update_and_null_for_a_new_proposal(
    evidence, tmp_path
):
    # Slice 3 shows both texts side by side, so the current file's text has to
    # survive the round trip; a new proposal has no current text to show.
    existing = _memory_file(
        name="cache-eviction-rule", description="The cue already sitting on disk"
    )
    updated = proposal.Proposal(
        file_text=_memory_file(name="cache-eviction-rule"),
        evidence=evidence,
        kind=proposal.update_kind("cache-eviction-rule"),
        existing_text=existing,
    )
    fresh = _named(evidence, "queue-backlog-rule")
    out_dir = _run_dir(tmp_path)

    published = proposal.write_proposals([updated, fresh], [], out_dir)

    records = _read_json(published, "proposals.json")
    # Records keep the order the proposals came in, so slice 3 can walk them
    # beside the run's own list without re-sorting.
    assert [record["name"] for record in records] == ["cache-eviction-rule", "queue-backlog-rule"]
    for record in records:
        assert set(record) == _PROPOSAL_RECORD_FIELDS
    by_name = _by_name(records)
    assert by_name["cache-eviction-rule"]["kind"] == "update cache-eviction-rule"
    assert by_name["cache-eviction-rule"]["existing_text"] == existing
    assert by_name["queue-backlog-rule"]["kind"] == "new"
    assert by_name["queue-backlog-rule"]["existing_text"] is None


def test_proposals_json_carries_the_full_slice_text_not_the_display_excerpt(evidence, tmp_path):
    # The marker sits past the leading window, so excerpt() returns a cut,
    # ellipsis-marked window. The machine surface must carry neither cut.
    long_text = _text_with_marker_at(
        proposal.EVIDENCE_EXCERPT_CHARS * 2, proposal.EVIDENCE_EXCERPT_CHARS * 5
    )
    candidate = proposal.Proposal(
        file_text=_memory_file(),
        evidence=proposal.Evidence(transcript=evidence.transcript, line_no=3, text=long_text),
    )
    out_dir = _run_dir(tmp_path)

    published = proposal.write_proposals([candidate], [], out_dir)

    record = _read_json(published, "proposals.json")[0]
    assert record["evidence_text"] == long_text
    assert record["evidence_text"] != proposal.excerpt(long_text, _MARKER)
    assert len(record["evidence_text"]) > proposal.EVIDENCE_EXCERPT_CHARS


def test_write_proposals_records_every_discard_with_its_location_and_reason(evidence, tmp_path):
    discards = [
        _Discard(transcript=evidence.transcript, line_no=12, reason="no measured claim"),
        _Discard(transcript=evidence.transcript, line_no=41, reason="already in memory"),
    ]
    out_dir = _run_dir(tmp_path)

    published = proposal.write_proposals(
        [_named(evidence, "cache-eviction-rule")], discards, out_dir
    )

    assert _read_json(published, "discards.json") == [
        {"transcript": str(evidence.transcript), "line_no": 12, "reason": "no measured claim"},
        {"transcript": str(evidence.transcript), "line_no": 41, "reason": "already in memory"},
    ]


@pytest.mark.parametrize(
    ("label", "leftover"),
    [("empty", None), ("holding an earlier run's file", "cache-eviction-rule.md")],
)
def test_write_proposals_refuses_to_publish_over_a_directory_that_already_exists(
    evidence, tmp_path, label, leftover
):
    # The empty case is the one a same-second second run produces, and the one a
    # plain os.replace onto the name would swallow without a word.
    out_dir = _run_dir(tmp_path)
    out_dir.mkdir(parents=True)
    if leftover is not None:
        (out_dir / leftover).write_text("an earlier run wrote this\n")
    before = sorted(path.name for path in out_dir.iterdir())

    with pytest.raises(FileExistsError) as excinfo:
        proposal.write_proposals([_named(evidence, "cache-eviction-rule")], [], out_dir)

    # The error surface the contract promises the caller: FileExistsError
    # carrying EEXIST. This says nothing about where the refusal was decided -
    # any code can raise FileExistsError(errno.EEXIST, ...) after a look - so
    # that the name is claimed rather than probed is pinned by the test built on
    # _take_the_name_the_moment_the_run_looks instead.
    assert excinfo.value.errno == errno.EEXIST
    assert sorted(path.name for path in out_dir.iterdir()) == before
    assert not _staged_siblings(out_dir)


def test_write_proposals_leaves_no_directory_and_no_staged_sibling_when_a_write_fails(
    evidence, monkeypatch, tmp_path
):
    # One proposal writes cleanly and the other cannot: its stem is longer than
    # the filesystem allows, so the run fails with the directory half built.
    # A reader must find no directory at all rather than the surviving half.
    proposals = [_named(evidence, "cache-eviction-rule"), _named(evidence, _UNWRITEABLE_NAME)]
    out_dir = _run_dir(tmp_path)
    watch = _watch_publication(monkeypatch, out_dir)

    with pytest.raises(OSError):
        proposal.write_proposals(proposals, [], out_dir)

    # The half that did get written never reached out_dir, so the survivor was
    # never visible to a reader: this is a rollback of a staged run, not a
    # deletion of a directory that was briefly wrong.
    _assert_never_built_in_place(watch, out_dir)
    assert not out_dir.exists()
    assert not _staged_siblings(out_dir)


def test_write_proposals_removes_its_reservation_when_the_staging_directory_cannot_be_built(
    evidence, monkeypatch, tmp_path
):
    # A regular file already occupying the staged sibling's exact path makes the
    # staging mkdir fail AFTER the reservation is taken, which is the only way to
    # reach the rmdir of the reservation from outside the module.
    out_dir = _run_dir(tmp_path)
    out_dir.parent.mkdir(parents=True)
    blocker = out_dir.parent / f"{out_dir.name}.partial-{os.getpid()}"
    blocker.write_text("a file, not a staging directory\n")
    attempts = _watch_reservation(monkeypatch, out_dir)

    with pytest.raises(OSError) as excinfo:
        proposal.write_proposals([_named(evidence, "cache-eviction-rule")], [], out_dir)

    # EEXIST: the staging mkdir ran and hit the blocker, rather than a probe
    # deciding to raise on its own.
    assert excinfo.value.errno == errno.EEXIST
    assert [path for path, _held in attempts if path == out_dir], "the run took no reservation"
    staging = [
        (path, held) for path, held in attempts if path.name.startswith(f"{out_dir.name}.partial-")
    ]
    assert staging, "the run never tried to stage"
    # The reservation was standing when staging was attempted, so there really
    # was one to release - and it is gone now.
    assert staging[0][1] is True
    assert not out_dir.exists()


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


def _publish_branch(monkeypatch, os_name):
    """Send write_proposals down `os_name`'s publish branch, or leave it on this
    host's own branch when `os_name` is None."""
    if os_name is not None:
        monkeypatch.setattr(proposal, "os", _ForcedOs(os_name))


def _run_competitor_at_the_reservation(monkeypatch, out_dir, competitor):
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
_CLAIMED_FILE = "the-other-runs-proposal.md"
_CLAIMED_TEXT = "the run that took the name published this\n"


def _claim_the_name_at_publication(monkeypatch, out_dir):
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
                (out_dir / _CLAIMED_FILE).write_text(_CLAIMED_TEXT)
                claim["claimed"] = True
            return publish(src, dst, *args, **kwargs)

        return claim_first

    monkeypatch.setattr(os, "replace", claiming(os.replace))
    monkeypatch.setattr(os, "rename", claiming(os.rename))
    return claim


@pytest.mark.parametrize(("branch", "os_name"), [("this host's own", None), ("windows", "nt")])
def test_write_proposals_leaves_exactly_one_winner_when_two_writers_race_for_one_directory(
    evidence, monkeypatch, tmp_path, branch, os_name
):
    """Two runs stamped the same UTC second aim at one directory. The name is
    claimed in one atomic step, so the second writer meets it standing: it
    fails, it publishes nothing, and - the part no after-the-fact look can tell
    apart from a lucky ordering - it leaves the reservation it could not take
    exactly where it found it, so the first writer still publishes.

    Both publish branches are driven, because a run that wins the name on one
    host and loses it on the other is the defect here. The windows branch is
    forced on every host; the posix branch is this host's own wherever the host
    is posix, and is not forced onto windows, where a single os.replace onto a
    directory cannot succeed at all."""
    _publish_branch(monkeypatch, os_name)
    out_dir = _run_dir(tmp_path)
    winner = _named(evidence, "cache-eviction-rule")
    watch = _watch_publication(monkeypatch, out_dir)
    outcome = _run_competitor_at_the_reservation(
        monkeypatch,
        out_dir,
        lambda: proposal.write_proposals([_named(evidence, "queue-backlog-rule")], [], out_dir),
    )

    published = proposal.write_proposals([winner], [], out_dir)

    assert outcome.get("ran"), "the second writer never reached the reserved name"
    # The loser met the standing name and failed on it, with the errno the
    # contract promises its caller. What the errno does NOT say is where the
    # refusal came from - any code can raise FileExistsError(errno.EEXIST, ...) -
    # so the reservation's atomicity is pinned by the test built on
    # _take_the_name_the_moment_the_run_looks instead.
    assert isinstance(outcome.get("error"), FileExistsError)
    assert outcome["error"].errno == errno.EEXIST
    assert "published" not in outcome
    # ...and it did not take the winner's name down with it on the way out.
    assert outcome["reservation_stood"] is True
    # The one winner published whole, on this branch too.
    _assert_never_built_in_place(watch, out_dir, published)
    assert published == out_dir
    assert sorted(path.name for path in published.iterdir()) == [
        "cache-eviction-rule.md",
        "discards.json",
        "proposals.json",
    ]
    assert (published / "cache-eviction-rule.md").read_text() == winner.file_text
    # Nothing of the loser's reached the directory: not its file, not its record.
    assert [record["name"] for record in _read_json(published, "proposals.json")] == [
        "cache-eviction-rule"
    ]
    assert not _staged_siblings(out_dir)


def test_write_proposals_leaves_the_directory_a_competitor_took_when_it_loses_the_publish_race(
    evidence, monkeypatch, tmp_path
):
    """The windows branch releases its reservation immediately before renaming
    the staging directory onto it, so for that instant the name is anybody's. A
    competing run takes it here; this run's rename then fails against the
    directory now standing there, and its rollback owns nothing of that name: it
    clears its own staging sibling and leaves a directory and a file it never
    created alone. Rolling back a name it no longer holds would delete the other
    run's published proposals, which is why the run tracks what it still owns.

    Only this branch has the window - the posix branch holds the reservation
    right through the replace - so it is forced on every host rather than waited
    for on one."""
    _publish_branch(monkeypatch, "nt")
    out_dir = _run_dir(tmp_path)
    claim = _claim_the_name_at_publication(monkeypatch, out_dir)

    with pytest.raises(OSError):
        proposal.write_proposals([_named(evidence, "cache-eviction-rule")], [], out_dir)

    assert claim.get("claimed"), (
        "the competing run could not take the name: this run published onto a "
        "reservation it was still holding, so the release before the rename is missing"
    )
    assert out_dir.is_dir(), "the rollback removed a directory this run no longer owned"
    assert sorted(path.name for path in out_dir.iterdir()) == [_CLAIMED_FILE]
    assert (out_dir / _CLAIMED_FILE).read_text() == _CLAIMED_TEXT
    # Its own mess stays its own to clear.
    assert not _staged_siblings(out_dir)


def _take_the_name_the_moment_the_run_looks(monkeypatch, out_dir):
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
        (out_dir / _CLAIMED_FILE).write_text(_CLAIMED_TEXT)

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


def test_write_proposals_does_not_hand_a_free_destination_to_a_competitor_before_claiming_it(
    evidence, monkeypatch, tmp_path
):
    """The destination is free when the run starts, and a run stamped the same
    UTC second is standing by for it. That second run gets its chance the moment
    this one looks at the name: a run that looks before it claims hands the name
    away inside its own window and publishes nothing, while a run that claims the
    name in one exclusive step never opens the window and publishes.

    This is the part the EEXIST the refusal test reads cannot show on its own. An
    implementation that probes and then raises by hand answers with that same
    errno while leaving this window open, and a probe that then creates the
    directory anyway publishes over whoever took it."""
    out_dir = _run_dir(tmp_path)
    winner = _named(evidence, "cache-eviction-rule")
    competitor = _take_the_name_the_moment_the_run_looks(monkeypatch, out_dir)

    published = proposal.write_proposals([winner], [], out_dir)

    assert not competitor, (
        f"the destination was handed away at a look ({competitor}) taken before it was claimed"
    )
    assert published == out_dir
    # Nothing of the competitor's is here, and nothing of this run's is missing.
    assert sorted(path.name for path in published.iterdir()) == [
        "cache-eviction-rule.md",
        "discards.json",
        "proposals.json",
    ]
    assert (published / "cache-eviction-rule.md").read_text() == winner.file_text
    assert not _staged_siblings(out_dir)


# Five distinct names sanitise_name maps onto the one stem "cache-eviction",
# written in the order the run receives them.
_COLLIDING_NAMES = [
    "Cache Eviction",
    "cache/eviction",
    "cache!!eviction",
    "CACHE.EVICTION",
    "cache+eviction",
]

# The file each of those five proposals is published as, in that same input
# order, and every filename the run leaves behind.
_COLLIDING_FILES = [
    "cache-eviction.md",
    "cache-eviction-2.md",
    "cache-eviction-3.md",
    "cache-eviction-4.md",
    "cache-eviction-5.md",
]
_PUBLISHED_FILENAMES = [
    "cache-eviction-2.md",
    "cache-eviction-3.md",
    "cache-eviction-4.md",
    "cache-eviction-5.md",
    "cache-eviction.md",
    "queue-backlog-rule.md",
]
_RENAMED_FILENAMES = [
    "cache-eviction-2.md",
    "cache-eviction-3.md",
    "cache-eviction-4.md",
    "cache-eviction-5.md",
]


def test_write_proposals_renames_a_stem_an_earlier_proposal_in_the_run_already_took(
    evidence, tmp_path
):
    # Five distinct names, one shared stem: sanitise_name maps all five onto
    # "cache-eviction", so the suffixes have to be generated from the number of
    # collisions seen rather than drawn from a fixed table. ASSUMED SHAPE for
    # "the collision is counted": the contract returns only the published Path,
    # so the count the report states is derived from proposals.json - a record
    # whose file stem is not sanitise_name(name) is one counted collision. Here
    # that count is four, and the last proposal proves a non-colliding stem is
    # not counted.
    assert {proposal.sanitise_name(name) for name in _COLLIDING_NAMES} == {"cache-eviction"}
    colliding = [
        _named(evidence, name, description=f"Cue number {position} on the shared stem")
        for position, name in enumerate(_COLLIDING_NAMES, start=1)
    ]
    separate = _named(evidence, "queue-backlog-rule")
    out_dir = _run_dir(tmp_path)

    published = proposal.write_proposals([*colliding, separate], [], out_dir)

    assert sorted(path.name for path in published.glob("*.md")) == _PUBLISHED_FILENAMES
    # Each file holds its own proposal's text, so the suffixes are not merely
    # present but handed out in INPUT order: the descriptions differ, so a run
    # that ordered the collisions any other way lands the wrong text here.
    for candidate, filename in zip(colliding, _COLLIDING_FILES, strict=True):
        assert (published / filename).read_text() == candidate.file_text
    records = _read_json(published, "proposals.json")
    assert [record["name"] for record in records] == [*_COLLIDING_NAMES, "queue-backlog-rule"]
    for record in records:
        assert set(record) == _PROPOSAL_RECORD_FIELDS
    by_name = _by_name(records)
    # Every record points at the file holding its OWN text, not a sibling's:
    # inside a collision group the filenames are interchangeable, the texts are not.
    for candidate, name in zip(colliding, _COLLIDING_NAMES, strict=True):
        assert (published / by_name[name]["file"]).read_text() == candidate.file_text
    renamed = [
        record
        for record in records
        if Path(record["file"]).stem != proposal.sanitise_name(record["name"])
    ]
    assert len(renamed) == 4
    assert sorted(Path(record["file"]).name for record in renamed) == _RENAMED_FILENAMES
    assert Path(by_name["queue-backlog-rule"]["file"]).name == "queue-backlog-rule.md"
