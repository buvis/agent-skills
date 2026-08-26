from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from agent_skills_braid import __version__

STATE_VERSION = 1
SKILL_NAME = re.compile(r"^name:\s*[\"']?([a-z0-9-]+)[\"']?\s*$")


class BraidError(RuntimeError):
    """A safe, user-actionable composition failure."""


class Mode(str, Enum):
    SYNC = "sync"
    DRY_RUN = "dry-run"
    CHECK = "check"


@dataclass(frozen=True)
class Settings:
    sources: tuple[Path, ...]
    agents_root: Path
    claude_root: Path
    mode: Mode = Mode.SYNC
    policy_files: tuple[Path, ...] = ()
    project_claude: bool = True
    platform: str = os.name

    def with_mode(self, mode: Mode) -> Settings:
        return replace(self, mode=mode)


@dataclass
class Result:
    linked: int = 0
    current: int = 0
    ignored: int = 0
    removed: int = 0
    backed_up: int = 0
    drift: int = 0


@dataclass(frozen=True)
class State:
    union: dict[str, str]
    hosts: dict[str, dict[str, str]]

    @classmethod
    def empty(cls) -> State:
        return cls(union={}, hosts={})

    def as_json(self) -> dict[str, Any]:
        return {"version": STATE_VERSION, "union": self.union, "hosts": self.hosts}


def _present(path: Path) -> bool:
    return os.path.lexists(path)


def _expand_user(path: str | Path) -> Path:
    value = os.fspath(path)
    if value == "~":
        return Path.home()
    if value.startswith(("~/", "~\\")):
        return Path.home() / value[2:]
    return Path(value).expanduser()


def _resolved(path: Path) -> Path:
    return _expand_user(path).resolve(strict=False)


def _absolute(path: Path) -> Path:
    return Path(os.path.abspath(_expand_user(path)))


def _skill_name(skill_directory: Path) -> str:
    skill_file = skill_directory / "SKILL.md"
    try:
        lines = skill_file.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise BraidError(f"cannot read {skill_file}: {error}") from error

    if not lines or lines[0] != "---":
        raise BraidError(f"invalid skill frontmatter: {skill_file}")
    for line in lines[1:]:
        if line == "---":
            break
        match = SKILL_NAME.fullmatch(line)
        if match:
            name = match.group(1)
            if name != skill_directory.name:
                raise BraidError(
                    f"skill name {name!r} does not match directory {skill_directory.name!r}"
                )
            return name
    raise BraidError(f"missing valid name in {skill_file}")


def _skills_directory(source: Path) -> Path:
    source = _resolved(source)
    nested = source / "skills"
    if nested.is_dir():
        return nested
    if source.is_dir() and source.name == "skills":
        return source
    raise BraidError(f"skill source has no skills directory: {source}")


def discover_inventory(sources: Iterable[Path]) -> dict[str, Path]:
    inventory: dict[str, Path] = {}
    owners: dict[str, Path] = {}
    seen_sources: set[Path] = set()

    for configured_source in sources:
        source = _skills_directory(configured_source)
        if source in seen_sources:
            continue
        seen_sources.add(source)
        for candidate in sorted(source.iterdir(), key=lambda path: path.name):
            if candidate.name.startswith(".") or not candidate.is_dir():
                continue
            if not (candidate / "SKILL.md").is_file():
                continue
            name = _skill_name(candidate)
            resolved_candidate = _resolved(candidate)
            if name in inventory and inventory[name] != resolved_candidate:
                raise BraidError(
                    f"duplicate skill name {name!r}: {owners[name]} and {configured_source}"
                )
            inventory[name] = resolved_candidate
            owners[name] = _resolved(configured_source)
    return inventory


def read_configured_sources(config_root: Path) -> tuple[Path, ...]:
    sources_directory = _expand_user(config_root) / "sources.d"
    if not sources_directory.is_dir():
        return ()

    sources: list[Path] = []
    for source_file in sorted(sources_directory.iterdir(), key=lambda path: path.name):
        if not source_file.is_file() or source_file.name.startswith("."):
            continue
        for raw_line in source_file.read_text(encoding="utf-8").splitlines():
            value = raw_line.split("#", 1)[0].strip()
            if not value:
                continue
            expanded = _expand_user(value)
            if not expanded.is_absolute():
                expanded = source_file.parent / expanded
            sources.append(expanded.resolve(strict=False))
    return tuple(sources)


def read_ignored(policy_files: Iterable[Path]) -> set[str]:
    ignored: set[str] = set()
    for policy_file in policy_files:
        if not policy_file.is_file():
            continue
        for raw_line in policy_file.read_text(encoding="utf-8").splitlines():
            value = raw_line.split("#", 1)[0].strip()
            if value:
                ignored.add(value)
    return ignored


