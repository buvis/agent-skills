# ADR Template

Use this template when creating Architecture Decision Records.

---

```markdown
# ADR-{NUMBER}: {TITLE}

**Status:** {Proposed | Accepted | Deprecated | Superseded by ADR-XXX}  
**Date:** {YYYY-MM-DD}  
**Decision Makers:** {Names and roles}  
**Technical Area:** {Category / Sub-category}

## Context

{What is the issue? What forces are at play? What constraints exist?
Describe the problem space and why a decision is needed.
Include relevant background, stakeholders, and timeline pressures.}

## Decision

{State the decision clearly and concisely in 1-3 paragraphs.
Use bold for the key choice. Be specific about what will and will not be done.}

## Rationale

{Number each reason. Explain WHY this option was chosen over alternatives.}

### 1. {First reason title}

{Explanation}

### 2. {Second reason title}

{Explanation}

### 3. {Third reason title}

{Explanation}

## Consequences

### Positive

- {Benefit 1}
- {Benefit 2}
- {Benefit 3}

### Negative

- {Drawback or risk 1}
- {Drawback or risk 2}
- {Drawback or risk 3}

## Alternatives Considered

### Alternative 1: {Name}

**Pros:** {Brief pros}

**Cons:** {Brief cons}

**Decision:** {Why rejected or deferred}

### Alternative 2: {Name}

**Pros:** {Brief pros}

**Cons:** {Brief cons}

**Decision:** {Why rejected or deferred}

## Architecture Impact

{Optional: Include a diagram or description of how the architecture changes.
Use code blocks for ASCII diagrams.}

```text
{ASCII architecture diagram if applicable}
```

## Review Criteria

{Under what conditions should this decision be revisited?
List specific triggers — not vague "if things change" statements.}

- {Specific trigger 1}
- {Specific trigger 2}
- {Specific trigger 3}
```

---

## Quality Checklist

When reviewing an ADR, verify:

- [ ] Title clearly states the decision (verb + noun pattern preferred)
- [ ] Status is one of: Proposed, Accepted, Deprecated, Superseded
- [ ] Context explains WHY a decision is needed (not just what was decided)
- [ ] Decision is stated clearly enough that someone could implement it without reading the rest
- [ ] Rationale explains WHY this choice (not just restating what was chosen)
- [ ] Consequences include both positive AND negative outcomes
- [ ] At least one alternative is documented with reason for rejection
- [ ] Review criteria list specific, measurable triggers for revisiting
- [ ] Technical area helps with categorization and searching
- [ ] Decision makers are named (accountability)

## Numbering Convention

- ADR numbers are sequential and never reused.
- Superseded ADRs keep their number but update status to "Superseded by ADR-XXX".
- Use the format: `ADR-{NNN}-{Kebab-Case-Title}.md`

## Tips for Extracting ADRs from Meetings

When analyzing meeting transcripts for architectural decisions, look for:

1. **Explicit choices between options** — "I would split" / "I think we should go with X"
2. **Reasons given for rejecting alternatives** — "we are not doing it because..."
3. **Constraints mentioned** — "the security team requires..." / "the firewall won't allow..."
4. **Agreement signals** — "yeah, I agree" / "that makes sense" / "we agree totally"
5. **Future considerations** — "we will need to revisit when..." / "not for POC but later..."
6. **Scope decisions** — "we will focus on X" / "not a priority for now"

Distinguish between:
- **Architectural decisions** (permanent structural choices) — CREATE an ADR
- **Operational decisions** (task assignments, schedules) — DO NOT create ADRs
- **Process decisions** (how to deploy a note) — Only create ADR if it establishes a reusable pattern
