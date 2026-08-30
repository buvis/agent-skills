"""Tests for funnel.py's reporting path: render_yield's pure formatting and
main()'s end-to-end CLI wiring (transcript selection, triage, the distil
stage behind --distil, and the yield report printed and written to disk)."""

import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace

import corpus
import dedup
import distil
import funnel
import proposal
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


_DISTIL_LABELS = ["proposals", "discards", "new_vs_update", "skipped_by_limit", "dedup_errors"]


def _five_key_counts():
    """The pre-distil counts dict every existing render_yield caller passes:
    not one of the five distil keys is present."""
    return {
        "transcripts_read": 5,
        "slices_matched": 3,
        "slices_kept": 2,
        "survivors": 1,
        "claude_checkup_version": "0.2.2",
    }


def test_render_yield_still_renders_a_legacy_five_key_counts_dict_without_a_key_error():
    """Pins the counts.get contract directly, so rewriting a distil line to
    counts["..."] fails here instead of in eleven unrelated tests.

    Also pins the caller's dict as read-only. `counts.setdefault(label, None)`
    renders the same text but hands a five-key caller back a ten-key dict,
    which is not what "pure string formatting" means: anything that reuses,
    compares or re-serialises the dict after the call sees the five keys the
    renderer invented."""
    counts = _five_key_counts()
    before = dict(counts)

    result = funnel.render_yield(counts)

    assert "survivors: 1" in result
    assert "claude_checkup_version: 0.2.2" in result
    assert counts == before


def test_render_yield_orders_the_distil_lines_after_survivors_and_before_the_version():
    result = funnel.render_yield(_five_key_counts())

    labels = [
        match.group(1)
        for match in (re.match(r"([a-z_]+): ", line) for line in result.splitlines())
        if match
    ]

    assert labels == [
        "transcripts_read",
        "slices_matched",
        "slices_kept",
        "survivors",
        *_DISTIL_LABELS,
        "claude_checkup_version",
    ]


@pytest.mark.parametrize("set_to_none", [False, True], ids=["key_missing", "key_none"])
@pytest.mark.parametrize("label", _DISTIL_LABELS)
def test_render_yield_renders_a_distil_line_as_n_a_when_the_stage_did_not_produce_it(label, set_to_none):
    counts = _five_key_counts()
    if set_to_none:
        counts[label] = None

    result = funnel.render_yield(counts)

    assert f"{label}: n/a" in result


@pytest.mark.parametrize(
    "distil_counts, expected_lines",
    [
        (
            {"proposals": 4, "discards": 2, "new_vs_update": (5, 3), "skipped_by_limit": 7, "dedup_errors": 1},
            ["proposals: 4", "discards: 2", "new_vs_update: 5/3", "skipped_by_limit: 7", "dedup_errors: 1"],
        ),
        (
            {"proposals": 0, "discards": 0, "new_vs_update": (0, 0), "skipped_by_limit": 0, "dedup_errors": 0},
            ["proposals: 0", "discards: 0", "new_vs_update: 0/0", "skipped_by_limit: 0", "dedup_errors: 0"],
        ),
    ],
    ids=["nonzero", "all_zero"],
)
def test_render_yield_renders_the_integer_distil_counts_the_stage_produced(distil_counts, expected_lines):
    """A stage that ran and yielded nothing reports 0, never n/a: n/a means
    the stage did not run. `skipped_by_limit: 0` is the normal uncapped run,
    so treating a zero as "missing" mislabels the most common case."""
    counts = _five_key_counts()
    counts.update(distil_counts)

    result = funnel.render_yield(counts)

    for expected in expected_lines:
        assert expected in result


@pytest.mark.parametrize(
    "pair, expected",
    [((3, 1), "new_vs_update: 3/1"), ((7, 4), "new_vs_update: 7/4"), ((0, 2), "new_vs_update: 0/2")],
    ids=["three_one", "seven_four", "zero_two"],
)
def test_render_yield_joins_a_populated_new_vs_update_pair_with_a_slash(pair, expected):
    """`new_vs_update` carries the (new, update) counts as a pair of ints, not
    a pre-formatted "3/1" string: render_yield owns the presentation, so a
    later "simplification" that moves the slash into the caller fails here.
    Both elements must be read: `(7, 4)` cannot be reconstructed from the
    first element and the pair's length, and `(0, 2)` cannot be reconstructed
    by treating a zero as absent."""
    counts = _five_key_counts()
    counts["new_vs_update"] = pair

    result = funnel.render_yield(counts)

    assert expected in result


def test_render_yield_how_to_proceed_paragraph_also_points_at_the_proposals_directory():
    """The paragraph gains a sentence naming where the distil stage put its
    proposals. Binds meaning, not wording: no exact path is pinned, but the
    mention has to be a directory the reader can open, and it has to be the
    PROPOSALS one. A bare word ("... promote durable facts into memory.
    proposals.") is not a destination; neither is a decoy slash elsewhere in
    the sentence ("... promote durable facts and/or proposals into memory."),
    which satisfies a plain second-token count while telling the reader
    nothing. The path-shaped token itself must name proposals."""
    result = funnel.render_yield(_five_key_counts())

    how_to_proceed = [line for line in result.splitlines() if line.startswith("How to proceed:")]

    assert len(how_to_proceed) == 1
    line = how_to_proceed[0]
    assert "proposals" in line.lower()
    path_tokens = {token.strip(".,;:()'\"") for token in line.split() if "/" in token}
    assert any("dev/local/audit-results" in token for token in path_tokens)
    assert any("proposal" in token.lower() for token in path_tokens)
    assert len(path_tokens) >= 2


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


@pytest.fixture
def timed_out_judge(monkeypatch):
    """Monkeypatches funnel.subprocess.run so the claude CLI invocation
    times out, embedding a sentinel value in the command so a leak of
    transcript slice text into stderr would be caught. Returns the
    sentinel string."""
    sentinel = "SENTINEL-TRANSCRIPT-SLICE-9f3c1a-do-not-leak"

    def fake_run(cmd, **kwargs):
        raise subprocess.TimeoutExpired(cmd=[*cmd[:-1], sentinel], timeout=120)

    monkeypatch.setattr(funnel.subprocess, "run", fake_run)
    return sentinel


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


