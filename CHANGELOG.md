# Changelog

All notable changes to this project are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

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

### Changed

- **braid**: read exclusions from `.braidignore` policy files in each source,
  replacing the single `~/.agents/braid.ignore` file.
- **skills**: declare plugin dependencies in a `## Dependencies` section and
  namespace plugin skills as `plugin:skill` in `convene-council`, `create-prd`,
  `debug-stuck-agent`, and `elicit-requirements`.

### Fixed

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
- **tests**: `uv run pytest` now collects every `test_*.py` a skill ships, which
  brings the previously unrun `audit-security` suite into the default run.
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
