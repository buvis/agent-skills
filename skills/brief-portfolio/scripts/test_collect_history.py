"""Regression tests for collect.py's snapshot rotation, offline mode, the
--no-git-fetch flag and the history row counters.
Run: python3 -m pytest test_collect_history.py -q"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
import collect
from collect import ROTATE_MIN_AGE, history_counts, main, should_rotate
from collect_test_helpers import (
    make_fake_run,
    make_registry,
    run_collector,
    write_data_json_fixture,
    write_registry_csv,
)


def test_rotate_min_age_is_four_hours():
    from datetime import timedelta

    assert timedelta(hours=4) == ROTATE_MIN_AGE


def test_should_rotate_false_for_snapshot_48_seconds_old():
    from datetime import timedelta

    now = datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc)
    existing_at = (now - timedelta(seconds=48)).isoformat()
    assert should_rotate(existing_at, now) is False


def test_should_rotate_true_for_snapshot_5_hours_old():
    from datetime import timedelta

    now = datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc)
    existing_at = (now - timedelta(hours=5)).isoformat()
    assert should_rotate(existing_at, now) is True


def test_should_rotate_boundary_is_inclusive_at_exactly_four_hours():
    from datetime import timedelta

    now = datetime(2026, 8, 20, 12, 0, 0, tzinfo=timezone.utc)
    just_under = now - (ROTATE_MIN_AGE - timedelta(seconds=1))
    exactly = now - ROTATE_MIN_AGE
    assert should_rotate(just_under.isoformat(), now) is False
    assert should_rotate(exactly.isoformat(), now) is True


def test_main_leaves_older_baseline_untouched_when_existing_snapshot_is_recent(
    tmp_path,
    monkeypatch,
):
    from datetime import timedelta

    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True)
    baseline_content = write_data_json_fixture(
        out_dir / "data-prev.json",
        "2026-08-01T00:00:00+00:00",
        "real-baseline",
    )
    recent_at = (datetime.now(timezone.utc) - timedelta(seconds=48)).isoformat(
        timespec="seconds",
    )
    write_data_json_fixture(out_dir / "data.json", recent_at, "48-seconds-old")

    run_collector(tmp_path, monkeypatch, ["alpha"], [])

    assert (out_dir / "data-prev.json").read_text() == baseline_content
    new_data = json.loads((out_dir / "data.json").read_text())
    assert new_data["generated_at"] != recent_at
    assert len(new_data["repos"]) == 1


def test_main_publishes_old_snapshot_as_data_prev_when_stale(tmp_path, monkeypatch):
    from datetime import timedelta

    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True)
    stale_at = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(
        timespec="seconds",
    )
    old_content = write_data_json_fixture(out_dir / "data.json", stale_at, "5-hours-old")

    run_collector(tmp_path, monkeypatch, ["alpha"], [])

    assert (out_dir / "data-prev.json").read_text() == old_content
    new_data = json.loads((out_dir / "data.json").read_text())
    assert new_data["generated_at"] != stale_at
    assert len(new_data["repos"]) == 1


def test_main_leaves_data_json_unchanged_when_prev_tmp_write_fails(
    tmp_path,
    monkeypatch,
):
    from datetime import timedelta

    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True)
    stale_at = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(
        timespec="seconds",
    )
    old_content = write_data_json_fixture(out_dir / "data.json", stale_at, "5-hours-old")

    original_write_text = Path.write_text

    def failing_write_text(self, *args, **kwargs):
        if str(self).endswith("data-prev.json.tmp"):
            raise OSError("disk full")
        return original_write_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", failing_write_text)

    with pytest.raises(OSError):
        run_collector(tmp_path, monkeypatch, ["alpha"], [])

    assert (out_dir / "data.json").read_text() == old_content


def test_offline_makes_zero_subprocess_calls(tmp_path, monkeypatch):
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True)
    write_data_json_fixture(out_dir / "data.json", "2026-08-20T00:00:00+00:00", "cached")

    def explode(*args, **kwargs):
        raise AssertionError(
            f"subprocess.run should not be called: {args!r} {kwargs!r}",
        )

    monkeypatch.setattr(collect.subprocess, "run", explode)
    monkeypatch.setattr(
        sys,
        "argv",
        ["collect.py", "--offline", "--out", str(out_dir)],
    )
    main()


def test_offline_leaves_cached_data_json_byte_for_byte_unchanged(tmp_path, monkeypatch):
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True)
    content = write_data_json_fixture(
        out_dir / "data.json",
        "2026-08-20T00:00:00+00:00",
        "cached",
    )

    monkeypatch.setattr(
        sys,
        "argv",
        ["collect.py", "--offline", "--out", str(out_dir)],
    )
    main()

    assert (out_dir / "data.json").read_text() == content


def test_offline_without_cached_data_json_exits_with_error(tmp_path, monkeypatch):
    out_dir = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        ["collect.py", "--offline", "--out", str(out_dir)],
    )

    with pytest.raises(SystemExit) as exc_info:
        main()

    message = str(exc_info.value.code)
    assert message
    assert str(out_dir / "data.json") in message
    assert "collect.py" in message


def test_offline_does_not_write_history_digest_or_prev_snapshot(tmp_path, monkeypatch):
    out_dir = tmp_path / "out"
    out_dir.mkdir(parents=True)
    write_data_json_fixture(out_dir / "data.json", "2026-08-20T00:00:00+00:00", "cached")

    monkeypatch.setattr(
        sys,
        "argv",
        ["collect.py", "--offline", "--out", str(out_dir)],
    )
    main()

    assert not (out_dir / "history.jsonl").exists()
    assert not (out_dir / "commits-digest.md").exists()
    assert not (out_dir / "data-prev.json").exists()


def test_no_git_fetch_flag_passes_fetch_false_to_collect_repo(tmp_path, monkeypatch):
    paths = make_registry(tmp_path, ["alpha"])
    monkeypatch.setattr(collect, "GITA_CSV", write_registry_csv(tmp_path, paths))
    monkeypatch.setattr(collect, "run", make_fake_run(set()))
    fetch_values = []

    def fake_collect_repo(path, days, fetch):
        fetch_values.append(fetch)
        return {"owner": "acme", "name": Path(path).name, "errors": []}

    monkeypatch.setattr(collect, "collect_repo", fake_collect_repo)
    out_dir = tmp_path / "out"
    monkeypatch.setattr(
        sys,
        "argv",
        ["collect.py", "--no-git-fetch", "--out", str(out_dir)],
    )
    main()

    assert fetch_values == [False]


def test_no_fetch_old_spelling_is_rejected_by_argparse(tmp_path, monkeypatch):
    paths = make_registry(tmp_path, ["alpha"])
    monkeypatch.setattr(collect, "GITA_CSV", write_registry_csv(tmp_path, paths))

    def explode(*args, **kwargs):
        raise AssertionError(
            f"subprocess.run should not be called: {args!r} {kwargs!r}"
        )

    monkeypatch.setattr(collect.subprocess, "run", explode)
    monkeypatch.setattr(
        sys,
        "argv",
        ["collect.py", "--no-fetch", "--out", str(tmp_path / "out")],
    )

    with pytest.raises(SystemExit):
        main()


def test_history_counts_marks_a_repo_with_errors_and_no_data():
    row = history_counts(
        {"owner": "acme", "name": "widget", "errors": ["meta: gh: not authenticated"]},
    )
    assert row["e"] == 1
    # The marker is added to the counts, not substituted for them.
    assert row["c"] == 0
    assert row["u"] == 0


def test_history_counts_leaves_a_repo_without_errors_unmarked():
    row = history_counts({"owner": "acme", "name": "widget", "errors": []})
    assert "e" not in row


def test_history_counts_leaves_a_partly_fetched_repo_unmarked():
    row = history_counts(
        {"owner": "acme", "name": "widget", "errors": ["ci: gh api: HTTP 500"],
         "commits": [{"sha": "abc1234"}], "stars": 3},
    )
    # One field failed but the rest is real data, so these are not fake zeros.
    assert "e" not in row
    assert row["c"] == 1
    assert row["s"] == 3


def test_history_counts_leaves_a_partial_failure_unmarked():
    row = history_counts({"errors": ["fetch: timeout"], "commits": []})
    # A non-fatal error alongside collected data must not get the "e" marker.
    assert "e" not in row
