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

- **distil-memory**: write the memory file and the `MEMORY.md` index atomically.
  The index is rewritten whole on every pointer upsert, so a process killed
  mid-write used to truncate it and lose every pointer line recorded before it,
  not just the one being added.
- **distil-memory**: report queue and write errors from the `docket` and `write`
  command lines instead of raising a Python traceback. A refused decision or a
  missing memory store now prints its message to stderr and exits 1.
- **brief-portfolio**: keep collecting when the skill-metrics log exists but
  cannot be read. An unreadable `skills.jsonl` used to abort the whole run and
  discard every repo already collected; the audit-cadence rows now fall back to
  "never" and the brief still renders.
- **purge-devlocal**: stamp today's `.trash/<date>/` batch directory on every
  `--apply` run, not only when something was actually trashed. A run over an
  already-clean store used to leave no trace, so anything reading that
  directory as "when did this last run" could never advance. On a run that
  trashes nothing, the stamp is now written after the retention pass, so a low
  `--empty-trash-days` no longer deletes it again immediately.
- **distil-memory**: keep transcript text out of stderr when the cheap-tier
  judge times out. The timeout message used to be the raw
  `subprocess.TimeoutExpired` text, which carries the whole command line and so
  echoed back the slice being classified; it now names only the timeout
  duration.
- **distil-memory**: point the yield report at the proposals directory the run
  actually published. It used to name a fixed
  `dev/local/audit-results/proposals/`, which no run ever creates, so anyone
  following the report found nothing. A run that fails to publish now names no
  proposals directory at all.
- **distil-memory**: reject a proposal whose name leaves nothing safe to use as
  a filename, instead of ending the run. Because the name is model output, a
  name like `!!! ???` used to raise out of the whole run before the yield
  report was printed; it is now an ordinary reasoned discard, so the run still
  reports what it read.
- **distil-memory**: read the memory index once instead of checking for it and
  then reading it. In the window between the two calls an index that was merely
  absent could be reported as unreadable, which is the one distinction that
  decides whether a fact is typed as new or as an update.
- **distil-memory**: skip a candidate memory name that is not a plain filename
  stem, so a malformed index entry cannot read a file from outside the memory
  directory. A refused name is treated as absent, exactly like a stale index
  entry, so it cannot manufacture a dedup error either.
- **distil-memory**: skip a candidate whose file is a link out of the memory
  directory. The name rule above only reads the name, so an ordinary stem whose
  file in the plane pointed elsewhere still handed back another directory's
  bytes under a memory's name. Each path is now resolved before it is opened,
  and a link that stays inside the plane is still read in full.
- **distil-memory**: give every discard a reason. A model that ended its
  `DISCARD:` line without words used to leave a blank field in `discards.json`,
  which the run then reported as a discard nobody could act on; it now says the
  model stated no reason.
- **distil-memory**: skip the distil stage when triage failed, instead of
  publishing an empty proposals directory and reporting zero proposals. Zero
  means the stage ran and found nothing, so reporting it for a stage that never
  had any input misread a failed run as an empty one. Such a run now reports
  the distil counts as `n/a` and writes no directory.

### Added

- **distil-memory**: an approved proposal can now be written into its project's
  memory store. The memory file lands beside the transcript that produced it and
  a matching one-line pointer is upserted into that store's `MEMORY.md`. A store
  that does not exist stops the write instead of being created, a new proposal
  never overwrites an existing memory that happens to share a filename, and an
  update that did not change the description leaves `MEMORY.md` untouched.
- **distil-memory**: proposal decisions now persist across sessions. Each run's
  proposals are queued to disk by `scripts/docket.py`, so an interrupted
  approval sitting resumes at the next undecided proposal with no duplicates
  and no skips. A sitting is capped at 10 decisions; a dropped proposal is
  filtered out of later runs over the same window unless the distil rubric
  changes, which reopens it. The queue file itself stays
  `dev/local/audit-results/distil-memory-queue.json`.
- **distil-memory**: a keep / edit / drop approval walkthrough. The skill now
  documents how to decide queued proposals one at a time and write the kept
  ones into the memory store beside the transcript that produced them. Nothing
  reaches a memory directory without an explicit per-entry decision, and the
  stage is invoked, never triggered - there is no always-on hook.
