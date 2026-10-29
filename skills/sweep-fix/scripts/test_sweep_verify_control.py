"""Tests for sweep.py: verify_control."""
import os
import signal
import subprocess
import time

import pytest

import sweep


# -- verify_control -------------------------------------------------------


def test_verify_control_returns_none_when_pattern_finds_hits_in_control_repo(tmp_path):
    control_repo = tmp_path / "control"
    control_repo.mkdir()
    (control_repo / "file.txt").write_text("CONTROLMARKER line\n")

    result = sweep.verify_control(
        "CONTROLMARKER", "rg", control_repo, "irrelevant-term"
    )

    assert result is None


def test_verify_control_returns_none_when_pattern_and_control_term_both_absent(
    tmp_path,
):
    control_repo = tmp_path / "control"
    control_repo.mkdir()
    (control_repo / "file.txt").write_text("unrelated content\n")

    result = sweep.verify_control(
        "NOTPRESENTPATTERN", "rg", control_repo, "NOTPRESENTTERM"
    )

    assert result is None


def test_verify_control_raises_unverified_when_pattern_misses_but_control_term_present(
    tmp_path, capsys
):
    control_repo = tmp_path / "control"
    control_repo.mkdir()
    (control_repo / "file.txt").write_text("CONTROLTERM appears here\n")

    with pytest.raises(SystemExit) as exc_info:
        sweep.verify_control("NOTPRESENTPATTERN", "rg", control_repo, "CONTROLTERM")

    assert exc_info.value.code == 1
    message = capsys.readouterr().err
    assert "unverified" in message
    assert "CONTROLTERM" in message
    assert str(control_repo) in message


def test_verify_control_raises_unverified_for_broken_backslash_pipe_alternation(
    tmp_path, capsys
):
    # The classic Rust-regex trap: `\|` is a literal pipe, not "OR", so this
    # pattern never matches "foo" alone even though the author meant
    # "foo OR bar".
    control_repo = tmp_path / "control"
    control_repo.mkdir()
    (control_repo / "file.txt").write_text("foo appears alone, no pipe here\n")

    with pytest.raises(SystemExit) as exc_info:
        sweep.verify_control("foo\\|bar", "rg", control_repo, "foo")

    assert exc_info.value.code == 1
    message = capsys.readouterr().err
    assert "unverified" in message
    assert "foo" in message
    assert str(control_repo) in message


def test_verify_control_raises_when_the_fallback_check_cannot_run(tmp_path):
    # control_repo does not exist, so the control scan cannot scan it. That
    # must not be silently reported as "verified, no issue" -- it must stop
    # the sweep, naming the failure and the control repo.
    control_repo = tmp_path / "does-not-exist"

    with pytest.raises(RuntimeError) as exc_info:
        sweep.verify_control(
            "NOTPRESENTPATTERN", "rg", control_repo, "NOTPRESENTTERM"
        )

    message = str(exc_info.value)
    assert "sweep unverified" in message
    assert "could not be scanned" in message
    assert str(control_repo) in message


def test_verify_control_raises_one_line_error_when_the_control_pattern_scan_fails(
    tmp_path, monkeypatch
):
    # The control repo exists, but scanning it for the pattern blows up with
    # multi-line error text. That must not read as "no hits"; the reason
    # must be collapsed onto one line.
    control_repo = tmp_path / "control"
    control_repo.mkdir()
    (control_repo / "file.txt").write_text("unrelated content\n")

    original_run_rg = sweep._run_rg

    def _fail_pattern_scan(args, *rest, **kwargs):
        if "-F" not in args:
            raise RuntimeError("rg failed: a\nb")
        return original_run_rg(args, *rest, **kwargs)

    monkeypatch.setattr(sweep, "_run_rg", _fail_pattern_scan)

    with pytest.raises(RuntimeError) as exc_info:
        sweep.verify_control(
            "NOTPRESENTPATTERN", "rg", control_repo, "NOTPRESENTTERM"
        )

    message = str(exc_info.value)
    assert "sweep unverified" in message
    assert "could not be scanned" in message
    assert str(control_repo) in message
    assert "\n" not in message


