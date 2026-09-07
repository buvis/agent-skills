"""Tests for proposal.write_proposals(): the run directory it reserves, the
files and manifests it publishes, and the rollback it leaves behind when a
write fails."""

import dataclasses
import errno
import json
import os
from pathlib import Path

import proposal
import pytest
from publication_test_helpers import (
    CLAIMED_FILE,
    CLAIMED_TEXT,
    assert_never_built_in_place,
    claim_the_name_at_publication,
    publish_branch,
    run_competitor_at_the_reservation,
    staged_siblings,
    take_the_name_the_moment_the_run_looks,
    watch_publication,
    watch_reservation,
)

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


def _read_json(published, filename):
    return json.loads((published / filename).read_text())


def _by_name(records):
    return {record["name"]: record for record in records}


def test_write_proposals_publishes_a_markdown_file_per_proposal_and_returns_the_directory(
    evidence, monkeypatch, tmp_path
):
    first = _named(evidence, "cache-eviction-rule")
    second = _named(evidence, "Signing Key Rotation")
    out_dir = _run_dir(tmp_path)
    watch = watch_publication(monkeypatch, out_dir)

    published = proposal.write_proposals([first, second], [], out_dir)

    # The directory a reader sees appears in one step, holding everything: it is
    # the staged directory renamed onto the name, no view taken while the run was
    # writing showed a partly filled out_dir, and every file it now holds was
    # written into the staging sibling instead.
    assert_never_built_in_place(watch, out_dir, published)
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
    assert not staged_siblings(out_dir)


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
    # take_the_name_the_moment_the_run_looks instead.
    assert excinfo.value.errno == errno.EEXIST
    assert sorted(path.name for path in out_dir.iterdir()) == before
    assert not staged_siblings(out_dir)


def test_write_proposals_leaves_no_directory_and_no_staged_sibling_when_a_write_fails(
    evidence, monkeypatch, tmp_path
):
    # One proposal writes cleanly and the other cannot: its stem is longer than
    # the filesystem allows, so the run fails with the directory half built.
    # A reader must find no directory at all rather than the surviving half.
    proposals = [_named(evidence, "cache-eviction-rule"), _named(evidence, _UNWRITEABLE_NAME)]
    out_dir = _run_dir(tmp_path)
    watch = watch_publication(monkeypatch, out_dir)

    with pytest.raises(OSError):
        proposal.write_proposals(proposals, [], out_dir)

    # The half that did get written never reached out_dir, so the survivor was
    # never visible to a reader: this is a rollback of a staged run, not a
    # deletion of a directory that was briefly wrong.
    assert_never_built_in_place(watch, out_dir)
    assert not out_dir.exists()
    assert not staged_siblings(out_dir)


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
    attempts = watch_reservation(monkeypatch, out_dir)

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


# Every filename a run publishing one proposal leaves behind.
_ONE_PROPOSAL_FILENAMES = ["cache-eviction-rule.md", "discards.json", "proposals.json"]


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
    publish_branch(monkeypatch, os_name)
    out_dir = _run_dir(tmp_path)
    winner = _named(evidence, "cache-eviction-rule")
    watch = watch_publication(monkeypatch, out_dir)
    outcome = run_competitor_at_the_reservation(
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
    # take_the_name_the_moment_the_run_looks instead.
    assert isinstance(outcome.get("error"), FileExistsError)
    assert outcome["error"].errno == errno.EEXIST
    assert "published" not in outcome
    # ...and it did not take the winner's name down with it on the way out.
    assert outcome["reservation_stood"] is True
    # The one winner published whole, on this branch too.
    assert_never_built_in_place(watch, out_dir, published)
    assert published == out_dir
    assert sorted(path.name for path in published.iterdir()) == _ONE_PROPOSAL_FILENAMES
    assert (published / "cache-eviction-rule.md").read_text() == winner.file_text
    # Nothing of the loser's reached the directory: not its file, not its record.
    assert [record["name"] for record in _read_json(published, "proposals.json")] == [
        "cache-eviction-rule"
    ]
    assert not staged_siblings(out_dir)


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
    publish_branch(monkeypatch, "nt")
    out_dir = _run_dir(tmp_path)
    claim = claim_the_name_at_publication(monkeypatch, out_dir)

    with pytest.raises(OSError):
        proposal.write_proposals([_named(evidence, "cache-eviction-rule")], [], out_dir)

    assert claim.get("claimed"), (
        "the competing run could not take the name: this run published onto a "
        "reservation it was still holding, so the release before the rename is missing"
    )
    assert out_dir.is_dir(), "the rollback removed a directory this run no longer owned"
    assert sorted(path.name for path in out_dir.iterdir()) == [CLAIMED_FILE]
    assert (out_dir / CLAIMED_FILE).read_text() == CLAIMED_TEXT
    # Its own mess stays its own to clear.
    assert not staged_siblings(out_dir)


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
    competitor = take_the_name_the_moment_the_run_looks(monkeypatch, out_dir)

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
    assert not staged_siblings(out_dir)


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
