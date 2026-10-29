---
design: skip
default_model: sonnet
model_tier_rationale: bounded GET pagination parameter change with existing GitHub shim coverage
---

# Dependency discovery uses smaller repository pages than necessary

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 35,
accepted option A on 2026-10-29. Reports are local audit artifacts and are not
shipped in the public repository. Performance evidence used a GitHub command shim.

## Problem

Dependency discovery enumerates repositories and checks their pull requests
sequentially. The audit observed one lookup per repository and noted no explicit
repository page size. Large accounts can pay extra pagination round trips in
addition to the unchanged per-repository request cost.

## Solution

Request 100 repositories per enumeration page while preserving pagination and
sequential pull-request checks. Use a GET query parameter, such as the endpoint
user/repos?per_page=100, without changing authentication or repository scope.
Do not introduce the concurrency proposed by option B.

## Requirements

### Must have

- Repository enumeration explicitly requests per_page=100 and retains pagination.
- Keep the request as GET and retain all repositories visible to the token.
- Preserve sequential PR checks, deterministic output, and dependency filters.
- Preserve enumeration errors and PRD 00097's incomplete-result exit-2 contract.
- Update the existing GitHub shim to recognize and verify the pagination parameter.
- Make no claim that the change removes per-repository network latency.

### Nice to have

- None.

## Implementation

```text
skills/review-deps-prs/scripts/
├── list-dep-prs.sh       # explicit repository discovery page size
└── test_list_dep_prs.sh  # query-parameter and existing behavior checks
```

### Module: repository enumeration request

- **Location**: `skills/review-deps-prs/scripts/list-dep-prs.sh`
- **Maps-to-capability**: reduce enumeration pagination requests.
- **Responsibility**: request larger pages without changing scope or execution order.
- **Exports**: existing shell command interface.

#### Feature: enumerate repositories in 100-item pages

- **Inputs**: authenticated GitHub repository enumeration.
- **Outputs**: the same complete repository list, requested with a larger page size.
- **Behavior**: keep paginating the GET endpoint and retain sequential downstream checks.

### Module: shell regression suite

- **Location**: `skills/review-deps-prs/scripts/test_list_dep_prs.sh`
- **Maps-to-capability**: verify page-size wiring without live GitHub requests.
- **Responsibility**: accept the new endpoint/query shape and preserve existing controls.
- **Exports**: none.

### Dependencies

- Enumeration request: existing GitHub listing and pagination (foundation).
- Shell regression suite: depends on the request and current partial-failure behavior.

## Tasks

### Phase 0: Foundation

- [ ] Add the explicit page-size query while preserving GET and pagination.
  Adjust the GitHub shim to assert the parameter and retain complete repository
  enumeration, bot filtering, output-order, and failure controls.
  Acceptance: `bash skills/review-deps-prs/scripts/test_list_dep_prs.sh` passes;
  the request includes per_page=100 and pagination, remains GET, and PR checks
  remain sequential with existing exit codes.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/review-deps-prs`,
and `braid --check` pass. No live portfolio request is needed for verification.

## Success Criteria

- Repository enumeration requests 100-item pages without reducing coverage.
- Sequential PR output and incomplete-result handling remain correct.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
10 repos: 11 calls, 0.04 s warm; 1000 repos: 1001 calls, 3.20 s and 3.23 s (about 3.2 ms per call, shim start-up). Reading the script (not measured): `gh api user/repos --paginate` passes no `per_page`, so a real run likely pages at the default 30.
```

These simulated timings do not establish real network performance.

### Risks

Per-repository calls remain sequential, so large accounts can still be slow.
Passing form fields can change an API command's method; retain GET explicitly
or use the query-string endpoint. Preserve PRD 00097's failure accounting.
