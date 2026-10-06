"""Read-only drift reporting and fail-clean state writes (PRD 00014).

Found by an agoge run on 2026-08-31 and recorded as strict xfail tests until the
defects were fixed. They stay as the regression tests for those fixes.
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Callable
from pathlib import Path

import pytest
from test_braid import enroll, kiro_root, make_skill, settings

from agent_skills_braid import cli
from agent_skills_braid.cli import BraidError, Mode, Result, Settings, run


def test_check_reports_a_managed_link_the_state_file_no_longer_records(tmp_path: Path) -> None:
    source = tmp_path / "personal"
    skill = make_skill(source, "temporary")
    make_skill(source, "kept")
    config = settings(tmp_path, source)
    run(config)

    (config.agents_root / ".braid-state.json").unlink()
    shutil.rmtree(skill)
    run(config)

    result = run(config.with_mode(Mode.CHECK))

    dangling = config.agents_root / "skills" / "temporary"
    assert os.path.lexists(dangling) and not dangling.exists()
    assert result.drift > 0


@pytest.mark.parametrize("mode", [Mode.DRY_RUN, Mode.CHECK])
def test_check_leaves_the_orphan_link_it_reports_on_disk(tmp_path: Path, mode: Mode) -> None:
    source = tmp_path / "personal"
    skill = make_skill(source, "temporary")
    make_skill(source, "kept")
    config = settings(tmp_path, source)
    run(config)
    (config.agents_root / ".braid-state.json").unlink()
    shutil.rmtree(skill)
    synced: list[str] = []
    run(config, emit=synced.append)
    reported: list[str] = []

    run(config.with_mode(mode), emit=reported.append)

    orphans = [root / "skills" / "temporary" for root in (config.agents_root, config.claude_root)]
    assert reported == [f"MISMATCH ORPHAN {orphan}" for orphan in orphans]
    assert all(os.path.lexists(orphan) for orphan in orphans)
    assert not (config.agents_root / "backups").exists()
    assert not any("ORPHAN" in line for line in synced)


def test_check_ignores_a_link_pointing_outside_every_source_root(tmp_path: Path) -> None:
    source = tmp_path / "personal"
    make_skill(source, "portable")
    config = settings(tmp_path, source)
    run(config)
    own_skill = tmp_path / "own-skill"
    own_skill.mkdir()
    planted = config.agents_root / "skills" / "own"
    planted.symlink_to(own_skill, target_is_directory=True)

    result = run(config.with_mode(Mode.CHECK))

    assert result.drift == 0
    assert planted.is_symlink()


def test_check_after_a_lost_state_file_reports_the_state_not_the_wanted_links(
    tmp_path: Path,
) -> None:
    source = tmp_path / "personal"
    make_skill(source, "portable")
    make_skill(source, "plugin-owned")
    policy = source / ".braidignore"
    policy.write_text("plugin-owned\n")
    config = enroll(settings(tmp_path, source, policy_files=(policy,)))
    run(config)
    state_path = config.agents_root / ".braid-state.json"
    state_path.unlink()
    reported: list[str] = []

    run(config.with_mode(Mode.CHECK), emit=reported.append)

    assert reported == [f"MISMATCH STATE {state_path}"]


def test_check_reports_a_kiro_link_the_state_does_not_record(tmp_path: Path) -> None:
    source = tmp_path / "personal"
    make_skill(source, "portable")
    config = enroll(settings(tmp_path, source))
    run(config)
    stray = kiro_root(config) / "skills" / "stray"
    stray.symlink_to(config.agents_root / "skills" / "portable", target_is_directory=True)
    reported: list[str] = []

    result = run(config.with_mode(Mode.CHECK), emit=reported.append)

    assert reported == [f"MISMATCH ORPHAN {stray}"]
    assert result.drift == 1
    assert stray.is_symlink()


def test_an_unreadable_link_stops_the_orphan_scan_with_a_braid_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "skills"
    root.mkdir()
    (root / "stray").symlink_to(tmp_path, target_is_directory=True)

    def vanished(path: object, *args: object, **kwargs: object) -> str:
        raise OSError(f"{path} vanished")

    monkeypatch.setattr(os, "readlink", vanished)

    with pytest.raises(BraidError, match="cannot scan"):
        cli._report_orphan_links(root, [tmp_path], set(), Result(), print)


def change_a_managed_path_by_hand(tmp_path: Path) -> tuple[Settings, Path]:
    source = tmp_path / "personal"
    skill = make_skill(source, "temporary")
    make_skill(source, "kept")
    config = settings(tmp_path, source)
    run(config)
    shutil.rmtree(skill)
    stale = config.agents_root / "skills" / "temporary"
    stale.unlink()
    stale.mkdir()
    return config, stale


def test_check_reports_a_hand_changed_managed_path_instead_of_aborting(tmp_path: Path) -> None:
    config, _stale = change_a_managed_path_by_hand(tmp_path)

    result = run(config.with_mode(Mode.CHECK))

    assert result.drift > 0


@pytest.mark.parametrize("mode", [Mode.DRY_RUN, Mode.CHECK])
def test_read_only_run_names_the_hand_changed_path_and_finishes_the_report(
    tmp_path: Path, mode: Mode
) -> None:
    config, stale = change_a_managed_path_by_hand(tmp_path)
    reported: list[str] = []

    run(config.with_mode(mode), emit=reported.append)

    assert reported[0] == f"MISMATCH CHANGED {stale}"
    # The Claude projection of the same skill comes after it and is still reported.
    assert len(reported) == 2


def test_sync_refuses_to_remove_a_hand_changed_managed_path(tmp_path: Path) -> None:
    config, stale = change_a_managed_path_by_hand(tmp_path)

    with pytest.raises(BraidError, match="refusing to clean changed managed path"):
        run(config)

    assert stale.is_dir()


def test_a_failed_state_write_reports_a_braid_error_and_leaves_no_temp_file(
    tmp_path: Path,
) -> None:
    source = tmp_path / "personal"
    make_skill(source, "portable")
    config = settings(tmp_path, source)
    state_path = config.agents_root / ".braid-state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.mkdir()

    with pytest.raises(BraidError):
        run(config)

    assert list(state_path.parent.glob(".*.tmp")) == []


def occupy_the_parent(state_path: Path) -> None:
    state_path.parent.write_text("not a directory")


def occupy_the_temp_path(state_path: Path) -> None:
    state_path.parent.mkdir()
    state_path.with_name(f".{state_path.name}.{os.getpid()}.tmp").mkdir()


@pytest.mark.parametrize(
    "occupy", [occupy_the_parent, occupy_the_temp_path], ids=["parent-is-a-file", "temp-is-a-dir"]
)
def test_a_failed_temp_cleanup_does_not_hide_the_state_write_error(
    tmp_path: Path, occupy: Callable[[Path], None]
) -> None:
    state_path = tmp_path / "agents" / ".braid-state.json"
    occupy(state_path)

    with pytest.raises(BraidError, match="cannot write Braid state"):
        cli._write_state(state_path, cli.State.empty())


def test_cli_reports_a_failed_state_write_on_one_line_and_exits_2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "personal"
    make_skill(source, "portable")
    agents_root = tmp_path / "home" / ".agents"
    state_path = agents_root / ".braid-state.json"
    state_path.mkdir(parents=True)
    monkeypatch.setattr(cli, "_repository_root", lambda: source)
    monkeypatch.setattr(
        "sys.argv",
        [
            "braid",
            "--no-kiro",
            "--agents-root",
            str(agents_root),
            "--claude-root",
            str(tmp_path / "home" / ".claude"),
            "--config-root",
            str(tmp_path / "empty-config"),
        ],
    )

    with pytest.raises(SystemExit) as stopped:
        cli.entrypoint()

    assert stopped.value.code == 2
    error = capsys.readouterr().err
    assert error.startswith(f"braid: cannot write Braid state {state_path}: ")
    assert error.count("\n") == 1
