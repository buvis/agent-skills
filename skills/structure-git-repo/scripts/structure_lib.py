"""Production logic for inspecting, scaffolding and checking repositories.

This module holds every production function and constant used by the
``structure_repo.py`` CLI entry point and exercised by ``structure_selftest.py``.
Keeping the logic here (and the CLI/self-test thin) lets the self-test import the
same code paths the CLI runs, without the test fixtures bloating the entry point.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

PUBLIC_COMMANDS = ("onboard", "check", "format", "run-tests", "build", "develop", "release")
KNOWN_PATHS = (
    "README.md",
    "AGENTS.md",
    "CLAUDE.md",
    ".claude/CLAUDE.md",
    "mise.toml",
    ".mise.toml",
    "tools",
    "dev/bin",
    "dev/local",
    "docs/dev",
    "docs/dev/project-management",
    "docs/dev/tmp",
    ".agents/skills",
    ".agents/specflow.json",
    ".agents/autopilot/runtime",
    ".agents/autopilot/records",
    ".claude/skills",
    ".codex/skills",
    ".github/skills",
    ".kiro/skills",
    ".kiro/specs",
)
LIMIT = 100
# Path segments whose subtree never holds a *maintained* nested AGENTS.md scope:
# disposable scratch, vendored/generated trees, and test fixtures. Tracked-only
# discovery already drops ignored/untracked scratch; this is a defensive second
# layer for repositories that mistakenly track such content.
NESTED_SCOPE_EXCLUDES = (
    "docs/dev/tmp",
    "node_modules",
    "vendor",
    "third_party",
    ".venv",
    "fixtures",
    "testdata",
)
# Superseded locations the target structure migrates away from. A restructure is
# not finished while these are still *tracked*: the content must move to its new
# home (verb-named tools/, .agents/autopilot/records + ignored runtime, specs under
# project-management/). Each maps a tracked legacy path to the structure note that
# supersedes it. The check is tracked-only, so ignored/untracked scratch left on
# disk never trips it; only committed legacy layout counts as unfinished migration.
LEGACY_PATHS: tuple[tuple[str, str], ...] = (
    ("dev/bin", "retired in favor of tools/ with its callers (layout.md)"),
    ("dev/local", "classify into tracked intake/specs instead of a dev/work bucket"),
    (
        "docs/dev/project-management/autopilot",
        "Autopilot records -> .agents/autopilot/records; runtime -> ignored "
        ".agents/autopilot/runtime (layout.md Workflow storage)",
    ),
    (
        "docs/dev/project-management/prds",
        "PRD buckets retire into intake/ and specs/ (layout.md)",
    ),
    (
        "docs/dev/project-management/runs",
        "no runs/ category; use reviews/ by scope linked to records (layout.md)",
    ),
)


def run_git(
    root: Path, *args: str, git_dir: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Ignore inherited repository overrides and avoid refreshing the index."""
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_OPTIONAL_LOCKS="0", LC_ALL="C")
    identity = [f"--git-dir={git_dir}", f"--work-tree={root}"] if git_dir else []
    return subprocess.run(
        ["git", *identity, "-c", "core.fsmonitor=false", "-C", str(root), *args],
        env=env,
        capture_output=True,
        text=True,
        errors="surrogateescape",
        timeout=30,
        check=False,
    )


def read_git(root: Path, *args: str, git_dir: Path | None = None) -> str:
    result = run_git(root, *args, git_dir=git_dir)
    if result.returncode:
        raise ValueError(result.stderr.strip() or "Git command failed")
    return result.stdout


def resolve_target(value: str) -> Path:
    target = Path(value).expanduser().absolute()
    if target.is_symlink():
        raise ValueError("Select the actual repository path, not a symlink to it")
    target = target.resolve()
    if target.exists() and not target.is_dir():
        raise ValueError("Target must be a directory")
    return target


