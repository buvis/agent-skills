"""Regression tests for collect.py's main() pipeline: the registry partition,
recovery from an unusable data.json, and the audit-cadence call site. Also
hosts the agoge 2026-09-05 strict xfail for a missing registry (main()) and
the true commit count behind a capped commit list (collect_commit_count,
collect_repo, and the history row).
Run: python3 -m pytest test_collect_pipeline.py -q"""

import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import collect
from collect import MACHINE_AUDIT_SKILLS, collect_repo, history_counts, main
from collect_test_helpers import make_git_repo, run_collector, write_data_json_fixture


def test_main_partition_invariant_covers_every_registry_path(tmp_path, monkeypatch):
    paths, out_dir = run_collector(tmp_path, monkeypatch, ["alpha", "beta"], ["broken"])
    data = json.loads((out_dir / "data.json").read_text())
    assert len(paths) == len(data["repos"]) + len(data["skipped"])
    assert len(data["skipped"]) == 1
    assert data["skipped"][0]["skipped"]


def test_main_history_entry_counts_skipped_repos(tmp_path, monkeypatch):
    _, out_dir = run_collector(tmp_path, monkeypatch, ["alpha", "beta"], ["broken"])
    lines = (out_dir / "history.jsonl").read_text().strip().splitlines()
    last = json.loads(lines[-1])
    assert last["skipped"] == 1


def test_main_history_row_marks_the_repo_whose_metadata_call_failed(tmp_path, monkeypatch):
    _, out_dir = run_collector(tmp_path, monkeypatch, ["alpha"], [])
    lines = (out_dir / "history.jsonl").read_text().strip().splitlines()
    last = json.loads(lines[-1])
    assert last["repos"]["acme/alpha"]["e"] == 1


def test_main_summary_line_reports_paths_and_skipped_counts(
    tmp_path,
    monkeypatch,
    capsys,
):
    paths, _ = run_collector(tmp_path, monkeypatch, ["alpha", "beta"], ["broken"])
    captured = capsys.readouterr()
    assert f"{len(paths)} repos, 1 skipped" in captured.out


def test_main_external_section_reports_error_when_gh_unauthenticated(
    tmp_path,
    monkeypatch,
):
    _, out_dir = run_collector(tmp_path, monkeypatch, ["alpha"], [])
    data = json.loads((out_dir / "data.json").read_text())
    assert data["external"]["review_requested"] == []
    assert data["external"]["authored"] == []
    assert data["external"]["error"]


def test_main_includes_skipped_repos_in_known_set_for_external_classification(
    tmp_path,
    monkeypatch,
):
    captured = {}

    def fake_collect_external(known):
        captured["known"] = known
        return {"review_requested": [], "authored": []}

    monkeypatch.setattr(collect, "collect_external", fake_collect_external)
    _, out_dir = run_collector(tmp_path, monkeypatch, ["alpha"], ["broken"])

    data = json.loads((out_dir / "data.json").read_text())
    skip_stub = data["skipped"][0]
    expected_slug = f'{skip_stub["owner"]}/{skip_stub["name"]}'
    assert expected_slug in captured["known"]


def test_main_completes_when_existing_data_json_is_invalid_json(tmp_path, monkeypatch):
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True)
    (out_dir / "data.json").write_text("{not valid json")

    run_collector(tmp_path, monkeypatch, ["alpha"], [])

    new_data = json.loads((out_dir / "data.json").read_text())
    assert "generated_at" in new_data
    assert len(new_data["repos"]) == 1
    assert not (out_dir / "data-prev.json").exists()


def test_main_completes_when_existing_data_json_lacks_generated_at(tmp_path, monkeypatch):
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True)
    (out_dir / "data.json").write_text(json.dumps({"marker": "legacy-snapshot"}))

    run_collector(tmp_path, monkeypatch, ["alpha"], [])

    new_data = json.loads((out_dir / "data.json").read_text())
    assert "generated_at" in new_data
    assert len(new_data["repos"]) == 1
    assert not (out_dir / "data-prev.json").exists()


def test_main_completes_when_existing_data_json_has_unparseable_generated_at(
    tmp_path,
    monkeypatch,
):
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True)
    (out_dir / "data.json").write_text(json.dumps({"generated_at": "not-a-date"}))

    run_collector(tmp_path, monkeypatch, ["alpha"], [])

    new_data = json.loads((out_dir / "data.json").read_text())
    assert "generated_at" in new_data
    assert len(new_data["repos"]) == 1
    assert not (out_dir / "data-prev.json").exists()


