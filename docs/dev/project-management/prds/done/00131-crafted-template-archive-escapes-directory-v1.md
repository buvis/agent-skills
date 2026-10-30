---
design: run
default_model: sonnet
model_tier_rationale: archive containment fix requires pre-extraction validation and supported-Python regression design
---

# Crafted template archives can write outside their destination

Source: agoge report `dev/local/audit-results/agoge-2026-10-25.md`, finding 1,
accepted option A on 2026-10-29. Reports are local audit artifacts and are not
shipped in the public repository. The original reproduction invoked the template
helper directly, not the complete vet CLI. The user explicitly approved covering
finding 42 through this same PRD on 2026-10-29: safe extraction must also remove
the confirmed omitted-filter deprecation warning. Python 3.14 breakage was not
verified by that audit.

## Problem

The evaluation harness builds templates by extracting a Git archive. A crafted
tree with duplicate symlink/directory names can bypass the pre-extraction link
map and cause a file to be written through a symlink outside the template root.
An operator vetting an untrusted task repository can therefore modify files
outside the intended evaluation workspace.

## Solution

Use safe data extraction filtering and preflight the complete archive before
extracting. Reject duplicate normalized member names and any member whose parent
path crosses an archive symlink. Retain existing link containment/cycle checks
and fail with a controlled tree error for unsafe input. Provide safe behavior
on supported Python versions without an unfiltered fallback.

## Requirements

### Must have

- Reproduce the duplicate symlink/directory archive case in an isolated fixture
  and assert nothing outside the destination is written or overwritten.
- Reject duplicate normalized member names before extraction.
- Reject member paths whose ancestors cross symlinks, rather than relying on a
  dictionary that loses duplicate-member information.
- Apply data extraction filtering or an equivalent safe compatibility path;
  missing runtime support must never silently select unrestricted extraction.
- Preserve supported Python 3.10+ behavior, testing the compatibility branch as
  well as the standard filtering path.
- Preserve existing rejection of escaping link chains and cycles.
- Preserve supported ordinary files, executable bits, safe internal/dangling
  symlinks, and deterministic template sealing.
- Report an unsafe archive through the existing TreeError contract before
  initializing or recording a successful template.
- Remove omitted-filter deprecation warnings through explicit safe extraction,
  not warning suppression or fully trusted extraction. Verify warning behavior
  on supported runtimes without claiming untested Python 3.14 compatibility.

### Nice to have

- None.

## Implementation

```text
skills/use-qwen/scripts/
├── eval_harness/trees.py  # validate archive members before safe extraction
└── test_eval_tree_links.py  # duplicate-member escape and benign-link controls
```

### Module: template extraction

- **Location**: `skills/use-qwen/scripts/eval_harness/trees.py`
- **Maps-to-capability**: contain untrusted repository extraction inside the template root.
- **Responsibility**: validate all member identities/ancestors and use safe extraction.
- **Exports**: `build_template`, `TreeError`.

#### Feature: reject unsafe archives before extraction

- **Inputs**: Git archive members, member link metadata, and the destination root.
- **Outputs**: a safely sealed template or a controlled refusal without outside writes.
- **Behavior**: retain the full member sequence for duplicate detection, validate
  symlink ancestry, and apply supported safe filtering before writing members.

### Module: extraction containment tests

- **Location**: `skills/use-qwen/scripts/test_eval_tree_links.py`
- **Maps-to-capability**: prove the observed write-out cannot recur.
- **Responsibility**: cover the crafted tree and supported benign template/link cases.
- **Exports**: none.

### Dependencies

- Template extraction: existing Git archive creation, link validation, and sealing (foundation).
- Containment tests: depend on extraction and isolated Git/template fixtures.
- Existing seal/evidence consumers continue to receive valid deterministic templates.

## Tasks

### Phase 0: Foundation

- [ ] Add a failing regression using the reported duplicate-entry tree/archive
  and an outside sentinel. Preflight duplicate member identities and symlink
  ancestors before extraction, then use safe filtering with explicit runtime
  compatibility handling. Assert controlled refusal, unchanged outside state,
  and no successful seal for the attack. Cover reversed/duplicate member ordering,
  both filter-support branches, and existing safe/escaping/cyclic link controls.
  Acceptance: `uv run pytest skills/use-qwen/scripts/test_eval_tree_links.py`
  passes; the crafted write-out regression fails against pre-change code.
  Run on supported CI Python versions and retain ordinary template sealing checks.
- [ ] Cover finding 42 with a focused extraction check that treats the specific
  omitted-filter deprecation warning as an error. Confirm safe-link controls
  still pass, including the compatibility path; do not suppress unrelated warnings.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/use-qwen`,
and `braid --check` pass.

## Success Criteria

- Crafted archive input cannot write or overwrite outside the template root.
- Duplicate names and symlink-parent traversal are refused before extraction.
- Supported safe templates retain their existing sealing/link behavior.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
`trees.build_template(<repo>, <commit>, <tmpl>)` printed `before: outside holds []` / `after: outside holds ['pwned']` / content `TRUDY_ESCAPE_MARKER`. Caveat: called directly, not through the full `vet` CLI.
```

Keep every repository, destination, and outside sentinel under temporary test
roots. Do not probe the operator's repositories or files during reproduction.

Finding 42's confirmed warning evidence, preserved verbatim:

```text
The suite printed 236 warnings, all `trees.py:141: DeprecationWarning: Python 3.14 will, by default, filter extracted tar archives`.
```

The warning count belongs to the historical audit run, not a required future
suite total. Verify that the specific omitted-filter warning no longer occurs
through the explicit safe-extraction path. The audit did not verify Python 3.14
breakage; do not promote that suspicion to a confirmed failure.

### Risks

Filtering can reject previously accepted symlink templates, and older runtimes
need a safe compatibility path. Duplicate normalization and archive ordering
must not permit a bypass. Finding 42 shares this implementation by explicit user
approval; its warning symptom remains separately traceable in the audit minutes.
