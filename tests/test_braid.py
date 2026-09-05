from __future__ import annotations

import json
import os
import shutil
from dataclasses import replace
from pathlib import Path

import pytest

from agent_skills_braid import cli
from agent_skills_braid.cli import (
    BraidError,
    Mode,
    Settings,
    create_directory_link,
    read_configured_sources,
    run,
)


def make_skill(source: Path, name: str) -> Path:
    skill = source / "skills" / name
    skill.mkdir(parents=True)
    (skill / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: Test {name}.\n---\n\n# {name}\n"
    )
    return skill


def settings(
    tmp_path: Path,
    *sources: Path,
    mode: Mode = Mode.SYNC,
    policy_files: tuple[Path, ...] = (),
) -> Settings:
    return Settings(
        sources=tuple(sources),
        agents_root=tmp_path / "home" / ".agents",
        claude_root=tmp_path / "home" / ".claude",
        mode=mode,
        policy_files=policy_files,
    )


def test_sync_composes_union_and_projects_only_eligible_skills(tmp_path: Path) -> None:
    source = tmp_path / "personal"
    portable = make_skill(source, "portable")
    make_skill(source, "plugin-owned")
    policy = source / ".braidignore"
    policy.write_text("plugin-owned\n")

    config = settings(tmp_path, source, policy_files=(policy,))
    claude_only = config.claude_root / "skills" / "claude-only"
    plugin_owned = config.claude_root / "skills" / "plugin-owned"
    claude_only.mkdir(parents=True)
    plugin_owned.mkdir(parents=True)
    (claude_only / "keep").write_text("yes")
    (plugin_owned / "keep").write_text("plugin")

    result = run(config)

    union_link = config.agents_root / "skills" / "portable"
    claude_link = config.claude_root / "skills" / "portable"
    assert union_link.is_symlink()
    assert union_link.resolve() == portable.resolve()
    assert claude_link.is_symlink()
    assert claude_link.resolve() == portable.resolve()
    assert (claude_only / "keep").read_text() == "yes"
    assert (plugin_owned / "keep").read_text() == "plugin"
    assert result.linked == 3
    assert result.ignored == 1

    checked = run(config.with_mode(Mode.CHECK))
    assert checked.drift == 0


def test_duplicate_names_fail_before_writing(tmp_path: Path) -> None:
    first = tmp_path / "first"
    second = tmp_path / "second"
    make_skill(first, "collision")
    make_skill(second, "collision")
    config = settings(tmp_path, first, second)

    with pytest.raises(BraidError, match="duplicate skill name"):
        run(config)

    assert not config.agents_root.exists()


def test_dry_run_reports_drift_without_writing(tmp_path: Path) -> None:
    source = tmp_path / "personal"
    make_skill(source, "portable")
    config = settings(tmp_path, source, mode=Mode.DRY_RUN)

    result = run(config)

    assert result.drift == 2
    assert not config.agents_root.exists()
    assert not config.claude_root.exists()


def test_real_union_collision_is_backed_up_before_linking(tmp_path: Path) -> None:
    source = tmp_path / "personal"
    expected = make_skill(source, "portable")
    config = settings(tmp_path, source)
    collision = config.agents_root / "skills" / "portable"
    collision.mkdir(parents=True)
    (collision / "original").write_text("keep")

    run(config)

    assert collision.is_symlink()
    assert collision.resolve() == expected.resolve()
    backups = list((config.agents_root / "backups").glob("*/compose/portable/original"))
    assert len(backups) == 1
    assert backups[0].read_text() == "keep"


def test_stale_cleanup_removes_only_manifest_owned_links(tmp_path: Path) -> None:
    source = tmp_path / "personal"
    skill = make_skill(source, "temporary")
    config = settings(tmp_path, source)
    unowned = config.agents_root / "skills" / "manual"
    unowned.mkdir(parents=True)
    (unowned / "keep").write_text("yes")
    run(config)

    shutil.rmtree(skill)
    result = run(config)

    assert not os.path.lexists(config.agents_root / "skills" / "temporary")
    assert (unowned / "keep").read_text() == "yes"
    assert result.removed == 2


def test_existing_source_tree_is_not_replaced_during_transition(tmp_path: Path) -> None:
    agents_root = tmp_path / "home" / ".agents"
    source_skill = make_skill(agents_root, "portable")
    config = Settings(
        sources=(agents_root,),
        agents_root=agents_root,
        claude_root=tmp_path / "home" / ".claude",
        mode=Mode.SYNC,
    )

    run(config)

    assert source_skill.is_dir()
    assert not source_skill.is_symlink()
    assert (config.claude_root / "skills" / "portable").is_symlink()
    state = json.loads((agents_root / ".braid-state.json").read_text())
    assert state["union"] == {}


