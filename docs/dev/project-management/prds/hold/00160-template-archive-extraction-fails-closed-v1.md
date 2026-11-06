---
catchup: run
design: run
default_model: opus
model_tier_rationale: security containment predicate on a destructive extraction path, with filter-parity equivalence across two Python code paths
---

# Seal templates only from archives that cannot write outside the template

Source: `docs/dev/project-management/audit-results/repository-closeout-preparation.md`
(Archive acceptance contract A1-A12) and its custody addendum
`repository-closeout-preparation-session-123534.md` (archive valid controls, Q4-Q5
refinement). Promotes held triage stubs 00155, 00156, 00157 and 00158, all raised
against done PRD 00131. Those four stubs stay in `hold/` until this PRD completes.

## Overview

### Problem Statement
`build_template` in `skills/use-qwen/scripts/eval_harness/trees.py` extracts a
`git archive` tar into the template directory. Four review findings remain open:

- 00158: a member beneath an archive symlink can bypass the containment walk.
  For `pkg/`, `alias -> pkg`, `alias/escape -> ../../outside` and
  `pkg/escape/secret.txt`, the link map records `alias/escape`, but `_land`
  looks up `pkg/escape` after it resolves `alias`, so the escaping target is
  missed.
- 00156: when `tarfile.data_filter` is absent, the code calls bare
  `archive.extractall(dest)`. setuid/setgid bits and ownership metadata from a
  crafted tar are then applied unfiltered.
- 00157: the same fallback raises the omitted-filter `DeprecationWarning` on
  Python 3.12/3.13. Under `-W error::DeprecationWarning`, valid archives fail
  (2 of 55 tests in `skills/use-qwen/scripts/test_eval_tree_links.py`).
- 00155: the refusal paths lack coverage that would break if a refusal were
  deleted.

Windows CI adds related symptoms (preparation rows Q4-Q6). Safe link chains fail
to read back after extraction. `hash_paths` does not refuse links that resolve
outside. With the filter present, tarfile's LinkOutsideDestinationError leaks
instead of `TreeError`. `/etc/passwd` is not reliably absolute under Windows
`os.path.isabs`.

### Target Users
Maintainers who run the qwen evaluation harness on crafted or untrusted task repositories.

### Success Metrics
- No accepted archive can create, modify, or chmod any path outside `dest`, on either filter path.
- Every acceptance row A1-A12 below has a named regression on both filter paths, and deleting the guarding code fails it.
- `uv run pytest skills/use-qwen/scripts/test_eval_tree_links.py skills/use-qwen/scripts/test_eval_tree_state.py -W error::DeprecationWarning` passes on Python 3.10, 3.12 and 3.13.
- Valid Git archives keep their exact bytes, executable bits and file/directory/dangling symlink semantics through seal and `fresh_clone`.

## Functional Decomposition

### Capability: Archive validation before any write
Decide from tar metadata alone whether an archive is acceptable, before extraction starts.

