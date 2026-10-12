---
name: elicit-requirements
description: Use when fleshing out a rough idea before /create-prd, when requirements are unclear or complex (adaptive depth, minimal to comprehensive). Triggers on "elicit requirements", "flesh out this idea", "what should we build", "scope this out".
argument-hint: "[<rough idea or path to brainstorming output>]"
---

# Elicit Requirements

Turn a rough idea into a validated discovery document that `/create-prd` can consume. Asks structured questions at adaptive depth, analyzes existing code when relevant, and produces a traceable requirements artifact.

**Pipeline position:** rough idea -> `/elicit-requirements` -> `/review-discovery-doc` -> `/create-prd` -> `/autopilot:plan-tasks` -> `/autopilot:run-autopilot`

## Dependencies

- Personal skills: `spike` (the spike fork runs the spike loop on a second non-answer)
- Harness tool: `AskUserQuestion`
- Optional pointers, suggested to the user but never invoked here: `review-discovery-doc`, `create-prd`
- Personal skill (reference only): `structure-git-repo` owns the intake layout this skill writes into (`references/layout.md`); step 5 stands on its own when that skill is absent.
- Plugin skills (`autopilot` plugin), the pipeline downstream of this skill, never invoked here:
  `autopilot:plan-tasks`, `autopilot:run-autopilot`. Without the plugin the discovery doc still
  lands; only the automated continuation is missing.

## Workflow

### 1. Accept Input

Find source material in this order:

1. **Argument** - a rough idea, a file path, or an intake item: `docs/dev/project-management/intake/new/NNNNN-slug/` (or its bare `NNNNN` ID), holding `idea.md` and optionally `qa-log.md`. An intake item is the preferred input: read both files, keep its number and slug, and treat every answer in `qa-log.md` as already given.
2. **Brainstorming output** - check for recent prior work: plan-mode output in the conversation, `docs/dev/project-management/spikes/` findings, `docs/dev/project-management/intake/new/` items, legacy `docs/dev/project-management/discovery/` docs. If found, read it and extract existing requirements, constraints, and decisions. Skip questions that the prior work already answers.
3. **Conversation context** - idea discussed in current conversation

If the input is a file path, read the file. Extract whatever is available: problem statement, requirements, constraints, success criteria, open questions.

The intake layout (`intake/new/NNNNN-slug/{idea.md,qa-log.md,discovery.md}`, retired to `intake/processed/` by `/create-prd`) is owned by `structure-git-repo` (`references/layout.md`); this skill writes into it and never moves an item.

### 2. Classify Depth

Read `references/classification-guide.md`. Score the input across four dimensions:

1. **Requirement clarity** - how complete is the input?
2. **Scope breadth** - how many modules/files affected?
3. **Codebase impact** - greenfield vs brownfield?
4. **Problem complexity** - obvious solution vs multiple approaches?

Apply the classification rule: all low = minimal, any high = comprehensive, otherwise standard.

Announce the classification and let the user override:

> **Depth: {level}** ({1-sentence rationale}). Say "go deeper" or "keep it light" to adjust.

If the user says nothing or proceeds, accept the classification and continue.

### 3. Brownfield Analysis (standard+ depth only)

For standard and comprehensive depth, scan the codebase before asking questions:

1. **Pattern scan** - find similar existing implementations. For skills: scan `~/.agents/skills/` for structure conventions. For hooks: scan `~/.claude/hooks/`. For the relevant project: scan source directories.
2. **Dependency map** - identify existing modules the new feature will touch
3. **Convention extraction** - naming patterns, file organization, testing approaches
4. **Integration surface** - specific files or functions that would need modification

Store findings internally. Use them to:
- Auto-populate integration point options in questions
- Skip questions whose answers are obvious from the scan
- Include findings in the Codebase Context section of the output

### 4. Ask Clarifying Questions

Read `references/question-bank.md`. Select questions appropriate to the depth level.

