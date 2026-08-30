"""Tests that one funnel.main() run reads the wall clock once and resolves
the transcript parser once, so every artefact of that run carries the same
stamp and the same version."""

import json
import re
import subprocess
from datetime import datetime, timedelta, timezone
from types import ModuleType

import corpus
import funnel

from funnel_test_helpers import FakeSessionData, make_transcript_parser_module, write_transcript


def test_write_report_names_the_file_with_the_timestamp_its_caller_supplied(tmp_path):
    report_dir = tmp_path / "audit-results"

    out_path = funnel._write_report("yield report body\n", report_dir, "20200102T030405Z")

    assert out_path == report_dir / "distil-memory-20200102T030405Z.md"
    assert out_path.read_text() == "yield report body\n"


def test_main_computes_one_utc_timestamp_for_the_run_and_hands_it_to_write_report(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(corpus, "select_transcripts", lambda **kwargs: [])
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (ModuleType("stub"), "0.2.2"))
    stamps = []

    def recording_write_report(report, report_dir, timestamp):
        stamps.append(timestamp)
        report_dir.mkdir(parents=True, exist_ok=True)
        out_path = report_dir / f"distil-memory-{timestamp}.md"
        out_path.write_text(report)
        return out_path

    monkeypatch.setattr(funnel, "_write_report", recording_write_report)

    exit_code = funnel.main([])

    assert exit_code == 0
    assert len(stamps) == 1
    assert re.fullmatch(r"\d{8}T\d{6}Z", stamps[0])
    stamped_at = datetime.strptime(stamps[0], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
    assert abs((datetime.now(timezone.utc) - stamped_at).total_seconds()) < 300


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


def test_main_reads_the_wall_clock_once_so_every_artefact_of_one_run_shares_a_stamp(tmp_path, monkeypatch):
    """One run, one instant. A second `now()` anywhere in main() lets a run
    that crosses a second boundary stamp its report and its proposals
    directory differently, which destroys the correlation the stamp exists
    to establish."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(corpus, "select_transcripts", lambda **kwargs: [])
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (ModuleType("stub"), "0.2.2"))
    reads: list[str] = []
    monkeypatch.setattr(
        funnel, "datetime", _counting_clock(reads, datetime(2020, 1, 2, 3, 4, 5, tzinfo=timezone.utc))
    )
    stamps = []

    def recording_write_report(report, report_dir, timestamp):
        stamps.append(timestamp)
        report_dir.mkdir(parents=True, exist_ok=True)
        out_path = report_dir / f"distil-memory-{timestamp}.md"
        out_path.write_text(report)
        return out_path

    monkeypatch.setattr(funnel, "_write_report", recording_write_report)

    exit_code = funnel.main([])

    assert exit_code == 0
    assert stamps == ["20200102T030405Z"]
    assert len(reads) == 1


def test_main_calls_resolve_parser_exactly_once(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    projects_root = tmp_path / "claude_projects"
    projects_root.mkdir()
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", projects_root)
    module, version = make_transcript_parser_module({})
    calls = []

    def counting_resolve(*args, **kwargs):
        calls.append((args, kwargs))
        return module, version

    monkeypatch.setattr(corpus, "resolve_parser", counting_resolve)

    exit_code = funnel.main([])

    assert exit_code == 0
    assert len(calls) == 1


def test_main_returns_zero_when_resolve_parser_succeeds_on_first_call_and_would_raise_on_a_second(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    projects_root = tmp_path / "claude_projects"
    projects_root.mkdir()
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", projects_root)
    module, version = make_transcript_parser_module({})
    calls = []

    def succeed_once_then_raise(*args, **kwargs):
        calls.append((args, kwargs))
        if len(calls) == 1:
            return module, version
        raise corpus.StaleParserError("a second resolve must never happen")

    monkeypatch.setattr(corpus, "resolve_parser", succeed_once_then_raise)

    exit_code = funnel.main([])

    assert exit_code == 0


def test_main_returns_one_and_prints_message_to_stderr_when_resolve_parser_raises_on_the_first_call(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", tmp_path / "claude_projects")

    def raise_immediately(*args, **kwargs):
        raise corpus.StaleParserError("claude-checkup cache is empty")

    monkeypatch.setattr(corpus, "resolve_parser", raise_immediately)

    exit_code = funnel.main([])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "claude-checkup cache is empty" in captured.err


def test_main_yield_report_states_the_version_from_the_single_resolution_that_selected_transcripts(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    projects_root = tmp_path / "claude_projects"
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", projects_root)
    project_dir = projects_root / "aaaa-myproj"
    now = datetime.now(timezone.utc)
    write_transcript(
        project_dir,
        "t1.jsonl",
        json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": "we measured this"}]}})
        + "\n",
    )
    versions = iter(["0.9.9", "0.0.1"])

    def resolve_with_a_distinct_version_per_call(*args, **kwargs):
        version = next(versions)
        module, _ = make_transcript_parser_module(
            {"t1.jsonl": FakeSessionData(latest=now - timedelta(days=1))}, version=version
        )
        return module, version

    monkeypatch.setattr(corpus, "resolve_parser", resolve_with_a_distinct_version_per_call)

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="durable", stderr="")

    monkeypatch.setattr(funnel.subprocess, "run", fake_run)

    exit_code = funnel.main([])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "claude_checkup_version: 0.9.9" in captured.out
    assert "claude_checkup_version: 0.0.1" not in captured.out


def test_main_reports_a_real_version_even_when_select_transcripts_is_stubbed_out_entirely(
    tmp_path, monkeypatch, capsys
):
    """Regression test: main() must not depend on select_transcripts() to
    have set any side-channel version state as a side effect. With
    select_transcripts replaced entirely, main() must still report the
    version it resolved itself - never None, and never a value left behind
    by another test."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(corpus, "select_transcripts", lambda **kwargs: [])
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (ModuleType("stub"), "1.2.3"))

    exit_code = funnel.main([])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "claude_checkup_version: 1.2.3" in captured.out
    assert "claude_checkup_version: None" not in captured.out
