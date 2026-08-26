# AGENTS.md

Working rules for this repository. Read before editing a skill.

## What this repo is

The canonical source for cross-agent skills. `~/.agents/skills/<name>` and
`~/.claude/skills/<name>` are generated symlinks laid by `braid`. Edit here,
commit here, then run `braid --check`. Never edit through a link, and never
stage a skill path into another repo: you would record the symlink, not the
change.

A skill is a directory under `skills/` holding `SKILL.md`, plus optional
`scripts/`, `references/`, and `assets/`.

## Referencing files from a skill

The same `SKILL.md` runs on Claude Code, Codex, Copilot, and Kiro. Every path
in it must resolve on all of them.

| Referencing | Write | Why |
|---|---|---|
| a file in the same skill | `~/.agents/skills/<name>/scripts/x.sh` | the one discovery path every host shares |
| a file inside a plugin | `${CLAUDE_PLUGIN_ROOT}/...` | plugin repos only, never here |
| a path in the user's home | `~/...` or `$HOME/...` | |
| anything at all | never `/Users/<name>/...` | resolves for exactly one machine |

`${CLAUDE_SKILL_DIR}` resolves on Claude Code and nowhere else. The plugin
twins of these skills use it; the copies in this repo must not. Use the
`~/.agents/skills/<name>/` form instead.

**The substitution trap.** Claude Code expands `${CLAUDE_SKILL_DIR}`,
`$ARGUMENTS`, and friends inside `SKILL.md` before the model reads it. A
session that writes rendered text back to disk destroys the placeholder and
bakes in an absolute `/Users/...` path. That is how `create-skill` acquired
four hardcoded home paths (fixed 2026-08-26). When a skill documents these
variables, re-read the file on disk after any edit and confirm the braces are
still there.

`skills/create-skill/scripts/validate_skill.py` enforces these path rules.
Run it on every skill you touch.

## Depending on a plugin

Many skills here have a namespaced twin in a released plugin: `strunk`,
`git-ferry`, `claude-checkup`, `aegis`, `autopilot`. Two rules follow.

**Compatibility copies.** A skill whose Claude version ships in a plugin
carries a `compatibility:` frontmatter line saying so, and its name goes in
`.braidignore`. That stops `braid` from projecting a duplicate unnamespaced
command into `~/.claude/skills`. The copy stays for Codex, Copilot, and Kiro,
which have no plugin system.

**Cross-references.** When a skill names a skill it does not own, declare it
in a `## Dependencies` section placed right after the intro:

- namespace plugin skills as `plugin:skill`, so `autopilot:plan-tasks`, never
  bare `plan-tasks`
- say whether the skill invokes the dependency or only points a human at it
- say what happens when it is absent: hard failure, or which fallback runs

Frontmatter is the wrong home for this. `metadata` never reaches the model at
runtime; the body loads exactly when the skill triggers. See `create-prd`,
`convene-council`, and `elicit-requirements` for the shape.

Never point at a plugin skill by filesystem path. Plugin skills live in a
versioned cache and the path changes on every release.

## Before committing

```bash
uv run pytest
uv run python3 skills/create-skill/scripts/validate_skill.py skills/<changed-skill>
braid --check
```

`uv run pytest` covers both suites: `tests/` for braid, and
`skills/create-skill/scripts/` for the skill validator, whose acceptance test
runs every skill in this repo through the live-profile bash lint.

This repository is public. Keep personal paths, usernames, hostnames,
employer names, and private project names out of it, including inside
examples and sample output. Write examples as `/Users/you/...` with generic
project names.