@pytest.mark.parametrize(
    ("search_error", "collapsed_reason"),
    [
        (RuntimeError("rg failed: line one\nline two"), "line one line two"),
        (subprocess.TimeoutExpired(["rg"], 30), "timed out after 30 seconds"),
        (OSError("boom"), "boom"),
    ],
    ids=["runtime-error", "timeout", "os-error"],
)
def test_verify_control_raises_one_line_error_when_control_term_search_fails(
    tmp_path, monkeypatch, search_error, collapsed_reason
):
    # The control repo exists and scans cleanly (zero hits for the pattern),
    # but the fixed-string search for the control term itself blows up.
    # That must not be read as "control term absent", whatever it raised.
    control_repo = tmp_path / "control"
    control_repo.mkdir()
    (control_repo / "file.txt").write_text("unrelated content\n")

    original_run_rg = sweep._run_rg

    def _fail_fixed_string_search(args, *rest, **kwargs):
        if "-F" in args:
            raise search_error
        return original_run_rg(args, *rest, **kwargs)

    monkeypatch.setattr(sweep, "_run_rg", _fail_fixed_string_search)

    with pytest.raises(RuntimeError) as exc_info:
        sweep.verify_control(
            "NOTPRESENTPATTERN", "rg", control_repo, "SEARCHFAILTERM"
        )

    message = str(exc_info.value)
    assert "sweep unverified" in message
    assert "could not search control term" in message
    assert "SEARCHFAILTERM" in message
    assert str(control_repo) in message
    assert collapsed_reason in message
    assert "\n" not in message


# -- verify_control: one deadline budget for both checks ---------------------


def _clean_control_repo(tmp_path, content="unrelated content\n"):
    control_repo = tmp_path / "control"
    control_repo.mkdir()
    (control_repo / "file.txt").write_text(content)
    return control_repo


_POSIX_RG_SHIM = pytest.mark.skipif(
    os.name == "nt", reason="the slow rg shim is a POSIX sh script"
)


