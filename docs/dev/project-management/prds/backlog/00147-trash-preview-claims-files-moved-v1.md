---
design: skip
default_model: sonnet
default_model_rationale: Additive JSON field with existing preview and apply tests.
---

# Trash preview claims files moved

Source: `dev/local/audit-results/agoge-2026-10-25.md`, finding 39, audit dated 2026-10-25. User accepted option A on 2026-10-29.

## Problem

The default trash preview prints candidate paths under the JSON key moved even though no file moves. Its dry-run warning is on stderr, so a consumer reading stdout alone can mistake the preview for an applied operation.

## Solution

Add a top-level Boolean applied field to the existing JSON result: false for previews, true for a completed invocation with --apply. Preserve existing moved and refused fields for compatibility.

## Requirements

### Must have

- Preview results contain `"applied": false` and leave files and manifests unchanged.
- Successful --apply invocations contain `"applied": true`; the existing moved and refused lists still describe individual results, including all-refused cases.
- Preserve existing moved/refused shapes, exit behavior, and stderr dry-run marker.
- The field describes execution mode, not a claim that every requested path moved. Do not turn failed mutations into successful JSON results.
- Document the field where the script's output is described, without a schema rename or new workflow.

### Nice to have

None.

## Implementation

```text
skills/brush/scripts/trash_untracked.py
skills/brush/scripts/test_brush_scripts.py
```

### Module: Trash result

- **Location**: `skills/brush/scripts/trash_untracked.py`
- **Maps-to-capability**: Machine-readable preview versus apply distinction.
- **Responsibility**: Include the mode flag in stdout JSON and describe its meaning in the existing script documentation.
- **Exports**: `main`.

#### Feature: Applied flag

- **Inputs**: Existing CLI arguments, including optional --apply.
- **Outputs**: Existing result JSON plus the applied Boolean.
- **Behavior**: Return false in preview and true for a completed apply invocation; retain per-path refusals and all mutation safeguards.

### Module: Trash regression tests

- **Location**: `skills/brush/scripts/test_brush_scripts.py`
- **Maps-to-capability**: Reliable stdout-only mode interpretation.
- **Responsibility**: Assert the flag and unchanged side-effect contracts using existing fixtures.
- **Exports**: Existing pytest tests.

### Dependencies

- Existing brush test fixtures and Python standard library. No new runtime dependency.

## Tasks

### Phase 0: Add the mode flag

- [ ] Add and document the top-level Boolean applied field without renaming existing keys.
- [ ] Extend preview and apply tests to assert the flag, retained list shapes, actual file placement, and preview absence of manifest writes. Cover an all-refused result so the mode flag is not confused with a moved-count flag.
- [ ] Run `uv run pytest skills/brush/scripts/test_brush_scripts.py` and repository-required checks before committing.

Exit criteria: A stdout-only consumer can identify preview mode and existing result consumers retain their fields.

## Success Criteria

- Every successful preview JSON result explicitly states applied false.
- Apply results and filesystem effects remain consistent with the existing per-path lists.

### Test Strategy

Original confirmed evidence, preserved verbatim:

```text
{"moved": [{"path": "old_junk.log", ...}]}, exit 0, file still in place.
```

Use existing temporary-repository fixtures to parse stdout JSON in both modes. Verify the preview flag and unchanged source file, then verify apply mode and its moved file. Keep the dry-run stderr marker and refusal regressions intact.

### Risks

Consumers ignoring the new field may still misinterpret previews. This is the accepted compatibility tradeoff; renaming moved to would_move was option B and is outside scope.
