"""Run the skill's shipped --selftest scripts under pytest (fixtures are authored)."""

from pathlib import Path
import subprocess
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


@pytest.mark.parametrize("name", ['check_review.py', 'check_trust.py'])
def test_selftest_passes(name):
    result = subprocess.run(
        [sys.executable, "-B", str(SCRIPTS / name), "--selftest"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_check_trust_fails_loudly_without_document_skill(tmp_path):
    scripts = tmp_path / "skills" / "review-abap-solution-documentation" / "scripts"
    scripts.mkdir(parents=True)
    copy = scripts / "check_trust.py"
    copy.write_text((SCRIPTS / "check_trust.py").read_text(encoding="utf-8"), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "-B", str(copy), "--selftest"],
        capture_output=True, text=True, check=False,
        # USERPROFILE is what Path.home() reads on Windows.
        env={"HOME": str(tmp_path), "USERPROFILE": str(tmp_path), "PATH": ""},
    )
    assert result.returncode != 0
    assert "document-abap-solution" in result.stderr
