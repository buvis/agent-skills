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


def test_verify_control_warns_to_stderr_when_fallback_check_cannot_run(
    tmp_path, capsys
):
    # control_repo does not exist, so the `_run_rg` fallback call itself
    # cannot run. That must not be silently reported as "verified, no
    # issue" -- it must warn, naming the failure and the control repo.
    control_repo = tmp_path / "does-not-exist"

    result = sweep.verify_control(
        "NOTPRESENTPATTERN", "rg", control_repo, "NOTPRESENTTERM"
    )

    assert result is None
    message = capsys.readouterr().err
    assert str(control_repo) in message