@pytest.fixture
def shim_pid_file(tmp_path):
    # Kills the rg shim if a failing test left it running.
    pid_file = tmp_path / "shim.pid"
    yield pid_file
    if pid_file.exists() and pid_file.read_text().strip():
        try:
            os.kill(int(pid_file.read_text()), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            pass


def _slow_scan_then_rg_shim(tmp_path, monkeypatch, pid_file, shim_tail):
    """Inject a control scan that burns 2s and comes back clean, so the
    control-term search runs next against a real `rg` shim on PATH that
    records its pid and then runs shim_tail. Returns the list each scan
    call appends its `deadline` keyword to."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    shim = bin_dir / "rg"
    shim.write_text(f'#!/bin/sh\necho $$ > "{pid_file}"\n{shim_tail}\n')
    shim.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    scan_deadlines = []

    def slow_clean_scan(*args, **kwargs):
        scan_deadlines.append(kwargs.get("deadline"))
        time.sleep(2.0)
        return [], {}, {}

    monkeypatch.setattr(sweep, "scan", slow_clean_scan)
    return scan_deadlines


@_POSIX_RG_SHIM
def test_verify_control_bounds_the_control_term_search_by_what_the_scan_left_of_the_deadline(
    tmp_path, monkeypatch, shim_pid_file
):
    # The scan burns 2s of a 3s budget; the shim sleeps 10s. The term search
    # may only use the ~1s left: a fresh 3s window would end near 5s, the
    # default per-call timeout far later.
    scan_deadlines = _slow_scan_then_rg_shim(
        tmp_path, monkeypatch, shim_pid_file, "exec sleep 10"
    )
    control_repo = _clean_control_repo(tmp_path)

    started = time.monotonic()
    with pytest.raises(TimeoutError):
        sweep.verify_control(
            "NOTPRESENTPATTERN", "rg", control_repo, "BUDGETTERM", deadline=3
        )
    elapsed = time.monotonic() - started

    # The scan gets the whole original budget, not a pre-shrunk share.
    assert scan_deadlines == [pytest.approx(3, abs=0.1)]
    assert shim_pid_file.exists()  # the term search really ran
    assert elapsed >= 2.8  # ...and was given the remaining ~1s, not cut at once
    assert elapsed < 4.0  # 3s shared budget + 1s cleanup tolerance


@_POSIX_RG_SHIM
def test_verify_control_lets_the_control_term_search_use_all_the_budget_the_scan_left(
    tmp_path, monkeypatch, shim_pid_file
):
    # The scan burns 2s of a 6s budget; the shim needs 2.5s, then reports
    # "no matches". It fits in the 4s left, so a term search held to any
    # fixed window shorter than that would be cut off and misreported.
    scan_deadlines = _slow_scan_then_rg_shim(
        tmp_path, monkeypatch, shim_pid_file, "sleep 2.5\nexit 1"
    )
    control_repo = _clean_control_repo(tmp_path)

    result = sweep.verify_control(
        "NOTPRESENTPATTERN", "rg", control_repo, "SPARETERM", deadline=6
    )

    assert result is None
    assert scan_deadlines == [pytest.approx(6, abs=0.1)]
    assert shim_pid_file.exists()


@pytest.mark.parametrize(
    ("scan_reason", "expected_error"),
    [
        (sweep.DEADLINE_REASON, TimeoutError),
        ("sweep deadline", RuntimeError),  # prefix of DEADLINE_REASON, not equal
        ("permission denied", RuntimeError),
    ],
    ids=["deadline-expired", "deadline-prefix-near-miss", "other-failure"],
)
def test_verify_control_raises_timeout_only_when_its_scan_ran_out_of_deadline(
    tmp_path, monkeypatch, scan_reason, expected_error
):
    control_repo = _clean_control_repo(tmp_path)
    monkeypatch.setattr(
        sweep,
        "scan",
        lambda *a, **k: ([], {}, {str(control_repo): scan_reason}),
    )
    searches = []
    monkeypatch.setattr(
        sweep,
        "_run_rg",
        lambda *a, **k: searches.append(a) or subprocess.CompletedProcess([], 1, "", ""),
    )

    with pytest.raises((TimeoutError, RuntimeError)) as exc_info:
        sweep.verify_control(
            "NOTPRESENTPATTERN", "rg", control_repo, "TIMEOUTTERM", deadline=5
        )

    assert exc_info.type is expected_error
    assert searches == []  # a failed control scan never falls through to the term search
    message = str(exc_info.value)
    if expected_error is TimeoutError:
        assert message.startswith("sweep unverified: ")
        assert str(control_repo) in message
        assert "deadline expired" in message
    else:
        assert "could not be scanned" in message
        assert str(control_repo) in message
        assert scan_reason in message


@pytest.mark.parametrize(
    ("content", "pattern", "control_term"),
    [
        ("AMPLEMARKER line\n", "AMPLEMARKER", "irrelevant-term"),
        ("unrelated content\n", "AMPLEABSENTPATTERN", "AMPLEABSENTTERM"),
    ],
    ids=["pattern-confirmed", "both-absent"],
)
def test_verify_control_with_ample_deadline_returns_none_as_without_one(
    tmp_path, content, pattern, control_term
):
    control_repo = _clean_control_repo(tmp_path, content)

    result = sweep.verify_control(pattern, "rg", control_repo, control_term, deadline=60)

    assert result is None


def test_verify_control_with_ample_deadline_still_exits_one_for_a_broken_pattern(
    tmp_path, capsys
):
    control_repo = _clean_control_repo(tmp_path, "AMPLETERM appears here\n")

    with pytest.raises(SystemExit) as exc_info:
        sweep.verify_control(
            "AMPLEBROKENPATTERN", "rg", control_repo, "AMPLETERM", deadline=60
        )

    assert exc_info.value.code == 1
    message = capsys.readouterr().err
    assert "unverified" in message
    assert "AMPLETERM" in message


def test_verify_control_with_ample_deadline_still_raises_runtime_error_for_a_missing_repo(
    tmp_path,
):
    control_repo = tmp_path / "does-not-exist"

    with pytest.raises(RuntimeError) as exc_info:
        sweep.verify_control(
            "NOTPRESENTPATTERN", "rg", control_repo, "NOTPRESENTTERM", deadline=60
        )

    assert exc_info.type is RuntimeError
    assert "could not be scanned" in str(exc_info.value)
    assert str(control_repo) in str(exc_info.value)


