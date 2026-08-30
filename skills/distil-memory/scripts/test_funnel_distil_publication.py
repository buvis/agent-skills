"""Tests for the order and the failure modes of the distil stage's
publication: the proposals directory lands before the report, both carry one
stamp, the report names the directory the run actually published, and a failed
publication leaves neither behind."""

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import funnel

from funnel_test_helpers import (
    FakeClaudeCli,
    _PROPOSAL_ONE,
    _PROPOSAL_TWO,
    _SLICE_ONE,
    _SLICE_TWO,
    _published,
    make_corpus,
)


def _counting_clock(reads: list[str], instant: datetime):
    """A stand-in for funnel.datetime frozen at `instant`, appending to
    `reads` on every wall-clock read so a second read is visible wherever it
    happens - not only when its value reaches _write_report."""

    class CountingClock(datetime):
        @classmethod
        def now(cls, tz=None):
            reads.append("now")
            return instant if tz is None else instant.astimezone(tz)

        @classmethod
        def utcnow(cls):
            reads.append("utcnow")
            return instant.replace(tzinfo=None)

    return CountingClock


def _how_to_proceed(report: str) -> str:
    """The one "How to proceed:" line of a report, printed or persisted."""
    lines = [line for line in report.splitlines() if line.startswith("How to proceed:")]
    assert len(lines) == 1, f"expected one How to proceed line, found {lines}"
    return lines[0]


def _proposals_paths_named(line: str) -> list[str]:
    """Every path-shaped token in a "How to proceed:" line that claims to be a
    proposals directory."""
    tokens = {token.strip(".,;:()'\"") for token in line.split() if "/" in token}
    return sorted(token for token in tokens if "proposal" in token.lower())


def _named_proposals_directory(line: str) -> Path:
    """The proposals directory a "How to proceed:" line names, as a path.

    Resolved against the cwd, so a relative path and an absolute one both land
    on the directory a reader following the report would open.
    """
    named = _proposals_paths_named(line)
    assert len(named) == 1, f"expected one proposals path in {line!r}, found {named}"
    return (Path.cwd() / named[0]).resolve()


def _everything_the_run_said(captured, audit_dir: Path) -> str:
    """Both streams plus every discard reason the run published.

    A proposal the run could not use may be reported either way - as a discard
    carrying a reason or as a publish failure on stderr - so both are read, and
    silence is what fails.
    """
    spoken = [captured.out, captured.err]
    spoken.extend(
        path.read_text() for path in audit_dir.glob("distil-memory-*-proposals/discards.json")
    )
    return "\n".join(spoken)


# Two instants a run can be frozen at, so two runs of one corpus publish two
# differently named directories. The later instant runs FIRST, so the second
# run's own directory is not the one that sorts last in the audit directory:
# run order and disk order disagree, and a report that reaches for the newest
# name on disk is caught naming the previous run's directory.
_TWO_INSTANTS = (
    datetime(2021, 6, 7, 8, 9, 10, tzinfo=timezone.utc),
    datetime(2020, 1, 2, 3, 4, 5, tzinfo=timezone.utc),
)

# A frontmatter name nothing safe survives: validate accepts it (a non-empty
# string), sanitise_name refuses it, so only the publisher ever finds out.
_UNUSABLE_NAME = "!!! ???"

_PROPOSAL_UNUSABLE_NAME = f"""---
name: "{_UNUSABLE_NAME}"
description: "A distilled memory whose whole name is punctuation"
metadata:
  node_type: memory
  type: project
---

A name made only of punctuation leaves no safe filename stem. See [[cheap-tier-map]].

**Why:** the name is model output, and nothing upstream promises it can be filed.

**How to apply:** read the run's output for what it could not publish.
"""


