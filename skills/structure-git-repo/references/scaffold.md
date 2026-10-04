# Scaffold an empty repository

## Seed the common core

Use the helper on a nonexistent/empty directory or a checkout containing only .git.
It previews by default; --apply writes README.md, AGENTS.md and a real CLAUDE.md
containing only `@AGENTS.md`, without overwriting. The bridge is part of the default
seed and check; no host flag, installed Claude or follow-up question is needed.
Supply the actual project purpose, not a placeholder. It does not initialize Git,
install software, select a language, or create speculative tasks/directories.

```bash
python3 ~/.agents/skills/structure-git-repo/scripts/structure_repo.py scaffold /path/to/repo --name example --purpose "Describe the actual project purpose."
python3 ~/.agents/skills/structure-git-repo/scripts/structure_repo.py scaffold /path/to/repo --name example --purpose "Describe the actual project purpose." --apply
```

The purpose string above illustrates the argument, not text to ship. Repeating an
identical seed preserves existing bytes; any different existing content is a conflict.
For existing project material use restructure mode. Never delete files to make a
repository qualify as empty. Reject an accidental nested repository target; a Git
worktree's .git file is valid when Git identifies it as its own worktree root.

For a requested new Git repository without Git metadata, initialize it at this exact
target using Git. Do not change an existing repository's branches/remotes. Resolve
the default branch from the user's conventions; no remote publication is implied.

## Tailor useful content

1. Add native language/package structure only for the stated project type. Preserve
   framework-prescribed names. Do not invent product behavior or a dummy test suite.
2. Add mise-managed runtimes and meaningful same-named command tasks/shims using
   tasks.md. Generate tools/ only when there are public commands. Put .env loading
   in configuration only when .env is used; document its setup without secrets.
3. For an enabled host, configure the minimal supported entry point from
   integrations.md. Shared working skills may be read natively without any Braid
   adapter. Do not add Braid, Specflow or Autopilot merely to fill the tree.
4. Enrich README/AGENTS with the actual commands, relevant invariants and pointers.
   Create docs/dev content where the request supplies or requires it. A new project
   without specs/reports does not need an empty project-management directory.

## Verify

Run the helper's check command; it requires the root Claude bridge. Follow the
instruction-scope checks in integrations.md for any nested AGENTS.md added later.
Inspect generated shims for executable permissions,
argument forwarding and task recursion; list/validate mise tasks if applicable.
Run the applicable safe repository validation tasks after inspecting their contents;
never launch develop or publish a release as a verification shortcut. Check release
preview only where supported and ensure it makes no repository/remote mutations.
Missing runtime/dependency access is an explicit INCOMPLETE verification item.

Record actual results in the final response. A minimal scaffold need not gain a
persistent report just to document its creation. COMPLETE means a useful repository
matching the stated scope, not merely a helper exit code of zero.
