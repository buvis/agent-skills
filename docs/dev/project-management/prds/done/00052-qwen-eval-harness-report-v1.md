---
catchup: force
design: skip
default_model: sonnet
model_tier_rationale: transcribes pinned markdown shapes from a fixed record contract; every count is asserted against the records by a named test
consensus_engine: shadow
---

# Qwen Eval Harness Report

## Overview

### Problem Statement

PRD 00051 leaves a round as a directory of `attempt.json` records. The
2026-09-03 report for PRD 00010 was typed by hand from such evidence, and
its review (`dev/local/reviews/00010-qwen38-multifile-capability-eval-v1-review-01.md`)
found the cost of that: a baseline logged as exit 1 while the artifact says
2, a report naming `*.prompt.md` files that are `*.prompt.txt`, a candidate
inventory that says seven prospects and counts eight, and a false-claim
flag the audit contract does not support. A count typed by a person drifts
from the file it summarises; a count computed from the file cannot.

This PRD adds the `render` subcommand that turns 00051's records into
`evidence.md`, `report.md` and an audit queue, refuses to show a false-claim
count until every valid attempt has an audit verdict, and documents the
harness in the use-qwen runbook and SKILL.md so a fresh session can run a
round from the docs alone. It applies no decision rule: PRD 00050 (or any
later round) reads the counts and applies its own. Re-check every premise
below at execution.

### Target Users

The maintainer reading a round's result, the session auditing transcripts,
and PRD 00050, whose report is these rendered counts plus hand-written
comparison prose.

### Success Metrics

- Every count in `report.md` is independently reproducible from attempt
  records, the run's task/engine inventory and incomplete attempt directories;
  reported measurements come from recorded telemetry, with null shown as unavailable.
- A round with an unaudited valid attempt shows `pending (k of n audited)`
  for the false-claim count and states that no decision rule may be applied.
- A fresh session can run `vet`, `run` and `render` on the fixture repo by
  following `eval-runbook.md` alone.

## Functional Decomposition

### Capability: Evidence Rendering

Turn attempt records into evidence blocks, tables and an audit queue without
retyping a number.

#### Feature: Evidence log
- **Description**: `run_eval_harness.py render <evidence-dir> --run-id <id>`
  writes `runs/<run-id>/evidence.md`.
- **Inputs**: every `runs/<run-id>/<n>-<engine>-a<k>/attempt.json` and its
  sibling files, `run.json`, each task's `vetting.json`.
- **Outputs**: `evidence.md`: the run config and recorded versions first,
  then a `## Setup` block per task (template sha, warmup, baseline,
  canonical and necessity results from `vetting.json`), then one block per
  attempt in the 00010 design's C6 shape (`dev/local/designs/00010-qwen38-multifile-capability-eval-v1-design.md`
  § C6): tree, dispatch argv, engine identity, captured output paths and
  byte sizes, dispatch exit code and validity, baseline exit code with its
  first failure line, changed files with `dropped` and `stray`, own, gate
  and ablation exit codes, `Result`, then the engine output and the gate
  output embedded verbatim in `<details>` blocks.
- **Behavior**: Blocks are ordered by task then engine then attempt. An
  attempt directory without `attempt.json` renders a block whose `Result`
  is `INCOMPLETE` and whose other fields are `n/a`. Nothing is inferred
  from prose; every field comes from a record key.

#### Feature: Scoreboard
- **Description**: The same `render` call writes `runs/<run-id>/report.md`.
- **Inputs**: the version-1 record contracts from PRD 00051, `run.json`,
  task `vetting.json` files and `audit.jsonl` when present. Task kind/repo
  come from `run.json.tasks`, never inferred from prose or path names.
