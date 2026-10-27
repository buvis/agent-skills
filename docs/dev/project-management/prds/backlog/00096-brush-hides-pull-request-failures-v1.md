---
design: skip
default_model: sonnet
model_tier_rationale: bounded GitHub probe error propagation and cleanup guard documentation with mocked regression tests
---

# brush hides failures while checking open pull requests

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 7,
accepted option A on 2026-10-26. Also covers finding 17 of the 2026-10-25 report.
The reports are local audit artifacts and are not shipped in the public repository.
Status: mocked evidence; the failure was simulated, not observed against live GitHub.

## Problem

Brush's fact collector silently returns unknown pull-request information when
the GitHub command fails, and accepts a non-list JSON response as pull-request
data. Operators depend on these facts to preserve branches with open pull
requests. An expired token, rate limit, or service error can therefore make a
protected branch look eligible for cleanup.

## Solution

Have the pull-request probe return a list only after a successful, list-shaped
reply. Return None directly only when the GitHub command is absent. Propagate
execution and response errors through the collector's existing warning mechanism,
which records an open_prs-prefixed reason and an unknown section value while
continuing other probes. Document that unknown pull-request status blocks branch
deletion and that warnings must be read before selecting cleanup actions.

## Requirements

### Must have

- Successful list replies, including an empty list, retain their normal meaning.
- Failed execution, malformed JSON, non-list JSON, and timeouts produce a
  warning identifying the open pull-request probe and its failure reason.
- An error object must never be exposed as a successful pull-request list.
- Missing GitHub tooling remains an unknown result rather than an empty list.
- Other fact sections remain available when the pull-request probe fails.
- Cleanup instructions prohibit branch deletion whenever open pull-request
  information is null, malformed, or accompanied by a probe failure warning.

### Nice to have

- None.

## Implementation

```text
skills/brush/
├── references/hygiene-rules.md  # unknown PR information prohibits branch deletion
└── scripts/
    ├── collect_facts.py        # validate replies and surface failures as warnings
    └── test_brush_scripts.py   # probe and collector-output regressions
```

### Module: pull-request facts

- **Location**: `skills/brush/scripts/collect_facts.py`
- **Maps-to-capability**: distinguish no open pull requests from unavailable information.
- **Responsibility**: validate probe results and propagate failures into warnings.
- **Exports**: `gather_prs`, `main`.

#### Feature: warn when pull-request status is unknown

- **Inputs**: command availability, exit status, output, and execution exceptions.
- **Outputs**: a valid list or unknown status; failures include an actionable warning.
- **Behavior**: retain direct None for absent tooling; propagate other failures to
  the existing collector exception handler rather than silently returning None.

### Module: probe regression tests

- **Location**: `skills/brush/scripts/test_brush_scripts.py`
- **Maps-to-capability**: prevent simulated API failures from looking like empty results.
- **Responsibility**: assert collector warnings and valid-list controls in temporary repos.
- **Exports**: none.

### Module: cleanup guards

- **Location**: `skills/brush/references/hygiene-rules.md`
- **Maps-to-capability**: preserve branches when pull-request information is unavailable.
- **Responsibility**: require reading warnings and prohibit unsafe branch deletion.
- **Exports**: none.

### Dependencies

- Pull-request facts: existing subprocess probe and section warning handler (foundation).
- Probe regression tests and cleanup guards: depend on the warning contract.
- Other fact sections continue through the existing collector loop (integration).

## Tasks

### Phase 0: Foundation

- [ ] Add regressions using a simulated GitHub command or controlled subprocess
  seam for successful lists, an empty list, a non-zero exit, an error object,
  malformed JSON, a timeout, and missing tooling. Propagate failures from
  the pull-request probe and validate the reply shape. Assert the final collector
  output includes an open_prs-prefixed warning on failures, preserves other fact
  sections, and never treats an error object as a list. Update cleanup guards
  to prohibit branch deletion when this information is unknown.
  Acceptance: `uv run pytest skills/brush/scripts/test_brush_scripts.py` passes;
  the failed-command and non-list warning cases fail against the prior code.
  Tests use temporary repositories and do not call live GitHub or delete branches.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/brush`,
and `braid --check` pass.

## Success Criteria

- Simulated GitHub failures are visible in collector warnings.
- Successful empty lists remain distinguishable from unknown status.
- Cleanup instructions explicitly prevent branch deletion on unknown PR status.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
`--repo <scratch> --fast`: ok -> `open_prs=[{"number": 7, "headRefName": "feat-x"...}] warnings=[]`; exit 1 -> `open_prs= null warnings= []`, exit 0; 200 with `{"message":"Bad credentials"}` -> `open_prs= {"message": "Bad credentials"} warnings= []`.
```

This evidence used a PATH shim. The regression tests validate handling of simulated
failures; they do not establish which errors live GitHub will return.

### Risks

Consumers that ignore warnings can still misuse unknown information; the guard
documentation must make null different from an empty list. Additional warnings
change observable output for existing consumers, but should not stop unrelated probes.
