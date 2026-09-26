"""Regression tests for collect.py's per-repo collector.
Run: python3 -m pytest test_collect_repo.py -q"""

import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import collect
from collect import collect_repo, stub_from_path
from collect_test_helpers import make_trash_dir, write_report


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
        if cmd[0] == "git" and cmd[1] == "rev-list":
            return "0\n"
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


def test_a_404_on_actions_runs_still_reads_as_actions_disabled(monkeypatch):
    runs_exc = RuntimeError(
        "gh: HTTP 404: Not Found (https://api.github.com/repos/demo/repo/actions/runs)"
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


def test_a_failed_metadata_call_still_collects_the_local_hygiene_stamps(
    tmp_path,
    monkeypatch,
):
    write_report(tmp_path, "- generated: 2026-08-15\n")
    make_trash_dir(tmp_path, dirs=["2026-08-20"])

    def fake_run(cmd, cwd=None, timeout=120):
        if cmd[0] == "git" and cmd[1] == "remote":
            return "git@github.com:acme/widget.git\n"
        raise AssertionError(f"unexpected command: {cmd}")

    def fake_gh_json(path):
        raise RuntimeError("gh: HTTP 500")

    monkeypatch.setattr(collect, "run", fake_run)
    monkeypatch.setattr(collect, "gh_json", fake_gh_json)

    result = collect_repo(tmp_path, 60, False)

    assert result["brush_last_run"] == "2026-08-15"
    assert result["purge_last_run"] == "2026-08-20"
    assert result["prds"] == {"backlog": [], "wip": [], "done_count": 0}
    assert result["changelog_unreleased"] is None
    assert len(result["errors"]) == 1
    assert result["errors"][0] == "meta: gh: HTTP 500"
    assert "branches" not in result
    assert "local" not in result


def test_collect_repo_resolves_the_current_branch_once(monkeypatch):
    calls = []

    def fake_run(cmd, cwd=None, timeout=120):
        calls.append(cmd)
        if cmd[0] == "git" and cmd[1] == "remote":
            return "git@github.com:acme/widget.git\n"
        return ""

    monkeypatch.setattr(collect, "run", fake_run)
    monkeypatch.setattr(collect, "gh_json", lambda path: {"default_branch": "master"})

    collect_repo("/repos/acme/widget", 60, False)

    rev_parse_calls = [
        c for c in calls if c == ["git", "rev-parse", "--abbrev-ref", "HEAD"]
    ]
    assert len(rev_parse_calls) == 1


def test_a_failed_current_branch_lookup_skips_branches_and_local_without_raising(
    monkeypatch,
):
    rev_parse_exc = RuntimeError("git: fatal error")

    def fake_run(cmd, cwd=None, timeout=120):
        if cmd[0] == "git" and cmd[1] == "remote":
            return "git@github.com:acme/widget.git\n"
        if cmd[0] == "git" and cmd[1] == "rev-parse":
            raise rev_parse_exc
        return ""

    monkeypatch.setattr(collect, "run", fake_run)
    monkeypatch.setattr(collect, "gh_json", lambda path: {"default_branch": "master"})

    result = collect_repo("/repos/acme/widget", 60, False)

    assert result is not None
    assert "prds" in result
    assert "branches" not in result
    assert "local" not in result
    assert any(e.startswith("branches:") for e in result["errors"])
    assert any(e.startswith("local:") for e in result["errors"])


@pytest.mark.parametrize(
    "remote_url, expected",
    [
        pytest.param("git@github.com:demo/repo.git", ("demo", "repo"), id="ssh"),
        pytest.param("https://github.com/demo/repo", ("demo", "repo"), id="https"),
        pytest.param(
            "https://github.com/demo/repo.git/",
            ("demo", "repo"),
            id="https-dotgit-trailing-slash",
        ),
        pytest.param(
            "https://github.com/demo/my.repo-2",
            ("demo", "my.repo-2"),
            id="dots-and-dashes-in-name",
        ),
        pytest.param(
            "git@github.com:demo/repo?x=1.git",
            None,
            id="query-string-not-in-charset",
        ),
        pytest.param(
            "git@github.com:demo/repo/../other.git",
            None,
            id="extra-slash-in-name-segment",
        ),
        pytest.param(
            "git@github.com:../other.git",
            None,
            id="owner-is-dotdot",
        ),
        pytest.param(
            "git@github.com:demo/...git",
            None,
            id="name-is-dotdot",
        ),
    ],
)
def test_remote_re_accepts_github_slugs_and_rejects_query_and_dotdot(
    monkeypatch, remote_url, expected
):
    def fake_run(cmd, cwd=None, timeout=120):
        if cmd[0] == "git" and cmd[1] == "remote":
            return remote_url + "\n"
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(collect, "run", fake_run)

    if expected is None:
        with pytest.raises(RuntimeError):
            collect.repo_slug("/repos/demo/repo")
    else:
        assert collect.repo_slug("/repos/demo/repo") == expected


def test_an_unparseable_remote_is_skipped_before_any_gh_call(monkeypatch):
    calls = []

    def fake_run(cmd, cwd=None, timeout=120):
        calls.append(cmd)
        if cmd[0] == "git" and cmd[1] == "remote":
            return "git@github.com:demo/repo?x=1.git\n"
        if cmd[0] == "gh":
            raise AssertionError(f"unexpected gh call: {cmd}")
        raise AssertionError(f"unexpected command: {cmd}")

    monkeypatch.setattr(collect, "run", fake_run)
    result = collect_repo("/repos/demo/repo", 60, False)

    assert result["skipped"]
    assert not any(cmd[0] == "gh" for cmd in calls)