def test_run_triage_returns_the_surviving_slices_with_a_matching_count_and_no_error(monkeypatch):
    """Two of three slices survive, so the reported count can only be right
    by counting them: a capped `min(len(survivors), 1)` or a hardcoded 1 both
    fail here, and the count-equals-length relation is asserted directly so no
    run can report a survivor total that disagrees with the list it hands
    back."""
    transient_slice = funnel.Slice(
        text="the test suite passed again", transcript=Path("t.jsonl"), line_no=1, marker="confirmed"
    )
    durable_slice = funnel.Slice(
        text="the config lives at /etc/foo", transcript=Path("t.jsonl"), line_no=2, marker="verified"
    )
    other_durable_slice = funnel.Slice(
        text="the cheap tier is haiku", transcript=Path("t.jsonl"), line_no=3, marker="measured"
    )

    judge_calls = []

    def fake_run(cmd, **kwargs):
        judge_calls.append(cmd)
        verdict = "transient" if cmd[-1].endswith(transient_slice.text) else "durable"
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=verdict, stderr="")

    monkeypatch.setattr(funnel.subprocess, "run", fake_run)

    survivors, survivors_count, error = funnel._run_triage(
        [transient_slice, durable_slice, other_durable_slice]
    )

    assert survivors == [durable_slice, other_durable_slice]
    assert survivors_count == 2
    assert survivors_count == len(survivors)
    assert error is None
    # Each slice is judged once. Deriving the count from a second triage pass
    # would double the cheap-tier bill and let a judge that changed its mind
    # report a count that does not match the survivors returned.
    assert len(judge_calls) == 3


def test_run_triage_returns_no_slices_and_a_zero_count_for_an_empty_kept_list(monkeypatch):
    def fail_if_called(*args, **kwargs):
        raise AssertionError("an empty kept list must reach no judge")

    monkeypatch.setattr(funnel.subprocess, "run", fail_if_called)

    survivors, survivors_count, error = funnel._run_triage([])

    assert survivors == []
    assert survivors_count == 0
    assert error is None


@pytest.mark.parametrize(
    "fake_run, expected_error_substring",
    [
        (_fail_with_runtime_error, "claude cli exploded"),
        (_fail_with_missing_binary, "No such file or directory"),
        (_fail_with_timeout, "claude timed out after 120s"),
    ],
    ids=["runtime_error", "missing_binary", "timeout"],
)
def test_run_triage_returns_no_slices_and_a_none_count_when_the_judge_call_fails(
    monkeypatch, fake_run, expected_error_substring
):
    monkeypatch.setattr(funnel.subprocess, "run", fake_run)
    slice_ = funnel.Slice(text="we measured this", transcript=Path("t.jsonl"), line_no=1, marker="measured")

    survivors, survivors_count, error = funnel._run_triage([slice_])

    assert survivors == []
    assert survivors_count is None
    assert expected_error_substring in error


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


def test_main_help_declares_exactly_the_days_all_project_dry_run_and_distil_flags(capsys):
    with pytest.raises(SystemExit):
        funnel.main(["--help"])

    captured = capsys.readouterr()
    help_text = captured.out + captured.err
    long_flags = set(re.findall(r"--[a-z][a-z-]*", help_text))

    assert long_flags == {
        "--days",
        "--all",
        "--project",
        "--dry-run",
        "--distil",
        "--distil-limit",
        "--help",
    }


def test_parse_args_defaults_distil_off_and_the_distil_limit_to_25():
    args = funnel._parse_args([])

    assert args.distil is False
    assert args.distil_limit == 25


def test_parse_args_accepts_distil_with_a_zero_limit_meaning_no_cap():
    args = funnel._parse_args(["--distil", "--distil-limit", "0"])

    assert args.distil is True
    assert args.distil_limit == 0


def test_parse_args_accepts_a_distil_limit_far_above_the_default():
    """Only a negative limit is refused. Rejecting anything above the default
    25 would make every larger cap unusable, and the refusal must not come
    from enumerating the allowed values."""
    args = funnel._parse_args(["--distil-limit", "500"])

    assert args.distil_limit == 500


@pytest.mark.parametrize("limit", ["-1", "-5", "-100"], ids=["minus_one", "minus_five", "minus_hundred"])
def test_main_rejects_a_negative_distil_limit_with_a_usage_error_before_reading_any_transcript(
    monkeypatch, capsys, limit
):
    """Every negative limit is refused, not just the literal -1. Enumerating
    the rejected values (`if number == -1`) lets `--distil-limit -5` through,
    and `survivors[:-5]` silently drops five survivors while reporting a
    nonsense skipped_by_limit."""

    def fail_if_called(*args, **kwargs):
        raise AssertionError("a negative --distil-limit must be refused at parse time")

    monkeypatch.setattr(corpus, "resolve_parser", fail_if_called)

    with pytest.raises(SystemExit) as exc_info:
        funnel.main(["--distil-limit", limit])

    assert exc_info.value.code == 2
    captured = capsys.readouterr()
    error_text = (captured.out + captured.err).lower()
    assert "--distil-limit" in error_text
    # A module that never declared the flag also exits 2, naming it in an
    # "unrecognized arguments" message. The refusal has to be about the
    # value, otherwise this test cannot tell the two apart.
    assert "unrecognized" not in error_text
    assert any(stem in error_text for stem in ("negativ", "invalid", "must", "cannot", "at least"))


