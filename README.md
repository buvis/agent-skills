# agent-skills

Skills that work in more than one AI coding assistant, plus `braid`, the small
composer that projects them into a host that cannot discover them natively.

A skill is a directory containing `SKILL.md`. Supporting `scripts/`,
`references/`, and `assets/` stay beside it.

## Which assistants see these

| Assistant | Discovery path | Setup |
|---|---|---|
| Codex | `~/.agents/skills` | Native. Nothing to do. |
| GitHub Copilot | `~/.agents/skills` | Native. Also reads `.github/skills`, `.copilot/skills`, `.claude/skills`. |
| Claude Code | `~/.claude/skills` | Run `braid`. It links each skill individually. |
| Kiro | `~/.kiro/skills` | Add `skill://~/.agents/skills/*/SKILL.md` to a custom agent, or link per skill. Kiro's import copies rather than links. |

## Install

```bash
git clone https://github.com/buvis/agent-skills ~/git/agent-skills

mkdir -p ~/.agents
ln -s ~/git/agent-skills/skills ~/.agents/skills   # single-source setup
ln -s ~/git/agent-skills/bin/braid ~/.agents/bin/braid

~/.agents/bin/braid --dry-run    # preview
~/.agents/bin/braid              # apply
~/.agents/bin/braid --check      # verify, exits 1 on drift
```

Codex and Copilot are done at that point. Claude Code needs the `braid` step.
Restart the assistant if a running session does not notice new skills.

`~/.codex/skills` has a different job and is not the shared source. Codex and
its installers use it for Codex-owned and system skills (notably
`~/.codex/skills/.system`). Do not symlink it wholesale. User-authored
cross-agent skills belong in `~/.agents/skills`.

## braid

`braid` creates one absolute symlink per skill at `$CLAUDE_ROOT/skills/<name>`,
pointing into `$AGENTS_ROOT/skills/<name>`. It is deliberately boring:

- **One skill at a time.** It never links the whole tree over `~/.claude/skills`,
  because Claude-only skills and plugin-owned skills also live there.
- **Destination-only entries survive.** Anything in `~/.claude/skills` that
  braid did not put there is left alone.
- **Nothing is deleted.** A name that is already a real directory, or a link
  pointing elsewhere, is moved to `~/.claude/skills-backup/<timestamp>-<pid>/`
  first.
- **`--check` is CI-friendly.** Exits 1 on any mismatch.

Both roots are environment variables, so a non-standard layout needs no edit:

```bash
AGENTS_ROOT=~/work/agents CLAUDE_ROOT=~/.claude braid
```

## braid.ignore

Names listed in `$AGENTS_ROOT/braid.ignore`, one per line, `#` for comments, are
never projected to Claude. This is policy, not an error list. Copy
`braid.ignore.example` to `~/.agents/braid.ignore` and edit.

The usual reason to ignore a name is that Claude already gets that skill from a
plugin. Linking a standalone copy beside it produces two entries under one name
and an ambiguous unnamespaced command. Ignore the standalone copy and let the
plugin win.

## Composing several sources

The layout above has one source. The reason `braid` links per skill rather than
linking the tree is so that `~/.agents/skills` can be a union of several
checkouts that do not belong in the same repository, most commonly a public
personal one and a private employer one:

```text
~/git/agent-skills/skills/               # public
~/git/<employer>/agent-skills/skills/    # private, never public

~/.agents/skills/
├── create-prd     -> <public>/skills/create-prd
├── release-train  -> <private>/skills/release-train
└── ...
```

Rules that keep this honest:

- Edit a skill in its owning checkout, never through `~/.agents/skills`. Links
  reflect content edits immediately; you only recompose after adding, removing,
  or renaming a skill.
- Never copy employer skills into the public checkout, and never create tracked
  links from it to them.
- Prefer a repository-scoped `<repo>/.agents/skills` for a skill that only
  applies to one project. The global union is for skills that genuinely apply
  everywhere.
- Reject duplicate skill names rather than resolving them by discovery order.
  Host discovery order is not a contract, and a silent winner is a bug you find
  months later.

Composing the union is currently manual: create the per-skill links yourself.
`braid` handles the host projection step only.

## Portability

Skills declare how portable they are in a `compatibility:` frontmatter field:

- **Portable** — ordinary filesystem, Git, and language tooling. Any capable
  assistant can follow it.
- **Portable compatibility copy** — a plugin owns this skill on one host; the
  standalone copy is here for assistants without that plugin, and is ignored
  when projecting back to that host.
- **Personal runtime** — callable anywhere, but depends on specific wrappers,
  quotas, or a review protocol that will not exist on your machine.
- **Host-specific** — depends on one host's config, transcript format, hook
  lifecycle, or tool names.

Be honest in that field. A Claude hook, a Codex session store, and a proprietary
sub-agent API are not portable, and pretending otherwise just moves the failure
to someone else's machine.

## Plugins are a different thing

A plugin packages skills and possibly agents, hooks, MCP servers, and commands.
Sharing a `skills/` directory is not sharing a plugin.

[Agent Plugins](https://agent-plugins.org/) v1 defines exactly two component
types, skills and MCP servers. Agents, hooks, and commands sit outside v1 and
live under a reverse-domain client namespace. So a package can be portable at
the envelope while its agents remain host-specific. Copilot recognizes several
manifest locations including `.claude-plugin/plugin.json`, and Kiro supports
Agent Plugins 1.0, but a recognized manifest only means installable. Test the
hooks, agents, resource paths, and permissions on every host you claim.

## References

- [OpenAI: Build skills](https://learn.chatgpt.com/docs/build-skills)
- [OpenAI: Plugins](https://learn.chatgpt.com/docs/plugins)
- [Claude Code: skills and symlink discovery](https://code.claude.com/docs/en/slash-commands)
- [GitHub Copilot: agent skills](https://docs.github.com/en/copilot/how-tos/copilot-on-github/customize-copilot/customize-cloud-agent/add-skills)
- [GitHub Copilot: plugins](https://docs.github.com/en/copilot/concepts/agents/about-plugins)
- [GitHub Copilot: plugin manifest reference](https://docs.github.com/en/copilot/reference/copilot-cli-reference/cli-plugin-reference)
- [Kiro: skills](https://kiro.dev/docs/skills/)
- [Kiro: Agent Plugins support](https://kiro.dev/blog/powers-supports-plugins/)
- [Agent Plugins specification](https://agent-plugins.org/)
