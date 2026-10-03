# 00008 - distil-memory yield, one project, 30-day window

Recorded 2026-08-30. This file records one real run of the built pipeline; it
changes no code.

## The command

Run once, from the repo root
(`/Users/bob/git/src/github.com/buvis/agent-skills`), in the background:

```bash
python3 skills/distil-memory/scripts/funnel.py --days 30 --project agent-skills --distil --distil-limit 5
```

Exit code 0. Nothing was printed to stderr, so no triage error, no distil
stage error and no publish error occurred.

**Selection used: the first one.** `--project agent-skills` matched one project
directory (`corpus.select_transcripts` keeps directories whose name ends with
`-agent-skills`) and selected 153 transcripts, so the no-`--project` fallback
was not needed and was not run.

Run wall time was roughly 58 minutes. Triage is not capped by `--distil-limit`:
it makes one cheap-tier call per kept slice, so 315 slices meant 315 sequential
`claude` calls. Only the distil stage was capped, at 5.

Artefacts (both written by the run, both read-only here):

- report: `dev/local/audit-results/distil-memory-20260830T162841Z.md`
- proposals: `dev/local/audit-results/distil-memory-20260830T162841Z-proposals/`

## The full yield report

Verbatim, as printed and as written to disk:

```
transcripts_read: 153
slices_matched: 315
slices_kept: 315
survivors: 123
proposals: 1
discards: 4
new_vs_update: 1/0
skipped_by_limit: 118
dedup_errors: 0
claude_checkup_version: 0.2.2

How to proceed: this report was also written to dev/local/audit-results/. Review the survivors and promote durable facts into memory. When the distil stage ran, its proposals are under dev/local/audit-results/proposals/.
```

Reading the nine counts:

| line | value | meaning |
|---|---|---|
| `transcripts_read` | 153 | transcripts selected by the 30-day, single-project filter |
| `slices_matched` | 315 | assistant text blocks carrying a raw marker hit, before `assistant_only` |
| `slices_kept` | 315 | of those, the ones surviving `assistant_only` |
| `survivors` | 123 | slices the cheap-tier judge called durable (192 triaged away) |
| `proposals` | 1 | complete memory files emitted by the distil stage |
| `discards` | 4 | survivors the distiller refused, reasons below |
| `new_vs_update` | 1/0 | the typed split |
| `skipped_by_limit` | 118 | survivors the `--distil-limit 5` cap never reached |
| `dedup_errors` | 0 | proposals whose typing could not be verified |

`slices_matched` and `slices_kept` are equal at 315: no marker-carrying
assistant block in this window was dropped as `isMeta` or as a compaction
summary. 5 of the 123 survivors were distilled (the cap), and those 5 produced
1 proposal and 4 discards, which accounts for every distilled slice.

## The new / update split

**1 new, 0 update.** The single proposal is `new`: `dedup.classify` found no
existing memory in the project's plane that it restates.

The one proposal:

- name: `plugin-ownership-check-needs-versioned-glob`
- kind: `new`
- `metadata.type`: `project` (the only type this skill emits)
- evidence: transcript `038e0e9c-...jsonl`, line 1575, in the single
  `-agent-skills` project directory
- substance: a plugin-ownership check globbed a plugin cache path without a
  version wildcard, so it answered `NONE` for six skill names that installed
  plugins already owned; a control case exposed the wrong glob
- it links `[[session-pins-plugin-version]]`, an existing memory, so the
  distil-stage link rule is satisfied

## Every discard, with its reason

Four discards. Transcripts are named by basename to keep home paths out of this
file; all four are in the one `-agent-skills` project directory.

**1. `038e0e9c-...jsonl`, line 421** - model judgment, not durable:

> every actionable item in the snippet is stale or already captured elsewhere.
> Verified against the current repo: `pyproject.toml` already has `testpaths =
> ["tests", "skills"]` and `pyyaml` in the dev group (the "two pytest commands"
> gap is fixed), and `skills/review-discovery-doc/SKILL.md` exists (the "dead
> pointer, doesn't exist in this repo" claim no longer holds). The remaining
> facts (the `${CLAUDE_SKILL_DIR}` corruption gotcha, the Dependencies-section
> convention) are explicitly stated as already documented in the repo's own
> AGENTS.md, which future sessions read directly - duplicating them here would
> just be a second, driftable copy of repo state rather than a fact worth
> remembering independently.

**2. `04673316-...jsonl`, line 38** - model judgment, not durable:

> this is a test-run report and line-level code-review findings for
> `skills/distil-memory/scripts/dedup.py` (TOCTOU double-syscall, missing
> docstring rationale) - the findings are either applied to the code (then
> git/the code is authoritative) or still open (then they belong in a
> PRD/review-tracking file, not agent memory). Nothing here is a fact that
> survives independent of the code's current state; a future session should
> read the file or the review report, not recall a stale line-number claim.

**3. `09bf8a55-...jsonl`, line 438** - validator rejection, not a model
judgment:

> the answer is not a usable memory file: body links to no other memory

**4. `14c35d58-...jsonl`, line 69** - model judgment, not durable:

> this is a single code-review finding (a parameter-name mismatch in `dedup.py`
> about to be fixed as part of the current review cycle), not a durable project
> fact - once addressed the code will show the correct signature, and until then
> it's directly visible by reading `skills/distil-memory/scripts/dedup.py:40-41`.
> Actionable review findings belong in the review's own tracking
> (ReportFindings/PRD), not in persistent memory.

Discard 3 is a different kind from the other three. Three are the strong model
declining a slice as transient. One is `validate_distil_output` refusing the
model's answer before it could become a proposal: the answer carried no
`[[link]]` while the plane's index does name memories. That is the designed
guard in `distil.distil` (a rejected answer becomes a named discard, never a bad
file), not a validation failure of an emitted proposal.

## dedup_error

**No proposal carries a `dedup_error`.** The report line reads `dedup_errors: 0`
and `proposals.json` records `"dedup_error": null` for the single proposal.
Every `new`/`update` verdict from this run is trustworthy: the memory index was
read, the shortlist was read, and the typing call returned.

## validate() on every emitted proposal

Every `*.md` in
`dev/local/audit-results/distil-memory-20260830T162841Z-proposals/` was loaded
into a `proposal.Proposal` and passed through `proposal.validate`.

- files checked: **1** (`plugin-ownership-check-needs-versioned-glob.md`)
- `proposal.validate`: **PASS** (1 of 1)
- failures: **none**

`proposal.validate_distil_output(..., index_has_names=True)`, the stricter
feature-owned validator, was run over the same file as a second check and also
passed. No defect to report.

## One observation, measured, outside the acceptance criteria

The funnel's own model calls land in the corpus it reads. Every `claude
--print` call runs with the repo root as cwd, so each one writes a new session
transcript into the same `-agent-skills` project directory the funnel scans.

Measured: that directory held 153 selectable transcripts when the run started
and 474 afterwards; 322 `.jsonl` files were created inside the run window,
against 321 model calls (315 triage + 5 distil + 1 dedup). Selection happens
before the first call, so this did not affect this run's numbers.

The effect on a later run looks small but is not zero: a mid-run count taken
after roughly 190 triage calls showed `slices_matched` rise from 315 to 316,
because a triage answer is the single word `durable` or `transient` and almost
never carries a marker. The cost is read volume, not false yield - though distil
answers are full memory files and can carry marker words. Recorded, not fixed;
no change was made to any code for this task.
