"""Regression tests for collect.py's main() pipeline: the registry partition,
recovery from an unusable data.json, and the audit-cadence call site.
Run: python3 -m pytest test_collect_pipeline.py -q"""

import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import collect
from collect import MACHINE_AUDIT_SKILLS, collect_repo, main
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


# Found by an agoge run on 2026-09-05. Each fails against the code as it stands,
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


@pytest.mark.xfail(
    strict=True,
    raises=KeyError,
    reason="agoge 2026-09-05: collect_commits truncates git log at MAX_COMMITS and nothing "
    "records the true total, so a busy repo reads as exactly '200 commits' on the page "
    "and the Brief headline undercounts the portfolio",
)
def test_a_capped_commit_list_still_carries_the_true_commit_count(tmp_path, monkeypatch):
    repo = tmp_path / "busy"
    make_git_repo(repo, commits=3)
    real_run = collect.run

    def fake_run(cmd, cwd=None, timeout=120):
        if cmd[0] == "git" and cmd[1] == "remote":
            return "git@github.com:acme/busy.git\n"
        if cmd[0] == "git":
            return real_run(cmd, cwd=cwd, timeout=timeout)
        raise RuntimeError("gh: not authenticated")

    monkeypatch.setattr(collect, "MAX_COMMITS", 2)
    monkeypatch.setattr(collect, "run", fake_run)
    monkeypatch.setattr(collect, "gh_json", lambda path: {"default_branch": "master"})

    result = collect_repo(str(repo), 60, False)

    assert len(result["commits"]) == 2
    assert result["commit_count"] == 3
