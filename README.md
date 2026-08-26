# agent-skills

Portable personal skills for AI coding assistants, plus `braid`, the composer
that assembles multiple source repositories and projects their skills into
host-specific discovery paths.

`~/.agents/skills` is the generated discovery view, not the canonical Git
source. A skill is a directory containing `SKILL.md`; supporting `scripts/`,
`references/`, and `assets/` stay beside it.

## Install

Keep the repository as a normal checkout and install Braid in editable mode so
the command continues to use that checkout as the personal source:

```bash
git clone https://github.com/buvis/agent-skills \
  ~/git/src/github.com/buvis/agent-skills
cd ~/git/src/github.com/buvis/agent-skills
uv tool install --editable .
braid --dry-run
braid
braid --check
```

Without installation, run `python bin/braid.py`. On Windows, use
`py bin\\braid.py`; Braid falls back to NTFS junctions when directory symlink
privileges are unavailable.

## Source and overlay architecture

Do **not** make `~/.agents` a submodule of the home dotfiles repository. Keep
each ownership/security domain in its own normal checkout and compose them into
`~/.agents/skills` with per-skill symlinks:

```text
~/git/src/github.com/buvis/agent-skills/       # public personal source
~/git/src/<employer>/agent-skills/             # private internal source

~/.config/agent-skills/sources.d/
├── personal                                   # dotfiles-managed
└── work                                       # work-machine only; never public

~/.agents/skills/
├── create-prd -> <personal-source>/skills/create-prd
├── company-release -> <work-source>/skills/company-release
└── ...
```

The dotfiles repository should track only bootstrap/composition configuration,
not a submodule gitlink for `~/.agents`. This avoids a second parent commit
whenever the public skill repository advances.

Maintenance rules:

- Edit a skill in its owning source checkout. Existing links reflect content
  edits immediately; recomposition is needed only after adding, removing, or
  renaming a skill.
- Commit and push personal changes in the public `agent-skills` repository.
  Pull on another machine only to receive changes made elsewhere.
- Keep employer skills in a separate internal repository. Never copy them into,
  or create tracked links from, the public checkout.
- Prefer repository-scoped employer skills (`<work-repo>/.agents/skills`) when
  they apply only to that repository. Put a work skill in the global union only
  when it genuinely applies across work projects.
- The composer must reject duplicate skill names by default. Resolve a
  collision by renaming or by an explicit machine-local precedence rule; never
  depend on an assistant's host-specific discovery order.
- A generated-state manifest must record every link the composer owns. Cleanup
  may remove only those recorded links, never arbitrary files under
  `~/.agents/skills`.

`braid` discovers every configured source, rejects duplicate skill names before
writing, composes per-skill links under `~/.agents/skills`, and then projects
eligible skills to Claude. Kiro can use the same assembled view; Copilot and
Codex discover it directly.

## How each assistant sees skills

| Assistant | Personal discovery path | Setup | Verified |
|---|---|---|---|
| Claude Code | `~/.claude/skills` | Run `braid`; it creates per-skill links. | Yes - `braid --check` reports zero drift and the links resolve. |
| GitHub Copilot | `~/.agents/skills` | Native, no extra link. It also reads `~/.copilot/skills`, and per project `.github/skills`, `.agents/skills`, `.claude/skills`. | Yes - `copilot skill --help` lists the source and `copilot skill list` returns the union. |
| Codex | `~/.agents/skills` | Native, no extra link. | Partly - the binary interns `.agents/skills` beside `.codex/config.toml`, but the CLI has no `skill list`, so nothing has confirmed the listing end to end. |
| Kiro | `~/.kiro/skills` | Add `skill://~/.agents/skills/*/SKILL.md` to a custom agent, or create equivalent per-skill links. Kiro's import command copies rather than links. | No - `~/.kiro` does not exist here and this row has never been run. |

Neither Copilot nor Codex can be pointed away from `~/.agents/skills`: Copilot's
personal source list is fixed and Codex interns the path. Whatever `braid` links
into the union is what those two hosts offer, so a name that must not reach them
has to stay out of `skills/` altogether. That is why the documentation copies of
runtime-bound plugin skills live in `docs/plugin-skills/`.

Do not link all of `~/.agents/skills` over `~/.claude/skills`: Claude-only
skills and plugin-owned skills also live there. `braid` links one skill at a
time, preserves destination-only entries, and skips names in
`.braidignore` policy files.

`~/.codex/skills` has a different job. Codex and its installers use it for
Codex-owned/system skills (notably `~/.codex/skills/.system`) and other
Codex-specific installations. Do not make it the shared source and do not
symlink it wholesale. User-authored cross-agent skills belong in
`~/.agents/skills`.

## braid

Preview, apply, or verify the union and Claude projection:

```bash
braid --dry-run
braid
braid --check
```

Put one source path per line in files under
`~/.config/agent-skills/sources.d/`. Lines may contain `#` comments. Keep the
public source in a dotfiles-managed `personal` file and the employer source in
a work-machine-only `work` file:

```text
# ~/.config/agent-skills/sources.d/personal
~/git/src/github.com/buvis/agent-skills

# ~/.config/agent-skills/sources.d/work
~/git/src/<employer>/agent-skills
```

