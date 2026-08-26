# Documentation copies of plugin skills

Nothing in this directory is a skill. Each entry is the **prose half** of a
Claude Code plugin skill whose other half - a CLI, a set of sub-agents, a hook,
audit scripts - ships in the plugin and was deliberately not copied here.

They are specifications. Read them to understand what the procedure does or to
port it to another host. Do not expect to run one.

## Why they are not in `skills/`

`skills/` is the only directory `braid` scans, and every host discovers what
braid links out of it. A `SKILL.md` placed there is advertised as runnable on
Claude Code, Codex, and Copilot alike.

That is fine for a skill that is all prose. It is a trap for these, because the
half that does the work is missing. A model on Codex would see `run-autopilot`
in its skill list, route to it, and fail on the first command.

`.braidignore` cannot prevent that. It is applied only on the way to
`~/.claude/skills`; Copilot and Codex read the union view at `~/.agents/skills`
directly, and neither can be pointed elsewhere - Copilot's personal source list
is fixed and Codex interns the path. Keeping these copies outside `skills/` is
the only thing that makes them undiscoverable, which is why a documentation copy
never gets a `.braidignore` entry.

## The other kind of copy

Do not confuse these with the **compatibility copies** that stay in `skills/`,
listed in `.braidignore`. Those are whole, portable skills that happen to be
owned by a plugin on Claude Code. They run fine on Codex and Copilot, so they
belong in the union; they are skipped only on the way to Claude, where the
plugin already provides a namespaced version and a second copy would become a
duplicate unnamespaced command.

| | Documentation copy | Compatibility copy |
|---|---|---|
| Lives in | `docs/plugin-skills/` | `skills/` |
| In `.braidignore` | never | always |
| Runs off Claude | no, the code stayed in the plugin | yes |
| Example | `run-autopilot`, `gateguard` | `catchup`, `python-patterns` |

## Rules for an entry here

1. It sits under `docs/plugin-skills/`, so no host discovers it.
2. Its `compatibility:` line opens with "Documentation copy of the `<plugin>`
   plugin skill" and names what stayed behind.
3. A banner above the first heading repeats that, so a model that skipped the
   frontmatter still learns the skill is not runnable as it stands.
4. Every path into the plugin is written `<name-plugin-root>/...`, never
   `${CLAUDE_PLUGIN_ROOT}`. A host that does not substitute the variable passes
   the literal to a shell, where it expands to nothing and the path silently
   becomes `/skills/...`. A marker that never resolves fails loudly instead.

Sync one the way you would any other skill: diff it against its twin in the
plugin, then re-apply these four rules to whatever the diff brought over.

## This directory should shrink to nothing

It is a holding pen, not a permanent class. Every entry exists because its
plugin is installable on Claude Code and nowhere else.

When a plugin is ported to Agent Plugins and a host can install the real thing,
delete the copy - there is nothing left for it to document. The compatibility
copy of a ported plugin goes too, and more urgently: once the host installs the
plugin, the standalone copy in `skills/` recreates the duplicate-command problem
on three hosts, where `.braidignore` can only fix one.

Two things to watch when judging whether a port has actually landed. Support is
per host, not a single event - Copilot reads `.claude-plugin/plugin.json` and
supports Agent Plugins, Kiro supports Agent Plugins 1.0, and Codex has its own
packaging that a Claude bundle does not automatically satisfy. And packaging is
the easy half: Agent Plugins standardizes how a plugin is bundled, not whether
the host has an equivalent sub-agent or hook primitive. A ported `run-autopilot`
on a host with no sub-agents is still a documentation copy, just with a manifest.