#### Feature: Member and link-target classification
- **Description**: Refuse every member whose name or link target can leave the template, in both the POSIX and the Windows path domains.
- **Inputs**: `tarfile.TarInfo` members from `git archive --format=tar`.
- **Outputs**: `None`, or a `TreeError` that names the member.
- **Behavior**: Refuse these names and link targets (A4): POSIX absolute; drive-absolute (`C:\x`, `C:/x`); drive-relative (`C:x`); rooted backslash (`\x`); UNC (`\\host\share`); extended prefixes (`\\?\`, `\\.\`); backslash and mixed separators; and NTFS stream-like `name:stream`. Judge with archive-domain rules, never only the host `os.path.isabs`. Refuse traversal: a `..` that climbs past the root, symlink-plus-`..` escapes, and self or cyclic chains. Accept an internal `..` whose real landing stays inside (A3). Refuse hardlinks, FIFOs, character and block devices, and every other non-file, non-dir, non-symlink type (A6).

#### Feature: Order-independent collision and ancestor rule
- **Description**: Refuse every archive where member order could decide what is written where.
- **Inputs**: The full member list.
- **Outputs**: `None`, or a `TreeError`.
- **Behavior**: Refuse any member whose path has an archive symlink as a proper ancestor, judged on normalized names (A1, A12). This is a deliberate narrowing: `git archive` of an ordinary repository never emits a member beneath a symlink, and the link itself stays supported. Refuse duplicate normalized names, file/dir swaps, and two content members with the same landing, in both member orders (A5). Refuse names that differ only in case, because extraction can merge them on case-insensitive hosts (A5).

### Capability: Safe extraction on both filter paths
Write an accepted archive identically whether or not `tarfile.data_filter` exists.

#### Feature: Filtered and manual extraction parity
- **Description**: Extract with `filter="data"` when a callable `tarfile.data_filter` exists. Otherwise extract member by member without any bare `extractall`.
- **Inputs**: A validated member list, the tar stream, and `dest`.
- **Outputs**: A tree with the members' bytes and links.
- **Behavior**: Detect filter availability at runtime with `callable(getattr(tarfile, "data_filter", None))`, never from the Python version (A8). The manual path writes regular files and directories and creates symlinks itself. It ignores uid/gid/uname/gname. It strips setuid, setgid, sticky and group/other write bits, and keeps owner read/write and the executable bit (A7). Both paths raise no `DeprecationWarning` (A10). Translate tarfile's FilterError and any `OSError` during extraction into `TreeError` with the cause chained (A10). Never pass `filter="fully_trusted"`.

#### Feature: Staged, atomic template exposure
- **Description**: An archive that fails anywhere leaves no template at `dest` and writes nothing outside.
- **Inputs**: `dest`, which may already exist with content or have link ancestors.
- **Outputs**: A sealed template at `dest`, or a `TreeError` with `dest` unchanged.
- **Behavior**: Extract into a fresh staging directory that this call creates beside `dest`. Seal it there. Rename it to `dest` only after the seal commit succeeds (A9). On any failure, remove only the staging directory this call created, never pre-existing `dest` data. When `dest` already exists and is non-empty, raise `TreeError` and do not extract (guess).

### Capability: Read containment after sealing
`hash_paths` and `fresh_clone` never read or copy bytes from outside the tree.

#### Feature: Contained hashing and cloning
- **Description**: Refuse a listed path whose real landing is outside `root` before any byte is read (A11). Keep correct hashes of in-tree files beside such a link.
- **Inputs**: A root and slash-form relpaths.
- **Outputs**: A digest map, or a `TreeError`.
- **Behavior**: Resolve with the same link walk used for archives, not only `Path.resolve`. A broken or mistyped link is never accepted as proof that a path is contained. Windows directory links in fixtures are created with `target_is_directory=True` when the target is a directory, and with the target's separators in native form. This is the Q4/Q5 hypothesis from the addendum: the native probe must compare raw and native-separator spellings.

## Structural Decomposition

### Repository Structure

```
skills/use-qwen/scripts/
├── eval_harness/
│   └── trees.py                      # Maps to: all capabilities
├── test_eval_tree_links.py           # Maps to: link, chain, hash containment regressions
├── test_eval_tree_state.py           # Maps to: refusal, atomicity, filter-parity regressions
└── test_eval_tree_archive_safety.py  # Maps to: A1-A12 matrix on both filter paths
```

### Module: trees
- **Maps to capability**: Archive validation before any write; Safe extraction on both filter paths; Read containment after sealing
- **Location**: `skills/use-qwen/scripts/eval_harness/trees.py`
- **Responsibility**: Validate, extract, seal and read templates without leaving the tree.
- **Exports**:
  - `build_template()` - unchanged signature; validates, stages, extracts, seals, renames.
  - `hash_paths()`, `fresh_clone()`, `contained()` - unchanged signatures, stricter containment.
  - `TreeError` - unchanged.
- New symbols: `_archive_name_escapes`, `_extract_without_filter`, `_safe_mode`

### Module: archive safety tests
- **Maps to capability**: all
- **Location**: `skills/use-qwen/scripts/test_eval_tree_archive_safety.py`, `skills/use-qwen/scripts/test_eval_tree_links.py`, `skills/use-qwen/scripts/test_eval_tree_state.py`
- **Responsibility**: Prove each acceptance row on both filter paths with crafted tar bytes in disposable directories, each with an outside sentinel.
- **Exports**: none
- New symbols: `test_eval_tree_archive_safety.py`

## Dependency Graph

### Foundation Layer (Phase 0)
No dependencies - built first.

- **archive safety tests**: The failing A1-A12 matrix plus a faithful no-filter seam. The seam removes `tarfile.data_filter` and replaces `TarFile.extractall` with one that rejects the `filter` keyword, so the seam cannot accept newer extraction keywords.

### Core Layer (Phase 1)
- **trees**: Depends on [archive safety tests]

### Integration Layer (Phase 2)
- **trees**: Depends on [trees core]; read containment and Windows fixture link typing.

## Implementation Phases

### Phase 0: Foundation
**Goal**: Reproduce every open finding as a failing test.

**Tasks**:
- [ ] Add `skills/use-qwen/scripts/test_eval_tree_archive_safety.py` with A1-A7 and A12 cases, each parametrized over filter-present and filter-absent seams, each with an outside sentinel whose bytes and mode it asserts unchanged (no deps) - Acceptance: `uv run pytest skills/use-qwen/scripts/test_eval_tree_archive_safety.py` fails on A1 (ancestor escape, both member orders) and A7 (setuid kept on the no-filter path) against the current `trees.py`.
- [ ] Add valid-input controls to the same file: binary and CRLF blobs, an executable file, file/directory/dangling safe links, root and subdirectory chains, deterministic seal sha across two runs (no deps) - Acceptance: controls pass on the filter-present seam against the current code.

**Exit Criteria**: The new module collects. Its security cases fail for the documented reasons.

### Phase 1: Core
**Goal**: Fail closed before any write, on both filter paths.

**Tasks**:
- [ ] Implement archive-domain name/target classification, the ancestor rule, collision and case rules, and type refusal in `skills/use-qwen/scripts/eval_harness/trees.py` (depends on: Phase 0) - Acceptance: A1-A6 and A12 cases in `skills/use-qwen/scripts/test_eval_tree_archive_safety.py` pass on both seams.
- [ ] Replace the bare `extractall` fallback with `_extract_without_filter` and `_safe_mode`, and translate filter and OS errors to `TreeError` (depends on: Phase 0) - Acceptance: A7, A8 and A10 cases pass. `uv run pytest skills/use-qwen/scripts/test_eval_tree_links.py skills/use-qwen/scripts/test_eval_tree_state.py -W error::DeprecationWarning` passes.
- [ ] Stage extraction and seal, then rename into `dest`; clean only owned staging on failure (depends on: Phase 0) - Acceptance: A9 cases with injected extraction and seal failures pass. Pre-existing `dest` sibling content survives.

**Exit Criteria**: All A1-A10 and A12 cases pass on both seams.

### Phase 2: Integration
**Goal**: Read containment and Windows-faithful fixtures.

**Tasks**:
- [ ] Make `hash_paths` and `fresh_clone` refuse outside landings using the link walk, and type directory links in `_lay_links` in `skills/use-qwen/scripts/test_eval_tree_links.py` (depends on: Phase 1) - Acceptance: A11 cases pass. A test asserts that the fixture link actually reaches its sentinel before it asserts refusal.
- [ ] Assert `TreeError` (never tarfile's LinkOutsideDestinationError) for the absolute-target case in `skills/use-qwen/scripts/test_eval_tree_state.py`, with POSIX-rooted, Windows-rooted, drive and UNC targets (depends on: Phase 1) - Acceptance: that parametrized test passes on both seams.

**Exit Criteria**: `uv run pytest skills/use-qwen -W error::DeprecationWarning` passes. Focused archive tests pass under `uv run --python 3.10`, `--python 3.12` and `--python 3.13`.

## Test Strategy

### Critical Scenarios
- **Happy path**: An ordinary `git archive` with nested files, an executable, and file and directory symlinks → the template has the same bytes, links and executable bits on both seams.
- **Edge case**: An internal `sub/../pkg/file` link whose landing stays inside → accepted.
- **Error case**: `alias -> pkg` plus `alias/escape -> ../../outside` plus `pkg/escape/secret.txt`, in either order → `TreeError` before extraction; outside sentinel unchanged; no template at `dest`.
- **Error case**: A setuid regular file on the no-filter seam → extracted mode has no setuid bit; os.chown is never called (spied).

## Risks

- **Windows link typing differs from POSIX**: Native results come only from the hosted Windows job; local tests simulate the path domain. Record unverified hypotheses as such.
- **The ancestor rule rejects a valid hand-built archive**: It is documented as a deliberate subset, and `git archive` never emits such members.