def inspect_git(target: Path, git_dir: Path | None = None) -> dict[str, Any]:
    if git_dir is not None and (not target.is_dir() or not git_dir.is_dir()):
        raise ValueError("Explicit Git directory and worktree must both exist")
    anchor = target
    while not anchor.exists():
        anchor = anchor.parent
    result = run_git(anchor, "rev-parse", "--is-bare-repository", git_dir=git_dir)
    if result.returncode:
        if "not a git repository" in result.stderr.lower():
            if git_dir or (anchor / ".git").exists() or (anchor / ".git").is_symlink():
                raise ValueError("Git metadata exists but Git cannot read this repository")
            return {"kind": "none"}
        raise ValueError(result.stderr.strip() or "Cannot inspect Git repository")
    resolved_git_dir = Path(
        read_git(anchor, "rev-parse", "--absolute-git-dir", git_dir=git_dir).strip()
    ).resolve()
    if result.stdout.strip() == "true":
        return {"kind": "bare", "git_dir": str(resolved_git_dir)}
    root = Path(read_git(anchor, "rev-parse", "--show-toplevel", git_dir=git_dir).strip()).resolve()
    if root != target:
        return {"kind": "parent", "root": str(root), "git_dir": str(resolved_git_dir)}
    hooks = run_git(root, "config", "--get", "core.hooksPath", git_dir=git_dir)
    if hooks.returncode not in (0, 1):
        raise ValueError(hooks.stderr.strip() or "Cannot read hook configuration")
    hooks_path = hooks.stdout.strip() if hooks.returncode == 0 else None
    status = read_git(
        root, "status", "--porcelain=v1", "-z", "--untracked-files=normal", git_dir=git_dir
    )
    entries = status.rstrip("\0").split("\0") if status else []
    return {
        "kind": "worktree",
        "root": str(root),
        "git_dir": str(resolved_git_dir),
        "explicit_worktree": git_dir is not None,
        "hooks_path_config": hooks_path,
        "hooks_path_foreign": foreign_hooks_path(hooks_path, root, resolved_git_dir),
        "status_porcelain_v1_tokens": entries[:LIMIT],
        "status_truncated": len(entries) > LIMIT,
    }


def foreign_hooks_path(hooks_path: str | None, root: Path, git_dir: Path) -> str | None:
    """Flag a core.hooksPath that points outside this worktree and its Git dir.

    A copied or relocated repository keeps the source checkout's absolute
    ``core.hooksPath`` in ``.git/config``. The hooks then run (or silently fail
    to run) from the *original* location, not the one being inspected. A relative
    path, or an absolute path under the current worktree or its Git directory, is
    local and returns ``None``; any other absolute path is reported as the foreign
    location so a move/restructure can repoint or clear it. Resolution does not
    require the path to exist, so a dangling foreign path is still reported.
    """
    if not hooks_path:
        return None
    candidate = Path(hooks_path).expanduser()
    if not candidate.is_absolute():
        return None
    resolved = candidate.resolve()
    for base in (root, git_dir):
        try:
            resolved.relative_to(base.resolve())
            return None
        except ValueError:
            continue
    return str(resolved)


def inspect_path(path: Path) -> dict[str, Any]:
    if path.is_symlink():
        return {"kind": "symlink", "target": os.readlink(path), "broken": not path.exists()}
    if path.is_dir():
        return {"kind": "directory"}
    if path.is_file():
        return {"kind": "file", "bytes": path.stat().st_size}
    return {"kind": "other" if path.exists() else "absent"}


def inspect_repo(target: Path, git_dir: Path | None = None) -> dict[str, Any]:
    names = sorted(path.name for path in target.iterdir()) if target.exists() else []
    return {
        "mode": "inspect",
        "target": str(target),
        "exists": target.exists(),
        "git": inspect_git(target, git_dir),
        "top_level": names[:LIMIT],
        "top_level_truncated": len(names) > LIMIT,
        "paths": {name: inspect_path(target / name) for name in KNOWN_PATHS},
        "scope": "Shallow inventory; inspect manifests, instructions and consumers separately.",
    }


def render_seed(name: str, purpose: str) -> dict[str, str]:
    if not name.strip() or not purpose.strip() or any(c in name + purpose for c in "\r\n\0"):
        raise ValueError("Supply a nonempty, single-line project name and actual purpose")
    return {
        "README.md": f"# {name.strip()}\n\n{purpose.strip()}\n",
        "AGENTS.md": (
            "# Repository instructions\n\n"
            "Read README.md for the project's purpose. Before editing, read applicable\n"
            "nested AGENTS.md files; their instructions apply to their directory trees.\n\n"
            "Keep one authored source for each concern. Preserve native package layouts.\n"
            "Name commands and executable helpers with verbs. Document actual commands\n"
            "and project invariants here as they are introduced.\n"
        ),
        "CLAUDE.md": "@AGENTS.md\n",
    }


