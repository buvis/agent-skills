"""Tests for funnel.py's reporting path: render_yield's pure formatting and
main()'s end-to-end CLI wiring (transcript selection, triage, and the
yield report printed and written to disk)."""

import json
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType

import corpus
import funnel
import pytest


class FakeSessionData:
    """Stand-in for the real claude-checkup parser's SessionData: an object
    with `.earliest`/`.latest` datetime-or-None attributes."""

    def __init__(self, latest=None, earliest=None):
        self.latest = latest
        self.earliest = earliest


def make_transcript_parser_module(results_by_filename, *, version="0.3.0"):
    """A parser module stub whose parse_session(path) looks up its result by
    the transcript's filename, and which satisfies assert_contract()."""
    module = ModuleType("stub_transcript_parser")
    module.parse_session = lambda path: results_by_filename[Path(path).name]
    module.SessionData = FakeSessionData
    return module, version


def write_transcript(project_dir: Path, filename: str, content: str = "") -> Path:
    project_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = project_dir / filename
    transcript_path.write_text(content)
    return transcript_path


def test_render_yield_performs_no_subprocess_calls_or_file_io(monkeypatch):
    def fail_subprocess(*args, **kwargs):
        raise AssertionError("render_yield must not invoke subprocess")

    def fail_open(*args, **kwargs):
        raise AssertionError("render_yield must not perform file I/O")

    monkeypatch.setattr(funnel.subprocess, "run", fail_subprocess)
    monkeypatch.setattr("builtins.open", fail_open)
    counts = {
        "transcripts_read": 3,
        "slices_matched": 2,
        "slices_kept": 1,
        "survivors": 1,
        "claude_checkup_version": "0.2.2",
    }

    result = funnel.render_yield(counts)

    assert isinstance(result, str)


def test_render_yield_prints_every_stage_ending_in_zero_when_a_run_finds_nothing():
    counts = {
        "transcripts_read": 0,
        "slices_matched": 0,
        "slices_kept": 0,
        "survivors": 0,
        "claude_checkup_version": "0.2.2",
    }

    result = funnel.render_yield(counts)

    lines = [line for line in result.splitlines() if line.strip()]
    count_lines = lines[:4]
    assert len(count_lines) == 4
    for line in count_lines:
        assert line.rstrip().endswith("0")


def test_render_yield_prints_key_value_line_for_each_count_when_values_are_nonzero():
    counts = {
        "transcripts_read": 12,
        "slices_matched": 8,
        "slices_kept": 5,
        "survivors": 3,
        "claude_checkup_version": "0.2.2",
    }

    result = funnel.render_yield(counts)

    assert "transcripts_read: 12" in result
    assert "slices_matched: 8" in result
    assert "slices_kept: 5" in result
    assert "survivors: 3" in result


def test_render_yield_states_the_resolved_claude_checkup_version():
    counts = {
        "transcripts_read": 12,
        "slices_matched": 8,
        "slices_kept": 5,
        "survivors": 3,
        "claude_checkup_version": "0.2.2",
    }

    result = funnel.render_yield(counts)

    assert "claude_checkup_version: 0.2.2" in result


def test_render_yield_renders_none_survivors_as_n_a_for_a_dry_run():
    counts = {
        "transcripts_read": 5,
        "slices_matched": 3,
        "slices_kept": 2,
        "survivors": None,
        "claude_checkup_version": "0.2.2",
    }

    result = funnel.render_yield(counts)

    assert "survivors: n/a" in result


def test_render_yield_ends_with_how_to_proceed_line_naming_the_audit_results_directory():
    counts = {
        "transcripts_read": 5,
        "slices_matched": 3,
        "slices_kept": 2,
        "survivors": 1,
        "claude_checkup_version": "0.2.2",
    }

    result = funnel.render_yield(counts)

    last_line = result.rstrip("\n").splitlines()[-1]
    assert last_line.startswith("How to proceed:")
    assert "dev/local/audit-results/" in last_line


def test_main_passes_days_all_project_flags_through_to_select_transcripts(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    calls = []

    def fake_select_transcripts(**kwargs):
        calls.append(kwargs)
        return []

    monkeypatch.setattr(corpus, "select_transcripts", fake_select_transcripts)
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (ModuleType("stub"), "0.2.2"))

    exit_code = funnel.main(["--days", "7", "--all", "--project", "myproj"])

    assert exit_code == 0
    assert len(calls) == 1
    assert calls[0]["days"] == 7
    assert calls[0]["all"] is True
    assert calls[0]["project"] == "myproj"


def test_main_with_argv_none_falls_back_to_sys_argv_and_default_flags(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["funnel.py", "--dry-run"])
    calls = []

    def fake_select_transcripts(**kwargs):
        calls.append(kwargs)
        return []

    monkeypatch.setattr(corpus, "select_transcripts", fake_select_transcripts)
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (ModuleType("stub"), "0.2.2"))

    exit_code = funnel.main()

    assert exit_code == 0
    assert len(calls) == 1
    assert calls[0]["days"] == 30
    assert calls[0]["all"] is False
    assert calls[0]["project"] is None


