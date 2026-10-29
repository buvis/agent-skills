---
name: purge-devtmp
description: Use when purging stale temporary development assets from docs/dev/tmp across repos with recoverable trash-first cleanup. Triggers on "purge dev tmp", "clean dev tmp", "gc dev tmp", "empty dev tmp trash".
compatibility: "Portable; requires Python 3.10+. The cleanup script is stdlib-only."
---

# Purge docs/dev/tmp

`docs/dev/tmp/` is globally gitignored and contains temporary development
assets only. Durable PRDs, plans, reviews, decisions, discovery, audits, and
automation state belong in tracked `docs/dev/project-management/` and are
never touched by this skill.

## Run

Dry-run first:

```bash
python3 ~/.agents/skills/purge-devtmp/scripts/purge_devtmp.py --all
```

`--all` scans Go-style checkouts under `~/git/src/` plus `~/.claude`.
Use `--repo <repo-root>` for explicit roots; a `docs/dev/tmp` path is also
accepted. The script refuses every other path.

Review the candidates, then apply:

```bash
python3 ~/.agents/skills/purge-devtmp/scripts/purge_devtmp.py --all --apply
```

Files and repository units whose relative path carries the number of a PRD
in backlog, wip, or hold are kept. A PRD number only inside a unit's member
path does not keep the unit.
Everything else older than seven days is moved to
`docs/dev/tmp/.trash/<date>/`. Nothing is directly unlinked. A directory that
holds a .git entry (a cloned or templated fixture) moves as one unit, so the
trash never has to recreate paths a sandbox refuses. Trash batches
older than 30 days are removed on later apply runs. Use
`--min-age-days`, `--age-days`, or `--empty-trash-days` to override the
defaults.

The manifest at `docs/dev/tmp/.trash/manifest.tsv` records date, rule,
original relative path, and trash path. Restore with `mv`.

A candidate path containing a tab or newline is refused and left in place,
reported as `refused-unsafe-path` with the reason; it is never trashed.
When a trash batch is emptied, its manifest rows are removed along with it
(rows from any cleanup tool sharing that batch date). Rows for retained
batches, unparseable historical rows, and rows whose batch failed to delete
are preserved.

## Tests

```bash
python3 -m pytest ~/.agents/skills/purge-devtmp/scripts/test_purge_devtmp.py -q
```
