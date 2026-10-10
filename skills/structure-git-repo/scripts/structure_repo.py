#!/usr/bin/env python3
"""Inspect repositories, seed an empty one, and check a small structural subset."""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
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
    status = read_git(
        root, "status", "--porcelain=v1", "-z", "--untracked-files=normal", git_dir=git_dir
    )
    entries = status.rstrip("\0").split("\0") if status else []
    return {
        "kind": "worktree",
        "root": str(root),
        "git_dir": str(resolved_git_dir),
        "explicit_worktree": git_dir is not None,
        "hooks_path_config": hooks.stdout.strip() if hooks.returncode == 0 else None,
        "status_porcelain_v1_tokens": entries[:LIMIT],
        "status_truncated": len(entries) > LIMIT,
    }


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
    text = re.sub(r"<!--.*?-->", "", bridge.read_text(encoding="utf-8"), flags=re.DOTALL)
    fence = ""
    for line in text.splitlines():
        if fence:
            if re.fullmatch(
                r" {0,3}" + re.escape(fence[0]) + "{" + str(len(fence)) + r",}\s*", line
            ):
                fence = ""
            continue
        match = re.match(r" {0,3}(`{3,}|~{3,})", line)
        if match:
            fence = match.group(1)
        elif re.fullmatch(r" {0,3}@(?:\./)?AGENTS\.md[ \t]*", line):
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
    check.
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
        for name in ("docs/dev/tmp", ".agents/autopilot/runtime"):
            tracked = read_git(
                target, "ls-files", "-z", "--", f":(top,literal){name}", git_dir=git_dir
            )
            entries = tracked.rstrip("\0").split("\0") if tracked else []
            record(
                f"untracked-{name}", not entries, {"count": len(entries), "paths": entries[:LIMIT]}
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
            "Checks core docs, Git boundary, tracked scratch/runtime, known links and shim modes.",
            "Without --nested, checks the root Claude bridge only. With --nested, also checks each "
            "tracked maintained nested AGENTS.md scope, excluding ignored/untracked scratch "
            "(including docs/dev/tmp), vendored/generated trees and fixtures; it reports gaps and "
            "never writes a nested bridge.",
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


def run_selftest() -> int:
    """Exercise the helper in disposable repositories; never touch a real checkout."""
    results: list[tuple[str, bool]] = []

    def verify(name: str, passed: bool) -> None:
        results.append((name, passed))
        print(f"{'PASS' if passed else 'FAIL'} {name}")

    def expect_refusal(name: str, target: Path) -> None:
        try:
            scaffold_repo(target, "Example", "Store project notes.", True)
        except ValueError:
            verify(name, True)
        else:
            verify(name, False)

    with tempfile.TemporaryDirectory(prefix="structure-repo-selftest-") as directory:
        base = Path(directory).resolve()
        target = base / "example"
        preview = scaffold_repo(target, "Example", "Store project notes.", False)
        verify("preview writes nothing", not target.exists() and len(preview["would_create"]) == 3)
        verify("nonexistent inventory", inspect_repo(target)["git"]["kind"] == "none")
        scaffold_repo(target, "Example", "Store project notes.", True)
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in target.iterdir()}
        repeated = scaffold_repo(target, "Example", "Store project notes.", True)
        after = {p.name: (p.read_bytes(), p.stat().st_mtime_ns) for p in target.iterdir()}
        verify(
            "identical seed preserves bytes and mtime",
            before == after and repeated["status"] == "UNCHANGED",
        )
        verify("check requires Git", check_repo(target)["structural_gate"] == "FAIL")
        (target / "README.md").write_text("Existing purpose\n", encoding="utf-8")
        expect_refusal("preserve conflicting seed", target)
        verify(
            "conflicting bytes unchanged",
            (target / "README.md").read_text() == "Existing purpose\n",
        )
        existing = base / "existing"
        existing.mkdir()
        (existing / "project.txt").write_text("Existing content", encoding="utf-8")
        expect_refusal("reject existing project", existing)
        read_git(target, "init", "--quiet")
        index = Path(read_git(target, "rev-parse", "--git-path", "index").strip())
        if not index.is_absolute():
            index = target / index
        read_git(target, "add", "--", "README.md")
        index_before = index.read_bytes()
        inspect_repo(target)
        verify("minimal Git repository passes", check_repo(target)["structural_gate"] == "PASS")
        verify("inspect/check preserve index", index.read_bytes() == index_before)
        expect_refusal("reject nested target", target / "child")
        git_only = base / "git-only"
        git_only.mkdir()
        read_git(git_only, "init", "--quiet")
        scaffold_repo(git_only, "Example", "Store project notes.", True)
        verify("seed Git-only checkout", check_repo(git_only)["structural_gate"] == "PASS")
        claude_target = base / "claude-example"
        preview = scaffold_repo(claude_target, "Example", "Store project notes.", False)
        verify(
            "Claude preview includes bridge without writes",
            not claude_target.exists() and "CLAUDE.md" in preview["would_create"],
        )
        scaffold_repo(claude_target, "Example", "Store project notes.", True)
        read_git(claude_target, "init", "--quiet")
        bridge = claude_target / "CLAUDE.md"
        verify(
            "Claude scaffold passes bridge check",
            bridge.read_bytes() == b"@AGENTS.md\n"
            and check_repo(claude_target)["structural_gate"] == "PASS",
        )
        before_bridge = (bridge.read_bytes(), bridge.stat().st_mtime_ns)
        repeated = scaffold_repo(claude_target, "Example", "Store project notes.", True)
        verify(
            "Claude scaffold preserves existing bridge",
            repeated["status"] == "UNCHANGED"
            and before_bridge == (bridge.read_bytes(), bridge.stat().st_mtime_ns),
        )
        bridge.unlink()
        verify(
            "default check rejects missing Claude bridge",
            check_repo(claude_target)["structural_gate"] == "FAIL",
        )
        waived = check_repo(
            claude_target, deviations={"claude-imports-AGENTS.md": "native plugin CLAUDE.md"}
        )
        waived_check = next(
            c for c in waived["checks"] if c["check"] == "claude-imports-AGENTS.md"
        )
        verify(
            "accepted deviation clears gate without a PASS",
            waived["structural_gate"] == "PASS"
            and waived_check["status"] == "DEVIATION"
            and waived["deviations"] == {"claude-imports-AGENTS.md": "native plugin CLAUDE.md"},
        )
        verify(
            "deviation preserves the underlying failure evidence",
            "would_fail" in waived_check["evidence"]
            and waived_check["evidence"]["deviation_reason"] == "native plugin CLAUDE.md",
        )
        try:
            check_repo(claude_target, deviations={"nonexistent-check": "typo"})
        except ValueError:
            verify("reject deviation naming an unknown check", True)
        else:
            verify("reject deviation naming an unknown check", False)
        read_git(claude_target, "init", "--quiet")
        read_git(claude_target, "add", "--", "README.md")
        try:
            check_repo(claude_target, deviations={"nonempty-README.md": "no reason to waive"})
        except ValueError:
            verify("reject deviation on a passing check", True)
        else:
            verify("reject deviation on a passing check", False)
        # Not-applicable: a repo that never adopted the AGENTS.md convention.
        no_agents = base / "no-agents"
        no_agents.mkdir()
        (no_agents / "README.md").write_text("# Infra\n\nGitOps cluster config.\n", encoding="utf-8")
        read_git(no_agents, "init", "--quiet")
        read_git(no_agents, "add", "--", "README.md")
        verify(
            "no-AGENTS repo fails the gate by default",
            check_repo(no_agents)["structural_gate"] == "FAIL",
        )
        na = check_repo(
            no_agents,
            not_applicable={
                "nonempty-AGENTS.md": "no agent-instructions convention here",
                "claude-imports-AGENTS.md": "no AGENTS.md to import",
            },
        )
        na_checks = {c["check"]: c for c in na["checks"]}
        verify(
            "declared not-applicable clears the gate",
            na["structural_gate"] == "PASS"
            and na_checks["nonempty-AGENTS.md"]["status"] == "NOT-APPLICABLE"
            and na_checks["claude-imports-AGENTS.md"]["status"] == "NOT-APPLICABLE"
            and set(na["not_applicable"]) == {"nonempty-AGENTS.md", "claude-imports-AGENTS.md"},
        )
        verify(
            "not-applicable preserves the underlying failure evidence",
            "would_fail" in na_checks["nonempty-AGENTS.md"]["evidence"]
            and na_checks["nonempty-AGENTS.md"]["evidence"]["not_applicable_reason"]
            == "no agent-instructions convention here",
        )
        # N/A must not hide a real defect: tracked scratch still fails even when
        # the AGENTS.md checks are excused.
        scratch = no_agents / "docs/dev/tmp/note.txt"
        scratch.parent.mkdir(parents=True)
        scratch.write_text("x\n", encoding="utf-8")
        read_git(no_agents, "add", "--force", "--", "docs/dev/tmp/note.txt")
        guarded = check_repo(
            no_agents,
            not_applicable={
                "nonempty-AGENTS.md": "no convention",
                "claude-imports-AGENTS.md": "no AGENTS.md",
            },
        )
        verify(
            "not-applicable cannot mask an unrelated FAIL",
            guarded["structural_gate"] == "FAIL",
        )
        read_git(no_agents, "rm", "--cached", "--", "docs/dev/tmp/note.txt")
        # A repo that DID adopt the convention cannot excuse its missing bridge as N/A
        # on the bridge alone while AGENTS.md is present and the bridge is absent:
        # that is still a real FAIL unless explicitly excused, which the operator may
        # do, but excusing a passing/absent-reason check is refused.
        try:
            check_repo(
                no_agents, not_applicable={"nonempty-README.md": "README is present and valid"}
            )
        except ValueError:
            verify("reject not-applicable on a passing check", True)
        else:
            verify("reject not-applicable on a passing check", False)
        try:
            check_repo(no_agents, not_applicable={"nonexistent-check": "typo"})
        except ValueError:
            verify("reject not-applicable naming an unknown check", True)
        else:
            verify("reject not-applicable naming an unknown check", False)
        try:
            check_repo(
                no_agents,
                deviations={"claude-imports-AGENTS.md": "x"},
                not_applicable={"claude-imports-AGENTS.md": "y"},
            )
        except ValueError:
            verify("reject a check marked both deviation and not-applicable", True)
        else:
            verify("reject a check marked both deviation and not-applicable", False)
        # Nested-scope scan (--nested): discover maintained nested AGENTS.md,
        # exclude scratch/untracked, report bridge gaps, write nothing.
        nested_repo = base / "nested"
        scaffold_repo(nested_repo, "Nested", "Exercise nested scopes.", True)
        read_git(nested_repo, "init", "--quiet")
        read_git(nested_repo, "add", "--", "README.md", "AGENTS.md", "CLAUDE.md")
        # A maintained nested scope WITH a bridge.
        good = nested_repo / "packages/api"
        good.mkdir(parents=True)
        (good / "AGENTS.md").write_text("# API\n\nScope instructions.\n", encoding="utf-8")
        (good / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
        # A maintained nested scope WITHOUT a bridge.
        bad = nested_repo / "packages/web"
        bad.mkdir(parents=True)
        (bad / "AGENTS.md").write_text("# Web\n\nScope instructions.\n", encoding="utf-8")
        # A nested AGENTS.md under scratch: must be excluded even if tracked.
        scratch_scope = nested_repo / "docs/dev/tmp/worktrees/wt1"
        scratch_scope.mkdir(parents=True)
        (scratch_scope / "AGENTS.md").write_text("# Scratch\n", encoding="utf-8")
        read_git(
            nested_repo,
            "add",
            "--",
            "packages/api/AGENTS.md",
            "packages/api/CLAUDE.md",
            "packages/web/AGENTS.md",
        )
        read_git(nested_repo, "add", "--force", "--", "docs/dev/tmp/worktrees/wt1/AGENTS.md")
        # An UNTRACKED nested AGENTS.md: must be excluded by tracked-only discovery.
        untracked_scope = nested_repo / "packages/experimental"
        untracked_scope.mkdir(parents=True)
        (untracked_scope / "AGENTS.md").write_text("# Experimental\n", encoding="utf-8")
        scopes = nested_agents_scopes(nested_repo)
        verify(
            "nested discovery finds maintained scopes only",
            scopes == ["packages/api", "packages/web"],
        )
        default_run = check_repo(nested_repo)
        verify(
            "nested scopes ignored without --nested",
            default_run["nested_scanned"] is False
            and not any("@" in c["check"] for c in default_run["checks"]),
        )
        scanned = check_repo(nested_repo, nested=True)
        scanned_checks = {c["check"]: c["status"] for c in scanned["checks"]}
        verify(
            "nested scan reports bridged scope PASS and unbridged scope FAIL",
            scanned["nested_scanned"] is True
            and scanned["nested_scopes"] == ["packages/api", "packages/web"]
            and scanned_checks["claude-imports-AGENTS.md@packages/api"] == "PASS"
            and scanned_checks["claude-imports-AGENTS.md@packages/web"] == "FAIL"
            and scanned["structural_gate"] == "FAIL",
        )
        verify(
            "nested scan excludes scratch and untracked scopes",
            not any(
                "docs/dev/tmp" in c or "experimental" in c
                for c in scanned_checks
                if "@" in c
            ),
        )
        before_web = (bad / "AGENTS.md").read_bytes()
        verify(
            "nested scan writes no nested bridge",
            not (bad / "CLAUDE.md").exists() and (bad / "AGENTS.md").read_bytes() == before_web,
        )
        # The fixture tracks a scratch AGENTS.md on purpose (to exercise segment
        # exclusion), so untracked-docs/dev/tmp fails independently; waive it too
        # to confirm nested waivers resolve and the gate then clears.
        waived_nested = check_repo(
            nested_repo,
            nested=True,
            not_applicable={
                "claude-imports-AGENTS.md@packages/web": "web scope documented, bridge deferred",
                "untracked-docs/dev/tmp": "fixture tracks scratch to test exclusion",
            },
        )
        web_status = next(
            c["status"]
            for c in waived_nested["checks"]
            if c["check"] == "claude-imports-AGENTS.md@packages/web"
        )
        verify(
            "waivers apply to nested check names",
            waived_nested["structural_gate"] == "PASS"
            and web_status == "NOT-APPLICABLE"
            and "claude-imports-AGENTS.md@packages/web" in waived_nested["not_applicable"],
        )
        for label, content in (
            ("prose", "Read AGENTS.md before working.\n"),
            ("inline code", "`@AGENTS.md`\n"),
            ("fenced code", "```text\n@AGENTS.md\n```\n"),
            ("tilde fence", "~~~text\n@AGENTS.md\n~~~\n"),
            ("indented code", "    @AGENTS.md\n"),
            ("comment", "<!--\n@AGENTS.md\n-->\n"),
            ("wrong target", "@missing.md\n"),
        ):
            bridge.write_text(content, encoding="utf-8")
            verify(f"reject {label} as Claude import", not check_claude_bridge(claude_target)[0])
        bridge.write_text("```text\nExample\n```\n@AGENTS.md\n", encoding="utf-8")
        verify("accept active import after closed fence", check_claude_bridge(claude_target)[0])
        native_content = "@./AGENTS.md\n\nKeep these Claude-specific instructions.\n"
        bridge.write_text(native_content, encoding="utf-8")
        before_bridge = (bridge.read_bytes(), bridge.stat().st_mtime_ns)
        verify("accept import with native instructions", check_claude_bridge(claude_target)[0])
        try:
            scaffold_repo(claude_target, "Example", "Store project notes.", True)
        except ValueError:
            verify("refuse replacement of authored Claude content", True)
        else:
            verify("refuse replacement of authored Claude content", False)
        verify(
            "check and refused scaffold preserve native instructions",
            before_bridge == (bridge.read_bytes(), bridge.stat().st_mtime_ns),
        )
        if os.name != "nt":
            bridge.unlink()
            bridge.symlink_to("AGENTS.md")
            verify("accept existing direct Claude symlink", check_claude_bridge(claude_target)[0])
            bridge.unlink()
            bridge.symlink_to("README.md")
            verify(
                "reject Claude symlink to wrong target", not check_claude_bridge(claude_target)[0]
            )
        for relative in ("docs/dev/tmp/note.txt", ".agents/autopilot/runtime/state.json"):
            path = git_only / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("Retain until inspected", encoding="utf-8")
            read_git(git_only, "add", "--force", "--", relative)
        verify("reject tracked scratch/runtime", check_repo(git_only)["structural_gate"] == "FAIL")
        read_git(
            git_only,
            "rm",
            "--cached",
            "--",
            "docs/dev/tmp/note.txt",
            ".agents/autopilot/runtime/state.json",
        )
        verify(
            "untracked scratch/runtime accepted", check_repo(git_only)["structural_gate"] == "PASS"
        )
        shim = git_only / "tools/check"
        shim.parent.mkdir()
        shim.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        if os.name != "nt":
            verify("reject nonexecutable shim", check_repo(git_only)["structural_gate"] == "FAIL")
        shim.chmod(0o755)
        verify("accept executable shim", check_repo(git_only)["structural_gate"] == "PASS")
        if os.name != "nt":
            link = git_only / ".kiro/specs"
            link.parent.mkdir()
            link.symlink_to("../missing-specs")
            verify("detect dangling known link", check_repo(git_only)["structural_gate"] == "FAIL")
            alias = base / "alias"
            alias.symlink_to(target, target_is_directory=True)
            try:
                resolve_target(str(alias))
            except ValueError:
                verify("reject target symlink", True)
            else:
                verify("reject target symlink", False)
        bare = base / "bare.git"
        read_git(base, "init", "--quiet", "--bare", str(bare))
        expect_refusal("reject bare repository", bare)
        dotfiles = base / "dotfiles"
        scaffold_repo(dotfiles, "Dotfiles", "Maintain shell configuration.", True)
        read_git(dotfiles, "add", "--", "README.md", git_dir=bare)
        verify(
            "accept explicitly selected bare-backed worktree",
            check_repo(dotfiles, bare)["structural_gate"] == "PASS",
        )
        verify(
            "explicit Git directory selects the correct index",
            read_git(dotfiles, "ls-files", "--", ":(top)README.md", git_dir=bare).strip()
            == "README.md",
        )
        # A commit is necessary for Git's disposable linked-worktree fixture only.
        read_git(
            target,
            "-c",
            "core.hooksPath=" + str(base / "no-hooks"),
            "-c",
            "commit.gpgSign=false",
            "-c",
            "user.name=Fixture",
            "-c",
            "user.email=fixture@example.invalid",
            "commit",
            "--quiet",
            "--allow-empty",
            "-m",
            "Initialize fixture",
        )
        worktree = base / "worktree"
        read_git(
            target,
            "-c",
            "core.hooksPath=" + str(base / "no-hooks"),
            "worktree",
            "add",
            "--quiet",
            "--detach",
            str(worktree),
        )
        verify(
            "recognize linked-worktree .git file",
            inspect_git(worktree)["kind"] == "worktree" and (worktree / ".git").is_file(),
        )
    passed = all(result for _, result in results)
    verdict = "DELIVERABLE" if passed else "NOT DELIVERABLE"
    print(f"{verdict}: helper self-test only ({len(results)} checks)")
    return 0 if passed else 1


def run_main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true", help="exercise disposable fixtures")
    commands = parser.add_subparsers(dest="command")
    for name in ("inspect", "check", "scaffold"):
        command = commands.add_parser(name)
        command.add_argument("target", help="repository path")
        if name in ("inspect", "check"):
            command.add_argument(
                "--git-dir", help="explicit Git directory for a bare-backed worktree"
            )
        if name == "check":
            command.add_argument(
                "--deviation",
                action="append",
                default=[],
                metavar="CHECK=REASON",
                help="waive one failing check as a Fit deviation; repeatable",
            )
            command.add_argument(
                "--not-applicable",
                action="append",
                default=[],
                metavar="CHECK=REASON",
                dest="not_applicable",
                help="mark one failing check out of scope for this repo kind; repeatable",
            )
            command.add_argument(
                "--nested",
                action="store_true",
                help="also check the Claude bridge for each maintained nested AGENTS.md scope",
            )
        if name == "scaffold":
            command.add_argument("--name", required=True)
            command.add_argument("--purpose", required=True)
            command.add_argument(
                "--apply", action="store_true", help="write the seed; default previews"
            )
    args = parser.parse_args()
    try:
        if args.selftest:
            if args.command:
                parser.error("--selftest cannot be combined with a repository command")
            return run_selftest()
        if not args.command:
            parser.error("select inspect, check or scaffold, or use --selftest")
        target = resolve_target(args.target)
        selected_git_dir = getattr(args, "git_dir", None)
        git_dir = Path(selected_git_dir).expanduser().resolve() if selected_git_dir else None
        if args.command == "inspect":
            result = inspect_repo(target, git_dir)
        elif args.command == "check":
            def parse_waivers(items: list[str], label: str) -> dict[str, str]:
                parsed: dict[str, str] = {}
                for item in items:
                    key, sep, reason = item.partition("=")
                    key, reason = key.strip(), reason.strip()
                    if not sep or not key or not reason:
                        raise ValueError(f"Use --{label} CHECK=REASON with a nonempty reason: {item}")
                    if key in parsed:
                        raise ValueError(f"Duplicate {label} for check: {key}")
                    parsed[key] = reason
                return parsed

            deviations = parse_waivers(getattr(args, "deviation", []), "deviation")
            not_applicable = parse_waivers(getattr(args, "not_applicable", []), "not-applicable")
            result = check_repo(
                target, git_dir, deviations, not_applicable, getattr(args, "nested", False)
            )
        else:
            result = scaffold_repo(target, args.name, args.purpose, args.apply)
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 1 if result.get("structural_gate") == "FAIL" else 0
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"status": "ERROR", "error": str(error)}, ensure_ascii=True))
        return 2


if __name__ == "__main__":
    sys.exit(run_main())
