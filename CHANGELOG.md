# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- **brief-portfolio**: nag each config audit on its own cadence instead of
  showing one coarse "config maintenance" row. Every machine audit gets its own
  overdue row against its own horizon, and `purge-devlocal` is tracked per repo.

### Fixed

- **brief-portfolio**: keep collecting when the skill-metrics log exists but
  cannot be read. An unreadable `skills.jsonl` used to abort the whole run and
  discard every repo already collected; the audit-cadence rows now fall back to
  "never" and the brief still renders.
- **purge-devlocal**: stamp today's `.trash/<date>/` batch directory on every
  `--apply` run, not only when something was actually trashed. A run over an
  already-clean store used to leave no trace, so anything reading that
  directory as "when did this last run" could never advance.

### Added

- **capture-experiment**: write up a spike or experiment session as a single
  zettelkasten note - hypothesis, setup, summarized observations, dead ends,
  and verdict - before the details are lost to compaction or a new session.
  Request-only, needs only a title.
- **plan-port**: plan a port of a skill, tool, or plugin into a target -
  inventory the source's documented behavior one row at a time, classify each
  row `port`, `redesign`, or `drop` with a mandatory reason, walk every
  proposed drop past you individually, and emit a dependency-ordered phase list
  plus a retirement block that says when the original may finally be deleted.
- **braid**: compose skills from several source repositories listed in
  `~/.config/agent-skills/sources.d/`, rejecting duplicate skill names before
  writing anything.
- **braid**: record every owned link in a state manifest so cleanup removes
  only what braid created.
- **braid**: fall back to NTFS junctions on Windows when directory symlink
  privileges are unavailable.
- **braid**: ship as an installable package (`uv tool install --editable .`)
  exposing a `braid` command.
- **skills**: migrate `spike`, `review-design-doc`, `review-discovery-doc`, and
  `review-prd-backlog` from the Claude-only tree, so the skills that reference
  them are no longer pointing at something a user cannot obtain.
- **AGENTS.md**: repository working rules covering portable path references,
  the `${CLAUDE_SKILL_DIR}` substitution trap, plugin dependency declarations,
  and the pre-commit checks.
- **skills**: publish `web-patterns`, `web-performance`, and `web-security`, the
  three strunk skills that had no copy here at all.
- **docs**: publish the runtime-bound plugin skills as specifications under
  `docs/plugin-skills/` - claude-checkup's seven audits, agoge's `run-agoge`,
  autopilot's seven, and aegis's `gateguard`. They carry the procedure and its
  references; the scripts, CLI, hooks and agents stay in the plugins, and a
  banner in each says so. They sit outside `skills/`, so no host discovers them
  as runnable skills.
- **skills**: publish `survey`, the on-demand codebase brief. Its one tie to
  Claude Code was a `sys.path` insert reaching a hook library for a cached
  optional import of `tree_sitter_language_pack`; the skill now does that import
  itself in six lines and no longer writes an audit entry on a host without the
  package, which is what made a survey create a store it promises never to
  create. The hardcoded skip list lost the twenty directory names taken from one
  host's config tree: they would have dropped a real `tasks/`, `logs/` or
  `jobs/` layer out of anyone else's brief, and only build and dependency output
  is skipped now. tree-sitter stays optional and the degraded note still says
  when it was absent.
- **skills**: publish `purge-devlocal`, the `dev/local` garbage collector that
  `brush` delegates to. Its classifier was already stdlib-only; the port
  rewrote four `CLAUDE_SKILL_DIR` paths and pointed the post-apply link check
  at `~/.agents/skills/review-prd-backlog/`, which now resolves for every host
  rather than one. The optional `engram` harvest and the per-project memory
  store are declared as optional instead of assumed, and `--all`'s Go-style
  layout assumption is stated where a reader meets it. `--repo` now refuses a
  path that is not a store instead of sweeping the project it points at, which
  mattered because the wire-in runs `--apply` unattended.
