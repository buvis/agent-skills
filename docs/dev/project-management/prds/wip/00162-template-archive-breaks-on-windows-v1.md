---
catchup: run
design: run
default_model: opus
model_tier_rationale: extraction, sealing and clone paths on a security-containment module, with native Windows semantics verifiable only on the hosted runner
---

# Seal and clone templates correctly on native Windows

Source: `docs/dev/project-management/audit-results/repository-closeout-execution.md`,
entry "Stage 1 — lanes built", section "Native run 41353724204". Builds on PRD
00160, which is built and waits for review on `closeout/archive`. This PRD
repairs the 72 Windows failures that run assigned to 00160's code and tests.
It does not change any 00160 acceptance row.

## Overview

### Problem Statement
The hosted Windows job (CPython 3.13.16, Windows Server 2025) failed 72 tests
in the 00160 archive modules. Linux and macOS pass. Five causes:

1. **Owner checks call POSIX-only functions (40 tests).** In
   `skills/use-qwen/scripts/test_eval_tree_archive_safety_modes.py` the helper
   at line 87 asserts `st_uid == os.getuid()`, and the root case at line 127
   patches `os.geteuid`. Neither function exists on Windows.
2. **Mode checks read `st_mode` (10 tests).** Lines 191-192 of the same file
   compare `stat.S_IMODE(st_mode)`. Windows reports `0o100666` or `0o100444`
   for every file, so the safe-mode contract cannot be read from disk there.
3. **The seal drops the executable bit (2 tests).**
   `test_control_build_template_keeps_the_executable_bit_and_only_where_it_was_set`
   in `skills/use-qwen/scripts/test_eval_tree_archive_safety.py` sees
   `bin/run` sealed as `100644`. `build_template` in
   `skills/use-qwen/scripts/eval_harness/trees.py` runs `git add -A`, and Git
   for Windows has `core.filemode=false`, so it records no executable bit.
4. **Links break on the manual path and in clones (9 tests).**
   `_extract_without_filter` calls `os.symlink(member.linkname, path)` in
   archive order with the archive's `/` text. `fresh_clone` uses
   `shutil.copytree(template, dest, symlinks=True)`. On Windows a symlink's
   file or directory type is fixed at creation. CPython types it as a
   directory only if the target already exists as one at that moment. A link
   that precedes its target (`pkg-link` sorts before `pkg/`) gets the file
   type, and a read through it fails with `OSError: [Errno 22]`. The
   `with-data-filter` path passes the same cases. This is preparation row Q4.
5. **Staging survives a failure (7 tests).** `build_template` cleans up with
   `shutil.rmtree(staging, ignore_errors=True)`. Git writes its object files
   read-only, Windows refuses to delete a read-only file, and the error is
   ignored. `test_eval_tree_archive_staging.py` finds `template.staging-*`
   beside `dest`.
6. **Absolute link text reads back with an extended prefix (4 tests).** The
   fixture assertions `os.readlink(root / "escape") == target` at
   `skills/use-qwen/scripts/test_eval_tree_links.py:663` and
   `skills/use-qwen/scripts/test_eval_tree_state.py:577` get `\\?\C:\...` and
   `\\?\UNC\host\share\x`. Production refusal is not in question: the test
   fails before it calls `hash_paths` or `contained`.

The execution record counts row 4 as 11. The failure list shows 9 nodes:
four `without-data-filter` controls in `test_eval_tree_archive_safety.py`,
one seal test and four `fresh_clone` chains in `test_eval_tree_links.py`.

### Target Users
Maintainers who run the qwen evaluation harness on Windows, and the Windows CI job.

### Success Metrics
- The hosted Windows job passes every test in the five 00160 archive modules, with no new skip and no xfail.
- Every existing POSIX assertion still runs and passes on Linux and macOS, unchanged in strength.
- A sealed template records `100755` for exactly the archive members whose mode has the owner executable bit, on every host.
- After any refused or failed `build_template`, nothing named `<dest>.staging-*` remains, on every host.

## Functional Decomposition

### Capability: Host-neutral archive assertions
Assert the 00160 owner and mode contract in a form each host can observe.

