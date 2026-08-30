"""Tests for the order and the failure modes of the distil stage's
publication: the proposals directory lands before the report, both carry one
stamp, and a failed publication leaves neither behind."""

import re
from datetime import datetime, timezone
from pathlib import Path

import funnel

from test_funnel_distil import (
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
    name, which is exactly how write_proposals refuses to overwrite a run."""
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
