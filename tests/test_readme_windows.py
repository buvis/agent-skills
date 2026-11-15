"""README's Windows wording claims only what CI exercises (PRD 00044)."""

from pathlib import Path

README = (Path(__file__).resolve().parent.parent / "README.md").read_text(encoding="utf-8")


def test_windows_command_uses_one_backslash() -> None:
    assert "py bin\\braid.py" in README
    assert "py bin\\\\braid.py" not in README


def test_coverage_note_names_windows_ci_and_git_bash_split() -> None:
    assert "full Python suite on `windows-latest`" in README
    assert "need Git Bash; Braid itself" in README


def test_junction_fallback_is_claimed_stub_tested_only() -> None:
    assert "junction fallback is stub-tested only" in README
