---
name: write-abap-specs
description: Use when writing ABAP development specifications as Jira stories from requirements and existing SAP code. Triggers on "write abap spec", "abap spec", "create dev spec", "spec from requirements", "specification from jira".
compatibility: "Portable; needs caller-supplied SAP, Jira, and Confluence provider capabilities. Word/PDF input additionally needs the publish-confluence-docs skill (Python 3.12+); without it, give Markdown input."
---

# Write ABAP Specs

Read functional requirements from any source, analyse existing ABAP artefacts in SAP, and produce structured implementation specifications published as Jira story descriptions.

## Dependencies

- A read-only SAP source/search/cross-reference provider, or a source export.
  Discover the actual tool names and argument schemas in the current session.
  SAP, Jira, and Confluence access is caller-supplied; this skill ships no provider.
- An issue reader/writer and optional Confluence page reader. Map the capability
  to the configured provider; the names below are not a prescribed tool API.
  Without a writer, save the approved specification locally and report that it
  has not been published.
- For Word/PDF input only: invoke the `publish-confluence-docs` skill
  (`~/.agents/skills/publish-confluence-docs/`) and its declared dependencies.
  If it is absent or cannot run, request Markdown or plain-text input instead.
  Never invent converted content.
- Naming rules from the target project. Do not assume an employer-specific
  namespace or impose one length limit on every ABAP object type.

## Input Sources

| Format | How to read |
|--------|-------------|
| Markdown (.md) | Read directly |
| Word (.docx) | Run `~/.agents/skills/publish-confluence-docs/scripts/docx_to_md.py` with that skill's Python environment |
| PDF (.pdf) | Run `~/.agents/skills/publish-confluence-docs/scripts/pdf_to_md.py` with that skill's Python environment |
| Jira ticket | Use the configured issue-reader capability |
| Confluence page | Use the configured page-reader capability |

## Specification Structure

Every specification MUST follow this structure (omit sections marked "if applicable" when not relevant):

```
## Feature
[Business purpose, problem statement, beneficiaries]

## Screen Adjustments (if applicable)
[UI changes, new fields, selection screens, ALV modifications]

## Architecture
[Technical design, class hierarchy, data flow, patterns used — explain WHY not just WHAT]

## Artefacts
| Object | Type | Action | Description |
|--------|------|--------|-------------|
| ZCL_... | CLAS | Create | ... |
| ZIF_... | INTF | Create | ... |

## Tests
| Test Class | Method | Scenario | Expected |
|-----------|--------|----------|----------|
| ZCL_..._TEST | ... | ... | ... |

## Dependencies (if applicable)
[External systems, BAPIs, RFCs, transport dependencies]

## Configuration (if applicable)
[Customizing tables, IMG activities, feature toggles]
```

## Workflow

### Step 1: Read Requirements

Read the input document or Jira ticket. Extract:
- Business requirement / user story
- Acceptance criteria
- Referenced ABAP objects (if any)
- Referenced transactions or reports

### Step 2: Identify Artefacts

If ABAP artefacts are NOT specified:
1. Search for related objects in SAP using keywords from the requirement
2. Propose a list of objects to analyse or create
3. **Ask the user to confirm** before proceeding

If artefacts ARE specified:
1. Verify they exist in the system
2. Read source to understand current state

### Step 3: Analyse Existing Code

For each relevant ABAP object:
- Read source code through the configured source-reader capability
- Check class hierarchy and interfaces
- Identify dependencies and callers through the configured where-used capability
- Note patterns used (factory, strategy, etc.)
- Check for existing test classes

### Step 4: Draft Specification

Write following the structure above. Ensure:
- Every new class has a corresponding test class
- Architecture section explains WHY, not just WHAT
- Artefacts table is complete (nothing left implicit)
- Naming follows the target project's documented conventions

### Step 5: User Confirmation

Present full specification. Wait for:
- Approval → proceed to publish
- Changes → revise and re-present
- Questions → clarify and update

### Step 6: Publish to Jira

Update the issue description through the configured issue-writer capability.
Use the representation its API accepts, such as Atlassian Document Format for
Jira Cloud REST v3. Do not assume Markdown or wiki markup is accepted verbatim.

## ABAP Analysis Patterns

### Finding Related Objects

```
Name-search capability: class objects matching Z*PAYROLL*
Package-listing capability: objects in the selected payroll package
```

### Reading Class Structure

1. Get source of main class
2. Check interfaces it implements
3. Check superclass hierarchy through the configured hierarchy reader
4. Look for test classes

### Checking Dependencies

1. Where-used of class/interface through the configured cross-reference reader
2. Transport requests for recent changes
3. Package dependencies

## Naming Conventions

These are authored examples, not a mandatory namespace or evidence from a SAP
system. Replace them with the target project's conventions.

| Type | Pattern | Example |
|------|---------|---------|
| Class | ZCL_{MODULE}_{PURPOSE} | ZCL_PAY_CALCULATOR |
| Interface | ZIF_{MODULE}_{PURPOSE} | ZIF_PAY_CALCULATOR |
| Table | ZTAB_{MODULE}_{ENTITY} | ZTAB_EXAMPLE_RESULTS |
| Test Class | ZCL_{MODULE}_{PURPOSE}_TEST | ZCL_PAY_CALCULATOR_TEST |
| Function Group | Z{MODULE}_{PURPOSE} | ZEXAMPLE_UTILS |
| Program | Z{MODULE}_{PURPOSE} | ZEXAMPLE_RECALCULATE |

Read the target project's naming rules. If they are missing and names must be
reserved, ask the project owner rather than importing rules from another employer.

## Rules

- Always search for existing objects before proposing new ones
- Follow project naming rules and the SAP length limit for each object type
- Propose unit tests for every new class/method
- When analysing code, look at class hierarchies, interfaces, and dependencies
- If the requirement is ambiguous, ask clarifying questions before writing specs
- Keep specifications concise but complete — a developer should implement from the spec alone
- Use the issue API's verified description format
