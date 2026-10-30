"""Run the skill's shipped --selftest scripts under pytest (fixtures are authored)."""

from pathlib import Path
import subprocess
import sys

import pytest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


@pytest.mark.parametrize("name", ['check_run.py'])
def test_selftest_passes(name):
    result = subprocess.run(
        [sys.executable, "-B", str(SCRIPTS / name), "--selftest"],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
