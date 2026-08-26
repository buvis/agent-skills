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

### Changed

- **braid**: read exclusions from `.braidignore` policy files in each source,
  replacing the single `~/.agents/braid.ignore` file.

### Fixed

- **skills**: replace hardcoded home paths with the portable
  `~/.agents/skills/<name>/` form, so helper scripts resolve on any machine.
- **create-skill**: restore the `${CLAUDE_SKILL_DIR}` placeholder that a
  rendered save had replaced with an absolute path.
- **create-skill**: run the validator acceptance test against this repository
  instead of a machine-specific skills directory, and exempt
  `~/.agents/skills/` from the bare-script-path lint.