- **skills**: publish `brush`, the project hygiene pass. Its git core was
  already host-neutral; five `CLAUDE_SKILL_DIR` paths became `~/.agents/skills/`
  ones, and the two Claude-only enrichments now say so instead of assuming: the
  notify ping skips when the script is absent, and phase 5 promotes memories
  only where the host keeps a per-project store. The preflight refusal that
  named one machine's dotfiles repo now refuses any work-tree that is `$HOME`,
  the batch probe no longer takes the preflight down on a host without `pgrep`,
  and phase 1 names the standalone `catchup` copy the other hosts actually get.
- **skills**: publish `audit-qwen`, the report card for the `use-qwen` fence.
  Its telemetry was already read per repo under `dev/local/autopilot`, so the
  only tie was repo discovery appending `~/.claude` unconditionally; it is now
  included when it actually holds a ledger, and the no-gita fallback scans the
  working directory instead of one host's config dir.
- **skills**: publish `brief-portfolio` and `use-qwen`. `brief-portfolio` needed
  only its asset paths rewritten; its Claude-config-maintenance row now reports
  "never" off Claude Code and says so. `use-qwen` needed more: two helper
  scripts resolved a root by walking three levels up, which lands on `~/.agents`
  through the link farm, and `promote-default.sh` copied a file it never checked
  existed, so a promotion silently skipped updating the integration doc. Both
  fixed; its 99 shell tests pass from the new location.
- **skills**: publish `assess-evolution` and `debrief-meeting`, the two
  Claude-only skills whose coupling turned out to be cosmetic. Both now reach
  Codex, Copilot and Gemini: `assess-evolution` lost a `~/.claude/rules/`
  pointer it only needed the principle from, and `debrief-meeting`'s twelve
  `CLAUDE_SKILL_DIR` paths became `~/.agents/skills/` ones. Its parser is
  stdlib-only, so it needs no dependency the repo did not already have.
- **docs**: a `docs/plugin-skills/README.md` saying what a documentation copy
  is, how it differs from a compatibility copy, the four rules one follows, and
  the condition for deleting it - the directory is a holding pen that should
  empty as plugins become installable off Claude Code.
- **AGENTS.md**: describe the documentation-copy class - where it lives, what
  it ships, the banner it carries, and why plugin paths are written
  `<name-plugin-root>/...` instead of a placeholder that expands to nothing.

- **work**: the qwen helper paths in the documentation copy resolve again. They
  named `~/.agents/skills/use-qwen/` while `use-qwen` sat outside the union, so
  all three pointed at nothing. Publishing `use-qwen` here fixes it at the
  source; the copy is byte-identical to the released plugin again.
- **tests**: guard skill placement - no skill in `skills/` may declare itself
  Claude-only, and every documentation copy must carry its banner, its
  `Documentation copy of the <plugin> plugin skill` line, a
  `<name-plugin-root>/` marker, and no `.braidignore` entry. The first of those
  is the `gateguard` case, which reached three hosts because nothing checked it.
- **ci**: run the suite on Python 3.10 and 3.13, plus `ruff check`,
  `ruff format --check`, and the skill validator over every skill.
- **ci**: run every skill's bash suite too. Five skills ship one
  (`use-codex`, `use-gemini`, `use-sonnet`, and `use-qwen`'s two, 172 tests
  between them) and pytest never sees them, so until now they passed or failed
  invisibly while CI reported green.

### Removed

- **skills**: retire the ten Codex audit forks (`audit-codex-config`,
  `audit-hooks`, `audit-memory`, `audit-permissions`, `audit-plugins`,
  `audit-project-orphans`, `audit-rules`, `audit-security`, `audit-settings`,
  `audit-skills`). They were the Claude audits with `.claude` swapped for
  `.codex`, and Codex keeps none of those paths: config is `config.toml`, not
  `settings.json`; sessions live in `sessions/<year>/<month>/`, not
  `projects/<encoded>/sessions-index.json`; `skills/` holds only `.system`; and
  `rules/` is one file. They scanned what was not there and reported clean.