`--source PATH` adds an ad hoc repository or `skills/` directory. `--no-claude`
updates only the shared union. `AGENTS_ROOT`, `CLAUDE_ROOT`, and
`AGENT_SKILLS_CONFIG` override the default roots.

For each non-ignored canonical skill, `braid` creates an absolute symlink at
`~/.claude/skills/<name>`. If that name is already a real directory or points
somewhere else, it is moved first to
`~/.claude/skills-backup/<timestamp>-<pid>/`. Claude-only destination entries
are untouched. Restart the assistant after changing skills if its current
session does not notice the update.

On Windows, Braid tries directory symlinks first and falls back to NTFS
junctions if Developer Mode or elevated symlink privileges are unavailable.
The same Python CLI and flags work on macOS, Linux, and Windows; no Bash runtime
is required.

`.braidignore` is intentional policy, not an error list. Braid loads it from
the tool repository, `~/.agents`, every source repository, and the machine-local
config directory. It holds exactly one class of name: a skill Claude gets from a
plugin, where a standalone copy would become a duplicate unnamespaced command.
Those copies still run on Codex and Copilot, so they stay in the union view and
are skipped only on the way to `~/.claude/skills`.

It is not a way to hide a skill from Codex or Copilot. Those two read the union
directly, so an exclusion never reaches them; the only lever is what braid links
into `~/.agents/skills` in the first place.

## Updating a skill

1. Resolve `~/.agents/skills/<name>` to its owning source checkout and edit the
   source, not the generated link farm.
2. If a newer standalone Claude definition exists, merge it into that source
   directory, keep its resources together, and replace avoidable host tool
   names with capability language (for example, “ask the user” or “spawn a
   sub-agent”).
3. If host coupling is real, keep it explicit in the `compatibility` frontmatter
   field. Do not pretend Claude hooks, Codex session storage, or a proprietary
   sub-agent API is portable.
4. Validate with the public repository's validator, then run `braid --check`.
5. Commit and push in the owning source repository. Recompose only if skill
   membership or names changed.

The current tree uses these compatibility classes:

- **Portable** — instructions and resources use ordinary filesystem, Git, or
  language tooling and can be followed by any capable assistant.
- **Portable compatibility copy** — the skill is owned by a Claude plugin, but
  a standalone copy remains under `~/.agents` for agents without that plugin.
  It is skipped when projecting back to Claude.
- **Documentation copy** — the prose of a plugin skill whose scripts, CLI, or
  agents stayed in the plugin. It is a specification, not a runnable procedure,
  so it lives in `docs/plugin-skills/` and no host discovers it.
- **Personal runtime** — callable from another assistant, but depends on this
  author's Claude/autoclaude files, wrappers, quotas, or review protocol.
- **Codex-specific / Claude-specific** — depends on that host's config,
  transcript format, hook lifecycle, or tool names. The frontmatter says so, and
  a skill that only Claude can run is kept out of `skills/` rather than ignored,
  since `.braidignore` cannot hide it from Codex or Copilot.

## Plugins: reuse versus port

A plugin is a package around skills and possibly agents, hooks, MCP servers,
commands, or executables. Sharing its `skills/` directory is not the same as
sharing the whole plugin.

- Reuse the same package when it implements the Agent Plugins 1.0/Open Plugin
  conventions supported by the target host and keeps host-specific behavior in
  namespaced adapters.
- Reuse portable `SKILL.md` content and MCP server definitions directly where
  the host supports them.
- Port the manifest and integration layer when the package is a legacy Claude
  plugin. Claude hook events, tool names, permissions, commands, agents, and
  `${CLAUDE_PLUGIN_ROOT}` are not automatically meaningful to another host.
- A recognized manifest is only an installability signal; test hooks, agents,
  resource paths, and permissions on every target.

GitHub Copilot recognizes several plugin manifest locations, including
`.claude-plugin/plugin.json`, and supports Agent Plugins. Kiro supports Agent
Plugins 1.0. Codex has its own plugin packaging and can reuse portable skills,
MCP, and host adapters, but a legacy Claude bundle is not automatically a Codex
plugin.

Current local policy:

| Claude plugin | Treatment outside Claude |
|---|---|
| `git-ferry` | Keep its six skills as standalone compatibility copies in `~/.agents`; skip them in `braid`. |
| `strunk` | Keep the language/testing skills as standalone compatibility copies; skip them in `braid`. |
| `claude-checkup` | Claude owns the audits and they need its config layout, so the copies here are documentation only and sit in `docs/plugin-skills/`. |
| `aegis` | `gateguard` documents a Claude hook and does nothing without it, so it is a documentation copy in `docs/plugin-skills/`. No cross-host behavior without a hook adapter. |
| `warden` | Already carries Codex and Copilot adapters in addition to Claude integration; continue moving it toward one multi-host plugin. |
| `loupe` | Hook-heavy Claude plugin; port the hook/event adapter before reuse. |
| `agoge` | Claude agent pack; its prompts are reusable, but agent declarations and orchestration need host adapters. |
| `frontend-design` | Treat as vendor/plugin-owned; install the host's corresponding plugin or keep a separate portable skill. |

For a new cross-host plugin, prefer one repository with portable `skills/` and
MCP definitions at the root, plus small `.claude-plugin`, `.codex-plugin`, and
other host adapters. Do not maintain divergent copies of the skill prose unless
the behavior truly differs.

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