def test_main_returns_nonzero_and_prints_message_when_select_transcripts_raises_stale_parser_error(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", tmp_path / "projects")

    def raise_stale(*args, **kwargs):
        raise corpus.StaleParserError("no claude-checkup versions found")

    monkeypatch.setattr(corpus, "resolve_parser", raise_stale)

    exit_code = funnel.main([])

    assert exit_code != 0
    captured = capsys.readouterr()
    assert "no claude-checkup versions found" in (captured.out + captured.err)


def test_main_normal_run_prints_and_writes_report_matching_render_yield_and_reflects_triage_discards(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    projects_root = tmp_path / "claude_projects"
    monkeypatch.setattr(corpus, "_PROJECTS_ROOT", projects_root)
    project_dir = projects_root / "aaaa-myproj"

    def write_jsonl(filename, texts):
        write_transcript(project_dir, filename, "".join(json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": t}]}}) + "\n" for t in texts))
    now = datetime.now(timezone.utc)
    write_jsonl("t1.jsonl", ["we measured this", "and confirmed that"])
    write_jsonl("t2.jsonl", ["nothing notable here"])

    module, version = make_transcript_parser_module(
        {
            "t1.jsonl": FakeSessionData(latest=now - timedelta(days=1)),
            "t2.jsonl": FakeSessionData(latest=now - timedelta(days=1)),
        }
    )
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (module, version))

    def fake_run(cmd, **kwargs):
        prompt = cmd[-1]
        if prompt.endswith("and confirmed that"):
            return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="transient", stderr="")
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="durable", stderr="")

    monkeypatch.setattr(funnel.subprocess, "run", fake_run)

    exit_code = funnel.main([])

    assert exit_code == 0
    expected_counts = {
        "transcripts_read": 2,
        "slices_matched": 2,
        "slices_kept": 2,
        "survivors": 1,
        "claude_checkup_version": version,
    }
    expected_report = funnel.render_yield(expected_counts)

    captured = capsys.readouterr()
    assert expected_report in captured.out

    report_files = sorted((tmp_path / "dev" / "local" / "audit-results").glob("distil-memory-*.md"))
    assert len(report_files) == 1
    assert report_files[0].read_text() == expected_report


def test_main_dry_run_makes_no_model_call_and_prints_and_writes_report_matching_render_yield(
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

    module, version = make_transcript_parser_module(
        {"t1.jsonl": FakeSessionData(latest=now - timedelta(days=1))}
    )
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (module, version))

    def fail_if_called(*args, **kwargs):
        raise AssertionError("dry run must not invoke subprocess (no model calls of any tier)")

    monkeypatch.setattr(funnel.subprocess, "run", fail_if_called)

    exit_code = funnel.main(["--dry-run"])

    assert exit_code == 0
    expected_counts = {
        "transcripts_read": 1,
        "slices_matched": 1,
        "slices_kept": 1,
        "survivors": None,
        "claude_checkup_version": version,
    }
    expected_report = funnel.render_yield(expected_counts)

    captured = capsys.readouterr()
    assert expected_report in captured.out
    assert "survivors: n/a" in captured.out

    report_files = sorted((tmp_path / "dev" / "local" / "audit-results").glob("distil-memory-*.md"))
    assert len(report_files) == 1
    assert report_files[0].read_text() == expected_report


def _expected_known_counts(version, survivors=None):
    return {
        "transcripts_read": 1,
        "slices_matched": 1,
        "slices_kept": 1,
        "survivors": survivors,
        "claude_checkup_version": version,
    }


@pytest.fixture
def known_counts_transcript(tmp_path, monkeypatch):
    """A single-transcript corpus with one known assistant text block
    ("we measured this"): transcripts_read=1, slices_matched=1,
    slices_kept=1, regardless of how the judge call fails."""
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
    module, version = make_transcript_parser_module(
        {"t1.jsonl": FakeSessionData(latest=now - timedelta(days=1))}
    )
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (module, version))
    return version


def _fail_with_runtime_error(cmd, **kwargs):
    return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="claude cli exploded")


def _fail_with_missing_binary(cmd, **kwargs):
    raise FileNotFoundError("[Errno 2] No such file or directory: 'claude'")


def _fail_with_timeout(cmd, **kwargs):
    raise subprocess.TimeoutExpired(cmd=cmd, timeout=120)


@pytest.mark.parametrize(
    "fake_run, expected_stderr_substring",
    [
        (_fail_with_runtime_error, "claude cli exploded"),
        (_fail_with_missing_binary, "No such file or directory"),
        (_fail_with_timeout, "claude timed out after 120s"),
    ],
    ids=["runtime_error", "missing_binary", "timeout"],
)
def test_main_prints_known_counts_and_survivors_n_a_and_writes_stderr_and_returns_nonzero_when_judge_fails(
    known_counts_transcript, monkeypatch, capsys, fake_run, expected_stderr_substring
):
    monkeypatch.setattr(funnel.subprocess, "run", fake_run)

    exit_code = funnel.main([])

    assert exit_code != 0
    expected_report = funnel.render_yield(_expected_known_counts(known_counts_transcript))

    captured = capsys.readouterr()
    assert expected_report in captured.out
    assert "survivors: n/a" in captured.out
    assert expected_stderr_substring in captured.err


