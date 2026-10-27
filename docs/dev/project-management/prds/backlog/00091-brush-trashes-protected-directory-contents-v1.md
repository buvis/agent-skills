---
design: skip
default_model: sonnet
model_tier_rationale: bounded recursive safety check using existing veto rules and regression fixtures
---

# brush trashes directories containing protected files

Source: agoge report `dev/local/audit-results/agoge-2026-10-26.md`, finding 2,
accepted option A on 2026-10-26. Also covers finding 6 of the 2026-10-25 report.
The reports are local audit artifacts and are not shipped in the public repository.

## Problem

Brush checks a directory's own name before moving it to trash, but does not apply
its protected-file rules to the files inside. Operators cleaning old untracked
debris can therefore move secrets or documents by selecting their parent directory.
The move is initially recoverable, but expired trash can later be permanently deleted.

## Solution

Apply the existing veto rules to every file contained in a candidate directory.
Refuse the entire directory if any contained file is vetoed. Make preview and
apply use the same decision, and preserve the existing move and manifest behavior
for eligible junk directories.

## Requirements

### Must have

- Check nested files before moving any part of a candidate directory.
- Reuse existing veto rules, including protected names, documentation, tracked
  files, protected paths, and freshness checks.
- If a contained file is vetoed, report the directory as refused and leave its
  contents in place. Do not append a move record for that directory.
- Apply the same protection in preview and apply modes.
- Continue to move eligible old directories containing only unprotected junk.
- Preserve existing direct-file protection and repository-boundary checks.

### Nice to have

- None.

## Implementation

```text
skills/brush/scripts/
├── trash_untracked.py     # inspect contained files before approving a directory
└── test_brush_scripts.py  # regressions and eligible-directory controls
```

### Module: trash eligibility

- **Location**: `skills/brush/scripts/trash_untracked.py`
- **Maps-to-capability**: protect files when their parent directory is selected.
- **Responsibility**: veto directory candidates before preview or relocation.
- **Exports**: `veto_reason`, `main`.

#### Feature: refuse directories containing vetoed files

- **Inputs**: a directory candidate, repository root, tracked paths, and age threshold.
- **Outputs**: a refusal when any contained file fails the existing eligibility rules.
- **Behavior**: inspect nested files and make an all-or-nothing eligibility decision
  before any move or manifest write for that directory.

### Module: directory protection tests

- **Location**: `skills/brush/scripts/test_brush_scripts.py`
- **Maps-to-capability**: prove directory selection cannot bypass file protection.
- **Responsibility**: exercise mixed-content directories and eligible junk controls.
- **Exports**: none.

### Dependencies

- Trash eligibility: existing veto rules and repository-relative paths (foundation).
- Directory protection tests: depend on trash eligibility and temporary repository fixtures.
- Preview and apply: share the eligibility decision before relocation (integration).

## Tasks

### Phase 0: Foundation

- [ ] Add failing regressions for a directory containing an old `.env`, an old
  `NOTES.md`, and ordinary junk, including protected files nested below another
  directory. Cover preview and apply. Reuse the existing file veto for directory
  contents. Assert refusal leaves the entire candidate in place and writes no
  manifest entry for it. Include controls for an eligible old junk-only directory
  and a protected file passed directly.
  Acceptance: `uv run pytest skills/brush/scripts/test_brush_scripts.py` passes;
  the protected-directory cases fail against the prior code.
  This finding has a strict-xfail regression only on the unmerged branch
  `agoge/authored-tests-2026-10-26`; implement independently if absent. If present,
  convert that regression to a normal test when the fix lands without merging
  unrelated branch changes.

Exit criteria: `uv run pytest`,
`uv run python3 skills/create-skill/scripts/validate_skill.py skills/brush`,
and `braid --check` pass.

## Success Criteria

- Selecting a parent directory cannot move its protected files into trash.
- Preview and apply report the same refusal for protected directory contents.
- Eligible junk-only directories retain their existing move and manifest behavior.

### Test Strategy

Carry the observed evidence verbatim from the accepted packet:

```text
Untracked old `sdir/` held `.env`, `NOTES.md`, `a.log`. `trash_untracked.py --repo <S>/repo --apply junk.log sdir` -> `"moved": [... {"path":"sdir","trash":"docs/dev/tmp/.trash/2026-10-26/sdir"}], "refused": []`. The same run refused `.env` and `scratch.txt` when passed directly.
```

Run regressions only in temporary repositories. Check file contents and manifest
state after refusal, and verify the eligible-directory control still moves as a unit.

### Risks

Large directories require traversal before eligibility is known. A stray README
now prevents trashing its entire parent directory; users must preserve it first.
Avoid following directory symlinks outside the repository while inspecting contents.