def scaffold_repo(target: Path, name: str, purpose: str, apply: bool) -> dict[str, Any]:
    seed = render_seed(name, purpose)
    git = inspect_git(target)
    if git["kind"] in ("bare", "parent"):
        raise ValueError(f"Refusing scaffold in {git['kind']} repository context: {git}")
    names = {path.name for path in target.iterdir()} if target.exists() else set()
    extra = names - {".git", *seed}
    if extra:
        raise ValueError(f"Existing project content requires restructure mode: {sorted(extra)}")
    pending = []
    for name, content in seed.items():
        path = target / name
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise ValueError(f"Conflicting seed path: {name}")
        if path.exists():
            if path.read_bytes() != content.encode("utf-8"):
                raise ValueError(f"Different existing content: {name}; use restructure mode")
        else:
            pending.append(name)
    created: list[str] = []
    if apply:
        target.mkdir(parents=True, exist_ok=True)
        try:
            for name in pending:
                with (target / name).open("x", encoding="utf-8", newline="\n") as stream:
                    created.append(name)
                    stream.write(seed[name])
        except OSError as error:
            raise ValueError(
                f"Partial scaffold; created {created}; inspect before retry: {error}"
            ) from error
    return {
        "mode": "scaffold",
        "target": str(target),
        "status": "APPLIED" if created else "UNCHANGED" if apply else "PLANNED",
        "created": created,
        "would_create": pending if not apply else [],
        "preserved": sorted(set(seed) - set(pending)),
        "git_initialized": False,
        "next": "Initialize Git if absent; tailor commands, docs and integrations to actual scope.",
    }


def has_standalone_import(text: str, target_pattern: str = r"@(?:\./)?[^\s/]+") -> bool:
    """True if an import line (``@target``) sits on its own outside comments/code.

    ``target_pattern`` defaults to any single-token import; pass a specific
    pattern (such as ``@(?:\\./)?AGENTS\\.md``) to require a particular target.
    """
    stripped = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    fence = ""
    for line in stripped.splitlines():
        if fence:
            if re.fullmatch(
                r" {0,3}" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}\s*", line
            ):
                fence = ""
            continue
        match = re.match(r" {0,3}(`{3,}|~{3,})", line)
        if match:
            fence = match.group(1)
        elif re.fullmatch(r" {0,3}" + target_pattern + r"[ \t]*", line):
            return True
    return False


def check_claude_bridge(target: Path) -> tuple[bool, dict[str, Any]]:
    """Recognize an adjacent import or direct symlink; do not simulate host loading."""
    bridge = target / "CLAUDE.md"
    agents = target / "AGENTS.md"
    evidence = {"path": str(bridge), **inspect_path(bridge)}
    if not bridge.is_file() or not agents.is_file() or not agents.read_bytes().strip():
        return False, {**evidence, "reason": "Require readable CLAUDE.md and nonempty AGENTS.md"}
    if bridge.is_symlink():
        valid = bridge.resolve() == agents.resolve()
        return valid, {**evidence, "imports_adjacent_agents": valid}
    if has_standalone_import(bridge.read_text(encoding="utf-8"), r"@(?:\./)?AGENTS\.md"):
        return True, {**evidence, "imports_adjacent_agents": True}
    return False, {
        **evidence,
        "reason": "Add @AGENTS.md on its own line outside comments/code; preserve other content",
    }


def nested_agents_scopes(target: Path, git_dir: Path | None = None) -> list[str]:
    """Tracked, maintained nested AGENTS.md directories relative to the root.

    Discovery is tracked-only (``git ls-files``), so ignored/untracked scratch
    such as disposable worktrees never appears. ``NESTED_SCOPE_EXCLUDES`` is a
    defensive second layer for repositories that mistakenly track scratch,
    vendored or fixture trees. The root AGENTS.md is excluded; it has its own
    check. A nested AGENTS.md that is a symlink, or is itself a pointer whose only
    directive is an ``@import`` line, is not an authored instruction scope and
    needs no adjacent bridge, so it is skipped.
    """
    listed = read_git(
        target, "ls-files", "-z", "--", ":(top)**/AGENTS.md", ":(top)AGENTS.md", git_dir=git_dir
    )
    scopes: list[str] = []
    for rel in sorted(set(listed.rstrip("\0").split("\0")) if listed else set()):
        if not rel or rel == "AGENTS.md":
            continue
        parent = str(Path(rel).parent).replace(os.sep, "/")
        segments = set(parent.split("/"))
        if any(exclude in parent for exclude in NESTED_SCOPE_EXCLUDES) or (
            segments & set(NESTED_SCOPE_EXCLUDES)
        ):
            continue
        agents_path = target / rel
        if agents_path.is_symlink():
            continue
        try:
            body = agents_path.read_text(encoding="utf-8", errors="surrogateescape")
        except OSError:
            continue
        # A pointer-only AGENTS.md (just an @import, with no authored prose beyond
        # comments/blank lines) delegates upward and owns no scope of its own.
        if has_standalone_import(body):
            residue = re.sub(r"<!--.*?-->", "", body, flags=re.DOTALL)
            residue = re.sub(r" {0,3}@(?:\./)?[^\s/]+[ \t]*$", "", residue, flags=re.MULTILINE)
            if not residue.strip():
                continue
        scopes.append(parent)
    return scopes