def test_main_completes_when_existing_data_json_is_unreadable(tmp_path, monkeypatch):
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True)
    write_data_json_fixture(out_dir / "data.json", "2026-08-01T00:00:00+00:00", "unreadable")

    original_read_text = Path.read_text
    data_json_path = str(out_dir / "data.json")

    def failing_read_text(self, *args, **kwargs):
        if str(self) == data_json_path:
            raise OSError("permission denied")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", failing_read_text)

    run_collector(tmp_path, monkeypatch, ["alpha"], [])

    monkeypatch.setattr(Path, "read_text", original_read_text)
    new_data = json.loads((out_dir / "data.json").read_text())
    assert "generated_at" in new_data
    assert len(new_data["repos"]) == 1
    assert not (out_dir / "data-prev.json").exists()


def test_main_warns_on_stderr_naming_baseline_when_existing_data_json_is_unusable(
    tmp_path,
    monkeypatch,
    capsys,
):
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True)
    (out_dir / "data.json").write_text("{not valid json")

    run_collector(tmp_path, monkeypatch, ["alpha"], [])

    captured = capsys.readouterr()
    warn_lines = [line for line in captured.err.splitlines() if "WARN" in line]
    assert any("data.json" in line for line in warn_lines)


def test_main_completes_when_existing_generated_at_is_json_null(
    tmp_path,
    monkeypatch,
    capsys,
):
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True)
    write_data_json_fixture(out_dir / "data.json", None, "null-generated-at")

    run_collector(tmp_path, monkeypatch, ["alpha"], [])

    captured = capsys.readouterr()
    warn_lines = [line for line in captured.err.splitlines() if "WARN" in line]
    assert any("data.json" in line for line in warn_lines)
    new_data = json.loads((out_dir / "data.json").read_text())
    assert "generated_at" in new_data
    assert new_data["generated_at"] is not None
    assert len(new_data["repos"]) == 1
    assert not (out_dir / "data-prev.json").exists()


def test_main_completes_when_existing_generated_at_is_timezone_naive(
    tmp_path,
    monkeypatch,
    capsys,
):
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True)
    write_data_json_fixture(out_dir / "data.json", "2026-08-01T00:00:00", "naive-generated-at")

    run_collector(tmp_path, monkeypatch, ["alpha"], [])

    captured = capsys.readouterr()
    warn_lines = [line for line in captured.err.splitlines() if "WARN" in line]
    assert any("data.json" in line for line in warn_lines)
    new_data = json.loads((out_dir / "data.json").read_text())
    assert "generated_at" in new_data
    assert new_data["generated_at"] != "2026-08-01T00:00:00"
    assert len(new_data["repos"]) == 1
    assert not (out_dir / "data-prev.json").exists()


def test_main_external_carries_audit_cadence_and_drops_claude_maintenance_last(
    tmp_path,
    monkeypatch,
):
    _, out_dir = run_collector(tmp_path, monkeypatch, ["alpha"], [])
    data = json.loads((out_dir / "data.json").read_text())
    external = data["external"]
    assert "audit_cadence" in external
    for skill in MACHINE_AUDIT_SKILLS:
        assert skill in external["audit_cadence"]
    assert "claude_maintenance_last" not in external