- **distil-memory**: `--distil` now turns surviving slices into memory-file
  proposals on disk. Each run publishes a
  `dev/local/audit-results/distil-memory-<stamp>-proposals/` directory holding
  one file per proposal plus a proposals and a discards manifest, stamped like
  the report beside it and written before it, so a saved report never names a
  directory that is not there. Each slice is typed against the memory plane
  beside its own transcript, and a memory that cannot be typed is kept as new
  and carries the reason. The yield report gained five lines - proposals,
  discards, new vs update, skipped by limit, dedup errors - each reading `n/a`
  until a stage produces it, so a report never implies a count it does not
  have. `--distil-limit` (25 by default, `0` for no cap) caps how many
  survivors are distilled and the report states the remainder; a negative limit
  is a usage error that names the flag and stops before a single transcript is
  read, and `--distil` alongside `--dry-run` says on stderr that it is being
  ignored, since a dry run makes no model calls.
- **distil-memory**: turn a surviving transcript slice into a complete memory
  file, or into a named discard. A strong-tier model gets the slice plus a few
  existing memories as anchors and answers with either a discard line or a
  whole file; nothing becomes a proposal until it passes the memory-file
  validators, so a rambling or half-written answer leaves a discard that says
  what was wrong with it. A model that fails to answer is a discard too, never
  a crash - except a missing CLI, which stops the run rather than turning every
  remaining slice into an empty discard. Discard reasons never quote the slice
  they came from.
- **distil-memory**: type a proposed memory as new or as an update of an
  existing one. Only the shortlisted memories are read, and a proposal whose
  name a memory already holds is typed an update without asking a model at all.
  Otherwise one strong-tier question covers the whole shortlist, and an answer
  naming no memory reads as new. A judge that fails raises instead of answering
  new, so a duplicate is never filed as a new memory because the model never
  replied.
- **distil-memory**: narrow a proposed memory to the few existing memories it
  might duplicate, by reading the memory index alone. Bullet links in
  `MEMORY.md` become name-to-cue entries, and each is scored against the
  proposal's name and description by the Jaccard ratio of their content words,
  so a long entry that merely mentions the query's words ranks below a short one
  that is about them. An absent index reads as an empty one, while an index that
  exists but cannot be read raises rather than silently answering "no
  duplicates".
- **distil-memory**: publish a run's proposals and discards atomically. The
  output directory is reserved with an exclusive `mkdir`, built in a sibling
  staging directory, and swapped into place with a single rename, so a reader
  sees either the complete run or no directory at all - never a report naming
  more proposals than the directory holds. A second run against an existing
  directory is refused rather than merged into, and two proposals whose names
  reduce to the same filename stem get numbered suffixes instead of
  overwriting each other.
- **distil-memory**: hold a distilled memory file to what this feature is
  allowed to emit. On top of the generic contract, it pins `metadata.type` to
  `project`, rejects a frontmatter-only fragment, rejects every malformed
  `[[wiki-link]]` naming the offending text, and requires at least one link once
  the memory index has something to link to. Also reduces a proposed name to a
  safe filename stem, and cuts the evidence excerpt around the verification
  marker rather than at the head, so the sentence that justified the slice
  survives truncation.
- **distil-memory**: check a proposed memory file against the memory-file
  contract before it can reach the queue. Rejects a missing or empty `name` or
  `description`, a `metadata.type` outside the four allowed values, and a
  description that merely restates its own `**How to apply:**` line, naming the
  field or rule that rejected it. Calibrated against the memory files that
  already exist rather than against an invented format.
- **distil-memory**: funnel Claude Code transcripts down to memory candidates
  without letting a model read the corpus wholesale. Selects transcripts by
  `--days`, `--all` or `--project`, slices assistant-authored text on
  verification markers with a regex (no model), triages the survivors on a
  cheap tier, and prints a per-stage yield report - transcripts read, slices
  matched, slices kept, survivors - that always states its counts, including
  zero. `--dry-run` prices a sweep with no model call at all. Refuses to run
  against a claude-checkup parser older than `0.2.2`, naming the version it
  resolved, because older releases over-count user prompts by roughly 41%.
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
