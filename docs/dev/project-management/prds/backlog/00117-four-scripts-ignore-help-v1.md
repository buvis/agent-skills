---
design: skip
default_model: sonnet
model_tier_rationale: four bounded CLI help branches with direct command verification
---

# Four documented scripts do not answer help requests

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 27,
accepted option A on 2026-10-28. The report is a local audit artifact and is not
shipped in the public repository.

## Problem

Survey ignores --help and scans the repository; three design-review helpers
interpret --help as a filename and fail. Users and agents cannot discover usage
through the usual help convention despite these being documented entry points.

## Solution

Accept -h and --help in the four scripts, print a concise one-line usage message
to stdout, and exit 0 before scanning a repository or reading a document.
Preserve normal invocation and error behavior. Do not add the repository-wide
documented-script gate proposed by option B.

## Requirements

### Must have

- Both help spellings produce usage and exit 0 in every named script.
- Help does not produce a survey brief, scan a document, or write artifacts.
- Usage names the script and its existing positional input where applicable.
- Normal survey and valid-document invocations preserve their output.
- Missing-argument and invalid-file behavior remains useful outside help requests.

### Nice to have

- None.

## Implementation

```text
skills/survey/scripts/run.py
skills/review-design-doc/scripts/section_weight_audit.py
skills/review-design-doc/scripts/claim_ladder_scan.py
skills/review-design-doc/scripts/adversarial_signal_scan.py
```

### Module: survey entry point

- **Location**: `skills/survey/scripts/run.py`
- **Maps-to-capability**: discover survey usage without running a survey.
- **Responsibility**: handle help before repository scanning.
- **Exports**: `main`.

#### Feature: provide concise help

- **Inputs**: -h or --help as the help argument.
- **Outputs**: one-line usage on stdout and exit 0.
- **Behavior**: return before normal input processing, preserving other invocations.

### Module: section weight entry point

- **Location**: `skills/review-design-doc/scripts/section_weight_audit.py`
- **Maps-to-capability**: explain the required document argument.
- **Responsibility**: handle help before file validation.
- **Exports**: `main`.

### Module: claim ladder entry point

- **Location**: `skills/review-design-doc/scripts/claim_ladder_scan.py`
- **Maps-to-capability**: explain the required document argument.
- **Responsibility**: handle help before file validation.
- **Exports**: `main`.

### Module: adversarial signal entry point

- **Location**: `skills/review-design-doc/scripts/adversarial_signal_scan.py`
- **Maps-to-capability**: explain the required document argument.
- **Responsibility**: handle help before file validation.
- **Exports**: `main`.

### Dependencies

- All four entry points: independent existing scripts (foundation).
- No new cross-skill dependency or repository-wide test gate is introduced.

## Tasks

### Phase 0: Foundation

- [ ] Add -h/--help handling to the four entry points before scanning or file
  checks. Verify each script with both flags using the normal Python invocation,
  not isolated mode, which breaks existing local imports. Acceptance: all eight
  help invocations exit 0, print one-line usage, and produce no brief, file error,
  or artifacts. Check a representative normal survey and valid temporary-document
  invocation for each review helper to preserve their existing behavior.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/survey`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/review-design-doc`,
and `braid --check` pass. Direct command checks suffice for these small branches;
do not add a repository-wide documented-script help test.

## Success Criteria

- All four scripts answer both standard help flags without running their work.
- Normal input and output behavior remains intact.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
A scripted `python3 <script> --help` sweep over every script path named in a SKILL.md: `rc=1 ... ['error: not a file: --help']` for the three; `run.py --help` printed the brief. Every other `.py` script answered `--help` rc 0 (audit_qwen, collect_facts, trash_untracked, ground_prd, init_skill, validate_skill, build, parse, docket, funnel, write, glean, purge_devtmp, check_links, structure_repo, sweep, run_eval_harness). Under `python3 -I` three scripts failed with ImportError; that is an artefact of the `-I` flag.
```

### Risks

The benefit is small per script. Keep the implementation to help handling and
avoid a broader argument-parser refactor. Preserve survey's existing footer
and other output, including the documentation correction in PRD 00116.
