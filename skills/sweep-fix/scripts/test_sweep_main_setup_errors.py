"""Tests for sweep.py: main exit paths for setup failures."""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

import sweep
from sweep_test_helpers import (
    _build_sweep_main_scaffold,
    _make_repo,
    _plant_matches,
    _write_registry,
)


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
    tmp_path, monkeypatch, capsys, deny_access
):
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        pytest.skip("root can read a chmod 0o000 file")
    argv, registry, out_path = _setup_argv(tmp_path, monkeypatch)
    restore = deny_access(registry)

    try:
        exit_code = sweep.main(argv)
    finally:
        restore()

    assert exit_code == 1
    assert not out_path.exists()
    assert not out_path.parent.exists()
    err_lines = capsys.readouterr().err.strip().splitlines()
    assert len(err_lines) == 1
    assert str(registry) in err_lines[0]


# -- main: setup failures exit 1 with one stderr line and no report ---------


def _zero_hit_argv(tmp_path, monkeypatch, control_repo, control_term):
    """One registered repo with no pattern hits, so the whole sweep finds
    zero hits and main() must run the control check. The report would land
    in a not-yet-existing `reports/` directory inside the repo."""
    empty_portfolio_root = tmp_path / "empty_portfolio_root"
    empty_portfolio_root.mkdir()
    monkeypatch.setattr(sweep, "PORTFOLIO_ROOT", empty_portfolio_root)

    repo_a = _make_repo(tmp_path / "org" / "repo-a")
    (repo_a / "file.txt").write_text("nothing relevant here\n")

    registry = tmp_path / "repos.csv"
    _write_registry(registry, [str(repo_a)])

    out_path = repo_a / "reports" / "report.md"
    argv = [
        "--kind", "rg",
        "--pattern", "ZEROHITPATTERN",
        "--reason", "regression test for fail-loud setup",
        "--control-term", control_term,
        "--control-repo", str(control_repo),
        "--registry", str(registry),
        "--cwd", str(repo_a),
        "--out", str(out_path),
    ]
    return argv, out_path


@pytest.mark.parametrize("marker", ["ALPHACONTROL", "BETACONTROL"])
@pytest.mark.parametrize("control_matches", [False, True], ids=["unverified", "verified"])
def test_empty_sweep_saves_control_verification_status_and_scan_details(
    tmp_path, monkeypatch, capsys, marker, control_matches
):
    control_repo = tmp_path / "control"
    control_repo.mkdir()
    pattern = f"^{marker}$"
    content = f"prefix{marker}suffix\n{marker}suffix\nprefix{marker}\n{marker}Xliteral\n"
    (control_repo / "file.txt").write_text(content)
    argv, original_out = _zero_hit_argv(tmp_path, monkeypatch, control_repo, marker)
    argv[argv.index("--pattern") + 1] = pattern
    repo_a = original_out.parent.parent
    repo_b = _make_repo(tmp_path / "org" / "repo-b")
    (repo_b / "file.txt").write_text(content)
    missing_repo = tmp_path / "org" / "missing-repo"
    registry = Path(argv[argv.index("--registry") + 1])
    _write_registry(registry, [str(repo_a), str(repo_b), str(missing_repo)])
    # The fallback term is absent, despite near-matching regex source text.
    argv[argv.index("--control-term") + 1] = f"{marker}.literal"
    if control_matches:
        # LF explicitly: a CRLF line never matches an rg `$` anchor on Windows.
        (control_repo / "confirmed.txt").write_text(f"{marker}\n", newline="\n")
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    argv[argv.index("--out") + 1] = "reports/verification.md"
    out_path = repo_a / "reports" / "verification.md"

    exit_code = sweep.main(argv)

    assert out_path.is_file()
    report = out_path.read_text()
    assert "Hits (0):" in report
    assert pattern in report
    assert "regression test for fail-loud setup" in report
    assert "Gaps (1):" in report
    assert f"- {missing_repo}: not found on disk" in report
    marker_line = "Unverified: control term not found"
    assert (marker_line in report.splitlines()) is (not control_matches)
    assert exit_code == (0 if control_matches else 1)
    assert str(out_path) in capsys.readouterr().out
    assert not (elsewhere / "reports").exists()