def test_main_reports_persistence_failure_to_stderr_and_returns_nonzero_when_writing_report_raises_oserror(
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
    module, version = make_transcript_parser_module(
        {"t1.jsonl": FakeSessionData(latest=now - timedelta(days=1))}
    )
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (module, version))

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="durable", stderr="")

    monkeypatch.setattr(funnel.subprocess, "run", fake_run)

    def raise_oserror(*args, **kwargs):
        raise OSError("no space left on device")

    monkeypatch.setattr(Path, "mkdir", raise_oserror)
    monkeypatch.setattr(Path, "write_text", raise_oserror)

    exit_code = funnel.main([])

    assert exit_code != 0
    expected_counts = {
        "transcripts_read": 1,
        "slices_matched": 1,
        "slices_kept": 1,
        "survivors": 1,
        "claude_checkup_version": version,
    }
    expected_report = funnel.render_yield(expected_counts)

    captured = capsys.readouterr()
    assert expected_report in captured.out
    assert "dev/local/audit-results" in captured.err


def test_main_writes_report_under_the_repository_root_and_prints_its_absolute_path_when_run_from_a_deeply_nested_cwd(
    tmp_path, monkeypatch, capsys
):
    repo_root = tmp_path / "myrepo"
    (repo_root / ".git").mkdir(parents=True)
    nested_cwd = repo_root / "a" / "b" / "c"
    nested_cwd.mkdir(parents=True)
    monkeypatch.chdir(nested_cwd)

    monkeypatch.setattr(corpus, "select_transcripts", lambda **kwargs: [])
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (ModuleType("stub"), "0.2.2"))

    def fail_if_called(*args, **kwargs):
        raise AssertionError("must not invoke the claude CLI")

    monkeypatch.setattr(funnel.subprocess, "run", fail_if_called)

    exit_code = funnel.main([])

    assert exit_code == 0

    nested_audit_dir = nested_cwd / "dev" / "local" / "audit-results"
    assert not nested_audit_dir.exists()

    report_dir = repo_root / "dev" / "local" / "audit-results"
    report_files = sorted(report_dir.glob("distil-memory-*.md"))
    assert len(report_files) == 1

    # The printed path must be the *absolute* path to the file that was
    # actually written. A relative print (e.g. bare "dev/local/audit-results/...")
    # would not equal this string, which already carries the tmp_path prefix.
    captured = capsys.readouterr()
    assert str(report_files[0]) in captured.out


def test_main_falls_back_to_cwd_dev_local_audit_results_when_no_ancestor_directory_contains_a_git_entry(
    tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)

    monkeypatch.setattr(corpus, "select_transcripts", lambda **kwargs: [])
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (ModuleType("stub"), "0.2.2"))

    def fail_if_called(*args, **kwargs):
        raise AssertionError("must not invoke the claude CLI")

    monkeypatch.setattr(funnel.subprocess, "run", fail_if_called)

    exit_code = funnel.main([])

    assert exit_code == 0
    report_files = sorted((tmp_path / "dev" / "local" / "audit-results").glob("distil-memory-*.md"))
    assert len(report_files) == 1


def test_main_help_declares_exactly_the_days_all_project_and_dry_run_flags(capsys):
    with pytest.raises(SystemExit):
        funnel.main(["--help"])

    captured = capsys.readouterr()
    help_text = captured.out + captured.err
    long_flags = set(re.findall(r"--[a-z][a-z-]*", help_text))

    assert long_flags == {"--days", "--all", "--project", "--dry-run", "--help"}


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


def test_main_never_leaks_transcript_slice_text_to_stderr_when_claude_cli_times_out(
    known_counts_transcript, monkeypatch, capsys
):
    sentinel = "SENTINEL-TRANSCRIPT-SLICE-9f3c1a-do-not-leak"

    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd=[*cmd[:-1], sentinel], timeout=120)

    monkeypatch.setattr(funnel.subprocess, "run", fake_run)

    exit_code = funnel.main([])

    assert exit_code != 0
    expected_report = funnel.render_yield(_expected_known_counts(known_counts_transcript))

    captured = capsys.readouterr()
    assert expected_report in captured.out
    assert "survivors: n/a" in captured.out
    assert sentinel not in captured.err


def test_main_stderr_still_states_the_timeout_duration_when_claude_cli_times_out(
    known_counts_transcript, monkeypatch, capsys
):
    sentinel = "SENTINEL-TRANSCRIPT-SLICE-9f3c1a-do-not-leak"

    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd=[*cmd[:-1], sentinel], timeout=120)

    monkeypatch.setattr(funnel.subprocess, "run", fake_run)

    exit_code = funnel.main([])

    assert exit_code != 0
    captured = capsys.readouterr()
    assert sentinel not in captured.err
    assert "120" in captured.err
