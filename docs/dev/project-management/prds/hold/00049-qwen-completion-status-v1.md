---
catchup: run
design: run
default_model: opus
model_tier_rationale: streamed process completion, cancellation, and compatibility across dispatch and qualification
---

# Qwen Completion Status

## Overview

### Problem Statement

PRD 00010's task-5 Qwen trace ends with an assistant `stopReason: length`,
then compaction, no final answer, and a successful process exit. It contains
61 read-only tool calls over 53 minutes and no edit. `qwen-run.sh` forwards
Pi's process status without establishing that an answer completed.
`run-eval.sh` then retries any unsuccessful dispatch against the same tree,
which is unsafe once the first dispatch may have edited it.

Sources: the 2026-09-05 retrospective; the preserved task-5 session JSONL in
`dev/local/audit-results/qwen38-vs-sonnet-multifile-2026-09-03-bundle/runs/`;
`skills/use-qwen/scripts/{qwen-run,run-eval}.sh`. The September 4 review at
`dev/local/reviews/00010-qwen38-multifile-capability-eval-v1-review-01.md`
invalidates the comparative scores; the trace is a diagnostic, not a
qualification result. Re-check these implementation premises at execution.

Scope: make noninteractive completion status trustworthy and qualification
one-shot. Runtime upgrades, automatic continuation/retry, task correctness,
test protection, and routing policy are separate responsibilities. Autopilot
PRD 00174 already owns no-edit rejection, test protection, and routing.

### Target Users

The maintainer dispatching local implementation attempts unattended.

### Success Metrics

- A child exiting zero without a completed final answer never yields wrapper success.
- A completed read-only answer can succeed without a diff; tests still judge code correctness.
- One qualification task causes at most one implementation dispatch.
- No new public flags, model promotion, runtime installation, or external config edits.

## Functional Decomposition

### Capability: Observable Noninteractive Completion

Determine completion from actual engine events, independent of success prose.

#### Feature: Terminal-event validation
- **Description**: Inspect the structured Pi stream for every noninteractive prompt dispatch.
- **Inputs**: Existing prompt/provider/model flags, Pi's event stream, and child exit status.
- **Outputs**: Existing text or JSON output and a truthful process status.
- **Behavior**: Use Pi's existing JSON transport internally. Exit zero only
  when Pi exits zero and the last assistant message ends with `stopReason:
  stop` and non-whitespace text. Terminal `length`, `error`, `aborted`,
  missing assistant output, or malformed/truncated protocol is failure.
  Intermediate tool calls and compactions followed by a completed answer
  remain valid. A compaction event alone is never a completed answer.
  Failure uses the existing nonzero exit convention and stderr diagnostics
  naming the observed reason; never infer success from words such as "done".
  Preserve harmless provider-probe diagnostics separately from protocol events;
  00010's port-8080 probe warning also appeared on passing runs and is not failure.

#### Feature: Output and cancellation compatibility
- **Description**: Preserve the helper's existing interfaces while observing completion.
- **Inputs**: `-j`, `-o`, `-f`, `-R`, preflight and interactive/resume modes; termination signals.
- **Outputs**: Requested output capture and termination without an orphaned writer.
- **Behavior**: Text mode emits the completed final text; `-j` retains the
  structured events without a new envelope. `-o` still captures the requested
  output, including failure diagnostics. Preserve provider identity on
  stderr, leading-dash prompt handling, and guarded child stdin. Read-only
  tools stay read-only. Preflight, registration, interactive and resume
  behavior retain their current contracts. Stream observation must not add
  an unbounded buffer or detach children outside the caller's timeout group.
  Do not retry, fabricate a continuation, or reset the caller's deadline.

### Capability: Qualification Without Contaminated Retries

Keep an incomplete implementation attempt from silently becoming a fresh trial.

#### Feature: One dispatch per qualification task
- **Description**: Remove `run-eval.sh`'s same-tree implementation retry.
- **Inputs**: The existing six-row manifest and wrapper result for each row.
- **Outputs**: The existing evidence report and unchanged qualification thresholds.
- **Behavior**: Each row invokes `qwen-run.sh` once. On nonzero return, retain
  its exit status and diagnostic, withhold a gate PASS and registry commit,
  and continue recording the remaining rows. Do not call this a verified
  infrastructure fault or claim Pi never ran. A new trial requires a new
  invocation after the runbook's baseline restoration and verification.
  Passing rows still require the real gate and the existing false-claim audit.

## Structural Decomposition

### Repository Structure

```text
skills/use-qwen/
├── SKILL.md                         # Completion versus correctness
├── scripts/
│   ├── qwen-run.sh                   # Terminal validation and output compatibility
│   ├── test_qwen_run.sh             # Observable stream/exit/cancellation fixtures
│   ├── run-eval.sh                  # One dispatch per manifest row
│   └── test_eval_automation.sh      # Retry and registry regressions
└── references/eval-runbook.md        # Incomplete attempts and fresh-trial requirement
```

