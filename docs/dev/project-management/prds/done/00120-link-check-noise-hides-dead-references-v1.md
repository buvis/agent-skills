---
design: run
default_model: sonnet
model_tier_rationale: reference-context rules and current PRD repair inventory require design before implementation
---

# Link-check noise obscures genuine broken PRD references

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 30,
accepted option A on 2026-10-28. The report is a local audit artifact and is not
shipped in the public repository.

## Problem

The working-document link checker reports both genuine missing references and
literal examples as broken links. The audit recorded 228 findings, including
TOML-like double-bracket examples and prior checker diagnostics misread as fresh
references. Real dead links in PRDs become harder to distinguish from noise,
so operators cannot rely on the check to identify new document rot.

## Solution

First make reference detection distinguish actual citations from literal syntax
and quoted checker output. Then repair genuine missing references in PRDs, using
verified replacement targets or removing obsolete citations. Do not broadly
exclude historical audit bundles or weaken detection of real missing references.

## Requirements

### Must have

- The reported literal double-bracket and diagnostic-prefix examples no longer
  produce spurious memory/PRD findings in their actual document contexts.
- Genuine missing paths, PRD citations, and memory links remain detectable with
  citing line context and the existing error contract.
- Determine current PRD repair targets after correcting false positives; the
  historical finding count is not a fixed completion target.
- Repair or remove genuine obsolete PRD references without fabricating targets
  or dropping citations still needed to understand requirements.
- Verify missing-target premises at execution time; skip already-fixed links and
  use current lifecycle locations for moved documents.
- Preserve PRD 00100's ordinary-root isolation and documented ~/.claude behavior.
- Retain historical audit scanning; do not silence whole directories as remediation.

### Nice to have

- None.

## Implementation

```text
skills/review-prd-backlog/scripts/
├── check_links.py       # context-aware reference extraction
└── test_check_links.py  # literal examples and genuine-link positive controls
docs/dev/project-management/prds/backlog/
└── 00050-qwen-ivan-capability-eval-v1.md        # reported genuine dead-link example (out of scope, do not edit)
docs/dev/project-management/prds/wip/
└── 00120-link-check-noise-hides-dead-references-v1.md  # this PRD
docs/dev/project-management/prds/done/
├── 00118-historical-commit-types-preserve-history-v1.md   # stale backlog/ lifecycle path, line 54
├── 00017-malformed-memory-half-written-v1.md              # provenance in dev/local, line 134
├── 00003-add-plan-port-skill-v1.md                        # provenance in dev/local, line 7
├── 00015-corrupt-queue-reads-as-drained-v1.md              # provenance in dev/local, line 101
├── 00006-nag-audit-cadence-in-brief-portfolio-v1.md        # provenance in dev/local, lines 3, 16, 166
├── 00002-add-sweep-fix-skill-v1.md                         # provenance in dev/local, line 3
├── 00009-walk-memory-proposal-queue-v1.md                  # provenance in dev/local, line 3
├── 00004-add-capture-experiment-skill-v1.md                # provenance in dev/local, line 7
├── 00030-survey-prunes-skip-dirs-deep-v1.md                # provenance in dev/local, line 91
├── 00007-extract-memory-candidates-from-transcripts-v1.md  # provenance in dev/local, line 7
└── 00008-distil-memory-proposals-v1.md                     # provenance in dev/local, line 8
docs/dev/project-management/designs/
└── 00120-link-check-noise-hides-dead-references-v1-design.md  # link-ok: waiver on the new doc's own example tokens
```

Design prerequisite: inspect current documents and enumerate every PRD file that
needs repair. Add each exact repo-relative path to this Repository Structure
before implementation planning. Resolve moved lifecycle paths there as well;
do not use globs, infer an unrestricted docs allowlist, or edit unlisted files.
This execution-time inventory is required because the accepted evidence is a
historical count and supplies only one concrete PRD example.

### Module: reference extraction

- **Location**: `skills/review-prd-backlog/scripts/check_links.py`
- **Maps-to-capability**: distinguish real references from document syntax and diagnostics.
- **Responsibility**: remove supported false positives without broad exclusions.
- **Exports**: `scan_file`, `run`.

#### Feature: classify reference context

- **Inputs**: working Markdown, citation tokens, and their surrounding syntax.
- **Outputs**: actual reference findings with existing file/line context.
- **Behavior**: distinguish literal examples and quoted diagnostics from genuine
  references while preserving positive detection and existing waivers.

### Module: reference regression tests

- **Location**: `skills/review-prd-backlog/scripts/test_check_links.py`
- **Maps-to-capability**: prove noise removal does not conceal genuine rot.
- **Responsibility**: pair each reported false-positive context with real-link controls.
- **Exports**: none.

### Module: PRD reference repair

- **Initial location**: `docs/dev/project-management/prds/backlog/00050-qwen-ivan-capability-eval-v1.md`
- **Maps-to-capability**: keep current PRD citations useful and resolvable.
- **Responsibility**: repair the concrete files enumerated during design, rechecking premises.
- **Exports**: none.

### Dependencies

- Reference extraction and tests: foundation, completed before classifying repair targets.
- PRD repair: depends on corrected classification and the concrete design inventory.
- Existing source-scope and reference-resolution contracts remain integration constraints.

## Tasks

### Phase 0: Foundation

- [ ] Add failing regressions reproducing the reported literal and diagnostic
  contexts, then correct reference extraction. Pair them with genuine unresolved
  memory, path, and PRD examples, and existing resolution/waiver controls.
  Acceptance: `uv run pytest skills/review-prd-backlog/scripts/test_check_links.py`
  passes; supported false-positive regressions fail against prior code while
  genuine missing references continue to be reported.

### Phase 1: PRD repair

- [ ] Depends on Phase 0 and the design's concrete path inventory. Premise:
  each listed citation is still genuinely broken after the checker correction.
  Re-check targets and lifecycle locations, repair verified replacements, and
  remove only obsolete references. Skip already-fixed cases and report why.
  Acceptance: every classified broken reference in the enumerated PRD files
  is repaired or removed, with replacement targets verified on disk; record
  remaining historical audit findings separately without broad exclusions.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/review-prd-backlog`,
and `braid --check` pass.

## Success Criteria

- Reported false-positive contexts no longer create spurious findings.
- Genuine missing references remain visible and cited PRD repairs resolve.
- Completion is based on current scoped findings, not an obsolete count or
  blanket suppression of historical documents.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
`check_links.py --root <repo> --json` -> exit 1, 228 findings, `scan_errors: []`. By location: audit-results 93, reviews 46, autopilot 44, prds 21, designs 13, meta 9, notes 1. 1 hit is outside the root (`/Users/.../memory/review-phase-known-overhead.md:22`, see packet 11). 0 hits in `README.md`, `AGENTS.md`, `CHANGELOG.md` or any `skills/*/SKILL.md`. Real rot example: `prds/backlog/00050-qwen-ivan-capability-eval-v1.md` cites `prds/done/00049-qwen-completion-status-v1.md` and `audit-results/qwen-ivan-calibration/protocol.md`, both missing. False positives: `[[package]]` and `[[links]]` read as wikilinks "(no memory)", and `00057- (no PRD/discovery file)` prefixes in `meta/project-capsule.md`.
```

Use isolated fixture trees for extraction regressions. Recheck current repository
references only during this PRD's design/implementation, rather than replaying the
historical audit during the decision walkthrough.

### Risks

Overbroad context filtering can hide real links in code examples or historical
prose. Most original findings were historical audit material, so repairing PRDs
does not imply zero findings across all documents. Source documents may move
while queued; exact scope refinement and premise checks are mandatory.
