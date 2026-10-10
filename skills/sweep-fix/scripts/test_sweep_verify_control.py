"""Tests for sweep.py: verify_control."""
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


def test_verify_control_raises_one_line_error_when_control_term_search_fails(
    tmp_path, monkeypatch
):
    # The control repo exists and scans cleanly (zero hits for the pattern),
    # but the fixed-string search for the control term itself blows up.
    # That must not be read as "control term absent".
    control_repo = tmp_path / "control"
    control_repo.mkdir()
    (control_repo / "file.txt").write_text("unrelated content\n")

    original_run_rg = sweep._run_rg

    def _fail_fixed_string_search(args, *rest, **kwargs):
        if "-F" in args:
            raise RuntimeError("rg failed: line one\nline two")
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
    assert "\n" not in message