@pytest.mark.parametrize(
    ("kind", "resolver_name", "tool_name"),
    [("rg", "resolve_rg", "rg"), ("astgrep", "resolve_ast_grep", "ast-grep")],
)
def test_an_unresolvable_scan_tool_exits_one_and_writes_no_report(
    tmp_path, monkeypatch, capsys, kind, resolver_name, tool_name
):
    argv, (repo_a, _repo_b, _repo_c), _scaffold_out_path = _build_sweep_main_scaffold(
        tmp_path, monkeypatch, "UNRESOLVABLETOOLMARKER", _make_repo
    )
    argv[argv.index("--kind") + 1] = kind
    out_path = repo_a / "reports" / "report.md"
    argv[argv.index("--out") + 1] = str(out_path)

    def _unresolvable():
        raise RuntimeError(f"Could not resolve {tool_name}: not found on PATH")

    monkeypatch.setattr(sweep, resolver_name, _unresolvable)
    scans = []
    monkeypatch.setattr(sweep, "scan", lambda *a, **k: scans.append(a) or ([], [], []))

    exit_code = sweep.main(argv)

    assert exit_code == 1
    assert scans == []
    assert not out_path.exists()
    assert not out_path.parent.exists()
    err_lines = capsys.readouterr().err.strip().splitlines()
    assert len(err_lines) == 1
    assert f"Could not resolve {tool_name}" in err_lines[0]
    assert "not found on PATH" in err_lines[0]


@pytest.mark.parametrize(
    ("kind", "unneeded_resolver_name"),
    [("rg", "resolve_ast_grep"), ("astgrep", "resolve_rg")],
)
def test_a_sweep_does_not_need_the_scan_tool_of_the_other_kind(
    tmp_path, monkeypatch, kind, unneeded_resolver_name
):
    argv, repos, out_path = _build_sweep_main_scaffold(
        tmp_path, monkeypatch, "OTHERTOOLMARKER", _make_repo
    )
    argv[argv.index("--kind") + 1] = kind
    for repo in repos:
        _plant_matches(repo, "OTHERTOOLMARKER", 1, ext=".py")

    def _unresolvable():
        raise RuntimeError("Could not resolve the other tool: not found on PATH")

    monkeypatch.setattr(sweep, unneeded_resolver_name, _unresolvable)

    exit_code = sweep.main(argv)

    assert exit_code == 0
    assert out_path.exists()
    assert "OTHERTOOLMARKER" in out_path.read_text()


def test_an_invalid_out_is_refused_before_the_scan_tool_is_resolved(
    tmp_path, monkeypatch, capsys
):
    argv, _repos, _out_path = _build_sweep_main_scaffold(
        tmp_path, monkeypatch, "OUTBEFORETOOLMARKER", _make_repo
    )
    outside_out = tmp_path / "outside" / "report.md"
    argv[argv.index("--out") + 1] = str(outside_out)

    resolver_calls = []

    def _unresolvable():
        resolver_calls.append(True)
        raise RuntimeError("Could not resolve rg: not found on PATH")

    monkeypatch.setattr(sweep, "resolve_rg", _unresolvable)

    with pytest.raises(SystemExit) as exc_info:
        sweep.main(argv)

    assert exc_info.value.code == 1
    assert resolver_calls == []
    assert not outside_out.parent.exists()
    message = capsys.readouterr().err
    assert str(outside_out) in message
    assert "Could not resolve" not in message


