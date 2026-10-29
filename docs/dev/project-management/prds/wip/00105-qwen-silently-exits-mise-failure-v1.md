---
design: skip
default_model: sonnet
model_tier_rationale: bounded shell initialization fallback with existing outcome and stdin-isolation regression coverage
---

# Qwen's wrapper exits silently when mise environment setup fails

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 16,
accepted option A on 2026-10-27. The report is a local audit artifact and is not
shipped in the public repository.

## Problem

The Qwen wrapper runs mise environment setup under errexit and pipefail before
normal preflight handling. A failed mise command, such as an untrusted configuration,
ends the wrapper with exit 1 and no diagnostic or documented outcome label.
Operators and dispatchers cannot distinguish the cause from an unexplained failure.

## Solution

On mise environment failure, retain the original PATH and print a warning to
stderr. Continue through existing preflight and dispatch handling. Keep successful
mise PATH setup and absent-mise behavior unchanged; do not add a new outcome label.

## Requirements

### Must have

- A failing mise env does not terminate the wrapper before normal outcome handling.
- Restore the exact original PATH on failure, ignoring any partial failing output.
- Print a clear stderr warning naming mise environment setup and the fallback.
- Preserve documented healthy and failure outcomes after fallback.
- Successful mise setup continues to expose its managed tools.
- Preserve absent-mise behavior and stdin isolation during environment setup.
- Retain macOS Bash 3.2 compatibility and the existing CLI interface.

### Nice to have

- None.

## Implementation

```text
skills/use-qwen/scripts/
├── qwen-run.sh       # guard mise setup and warn while retaining the old PATH
└── test_qwen_run.sh  # failing-mise regressions and existing preflight controls
```

### Module: wrapper environment setup

- **Location**: `skills/use-qwen/scripts/qwen-run.sh`
- **Maps-to-capability**: preserve normal outcome reporting when mise setup fails.
- **Responsibility**: apply mise PATH only on success, otherwise warn and fall back.
- **Exports**: existing wrapper CLI and outcome labels.

#### Feature: retain a usable environment on mise failure

- **Inputs**: original PATH, mise availability, and mise env result.
- **Outputs**: updated PATH on success or original PATH plus a warning on failure.
- **Behavior**: handle the failing substitution explicitly rather than allowing
  errexit/pipefail to stop the wrapper; continue to established preflight checks.

### Module: shell regression suite

- **Location**: `skills/use-qwen/scripts/test_qwen_run.sh`
- **Maps-to-capability**: prove mise failures remain visible and labeled downstream.
- **Responsibility**: exercise controlled mise and pi shims through the real wrapper.
- **Exports**: none.

### Dependencies

- Wrapper environment setup: existing shell initialization (foundation).
- Shell regression suite: depends on fallback behavior and current mock backend.
- Existing preflight and dispatch consume the resulting PATH (integration).

## Tasks

### Phase 0: Foundation

- [ ] Extend the existing mise shim to fail on demand, including a case that
  emits partial PATH output before failure. Add an explicit fallback with a
  stderr warning. Assert the original-path pi shim remains selected, normal
  outcome handling runs, and failing output does not change tool selection.
  Cover a healthy mock backend and an existing labeled failure after fallback,
  plus successful-mise and absent-mise controls. Retain stdin-isolation coverage.
  Acceptance: `bash skills/use-qwen/scripts/test_qwen_run.sh` passes; the
  failing-mise outcome and warning regression fails against the prior wrapper.
  Use shims and the existing mock backend rather than a live model or real user config.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/use-qwen`,
and `braid --check` pass, alongside the shell-suite acceptance above.

## Success Criteria

- Mise setup failure produces a warning and reaches normal labeled outcomes.
- Partial failing output never replaces the original PATH.
- Successful and absent-mise behavior remain intact.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
Real mise with a scratch HOME: `mise env -s bash` -> "Config files in ... are not trusted", exit 1; `qwen-run.sh --preflight` -> `exit=1`, empty stdout and stderr. A failing `mise` shim first on PATH gave the same. With no `mise` on PATH it reaches `ERROR: preflight failed (endpoint_unreachable)`.
```

### Risks

The original PATH can select a different pi executable from the mise-managed
one; this is the accepted fallback tradeoff. The stderr warning must remain
visible so the configuration failure is not hidden by a later successful outcome.
