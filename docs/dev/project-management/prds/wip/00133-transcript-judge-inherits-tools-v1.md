---
design: skip
default_model: sonnet
model_tier_rationale: bounded no-tools judge invocation and untrusted-data framing with subprocess-seam regressions
---

# Transcript instructions reach a judge without tool restrictions

Source: agoge report `dev/local/audit-results/agoge-2026-10-25.md`, finding 7,
accepted option A on 2026-10-29. Reports are local audit artifacts and are not
shipped in the public repository. Evidence used a command shim; real model
obedience to injected instructions was not tested.

## Problem

The memory triage judge receives raw transcript snippets in its prompt and
invokes the CLI without restricting tools. A hostile snippet could therefore
ask the judge to perform actions outside its text-classification purpose.
The exposure is suspected; the audit established prompt/argument wiring rather
than successful exploitation against a real model.

## Solution

Disable judge tools at invocation and delimit snippets explicitly as untrusted
classification data. Preserve the prompt's classification instruction outside
that data. Restrict inherited MCP configuration as well as built-in tools,
without changing global settings or relying on delimiters as a security boundary.

## Requirements

### Must have

- Invoke the judge with no built-in tools using the supported CLI option.
- Prevent inherited MCP tools from reintroducing action capabilities.
- Use subprocess argv entries that preserve an actual empty tool-list argument;
  omitting a value must not restore default tools.
- Delimit/encode transcript snippets as untrusted data, with classification
  instructions outside the data representation.
- Preserve stdin prompt delivery, model-tier resolution, timeout, and session-persistence settings.
- Unsupported restriction flags or other CLI failures remain visible; never retry
  the same untrusted input with tools enabled.
- Preserve existing classification semantics; empty/error-output classification
  policy is older finding 16 and is not silently changed here.

### Nice to have

- None.

## Implementation

```text
skills/distil-memory/scripts/
├── funnel.py               # no-tools invocation and untrusted snippet framing
├── test_funnel_triage.py   # subprocess argv and adversarial snippet coverage
└── test_funnel_main.py     # adjust prompt-aware fakes, retaining integration assertions
```

### Module: restricted text judge

- **Location**: `skills/distil-memory/scripts/funnel.py`
- **Maps-to-capability**: classify transcript data without granting tool actions.
- **Responsibility**: restrict the child invocation and frame snippets as data.
- **Exports**: `judge`, `triage`.

#### Feature: run a no-tools classifier

- **Inputs**: transcript snippet and classification instruction.
- **Outputs**: existing classifier text or an existing controlled CLI failure.
- **Behavior**: pass untrusted text through stdin with tools disabled and no
  inherited MCP capabilities; do not weaken restrictions after an error.

### Module: judge regression tests

- **Locations**: `skills/distil-memory/scripts/test_funnel_triage.py`,
  `skills/distil-memory/scripts/test_funnel_main.py`.
- **Maps-to-capability**: prove restrictive invocation survives malicious snippet text.
- **Responsibility**: assert argv, framing, and existing classification/model controls.
- **Exports**: none.

### Dependencies

- Restricted judge: existing CLI subprocess boundary (foundation).
- Regression tests: depend on the invocation and prompt contract.
- Existing funnel filtering, reporting, and publication behavior remain integration controls.

## Tasks

### Phase 0: Foundation

- [ ] Add subprocess-seam regressions for the empty tool list and excluded
  inherited MCP configuration, then restrict the invocation. Delimit/encode
  snippets as untrusted data and test a snippet containing instructions and
  delimiter-like text. Update prompt-aware test fakes to follow the new framing
  without weakening their classification assertions. Assert tier/session/timeout
  behavior remains, input stays on stdin, and an unsupported-flag failure makes
  no unrestricted retry. Acceptance:
  `uv run pytest skills/distil-memory/scripts/test_funnel_triage.py skills/distil-memory/scripts/test_funnel_main.py`
  passes; the tool-restriction argv regression fails against prior code.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/distil-memory`,
and `braid --check` pass. Use shims or subprocess seams, not a live model or user corpus.

## Success Criteria

- The judge receives snippets only under a no-tools invocation.
- Prompt framing distinguishes transcript data from classifier instructions.
- CLI failures cannot trigger a fallback with restored tools.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
Shim log: `argv: --print --no-session-persistence --model haiku`, `stdin contains injection verbatim: True`. No model run, so it is unknown whether a real judge obeys.
```

Authoring verification on 2026-10-29: installed `claude --help` documents
`--tools` with an empty string to disable built-in tools, and
`--strict-mcp-config` to ignore MCP configurations outside explicitly supplied
ones. Use those supported controls without supplying any MCP servers; re-check
the CLI help at implementation time if its interface changes.

### Risks

CLI option semantics can change. Tests must preserve the empty argv element,
and errors must fail closed rather than restoring defaults. Delimiters improve
instruction/data clarity but do not themselves provide action isolation.