- **Outputs**: `report.md` with, in order: `## Run` (flags, bound, shape,
  engines, declared reasoning effort, versions, server props); `## Scores`
  (one row per task: task, kind, repo, each engine's effective outcome and
  class, attempts per engine); `## Counts` (per engine: attempts, `PASS`,
  `FAIL` by class, `TIMEOUT`, `SUSPECT`, `DISCARDED`, `INCOMPLETE`, and the
  derived `scored` = tasks whose latest attempt for every requested engine
  has a record with launch `started` or `unknown` (including post-launch
  failures/timeouts; excluding verified unstarted and incomplete attempts), `drops` =
  `FAIL:dropped-a-file` count, `f` = flagged audit rows on `VALID` attempts);
  `## Classification` (one row per `FAIL`: engine, task, class, the record
  field that decided it); `## Vetting` (per task: baseline rc, canonical rc,
  necessity per path). Append `## Measurements`: per attempt, dispatch
  wall_s, first_edit_s, the five usage fields and audit review_effort_s.
  Render null as `unavailable`; zero stays numeric zero. Values come from
  records, not estimates or token-to-money conversions.
- **Behavior**: The effective outcome per task and engine is the last
  numbered attempt directory's outcome, or INCOMPLETE if its record is
  missing; never fall back to an older attempt. Outcomes/counts include
  every attempt directory, including verified pre-launch discards before
  a retry. A planned task/engine without any directory is NOT_STARTED in
  Scores, counted separately under `not_started`, and not an attempt.
  This also defines single-engine runs; no absent second engine is invented.
  `f` renders as `pending (k of n
  audited)` until every `VALID` attempt has a row in `audit.jsonl`; with zero
  VALID attempts f is 0 even when no audit file exists. While rows are missing the
  report then carries the sentence "Audit incomplete: no decision rule may
  be applied to these counts." `render` validates stored outcomes/classes
  against 00051's pure classifier and rejects inconsistent/corrupt records
  naming their path. It never applies a decision rule, writes outside
  `runs/<run-id>/`, or overwrites a consumer-authored `comparison.md`.

#### Feature: Audit queue
- **Description**: `render` writes `runs/<run-id>/audit-queue.md` and reads
  `runs/<run-id>/audit.jsonl`.
- **Inputs**: the `VALID` attempts' `out.txt`, `session.jsonl`, `gate.rc`,
  `status.txt`; the hand-written `audit.jsonl` (one JSON object per line:
  `attempt_dir`, `verdict` in `clean|flagged|unverifiable`, `claim`,
  `evidence`, `review_verdict`, `review_findings`, `review_effort_s`).
  attempt_dir is the relative attempt-directory basename; claim/evidence
  are strings, nonempty for flagged claims. review_verdict is
  `clean|blocking|unverifiable`; review_findings is a list of strings,
  nonempty for blocking reviews; review_effort_s is nonnegative seconds or
  null. Claim truth and substantive code review are separate verdicts.
- **Outputs**: `audit-queue.md`: one section per `VALID` attempt with the
  final message path and byte size, the session log path or `none`, the
  gate exit code, the changed-file list, and `verdict: <from audit.jsonl or
  PENDING>`.
- **Behavior**: Require exactly one row per audited VALID attempt. A
  duplicate attempt_dir, unknown/non-VALID attempt, missing/extra key,
  invalid value/type or malformed JSON fails `render` naming the line;
  do not silently select first/last or double-count duplicates. Validate
  all input before replacing any rendered file. With no invalid input,
  missing rows remain PENDING and do not prevent rendering the audit queue.
  Sonnet attempts may carry `unverifiable`; the count `f` includes only
  `flagged` rows on `VALID` attempts, matching the 00010 design's C7.

### Capability: Documentation

Make the harness the documented path for multi-file and TDD-shape rounds.

#### Feature: Runbook section
- **Description**: Add `## 7. Harness rounds` to
  `skills/use-qwen/references/eval-runbook.md`.
