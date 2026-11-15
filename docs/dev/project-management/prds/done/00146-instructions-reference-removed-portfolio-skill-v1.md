---
design: skip
catchup: skip
default_model: sonnet
default_model_rationale: Three bounded documentation corrections with existing validation.
---

# Instructions reference a removed portfolio skill

Source: `dev/local/audit-results/agoge-2026-10-25.md`, finding 36, audit dated 2026-10-25. User accepted option A on 2026-10-29.

## Problem

Sweep-fix and brush still refer to the removed brief-portfolio skill and its collection script. Agents can follow an absent executable path, while the brush report template makes an obsolete claim about its consumer.

## Solution

Remove obsolete operational references from the three affected documents. Name the successor only if its current documented behavior supports the specific claim. Otherwise remove the claim without inventing a replacement command or dependency.

## Requirements

### Must have

- Sweep-fix no longer points agents at the removed collection script.
- Brush instructions and its report template no longer describe brief-portfolio as an active consumer.
- Preserve the report's generated-date field and schema; correcting consumer prose does not authorize an output-format change.
- Keep historical CHANGELOG entries and removal records intact.
- If mentioning the successor, verify its relevant contract first and use a portable supported reference.

### Nice to have

None.

## Implementation

```text
skills/sweep-fix/SKILL.md
skills/brush/SKILL.md
skills/brush/references/report-template.md
```

### Module: Operational documentation

- **Location**: `skills/sweep-fix/SKILL.md`, `skills/brush/SKILL.md`, `skills/brush/references/report-template.md`
- **Maps-to-capability**: Runnable instructions and accurate consumer descriptions.
- **Responsibility**: Remove dead operational paths and obsolete claims while preserving valid workflow steps and report fields.
- **Exports**: Existing skill instructions and report template.

#### Feature: Supported portfolio references

- **Inputs**: Existing references to the removed skill.
- **Outputs**: Accurate instructions without a missing command path.
- **Behavior**: Remove obsolete lines or replace a specific claim with a verified successor reference. Do not extend link scanning, restore the removed skill, or add a new runtime dependency.

### Dependencies

- Existing skill validator and braid checks. No implementation dependency on a portfolio tool.

## Tasks

### Phase 0: Documentation corrections

- [ ] Correct the three operational documents, retaining the generated-date contract.
- [ ] Search those documents for remaining active references to brief-portfolio or its script and review each result. Historical prose elsewhere is outside scope.
- [ ] Run the skill validator on both touched skills, `braid --check`, and repository-required checks before committing. No new behavior tests are required for prose-only changes.

Exit criteria: The affected instructions have no dead operational pointer, valid report fields remain, and both skills validate.

## Success Criteria

- An agent following either skill is not directed to an absent brief-portfolio script.
- Consumer descriptions reflect verified current behavior or are removed.

### Test Strategy

Original confirmed evidence, preserved verbatim:

```text
`ls skills/brief-portfolio` -> no such dir. `sweep-fix/SKILL.md:77` names `~/.agents/skills/brief-portfolio/scripts/collect.py`.
```

Review the current three documents rather than relying on historical line numbers. Validate both skills and confirm the template's generated-date field remains unchanged. A broader link-checker expansion was option B and is outside this acceptance.

### Risks

An assumed successor contract can replace one dead pointer with another. Remove an obsolete claim when the successor cannot be verified. Removing the date field along with its obsolete consumer explanation would change the report contract unnecessarily.