def test_main_notes_to_stderr_that_distil_is_ignored_only_when_it_is_combined_with_dry_run(
    tmp_path, monkeypatch, capsys
):
    """All three legs, because "only when" is the claim: no note without
    --distil, no note for --distil on its own (that run is not ignoring
    anything), and a note only for the combination."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(corpus, "select_transcripts", lambda **kwargs: [])
    monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (ModuleType("stub"), "0.2.2"))

    assert funnel.main(["--dry-run"]) == 0
    assert "--distil" not in capsys.readouterr().err

    assert funnel.main(["--distil"]) == 0
    assert "--distil" not in capsys.readouterr().err

    assert funnel.main(["--dry-run", "--distil"]) == 0
    assert "--distil" in capsys.readouterr().err


def test_main_with_distil_still_selects_transcripts_over_the_requested_days_and_still_judges_them(
    known_counts_transcript, monkeypatch, capsys
):
    """Passing --distil must not rewrite the other flags. A main() that
    quietly sets dry_run=True and days=distil_limit turns a real 90-day run
    into a 25-day dry run that never calls the judge and reports
    `survivors: n/a` - and every existing flag test still passes, because none
    of them passes --distil. Only the cheap tier is counted: triage judges the
    one slice once, whatever the distil stage then asks the strong tier."""
    calls = []
    real_select_transcripts = corpus.select_transcripts

    def recording_select_transcripts(**kwargs):
        calls.append(kwargs)
        return real_select_transcripts(**kwargs)

    monkeypatch.setattr(corpus, "select_transcripts", recording_select_transcripts)

    judge_calls = []

    def fake_run(cmd, **kwargs):
        judge_calls.append(cmd)
        return subprocess.CompletedProcess(args=cmd, returncode=0, stdout="durable", stderr="")

    monkeypatch.setattr(funnel.subprocess, "run", fake_run)

    exit_code = funnel.main(["--distil", "--days", "90"])

    assert exit_code == 0
    assert len(calls) == 1
    assert calls[0]["days"] == 90
    assert len([cmd for cmd in judge_calls if cmd[3] == "haiku"]) == 1
    captured = capsys.readouterr()
    assert "survivors: 1" in captured.out
    assert "survivors: n/a" not in captured.out


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


def test_main_never_leaks_transcript_slice_text_to_stderr_when_claude_cli_times_out(
    known_counts_transcript, timed_out_judge, capsys
):
    sentinel = timed_out_judge

    exit_code = funnel.main([])

    assert exit_code != 0
    expected_report = funnel.render_yield(_expected_known_counts(known_counts_transcript))

    captured = capsys.readouterr()
    assert expected_report in captured.out
    assert "survivors: n/a" in captured.out
    assert sentinel not in captured.err


def test_main_stderr_still_states_the_timeout_duration_when_claude_cli_times_out(
    known_counts_transcript, timed_out_judge, capsys
):
    sentinel = timed_out_judge

    exit_code = funnel.main([])

    assert exit_code != 0
    captured = capsys.readouterr()
    assert sentinel not in captured.err
    assert "120" in captured.err


# --- the distil stage main() drives behind --distil --------------------------

_SLICE_ONE = "we measured that the cheap judge tier resolves to haiku"
_SLICE_TWO = "we verified that the yield report lands under audit results"
_SLICE_THREE = "we confirmed the suite passed again"

_INDEX_HEADER = "# Project memory\n\n"
_ENTRY_CHEAP_TIER_MAP = (
    "- [Cheap tier map](cheap-tier-map.md) — the cheap judge tier resolves to the haiku model.\n"
)
_ENTRY_REPORT_DIRECTORY = (
    "- [Report directory](report-directory.md) — the yield report lands under audit results.\n"
)
_INDEX = _INDEX_HEADER + _ENTRY_CHEAP_TIER_MAP + _ENTRY_REPORT_DIRECTORY

_MEMORY_CHEAP_TIER_MAP = """---
name: cheap-tier-map
description: "The cheap judge tier maps to the haiku model"
metadata:
  node_type: memory
  type: project
---

The cheap tier maps to haiku.

**Why:** the wrong tier picks the wrong model and every call costs more.

**How to apply:** read the tier map before naming a model.
"""

_MEMORY_REPORT_DIRECTORY = """---
name: report-directory
description: "The yield report is written under the audit results directory"
metadata:
  node_type: memory
  type: project
---

The yield report lands under dev/local/audit-results.

**Why:** a reader who looks anywhere else finds nothing.

**How to apply:** open that directory after a run.
"""

# An indexed memory that is NOT a project memory, named so it sorts ahead of
# every other entry: a stage that anchors on whatever the index names picks it
# up first and hands the distiller imported prose as house style.
_ENTRY_REFERENCE_NOTE = (
    "- [Reference note](aaa-reference-note.md) — the cheap judge tier resolves to the haiku model.\n"
)

_MEMORY_REFERENCE_NOTE = """---
name: aaa-reference-note
description: "An imported reference page about the judge tiers"
metadata:
  node_type: memory
  type: reference
---

Imported reference material about the judge tiers.

**Why:** a page copied in from elsewhere is not this project's own memory.

**How to apply:** read it for background, never as the shape to copy.
"""

_PROPOSAL_ONE = """---
name: cheap-tier-is-haiku
description: "The cheap judge tier resolves to the haiku model"
metadata:
  node_type: memory
  type: project
---

The cheap tier resolves to haiku, so a cheap call never reaches sonnet. See [[cheap-tier-map]].

**Why:** a run that picks the strong tier for triage pays for every slice.

**How to apply:** name the tier, never the model, when asking for a verdict.
"""

_PROPOSAL_TWO = """---
name: report-under-audit-results
description: "The yield report is written under the audit results directory"
metadata:
  node_type: memory
  type: project
---

Every run writes its yield report under dev/local/audit-results. See [[report-directory]].

**Why:** a reader who looks in the skill directory finds nothing.

**How to apply:** open the audit results folder to read the newest report.
"""

_DISCARD_ANSWER = "DISCARD: this only repeats that a suite passed"
_DISCARD_REASON = "this only repeats that a suite passed"

# A second memory file carrying the same frontmatter name as _PROPOSAL_ONE.
_PROPOSAL_SAME_NAME = """---
name: cheap-tier-is-haiku
description: "The strong judge tier resolves to the sonnet model"
metadata:
  node_type: memory
  type: project
---

The strong tier resolves to sonnet, so a strong call never lands on haiku. See [[cheap-tier-map]].

**Why:** a run that names a model directly drifts the day the map changes.

**How to apply:** ask for the strong tier whenever a verdict needs judgement.
"""

# A memory file that is valid apart from a name aimed outside its directory.
_PROPOSAL_HOSTILE_NAME = """---
name: ../Escape Hatch
description: "Every distilled memory file is published inside the run's proposals directory"
metadata:
  node_type: memory
  type: project
---

A run publishes its memory files inside its own proposals directory. See [[report-directory]].

**Why:** a file written anywhere else is invisible to the run that produced it.

**How to apply:** open the run's proposals directory to find what it published.
"""

# A memory file that is valid on its own but links to no other memory. Whether
# that is acceptable is the plane's call, not the file's: over an index that
# names memories to link to it is a discard, over one that names none it is a
# proposal. The same answer is used for both.
_PROPOSAL_WITHOUT_A_LINK = """---
name: strong-tier-is-sonnet
description: "The strong judge tier resolves to the sonnet model"
metadata:
  node_type: memory
  type: project
