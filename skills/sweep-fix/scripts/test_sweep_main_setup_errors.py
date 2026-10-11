"""Tests for sweep.py: main exit paths for setup failures."""
import os
import shutil
import subprocess

import pytest

import sweep
from sweep_test_helpers import _make_repo, _write_registry


def _setup_argv(tmp_path, monkeypatch, kind="rg"):
    empty_portfolio_root = tmp_path / "empty_portfolio_root"
    empty_portfolio_root.mkdir()
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", empty_portfolio_root)

    repo_a = _make_repo(tmp_path / "org" / "repo-a")
    (repo_a / "file.txt").write_text("SETUPERRMARKER line\n")
    control_repo = tmp_path / "control"
    control_repo.mkdir()
    (control_repo / "file.txt").write_text("SETUPERRMARKER control line\n")
    registry = tmp_path / "repos.csv"
    _write_registry(registry, [str(repo_a)])
    out_path = repo_a / "reports" / "report.md"
    argv = [
        "--kind", kind,
        "--pattern", "SETUPERRMARKER",
        "--reason", "regression test for setup errors",
        "--control-term", "SETUPERRMARKER",
        "--control-repo", str(control_repo),
        "--registry", str(registry),
        "--cwd", str(repo_a),
        "--out", str(out_path),
    ]
    return argv, registry, out_path


def test_a_timed_out_mise_which_exits_one_naming_ast_grep_and_writes_no_report(
    tmp_path, monkeypatch, capsys
):
    argv, _registry, out_path = _setup_argv(tmp_path, monkeypatch, kind="astgrep")
    monkeypatch.setattr(
        shutil, "which", lambda name, *a, **k: "/fake/mise" if name == "mise" else None
    )

    def _time_out(*args, **kwargs):
        raise subprocess.TimeoutExpired(cmd=["mise", "which", "ast-grep"], timeout=10)

    monkeypatch.setattr(subprocess, "run", _time_out)

    exit_code = sweep.main(argv)

    assert exit_code == 1
    assert not out_path.exists()
    assert not out_path.parent.exists()
    err_lines = capsys.readouterr().err.strip().splitlines()
    assert len(err_lines) == 1
    assert "ast-grep" in err_lines[0]


def test_an_unreadable_registry_exits_one_naming_the_path_and_writes_no_report(
    tmp_path, monkeypatch, capsys
):
    if os.geteuid() == 0:
        pytest.skip("root can read a chmod 0o000 file")
    argv, registry, out_path = _setup_argv(tmp_path, monkeypatch)
    registry.chmod(0o000)

    try:
        exit_code = sweep.main(argv)
    finally:
        registry.chmod(0o600)

    assert exit_code == 1
    assert not out_path.exists()
    assert not out_path.parent.exists()
    err_lines = capsys.readouterr().err.strip().splitlines()
    assert len(err_lines) == 1
    assert str(registry) in err_lines[0]