- **Inputs**: the runbook as it is; the CLI from PRD 00051 and this PRD.
- **Outputs**: a new section before `## Scope of approval` (about 25 lines):
  when to use the harness (any round that is multi-file, TDD-shape, or
  compares two engines), the three commands in order with their required
  flags, where the evidence lands, the statement that tree reconstruction,
  fresh per-attempt baselines, serial gates and process-tree
  bounds are enforced by code in harness rounds, and that
  single-file qualification stays on `run-eval.sh` (§ 1-5).
- **Behavior**: Premise: the runbook has `## 1.` through `## 6.` followed
  by `## Scope of approval` and no `## 7.`; re-check with
  `rg -n "^## " skills/use-qwen/references/eval-runbook.md`, skip and
  report if the shape differs. Existing § 1-6 text is not rewritten; § 7
  explicitly states that historical 00010 scores are invalid and its
  reverse-patch/manual snapshot procedure does not govern harness rounds.
  00010 is in done/, with no pending repair task assumed by this PRD.

#### Feature: SKILL.md and CHANGELOG
- **Description**: One bullet in `skills/use-qwen/SKILL.md` Onboarding step 2
  and CHANGELOG entries.
- **Inputs**: SKILL.md § Onboarding a New Model, step 2; `CHANGELOG.md`
  `[Unreleased]`.
- **Outputs**: after the step-2 numbered list, one bullet: "Multi-file,
  TDD-shape or two-engine rounds run through
  `~/.agents/skills/use-qwen/scripts/run_eval_harness.py` (`vet`, `run`, `render`; runbook § 7);
  qualification stays on `run-eval.sh`."; a `### Added` entry
  `**use-qwen**: render eval rounds into evidence, scoreboard and audit
  queue from attempt records (`run_eval_harness.py render`)`.
- **Behavior**: Premise: SKILL.md step 2 has no bullet naming
  `run_eval_harness.py`; re-check with `rg -n "run_eval_harness" skills/use-qwen/SKILL.md`,
  skip and report if present. The Default bullet and Model Selection scope
  text are untouched.

## Structural Decomposition

### Repository Structure

```
skills/use-qwen/
├── SKILL.md                              # Onboarding step 2: one bullet naming the harness
├── references/eval-runbook.md            # New § 7 Harness rounds; § 1-6 untouched
└── scripts/
    ├── run_eval_harness.py               # Gains the render subcommand
    ├── eval_harness/
    │   └── report.py                     # evidence.md, report.md, audit-queue.md, audit.jsonl reader
    └── test_run_eval_harness.py          # Adds render tests over a fixture round
CHANGELOG.md                              # Added: use-qwen render
```

### Module: Report
- **Maps to capability**: Evidence Rendering
- **Responsibility**: Own eval_harness/report.py, the entrypoint's render dispatch and render tests; read records/audit rows, write three markdown files and compute counts/measurements.
- **Exports**: `render()`, `load_audit()`, `count()`.

### Module: Harness Docs
- **Maps to capability**: Documentation
- **Responsibility**: Own references/eval-runbook.md § 7, the SKILL.md bullet and CHANGELOG entry.
- **Exports**: prose only.

## Dependency Graph

### Foundation Layer (Phase 0)
- **PRD 00051**: `vet`, `run`, the attempt record contract and the fixture
  round exist with green tests. This PRD builds nothing until it does.

### Core Layer (Phase 1)
- **Report**: Depends on [PRD 00051].

### Integration Layer (Phase 2)
- **Harness Docs**: Depends on [Report].

## Implementation Phases

### Phase 0: Foundation
**Goal**: Confirm the records this PRD reads exist as specified.

**Tasks**:
- [ ] Verify PRD 00051 landed (no deps). Premise: `skills/use-qwen/scripts/eval_harness/attempt.py`
  exists, `run_eval_harness.py run --help` exits 0, and
  `uv run pytest skills/use-qwen/scripts -q` passes; if any fails, record
  the shortfall and stop. Acceptance: a fixture round produced by 00051's
  test builder (two `cmd:` engines, both shapes, including one `TIMEOUT`,
  one `DISCARDED:harness` with retry and one `FAIL:test-mutation`) is
  available to the render tests as a pytest fixture.

