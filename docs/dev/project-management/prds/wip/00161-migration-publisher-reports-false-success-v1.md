---
catchup: run
design: skip
default_model: sonnet
model_tier_rationale: exact behaviors and named regressions per finding; small edits to two helpers and three skill texts, no new contracts
---

# Make the migrated publisher and ABAP skills report failures honestly

Source: `docs/dev/project-management/audit-results/repository-closeout-preparation.md`
(Seven-skill migration inspection, findings C1, C2 and C5) and the custody addendum
`repository-closeout-preparation-session-123534.md` (C6, C7, and the C2
replacement boundary). This branch is based on PR #17 head
`9249695b334f2a894bda8e016d974480cece918e`. C3 (PR body follow-up number) and
C4 (licence provenance) are PR metadata. The closeout coordinator owns them, not
this PRD. Reserved PRD 00159 (validator consolidation) stays out of scope.

## Overview

### Problem Statement
- C1: `upload` in `skills/publish-confluence-docs/scripts/confluence_attach.py`
  checks only the HTTP code that curl writes to stdout. A curl exit 23 with
  stdout `200` returns True. `/dev/null` is hard-coded as the response sink,
  which does not exist on Windows.
- C2: `image_tag` in `skills/publish-confluence-docs/scripts/confluence_embed_images.py`
  puts the filename into an XML attribute without escaping. `a&b.png` produces
  invalid storage XML. `re.sub` also treats the replacement as a template, so a
  backslash in a filename is reinterpreted.
- C5: in `skills/publish-confluence-docs/SKILL.md`, `## Dependencies` comes
  after the pipeline and script sections, against the repository rule that it
  follows the intro. `skills/explore-abap-solution/SKILL.md` names the
  `document-abap-solution` next step outside its Dependencies section and does
  not say it is a human handoff.
- C6: `skills/explore-abap-solution/SKILL.md` says manual inspection cannot
  replace the automated gate. Its Phase V step 1 then tells the runner to
  reproduce every check by hand when the helper is missing, which yields a
  PASS-shaped report.
- C7: `skills/document-abap-solution/SKILL.md` forbids a separate
  `solution.json`, but its consistency step still lists `solution.json` as an
  input.

### Target Users
Users who publish documents to Confluence or run the ABAP exploration and documentation skills.

### Success Metrics
- `uv run --with python-docx==1.1.2 --with pymupdf==1.25.3 --with pyyaml==6.0.2 python -m pytest skills/publish-confluence-docs` passes, including the new regressions below.
- `uv run python3 skills/create-skill/scripts/validate_skill.py` exits 0 for `skills/publish-confluence-docs`, `skills/explore-abap-solution` and `skills/document-abap-solution`.
- `python3 skills/explore-abap-solution/scripts/check_run.py --selftest` and `python3 skills/document-abap-solution/scripts/check_run.py --selftest` exit 0.

## Functional Decomposition

### Capability: Honest publishing results
The publisher helpers report success only when the remote write succeeded.

#### Feature: Attachment upload success requires process and HTTP success
- **Description**: `upload` returns True only when curl exits 0 and the HTTP status is 200-299.
- **Inputs**: The curl `CompletedProcess`.
- **Outputs**: True or False, and one `OK:` or `FAIL:` line.
- **Behavior**: Use `os.devnull` as the `-o` sink, never a literal path. Treat any nonzero curl exit as failure, and name the exit code in the `FAIL:` line. A missing curl (`FileNotFoundError`) is failure with a message naming curl, not a traceback. Never print the token.

#### Feature: Escaped image tags and literal replacement
- **Description**: The image tag is valid XML for any filename, and the replacement is inserted literally.
- **Inputs**: Filename, width, page storage content.
- **Outputs**: Updated storage content.
- **Behavior**: Escape the filename with the standard library's XML attribute quoting (xml.sax.saxutils quoteattr) or an equivalent that covers `&`, `<`, `>` and `"`. Replace the matched note macro with a function replacement (`lambda _m: tag`), so backslashes stay literal. Ordinary names produce byte-identical tags to today.

### Capability: Honest skill instructions
Skill text never lets a missing tool turn into a claimed pass.

#### Feature: Missing self-check is INCOMPLETE
- **Description**: In `skills/explore-abap-solution/SKILL.md` Phase V step 1, a missing `check_run.py` makes the package `Status: INCOMPLETE` with the reason "self-check helper missing (incomplete skill copy)" and recovery guidance to reinstall the skill. It does not tell the runner to hand-reproduce PASS lines.
- **Inputs**: Skill text.
- **Outputs**: Edited skill text consistent with its line 19 rule.
- **Behavior**: Both passages agree that manual inspection is never a substitute for the automated gate.

#### Feature: Consistent dependency and data references
- **Description**: Put Dependencies directly after the intro in the publisher skill. Declare the explore→document step as a human handoff. Refer to embedded solution data, not `solution.json`, in the documentation skill's consistency step.
- **Inputs**: Three SKILL.md files.
- **Outputs**: Edited texts that pass the validator.
- **Behavior**: The explore skill's Dependencies section gains: "`document-abap-solution` (sibling, human handoff): the final report points the user at it; this skill never invokes it. Absent: the research package is still complete and valid." The document skill's consistency list names "the inline `solution-data` block" in place of `solution.json`.

## Structural Decomposition

### Repository Structure