def check_repo(
    target: Path,
    git_dir: Path | None = None,
    deviations: dict[str, str] | None = None,
    not_applicable: dict[str, str] | None = None,
    nested: bool = False,
) -> dict[str, Any]:
    accepted = dict(deviations or {})
    excused = dict(not_applicable or {})
    both = sorted(set(accepted) & set(excused))
    if both:
        raise ValueError(f"A check cannot be both a deviation and not-applicable: {both}")
    applied: dict[str, str] = {}
    skipped: dict[str, str] = {}
    checks: list[dict[str, Any]] = []

    def record(name: str, passed: bool, evidence: Any) -> None:
        status = "PASS" if passed else "FAIL"
        if status == "FAIL" and name in accepted:
            status = "DEVIATION"
            applied[name] = accepted[name]
            evidence = {"deviation_reason": accepted[name], "would_fail": evidence}
        elif status == "FAIL" and name in excused:
            status = "NOT-APPLICABLE"
            skipped[name] = excused[name]
            evidence = {"not_applicable_reason": excused[name], "would_fail": evidence}
        checks.append({"check": name, "status": status, "evidence": evidence})

    git = inspect_git(target, git_dir)
    record("own-git-worktree", git["kind"] == "worktree", git)
    for name in ("README.md", "AGENTS.md"):
        path = target / name
        valid = path.is_file() and bool(path.read_bytes().strip())
        record(f"nonempty-{name}", valid, inspect_path(path))
    valid, evidence = check_claude_bridge(target)
    record("claude-imports-AGENTS.md", valid, evidence)
    scanned_scopes: list[str] = []
    if nested and git["kind"] == "worktree":
        scanned_scopes = nested_agents_scopes(target, git_dir)
        for scope in scanned_scopes:
            scope_valid, scope_evidence = check_claude_bridge(target / scope)
            record(f"claude-imports-AGENTS.md@{scope}", scope_valid, scope_evidence)
    if git["kind"] == "worktree":
        record(
            "local-hooks-path",
            git.get("hooks_path_foreign") is None,
            {
                "hooks_path_config": git.get("hooks_path_config"),
                "foreign_hooks_path": git.get("hooks_path_foreign"),
            },
        )
        for name in ("docs/dev/tmp", ".agents/autopilot/runtime"):
            tracked = read_git(
                target, "ls-files", "-z", "--", f":(top,literal){name}", git_dir=git_dir
            )
            entries = tracked.rstrip("\0").split("\0") if tracked else []
            record(
                f"untracked-{name}", not entries, {"count": len(entries), "paths": entries[:LIMIT]}
            )
        for name, supersedes in LEGACY_PATHS:
            tracked = read_git(
                target, "ls-files", "-z", "--", f":(top,literal){name}", git_dir=git_dir
            )
            entries = tracked.rstrip("\0").split("\0") if tracked else []
            record(
                f"migrated-{name}",
                not entries,
                {"supersedes": supersedes, "count": len(entries), "paths": entries[:LIMIT]},
            )
    for name in KNOWN_PATHS:
        path = target / name
        if path.is_symlink():
            record(f"resolves-{name}", path.exists(), inspect_path(path))
    for name in PUBLIC_COMMANDS:
        path = target / "tools" / name
        if path.exists() or path.is_symlink():
            valid = path.is_file() and (os.name == "nt" or os.access(path, os.X_OK))
            record(f"executable-tools/{name}", valid, inspect_path(path))
    unused_dev = sorted(set(accepted) - set(applied))
    unused_na = sorted(set(excused) - set(skipped))
    if unused_dev or unused_na:
        checked = sorted(c["check"] for c in checks)
        parts = []
        if unused_dev:
            parts.append(f"deviations that did not apply: {unused_dev}")
        if unused_na:
            parts.append(f"not-applicable waivers that did not apply: {unused_na}")
        raise ValueError(
            "A waiver must match a check that fails without it; "
            + "; ".join(parts)
            + f". Observed checks: {checked}"
        )
    gate_fail = any(c["status"] == "FAIL" for c in checks)
    return {
        "mode": "check",
        "target": str(target),
        "structural_gate": "FAIL" if gate_fail else "PASS",
        "checks": checks,
        "deviations": applied,
        "not_applicable": skipped,
        "nested_scanned": nested,
        "nested_scopes": scanned_scopes,
        "limitations": [
            "Checks core docs, Git boundary, tracked scratch/runtime, superseded layout, known "
            "links and shim modes.",
            "Without --nested, checks the root Claude bridge only. With --nested, also checks each "
            "tracked maintained nested AGENTS.md scope, excluding ignored/untracked scratch "
            "(including docs/dev/tmp), vendored/generated trees and fixtures; it reports gaps and "
            "never writes a nested bridge.",
            "local-hooks-path fails when core.hooksPath is an absolute path outside this worktree "
            "and its Git dir (a copied/relocated checkout pointing at the source). It does not "
            "prove hooks are installed or run, only that the configured path is local.",
            "migrated-<path> fails while a superseded layout is still tracked; it does not verify "
            "the content reached its new home, only that the old location is no longer committed.",
            "Import checks do not prove host loading under the session's settings/exclusions.",
            "No task/hook/release execution or approval/path-consumer validation.",
            "DEVIATION marks a FAIL waived under Fit; it does not fail the gate but is not a PASS.",
            "NOT-APPLICABLE marks a FAIL the operator declared out of scope for this repo kind "
            "(for example, no AGENTS.md so no bridge applies); it never auto-infers and must be "
            "requested per check, so it cannot silently hide a defect.",
            "A PASS gate is structural only: it is not evidence that hooks, releases, host "
            "instruction loading or workflow recovery actually work. COMPLETE still requires the "
            "mode reference's operational evidence.",
        ],
    }