- **skills**: retire the four Codex storage workflows (`agent-sort`,
  `restore-tasks`, `resume-session`, `save-session`) for the same reason. They
  read `~/.codex/tasks`, `~/.codex/projects`, `~/.codex/decisions`,
  `~/.codex/commands` and `~/.codex/dev`; none of those exist.

### Changed

- **braid**: read exclusions from `.braidignore` policy files in each source,
  replacing the single `~/.agents/braid.ignore` file.
- **audit-context**, **audit-mcp-health**, **audit-sessions**: retire the Codex
  forks and keep their claude-checkup twins as specifications under
  `docs/plugin-skills/`, which say which config dir they read instead of
  implying a Codex-native one.
- **skills**: declare plugin dependencies in a `## Dependencies` section and
  namespace plugin skills as `plugin:skill` in `convene-council`, `create-prd`,
  `debug-stuck-agent`, and `elicit-requirements`.

### Fixed

- **catchup**: read the keepers from `dev/local/meta/` and write the capsule
  there, falling back to the older root path only on an unmigrated store. The
  root compat symlinks are gone, so the previous root-only paths would have
  minted a second capsule that nothing reads.
- **catchup-upstream**: look for and delete the legacy upstream cursor at both
  `dev/local/meta/` and the older root path.
- **use-qwen**: `promote-default.sh` rewrites its files on Linux too. It used
  the BSD spelling `sed -i ''`, which GNU sed reads as two filenames, so every
  literal-id replacement failed with "can't read s|...|" and a promotion left
  the files untouched. Now edits through a temp file and writes back with
  `cat`, preserving the mode of the executable test script it rewrites.
- **create-skill**: drop the `PERMISSION_BINARIES` allowlist from the validator.
  Every entry was extensionless while the check it fed only flags script
  suffixes, so the two conditions were mutually exclusive and the list could
  never change a verdict - it just published one machine's permission config,
  private tool names included. A test now pins the real rule: a script suffix
  is flagged, an extensionless binary path is not, whatever it is called.
- **skills**: replace hardcoded home paths with the portable
  `~/.agents/skills/<name>/` form, so helper scripts resolve on any machine.
- **create-skill**: restore the `${CLAUDE_SKILL_DIR}` placeholder that a
  rendered save had replaced with an absolute path.
- **create-skill**: run the validator acceptance test against this repository
  instead of a machine-specific skills directory, and exempt
  `~/.agents/skills/` from the bare-script-path lint.
- **convene-council**: drop the dead pointer to a `run-autopilot` reference
  file that moved to the autopilot plugin.
- **skills**: describe the personal-runtime compatibility class without naming
  the author, which also removes the collision with the autopilot reviewer
  persona of the same name.
- **tests**: `uv run pytest` now collects every `test_*.py` a skill ships, so a
  suite bundled with a skill can no longer sit unrun.
- **explain-interactively**: lead the description with its trigger, and clone a
  GitHub source into the session scratchpad instead of `/tmp`.
- **explain-interactively**: `build.sh` takes the course directory as an argument
  and resolves every path from it, so assembling no longer depends on the caller
  having changed into the course directory first. It refuses, without writing,
  when the argument is missing or the directory has no `modules/`.
- **python-testing**, **rust-patterns**: restore the rulings the plugin twins
  fixed, which the first import had carried over in their thinned form.
- **apply-design-system**: rename `design-system` to match its strunk twin,
  replace the superseded body, and ignore the name so Claude Code stops loading
  a second, contradictory design skill alongside the plugin one.
- **gateguard**: point at the aegis hook with a marker that cannot half-resolve,
  replacing a `${CLAUDE_PLUGIN_ROOT}` that expands to nothing off Claude Code.
- **use-codex**, **use-gemini**, **use-sonnet**: ship the helper scripts. They
  carry no Claude coupling, so publishing them as documentation was wrong, and
  it broke a path Codex's own rules file allow-lists. Their SKILL.md now points
  at `~/.agents/skills/<name>/scripts/`, which resolves on every host.