---

The strong tier resolves to sonnet, so a strong call never lands on haiku.

**Why:** a run that names a model directly drifts the day the tier map changes.

**How to apply:** ask for the strong tier whenever a verdict needs judgement.
"""

# Two answers no validator accepts: one with frontmatter missing the required
# fields, one with no frontmatter at all (so not even a name can be parsed).
_MALFORMED_ANSWER = """---
name: ../../pwned
---

Sure! Here is the memory file you asked for..."""

_UNPARSEABLE_ANSWER = "Sure! Here is the memory file you asked for, without any frontmatter."


def _tier_note(number):
    """One more indexed memory sharing the proposal's words, so a long index
    offers a shortlist far more candidates than it is allowed to read."""
    name = f"tier-note-{number}"
    entry = (
        f"- [Tier note {number}]({name}.md) — "
        f"the cheap judge tier resolves to the haiku model, note {number}.\n"
    )
    text = f"""---
name: {name}
description: "The cheap judge tier resolves to the haiku model, note {number}"
metadata:
  node_type: memory
  type: project
---

Note {number} on the cheap tier.

**Why:** the tier map reads as settled while a note still disagrees with it.

**How to apply:** open note {number} beside the tier map.
"""
    return name, entry, text


def _deliver(cmd, answer):
    """One fake CLI answer: a string is stdout from a clean exit, a callable
    is a failing `subprocess.run` stand-in (the module already defines three)."""
    if callable(answer):
        return answer(cmd)
    return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=answer, stderr="")


class FakeClaudeCli:
    """Stands in for the `claude` binary at funnel.subprocess.run, so the whole
    pipeline runs for real while no test reaches a model.

    Routes on what actually arrived: the cheap tier is always triage, a
    strong-tier prompt ending in a slice's text is the distil call (the distil
    prompt puts the snippet last), and any other strong-tier prompt is dedup's
    classify call. Records what it was asked, so a test can pin what the stage
    did NOT ask for.
    """

    def __init__(self, distil_answers, classify=None, transient_texts=()):
        self.distil_answers = dict(distil_answers)
        self.classify = classify if classify is not None else (lambda prompt: "new")
        self.transient_texts = tuple(transient_texts)
        self.distilled = []
        self.distil_prompts = []
        self.classified = []

    def __call__(self, cmd, **kwargs):
        prompt = cmd[-1]
        if cmd[3] == "haiku":
            verdict = "transient" if prompt.endswith(self.transient_texts) else "durable"
            return _deliver(cmd, verdict)
        for text, answer in self.distil_answers.items():
            if prompt.endswith(text):
                self.distilled.append(text)
                self.distil_prompts.append(prompt)
                return _deliver(cmd, answer)
        self.classified.append(prompt)
        return _deliver(cmd, self.classify(prompt))


def _refuse_to_distil(cmd, **kwargs):
    raise AssertionError("the stage must stop after the CLI goes missing, not distil the next survivor")


@pytest.fixture
def make_corpus(tmp_path, monkeypatch):
    """Build a one-project corpus under tmp_path and return its landmarks.

    Each `slice_texts` entry becomes one assistant text block on its own JSONL
    line of a single transcript, so slice N carries line_no N. The project's
    memory plane sits where the distil stage looks for it - beside the
    transcript, at `<project>/memory` - and holds an index naming two memories,
    both on disk, plus an unindexed decoy no step is allowed to open.
    `extra_memories` adds that many further indexed memories, for a plane whose
    index outgrows the shortlist.
    """

    def build(slice_texts=(_SLICE_ONE, _SLICE_TWO), extra_memories=0):
        monkeypatch.chdir(tmp_path)
        projects_root = tmp_path / "claude_projects"
        monkeypatch.setattr(corpus, "_PROJECTS_ROOT", projects_root)
        project_dir = projects_root / "aaaa-myproj"
        transcript = write_transcript(
            project_dir,
            "t1.jsonl",
            "".join(
                json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}) + "\n"
                for text in slice_texts
            ),
        )
        memory_dir = project_dir / "memory"
        memory_dir.mkdir()
        notes = [_tier_note(number) for number in range(1, extra_memories + 1)]
        (memory_dir / "MEMORY.md").write_text(_INDEX + "".join(entry for _, entry, _ in notes))
        for name, _entry, text in notes:
            (memory_dir / f"{name}.md").write_text(text)
        (memory_dir / "cheap-tier-map.md").write_text(_MEMORY_CHEAP_TIER_MAP)
        (memory_dir / "report-directory.md").write_text(_MEMORY_REPORT_DIRECTORY)
        (memory_dir / "unindexed-decoy.md").write_text("---\nname: unindexed-decoy\n---\n\nnot in the index\n")

        module, version = make_transcript_parser_module(
            {"t1.jsonl": FakeSessionData(latest=datetime.now(timezone.utc) - timedelta(days=1))}
        )
        monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (module, version))
        return SimpleNamespace(
            transcript=transcript,
            memory_dir=memory_dir,
            decoy=memory_dir / "unindexed-decoy.md",
            audit_dir=tmp_path / "dev" / "local" / "audit-results",
            version=version,
        )

    return build


@pytest.fixture
def make_two_project_corpus(tmp_path, monkeypatch):
    """Build a corpus of two projects and return both projects' landmarks.

    Each project owns a transcript carrying one slice, its own index naming one
    memory, and that memory on disk. Nothing is shared between the planes, so a
    proposal typed against the wrong one cannot resolve to an update.
    """

    def build():
        monkeypatch.chdir(tmp_path)
        projects_root = tmp_path / "claude_projects"
        monkeypatch.setattr(corpus, "_PROJECTS_ROOT", projects_root)

        projects = []
        for directory, filename, slice_text, entry, memory_name, memory_text in (
            (
                "aaaa-projone",
                "t1.jsonl",
                _SLICE_ONE,
                _ENTRY_CHEAP_TIER_MAP,
                "cheap-tier-map",
                _MEMORY_CHEAP_TIER_MAP,
            ),
            (
                "bbbb-projtwo",
                "t2.jsonl",
                _SLICE_TWO,
                _ENTRY_REPORT_DIRECTORY,
                "report-directory",
                _MEMORY_REPORT_DIRECTORY,
            ),
        ):
            project_dir = projects_root / directory
            transcript = write_transcript(
                project_dir,
                filename,
                json.dumps(
                    {"type": "assistant", "message": {"content": [{"type": "text", "text": slice_text}]}}
                )
                + "\n",
            )
            memory_dir = project_dir / "memory"
            memory_dir.mkdir()
            (memory_dir / "MEMORY.md").write_text(_INDEX_HEADER + entry)
            (memory_dir / f"{memory_name}.md").write_text(memory_text)
            projects.append(SimpleNamespace(transcript=transcript, memory_dir=memory_dir))

        recent = FakeSessionData(latest=datetime.now(timezone.utc) - timedelta(days=1))
        module, version = make_transcript_parser_module({"t1.jsonl": recent, "t2.jsonl": recent})
        monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (module, version))
        return SimpleNamespace(
            one=projects[0],
            two=projects[1],
            audit_dir=tmp_path / "dev" / "local" / "audit-results",
        )

    return build


def _published(audit_dir):
    """The single proposals directory a distil run publishes, with both of its
    manifests already parsed."""
    directories = sorted(audit_dir.glob("distil-memory-*-proposals"))
    assert len(directories) == 1, f"expected one proposals directory, found {[p.name for p in directories]}"
    out_dir = directories[0]
    return (
        out_dir,
        json.loads((out_dir / "proposals.json").read_text()),
        json.loads((out_dir / "discards.json").read_text()),
    )


def _record_read_text(monkeypatch):
    """Every path opened with Path.read_text from now on, in order."""
    reads = []
    real_read_text = Path.read_text

    def recording_read_text(self, *args, **kwargs):
        reads.append(Path(self))
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", recording_read_text)
    return reads


def _forbid_full_read(monkeypatch, memory_dir, decoy):
    """Make `decoy` explode when read and `memory_dir` explode when listed.

    An exception the pipeline could swallow would prove nothing, so both raise
    AssertionError, which no handler on the path catches.
    """
    real_read_text = Path.read_text
    real_scandir = os.scandir
    real_listdir = os.listdir

    def refuse_walk(path):
        try:
            walked = Path(path)
        except TypeError:
            return
        if walked == memory_dir:
            raise AssertionError(f"{memory_dir} must never be listed: only the names the index gives may be opened")

    def guarded_read_text(self, *args, **kwargs):
        if Path(self) == decoy:
            raise AssertionError(f"{decoy.name} is not named by the index and must never be read")
        return real_read_text(self, *args, **kwargs)

    def guarded_scandir(path=".", *args, **kwargs):
        refuse_walk(path)
        return real_scandir(path, *args, **kwargs)

    def guarded_listdir(path=".", *args, **kwargs):
        refuse_walk(path)
        return real_listdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)
    monkeypatch.setattr(os, "scandir", guarded_scandir)
    monkeypatch.setattr(os, "listdir", guarded_listdir)


def test_main_with_distil_and_dry_run_distils_nothing_and_says_so_on_stderr(make_corpus, monkeypatch, capsys):
    """A dry run reaches no model of any tier, so it cannot have distilled
    anything: no proposals directory, and every distil count reads n/a."""
    built = make_corpus()

    def fail_if_called(*args, **kwargs):
        raise AssertionError("a dry run must reach no model of any tier")

    monkeypatch.setattr(funnel.subprocess, "run", fail_if_called)

    exit_code = funnel.main(["--distil", "--dry-run"])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "--distil" in captured.err
    assert "transcripts_read: 1" in captured.out
    assert "slices_kept: 2" in captured.out
    for label in _DISTIL_LABELS:
        assert f"{label}: n/a" in captured.out
    assert list(built.audit_dir.glob("*-proposals")) == []


def test_main_with_distil_publishes_the_proposals_directory_and_reports_integer_counts(
    make_corpus, monkeypatch, capsys
):
    """The wiring pin: a real --distil run (no --dry-run) over a one-slice
    corpus. A main() that parses the flag and ignores it renders every distil
    count as n/a and writes no proposals directory, so both are asserted."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    fake_cli = FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE})
    monkeypatch.setattr(funnel.subprocess, "run", fake_cli)

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "proposals: 1" in out
    assert "discards: 0" in out
    assert "new_vs_update: 1/0" in out
    assert "skipped_by_limit: 0" in out
    assert "dedup_errors: 0" in out
    for label in _DISTIL_LABELS:
        assert f"{label}: n/a" not in out

    out_dir, records, discards = _published(built.audit_dir)
    assert sorted(p.name for p in out_dir.glob("*.md")) == ["cheap-tier-is-haiku.md"]
    assert (out_dir / "cheap-tier-is-haiku.md").read_text() == _PROPOSAL_ONE.strip()
    assert discards == []
    assert [record["name"] for record in records] == ["cheap-tier-is-haiku"]
    assert [record["kind"] for record in records] == ["new"]
    assert records[0]["dedup_error"] is None
    assert records[0]["transcript"] == str(built.transcript)
    assert records[0]["line_no"] == 1
    assert records[0]["evidence_text"] == _SLICE_ONE

    for published_file in out_dir.glob("*.md"):
        proposal.validate(
            proposal.Proposal(
                file_text=published_file.read_text(),
                evidence=proposal.Evidence(transcript=built.transcript, line_no=1, text=_SLICE_ONE),
            )
        )


