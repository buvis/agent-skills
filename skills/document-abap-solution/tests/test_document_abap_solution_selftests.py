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


def test_check_run_extracts_identifiers_with_the_shared_helper(monkeypatch):
    # PRD 00175: one home for the identifier regexes. A local redefinition in
    # check_run.py would shadow the import and drift from check_trust.py.
    monkeypatch.syspath_prepend(str(SCRIPTS))
    import abap_idents
    import check_run

    assert check_run.custom_idents is abap_idents.custom_idents
    assert not hasattr(check_run, "_ident_pattern")
