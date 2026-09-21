"""Regression tests for collect.py's local parsers: brush reports, skill
adherence, audit cadence and the purge-devlocal trash scan.
Run: python3 -m pytest test_collect_local.py -q"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from collect import (
    MACHINE_AUDIT_SKILLS,
    collect_audit_cadence,
    collect_brush,
    collect_claude_skill_adherence,
    collect_purge_devlocal,
)
from collect_test_helpers import make_trash_dir, write_report


def test_reads_generated_date_from_brush_report(tmp_path):
    write_report(
        tmp_path,
        "# Brush report - x\n\n"
        "- generated: 2026-07-13 14:02 | mode: quick | HEAD: abc123 | branch: master | unpushed: 0\n",
    )
    assert collect_brush(tmp_path) == "2026-07-13"


def test_never_brushed_repo_returns_none(tmp_path):
    assert collect_brush(tmp_path) is None


def test_report_without_generated_line_returns_none(tmp_path):
    write_report(tmp_path, "# Brush report - x\n")
    assert collect_brush(tmp_path) is None


def test_skill_adherence_none_when_no_file(tmp_path):
    assert collect_claude_skill_adherence(tmp_path / "skills.jsonl") is None


def test_skill_adherence_counts_last_30d_and_ranks_top(tmp_path):
    from datetime import timedelta

    now = datetime.now(timezone.utc)
    recent = now.isoformat()
    old = (now - timedelta(days=45)).isoformat()
    f = tmp_path / "skills.jsonl"
    f.write_text(
        "\n".join(
            json.dumps(r)
            for r in [
                {"skill": "work", "ts": recent},
                {"skill": "work", "ts": recent},
                {"skill": "brush", "ts": recent},
                {"skill": "survey", "ts": old},  # outside the 30d window
                "not json",
            ]
        )
        + "\n",
    )
    got = collect_claude_skill_adherence(f)
    assert got["count"] == 3
    assert got["distinct"] == 2
    assert got["top"][0] == {"skill": "work", "n": 2}
    assert not any(t["skill"] == "survey" for t in got["top"])


def test_skill_adherence_empty_when_all_stale(tmp_path):
    from datetime import timedelta

    old = (datetime.now(timezone.utc) - timedelta(days=60)).isoformat()
    f = tmp_path / "skills.jsonl"
    f.write_text(json.dumps({"skill": "work", "ts": old}) + "\n")
    assert collect_claude_skill_adherence(f) == {"count": 0, "distinct": 0, "top": []}


def test_machine_audit_skills_is_six_skills_in_order():
    assert MACHINE_AUDIT_SKILLS == [
        "claude-checkup:audit-filesystem",
        "claude-checkup:audit-context",
        "claude-checkup:audit-config",
        "claude-checkup:audit-authoring",
        "claude-checkup:audit-sessions",
        "claude-checkup:audit-mcp-health",
    ]


def test_audit_cadence_all_none_when_file_missing(tmp_path):
    result = collect_audit_cadence(tmp_path / "skills.jsonl")
    assert result == {skill: None for skill in MACHINE_AUDIT_SKILLS}


def test_audit_cadence_returns_newest_day_per_skill_and_none_for_no_rows(tmp_path):
    f = tmp_path / "skills.jsonl"
    f.write_text(
        "\n".join(
            json.dumps(r)
            for r in [
                {
                    "skill": "claude-checkup:audit-filesystem",
                    "ts": "2026-08-15T10:30:00+00:00",
                },
                {
                    "skill": "claude-checkup:audit-filesystem",
                    "ts": "2026-08-10T09:00:00+00:00",
                },
                {"skill": "purge-devlocal", "ts": "2026-08-12T00:00:00+00:00"},
            ]
        )
        + "\n",
    )
    result = collect_audit_cadence(f)
    assert result["claude-checkup:audit-filesystem"] == "2026-08-15"
    assert result["purge-devlocal"] == "2026-08-12"
    assert result["claude-checkup:audit-context"] is None


def test_audit_cadence_has_no_lookback_cutoff_for_a_very_old_row(tmp_path):
    f = tmp_path / "skills.jsonl"
    f.write_text(
        json.dumps(
            {"skill": "claude-checkup:audit-config", "ts": "2020-01-01T00:00:00+00:00"},
        )
        + "\n",
    )
    result = collect_audit_cadence(base=f)
    assert result["claude-checkup:audit-config"] == "2020-01-01"


def test_audit_cadence_seeds_all_six_keys_and_includes_unnamespaced_skill(tmp_path):
    f = tmp_path / "skills.jsonl"
    f.write_text(
        "\n".join(
            json.dumps(r)
            for r in [
                {
                    "skill": "claude-checkup:audit-sessions",
                    "ts": "2026-08-20T00:00:00+00:00",
                },
                {"skill": "purge-devlocal", "ts": "2026-08-18T00:00:00+00:00"},
            ]
        )
        + "\n",
    )
    result = collect_audit_cadence(f)
    for skill in MACHINE_AUDIT_SKILLS:
        assert skill in result
    assert result["claude-checkup:audit-sessions"] == "2026-08-20"
    for skill in MACHINE_AUDIT_SKILLS:
        if skill != "claude-checkup:audit-sessions":
            assert result[skill] is None
    assert result["purge-devlocal"] == "2026-08-18"


def test_audit_cadence_skips_malformed_json_line_without_raising(tmp_path):
    f = tmp_path / "skills.jsonl"
    f.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "skill": "claude-checkup:audit-config",
                        "ts": "2026-08-14T00:00:00+00:00",
                    },
                ),
                "not json",
            ]
        )
        + "\n",
    )
    result = collect_audit_cadence(f)
    assert result["claude-checkup:audit-config"] == "2026-08-14"


def test_audit_cadence_returns_seeded_dict_when_read_raises_oserror(tmp_path, monkeypatch):
    f = tmp_path / "skills.jsonl"
    f.write_text(
        json.dumps(
            {"skill": "claude-checkup:audit-config", "ts": "2026-08-14T00:00:00+00:00"},
        )
        + "\n",
    )

    original_read_text = Path.read_text
    target_path = str(f)

    def failing_read_text(self, *args, **kwargs):
        if str(self) == target_path:
            raise OSError("permission denied")
        return original_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", failing_read_text)

    result = collect_audit_cadence(f)

    assert result == {skill: None for skill in MACHINE_AUDIT_SKILLS}


def test_collect_purge_devlocal_returns_none_when_trash_dir_absent(tmp_path):
    assert collect_purge_devlocal(tmp_path) is None


def test_collect_purge_devlocal_returns_the_only_dated_subdirectory(tmp_path):
    make_trash_dir(tmp_path, dirs=["2026-08-01"])
    assert collect_purge_devlocal(tmp_path) == "2026-08-01"


def test_collect_purge_devlocal_returns_newest_of_two_dated_subdirectories(tmp_path):
    make_trash_dir(tmp_path, dirs=["2026-08-01", "2026-08-20"])
    assert collect_purge_devlocal(tmp_path) == "2026-08-20"


def test_collect_purge_devlocal_returns_none_when_no_dated_directory_present(tmp_path):
    make_trash_dir(tmp_path, dirs=["backup", "2026-8-1"], files=["manifest.tsv"])
    assert collect_purge_devlocal(tmp_path) is None


def test_collect_purge_devlocal_ignores_plain_file_named_like_a_date(tmp_path):
    make_trash_dir(tmp_path, files=["2026-08-01"])
    assert collect_purge_devlocal(tmp_path) is None


def test_collect_purge_devlocal_picks_newest_directory_despite_a_later_named_file(
    tmp_path,
):
    make_trash_dir(
        tmp_path,
        dirs=["2026-08-01", "2026-08-20"],
        files=["2026-08-31", "manifest.tsv"],
    )
    assert collect_purge_devlocal(tmp_path) == "2026-08-20"


def test_collect_purge_devlocal_accepts_str_path_argument(tmp_path):
    make_trash_dir(tmp_path, dirs=["2026-08-01"])
    assert collect_purge_devlocal(str(tmp_path)) == "2026-08-01"
