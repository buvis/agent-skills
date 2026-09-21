"""Regression tests for collect.py's per-repo collector.
Run: python3 -m pytest test_collect_repo.py -q"""

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import collect
from collect import collect_repo, stub_from_path
from collect_test_helpers import make_trash_dir


def _run_answering_gh(outcome):
    def fake_run(cmd, cwd=None, timeout=120):
        if cmd[0] == "git" and cmd[1] == "remote":
            return "git@github.com:acme/widget.git\n"
        if cmd[0] == "gh":
            if isinstance(outcome, Exception):
                raise outcome
            return outcome
        raise AssertionError(f"unexpected command: {cmd}")

    return fake_run


def test_stub_from_path_builds_owner_name_org_and_reason_from_path():
    result = stub_from_path("/repos/acme/widget", "not a github remote: bad-url")
    assert result == {
        "owner": "acme",
        "name": "widget",
        "org": "acme",
        "path": "/repos/acme/widget",
        "skipped": "not a github remote: bad-url",
    }


def test_collect_repo_returns_skip_stub_when_remote_unresolvable(monkeypatch):
    def fake_run(cmd, cwd=None, timeout=120):
        if cmd[0] == "git" and cmd[1] == "remote":
            raise RuntimeError("not a github remote: bad-url")
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(collect, "run", fake_run)
    result = collect_repo("/repos/acme/widget", 60, False)
    assert result == {
        "owner": "acme",
        "name": "widget",
        "org": "acme",
        "path": "/repos/acme/widget",
        "skipped": "not a github remote: bad-url",
    }


def test_collect_repo_records_fetch_timeout_without_raising(monkeypatch):
    fetch_cmd = ["git", "fetch", "--quiet", "origin"]
    timeout_exc = subprocess.TimeoutExpired(fetch_cmd, 180)

    def fake_run(cmd, cwd=None, timeout=120):
        if cmd[0] == "git" and cmd[1] == "remote":
            return "git@github.com:acme/widget.git\n"
        if cmd[0] == "git" and cmd[1] == "fetch":
            raise timeout_exc
        if cmd[0] == "gh":
            raise RuntimeError("gh: not authenticated")
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(collect, "run", fake_run)
    result = collect_repo("/repos/acme/widget", 60, True)
    assert result is not None
    assert "skipped" not in result
    assert f"fetch: {timeout_exc}" in result["errors"]


def test_collect_repo_returns_skip_stub_when_remote_get_url_times_out(monkeypatch):
    def fake_run(cmd, cwd=None, timeout=120):
        if cmd[0] == "git" and cmd[1] == "remote":
            raise subprocess.TimeoutExpired(cmd, timeout)
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(collect, "run", fake_run)
    result = collect_repo("/repos/acme/widget", 60, False)
    assert result["skipped"]
    assert result["owner"] == "acme"
    assert result["name"] == "widget"


def test_collect_repo_returns_skip_stub_when_git_binary_missing(monkeypatch):
    def fake_run(cmd, cwd=None, timeout=120):
        if cmd[0] == "git" and cmd[1] == "remote":
            raise FileNotFoundError("[Errno 2] No such file or directory: 'git'")
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(collect, "run", fake_run)
    result = collect_repo("/repos/acme/widget", 60, False)
    assert result["skipped"]
    assert result["owner"] == "acme"
    assert result["name"] == "widget"


def test_collect_repo_records_meta_os_error_without_raising(monkeypatch):
    os_exc = OSError("too many open files")

    monkeypatch.setattr(collect, "run", _run_answering_gh(os_exc))
    result = collect_repo("/repos/acme/widget", 60, False)
    assert result is not None
    assert "skipped" not in result
    assert any(str(os_exc) in e for e in result["errors"])


def test_collect_repo_records_meta_timeout_without_raising(monkeypatch):
    timeout_exc = subprocess.TimeoutExpired(["gh", "api", "repos/acme/widget"], 120)

    monkeypatch.setattr(collect, "run", _run_answering_gh(timeout_exc))
    result = collect_repo("/repos/acme/widget", 60, False)
    assert result is not None
    assert "skipped" not in result
    assert any(str(timeout_exc) in e for e in result["errors"])


