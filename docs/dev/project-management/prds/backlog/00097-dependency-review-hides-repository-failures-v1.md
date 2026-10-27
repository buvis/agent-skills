---
design: skip
default_model: sonnet
model_tier_rationale: bounded shell failure accounting with partial-result and all-failed regression cases
---

# Dependency review silently skips failed repositories

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 8,
accepted option A on 2026-10-26. The report is a local audit artifact and is not
shipped in the public repository. Status: mocked evidence, using a GitHub command shim.

## Problem

The dependency-listing script suppresses each repository's pull-request lookup
errors and continues with exit 0. Operators can interpret an empty heading as
no dependency updates even when every lookup failed. Partial failures also hide
repositories from the review without any indication that results are incomplete.

## Solution

Count failed repository lookups, print `could not list: <repo>` to stderr for
each failure, and exit 2 when any repository lookup fails. Continue collecting
and printing successful results. Keep successful scans at exit 0 and preserve
the existing repository-enumeration failure behavior.

## Requirements

### Must have

- Report each failed repository lookup on stderr, naming the repository.
- Return exit 2 for partial failure and for failure of every repository lookup.
- Continue scanning remaining repositories after a lookup failure.
- Preserve successful dependency pull-request results on stdout.
- Return exit 0 when all repository lookups succeed, including no matching PRs.
- Preserve the existing exit 1 and diagnostic for failed repository enumeration.
- Document that exit 2 means the displayed results are incomplete.

### Nice to have

- None.

## Implementation

```text
skills/review-deps-prs/
├── SKILL.md                      # explain incomplete results and exit 2
└── scripts/
    ├── list-dep-prs.sh           # count and report failed per-repository lookups
    └── test_list_dep_prs.sh      # partial failure, all failed, and success controls
```

### Module: dependency listing

- **Location**: `skills/review-deps-prs/scripts/list-dep-prs.sh`
- **Maps-to-capability**: expose incomplete dependency reviews without losing good results.
- **Responsibility**: account for failed lookups and set the final exit status.
- **Exports**: the existing shell command interface.

#### Feature: report repository lookup failures

- **Inputs**: the repository list and each GitHub lookup's status and results.
- **Outputs**: successful PR listings on stdout, failed repository names on stderr,
  and exit 2 if the result is incomplete.
- **Behavior**: continue after individual failures, then distinguish incomplete
  results from a successful scan with no dependency PRs.

### Module: shell regression suite

- **Location**: `skills/review-deps-prs/scripts/test_list_dep_prs.sh`
- **Maps-to-capability**: prove partial and total lookup failures are visible.
- **Responsibility**: use the existing GitHub shim to assert stdout, stderr, and status.
- **Exports**: none.

### Module: operator instructions

- **Location**: `skills/review-deps-prs/SKILL.md`
- **Maps-to-capability**: prevent incomplete scans from being reported as complete.
- **Responsibility**: document the new exit status and treatment of partial results.
- **Exports**: none.

### Dependencies

- Dependency listing: existing repository enumeration and per-repository loop (foundation).
- Shell suite and operator instructions: depend on the listing's exit contract.
- Existing author and title filtering remains in the listing pipeline (integration).

## Tasks

### Phase 0: Foundation

- [ ] Extend the shell shim with one-failed-repository and all-failed modes,
  then add failure accounting and stderr diagnostics to the listing script.
  Assert exit 2 and the failed names in both modes, retain successful results
  in the partial case, and verify later repositories are still queried.
  Keep successful-empty and enumeration-failure controls. Document exit 2 and
  the need to treat its output as incomplete. Retain macOS Bash 3.2 compatibility.
  Acceptance: `bash skills/review-deps-prs/scripts/test_list_dep_prs.sh` passes;
  the partial and all-failed assertions fail against the prior script.
  Tests use a shim and do not call live GitHub or change pull requests.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/review-deps-prs`,
and `braid --check` pass, alongside the shell-suite acceptance above.

## Success Criteria

- No failed per-repository lookup ends as an unqualified successful scan.
- Partial results remain available and explicitly incomplete.
- Existing dependency matching and repository-enumeration error behavior remain correct.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
Mode `prfail` (api ok, every `pr list` exits 1, "rate limit"): exit 0, stdout `=== Dependency Update PRs ===` only, stderr empty. Mode `partial` (o/b fails with 502): exit 0, o/b absent. Mode `apifail`: exit 1 with stderr message (correct). Empty repo list: the message goes to stdout.
```

This used a PATH shim. Validate failure handling through command exit statuses,
without relying on any particular live GitHub error-body wording.

### Risks

Callers that treat every non-zero status as fatal must account for exit 2 and
retain useful partial results. The simulated failures do not prove the exact
error messages returned by real GitHub.
