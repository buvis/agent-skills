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

`skills/` is the only directory braid scans (`_skills_directory`), and every
host discovers what braid links from it. Putting a `SKILL.md` there advertises
it as runnable on Claude Code, Codex, and Copilot alike. Prose that documents a
procedure without shipping the code to run it belongs in `docs/plugin-skills/`,
which nothing scans.

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

**Documentation copies.** Some plugin skills are half instructions, half
executable: autopilot ships a CLI, agoge ships seven agents, claude-checkup
ships audit scripts. Duplicating that code here would fork a released product
and drop its tests into `uv run pytest`, so these copies carry `SKILL.md` and
`references/` only.

They live in `docs/plugin-skills/<name>/`, never in `skills/`. Half a skill is
not a skill: with only the prose, Codex and Copilot would list it, route to it,
and fail, because the half that runs ships in a Claude plugin they cannot
install. `.braidignore` cannot save them - it applies on the way to
`~/.claude/skills` and those two hosts read the union view directly. Keeping
the copies outside `skills/` is what makes them undiscoverable, so a
documentation copy never gets a `.braidignore` entry. Four rules keep them
honest:

- it sits under `docs/plugin-skills/`, so no host discovers it;
- the `compatibility:` line opens with "Documentation copy of the `<plugin>`
  plugin skill" and names what stayed behind;
- a banner above the first heading repeats it, so a model that skipped the
  frontmatter still learns the skill is not runnable as it stands;
- every path into the plugin is written `<name-plugin-root>/...`. Never
  `${CLAUDE_PLUGIN_ROOT}`: a host that does not substitute it passes the
  literal to a shell, where it expands to nothing and the path silently
  becomes `/skills/...`. A marker that never resolves fails loudly instead.

Sync a documentation copy the same way as any other: diff it against its twin,
then re-apply these four rules to whatever the diff brought over.

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

`uv run pytest` collects `tests/` for braid plus every `test_*.py` a skill
ships under `skills/`. A skill that adds tests is picked up with no config
change. One of them, the `create-skill` validator's acceptance test, runs every
skill in this repo through the live-profile bash lint.

This repository is public. Keep personal paths, usernames, hostnames,
employer names, and private project names out of it, including inside
examples and sample output. Write examples as `/Users/you/...` with generic
project names.