def test_main_completes_when_audit_cadence_metrics_file_is_unreadable(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    metrics_dir = fake_home / ".local/share/agents/metrics"
    metrics_dir.mkdir(parents=True)
    metrics_file = metrics_dir / "skills.jsonl"
    metrics_file.write_text(
        json.dumps(
            {"skill": "claude-checkup:audit-config", "ts": "2026-08-14T00:00:00+00:00"},
        )
        + "\n",
    )
    monkeypatch.setattr(Path, "home", lambda: fake_home)

    original_read_text = Path.read_text
    metrics_path = str(metrics_file)

    def failing_read_text(self, *args, **kwargs):
        if str(self) == metrics_path:
            raise OSError("permission denied")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", failing_read_text)

    _, out_dir = run_collector(tmp_path, monkeypatch, ["alpha"], [])

    monkeypatch.setattr(Path, "read_text", original_read_text)
    new_data = json.loads((out_dir / "data.json").read_text())
    assert "generated_at" in new_data
    assert len(new_data["repos"]) == 1


def test_main_writes_data_json_when_audit_cadence_raises_unexpected_exception(
    tmp_path,
    monkeypatch,
    capsys,
):
    def raising_collect_audit_cadence():
        raise ValueError("unexpected: not an OSError")

    monkeypatch.setattr(collect, "collect_audit_cadence", raising_collect_audit_cadence)

    _, out_dir = run_collector(tmp_path, monkeypatch, ["alpha"], [])

    assert (out_dir / "data.json").exists()
    new_data = json.loads((out_dir / "data.json").read_text())
    assert len(new_data["repos"]) == 1

    # This call site mirrors collect_external's degrade-and-warn shape: catch
    # the exception, warn on stderr, and still populate
    # data["external"]["audit_cadence"] with the seeded map rather than
    # silently dropping the key. Pin both halves of that contract.
    captured = capsys.readouterr()
    assert new_data["external"]["audit_cadence"] == collect._seeded_audit_cadence()
    assert "WARN audit_cadence" in captured.err


def test_a_raising_skill_adherence_reader_costs_one_metric_not_the_run(
    tmp_path,
    monkeypatch,
    capsys,
):
    def raising_collect_claude_skill_adherence():
        raise ValueError("unexpected: not an OSError")

    monkeypatch.setattr(
        collect, "collect_claude_skill_adherence", raising_collect_claude_skill_adherence
    )

    _, out_dir = run_collector(tmp_path, monkeypatch, ["alpha"], [])

    assert (out_dir / "data.json").exists()
    new_data = json.loads((out_dir / "data.json").read_text())
    assert len(new_data["repos"]) == 1

    captured = capsys.readouterr()
    assert new_data["skill_adherence"] is None
    assert "WARN skill_adherence" in captured.err


# Found by an agoge run on 2026-09-05. It fails against the code as it stands,
# so the strict xfail is the executable record of the defect: fix the defect and
# the marker goes stale, turning the suite red to say "delete me".


@pytest.mark.xfail(
    strict=True,
    raises=FileNotFoundError,
    reason="agoge 2026-09-05: main() opens GITA_CSV unguarded, so a missing registry "
    "escapes as a FileNotFoundError traceback instead of the 'no repos found in gita "
    "registry' exit that SKILL.md documents for that case",
)
def test_missing_registry_file_exits_with_the_documented_message(tmp_path, monkeypatch):
    monkeypatch.setattr(collect, "GITA_CSV", tmp_path / "absent" / "repos.csv")
    monkeypatch.setattr(
        sys, "argv", ["collect.py", "--no-git-fetch", "--out", str(tmp_path / "out")]
    )

    with pytest.raises(SystemExit) as exc:
        main()

    assert "no repos found in gita registry" in str(exc.value)


# The true commit count. agoge 2026-09-05 found that collect_commits caps its list
# at MAX_COMMITS and nothing recorded the real total, so a busy repo read as
# exactly "200 commits" and the history trend flattened at the cap.


def test_a_capped_commit_list_still_carries_the_true_commit_count(tmp_path, monkeypatch):
    repo = tmp_path / "busy"
    make_git_repo(repo, commits=3)
    _serve_git_from_tmp_repos(monkeypatch)
    monkeypatch.setattr(collect, "MAX_COMMITS", 2)

    result = collect_repo(str(repo), 60, False)

    assert len(result["commits"]) == 2
    assert result["commit_count"] == 3


def _serve_git_from_tmp_repos(monkeypatch, default_branch="master"):
    """Send git to the real tmp repos (origin slug acme/<dir name>), fail every
    gh call, and give the metadata call `default_branch` as the default branch."""
    real_run = collect.run

    def fake_run(cmd, cwd=None, timeout=120):
        if cmd[0] == "git" and cmd[1] == "remote":
            return f"git@github.com:acme/{Path(cwd).name}.git\n"
        if cmd[0] == "git":
            return real_run(cmd, cwd=cwd, timeout=timeout)
        raise RuntimeError("gh: not authenticated")

    monkeypatch.setattr(collect, "run", fake_run)
    monkeypatch.setattr(collect, "gh_json", lambda path: {"default_branch": default_branch})


def _make_mixed_age_repo(repo, monkeypatch, branch):
    """Two commits dated ~100 days ago (origin/master), then one commit dated
    now on top of them, published as origin/<branch>."""
    old_date = (datetime.now(timezone.utc) - timedelta(days=100)).strftime(
        "%Y-%m-%dT12:00:00+00:00"
    )
    monkeypatch.setenv("GIT_AUTHOR_DATE", old_date)
    monkeypatch.setenv("GIT_COMMITTER_DATE", old_date)
    make_git_repo(repo, commits=2)
    monkeypatch.delenv("GIT_AUTHOR_DATE")
    monkeypatch.delenv("GIT_COMMITTER_DATE")
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com",
         "commit", "--allow-empty", "-q", "-m", "fresh"],
        cwd=repo, check=True, capture_output=True,
    )
    subprocess.run(
        ["git", "update-ref", f"refs/remotes/origin/{branch}", "HEAD"],
        cwd=repo, check=True, capture_output=True,
    )


def test_commit_count_excludes_commits_older_than_the_window(tmp_path, monkeypatch):
    repo = tmp_path / "mixed"
    _make_mixed_age_repo(repo, monkeypatch, "master")
    # precondition: origin/master holds two ~100-day-old commits and one from today
    assert len(collect.collect_commits(str(repo), "master", 60)) == 1
    assert len(collect.collect_commits(str(repo), "master", 120)) == 3

    assert collect.collect_commit_count(str(repo), "master", 60) == 1
    assert collect.collect_commit_count(str(repo), "master", 120) == 3