def test_a_non_json_metadata_body_lands_in_errors_and_the_run_continues(monkeypatch):
    monkeypatch.setattr(collect, "run", _run_answering_gh("<html>502</html>"))
    result = collect_repo("/repos/acme/widget", 60, False)
    assert result is not None
    assert "skipped" not in result
    assert len(result["errors"]) == 1
    assert result["errors"][0].startswith("meta:")
    assert "Expecting value" in result["errors"][0]


def test_an_empty_metadata_body_lands_in_errors_and_the_run_continues(monkeypatch):
    monkeypatch.setattr(collect, "run", _run_answering_gh(""))
    result = collect_repo("/repos/acme/widget", 60, False)
    assert result is not None
    assert "skipped" not in result
    assert len(result["errors"]) == 1
    assert result["errors"][0].startswith("meta:")
    assert "NoneType" in result["errors"][0]


def test_collect_repo_records_meta_http_403_without_raising(monkeypatch):
    http_403_exc = RuntimeError("gh: HTTP 403: API rate limit exceeded")

    monkeypatch.setattr(collect, "run", _run_answering_gh(http_403_exc))
    result = collect_repo("/repos/acme/widget", 60, False)
    assert result is not None
    assert "skipped" not in result
    assert len(result["errors"]) == 1
    assert result["errors"][0].startswith("meta:")
    assert str(http_403_exc) in result["errors"][0]


def _run_answering_actions_runs(runs_exc):
    def fake_run(cmd, cwd=None, timeout=120):
        if cmd[0] == "git" and cmd[1] == "remote":
            return "git@github.com:demo/repo.git\n"
        if cmd[0] == "git":
            return ""
        if cmd[0] == "gh" and cmd[1] == "api":
            path = cmd[2]
            if "actions/runs" in path:
                raise runs_exc
            if path == "repos/demo/repo":
                return '{"default_branch": "master"}'
            return "[]"
        if cmd[0] == "gh" and cmd[1] == "pr":
            return "[]"
        raise AssertionError(f"unexpected command: {cmd}")

    return fake_run


def test_a_500_on_actions_runs_lands_in_errors_and_leaves_ci_absent(monkeypatch):
    runs_exc = RuntimeError(
        "gh: HTTP 500: Internal Server Error (https://api.github.com/repos/demo/repo/actions/runs)"
    )

    monkeypatch.setattr(collect, "run", _run_answering_actions_runs(runs_exc))
    result = collect_repo("/repos/demo/repo", 60, False)
    assert result is not None
    assert "skipped" not in result
    assert "ci" not in result
    assert len(result["errors"]) == 1
    assert result["errors"][0].startswith("ci:")


def test_a_403_on_actions_runs_still_reads_as_actions_disabled(monkeypatch):
    runs_exc = RuntimeError(
        "gh: HTTP 403: Forbidden (https://api.github.com/repos/demo/repo/actions/runs)"
    )

    monkeypatch.setattr(collect, "run", _run_answering_actions_runs(runs_exc))
    result = collect_repo("/repos/demo/repo", 60, False)
    assert result is not None
    assert "skipped" not in result
    assert result["ci"] == []
    assert not any(e.startswith("ci:") for e in result["errors"])


def test_collect_repo_purge_last_run_key_equals_collect_purge_devlocal_result(
    tmp_path,
    monkeypatch,
):
    make_trash_dir(tmp_path, dirs=["2026-08-20"])

    def fake_run(cmd, cwd=None, timeout=120):
        if cmd[0] == "git" and cmd[1] == "remote":
            return "git@github.com:acme/widget.git\n"
        return ""

    monkeypatch.setattr(collect, "run", fake_run)
    monkeypatch.setattr(collect, "gh_json", lambda path: {"default_branch": "master"})

    result = collect_repo(tmp_path, 60, False)

    assert result["purge_last_run"] == "2026-08-20"