**Exit Criteria**: The render tests have a fixture round to read.

### Phase 1: Core
**Goal**: `render` produces the three files from records alone.

**Tasks**:
- [ ] Implement `report.py` and the `render` subcommand (depends on: Phase 0).
  Acceptance: on the fixture round, `evidence.md` has one C6-shaped block
  per attempt directory including an `INCOMPLETE` block for a directory
  without `attempt.json`; `report.md` has the five original sections then
  Measurements in order; tests independently recount the records, run
  inventory and incomplete directories and assert every Counts number.
  Fixtures pin single-engine runs, retry-then-incomplete and never-started
  task/engine pairs, plus exact telemetry values and null/zero distinction.
  `f` renders
  `pending (0 of N audited)` with the audit-incomplete sentence when no
  `audit.jsonl` exists, `pending (k of N audited)` with a partial file,
  and a number with the sentence absent when every `VALID` attempt has a
  row; malformed or duplicate audit rows fail `render` naming their line
  and leave all existing output files unchanged; a contradictory stored
  outcome/class is rejected by re-derivation through classify();
  `audit-queue.md` lists exactly the `VALID` attempts with `PENDING` where
  no row exists. A sentinel comparison.md remains byte-identical after
  repeated rendering. `uv run pytest skills/use-qwen/scripts -q` passes.

**Exit Criteria**: `render` is idempotent on the fixture round and writes
nothing outside `runs/<run-id>/`.

### Phase 2: Integration
**Goal**: The docs carry the harness.

**Tasks**:
- [ ] Add runbook § 7, the SKILL.md bullet and the CHANGELOG entry (depends
  on: Phase 1). Premises as stated in the two Documentation features;
  re-check both and skip-and-report on mismatch. Acceptance:
  `rg -n "^## 7\. Harness rounds" skills/use-qwen/references/eval-runbook.md`
  matches once and `## Scope of approval` still follows it;
  `rg -c "run_eval_harness" skills/use-qwen/SKILL.md` prints 1;
  `uv run python3 skills/create-skill/scripts/validate_skill.py skills/use-qwen`,
  `braid --check`, `uv run pytest`, `bash skills/use-qwen/scripts/test_qwen_run.sh`
  and `bash skills/use-qwen/scripts/test_eval_automation.sh` pass; the
  diff touches no registry, default-model, routing or server file.

**Exit Criteria**: A fresh session can run `vet`, `run` and `render` on the
fixture repo by following the runbook alone.

## Test Strategy

### Critical Scenarios
- **Happy path**: fixture round fully audited → `report.md` counts equal
  the independent recount, `f` is a number, no audit-incomplete sentence.
- **Edge case**: one `VALID` attempt without an audit row → `f` shows
  `pending (k of n audited)` and the audit-incomplete sentence is present.
- **Edge case**: attempt directory missing `attempt.json` → `INCOMPLETE`
  block in `evidence.md`, counted under `INCOMPLETE`, never under any
  outcome.
- **Error case**: `audit.jsonl` row with `verdict: maybe` → `render` exits
  non-zero naming the line and writes no partial files.
- **Docs**: runbook shape differs from the premise → the docs task skips
  and reports instead of editing.

## Risks

- **Record contract drift**: `render` reads 00051's exact key set; the
  contract test in 00051 and the recount test here fail together when a
  key moves, so drift shows as a test failure, not a wrong count.
- **Hand-written audit rows**: a typo in `attempt_dir` would silently drop
  a verdict; `render` therefore fails on any row that matches no attempt.
- **Prose creep in the runbook**: § 7 is capped at about 25 lines and
  points at `--help` for flags, so the skill's context cost stays flat.
