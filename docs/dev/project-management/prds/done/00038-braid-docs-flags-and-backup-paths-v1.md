---
default_model: sonnet
rework_cap: 5
catchup: skip
design: skip
---

# Braid's flags and backup paths match the README

## Problem

The README puts backups at `~/.claude/skills-backup/<timestamp>-<pid>/` (`README.md:139-142`), but
`_backup` (`src/agent_skills_braid/cli.py:258`) appends a category level, so the real Claude path ends in
`project/` and the union path (`<agents-root>/backups/<ts>-<pid>/compose/`, from `cli.py:349-350`) is not
in the README at all; an operator hunting a displaced skill under the documented path finds an empty
directory and may conclude it was deleted. In the same document, `README.md:134-136` names `--source` and
`--no-claude` and nothing else, while `_parser()` (`cli.py:415-419`) defines `--policy`, `--agents-root`,
`--claude-root`, `--config-root` and `--no-claude` with no `help=` text, so `braid --help` prints them with
a blank description column and the working `--policy` flag is reachable only by reading the source.
Source: agoge run `dev/local/audit-results/agoge-2026-08-31.md`, findings 33 (LOW, merged journey and
release lanes) and 39 (LOW, release lane); decision 2026-09-02: correct both backup paths in the README and
add `help=` strings plus a README flag table.

```
BACKUP .../claude/skills/spike -> .../claude/skills-backup/20260831-035442-72146/project/spike
BACKUP .../agents/skills/survey -> .../agents/backups/20260831-040729-8073/compose/survey
Content survived both moves, so this is discoverability, not data loss.
The help output shows the five flags with no help= text. --policy is fully
functional and reachable only by reading the source: running with
--policy /.../mypolicy.txt gave 21 ignored against 20 ignored without it.
```

## Solution

Give each of the five bare `add_argument` calls a `help=` string describing what the code does today, then
bring the README's braid section in line: replace the prose sentence at `README.md:134-136` with a flag
table beside the env vars already documented, and correct the backup paragraph at `README.md:138-143` so it
names both real destinations, category level included. Docs and argparse help only, no behavior change.

## Requirements

### Must have

- `--policy`: repeatable extra `.braidignore` policy file, loaded with the repository, agents-root,
  config-root and per-source files (`cli.py:445-455`).
- `--agents-root`, `--claude-root`, `--config-root`: override the union root, the Claude root and the
  config directory holding `sources.d`, ahead of `AGENTS_ROOT`, `CLAUDE_ROOT` and `AGENT_SKILLS_CONFIG`
  (`cli.py:427-431`).
- `--no-claude`: update only the shared union, skip the Claude projection (`cli.py:466`).
- The README table is markdown with a `| Flag | Effect |` header and one row per flag, where the prose
  sentence at `README.md:134-136` is now.
- The README states both destinations as the code builds them:
  `~/.claude/skills-backup/<timestamp>-<pid>/project/` and `<agents-root>/backups/<timestamp>-<pid>/compose/`.

### Nice to have

- none

## Implementation

### Module: braid argument parser

- **Location**: `src/agent_skills_braid/`
- **Responsibility**: Define the command-line surface and its help text.
- **Exports**: `_parser()` (`cli.py:400-421`)

### Module: braid README

- **Location**: `./`
- **Responsibility**: Document the flags and the backup layout the code produces.
- **Exports**: the flag paragraph (`README.md:134-136`), the backup paragraph (`README.md:138-143`)

### Dependencies

- braid argument parser: No dependencies (foundation)
- braid README: Depends on [braid argument parser] - the table repeats the help strings, so the wording is
  settled first

## Tasks

### Phase 0: Foundation

- [ ] Add a `help=` string to each of the five bare `add_argument` calls (`cli.py:415-419`) describing the
  behavior listed under Must have - Acceptance: `rg -n -c "help=" src/agent_skills_braid/cli.py` prints 8
  (3 today), and `python3 bin/braid.py --help` exits 0 and prints description text for `--policy POLICY`,
  `--agents-root AGENTS_ROOT`, `--claude-root CLAUDE_ROOT`, `--config-root CONFIG_ROOT` and `--no-claude`,
  each of which today ends at its metavar with nothing after it.

### Phase 1: Core

- [ ] Replace the flag sentence in the README with the `| Flag | Effect |` table, keeping the env-var
  sentence. Premise: `README.md:134-136` still reads "`--source PATH` adds an ad hoc repository or
  `skills/` directory. `--no-claude` updates only the shared union. `AGENTS_ROOT`, `CLAUDE_ROOT`, and
  `AGENT_SKILLS_CONFIG` override the default roots."; if not, skip and report (depends on: Phase 0) -
  Acceptance: `rg -n --fixed-strings -e "--policy" README.md`,
  `rg -n --fixed-strings -e "--agents-root" README.md`,
  `rg -n --fixed-strings -e "--claude-root" README.md` and
  `rg -n --fixed-strings -e "--config-root" README.md` each print at least one line (all print nothing
  today), and `rg -n --fixed-strings "AGENT_SKILLS_CONFIG" README.md` still matches.
- [ ] Correct the backup paragraph so it names both destinations. Premise: `README.md:141` still reads
  `~/.claude/skills-backup/<timestamp>-<pid>/` with no `project/` level and the union path is absent; if
  either has changed, skip and report (depends on: Phase 0) - Acceptance:
  `rg -n -c --fixed-strings "skills-backup/<timestamp>-<pid>/project/" README.md` prints 1 and
  `rg -n -c --fixed-strings "backups/<timestamp>-<pid>/compose/" README.md` prints 1 (both print nothing
  today).

## Success Criteria

- `python3 bin/braid.py --help` shows a description for all ten options (`-h`, `--dry-run`, `--check`,
  `--source`, `--policy`, `--agents-root`, `--claude-root`, `--config-root`, `--no-claude`, `--version`);
  each parser action has a nonempty help description. Descriptions wrapped onto continuation lines
  are valid; no formatter change is required. A headless parser-action assertion checks the five
  newly described options, and the CLI exits 0.
- Both README backup strings string-match the `BACKUP` lines a sync prints, category level included.
- `uv run pytest tests -q` reports the same result as before the change; no product code is touched.
- PRD 00044 owns `README.md:26-28` and `README.md:145-148`; this PRD leaves both untouched.
- Nothing checks the README against the code, so it can drift again; unifying the two backup layouts was
  declined and they stay divergent.
