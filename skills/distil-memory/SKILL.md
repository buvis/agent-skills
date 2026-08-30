---
name: distil-memory
description: Use when promoting durable facts from Claude Code session transcripts into memory - scans transcripts for measured/verified claims, filters to genuine assistant prose, triages survivors with a cheap-tier judge, and reports what to promote.
---

# Distil Memory

Mine Claude Code session transcripts for facts worth promoting into memory.
Scans a window of transcripts for assistant-authored claims carrying a
measured/verified/confirmed/reproduced/proven marker, strips out anything
that isn't the model's own authored prose (tool calls, thinking, compaction
summaries, non-assistant turns), then asks a cheap-tier judge to separate
durable facts from transient confirmations (a passing test, a repeated "yes
it works"). What survives becomes a yield report naming what to review and
promote by hand - this skill never writes to memory itself.

## Dependencies

- `claude-checkup:audit-sessions`'s `parser.py`
  (`~/.claude/plugins/cache/buvis-plugins/claude-checkup/*/skills/audit-sessions/scripts/parser.py`),
  minimum version `0.2.2`. `corpus.py`'s `resolve_parser()` dynamically
  imports the highest-versioned installed copy directly (not a package
  import); `assert_contract()` hard-fails below `0.2.2`, the release that
  fixed `d10ecb1`'s `promptSource=="sdk"` bug - older parsers over-count
  user prompts by roughly 41%. Absent or stale cache raises
  `StaleParserError`; `funnel.py`'s `main()` catches it, prints to stderr,
  and exits `1` - there is no fallback.

## Invocation

```bash
python3 ~/.agents/skills/distil-memory/scripts/funnel.py [--days N] [--all] [--project NAME] [--dry-run]
```

## Flags

- `--days N` (default `30`): only include transcripts whose latest activity
  is on or after `now - N days` (UTC). A transcript whose date can't be
  determined - `parse_session()` returns `None`, or `SessionData.latest` is
  `None` - is kept regardless, since there's no evidence to justify dropping
  it.
- `--all`: skip the date filter entirely; every transcript under
  `~/.claude/projects/` is read regardless of age. Overrides `--days`.
- `--project NAME`: restrict to project directories whose name ends with
  `-NAME` (Claude Code encodes the repo path into the directory name, so
  this matches on the trailing project segment).
- `--dry-run`: run selection and scanning only, skip the judge-triage stage.
  `survivors` renders as `n/a` in the yield report. Use this to preview
  `slices_matched`/`slices_kept` before spending judge calls.

## Pipeline

1. **Select** (`corpus.py:select_transcripts`): resolve the
   highest-versioned `claude-checkup` parser (see Dependencies), then list
   transcripts under `~/.claude/projects/` filtered by
   `--days`/`--all`/`--project`.
2. **Scan** (`funnel.py:scan`): one read pass per transcript. Counts every
   raw marker hit (`measured`, `verified`, `confirmed`, `reproduced`,
   `proven`, case-insensitive, word-boundary) across all assistant-role text
   blocks as `slices_matched`, before filtering. Then applies
   `assistant_only` (drops non-assistant entries, `isMeta` entries,
   compaction summaries, non-text content blocks, and empty/whitespace
   text) and marker-matches what's left; survivors of both are
   `slices_kept`.
3. **Triage** (`funnel.py:triage`, skipped on `--dry-run`): a cheap-tier
   (`haiku`) judge classifies each kept slice as `transient` (verifies
   something already known or already working) or `durable` (a new fact
   worth remembering). Fail-open: any judge response other than an exact
   `transient` match keeps the slice. What's left is `survivors`.
4. **Report** (`funnel.py:render_yield`): prints the yield report and
   writes it to `dev/local/audit-results/distil-memory-<UTC timestamp>.md`
   (`%Y%m%dT%H%M%SZ`).

## Yield report

Four stages, in order:

- `transcripts_read` - transcripts selected by step 1.
- `slices_matched` - raw marker hits found in step 2, before
  `assistant_only` filtering.
- `slices_kept` - marker-matched slices that survived `assistant_only`
  filtering.
- `survivors` - slices that survived judge triage (`n/a` on `--dry-run`).

Written to `dev/local/audit-results/distil-memory-<UTC timestamp>.md`.
Review the survivors by hand and promote durable facts into memory - this
skill stops at the report and never writes to memory itself.