#### Feature: Owner and mode checks per host
- **Description**: Keep the POSIX owner and `st_mode` assertions on POSIX. On Windows, assert the same contract through what Windows can show.
- **Inputs**: The extracted staging tree and the sealed Git tree.
- **Outputs**: Test assertions.
- **Behavior**: On POSIX keep `st_uid == os.getuid()` and the exact `S_IMODE` comparison. On every host also assert the sealed Git tree mode (`git ls-tree`) for each member: `100755` where the archive mode has the owner executable bit, else `100644`. On every host keep the chown spy: no `os.chown` call with a foreign uid or gid. The root case patches `os.geteuid` only where it exists; on Windows the case still runs and still asserts the spy and the sealed modes. Use no `skipif` on a whole test.

### Capability: Executable bit survives the seal
The sealed commit records the archive's executable bits on every host.

#### Feature: Index modes from the archive
- **Description**: Set each regular file's index mode from its archive mode before the seal commit.
- **Inputs**: The validated member list and the staging repository.
- **Outputs**: A sealed commit whose tree modes match the archive.
- **Behavior**: After `git add -A`, run `git update-index --chmod=+x` for each regular member whose mode has `S_IXUSR`, and `--chmod=-x` for each that does not, in one call per group, with `--` before the paths. Read the bit from the archive member, never from disk. The deterministic seal sha (00160 control) is unchanged on POSIX.

### Capability: Links typed and spelled for the host
Every symlink the harness writes resolves on Windows as it does on POSIX.

#### Feature: Two-pass link creation
- **Description**: Create links only after all files and directories exist, typed by their real target, with native separators.
- **Inputs**: The member list (`_extract_without_filter`) or the template tree (`fresh_clone`).
- **Outputs**: Links that read back to the archive text in slash form and that resolve on Windows.
- **Behavior**: Write regular files and directories first. Then create each symlink with the target text converted to the host separator (`os.sep`) and `target_is_directory=True` when its landing inside the tree is a directory. Create chained links in an order where each link's target exists first. A dangling link stays dangling and file-typed. `fresh_clone` copies files and directories first and lays the links in the same second pass. It still refuses an escaping link before it copies anything. Link text read back with `Path(os.readlink(p)).as_posix()` equals the archive text.

### Capability: Owned staging always goes away
A failed or refused build removes the staging directory it created.

#### Feature: Read-only-aware cleanup
- **Description**: Remove read-only files during staging cleanup.
- **Inputs**: The staging path this call created.
- **Outputs**: No staging directory.
- **Behavior**: Replace `shutil.rmtree(staging, ignore_errors=True)` with a removal whose error handler clears the read-only attribute (`os.chmod(path, stat.S_IWRITE)`) and retries once. Use `onexc` where Python provides it and `onerror` on 3.10 and 3.11, so no `DeprecationWarning` fires under `-W error`. If removal still fails, keep the original exception as the raised error; do not mask it. Remove only the staging path this call created.

