---
design: skip
default_model: sonnet
default_model_rationale: Small existing Python error path with focused regression coverage.
---

# Report a missing memory store clearly

Source: Agoge 2026-10-25, finding 25. User accepted option A on 2026-10-29.

## Problem

The memory writer reports an absent temporary output file when the destination store directory does not exist. This hides the actual prerequisite and contradicts the documented diagnostic.

## Solution

Validate the destination directory before attempting a memory write. Raise the existing controlled error with `store directory does not exist: <store>` for an absent store. Keep directory creation an explicit caller action.

## Requirements

### Must have

- An absent destination store produces the diagnostic above, naming the supplied store path.
- Both direct writer use and the CLI refuse before creating any memory, index, or temporary file.
- The CLI returns 1, writes the error to stderr, and produces no stdout or traceback.
- Preserve existing successful writes, update checks, pointer updates, and rollback behavior.
- Replace the existing self-derived missing-store expectation with an independent assertion of the diagnostic.

### Nice to have

None.

## Implementation

```text
skills/distil-memory/scripts/
  write.py
  test_write.py
  test_write_cli.py
```

### Module: Memory writer

- **Location**: `skills/distil-memory/scripts/write.py`
- **Maps-to-capability**: Controlled refusal for an absent destination store.
- **Responsibility**: Validate the store before writing and report the prerequisite through the existing error path.
- **Exports**: `write_memory`, `WriteError`, `main`.

#### Feature: Missing-store refusal

- **Inputs**: Valid proposal entry and absent destination directory.
- **Outputs**: A controlled error naming the store; CLI exit 1.
- **Behavior**: Check the store before writes, preserve the absent directory, and retain all other existing validation and rollback contracts. Do not infer directory creation from a mistyped path. Handle other filesystem failures through existing controlled diagnostics without mislabeling permissions as absence.

### Module: Writer regression tests

- **Location**: `skills/distil-memory/scripts/test_write.py`, `skills/distil-memory/scripts/test_write_cli.py`
- **Maps-to-capability**: Stable public diagnostic and refusal without side effects.
- **Responsibility**: Assert the direct exception and CLI behavior using an absent temporary test path.
- **Exports**: Existing pytest tests.

### Dependencies

- Writer tests depend on the existing writer and test helpers. No new runtime dependency.

## Tasks

### Phase 0: Diagnostic and regression

- [ ] Validate the destination before memory writes and emit the selected controlled diagnostic.
- [ ] Assert the exact diagnostic independently in direct and CLI tests; verify exit 1, empty stdout, no traceback, and no created directory or temporary file.
- [ ] Run `uv run pytest skills/distil-memory/scripts` and the repository-required checks before committing.

Exit criteria: An absent store is identified clearly, existing-store behavior passes regression coverage, and no directory is created implicitly.

## Success Criteria

- Users see the missing store path instead of a temporary filename.
- Existing write and rollback tests pass.

### Test Strategy

Original confirmed evidence, preserved verbatim:

```text
[Errno 2] No such file or directory: '.../nostore/widget-fact.md.tmp'
```

The original CLI returned 1. Exercise direct and CLI refusal with a valid entry and absent store; assert the new message rather than deriving it from the function under test. Run the existing writer regression suite.

### Risks

A generic directory check can obscure permission failures. Preserve meaningful controlled diagnostics for those failures and avoid expanding this change into store creation or unrelated validation.
