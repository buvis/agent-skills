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
promote by hand, and behind `--distil` a set of typed, evidenced proposals a
human reviews. A separate approval stage can write a proposal, but only after
an explicit per-entry decision.

## Dependencies

- `claude-checkup:audit-sessions`'s `parser.py`
  (`~/.claude/plugins/cache/buvis-plugins/claude-checkup/*/skills/audit-sessions/scripts/parser.py`),
  minimum version `0.2.2`. `corpus.py`'s `resolve_parser()` dynamically
  imports the highest-versioned installed copy directly (not a package
  import); `assert_contract()` hard-fails below `0.2.2`, the release that
  fixed `d10ecb1`'s `promptSource=="sdk"` bug - older parsers over-count
  user prompts by roughly 41%. `funnel.py`'s `main()` exits non-zero on
  three failure paths, each printing to stderr: an absent or stale cache
  raises `StaleParserError`; a triage model-call failure (the `claude` CLI
  errors, is missing, or times out); and a report-write failure. There is
  no fallback for any of the three.
- `encode-incident`, pointed at rather than invoked. It owns `feedback`
  memories; this skill emits `project` memories only, and neither skill reads
  or rewrites the other's type. Nothing here depends on it being installed.

## Invocation

```bash
python3 ~/.agents/skills/distil-memory/scripts/funnel.py [--days N] [--all] [--project NAME] [--dry-run] [--distil] [--distil-limit N]
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
  `survivors` renders as `n/a` in the yield report (it is also `n/a` after a
  triage model-call failure). Use this to preview `slices_matched`/`slices_kept`
  before spending judge calls.
- `--distil`: run the distil stage on the survivors (step 4). Ignored with
  `--dry-run`, since a dry run makes no model calls - the CLI prints a note to
  stderr saying so and continues.
- `--distil-limit N` (default `25`): cap how many survivors are distilled.
  `0` means no cap. A negative value is a usage error - argparse rejects it
  before the run starts.

## Pipeline

1. **Select** (`corpus.py:select_transcripts`): resolve the
   highest-versioned `claude-checkup` parser (see Dependencies), then list
   transcripts under `~/.claude/projects/` filtered by
   `--days`/`--all`/`--project`.
2. **Scan** (`funnel.py:scan`): one read pass per transcript. Counts every
   assistant-role text block carrying a raw marker hit (`measured`,
   `verified`, `confirmed`, `reproduced`, `proven`, case-insensitive,
   word-boundary) as one `slices_matched`, before filtering - a block with
   three markers still counts as one. Then applies
   `assistant_only` (drops non-assistant entries, `isMeta` entries,
   compaction summaries, non-text content blocks, and empty/whitespace
   text) and marker-matches what's left; survivors of both are
   `slices_kept`.
3. **Triage** (`funnel.py:triage`, skipped on `--dry-run`): a cheap-tier
   (`haiku`) judge classifies each kept slice as `transient` (verifies
   something already known or already working) or `durable` (a new fact
   worth remembering). Fail-open: any judge response other than an exact
   `transient` match keeps the slice. What's left is `survivors`.
4. **Distil** (`funnel.py:_distil_and_publish`, runs only behind `--distil`):
   calls `distil.distil` at the `strong` tier to turn each surviving slice
   into either a complete memory file (a proposal, carrying the transcript
   path, line number and slice text it came from) or a discard naming why it
   was refused. Each proposal is then typed with `dedup.classify`, also
   `strong` tier: `new`, or `update <existing-name>` when the proposal
   restates a memory that already exists. Deduplication is two steps on
   purpose - `dedup.shortlist` narrows the field using MEMORY.md's recall
   cues, and only the shortlisted memory files are then read. Reading every
   memory file on every proposal is the cost this two-step avoids.
5. **Report** (`funnel.py:render_yield`): prints the yield report and
   writes it to `dev/local/audit-results/distil-memory-<UTC timestamp>.md`
   (`%Y%m%dT%H%M%SZ`).

## Yield report

Nine counts, in order - four from stages 1-3, then five from the distil stage:

- `transcripts_read` - transcripts selected by step 1.
- `slices_matched` - assistant-role text blocks carrying a raw marker hit
  found in step 2, before `assistant_only` filtering (one per block, not
  one per marker).
- `slices_kept` - marker-matched slices that survived `assistant_only`
  filtering.
- `survivors` - slices that survived judge triage (`n/a` on `--dry-run` and
  also `n/a` after a triage model-call failure).
- `proposals` - complete memory files emitted by step 4.
- `discards` - slices the distiller refused, each with a reason.
- `new_vs_update` - the split of typed proposals, rendered `<new>/<update>`.
- `skipped_by_limit` - survivors the `--distil-limit` cap skipped.
- `dedup_errors` - proposals whose typing could not be verified (the memory
  plane or a shortlisted candidate could not be read). The proposal is kept,
  but its `new`/`update` verdict is not trustworthy.

All five distil lines render `n/a` when the distil stage did not run; a stage
that ran and yielded nothing reports `0`.

Written to `dev/local/audit-results/distil-memory-<UTC timestamp>.md`. The
distil stage writes
`dev/local/audit-results/distil-memory-<UTC timestamp>-proposals/` beside it,
sharing the run's one timestamp: one `<name>.md` per proposal (the complete
memory file) plus `proposals.json` and `discards.json`. That directory is
published atomically - a reader sees a complete directory or none at all,
never a partial one.

Review the survivors and proposals by hand. The five-stage pipeline stops at
typed, evidenced proposals. Use the approval stage below to decide whether to
write each one.

## Approval walkthrough (stage 6)

This stage is invoked after a distil run has published a proposals directory.
There is no always-on hook; this stage is invoked, never triggered. No
automatic write anywhere: nothing reaches a memory directory without an
explicit per-entry decision.

Before the first sitting, add the published proposals to the durable queue:

```bash
python3 ~/.agents/skills/distil-memory/scripts/queue.py save --proposals-dir <proposals-dir>
```

Then run this walkthrough in chat. Ask about one entry at a time, with no bulk
approval or rejection:

1. Start the sitting once. This resets the sitting's decision count, not the
   lifetime cursor:

   ```bash
   python3 ~/.agents/skills/distil-memory/scripts/queue.py start
   ```

2. Get the next undecided entry and keep the printed JSON as `entry.json`:

   ```bash
   python3 ~/.agents/skills/distil-memory/scripts/queue.py next > entry.json
   ```

   Empty output with exit 1 means either the queue is drained or this sitting
   has reached `queue.PER_RUN_CAP` (10). Stop and report. `next` enforces the
   cap itself, so do not count decisions in chat.

3. Show `transcript`, `line_no`, and `evidence_text`, then show the proposed
   `file_text`. For an update, show `existing_text` beside `file_text`. Ask for
   one decision: keep, edit, or drop.

4. For drop, record the decision and return to step 2:

   ```bash
   python3 ~/.agents/skills/distil-memory/scripts/queue.py decide "<id>" dropped
   ```

5. For keep with no edit, record the decision, derive the store path as
   `Path(entry["transcript"]).parent / "memory"`, then write the saved entry:

   ```bash
   python3 ~/.agents/skills/distil-memory/scripts/queue.py decide "<id>" kept
   python3 ~/.agents/skills/distil-memory/scripts/write.py write --store "<store-path>" < entry.json
   ```

   The driver computes `<store-path>` from the entry. Neither `queue.py` nor
   `write.py` computes it. `write.py` prints the memory file path, followed by
   the `MEMORY.md` pointer line or the literal `MEMORY.md: unchanged`.

6. For edit, use `funnel.judge(prompt, "strong")`, the skill's one model-call
   route, to re-emit the whole memory file with the requested change. Validate
   that whole file with `proposal.validate_distil_output` before replacing the
   queued `file_text`. If validation fails, report the failure, write nothing,
   and leave the proposal undecided. A re-emitted file failing the frontmatter
   contract is not written, and the proposal stays undecided.

   After validation succeeds, replace `file_text` in the driver's saved
   `entry.json`, save the same text as `<edited-file-path>`, then run:

   ```bash
   python3 ~/.agents/skills/distil-memory/scripts/queue.py decide "<id>" kept --file "<edited-file-path>"
   python3 ~/.agents/skills/distil-memory/scripts/write.py write --store "<store-path>" < entry.json
   ```

   Derive `<store-path>` with the same expression from step 5. The `--file`
   value replaces the queue entry's `file_text`; the refreshed `entry.json`
   gives that same replacement to `write.py`. Return to step 2 after any
   completed decision.

7. When `next` exits 1, write a sitting report under
   `dev/local/audit-results/`. Include counts of kept without edit, edited, and
   dropped entries, the lifetime cursor printed by:

   ```bash
   python3 ~/.agents/skills/distil-memory/scripts/queue.py cursor
   ```

   Also include every path written. Compare the cursor with the total entry
   count in `dev/local/audit-results/distil-memory-queue.json` to distinguish a
   drained queue from a sitting that stopped at the cap. End with this verbatim
   block:

   ```text
   How to proceed: this report was also written to dev/local/audit-results/. Review the survivors and promote durable facts into memory.
   ```

## Out of scope

- **Corrections as a second signal.** The measured yield is thin - 11 raw
  matches across 8 files - and no detector, criterion or funnel stage is
  specified for them.
- **Cross-project routing.** A fact established about repo B during a session
  in repo A is proposed into repo A's memory. Having the model guess the
  target repo is the same class of mistake as the encoder bug that was
  retired.