```
skills/
├── publish-confluence-docs/
│   ├── SKILL.md                                  # Maps to: Consistent dependency and data references
│   ├── scripts/confluence_attach.py              # Maps to: Attachment upload success
│   ├── scripts/confluence_embed_images.py        # Maps to: Escaped image tags
│   └── tests/test_confluence_exit_codes.py       # Maps to: C1 and C2 regressions
├── explore-abap-solution/
│   └── SKILL.md                                  # Maps to: Missing self-check is INCOMPLETE; human handoff
└── document-abap-solution/
    └── SKILL.md                                  # Maps to: embedded solution data reference
```

### Module: publisher helpers
- **Maps to capability**: Honest publishing results
- **Location**: `skills/publish-confluence-docs/scripts/confluence_attach.py`, `skills/publish-confluence-docs/scripts/confluence_embed_images.py`, `skills/publish-confluence-docs/tests/test_confluence_exit_codes.py`
- **Responsibility**: Report upload and embed results truthfully without network access in tests.
- **Exports**:
  - `upload()` - unchanged signature.
  - `image_tag()` - unchanged signature, escaped output.

### Module: skill texts
- **Maps to capability**: Honest skill instructions
- **Location**: `skills/publish-confluence-docs/SKILL.md`, `skills/explore-abap-solution/SKILL.md`, `skills/document-abap-solution/SKILL.md`
- **Responsibility**: Instructions consistent with the repository's dependency convention and with each skill's own gates.
- **Exports**: none

## Dependency Graph

### Foundation Layer (Phase 0)
No dependencies - built first.

- **publisher helpers**: Independent of the skill texts.
- **skill texts**: Independent of the helpers.

### Core Layer (Phase 1)
- **skill texts**: Depends on [] (validated after editing).

### Integration Layer (Phase 2)
- None: the two modules ship together and share no code.

## Implementation Phases

### Phase 0: Foundation
**Goal**: Fix the two helper defects with regressions.

**Tasks**:
- [ ] Make `upload` in `skills/publish-confluence-docs/scripts/confluence_attach.py` require curl exit 0 and a 2xx status, use `os.devnull`, and handle a missing curl; add tests in `skills/publish-confluence-docs/tests/test_confluence_exit_codes.py` for curl exit 23 with stdout `200`, missing curl, HTTP 500, and success, all with a mocked `subprocess.run` (no deps) - Acceptance: `uv run --with python-docx==1.1.2 --with pymupdf==1.25.3 --with pyyaml==6.0.2 python -m pytest skills/publish-confluence-docs/tests/test_confluence_exit_codes.py -k "upload"` passes, and the curl-exit-23 test fails against the old `upload`.
- [ ] Escape the filename in `image_tag` and use a function replacement in `skills/publish-confluence-docs/scripts/confluence_embed_images.py`; add tests for `a&b.png`, `q"x.png`, a backslash name, an ordinary name (byte-identical tag), and an XML parse of the produced tag (no deps) - Acceptance: `uv run --with python-docx==1.1.2 --with pymupdf==1.25.3 --with pyyaml==6.0.2 python -m pytest skills/publish-confluence-docs/tests/test_confluence_exit_codes.py -k "image"` passes.

**Exit Criteria**: Both helper regressions pass, and the old code fails them.

### Phase 1: Core
**Goal**: Align the three skill texts.

**Tasks**:
- [ ] Move `## Dependencies` in `skills/publish-confluence-docs/SKILL.md` to directly after the intro, without changing its content (no deps) - Acceptance: `rg -n "^## " skills/publish-confluence-docs/SKILL.md` lists Dependencies first; the validator exits 0.
- [ ] Rewrite Phase V step 1 of `skills/explore-abap-solution/SKILL.md` so a missing helper means INCOMPLETE, and add the human-handoff Dependencies entry (no deps) - Acceptance: `rg -n "reproduce every check by hand" skills/explore-abap-solution/SKILL.md` finds nothing; `rg -n "human handoff" skills/explore-abap-solution/SKILL.md` finds the entry; validator and `--selftest` exit 0.
- [ ] Replace `solution.json` with the inline `solution-data` block in the consistency step of `skills/document-abap-solution/SKILL.md` (no deps) - Acceptance: `rg -n "notes.md, solution.json" skills/document-abap-solution/SKILL.md` finds nothing; validator and `--selftest` exit 0.

**Exit Criteria**: All three validators and both selftests exit 0.

### Phase 2: Integration
**Goal**: Confirm the complete migration-skill suite.

**Tasks**:
- [ ] Run the dependency-enabled migration suite (depends on: Phase 1) - Acceptance: `uv run --with mcp==2.3.0 --with httpx2==2.16.0 --with python-docx==1.1.2 --with pymupdf==1.25.3 --with pyyaml==6.0.2 python -m pytest -q -ra skills/build-mcp-server skills/create-adr skills/document-abap-solution skills/explore-abap-solution skills/publish-confluence-docs skills/review-abap-solution-documentation skills/write-abap-specs` passes with zero skips.

**Exit Criteria**: `uv run pytest` and `uv run ruff check` pass at the lane tip.

## Test Strategy

### Critical Scenarios
- **Happy path**: curl exit 0 with stdout `201` → `OK: Uploaded`, returns True.
- **Edge case**: Filename `a&b.png` → the tag parses as XML and its `ri:filename` reads back as `a&b.png`.
- **Error case**: curl exit 23 with stdout `200` → `FAIL:` line naming exit 23, returns False, and `main` exits 1.

## Risks

- **Live Confluence behavior is unverified**: The tests mock curl and urllib only. No live publishing is attempted, and the PR keeps that limit stated.
