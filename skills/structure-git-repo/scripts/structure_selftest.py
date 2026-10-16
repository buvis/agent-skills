"""Self-test for ``structure_repo``: exercise the library in disposable fixtures.

Invoked by ``structure_repo.py --selftest``. All production code paths come from
``structure_lib``; this module only builds throwaway repositories under a
temporary directory and asserts observable behavior. It never touches a real
checkout.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from structure_lib import (
    check_claude_bridge,
    check_many,
    check_repo,
    discover_repositories,
    inspect_git,
    inspect_repo,
    nested_agents_scopes,
    read_git,
    resolve_target,
    scaffold_repo,
)


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
        # A pointer-only nested AGENTS.md (just an @import + a comment): delegates
        # upward, owns no scope, needs no bridge.
        pointer_scope = nested_repo / "packages/pointer"
        pointer_scope.mkdir(parents=True)
        (pointer_scope / "AGENTS.md").write_text(
            "@AGENTS.md\n\n<!-- pointer only; edit the root -->\n", encoding="utf-8"
        )
        read_git(nested_repo, "add", "--", "packages/pointer/AGENTS.md")
        # A pointer that also carries authored prose IS a scope and must be kept.
        hybrid_scope = nested_repo / "packages/hybrid"
        hybrid_scope.mkdir(parents=True)
        (hybrid_scope / "AGENTS.md").write_text(
            "@AGENTS.md\n\nExtra scope-specific rules live here.\n", encoding="utf-8"
        )
        read_git(nested_repo, "add", "--", "packages/hybrid/AGENTS.md")
        scopes = nested_agents_scopes(nested_repo)
        verify(
            "nested discovery finds maintained scopes only",
            scopes == ["packages/api", "packages/hybrid", "packages/web"],
        )
        verify(
            "nested discovery skips pointer-only AGENTS.md",
            "packages/pointer" not in scopes,
        )
        if os.name != "nt":
            # A symlinked nested AGENTS.md is not an authored scope either.
            link_scope = nested_repo / "packages/linked"
            link_scope.mkdir(parents=True)
            (link_scope / "AGENTS.md").symlink_to("../api/AGENTS.md")
            read_git(nested_repo, "add", "--", "packages/linked/AGENTS.md")
            verify(
                "nested discovery skips symlinked AGENTS.md",
                "packages/linked" not in nested_agents_scopes(nested_repo),
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
            and scanned["nested_scopes"]
            == ["packages/api", "packages/hybrid", "packages/web"]
            and scanned_checks["claude-imports-AGENTS.md@packages/api"] == "PASS"
            and scanned_checks["claude-imports-AGENTS.md@packages/web"] == "FAIL"
            and scanned_checks["claude-imports-AGENTS.md@packages/hybrid"] == "FAIL"
            and "claude-imports-AGENTS.md@packages/pointer" not in scanned_checks
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
                "claude-imports-AGENTS.md@packages/hybrid": "hybrid scope bridge deferred",
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
        # Superseded layout: a tracked legacy path fails migrated-<path> until moved.
        legacy = git_only / "docs/dev/project-management/autopilot/ledger.json"
        legacy.parent.mkdir(parents=True)
        legacy.write_text("{}\n", encoding="utf-8")
        read_git(git_only, "add", "--force", "--", "docs/dev/project-management/autopilot/ledger.json")
        legacy_run = check_repo(git_only)
        legacy_check = next(
            c for c in legacy_run["checks"]
            if c["check"] == "migrated-docs/dev/project-management/autopilot"
        )
        verify(
            "tracked superseded layout fails migrated check",
            legacy_run["structural_gate"] == "FAIL"
            and legacy_check["status"] == "FAIL"
            and "supersedes" in legacy_check["evidence"],
        )
        waived_legacy = check_repo(
            git_only,
            deviations={
                "migrated-docs/dev/project-management/autopilot": "migration group deferred"
            },
        )
        verify(
            "superseded layout waivable as a Fit deviation",
            waived_legacy["structural_gate"] == "PASS",
        )
        read_git(
            git_only, "rm", "--cached", "--",
            "docs/dev/project-management/autopilot/ledger.json",
        )
        verify(
            "untracked superseded layout no longer fails",
            check_repo(git_only)["structural_gate"] == "PASS",
        )
        # Foreign hooks path: an absolute core.hooksPath outside the worktree and
        # its Git dir (a copied/relocated checkout) fails local-hooks-path.
        read_git(git_only, "config", "core.hooksPath", str(base / "elsewhere" / "hooks"))
        foreign_run = check_repo(git_only)
        foreign_check = next(
            c for c in foreign_run["checks"] if c["check"] == "local-hooks-path"
        )
        verify(
            "foreign hooks path fails local-hooks-path",
            foreign_run["structural_gate"] == "FAIL"
            and foreign_check["status"] == "FAIL"
            and foreign_check["evidence"]["foreign_hooks_path"] is not None,
        )
        # A hooks path inside the worktree is local and passes.
        read_git(git_only, "config", "core.hooksPath", str(git_only / ".githooks"))
        verify(
            "worktree-local hooks path passes",
            check_repo(git_only)["structural_gate"] == "PASS",
        )
        read_git(git_only, "config", "--unset", "core.hooksPath")
        verify(
            "cleared hooks path passes",
            check_repo(git_only)["structural_gate"] == "PASS"
            and inspect_git(git_only)["hooks_path_foreign"] is None,
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
        # check-all: discover sibling repositories under a parent and roll up gates.
        portfolio = base / "portfolio"
        portfolio.mkdir()
        passing = portfolio / "passing"
        scaffold_repo(passing, "Passing", "A well-structured repository.", True)
        read_git(passing, "init", "--quiet")
        failing = portfolio / "failing"
        failing.mkdir()
        (failing / "README.md").write_text("# Failing\n\nNo AGENTS.md.\n", encoding="utf-8")
        read_git(failing, "init", "--quiet")
        (portfolio / "not-a-repo").mkdir()
        discovered = discover_repositories([portfolio])
        verify(
            "check-all discovers only worktree children",
            sorted(p.name for p in discovered) == ["failing", "passing"],
        )
        rollup = check_many(discovered)
        gates = {Path(r["target"]).name: r["gate"] for r in rollup["repositories"]}
        verify(
            "check-all rolls up mixed gates to FAIL",
            rollup["rollup_gate"] == "FAIL"
            and gates == {"failing": "FAIL", "passing": "PASS"}
            and rollup["summary"] == {"PASS": 1, "FAIL": 1, "ERROR": 0},
        )
        # A parent of only-passing repositories rolls up to PASS.
        read_git(failing, "init", "--quiet")
        (failing / "AGENTS.md").write_text("# Instructions\n\nScope.\n", encoding="utf-8")
        (failing / "CLAUDE.md").write_text("@AGENTS.md\n", encoding="utf-8")
        verify(
            "check-all rolls up all-pass to PASS",
            check_many(discover_repositories([portfolio]))["rollup_gate"] == "PASS",
        )
        # A root that is itself a worktree is treated as a single target.
        verify(
            "check-all accepts a direct repository root",
            [p.name for p in discover_repositories([passing])] == ["passing"],
        )
    passed = all(result for _, result in results)
    verdict = "DELIVERABLE" if passed else "NOT DELIVERABLE"
    print(f"{verdict}: helper self-test only ({len(results)} checks)")
    return 0 if passed else 1