def create_directory_link(
    destination: Path,
    target: Path,
    *,
    platform: str = os.name,
    runner: Callable[..., object] = subprocess.run,
) -> str:
    try:
        os.symlink(str(target), str(destination), target_is_directory=True)
        return "symlink"
    except OSError as error:
        if platform != "nt" or getattr(error, "winerror", None) not in {5, 1314}:
            raise BraidError(f"cannot link {destination} -> {target}: {error}") from error

    completed = runner(
        ["cmd", "/c", "mklink", "/J", str(destination), str(target)],
        capture_output=True,
        text=True,
        check=False,
    )
    if getattr(completed, "returncode", 1) != 0:
        detail = getattr(completed, "stderr", "") or getattr(completed, "stdout", "")
        raise BraidError(f"cannot create junction {destination} -> {target}: {detail.strip()}")
    return "junction"


def _points_to(path: Path, target: Path, platform: str) -> bool:
    if path.is_symlink():
        raw_target = Path(os.readlink(path))
        if not raw_target.is_absolute():
            raw_target = path.parent / raw_target
        return _resolved(raw_target) == _resolved(target)
    if platform == "nt" and path.is_dir():
        return _resolved(path) == _resolved(target)
    return False


def _load_state(path: Path) -> State:
    if not path.is_file():
        return State.empty()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise BraidError(f"cannot read Braid state {path}: {error}") from error
    if payload.get("version") != STATE_VERSION:
        raise BraidError(f"unsupported Braid state version in {path}")
    union = payload.get("union")
    hosts = payload.get("hosts")
    if not isinstance(union, dict) or not isinstance(hosts, dict):
        raise BraidError(f"invalid Braid state schema in {path}")
    if not all(isinstance(key, str) and isinstance(value, str) for key, value in union.items()):
        raise BraidError(f"invalid union state in {path}")
    normalized_hosts: dict[str, dict[str, str]] = {}
    for host, links in hosts.items():
        if not isinstance(host, str) or not isinstance(links, dict):
            raise BraidError(f"invalid host state in {path}")
        if not all(isinstance(key, str) and isinstance(value, str) for key, value in links.items()):
            raise BraidError(f"invalid host link state in {path}")
        normalized_hosts[host] = dict(links)
    return State(union=dict(union), hosts=normalized_hosts)


def _write_state(path: Path, state: State) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(json.dumps(state.as_json(), indent=2, sort_keys=True) + "\n")
    os.replace(temporary, path)


def _backup(
    path: Path,
    root: Path,
    category: str,
    result: Result,
    emit: Callable[[str], None],
) -> None:
    backup = root / category / path.name
    backup.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(path), str(backup))
    result.backed_up += 1
    emit(f"BACKUP {path} -> {backup}")


def _remove_owned_link(path: Path, target: Path, platform: str) -> None:
    if path.is_symlink():
        path.unlink()
        return
    if platform == "nt" and path.is_dir() and _points_to(path, target, platform):
        os.rmdir(path)
        return
    raise BraidError(f"refusing to remove changed or unowned path: {path}")


def _sync_links(
    *,
    desired: dict[str, Path],
    previous: dict[str, str],
    destination_root: Path,
    backup_root: Path,
    backup_category: str,
    mode: Mode,
    platform: str,
    result: Result,
    emit: Callable[[str], None],
    preserve_real_sources: bool,
) -> dict[str, str]:
    managed: dict[str, str] = {}

    for name, target in sorted(desired.items()):
        destination = destination_root / name
        if preserve_real_sources and _absolute(destination) == _absolute(target):
            result.current += 1
            continue
        if _points_to(destination, target, platform):
            result.current += 1
            managed[name] = str(target)
            continue

        result.drift += 1
        verb = "MISMATCH" if mode is Mode.CHECK else "WOULD LINK"
        if mode is not Mode.SYNC:
            emit(f"{verb} {destination} -> {target}")
            continue

        destination_root.mkdir(parents=True, exist_ok=True)
        if _present(destination):
            _backup(destination, backup_root, backup_category, result, emit)
        backend = create_directory_link(destination, target, platform=platform)
        result.linked += 1
        managed[name] = str(target)
        emit(f"LINK[{backend}] {destination} -> {target}")

    for name, raw_target in sorted(previous.items()):
        if name in desired:
            continue
        destination = destination_root / name
        if not _present(destination):
            continue
        old_target = Path(raw_target)
        if not _points_to(destination, old_target, platform):
            raise BraidError(f"refusing to clean changed managed path: {destination}")
        result.drift += 1
        verb = "MISMATCH STALE" if mode is Mode.CHECK else "WOULD REMOVE"
        if mode is not Mode.SYNC:
            emit(f"{verb} {destination}")
            continue
        _remove_owned_link(destination, old_target, platform)
        result.removed += 1
        emit(f"REMOVE {destination}")

    return managed


