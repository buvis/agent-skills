---
design: skip
default_model: sonnet
model_tier_rationale: bounded source-scope guard with isolated-home CLI regression and conflicting-test correction
---

# Repository link checks include memory files outside the selected root

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 11,
accepted option A on 2026-10-27. Related to finding 30 of the 2026-10-25 report;
that report's root-encoding concern remains distinct. The reports are local audit
artifacts and are not shipped in the public repository.

## Problem

The backlog link checker includes the selected repository's home-directory
auto-memory files as sources for every root, although its documentation limits
this to runs targeting ~/.claude. A clean repository can fail solely because an
external memory file contains broken references. Operators receive findings
outside their selected repository and results depend on personal home state.

## Solution

Include auto-memory files as scanned sources only when the resolved root equals
the resolved ~/.claude directory. Continue scanning project-management documents
for ordinary repositories, and preserve the documented memory scan for ~/.claude.
Update the existing broad-scan test to assert the accepted scope.

## Requirements

### Must have

- Ordinary repository roots do not include external auto-memory files as sources.
- Broken references found only in those memory files do not make a clean ordinary
  repository fail its link check.
- Runs targeting ~/.claude still scan the associated auto-memory files.
- Compare resolved paths consistently, including symlink spellings of the root.
- Preserve project-management source scanning and existing reference resolution.
- Update the conflicting broad-scan test and add isolated-home CLI coverage.
- Implement option A directly without adding an include-memory flag.

### Nice to have

- None.

## Implementation

```text
skills/review-prd-backlog/scripts/
├── check_links.py       # gate memory source inclusion on the resolved root
└── test_check_links.py  # ordinary-root exclusion and ~/.claude inclusion controls
```

### Module: source selection

- **Location**: `skills/review-prd-backlog/scripts/check_links.py`
- **Maps-to-capability**: keep findings within the documented source scope.
- **Responsibility**: include memory sources only for the documented ~/.claude root.
- **Exports**: `run`, `project_memory_dir`, `main`.

#### Feature: constrain memory source scanning

- **Inputs**: the selected root and home directory.
- **Outputs**: repository findings plus memory-source findings only for ~/.claude.
- **Behavior**: resolve paths before deciding whether to append memory files to
  the source set. Leave ordinary repository document scanning intact.

### Module: source-scope regression tests

- **Location**: `skills/review-prd-backlog/scripts/test_check_links.py`
- **Maps-to-capability**: prove unrelated memory state cannot fail ordinary-root checks.
- **Responsibility**: exercise both sides of the root guard with a scratch home.
- **Exports**: none.

### Dependencies

- Source selection: existing project-management and memory source enumeration (foundation).
- Source-scope tests: depend on source selection and isolated-home fixtures.
- Existing path, PRD, and memory-link resolution remains integrated with the scanner.

## Tasks

### Phase 0: Foundation

- [ ] Add a failing CLI regression with a clean ordinary repository and a scratch
  home containing its associated memory file with dead references. Gate memory
  source inclusion on the resolved ~/.claude root. Change
  `test_memory_dir_scanned_as_source` to target the scratch ~/.claude directory
  and retain its positive memory-source assertion; add the ordinary-root negative
  case. Cover resolved root spellings where supported. Assert a clean exit and
  no external-source findings for the ordinary root, while ~/.claude still
  reports broken memory references. Do not weaken existing resolution tests.
  Acceptance: `uv run pytest skills/review-prd-backlog/scripts/test_check_links.py`
  passes; the ordinary-root CLI regression fails against the prior code.
  The unmerged branch `agoge/authored-tests-2026-10-26` holds a strict-xfail
  regression for this finding. Implement independently if absent; if present,
  convert it to a normal regression without merging unrelated branch changes.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/review-prd-backlog`,
and `braid --check` pass.

## Success Criteria

- External memory-source errors cannot fail a clean ordinary repository check.
- The documented ~/.claude memory scan remains active and tested.
- Existing repository document checks and reference resolution continue working.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
Scratch repo with a clean PRD, scratch HOME holding `.claude/projects/<encoded root>/memory/m1.md` with a dead path, `[[ghost]]` and `99999-`. Output listed the three memory-file findings, `3 dangling, 0 scan errors`, exit 1. `--root` is `.resolve()`d, so `/var/...` becomes `-private-var-...`, which may not match the harness's own spelling.
```

Use temporary repositories and a scratch home, never the operator's memory store.

### Risks

Users who relied on extra memory-source scans for other repositories lose that
implicit check. The old broad-scan test conflicts with the accepted behavior;
rewrite its root setup rather than deleting positive coverage for ~/.claude.