def test_no_claude_preserves_existing_projection_and_state(tmp_path: Path) -> None:
    source = tmp_path / "personal"
    make_skill(source, "portable")
    config = settings(tmp_path, source)
    run(config)
    claude_link = config.claude_root / "skills" / "portable"

    result = run(replace(config, project_claude=False))

    assert result.drift == 0
    assert claude_link.is_symlink()
    state = json.loads((config.agents_root / ".braid-state.json").read_text())
    assert "portable" in state["hosts"]["claude"]


def test_windows_symlink_privilege_failure_falls_back_to_junction(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "target"
    destination = tmp_path / "destination"
    target.mkdir()
    calls: list[list[str]] = []

    error = OSError("symlink privilege unavailable")
    error.winerror = 1314  # type: ignore[attr-defined]

    def denied(*_args: object, **_kwargs: object) -> None:
        raise error

    class Completed:
        returncode = 0
        stdout = "junction created"
        stderr = ""

    def runner(command: list[str], **_kwargs: object) -> Completed:
        calls.append(command)
        return Completed()

    monkeypatch.setattr(os, "symlink", denied)

    backend = create_directory_link(destination, target, platform="nt", runner=runner)

    assert backend == "junction"
    assert calls == [["cmd", "/c", "mklink", "/J", str(destination), str(target)]]


def test_configured_sources_support_comments_home_and_relative_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    config_root = home / ".config" / "agent-skills"
    source_list = config_root / "sources.d" / "work"
    source_list.parent.mkdir(parents=True)
    source_list.write_text("# private source\n~/work-skills\n../../shared-skills\n")
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))

    sources = read_configured_sources(config_root)

    assert sources == (
        (home / "work-skills").resolve(),
        (source_list.parent / "../../shared-skills").resolve(),
    )


def test_cli_loads_machine_policy_from_agents_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source = tmp_path / "personal"
    make_skill(source, "portable")
    make_skill(source, "machine-ignored")
    agents_root = tmp_path / "home" / ".agents"
    agents_root.mkdir(parents=True)
    (agents_root / ".braidignore").write_text("machine-ignored\n")
    claude_root = tmp_path / "home" / ".claude"
    monkeypatch.setattr(cli, "_repository_root", lambda: source)

    status = cli.main(
        [
            "--agents-root",
            str(agents_root),
            "--claude-root",
            str(claude_root),
            "--config-root",
            str(tmp_path / "empty-config"),
        ]
    )

    assert status == 0
    assert "3 change(s)" in capsys.readouterr().out
    assert (agents_root / "skills" / "machine-ignored").is_symlink()
    assert not os.path.lexists(claude_root / "skills" / "machine-ignored")


# Found by an agoge run on 2026-08-31. Each of these fails against the code as
# it stands, so the strict xfail is the executable record of the defect: fix
# the defect and the marker goes stale, turning the suite red to say "delete me".


@pytest.mark.xfail(
    strict=True,
    reason="agoge 2026-08-31: --check reconciles against the state manifest only, never "
    "against the filesystem, so a link braid created but no longer records is invisible. "
    "The re-sync below is what hides it: it rewrites the state without the orphan, so "
    "the MISMATCH STATE signal for a missing manifest is spent before --check runs.",
)
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


@pytest.mark.xfail(
    strict=True,
    reason="agoge 2026-08-31: the cleanup refusal is raised before the mode check, so "
    "read-only --check aborts mid-report instead of reporting the changed path",
)
def test_check_reports_a_hand_changed_managed_path_instead_of_aborting(tmp_path: Path) -> None:
    source = tmp_path / "personal"
    skill = make_skill(source, "temporary")
    make_skill(source, "kept")
    config = settings(tmp_path, source)
    run(config)

    shutil.rmtree(skill)
    stale = config.agents_root / "skills" / "temporary"
    stale.unlink()
    stale.mkdir()

    result = run(config.with_mode(Mode.CHECK))

    assert result.drift > 0


@pytest.mark.xfail(
    strict=True,
    reason="agoge 2026-08-31: _write_state has no try/finally, so a failed state write "
    "escapes as a bare OSError and orphans one temp snapshot per run",
)
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


# Found by an agoge run on 2026-09-05; same contract as the 2026-08-31 block above.


@pytest.mark.xfail(
    strict=True,
    reason="agoge 2026-09-05: discover_inventory follows a symlinked skill directory "
    "(candidate.is_dir() is true through the link) and records its resolved target, so a "
    "link planted in a source tree projects a directory that lives outside that tree",
)
def test_a_symlinked_skill_directory_outside_the_source_is_not_inventoried(
    tmp_path: Path,
) -> None:
    source = tmp_path / "personal"
    make_skill(source, "kept")
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "SKILL.md").write_text("---\nname: evil\ndescription: Test evil.\n---\n\n# evil\n")
    (source / "skills" / "evil").symlink_to(outside, target_is_directory=True)

    inventory = cli.discover_inventory([source])

    assert "evil" not in inventory
