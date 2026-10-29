"""Tests for sweep.py: main as a real CLI process, deadline-bounded."""
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

import sweep
from sweep_test_helpers import (
    _is_running,
    _make_repo,
    _recorded_pids,
    _still_running_after,
    _write_registry,
    _write_tree_shim,
)

_POSIX_SHIM = pytest.mark.skipif(
    os.name == "nt",
    reason="the search shim is a POSIX sh script that forks a grandchild",
)
_SCRIPTS_DIR = Path(sweep.__file__).resolve().parent
# The child points PORTFOLIO_ROOT at an empty directory, as the in-process
# tests above do with monkeypatch, then runs main() and exits with its code.
_CLI_CHILD = (
    "import sys\n"
    "from pathlib import Path\n"
    "import sweep\n"
    "sweep.PORTFOLIO_ROOT = Path(sys.argv[1])\n"
    "sys.exit(sweep.main(sys.argv[2:]))\n"
)


def _rg_hit_line(marker):
    match = {
        "type": "match",
        "data": {
            "path": {"text": "match.txt"},
            "line_number": 1,
            "lines": {"text": f"{marker}\n"},
        },
    }
    return json.dumps(match) + "\n"


def _run_cli(tmp_path, argv, bin_dir=None):
    """Run main() in a child interpreter. Returns (exit code, seconds until
    the child process itself exited, stdout, stderr). Output goes to files,
    not pipes, so a leaked grandchild holding a pipe cannot stretch the
    measured time; a child still alive after 30s is killed with its group."""
    portfolio = tmp_path / "empty_portfolio_root"
    portfolio.mkdir(exist_ok=True)
    logs = tmp_path / "cli-logs"
    logs.mkdir()
    env = dict(os.environ)
    env["PYTHONPATH"] = os.pathsep.join(
        part for part in (str(_SCRIPTS_DIR), env.get("PYTHONPATH")) if part
    )
    if bin_dir is not None:
        env["PATH"] = f"{bin_dir}{os.pathsep}{env['PATH']}"
    with open(logs / "out", "w") as out, open(logs / "err", "w") as err:
        started = time.monotonic()
        proc = subprocess.Popen(
            [sys.executable, "-c", _CLI_CHILD, str(portfolio), *argv],
            stdout=out, stderr=err, env=env, start_new_session=os.name != "nt",
        )
        try:
            code = proc.wait(timeout=30)
            elapsed = time.monotonic() - started
        finally:
            if proc.poll() is None:
                if os.name != "nt":
                    os.killpg(proc.pid, signal.SIGKILL)
                proc.kill()
                proc.wait()
    return code, elapsed, (logs / "out").read_text(), (logs / "err").read_text()


def _cli_argv(registry, cwd_repo, control_repo, pattern, control_term, out_path, deadline):
    return [
        "--kind", "rg",
        "--pattern", pattern,
        "--reason", f"regression test for {pattern}",
        "--control-term", control_term,
        "--control-repo", str(control_repo),
        "--registry", str(registry),
        "--cwd", str(cwd_repo),
        "--out", str(out_path),
        "--deadline", str(deadline),
    ]


def _registered_repos(tmp_path, names):
    repos = [_make_repo(tmp_path / "org" / name) for name in names]
    registry = tmp_path / "repos.csv"
    _write_registry(registry, [str(repo) for repo in repos])
    return registry, repos


