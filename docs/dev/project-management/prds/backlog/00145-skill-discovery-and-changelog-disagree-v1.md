---
design: skip
default_model: sonnet
default_model_rationale: Narrow discovery predicate and literal-name matching changes with existing tests.
---

# Skill discovery and changelog checks disagree

Source: `dev/local/audit-results/agoge-2026-10-25.md`, finding 32, audit dated 2026-10-25. User accepted option A on 2026-10-29.

## Problem

CI and the changelog gate treat every directory under skills as a skill, while braid requires a SKILL.md file. The changelog gate also accepts a name embedded inside another word. Stray directories can fail validation, and short skill names can pass without a distinct mention.

## Solution

Apply the actual-skill predicate in both CI's validator loop and the changelog gate. Match literal complete skill names with appropriate boundaries, retaining existing plain, backtick, and bold mentions rather than requiring new Markdown formatting.

## Requirements

### Must have

- Only directories containing a SKILL.md file enter the validator loop or changelog coverage check.
- A distinct literal skill name satisfies coverage; a substring inside a longer name or word does not. Preserve existing case sensitivity and sorted missing-name output.
- Escape names as literals when building any regular expression; treat skill-name characters such as hyphens consistently at boundaries.
- Continue validating real skills even when another real skill fails; do not weaken validator behavior or silently exempt malformed SKILL.md files.
- Update tests that explicitly pin substring matching and fixtures that currently omit SKILL.md despite representing real skills.
- Preserve valid existing changelog mentions without rewriting release history.

### Nice to have

None.

## Implementation

```text
.github/workflows/ci.yml
scripts/check_changelog_skills.py
scripts/test_check_changelog_skills.py
```

### Module: Changelog coverage

- **Location**: `scripts/check_changelog_skills.py`
- **Maps-to-capability**: Changelog coverage for actual skills and distinct names.
- **Responsibility**: Filter the inventory and check complete literal names.
- **Exports**: `find_missing`, `main`.

#### Feature: Consistent inventory and matching

- **Inputs**: Skills directory and changelog text.
- **Outputs**: Sorted missing real-skill names with existing CLI codes and diagnostics.
- **Behavior**: Ignore stray directories and files; require a distinct name mention, accepting existing Markdown or prose forms. A name occurring only inside a longer skill name does not count.

### Module: CI validation loop

- **Location**: `.github/workflows/ci.yml`
- **Maps-to-capability**: Validate the same actual skill inventory.
- **Responsibility**: Skip directories without a SKILL.md file while retaining aggregate failure reporting.
- **Exports**: Existing Validate every skill step.

### Module: Coverage regression tests

- **Location**: `scripts/test_check_changelog_skills.py`
- **Maps-to-capability**: Reliable inventory and distinct-name detection.
- **Responsibility**: Use representative skill fixtures and replace obsolete substring expectations.
- **Exports**: Existing pytest tests.

### Dependencies

- Existing Python standard library, validator, and CI shell loop. No new runtime dependency or discovery abstraction.

## Tasks

### Phase 0: Inventory and matching

- [ ] Apply the SKILL.md-file predicate to the changelog gate and CI loop.
- [ ] Match distinct literal skill names while retaining valid existing formatting and output contracts.
- [ ] Test a stray directory, actual missing skill, embedded names, hyphenated names, formatting variants, and case sensitivity. Correct real-skill fixtures and the test that currently requires substring acceptance.
- [ ] Run `uv run pytest scripts/test_check_changelog_skills.py`, `python3 scripts/check_changelog_skills.py`, and the CI validator loop with a temporary stray-directory fixture; remove the fixture afterward. Run repository-required checks before committing.

Exit criteria: Both consumers ignore stray directories, actual missing skills still fail, and embedded-name mentions no longer satisfy coverage.

## Success Criteria

- The actual skill inventory is consistent across these consumers.
- Distinct existing changelog mentions pass and substring-only mentions fail.

### Test Strategy

Original confirmed evidence, preserved verbatim:

```text
`validate_skill.py skills/purge-devlocal/` -> exit 1. `find_missing` on `fix`, `skill`, `use`, `zz-never-mentioned` -> `['zz-never-mentioned']` only.
```

Use isolated fixtures containing both directories with SKILL.md and stray directories without it. Give short names only embedded occurrences and then distinct mentions, verifying both sides of the matcher. Inspect or exercise the exact CI loop without adding permanent dummy skills. Do not require the standalone validator to accept a non-skill directory; selection belongs to its callers.

### Risks

Bold-only matching would reject valid existing entries. Use boundaries without introducing a new formatting requirement. Superficial test fixtures without SKILL.md can make the filtered gate pass vacuously; update those fixtures before judging coverage.
