---
design: skip
default_model: sonnet
model_tier_rationale: bounded path interpretation fix with containment, protection, and existing manifest regression controls
---

# Brush misinterprets absolute paths

Source: agoge report `dev/local/audit-results/agoge-2026-10-25.md`, finding 22,
accepted option A on 2026-10-29. Reports are local audit artifacts and are not
shipped in the public repository.

## Problem

Brush strips leading path separators before resolving user input. Full paths
inside the repository become incorrect relative paths, while an outside path
such as /scratch.log can be reinterpreted as the repository's scratch.log.
Operators receive confusing refusals or target a different file than intended.

## Solution

Interpret absolute paths literally and relative paths from the repository root.
Resolve the candidate and apply the existing containment check before converting
it to the repository-relative Git spelling used by protection, output, and manifests.

## Requirements

### Must have

- Eligible absolute paths inside the repository work in preview and apply modes.
- Absolute paths outside the repository are refused as outside repo, not re-rooted.
- A missing outside path must not select an existing repository-relative decoy.
- Preserve relative-path behavior and native platform path semantics, including
  Windows absolute paths and literal POSIX backslash characters.
- Resolve symlinks before containment checks so an inside spelling cannot escape
  through a link to an outside target.
- Preserve tracked, protected, age, nested-directory, and project-document vetoes.
- Keep JSON and manifest path conventions unchanged; accepted absolute input
  is reported using the existing normalized repository-relative identity.
- Update argument help to describe supported absolute and relative inputs.

### Nice to have

- None.

## Implementation

```text
skills/brush/scripts/
├── trash_untracked.py     # literal absolute inputs, containment, and help wording
└── test_brush_scripts.py  # absolute-path and re-rooting regressions
```

### Module: candidate path resolution

- **Location**: `skills/brush/scripts/trash_untracked.py`
- **Maps-to-capability**: act on the path the operator actually supplied.
- **Responsibility**: distinguish absolute/relative inputs before existing containment and vetoes.
- **Exports**: `main`, `as_git_rel`, `veto_reason`.

#### Feature: accept contained absolute paths

- **Inputs**: native absolute or repository-relative user paths.
- **Outputs**: the intended contained candidate or an outside-repo refusal.
- **Behavior**: retain native absolute meaning, then normalize only a contained
  candidate for existing protection and output logic.

### Module: path interpretation tests

- **Location**: `skills/brush/scripts/test_brush_scripts.py`
- **Maps-to-capability**: prevent accidental re-rooting and protection bypass.
- **Responsibility**: cover intended files, outside paths, decoys, and protected controls.
- **Exports**: none.

### Dependencies

- Candidate resolution: existing root, containment, and veto helpers (foundation).
- Tests: depend on resolution and temporary repository fixtures.
- Preserve PRD 00091's nested-file veto and PRD 00106's manifest convention.

## Tasks

### Phase 0: Foundation

- [ ] Add failing preview/apply cases for an old eligible file supplied by its
  absolute in-repo path, an absolute outside path, and an outside root-level
  spelling with an eligible relative decoy. Interpret paths literally before
  normalization, and update help. Assert outside/decoy files remain untouched,
  contained absolute inputs use the correct normalized identity, and protected
  absolute inputs are still refused. Include spaces and existing symlink/parent
  traversal and native path-format controls. Acceptance:
  `uv run pytest skills/brush/scripts/test_brush_scripts.py` passes; contained
  absolute and re-rooting regressions fail against prior code.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/brush`,
and `braid --check` pass.

## Success Criteria

- Absolute input selects its literal contained path or receives an outside refusal.
- No outside spelling silently selects a repository-relative file.
- Existing protection and manifest/output identities remain correct.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
`.../brushrepo/scratch.log` -> `"reason": "missing"`. `/scratch.log` was accepted as the repo's `scratch.log`.
```

Use temporary roots and decoys; do not create files in the actual filesystem root.

### Risks

Callers relying on slash-prefixed relative shorthand now receive refusals.
Incorrect normalization could break Windows paths or POSIX literal characters;
keep native interpretation distinct from Git's relative output representation.