def test_main_asks_the_distiller_with_the_discard_convention_and_the_planes_anchors(
    make_corpus, monkeypatch
):
    """The slice alone is not a prompt. Without the discard convention the model
    has no way to turn a transient snippet down, and without anchors it has no
    house style to copy, so both have to reach the strong tier with the text.

    The anchors are the ones the plane offers: capped, and project memories
    only. A stage that anchors on everything the index names grows its prompt
    with the size of the memory plane and quotes imported reference pages back
    at the model as the shape to copy.
    """
    built = make_corpus(slice_texts=(_SLICE_ONE,), extra_memories=8)
    index = built.memory_dir / "MEMORY.md"
    (built.memory_dir / "aaa-reference-note.md").write_text(_MEMORY_REFERENCE_NOTE)
    index.write_text(index.read_text() + _ENTRY_REFERENCE_NOTE)
    index_text = index.read_text()
    anchors = distil.load_examples(built.memory_dir, index_text)
    ignored = [
        text
        for text in (
            (built.memory_dir / f"{name}.md").read_text() for name in sorted(dedup.parse_index(index_text))
        )
        if text not in anchors
    ]
    fake_cli = FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE})
    monkeypatch.setattr(funnel.subprocess, "run", fake_cli)

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    assert len(fake_cli.distil_prompts) == 1
    prompt = fake_cli.distil_prompts[0]
    assert "DISCARD:" in prompt
    assert _SLICE_ONE in prompt

    assert len(anchors) == distil.EXAMPLE_COUNT
    assert _MEMORY_CHEAP_TIER_MAP in anchors
    for anchor in anchors:
        assert anchor in prompt
    assert _MEMORY_REFERENCE_NOTE in ignored, "the fixture must offer a non-project memory to ignore"
    assert len(ignored) > 1, "the fixture must name more memories than the anchor cap allows"
    for text in ignored:
        assert text not in prompt
    assert list(built.audit_dir.glob("distil-memory-*-proposals"))