def run(settings: Settings, emit: Callable[[str], None] = print) -> Result:
    inventory = discover_inventory(settings.sources)
    ignored = read_ignored(settings.policy_files)
    state_path = settings.agents_root / ".braid-state.json"
    previous_state = _load_state(state_path)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = f"{timestamp}-{os.getpid()}"
    result = Result()
    union_root = settings.agents_root / "skills"

    union = _sync_links(
        desired=inventory,
        previous=previous_state.union,
        destination_root=union_root,
        backup_root=settings.agents_root / "backups" / suffix,
        backup_category="compose",
        mode=settings.mode,
        platform=settings.platform,
        result=result,
        emit=emit,
        preserve_real_sources=True,
    )

    hosts = dict(previous_state.hosts)
    if settings.project_claude:
        eligible = {name: union_root / name for name in inventory if name not in ignored}
        result.ignored += len(inventory) - len(eligible)
        hosts["claude"] = _sync_links(
            desired=eligible,
            previous=previous_state.hosts.get("claude", {}),
            destination_root=settings.claude_root / "skills",
            backup_root=settings.claude_root / "skills-backup" / suffix,
            backup_category="project",
            mode=settings.mode,
            platform=settings.platform,
            result=result,
            emit=emit,
            preserve_real_sources=False,
        )

    next_state = State(union=union, hosts=hosts)
    if next_state != previous_state and result.drift == 0:
        result.drift += 1
        if settings.mode is not Mode.SYNC:
            emit(f"MISMATCH STATE {state_path}")
    if settings.mode is Mode.SYNC:
        _write_state(state_path, next_state)
    return result


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _deduplicate(paths: Iterable[Path]) -> tuple[Path, ...]:
    result: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        resolved = _resolved(path)
        if resolved not in seen:
            seen.add(resolved)
            result.append(resolved)
    return tuple(result)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="braid",
        description="Compose Agent Skills from multiple repositories and project them to hosts.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="report changes without writing")
    mode.add_argument("--check", action="store_true", help="exit non-zero when links drift")
    parser.add_argument(
        "--source",
        action="append",
        type=Path,
        default=[],
        help="additional repository root or skills directory (repeatable)",
    )
    parser.add_argument("--policy", action="append", type=Path, default=[])
    parser.add_argument("--agents-root", type=Path)
    parser.add_argument("--claude-root", type=Path)
    parser.add_argument("--config-root", type=Path)
    parser.add_argument("--no-claude", action="store_true")
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def main(argv: list[str] | None = None) -> int:
    arguments = _parser().parse_args(argv)
    home = Path.home()
    agents_root = arguments.agents_root or Path(os.environ.get("AGENTS_ROOT", home / ".agents"))
    claude_root = arguments.claude_root or Path(os.environ.get("CLAUDE_ROOT", home / ".claude"))
    config_root = arguments.config_root or Path(
        os.environ.get("AGENT_SKILLS_CONFIG", home / ".config" / "agent-skills")
    )
    repository_root = _repository_root()
    sources: list[Path] = []
    if (repository_root / "skills").is_dir():
        sources.append(repository_root)
    sources.extend(read_configured_sources(config_root))
    sources.extend(arguments.source)
    sources = list(_deduplicate(sources))
    if not sources:
        raise BraidError(
            "no skill sources configured; add a path under "
            f"{config_root / 'sources.d'} or pass --source"
        )

    policy_files: list[Path] = []
    candidates = [
        repository_root / ".braidignore",
        agents_root / ".braidignore",
        config_root / ".braidignore",
    ]
    for source in sources:
        policy_root = source if (source / "skills").is_dir() else source.parent
        candidates.append(policy_root / ".braidignore")
    candidates.extend(arguments.policy)
    policy_files.extend(path for path in _deduplicate(candidates) if path.is_file())

    selected_mode = (
        Mode.CHECK if arguments.check else Mode.DRY_RUN if arguments.dry_run else Mode.SYNC
    )
    settings = Settings(
        sources=tuple(sources),
        agents_root=_resolved(agents_root),
        claude_root=_resolved(claude_root),
        mode=selected_mode,
        policy_files=tuple(policy_files),
        project_claude=not arguments.no_claude,
    )
    result = run(settings)
    change_label = "drift" if selected_mode is Mode.CHECK else "change(s)"
    print(
        "braid: "
        f"{result.linked} linked, {result.current} current, {result.ignored} ignored, "
        f"{result.removed} removed, {result.backed_up} backed up, "
        f"{result.drift} {change_label}"
    )
    if selected_mode is Mode.CHECK and result.drift:
        return 1
    return 0


def entrypoint() -> None:
    try:
        raise SystemExit(main())
    except BraidError as error:
        print(f"braid: {error}", file=sys.stderr)
        raise SystemExit(2) from error


if __name__ == "__main__":
    entrypoint()