**Rules:**
- One question per message (the global CLAUDE.md planning rule; not restated elsewhere in this skill).
- Use `AskUserQuestion` tool with multiple-choice options when the question fits that format. Open-ended for scope boundaries and risk identification.
- **Mark the recommended option.** When one option is clearly best, make it the first option, append ` (Recommended)` to its label, and state the one-line rationale in its description. If no option is clearly best, present them neutrally and say so.
- Skip questions the input or brownfield analysis already answers. Note the inferred answer in the discovery log.
- After each answer, append the Q&A pair to the Discovery Log section of the working discovery file. This survives compaction.
- For comprehensive depth: after all questions, review answers for contradictions. If found, ask a contradiction resolution question.

**Question count by depth:**
- Minimal: 0-2 (inline, no file needed for the questions themselves)
- Standard: 3-6
- Comprehensive: 6-12

**Early exit:** If the user says "that's enough" or similar, stop asking and generate the document with what you have.

**Spike fork:** A non-answer is "don't know", "whatever you think", "I'd need to see it", or any answer that defers the decision to seeing something run. When contract-level questions (interface, data shape, output form, success criteria) draw a second non-answer, stop eliciting and offer via AskUserQuestion: **Spike it** (run the spike skill's loop on the fuzzy part; when it converges, fold its ASSUMPTIONS and answers into the Discovery Log and resume here - skip the spike skill's graduate step, this flow already ends in create-prd), **Keep answering**, or **Park as open questions** (they land in Open Questions for create-prd). Non-answers are a routing signal, not a failure: a 20-minute build answers them cheaper than more questions.

### 5. Write Discovery Document

Read `references/discovery-template.md`. Generate the discovery document at the classified depth.

**Sequence numbering:**
1. An existing intake item keeps its `NNNNN` and slug; skip the scan.
2. Otherwise list every `NNNNN-*` entry, file or directory, in `docs/dev/project-management/prds/**`, `docs/dev/project-management/intake/*/` and legacy `docs/dev/project-management/discovery/`
3. Extract leading 5-digit prefixes matching `^[0-9]{5}-`
4. New sequence = max + 1, zero-padded to 5 digits

**File path:** `docs/dev/project-management/intake/new/{sequence}-{feature-slug}/discovery.md`

For a new item, create the directory and write `idea.md` first: `# {title}`, then `Status: intake, not yet specced. Recorded {YYYY-MM-DD}.`, then the input as given (a pasted idea verbatim under `## Idea (from the user)`; a file by path plus its extracted points). `/create-prd` rewrites that status line when it retires the item. Never write `idea.md` over one that exists.

Legacy fallback: when the repo has `docs/dev/project-management/discovery/` and no `intake/` directory, keep writing `discovery/{sequence}-{feature-slug}.md` there, so an unmigrated repo does not get two queues. A repo with neither gets `intake/new/`.

**Content rules:**
- Under `## Classification`, add `Source: \`idea.md\` beside this file.` (name `qa-log.md` too when it exists) so the document links back to its inputs.
- Every section that appears must have real content. No stubs, no "N/A", no "TBD".
- Omit sections that don't apply at the current depth rather than filling them with placeholders.
- Discovery Log is mandatory at all depths.
- Open Questions section: list anything still unresolved. `/create-prd` will see these.

### 6. Suggest Next Step

After writing the document:

> Discovery saved to `docs/dev/project-management/intake/new/{sequence}-{feature-slug}/discovery.md`.
> Review it with `/review-discovery-doc {sequence}` (a critical five-lens pass), then run `/create-prd {sequence}` when ready; create-prd moves the item to `intake/processed/`.

On the legacy fallback, print the `discovery/{filename}` path instead and pass it to both commands.

Do not auto-invoke `/review-discovery-doc` or `/create-prd`. The user reviews first.

## Principles

These are drawn from AIDLC's Inception phase and adapted for a solo developer workflow:

- **When in doubt, ask.** Never assume requirements. Overconfidence leads to rework.
- **Adaptive depth.** Simple ideas get minimal ceremony. Complex ideas get thorough exploration. The workflow adapts to the work, not the other way around.
- **Questions in files, not just chat.** Storing Q&A in the discovery document creates a traceable record and survives context compaction.
- **Human approval gates.** The user reviews the discovery doc before it becomes a PRD. No silent progression.
- **Don't ask what code can answer.** If brownfield analysis reveals the answer, state the finding instead of asking.

## Reference Files

- `references/classification-guide.md` - depth classification rubric
- `references/question-bank.md` - question templates by depth and category
- `references/discovery-template.md` - output document template