def check_many(
    targets: list[Path],
    nested: bool = False,
) -> dict[str, Any]:
    """Walk several repositories and roll up their structural gates.

    Each target runs through ``check_repo`` with no waivers: a portfolio sweep is
    a readable signal, so every deviation/not-applicable is a per-repository
    judgement made in a focused run, never applied in bulk here. A target that
    errors (not a repository, unreadable Git) is recorded as ERROR rather than
    aborting the sweep. The roll-up gate FAILs if any repository FAILs or ERRORs.
    """
    repositories: list[dict[str, Any]] = []
    counts = {"PASS": 0, "FAIL": 0, "ERROR": 0}
    for target in targets:
        entry: dict[str, Any] = {"target": str(target)}
        try:
            result = check_repo(target, nested=nested)
            gate = result["structural_gate"]
            entry["gate"] = gate
            entry["failed_checks"] = [
                c["check"] for c in result["checks"] if c["status"] == "FAIL"
            ]
            counts[gate] += 1
        except (OSError, ValueError, subprocess.TimeoutExpired) as error:
            entry["gate"] = "ERROR"
            entry["error"] = str(error)
            counts["ERROR"] += 1
        repositories.append(entry)
    return {
        "mode": "check-all",
        "count": len(repositories),
        "summary": counts,
        "rollup_gate": "FAIL" if (counts["FAIL"] or counts["ERROR"]) else "PASS",
        "repositories": repositories,
        "nested_scanned": nested,
        "limitations": [
            "A portfolio roll-up applies no waivers; mark a per-repository DEVIATION or "
            "NOT-APPLICABLE in a focused `check` run, not in bulk.",
            "FAIL counts both structural failures and repositories that errored (not a "
            "repository, unreadable Git).",
            "Each repository carries the same structural-only caveats as a single `check`.",
        ],
    }


def discover_repositories(roots: list[Path]) -> list[Path]:
    """Return immediate child directories under each root that are Git worktrees.

    A portfolio lives as sibling checkouts under one or more parent directories
    (``check-all PARENT``). Only direct children are considered, each kept when it
    is its own worktree root; nested, bare and parent-identified directories are
    skipped so the sweep never recurses into a repository's internals. A root that
    is itself a worktree is returned as a single target.
    """
    discovered: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        try:
            if inspect_git(root)["kind"] == "worktree":
                discovered.append(root)
                continue
        except (OSError, ValueError, subprocess.TimeoutExpired):
            pass
        for child in sorted(root.iterdir()):
            if not child.is_dir() or child.is_symlink():
                continue
            try:
                if inspect_git(child)["kind"] == "worktree":
                    discovered.append(child)
            except (OSError, ValueError, subprocess.TimeoutExpired):
                continue
    return discovered
