---
design: skip
catchup: skip
default_model: sonnet
model_tier_rationale: three documentation-only corrections with execution-time premise checks
---

# Three documentation statements have drifted from their sources

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 25,
accepted option A on 2026-10-28. Also covers findings 34 and 35 of the 2026-10-25
report. Reports are local audit artifacts and are not shipped in the public repository.

## Problem

The CI comment names an obsolete shell-suite count, the approved-model registry
calls the shipped default unpromoted, and the README's plugin-treatment table
omits the autopilot group present in the exclusion policy. Readers receive
inconsistent explanations even though runtime behavior is correct.

## Solution

Correct the CI count comment, remove the stale model-promotion claim, and add
the autopilot row to the README. Re-check each premise at execution time and
describe the current sources rather than copying numbers or model state blindly.
Change prose only, preserving CI steps, model records, and projection policy.

## Requirements

### Must have

- CI's comment reflects the actual number of shell suites and contributing skills;
  the audit's correction was five skills and six suites.
- Remove the not-yet-promoted claim only if the referenced model is still the
  shipped default; describe actual status if its default has since changed.
- Explain autopilot's cross-host treatment in the README consistently with the
  current compatibility and documentation-copy rules.
- Preserve workflow behavior, approved model entries, and .braidignore policy.
- Skip already-corrected statements and report changed premises rather than
  duplicating content or restoring obsolete facts.

### Nice to have

- None.

## Implementation

```text
.github/workflows/ci.yml                    # shell-suite count comment only
skills/use-qwen/scripts/approved-models.txt  # promotion-status comment only
README.md                                  # autopilot plugin-treatment row
```

### Module: documentation consistency

- **Locations**: `.github/workflows/ci.yml`,
  `skills/use-qwen/scripts/approved-models.txt`, `README.md`.
- **Maps-to-capability**: give readers accurate CI, model, and plugin information.
- **Responsibility**: reconcile three stale statements with authoritative local sources.
- **Exports**: none.

#### Feature: correct the three reported statements

- **Inputs**: actual shell-suite inventory, shipped model selection, and plugin policy.
- **Outputs**: corrected comments and a matching README row.
- **Behavior**: update prose after checking its premise, without changing execution
  or policy data.

### Dependencies

- Documentation consistency: existing inventory and model/plugin policy (foundation).
- No production behavior or new dependencies are introduced.

## Tasks

### Phase 0: Foundation

- [ ] Premise: the three reported statements still differ from their current
  local sources. Re-check the shell-suite inventory, shipped default, exclusion
  groups, and compatibility/documentation-copy rules before editing. Correct
  each remaining mismatch and skip any already resolved item, reporting why.
  Add no duplicate autopilot row and change no executable workflow/model/policy
  content. Acceptance: inspect the diff against all three sources;
  `python3 scripts/check_changelog_skills.py` passes and workflow commands,
  approved-model records, and projection policy are unchanged.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/use-qwen`,
and `braid --check` pass. No new tests are needed for these prose corrections.

## Success Criteria

- All three statements match the sources verified when the PRD executes.
- Changes remain limited to comments and README prose.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
`rg --files -g 'test_*.sh'` lists 6 suites across 5 skills (use-sonnet, use-qwen x2, use-codex, use-gemini, review-deps-prs); the CI glob (`skills/*/scripts/test_*.sh`) covers all six; wendy ran the new suite: `SUMMARY: 6 passed, 0 failed`. `default-model.txt`, `SHIPPED_DEFAULT_ID` (`test_qwen_run.sh:628`) and `SKILL.md:9,66` agree on `unsloth/Qwen3.8-27B-GGUF:UD-Q6_K_XL`. All 20 `.braidignore` names exist as skills; 50/50 skill dirs agree across braid, the validator loop and the changelog check.
```

The CI count was confirmed by execution; the other discrepancies were file
comparisons. Validate prose against the current files without adding tests that
merely assert a fixed count or model comment.

### Risks

Fixed counts and model status can drift again. The user chose explicit corrections
rather than deleting the count, so execution-time checks must prevent stale edits.