### Module: Dispatch Completion
- **Maps to capability**: Observable Noninteractive Completion
- **Responsibility**: Validate the engine's terminal state while preserving the CLI.
- **Exports**: Existing `qwen-run.sh` options, stdout/stderr, and exit status.

### Module: Dispatch Completion fixtures
- **Maps to capability**: Observable Noninteractive Completion
- **Responsibility**: Own test_qwen_run.sh's sanitized event and child-lifetime fixtures.
- **Exports**: Stubbed completion, output and cancellation regressions.

### Module: Qualification Evidence
- **Maps to capability**: Qualification Without Contaminated Retries
- **Responsibility**: Prevent retries from reusing potentially modified task state.
- **Exports**: Existing six-row manifest, evidence report, and registry gate.

## Dependency Graph

### Foundation Layer (Phase 0)
No dependencies - built first.

- **Dispatch Completion fixtures**: Sanitized Pi events and process behavior reproductions.

### Core Layer (Phase 1)
- **Dispatch Completion**: Depends on [Dispatch Completion fixtures].

### Integration Layer (Phase 2)
- **Qualification Evidence**: Depends on [Dispatch Completion].

## Implementation Phases

### Phase 0: Foundation
**Goal**: Reproduce the observable failure without an hour-long model run.

**Tasks**:
- [ ] Re-check the wrapper and installed Pi event schema; add sanitized fixtures
  for completed text, tool-only output, terminal length followed by compaction,
  recovered compaction, harmless probe chatter, malformed stream, and nonzero child exit (no deps).
  Acceptance: `bash skills/use-qwen/scripts/test_qwen_run.sh` demonstrates
  failure on the current incomplete-success cases and records the other
  cases' expected output/status. Keep existing assertions; adapt the Pi stub
  to emit real event shapes instead of deleting compatibility checks.
  If the premise is already fixed, retain regression coverage and report the skipped change.

**Exit Criteria**: The failure is reproducible using a local stub and mock endpoint.

### Phase 1: Core
**Goal**: Noninteractive wrapper success requires a completed final answer.

**Tasks**:
- [ ] Implement terminal validation and output compatibility (depends on: Phase 0).
  Acceptance: `bash skills/use-qwen/scripts/test_qwen_run.sh` passes all old
  and new cases; both default text and `-j`, with and without `-o`, reject
  incomplete streams and accept a normal read-only answer without file edits.
- [ ] Verify process-group termination while consuming a stream (depends on:
  Phase 1 terminal validation). Acceptance: the same suite times out a stub
  with a child writer and confirms both stop, no late sentinel write occurs,
  and a large stream is forwarded incrementally rather than accumulated.

**Exit Criteria**: Incomplete output cannot be mistaken for completion or outlive cancellation.

### Phase 2: Integration
**Goal**: Qualification respects failed attempts without same-tree retries.

**Tasks**:
- [ ] Replace the qualification retry loop with one dispatch per row (depends
  on: Phase 1). Acceptance: `bash skills/use-qwen/scripts/test_eval_automation.sh`
  passes fixtures where a stub edits a marker then fails, is invoked exactly
  once for that row, and cannot cause `--commit` to modify the registry.
- [ ] Document completion versus correctness, no automatic continuation, and
  the new-trial restoration requirement (depends on: Phase 2 qualification).
  Re-read the runbook before editing; historical PRD 00010 is in done/
  but its reviewed comparative scores remain invalid. No pending repair
  task in 00010 is assumed. Acceptance: both shell suites,
  `uv run pytest`, `uv run python3 skills/create-skill/scripts/validate_skill.py
  skills/use-qwen`, and `braid --check` pass; the diff contains no model,
  routing, global runtime, or installed-package changes.

**Exit Criteria**: Regression coverage and guidance agree on one-shot qualification.

## Test Strategy

### Critical Scenarios
- **Happy path**: Valid final answer after tools or compaction -> exit zero.
- **Edge case**: Valid analysis answer with no edits -> exit zero; no invented diff requirement.
- **Error case**: Length stop then compaction only -> nonzero, retained reason, no retry.
- **Error case**: Truncated JSON or child failure after partial edits -> nonzero, no registry update.
- **Cancellation**: Caller timeout -> parser and engine children stop together.

## Risks

- **Pi version drift**: Capture the tested version and derive fixtures from its actual protocol.
- **Existing stubs mask behavior**: Assert public output/status and child lifetime, not implementation strings.
- **Stricter status reduces apparent passes**: Expected; it detects incomplete runs without proving code wrong.
- **Recovery remains separate**: This work detects the compaction failure; it does not claim to fix Pi's continuation.

Unresolved questions: none. Implementation layout is resolved by the design phase.