def test_main_with_distil_reports_the_new_update_split_and_names_the_reason_each_discard_carries(
    make_corpus, monkeypatch, capsys
):
    """Three survivors, three outcomes: one memory the plane does not hold, one
    that restates an existing memory, and one the distiller turns down. The
    split and the discard's reason both have to reach disk."""
    built = make_corpus(slice_texts=(_SLICE_ONE, _SLICE_TWO, _SLICE_THREE))
    fake_cli = FakeClaudeCli(
        {_SLICE_ONE: _PROPOSAL_ONE, _SLICE_TWO: _PROPOSAL_TWO, _SLICE_THREE: _DISCARD_ANSWER},
        classify=lambda prompt: "report-directory" if "report-under-audit-results" in prompt else "new",
    )
    monkeypatch.setattr(funnel.subprocess, "run", fake_cli)

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "proposals: 2" in out
    assert "discards: 1" in out
    assert "new_vs_update: 1/1" in out

    _out_dir, records, discards = _published(built.audit_dir)
    by_name = {record["name"]: record for record in records}
    assert set(by_name) == {"cheap-tier-is-haiku", "report-under-audit-results"}
    assert by_name["cheap-tier-is-haiku"]["kind"] == "new"
    assert by_name["cheap-tier-is-haiku"]["existing_text"] is None
    assert by_name["report-under-audit-results"]["kind"] == "update report-directory"
    assert by_name["report-under-audit-results"]["existing_text"] == _MEMORY_REPORT_DIRECTORY
    assert discards == [
        {"transcript": str(built.transcript), "line_no": 3, "reason": _DISCARD_REASON}
    ]


@pytest.mark.parametrize(
    "answer",
    [_MALFORMED_ANSWER, _UNPARSEABLE_ANSWER],
    ids=["frontmatter_missing_fields", "no_frontmatter_at_all"],
)
def test_main_discards_an_answer_that_is_not_a_usable_memory_file_and_still_reports(
    answer, tmp_path, make_corpus, monkeypatch, capsys
):
    """Nothing the model sends back is published unchecked. An answer that
    breaks the memory-file contract leaves a named discard and no file, and the
    run still ends in a report: an answer nobody can even parse a name out of
    must not take the run down with it."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    monkeypatch.setattr(funnel.subprocess, "run", FakeClaudeCli({_SLICE_ONE: answer}))

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "proposals: 0" in out
    assert "discards: 1" in out
    assert "new_vs_update: 0/0" in out
    assert len(sorted(built.audit_dir.glob("distil-memory-*.md"))) == 1

    out_dir, records, discards = _published(built.audit_dir)
    assert records == []
    assert sorted(path.name for path in out_dir.iterdir()) == ["discards.json", "proposals.json"]
    assert len(discards) == 1
    assert discards[0]["transcript"] == str(built.transcript)
    assert discards[0]["line_no"] == 1
    assert discards[0]["reason"].strip()
    assert list(tmp_path.rglob("*pwned*")) == []


def test_main_discards_an_answer_that_links_to_nothing_when_the_index_names_memories_to_link(
    make_corpus, monkeypatch, capsys
):
    """A memory that joins a populated plane has to link into it, so an answer
    carrying no [[link]] is not a usable memory file there. The rule can only
    fire if the plane's own names reach the validator: a stage that always says
    the index is empty publishes this answer instead."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    monkeypatch.setattr(
        funnel.subprocess, "run", FakeClaudeCli({_SLICE_ONE: _PROPOSAL_WITHOUT_A_LINK})
    )

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "proposals: 0" in out
    assert "discards: 1" in out

    out_dir, records, discards = _published(built.audit_dir)
    assert records == []
    assert list(out_dir.glob("*.md")) == []
    assert len(discards) == 1
    assert discards[0]["line_no"] == 1
    assert "link" in discards[0]["reason"]


def test_main_publishes_an_answer_that_links_to_nothing_when_the_index_names_no_memory(
    make_corpus, monkeypatch, capsys
):
    """The companion: the same answer over a plane whose index names nothing.
    There is no memory to link to, so demanding a link would discard the first
    memory every project ever distils. A stage that always says the index has
    names throws this one away."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    (built.memory_dir / "MEMORY.md").write_text(_INDEX_HEADER)
    monkeypatch.setattr(
        funnel.subprocess, "run", FakeClaudeCli({_SLICE_ONE: _PROPOSAL_WITHOUT_A_LINK})
    )

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "proposals: 1" in out
    assert "discards: 0" in out
    assert "dedup_errors: 0" in out

    out_dir, records, discards = _published(built.audit_dir)
    assert discards == []
    assert [record["name"] for record in records] == ["strong-tier-is-sonnet"]
    assert (out_dir / "strong-tier-is-sonnet.md").read_text() == _PROPOSAL_WITHOUT_A_LINK.strip()


def test_main_publishes_a_proposal_named_for_another_directory_inside_its_own(
    tmp_path, make_corpus, monkeypatch, capsys
):
    """A frontmatter name is model output, so it reaches the filesystem only as
    a sanitised stem. A name carrying `../` must not steer the file out of the
    run's proposals directory, where nothing would ever find it again."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    monkeypatch.setattr(
        funnel.subprocess, "run", FakeClaudeCli({_SLICE_ONE: _PROPOSAL_HOSTILE_NAME})
    )

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    assert "proposals: 1" in capsys.readouterr().out

    out_dir, records, _discards = _published(built.audit_dir)
    assert len(records) == 1
    assert sorted(path.name for path in out_dir.glob("*.md")) == ["escape-hatch.md"]
    assert (out_dir / "escape-hatch.md").read_text() == _PROPOSAL_HOSTILE_NAME.strip()
    strays = [path for path in tmp_path.rglob("*scape*") if path.parent != out_dir]
    assert strays == []