def test_collect_repo_counts_the_default_branch_inside_the_requested_window(
    tmp_path,
    monkeypatch,
):
    repo = tmp_path / "trunked"
    _make_mixed_age_repo(repo, monkeypatch, "trunk")
    _serve_git_from_tmp_repos(monkeypatch, default_branch="trunk")
    # precondition: origin/trunk holds two ~100-day-old commits and one from
    # today, while origin/master stops at the two old ones
    assert len(collect.collect_commits(str(repo), "trunk", 60)) == 1
    assert len(collect.collect_commits(str(repo), "master", 120)) == 2

    assert collect_repo(str(repo), 60, False)["commit_count"] == 1
    assert collect_repo(str(repo), 120, False)["commit_count"] == 3


def test_commit_count_ignores_local_commits_not_on_the_origin_default_branch(tmp_path):
    repo = tmp_path / "ahead"
    make_git_repo(repo, commits=3)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.com",
         "commit", "--allow-empty", "-q", "-m", "local only"],
        cwd=repo, check=True, capture_output=True,
    )
    # precondition: origin/master still holds only the fixture's three commits
    assert len(collect.collect_commits(str(repo), "master", 60)) == 3

    assert collect.collect_commit_count(str(repo), "master", 60) == 3


def test_history_row_commit_field_uses_the_true_count(tmp_path, monkeypatch):
    make_git_repo(tmp_path / "alpha", commits=3)
    make_git_repo(tmp_path / "beta", commits=5)
    registry = tmp_path / "repos.csv"
    registry.write_text(f"{tmp_path / 'alpha'}\n{tmp_path / 'beta'}\n")
    out_dir = tmp_path / "out"
    _serve_git_from_tmp_repos(monkeypatch)
    monkeypatch.setattr(collect, "MAX_COMMITS", 2)
    monkeypatch.setattr(collect, "GITA_CSV", registry)
    monkeypatch.setattr(Path, "home", lambda: tmp_path / "home")
    monkeypatch.setattr(sys, "argv", ["collect.py", "--no-git-fetch", "--out", str(out_dir)])

    main()

    data = json.loads((out_dir / "data.json").read_text())
    assert all(len(r["commits"]) == 2 for r in data["repos"])
    counts = {f'{r["owner"]}/{r["name"]}': r["commit_count"] for r in data["repos"]}
    assert counts == {"acme/alpha": 3, "acme/beta": 5}
    last = json.loads((out_dir / "history.jsonl").read_text().strip().splitlines()[-1])
    assert {slug: row["c"] for slug, row in last["repos"].items()} == counts


def test_history_row_commit_field_falls_back_to_the_list_length_without_a_count():
    legacy = {"owner": "acme", "name": "legacy", "errors": [],
              "commits": [{"sha": "a1"}, {"sha": "b2"}]}

    assert history_counts(legacy)["c"] == 2
    assert "e" not in history_counts(legacy)


def test_history_row_marks_error_even_when_commit_count_alone_succeeded():
    row_with_only_commit_count = {"owner": "acme", "name": "onlycount",
                                   "errors": ["meta: boom"], "commit_count": 5}
    assert history_counts(row_with_only_commit_count)["e"] == 1


def test_a_failing_commit_count_warns_and_history_falls_back_to_the_list(
    tmp_path,
    monkeypatch,
):
    repo = tmp_path / "flaky"
    make_git_repo(repo, commits=3)
    _serve_git_from_tmp_repos(monkeypatch)

    def raising_collect_commit_count(path, branch, days):
        raise RuntimeError("rev-list timed out")

    monkeypatch.setattr(collect, "collect_commit_count", raising_collect_commit_count)

    result = collect_repo(str(repo), 60, False)

    assert "commit_count" not in result
    assert "commit_count: rev-list timed out" in result["errors"]
    assert len(result["commits"]) == 3
    assert history_counts(result)["c"] == 3


def test_a_failed_metadata_call_leaves_commit_count_absent(tmp_path, monkeypatch):
    repo = tmp_path / "unreachable"
    make_git_repo(repo, commits=3)
    _serve_git_from_tmp_repos(monkeypatch)

    def failing_gh_json(path):
        raise RuntimeError("gh: not authenticated")

    def unreachable_collect_commit_count(path, branch, days):
        raise AssertionError("collect_commit_count must not run after a metadata failure")

    monkeypatch.setattr(collect, "gh_json", failing_gh_json)
    monkeypatch.setattr(collect, "collect_commit_count", unreachable_collect_commit_count)

    result = collect_repo(str(repo), 60, False)

    assert any(e.startswith("meta: ") for e in result["errors"])
    assert "commits" not in result
    assert "commit_count" not in result
    assert not any("must not run after a metadata failure" in e for e in result["errors"])
