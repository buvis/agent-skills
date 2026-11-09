---
design: skip
default_model: sonnet
model_tier_rationale: bounded triage outcome accounting with explicit report/status and fail-open compatibility tests
---

# Unusable judge replies silently pass memory candidates through

Source: agoge report `dev/local/audit-results/agoge-2026-10-25.md`, finding 16,
accepted option A on 2026-10-29. Reports are local audit artifacts and are not
shipped in the public repository. The observed responses came from a judge shim,
not a live model/authentication failure.

## Problem

Triage discards only an exact transient response and keeps everything else.
Empty output or an authentication-error string with exit 0 therefore retains
all candidates while reporting success. Operators cannot distinguish usable
classification from a judge that never answered the task.

## Solution

Classify normalized replies as transient, durable, or unclassified. Report the
unclassified count and warn when replies are unusable. For a nonempty triage
where every reply is unclassified, return exit 1 and retain the diagnostic report
rather than treating triage as successful. Preserve fail-open item retention
for unclassified replies in mixed runs.

## Requirements

### Must have

- Match transient/durable exactly after the existing case/whitespace normalization.
- Empty, error-like, and other unexpected replies count as unclassified, not as
  confirmed durable judgments.
- Show the unclassified count in the yield report and warn without echoing
  transcript snippets or arbitrary judge output.
- A nonempty all-unclassified triage yields exit 1 and a written diagnostic report;
  downstream distillation/publication does not treat that failed triage as successful.
- Mixed runs retain unclassified candidates per the accepted fail-open policy
  while distinguishing them from explicit durable replies in accounting.
- Empty candidate sets and dry-run are not all-unclassified failures; counts for
  a stage that did not run remain unavailable rather than fabricated.
- Perform one judge pass without the preflight/model-call cost proposed by option C.
- Preserve model-call failure behavior and PRD 00133's no-tools/data-framing restrictions.

### Nice to have

- None.

## Implementation

```text
skills/distil-memory/
├── SKILL.md                              # describe unclassified reporting/failure semantics
└── scripts/
    ├── funnel.py                         # classify replies and propagate counts/status
    ├── test_funnel_triage.py              # reply classes and mixed fail-open behavior
    ├── test_funnel_report.py              # count rendering and unavailable-stage controls
    ├── test_funnel_main.py                # all-unclassified status/report integration
    ├── test_funnel_distil.py              # retained report/integration expectations
    └── test_funnel_distil_publication.py   # failed triage cannot publish as success
```

### Module: triage outcome accounting

- **Location**: `skills/distil-memory/scripts/funnel.py`
- **Maps-to-capability**: distinguish usable classification from retained unknown replies.
- **Responsibility**: propagate one-pass reply counts, warnings, and all-unclassified failure.
- **Exports**: `triage`, `_run_triage`, `render_yield`, `main`.

#### Feature: report unclassified replies honestly

- **Inputs**: judge replies and triage stage state.
- **Outputs**: retained/discarded candidates, explicit unclassified count, and failure
  for a nonempty run with no usable judgments.
- **Behavior**: preserve mixed-run fail-open retention, but do not count unknown
  replies as positive durable judgments or let an all-unknown stage report success.

### Module: triage/report regressions

- **Locations**: `skills/distil-memory/scripts/test_funnel_triage.py`,
  `skills/distil-memory/scripts/test_funnel_report.py`,
  `skills/distil-memory/scripts/test_funnel_main.py`,
  `skills/distil-memory/scripts/test_funnel_distil.py`,
  `skills/distil-memory/scripts/test_funnel_distil_publication.py`.
- **Maps-to-capability**: verify counts, status, retention, and downstream behavior together.
- **Responsibility**: test controlled replies without calling a live model.
- **Exports**: none.

### Module: operator instructions

- **Location**: `skills/distil-memory/SKILL.md`
- **Maps-to-capability**: explain unknown retained candidates and unusable triage runs.
- **Responsibility**: document the new count and all-unclassified exit behavior.
- **Exports**: none.

### Dependencies

- Reply accounting: existing triage and judge boundary (foundation).
- Report/status and publication control: depend on explicit reply counts/outcome.
- Tests/instructions: depend on that contract and retain existing no-tools handling.

## Tasks

### Phase 0: Foundation

- [ ] Add controlled-response regressions for empty output, authentication-error
  text, unexpected prose, valid normalized labels, and mixed replies. Add explicit
  unclassified accounting and warnings. Assert a nonempty all-unclassified run
  writes its report, exits 1, and does not run downstream publication; mixed
  runs keep unknown candidates while reporting the count. Preserve dry-run,
  zero-input, model-error, one-pass, and prompt-privacy controls. Update affected
  report expectations and skill prose without weakening their existing assertions.
  Acceptance: `uv run pytest skills/distil-memory/scripts/test_funnel_triage.py skills/distil-memory/scripts/test_funnel_report.py skills/distil-memory/scripts/test_funnel_main.py skills/distil-memory/scripts/test_funnel_distil.py skills/distil-memory/scripts/test_funnel_distil_publication.py`
  passes; the all-unclassified success/absence-of-count regressions fail against prior code.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/distil-memory`,
and `braid --check` pass.

## Success Criteria

- Unusable judge output is counted and visible rather than implied durable.
- All-unclassified runs fail clearly while preserving a diagnostic report.
- Mixed-run fail-open retention and valid-label behavior remain correct.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
claude shim printing nothing, exit 0 -> `survivors: 2`, rc 0. Shim printing `Invalid API key` -> `survivors: 2`. Control `transient` -> 0.
```

Use fake judges or subprocess seams and temporary report roots, not live model calls.

### Risks

Mixed runs still retain unclassified items, which is the accepted tradeoff.
Callers relying on silent all-unknown success now receive exit 1. Count propagation
must not trigger a second judge pass or weaken PRD 00133's tool restrictions.