def test_main_publishes_two_proposals_that_share_a_name_as_two_files(
    make_corpus, monkeypatch, capsys
):
    """Two survivors can distil to the same frontmatter name, and each one is a
    separate proposal about a separate slice. Writing both to one path keeps the
    later text only and leaves two records pointing at a file one of them never
    wrote."""
    built = make_corpus()
    monkeypatch.setattr(
        funnel.subprocess,
        "run",
        FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE, _SLICE_TWO: _PROPOSAL_SAME_NAME}),
    )

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    assert "proposals: 2" in capsys.readouterr().out

    out_dir, records, _discards = _published(built.audit_dir)
    assert len(records) == 2
    assert sorted(path.read_text() for path in out_dir.glob("*.md")) == sorted(
        [_PROPOSAL_ONE.strip(), _PROPOSAL_SAME_NAME.strip()]
    )


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


def test_main_keeps_the_proposal_as_new_with_a_dedup_error_when_the_index_cannot_be_read(
    make_corpus, monkeypatch, capsys
):
    """Failure path one: the index is present but unreadable. The proposal
    survives, types as new without a model call, and says what failed."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    index = built.memory_dir / "MEMORY.md"
    index.unlink()
    index.mkdir()
    fake_cli = FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE})
    monkeypatch.setattr(funnel.subprocess, "run", fake_cli)

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    assert "dedup_errors: 1" in capsys.readouterr().out
    assert fake_cli.classified == []

    _out_dir, records, _discards = _published(built.audit_dir)
    assert [record["kind"] for record in records] == ["new"]
    assert isinstance(records[0]["dedup_error"], str)
    assert records[0]["dedup_error"].strip()


def test_main_keeps_the_proposal_as_new_with_a_dedup_error_naming_a_candidate_it_could_not_read(
    make_corpus, monkeypatch, capsys
):
    """Failure path two: the shortlisted memory exists but will not open. The
    proposal is kept and the error names the memory that stayed unread."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    candidate = built.memory_dir / "cheap-tier-map.md"
    candidate.unlink()
    candidate.mkdir()
    fake_cli = FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE})
    monkeypatch.setattr(funnel.subprocess, "run", fake_cli)

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    assert "dedup_errors: 1" in capsys.readouterr().out

    _out_dir, records, _discards = _published(built.audit_dir)
    assert [record["kind"] for record in records] == ["new"]
    assert "cheap-tier-map" in records[0]["dedup_error"]


def test_main_keeps_the_proposal_as_new_with_a_dedup_error_when_the_dedup_judge_fails(
    make_corpus, monkeypatch, capsys
):
    """Failure path three: the typing call itself errors. The distilled memory
    is not thrown away because the model that would have typed it fell over."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    fake_cli = FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE}, classify=lambda prompt: _fail_with_runtime_error)
    monkeypatch.setattr(funnel.subprocess, "run", fake_cli)

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    assert "dedup_errors: 1" in capsys.readouterr().out
    assert len(fake_cli.classified) == 1

    _out_dir, records, _discards = _published(built.audit_dir)
    assert [record["name"] for record in records] == ["cheap-tier-is-haiku"]
    assert [record["kind"] for record in records] == ["new"]
    assert isinstance(records[0]["dedup_error"], str)
    assert records[0]["dedup_error"].strip()


def test_main_sets_the_dedup_error_on_every_proposal_from_a_directory_whose_index_cannot_be_read(
    make_corpus, monkeypatch, capsys
):
    """The index is read once for the directory, before any proposal exists, so
    the failure has to be held and handed to every proposal that follows - not
    only the one being built when it happened."""
    built = make_corpus()
    index = built.memory_dir / "MEMORY.md"
    index.unlink()
    index.mkdir()
    monkeypatch.setattr(
        funnel.subprocess, "run", FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE, _SLICE_TWO: _PROPOSAL_TWO})
    )

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    assert "dedup_errors: 2" in capsys.readouterr().out

    _out_dir, records, _discards = _published(built.audit_dir)
    assert len(records) == 2
    assert [record["kind"] for record in records] == ["new", "new"]
    errors = [record["dedup_error"] for record in records]
    assert all(isinstance(error, str) and error.strip() for error in errors)
    assert errors[0] == errors[1]


def test_main_ends_the_distil_stage_without_a_dedup_error_when_the_cli_is_missing_during_dedup(
    make_corpus, monkeypatch, capsys
):
    """A missing binary fails identically for every remaining call, so the
    stage stops rather than burning the cap. It is an abort, not a dedup
    failure: nothing is annotated, and what was already produced still ships.
    Only that - the proposal whose typing call hit the missing binary was never
    typed, so shipping it as `new` would report a verdict nobody reached."""
    built = make_corpus(slice_texts=(_SLICE_ONE, _SLICE_TWO, _SLICE_THREE))
    fake_cli = FakeClaudeCli(
        {_SLICE_ONE: _PROPOSAL_ONE, _SLICE_TWO: _PROPOSAL_TWO, _SLICE_THREE: _refuse_to_distil},
        classify=lambda prompt: _fail_with_missing_binary if "report-under-audit-results" in prompt else "new",
    )
    monkeypatch.setattr(funnel.subprocess, "run", fake_cli)

    exit_code = funnel.main(["--distil"])

    assert exit_code != 0
    assert fake_cli.distilled == [_SLICE_ONE, _SLICE_TWO]
    assert "dedup_errors: 0" in capsys.readouterr().out

    out_dir, records, _discards = _published(built.audit_dir)
    assert (out_dir / "cheap-tier-is-haiku.md").read_text() == _PROPOSAL_ONE.strip()
    assert [record["name"] for record in records] == ["cheap-tier-is-haiku"]
    assert sorted(path.name for path in out_dir.glob("*.md")) == ["cheap-tier-is-haiku.md"]
    assert all(record["dedup_error"] is None for record in records)


def test_main_ends_the_distil_stage_at_once_when_the_cli_is_missing_during_distillation(
    make_corpus, monkeypatch, capsys
):
    """The same abort at the earlier of the two strong calls. A missing binary
    fails identically for every remaining survivor, so the first distil call
    that hits it ends the stage. Recording it as a discard instead would burn
    the whole cap and fill the run's manifest with one junk discard per
    survivor, each naming a failure the model never saw."""
    built = make_corpus()
    fake_cli = FakeClaudeCli({_SLICE_ONE: _fail_with_missing_binary, _SLICE_TWO: _refuse_to_distil})
    monkeypatch.setattr(funnel.subprocess, "run", fake_cli)

    exit_code = funnel.main(["--distil"])

    assert exit_code != 0
    assert fake_cli.distilled == [_SLICE_ONE]
    out = capsys.readouterr().out
    assert "survivors: 2" in out
    assert "proposals: 0" in out
    assert "discards: 0" in out

    out_dir, records, discards = _published(built.audit_dir)
    assert discards == []
    assert records == []
    assert list(out_dir.glob("*.md")) == []


def test_main_types_a_proposal_as_new_when_the_typing_answer_names_no_shortlisted_memory(
    make_corpus, monkeypatch, capsys
):
    """The typing verdict is a choice from the shortlist, not prose to copy into
    the kind. An answer naming no memory the plane holds means there is nothing
    to update, so the proposal ships as new instead of as an update to a
    sentence nobody can resolve to a file."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    fake_cli = FakeClaudeCli(
        {_SLICE_ONE: _PROPOSAL_ONE}, classify=lambda prompt: "I think this one is brand new."
    )
    monkeypatch.setattr(funnel.subprocess, "run", fake_cli)

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "proposals: 1" in out
    assert "new_vs_update: 1/0" in out
    assert "dedup_errors: 0" in out
    assert len(fake_cli.classified) == 1

    _out_dir, records, _discards = _published(built.audit_dir)
    assert [record["kind"] for record in records] == ["new"]
    assert records[0]["existing_text"] is None
    assert records[0]["dedup_error"] is None


