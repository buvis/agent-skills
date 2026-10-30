---
design: run
default_model: sonnet
model_tier_rationale: Portable path serialization requires consumer compatibility and a bounded tracked-document inventory.
---

# Documents publish personal home paths

Source: `dev/local/audit-results/agoge-2026-10-25.md`, finding 46, audit dated 2026-10-25. User accepted option A on 2026-10-29. Status remains unverified: the audit combined static path searches with a writer code read, without a product run demonstrating a newly generated disclosure.

## Problem

The audit reported personal absolute home paths in 49 tracked project-management documents and observed that proposal manifests serialize absolute transcript paths. The repository forbids personal paths in public artifacts. Existing documents retain machine-specific identifiers, and generators can repeat the pattern.

## Solution

Use repository-relative paths where appropriate and home-relative notation for references beneath the operator's home. Update affected generators and their consumers together, scrub current tracked documents, and add a focused regression check. Preserve historical commits and tags.

## Requirements

### Must have

- Inventory the current tracked project-management documents with personal home prefixes before editing. The historical count of 49 is not an exact current target.
- During design, enumerate the concrete document and generator paths to change and add that inventory to this PRD's structural decomposition. Do not approve an unbounded sweep of unrelated files.
- Generated reports and proposal/discard manifests must not serialize the operator's absolute home prefix. Use portable paths, with correct component-boundary checks rather than arbitrary substring replacement.
- Update consumers that open or compare serialized transcript paths so home-relative paths resolve intentionally. Preserve legacy absolute records, stable evidence association, queue deduplication, and store ownership checks.
- Scrub the identified current tracked documents with context-aware replacements, preserving evidence meaning and valid repository-relative links. Review link destinations and structured data separately from prose.
- Add a regression check for personal home prefixes in tracked project-management documents, including prefixes from other machines; allow explicit generic placeholders such as /Users/you and synthetic fixture values outside that public-document scope.
- Keep diagnostics free of copied private path contents where a path-only diagnostic suffices. Do not add the actual operator prefix to the test source or this PRD.
- Preserve git history and tags. Correcting current documents does not erase historical exposure.

### Nice to have

None.

## Implementation

Initial confirmed code locations and planned regression file:

```text
skills/distil-memory/scripts/
  proposal.py
  funnel.py
  docket.py
  test_proposal_publication.py
  test_funnel_distil.py
  test_docket.py
  test_docket_unpublished.py
scripts/
  test_public_doc_paths.py  # new tracked-document regression
docs/dev/project-management/  # design must enumerate concrete affected files
```

The design must replace the final directory-only placeholder with the current affected document inventory and add any other demonstrated generator/consumer paths before implementation. The local audit report remains the durable original evidence; do not copy private home paths into tracked planning artifacts.

### Module: Portable artifact paths

- **Location**: `skills/distil-memory/scripts/proposal.py`, `skills/distil-memory/scripts/funnel.py`
- **Maps-to-capability**: Generated artifacts avoid personal absolute home prefixes.
- **Responsibility**: Serialize portable source and report references without altering transcript content or evidence meaning.
- **Exports**: `write_proposals`, `render_yield`, and existing report output.

#### Feature: Portable serialization

- **Inputs**: Source transcript paths, generated artifact paths, home and repository context.
- **Outputs**: Portable references preserving the intended source identity.
- **Behavior**: Prefer repository-relative references when the consumer has that context; represent home descendants with home-relative notation and expand deliberately at the I/O boundary. Define a safe non-home external-path representation during design rather than copying another user's identifier. Avoid resolving a display-only reference merely to reconstruct an absolute public string.

### Module: Path consumers

- **Location**: `skills/distil-memory/scripts/docket.py` and its existing tests listed above.
- **Maps-to-capability**: Portable references retain queue identity and store matching.
- **Responsibility**: Normalize accepted old and new path forms consistently at comparison/open boundaries.
- **Exports**: Existing docket commands and proposal-loading behavior.

### Module: Current documents and regression check

- **Location**: Concrete documents enumerated during design; new regression file scripts/test_public_doc_paths.py.
- **New symbols**: `scripts/test_public_doc_paths.py`.
- **Maps-to-capability**: Existing public documents are scrubbed and future home-prefix regressions fail verification.
- **Responsibility**: Inspect tracked paths rather than unrelated ignored local artifacts; report offending relative filenames without reproducing private contents.
- **Exports**: Pytest regression collected by the existing scripts test path.

### Dependencies

- Path writers and consumers must land together. Existing proposal publication, docket deduplication, and unpublished-store tests are compatibility controls.
- The existing pytest configuration collects scripts tests; no new CI service or external scanner is needed.

## Tasks

### Phase 0: Bounded inventory and repair

- [ ] Enumerate the current tracked-document occurrences and demonstrated generators/consumers, record concrete paths in the design and this PRD, and define reversible portable path rules. Keep private prefixes out of tracked artifacts.
- [ ] Update generators and consumers together, covering both portable and legacy records without duplicate queue entries or incorrect store matching.
- [ ] Scrub the enumerated current documents while preserving structured formats, evidence meaning, and valid links. Review the complete document diff.
- [ ] Add the tracked-document home-prefix regression and synthetic-home generator/consumer tests. Assert fake home prefixes are absent from published artifacts and portable references resolve to the correct source locally.
- [ ] Run `uv run pytest skills/distil-memory/scripts scripts/test_public_doc_paths.py` and repository-required checks before committing. Validate any additional touched skill.

Exit criteria: The bounded current-document inventory is scrubbed, new artifacts omit personal home prefixes, old/new path consumers retain behavior, and regression checks pass.

## Success Criteria

- No personal absolute home prefix remains in the scoped tracked public documents.
- Generator tests demonstrate portable output and correct consumer round trips.
- Existing queue identity, store matching, and proposal publication tests pass.

### Test Strategy

Original suspected evidence, preserved verbatim:

```text
`rg -l "<home>" docs/dev/project-management` -> 49 files; `git ls-files` confirms the sampled ones are tracked.
```

The source deliberately uses a placeholder for the private prefix. Recompute the current inventory during design without treating the historical count as a measured current fact. Use fake home directories for runtime regressions, including proposal and discard manifests, rendered reports, legacy absolute records, and equivalent portable records. Verify deduplication and store ownership comparisons use the same source identity. The new tracked-document check must detect a synthetic personal prefix while allowing documented generic examples.

### Risks

Blind text replacement can break links or structured records. Tilde strings do not expand automatically in Path construction, and changing serialized strings can defeat queue deduplication. Coordinate writers and consumers, preserve legacy records, and review the bounded scrub. History continues to contain old paths by explicit preserve-history policy.
