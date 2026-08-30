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
    of them passes --distil."""
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
    assert len(judge_calls) == 1
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