@_POSIX_SHIM
def test_cli_exits_within_cleanup_tolerance_of_the_deadline_and_reports_finished_hits(
    tmp_path, shim_pid_dir
):
    registry, (repo_fast, repo_slow_a, repo_slow_b) = _registered_repos(
        tmp_path, ["repo-fast", "repo-slow-a", "repo-slow-b"]
    )
    control_repo = tmp_path / "control"
    control_repo.mkdir()
    (control_repo / "file.txt").write_text("CLIDEADLINEMARKER control line\n")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_tree_shim(bin_dir, shim_pid_dir, "repo-fast", _rg_hit_line("CLIDEADLINEMARKER"))
    out_path = repo_fast / "report.md"
    argv = _cli_argv(
        registry, repo_fast, control_repo,
        "CLIDEADLINEMARKER", "CLIDEADLINEMARKER", out_path, deadline=3,
    )

    code, elapsed, _out, err = _run_cli(tmp_path, argv, bin_dir)
    spawned = _recorded_pids(shim_pid_dir, "shim") + _recorded_pids(shim_pid_dir, "grandchild")

    assert elapsed < 5, err  # 3s deadline + 2s cleanup; the shim sleeps 10s
    assert code == 0, err
    report = out_path.read_text()
    assert "Hits (1):" in report
    assert len(re.findall(r"^- .+:\d+: .*CLIDEADLINEMARKER.*$", report, re.MULTILINE)) == 1
    assert "Failed:" in report
    assert str(repo_slow_a) in report
    assert str(repo_slow_b) in report
    assert _recorded_pids(shim_pid_dir, "grandchild")  # slow searches really ran
    assert _still_running_after(spawned, grace=1.0) == []
    assert list(shim_pid_dir.glob("finished-*")) == []


@_POSIX_SHIM
def test_cli_exits_one_unverified_with_no_report_when_the_deadline_leaves_no_budget_for_control(
    tmp_path, shim_pid_dir
):
    # Every search hangs, so the sweep finds zero hits and spends the whole
    # budget. The control repo holds the pattern and not the control term,
    # so a control check that did run would confirm the sweep (exit 0) and
    # the broken-pattern refusal cannot fire: exit 1 can only be the
    # deadline leaving the check unverified.
    registry, (repo_a, _repo_b) = _registered_repos(tmp_path, ["repo-a", "repo-b"])
    control_repo = tmp_path / "control"
    control_repo.mkdir()
    (control_repo / "file.txt").write_text("NOBUDGETPATTERN control line\n")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_tree_shim(bin_dir, shim_pid_dir)
    out_path = repo_a / "reports" / "report.md"
    argv = _cli_argv(
        registry, repo_a, control_repo,
        "NOBUDGETPATTERN", "NOBUDGETTERM", out_path, deadline=3,
    )

    code, elapsed, _out, err = _run_cli(tmp_path, argv, bin_dir)
    spawned = _recorded_pids(shim_pid_dir, "shim") + _recorded_pids(shim_pid_dir, "grandchild")

    # Under 1s past the deadline: a control check handed a fresh budget of
    # its own (even 1s) after the sweep spent the shared one ends later.
    assert elapsed < 4, err
    assert code == 1, err
    unverified = [line for line in err.splitlines() if line.startswith("sweep unverified: ")]
    assert len(unverified) == 1, err
    assert str(control_repo) in unverified[0]
    assert "deadline expired" in unverified[0]
    assert not out_path.exists()
    assert not out_path.parent.exists()
    assert spawned
    assert _still_running_after(spawned, grace=1.0) == []


@pytest.mark.parametrize(
    ("control_content", "expected_code"),
    [
        ("AMPLECLIPATTERN control line\n", 0),
        ("AMPLECLITERM only, no pattern text here\n", 1),
    ],
    ids=["confirmed-clean", "broken-pattern"],
)
def test_cli_zero_hit_sweep_with_ample_deadline_verifies_control_as_before(
    tmp_path, control_content, expected_code
):
    try:
        sweep.resolve_rg()
    except RuntimeError:
        pytest.skip("rg is not available in this environment")
    registry, (repo_a,) = _registered_repos(tmp_path, ["repo-a"])
    (repo_a / "file.txt").write_text("nothing relevant here\n")
    control_repo = tmp_path / "control"
    control_repo.mkdir()
    (control_repo / "file.txt").write_text(control_content)
    out_path = repo_a / "reports" / "report.md"
    argv = _cli_argv(
        registry, repo_a, control_repo,
        "AMPLECLIPATTERN", "AMPLECLITERM", out_path, deadline=60,
    )

    code, _elapsed, _out, err = _run_cli(tmp_path, argv)

    assert code == expected_code, err
    if expected_code == 0:
        assert "Hits (0):" in out_path.read_text()
    else:
        assert not out_path.exists()
        assert not out_path.parent.exists()
        assert "unverified" in err
        assert "AMPLECLITERM" in err