def test_main_reads_no_more_memories_than_the_anchor_cap_and_the_shortlist_allow(
    make_corpus, monkeypatch, capsys
):
    """The anchor cap and the shortlist together are what bound the cost of a
    run. With an index naming ten memories, the WHOLE run over one survivor -
    anchors and candidates alike - opens at most the anchor cap plus the
    shortlist limit, so the price does not grow with the size of the plane."""
    built = make_corpus(slice_texts=(_SLICE_ONE,), extra_memories=8)
    reads = _record_read_text(monkeypatch)
    fake_cli = FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE})
    monkeypatch.setattr(funnel.subprocess, "run", fake_cli)

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    assert "proposals: 1" in capsys.readouterr().out
    assert fake_cli.distilled == [_SLICE_ONE], "the survivor was never distilled"

    memory_reads = [
        path for path in reads if path.parent == built.memory_dir and path.name != "MEMORY.md"
    ]
    assert len(memory_reads) <= dedup.SHORTLIST_LIMIT + distil.EXAMPLE_COUNT


def test_main_types_a_proposal_without_ever_reading_a_memory_the_index_does_not_name(
    make_corpus, monkeypatch, capsys
):
    """The no-full-read pin over the whole pipeline. The memory plane holds an
    unindexed decoy that explodes when opened, and listing the directory is
    refused outright, so any step that walks the plane instead of following the
    index fails here - anchors, shortlist, candidates and typing alike."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    expected_existing = (built.memory_dir / "cheap-tier-map.md").read_text()
    _forbid_full_read(monkeypatch, built.memory_dir, built.decoy)
    monkeypatch.setattr(
        funnel.subprocess,
        "run",
        FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE}, classify=lambda prompt: "cheap-tier-map"),
    )

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    assert "proposals: 1" in capsys.readouterr().out

    _out_dir, records, _discards = _published(built.audit_dir)
    assert [record["kind"] for record in records] == ["update cheap-tier-map"]
    assert records[0]["existing_text"] == expected_existing
    assert records[0]["dedup_error"] is None


def test_main_reads_a_memory_directorys_index_once_however_many_survivors_it_holds(
    make_corpus, monkeypatch
):
    """The index, the anchors and the has-names flag are cached per memory
    directory. Re-reading MEMORY.md per survivor costs a file read for every
    slice and lets two survivors of one directory disagree about its index."""
    built = make_corpus()
    reads = _record_read_text(monkeypatch)
    monkeypatch.setattr(
        funnel.subprocess, "run", FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE, _SLICE_TWO: _PROPOSAL_TWO})
    )

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    assert reads.count(built.memory_dir / "MEMORY.md") == 1


def test_main_types_each_projects_proposal_against_that_projects_own_memory_plane(
    make_two_project_corpus, monkeypatch, capsys
):
    """A run spanning two projects meets two memory planes, and the plane a
    proposal is typed against is the one beside its own transcript. A stage that
    settles on one directory for the whole run types the second project's
    proposal against the first project's memories: it would find nothing to
    update there, and would never open the second project's index at all."""
    built = make_two_project_corpus()
    reads = _record_read_text(monkeypatch)
    fake_cli = FakeClaudeCli(
        {_SLICE_ONE: _PROPOSAL_ONE, _SLICE_TWO: _PROPOSAL_TWO},
        classify=lambda prompt: (
            "report-directory" if "report-under-audit-results" in prompt else "cheap-tier-map"
        ),
    )
    monkeypatch.setattr(funnel.subprocess, "run", fake_cli)

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "transcripts_read: 2" in out
    assert "proposals: 2" in out
    assert "new_vs_update: 0/2" in out
    assert "dedup_errors: 0" in out

    _out_dir, records, discards = _published(built.audit_dir)
    assert discards == []
    by_name = {record["name"]: record for record in records}
    assert by_name["cheap-tier-is-haiku"]["kind"] == "update cheap-tier-map"
    assert by_name["cheap-tier-is-haiku"]["existing_text"] == _MEMORY_CHEAP_TIER_MAP
    assert by_name["report-under-audit-results"]["kind"] == "update report-directory"
    assert by_name["report-under-audit-results"]["existing_text"] == _MEMORY_REPORT_DIRECTORY
    assert reads.count(built.one.memory_dir / "MEMORY.md") == 1
    assert reads.count(built.two.memory_dir / "MEMORY.md") == 1