### Capability: Fixture link text compared as written
#### Feature: Extended-prefix normalization in tests
- **Description**: Compare the fixture's absolute link text after removing the Windows extended prefix.
- **Inputs**: `os.readlink` output.
- **Outputs**: The text the fixture wrote.
- **Behavior**: A test helper maps `\\?\UNC\` to `\\` and strips a leading `\\?\`. Both fixture assertions use it. The assertion still fails if the link text differs in any other way. Production refusal assertions stay as they are.

## Structural Decomposition

### Repository Structure

```
skills/use-qwen/scripts/
├── eval_harness/
│   └── trees.py                             # Maps to: seal modes, two-pass links, staging cleanup
├── test_eval_tree_archive_safety.py         # Maps to: executable bit, manual-path link controls
├── test_eval_tree_archive_safety_modes.py   # Maps to: host-neutral owner and mode checks
├── test_eval_tree_archive_staging.py        # Maps to: staging cleanup
├── test_eval_tree_links.py                  # Maps to: clone links, extended prefix
└── test_eval_tree_state.py                  # Maps to: extended prefix
```

### Module: trees
- **Maps to capability**: Executable bit survives the seal; Links typed and spelled for the host; Owned staging always goes away
- **Location**: `skills/use-qwen/scripts/eval_harness/trees.py`
- **Responsibility**: Seal, clone and clean up identically on POSIX and Windows.
- **Exports**: `build_template()`, `fresh_clone()` - unchanged signatures.
- New symbols: `_lay_links_typed`, `_remove_staging`

### Module: archive tests
- **Maps to capability**: all
- **Location**: the five test modules above
- **Responsibility**: Prove each repair on every host, and simulate the Windows link and read-only behavior on POSIX.
- **Exports**: none

## Dependency Graph

### Foundation Layer (Phase 0)
No dependencies - built first.

- **archive tests**: Regressions that fail on POSIX for the old code: a spy on `os.symlink` that records `target_is_directory` and the target text; a seal test that forces `core.filemode=false` for the staging repository (through Git's environment config) and expects `100755`; a staging test that marks a staging file read-only and makes `os.unlink` refuse read-only files.

### Core Layer (Phase 1)
- **trees**: Depends on [archive tests]

### Integration Layer (Phase 2)
- **archive tests**: Depends on [trees]; host-neutral owner and mode assertions and the extended-prefix helper.

## Implementation Phases

### Phase 0: Foundation
**Goal**: Reproduce each product cause on POSIX.

**Tasks**:
- [ ] Add regressions for causes 3, 4 and 5 in `skills/use-qwen/scripts/test_eval_tree_archive_safety.py`, `skills/use-qwen/scripts/test_eval_tree_links.py` and `skills/use-qwen/scripts/test_eval_tree_archive_staging.py` (no deps) - Acceptance: each new test fails against the current `trees.py` on macOS for the documented reason: link created before its directory target or without `target_is_directory`; executable bit lost under `core.filemode=false`; staging left when read-only files refuse deletion.

**Exit Criteria**: The new tests collect and fail for the documented reasons.

### Phase 1: Core
**Goal**: Fix the three product causes.

**Tasks**:
- [ ] Set index modes from archive members before the seal commit in `skills/use-qwen/scripts/eval_harness/trees.py` (depends on: Phase 0) - Acceptance: the executable-bit regression and the existing deterministic-seal control pass on Python 3.10, 3.12 and 3.13.
- [ ] Create links in a second, typed, native-separator pass in `_extract_without_filter` and `fresh_clone` (depends on: Phase 0) - Acceptance: the link spy regressions pass, and every existing link, chain and escape test in the five modules passes on both filter seams.
- [ ] Replace the staging cleanup with a read-only-aware removal (depends on: Phase 0) - Acceptance: the staging regression passes, and `uv run pytest skills/use-qwen/scripts/test_eval_tree_archive_staging.py -W error::DeprecationWarning` passes on Python 3.10 and 3.13.

**Exit Criteria**: All Phase 0 regressions pass. No existing test changed its assertions.

### Phase 2: Integration
**Goal**: Host-neutral test assertions.

**Tasks**:
- [ ] Make the owner and mode checks in `skills/use-qwen/scripts/test_eval_tree_archive_safety_modes.py` host-neutral, keeping the POSIX `st_uid` and `S_IMODE` assertions on POSIX (depends on: Phase 1) - Acceptance: the module passes on macOS with the same assertion count per case as before, plus the sealed-mode assertion; `os.getuid` and `os.geteuid` are reached only where they exist.
- [ ] Add the extended-prefix helper and use it at `skills/use-qwen/scripts/test_eval_tree_links.py:663` and `skills/use-qwen/scripts/test_eval_tree_state.py:577` (depends on: Phase 1) - Acceptance: a unit test of the helper covers `\\?\C:\x`, `\\?\UNC\h\s\x`, `C:\x` and a POSIX path.

**Exit Criteria**: `uv run pytest skills/use-qwen -W error::DeprecationWarning` passes on macOS. The five archive modules pass under `uv run --python 3.10`, `--python 3.12` and `--python 3.13`. Native Windows proof comes from the hosted run after integration.

## Test Strategy

### Critical Scenarios
- **Happy path**: Archive with `pkg-link -> pkg`, `nested -> pkg-link/nested.txt` and an executable `bin/run`, built without the data filter → links read back as written, `nested` reads `nested\n`, `bin/run` is sealed `100755`.
- **Edge case**: A dangling link → created file-typed, still dangling, text unchanged.
- **Error case**: Seal commit fails while staging holds read-only Git objects → the injected error is raised, no `template.staging-*` remains, siblings unchanged.

## Risks

- **Native behavior is inferred**: CPython's directory check at link creation and Git's `core.filemode=false` explain the logs, but only the hosted Windows run proves the repair. Record the run result in the execution record.
- **Separator conversion changes link text on disk**: On Windows the stored text uses `\`. The manifest records link text, so a template and its clone must both be written by this code; the slash-form read-back keeps assertions portable.
