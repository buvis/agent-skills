---
catchup: run
design: skip
default_model: opus
model_tier_rationale: clone path of a security-containment module, with native Windows semantics verifiable only on the hosted runner
---

# Clone chained links and check the disk mode correctly on native Windows

Source: `docs/dev/project-management/audit-results/repository-closeout-execution.md`,
entry "Stage 1 repair cycle 1", native run 41523204971 on candidate
`5bc7cc4`. Builds on PRD 00162, which is built and waits for review on
`closeout/archive-windows`. This PRD repairs the last 6 Windows failures that
run found. Linux, macOS and every other Windows test pass.

## Overview

### Problem Statement
The hosted Windows job (CPython 3.13.17) failed 6 tests:

1. **Clone link text keeps `/` (4 tests).**
   `test_fresh_clone_copies_a_link_chain_that_stays_inside_the_template` in
   `skills/use-qwen/scripts/test_eval_tree_links.py` fails for four of its
   five chains with `OSError: [Errno 22] Invalid argument` when it reads the
   chain's last link in the clone. `_copytree_links_typed` in
   `skills/use-qwen/scripts/eval_harness/trees.py` passes `os.readlink(link)`
   to `os.symlink` unchanged. The fixture writes chain links such as
   `alias/calc.py` with `/`. Windows cannot resolve a relative link whose
   text holds `/` (ERROR_INVALID_NAME, reported as EINVAL). The one chain that
   passes has no `/` in its link text. PRD 00162 already required
   host-separator text in `fresh_clone`; the archive path
   (`_lay_links_typed`) does it, the clone path does not.
2. **The control test reads the executable bit from disk (2 tests).**
   `test_control_build_template_keeps_the_executable_bit_and_only_where_it_was_set`
   in `skills/use-qwen/scripts/test_eval_tree_archive_safety.py` now passes
   its sealed-mode assertion on both seams, then fails at line 587 on
   `bin/run`: it compares `lstat().st_mode & S_IXUSR` with the archive mode.
   Windows keeps no executable bit on disk, so the bit cannot be read there.

### Target Users
Maintainers who run the qwen evaluation harness on Windows, and the Windows CI job.

### Success Metrics
- The hosted Windows job passes every test, with no new skip and no xfail.
- Every existing POSIX assertion still runs and passes on Linux and macOS, unchanged in strength.

## Functional Decomposition

### Capability: Clone links spelled for the host
#### Feature: Host-separator link text in clones
- **Description**: `fresh_clone` writes each link's text with the host separator.
- **Inputs**: The template's link text.
- **Outputs**: Clone links that resolve on Windows.
- **Behavior**: In `_copytree_links_typed`, convert `/` in the link text to `os.sep` before `os.symlink`, as `_lay_links_typed` does. Typing, the escape refusal and the copy order stay as they are. On POSIX the text is unchanged. Link text read back with `Path(os.readlink(p)).as_posix()` still equals the template's text.

### Capability: Disk executable bit checked where the host keeps one
#### Feature: Capability-guarded disk check
- **Description**: Check the on-disk executable bit only on a host that keeps one.
- **Inputs**: The sealed template.
- **Outputs**: Test assertions.
- **Behavior**: The sealed-mode assertion runs on every host, unchanged. The on-disk loop runs where a `chmod(0o755)` probe leaves `S_IXUSR` set, the same capability probe `test_eval_tree_state.py` uses (`_host_carries_an_executable_bit`). On POSIX the loop runs exactly as now. No `skipif` on the test.

## Structural Decomposition

### Repository Structure

```
skills/use-qwen/scripts/
├── eval_harness/
│   └── trees.py                       # Maps to: clone link text
├── test_eval_tree_archive_safety.py   # Maps to: disk executable-bit check
└── test_eval_tree_links.py            # Maps to: clone link text (spy assertion)
```

### Module: trees
- **Maps to capability**: Clone links spelled for the host
- **Location**: `skills/use-qwen/scripts/eval_harness/trees.py`
- **Responsibility**: Clone links that resolve on every host.
- **Exports**: `fresh_clone()` - unchanged signature.

### Module: archive tests
- **Maps to capability**: both
- **Location**: the two test modules above
- **Responsibility**: Prove each repair; keep every POSIX assertion.
- **Exports**: none

## Dependency Graph

### Foundation Layer (Phase 0)
No dependencies - built first.

- **archive tests**: A spy regression for the clone link text.

### Core Layer (Phase 1)
- **trees**: Depends on [archive tests]
- **archive tests**: the guarded disk check; no dependency on trees.

## Implementation Phases

### Phase 0: Foundation
**Goal**: Pin the clone link text.

**Tasks**:
- [ ] Add a regression in `skills/use-qwen/scripts/test_eval_tree_links.py` that spies on `os.symlink` during `fresh_clone` of a template with a slash-holding chain link and asserts each target reaches it in host-separator form (no deps) - Acceptance: on macOS the test passes against the current code (`os.sep` is `/`); with `os.sep` monkeypatched to `\` inside `eval_harness.trees` only, it fails against the current code and passes after Phase 1.

**Exit Criteria**: The new test collects and shows the documented red/green behaviour.

### Phase 1: Core
**Goal**: Fix both causes.

**Tasks**:
- [ ] Convert clone link text to the host separator in `_copytree_links_typed` (depends on: Phase 0) - Acceptance: the Phase 0 regression passes, and every existing `fresh_clone` link, chain, cycle and escape test passes.
- [ ] Guard the on-disk executable-bit loop in `skills/use-qwen/scripts/test_eval_tree_archive_safety.py` with the host capability probe (no deps) - Acceptance: on macOS the loop still runs and asserts all four files; the sealed-mode assertion is unchanged.

**Exit Criteria**: `uv run pytest skills/use-qwen -W error::DeprecationWarning` passes on macOS. Native Windows proof comes from the hosted run after integration.

## Test Strategy

### Critical Scenarios
- **Happy path**: Template with `alias -> .` and `same -> alias/calc.py`, cloned → `same` reads `inside\n` on every host.
- **Edge case**: A dangling link with a `/` in its text → still dangling, text read back in slash form unchanged.
- **Error case**: An escaping chain → still refused before anything is copied.

## Risks

- **Native behavior is inferred**: ERROR_INVALID_NAME for a `/` in relative link text explains the log; only the hosted run proves the repair. Record the run result in the execution record.
- **Data-filter extraction**: `tarfile`'s own `extractall(filter="data")` writes link text as archived. No hosted test reads through such a link today; this PRD does not change that path.