def test_a_failed_control_search_exits_one(tmp_path, monkeypatch, capsys):
    control_repo = tmp_path / "control"
    control_repo.mkdir()
    (control_repo / "file.txt").write_text("unrelated control content\n")
    argv, out_path = _zero_hit_argv(
        tmp_path, monkeypatch, control_repo, "FAILEDSEARCHTERM"
    )

    original_run_rg = sweep._run_rg

    def _fail_fixed_string_search(args, *rest, **kwargs):
        if "-F" in args:
            raise RuntimeError("rg failed: line one\nline two")
        return original_run_rg(args, *rest, **kwargs)

    monkeypatch.setattr(sweep, "_run_rg", _fail_fixed_string_search)

    exit_code = sweep.main(argv)

    assert exit_code == 1
    assert not out_path.exists()
    assert not out_path.parent.exists()
    err_lines = capsys.readouterr().err.strip().splitlines()
    assert len(err_lines) == 1
    assert "sweep unverified" in err_lines[0]
    assert str(control_repo) in err_lines[0]
    assert "line one line two" in err_lines[0]


def test_a_control_repo_whose_pattern_scan_fails_exits_one_with_one_stderr_line(
    tmp_path, monkeypatch, capsys
):
    # The control repo exists, but scanning it for the pattern blows up with
    # multi-line error text. That is a failed control check, not "no hits",
    # and the reason must reach stderr collapsed onto one line.
    control_repo = tmp_path / "control"
    control_repo.mkdir()
    (control_repo / "file.txt").write_text("unrelated control content\n")
    argv, out_path = _zero_hit_argv(
        tmp_path, monkeypatch, control_repo, "SCANFAILCONTROLTERM"
    )

    original_run_rg = sweep._run_rg

    def _fail_control_pattern_scan(args, cwd, *rest, **kwargs):
        if "-F" not in args and Path(cwd).resolve() == control_repo.resolve():
            raise RuntimeError("rg failed: a\nb")
        return original_run_rg(args, cwd, *rest, **kwargs)

    monkeypatch.setattr(sweep, "_run_rg", _fail_control_pattern_scan)

    exit_code = sweep.main(argv)

    assert exit_code == 1
    assert not out_path.exists()
    assert not out_path.parent.exists()
    err_lines = capsys.readouterr().err.strip().splitlines()
    assert len(err_lines) == 1
    assert "could not be scanned" in err_lines[0]
    assert str(control_repo) in err_lines[0]


def test_an_unscannable_control_repo_exits_one_and_writes_no_report(
    tmp_path, monkeypatch, capsys
):
    control_repo = tmp_path / "control-does-not-exist"
    argv, out_path = _zero_hit_argv(
        tmp_path, monkeypatch, control_repo, "MISSINGCONTROLTERM"
    )

    exit_code = sweep.main(argv)

    assert exit_code == 1
    assert not out_path.exists()
    assert not out_path.parent.exists()
    err_lines = capsys.readouterr().err.strip().splitlines()
    assert len(err_lines) == 1
    assert "could not be scanned" in err_lines[0]
    assert str(control_repo) in err_lines[0]


def test_a_missing_registry_exits_one_naming_the_path(
    tmp_path, monkeypatch, capsys
):
    argv, (repo_a, _repo_b, _repo_c), _scaffold_out_path = _build_sweep_main_scaffold(
        tmp_path, monkeypatch, "MISSINGREGISTRYMARKER", _make_repo
    )
    missing_registry = str(tmp_path / "no-such-repos.csv")
    argv[argv.index("--registry") + 1] = missing_registry
    out_path = repo_a / "reports" / "report.md"
    argv[argv.index("--out") + 1] = str(out_path)

    with pytest.raises(RuntimeError) as exc_info:
        sweep.enumerate_repos(missing_registry, repo_a)
    assert str(exc_info.value) == f"registry not found: {missing_registry}"

    exit_code = sweep.main(argv)

    assert exit_code == 1
    assert not out_path.exists()
    assert not out_path.parent.exists()
    assert capsys.readouterr().err.strip() == f"registry not found: {missing_registry}"