def test_main_distil_limit_caps_the_survivors_distilled_and_reports_the_remainder_as_skipped(
    make_corpus, monkeypatch, capsys
):
    """--distil-limit 1 over two durable survivors distils the first and states
    the other as skipped. A main() that never reads the flag distils both and
    reports skipped_by_limit: 0."""
    built = make_corpus()
    fake_cli = FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE, _SLICE_TWO: _PROPOSAL_TWO})
    monkeypatch.setattr(funnel.subprocess, "run", fake_cli)

    exit_code = funnel.main(["--distil", "--distil-limit", "1"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "survivors: 2" in out
    assert "proposals: 1" in out
    assert "skipped_by_limit: 1" in out
    assert fake_cli.distilled == [_SLICE_ONE]

    _out_dir, records, _discards = _published(built.audit_dir)
    assert [record["name"] for record in records] == ["cheap-tier-is-haiku"]


def test_main_distil_limit_zero_distils_every_survivor_and_skips_none(make_corpus, monkeypatch, capsys):
    """Zero means no cap, not an empty slice: `survivors[:0]` would distil
    nothing while still reporting skipped_by_limit: 0."""
    built = make_corpus()
    fake_cli = FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE, _SLICE_TWO: _PROPOSAL_TWO})
    monkeypatch.setattr(funnel.subprocess, "run", fake_cli)

    exit_code = funnel.main(["--distil", "--distil-limit", "0"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "proposals: 2" in out
    assert "skipped_by_limit: 0" in out
    assert sorted(fake_cli.distilled) == sorted([_SLICE_ONE, _SLICE_TWO])

    _out_dir, records, _discards = _published(built.audit_dir)
    assert len(records) == 2


def test_main_publishes_the_proposals_before_it_writes_the_report(make_corpus, monkeypatch):
    """The report may only ever name artefacts that are already on disk, so the
    whole publication - both manifests and the memory file - has to exist by the
    time the report is written."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    monkeypatch.setattr(funnel.subprocess, "run", FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE}))
    real_write_report = funnel._write_report
    seen = {}

    def recording_write_report(report, report_dir, timestamp):
        out_dir = report_dir / f"distil-memory-{timestamp}-proposals"
        seen["contents"] = sorted(p.name for p in out_dir.iterdir()) if out_dir.is_dir() else None
        return real_write_report(report, report_dir, timestamp)

    monkeypatch.setattr(funnel, "_write_report", recording_write_report)

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    assert seen["contents"] == ["cheap-tier-is-haiku.md", "discards.json", "proposals.json"]
    assert len(sorted(built.audit_dir.glob("distil-memory-*.md"))) == 1


def test_main_stamps_the_report_file_and_the_proposals_directory_of_one_run_identically(
    make_corpus, monkeypatch
):
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    monkeypatch.setattr(funnel.subprocess, "run", FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE}))

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    report_files = sorted(built.audit_dir.glob("distil-memory-*.md"))
    proposal_dirs = sorted(built.audit_dir.glob("distil-memory-*-proposals"))
    assert len(report_files) == 1
    assert len(proposal_dirs) == 1
    report_stamp = re.fullmatch(r"distil-memory-(\d{8}T\d{6}Z)\.md", report_files[0].name)
    directory_stamp = re.fullmatch(r"distil-memory-(\d{8}T\d{6}Z)-proposals", proposal_dirs[0].name)
    assert report_stamp is not None
    assert directory_stamp is not None
    assert report_stamp.group(1) == directory_stamp.group(1)


def test_main_writes_no_report_file_and_returns_nonzero_when_publishing_the_proposals_fails(
    make_corpus, monkeypatch, capsys
):
    """A persisted report naming a directory that does not exist is worse than
    no report, so a failed publication leaves stdout and stderr talking and the
    disk silent. The clock is frozen so the run lands on a reserved directory
    name, which is exactly how write_proposals refuses to overwrite a run.

    The reserved directory is on disk, put there by this test rather than by the
    run, so a report that guides its reader to it is guiding them to somebody
    else's proposals. stderr may name it freely - that is the diagnostic - but
    the "How to proceed:" line must not, because this run published nothing."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    monkeypatch.setattr(funnel.subprocess, "run", FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE}))
    monkeypatch.setattr(
        funnel, "datetime", _counting_clock([], datetime(2020, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
    )
    (built.audit_dir / "distil-memory-20200102T030405Z-proposals").mkdir(parents=True)

    exit_code = funnel.main(["--distil"])

    assert exit_code != 0
    captured = capsys.readouterr()
    assert "transcripts_read: 1" in captured.out
    assert "How to proceed:" in captured.out
    assert "proposals" in captured.err.lower()
    assert "distil-memory-20200102T030405Z-proposals" not in _how_to_proceed(captured.out)
    assert sorted(built.audit_dir.glob("distil-memory-*.md")) == []


def test_main_leaves_no_proposals_directory_behind_when_publishing_fails_part_way(
    make_corpus, monkeypatch, capsys
):
    """Publication is all or nothing. The first memory file is already written
    when the second write fails here, and a half-filled directory is one a
    reader can see and the next run cannot reserve, so the whole publication
    has to roll back rather than survive in pieces."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    monkeypatch.setattr(funnel.subprocess, "run", FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE}))
    real_write_text = Path.write_text

    def fail_on_the_second_manifest(self, *args, **kwargs):
        if Path(self).name == "discards.json":
            raise OSError("no space left on device")
        return real_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", fail_on_the_second_manifest)

    exit_code = funnel.main(["--distil"])

    assert exit_code != 0
    captured = capsys.readouterr()
    assert "transcripts_read: 1" in captured.out
    assert "How to proceed:" in captured.out
    assert "proposals" in captured.err.lower()
    assert list(built.audit_dir.glob("*proposals*")) == []
    assert sorted(built.audit_dir.glob("distil-memory-*.md")) == []


def test_main_names_the_directory_it_published_in_both_the_printed_and_the_persisted_report(
    make_corpus, monkeypatch, capsys
):
    """A report is only worth reading if the reader can open what it names. The
    run puts its proposals in a stamped directory of its own, so the path the
    printed report gives, the path the report on disk gives, and the directory
    that exists are one and the same. A paragraph naming a fixed
    `dev/local/audit-results/proposals/` sends every reader to a directory no
    run ever creates.

    An audit directory holds every run's proposals, not just this run's, so a
    decoy stamped far in the future sits there before main() starts. With one
    directory on disk any way of finding *a* directory finds *the* directory;
    with the decoy, a report that names the newest stamp on disk names a run
    that never happened."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    monkeypatch.setattr(funnel.subprocess, "run", FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE}))
    decoy = built.audit_dir / "distil-memory-29991231T235959Z-proposals"
    decoy.mkdir(parents=True)

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    printed = capsys.readouterr().out
    published = [
        path for path in built.audit_dir.glob("distil-memory-*-proposals") if path != decoy
    ]
    assert len(published) == 1, f"expected one published directory, found {published}"
    out_dir = published[0]
    report_files = sorted(built.audit_dir.glob("distil-memory-*.md"))
    assert len(report_files) == 1

    persisted = report_files[0].read_text()
    assert _named_proposals_directory(_how_to_proceed(printed)) == out_dir.resolve()
    assert _named_proposals_directory(_how_to_proceed(persisted)) == out_dir.resolve()


def test_main_names_each_runs_own_proposals_directory_rather_than_one_fixed_path(
    make_corpus, monkeypatch, capsys
):
    """Two runs of one corpus publish two directories, because each carries its
    own stamp. A report naming any literal is right about at most one of them
    and lies about the other, so the two reports have to differ exactly where
    the two directories do.

    The runs go in descending stamp order, so the second run's directory sorts
    FIRST of the two on disk. Naming the newest directory in the audit results
    is therefore right once and wrong once: it hands the second run's reader the
    first run's proposals."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    monkeypatch.setattr(funnel.subprocess, "run", FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE}))
    named = []

    for instant in _TWO_INSTANTS:
        monkeypatch.setattr(funnel, "datetime", _counting_clock([], instant))
        assert funnel.main(["--distil"]) == 0
        named.append(_named_proposals_directory(_how_to_proceed(capsys.readouterr().out)))

    published = sorted(path.resolve() for path in built.audit_dir.glob("distil-memory-*-proposals"))
    assert [path.name for path in published] == [
        "distil-memory-20200102T030405Z-proposals",
        "distil-memory-20210607T080910Z-proposals",
    ]
    assert named == [published[1], published[0]]
    assert named[0] != named[1]


def test_render_yield_names_the_published_directory_from_what_main_hands_it(
    make_corpus, monkeypatch, tmp_path, capsys
):
    """One value, not two literals that can drift: the published directory
    reaches the renderer as an argument, so rendering the same call's arguments
    again, on their own, names the same directory.

    Two things have to hold, and the first alone is not enough. The directory
    has to be IN what main() handed over - a renderer told nothing cannot be
    reporting what this run published, whatever it prints. And the re-render has
    to survive the filesystem going away: the published directory is renamed, a
    decoy with a far later stamp takes the audit directory's last sort slot, and
    the cwd moves to an empty tree. A pure formatter is unmoved by all three and
    renders the identical text; a renderer that reads the clock again or hunts
    the disk for the newest directory renders something else."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    monkeypatch.setattr(funnel.subprocess, "run", FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE}))
    real_render_yield = funnel.render_yield
    seen = {}

    def recording_render_yield(*args, **kwargs):
        seen["call"] = ([dict(arg) if isinstance(arg, dict) else arg for arg in args], dict(kwargs))
        seen["rendered"] = real_render_yield(*args, **kwargs)
        return seen["rendered"]

    monkeypatch.setattr(funnel, "render_yield", recording_render_yield)

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    capsys.readouterr()
    out_dir, _records, _discards = _published(built.audit_dir)
    args, kwargs = seen["call"]
    assert _named_proposals_directory(_how_to_proceed(seen["rendered"])) == out_dir.resolve()
    assert out_dir.name in str((args, kwargs)), (
        f"main() handed render_yield {(args, kwargs)!r}, which does not carry {out_dir.name}"
    )

    out_dir.rename(out_dir.parent / "renamed-out-of-the-way")
    (built.audit_dir / "distil-memory-29991231T235959Z-proposals").mkdir()
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)

    rendered = real_render_yield(*args, **kwargs)

    assert rendered == seen["rendered"]


def test_main_reports_and_returns_when_a_proposal_name_leaves_no_safe_filename(
    make_corpus, monkeypatch, capsys
):
    """A frontmatter name is model output and nothing upstream promises it can
    be filed: validate only asks for a non-empty string, and `!!! ???` is one.
    sanitise_name refuses it with a ProposalError, a ValueError and not an
    OSError, so it escapes main() before the report is printed and the run dies
    with a traceback saying nothing about the transcripts it read.

    main() owes its caller a report and an exit code however the publication
    ends, and the unusable proposal has to be named - as a discard reason or a
    publish failure, but never silence. No particular exit code is pinned,
    because both resolutions are open, yet each owes its own evidence or
    "either resolution" reads as "any behaviour at all": a run ending in 0
    claims the healthy one and has to leave the discard that claim rests on, a
    record in discards.json whose reason names the name it could not file, while
    a run that published no directory ends non-zero. Neither may count the name
    as a published proposal, which rules out filing it under a fallback stem and
    calling the run done.

    Counting it anyway looks healthy - exit 0, `proposals: 1`, `discards: 0`, an
    empty published directory - so the count on stdout has to answer for the
    run's own manifest, which the directory's .md files cannot, being zero too."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    monkeypatch.setattr(
        funnel.subprocess, "run", FakeClaudeCli({_SLICE_ONE: _PROPOSAL_UNUSABLE_NAME})
    )

    exit_code = funnel.main(["--distil"])

    assert isinstance(exit_code, int)
    captured = capsys.readouterr()
    assert "transcripts_read: 1" in captured.out
    assert "How to proceed:" in captured.out
    assert _UNUSABLE_NAME in _everything_the_run_said(captured, built.audit_dir)
    manifests = sorted(built.audit_dir.glob("distil-memory-*-proposals/proposals.json"))
    published = "\n".join(path.read_text() for path in manifests)
    assert _UNUSABLE_NAME not in published
    if manifests:
        assert f"proposals: {len(json.loads(manifests[0].read_text()))}" in captured.out
    else:
        assert exit_code != 0
    if exit_code == 0:
        discards = json.loads((manifests[0].parent / "discards.json").read_text())
        reasoned = [record for record in discards if _UNUSABLE_NAME in record["reason"]]
        assert reasoned, (
            f"the run ended 0, so it owes a reasoned discard naming {_UNUSABLE_NAME},"
            f" but discards.json holds {discards}"
        )


def test_main_publishes_and_returns_zero_when_every_proposal_name_sanitises_cleanly(
    make_corpus, monkeypatch, capsys
):
    """The companion to the unusable name: handling one must not become
    refusing every proposal. Two ordinary names still reach disk as two files,
    nothing is discarded, and the run still ends in 0."""
    built = make_corpus()
    monkeypatch.setattr(
        funnel.subprocess,
        "run",
        FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE, _SLICE_TWO: _PROPOSAL_TWO}),
    )

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    assert "proposals: 2" in capsys.readouterr().out
    out_dir, records, discards = _published(built.audit_dir)
    assert discards == []
    assert sorted(record["name"] for record in records) == [
        "cheap-tier-is-haiku",
        "report-under-audit-results",
    ]
    assert sorted(path.name for path in out_dir.glob("*.md")) == [
        "cheap-tier-is-haiku.md",
        "report-under-audit-results.md",
    ]
