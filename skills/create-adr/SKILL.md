---
name: create-adr
description: Use when creating Architecture Decision Records (ADRs) from meeting transcripts, discussions, or on-demand from user-provided information. Triggers on "create ADR", "write ADR", "document decision", "architectural decision", "identify decisions in transcript", "ADR from meeting".
---

# Create ADR

Identify architectural decisions and produce Architecture Decision Record (ADR) documents.

## Dependencies

Read/write access to the selected project and the supplied decision record or
transcript. No external tools or private templates are required. Use
`references/adr-template.md` and the target project's ADR location and numbering.

## Modes of Operation

### Mode 1: Transcript Analysis

Given a meeting transcript (text, .vtt, or pasted content), identify all architectural decisions and produce one ADR per decision.

### Mode 2: On-Demand Single ADR

Given specific information about a decision (what was decided, why, who, alternatives), produce a single ADR document.

## Workflow

### 1. Determine mode

- If the user provides a transcript or meeting notes → **Mode 1** (batch extraction)
- If the user describes a specific decision → **Mode 2** (single ADR)

### 2. Mode 1: Extract decisions from transcript

Scan the transcript for architectural decisions. Look for:

1. **Explicit choices between options** — "I would split" / "I think we should go with X"
2. **Reasons given for rejecting alternatives** — "we are not doing it because..."
3. **Constraints mentioned** — "the security team requires..." / "the firewall won't allow..."
4. **Agreement signals** — "yeah, I agree" / "that makes sense"
5. **Future considerations** — "we will need to revisit when..."
6. **Scope decisions** — "we will focus on X" / "not a priority for now"

**Filter out non-architectural content:**
- Task assignments (operational, not ADR-worthy)
- Schedule coordination
- Small talk / social conversation
- Process complaints without structural decisions
- One-time operational fixes

**Present findings** to the user as a numbered list with:
- Short title for each decision
- One-line summary of what was decided
- Participants who agreed

Ask the user to confirm which ones to produce as ADRs (or say "all").

### 3. Mode 2: Gather information

If the user provides incomplete information, ask for:

- **What** was decided (required)
- **Why** it was decided (required — at least one reason)
- **Who** decided (optional — default to "Architecture Team")
- **What alternatives** were considered (optional — ask if not provided)
- **What area** it affects (optional — infer from context)
- **When to revisit** (optional — ask if not provided)

Do not ask for everything at once. Gather the essentials (what + why), then fill in the rest from context or ask one follow-up.

### 4. Determine numbering

- Check the output directory for existing ADR files.
- Find the highest existing ADR number.
- Assign the next sequential number.
- If no directory context exists, ask the user for the starting number or default to ADR-001.

### 5. Write ADRs

Use the template from `references/adr-template.md`. For each ADR:

1. Fill all required sections (Context, Decision, Rationale, Consequences, Alternatives, Review Criteria).
2. Use numbered rationale points (### 1. Title format).
3. Include both positive and negative consequences.
4. Document at least one alternative with rejection reason.
5. Write specific review criteria (not vague triggers).
6. Title format: verb + noun (e.g., "Use X for Y", "Deploy to Z", "Split A by B").

**File naming:** `ADR-{NNN}-{Kebab-Case-Title}.md`

### 6. Output location

- If the user specifies a directory, save there.
- If an existing ADR directory is detectable (look for `ADR-*.md` files), use that.
- Otherwise, ask the user where to save.

### 7. Summary

After creating all ADRs, present a table:

| # | Title | Status | File |
|---|-------|--------|------|

## Quality Rules

- **Context** must explain WHY a decision was needed, not just restate the decision.
- **Decision** must be implementable from reading that section alone.
- **Rationale** must explain WHY this choice was made (not restate WHAT was chosen).
- **Consequences** must include negatives — every decision has tradeoffs.
- **Alternatives** must include at least one with a specific rejection reason.
- **Review Criteria** must list measurable/observable triggers.

## References

- `references/adr-template.md` — the canonical ADR template with quality checklist
