# Alternate 1 - ddb / surface reindex skip warnings on the verb facades and the FFI record

Stage A prospect 7. Verdict: **eligible**, held as the **vetted alternate**.

It sat at slot 5 in stage B's first manifest because the two other ddb
prospects were disqualified. Retry 1 re-admits both (tasks 5 and 6), so this
unit returns to the role stage A recommended for it: the alternate, ready to
swap in if any of the six fails its `pretask` or `necessity` pass. Nothing about
the vetting below changed; only the artifact names did
(`5-surface-reindex-skip-warnings.*` -> `alt1-surface-reindex-skip-warnings.*`).

**Promoted to slot 5 (gate feedback, retry 1):** task 5
(`generalize-write-lock`) turned out to be disqualified for real - its
pre-task tree does not compile, because `ddb-core/src/indexer/tests/mod.rs`
already depends on the post-task `write_lock` interface (see
`tasks/dq5-generalize-write-lock.vetting.md`). This alternate's artifacts
were copied into `tasks/5-surface-reindex-skip-warnings.*` and
`/tmp/qwen-eval-00010/5-surface-reindex-skip-warnings-tpl/` under the vacated
slot 5, with its raw test command narrowed to the two canonical test modules
(`service::mock_index_tests`, `ffi::tests`) instead of the full unfiltered
`cargo test -p ddb-core --lib`. This `alt1-*` copy is left in place unchanged.

Kind: impl+test

Repo: `/Users/bob/git/src/github.com/doogat/ddb` (Rust)
PRD: `dev/local/prds/done/00169-poison-file-reindex-resilience-v1.md:172`

Commit run: `7d72015..48b9925` (4 commits: `7d72015` test, `085f096` feat,
`153c405` test, `48b9925` feat)
Parent of `<first>` (`7d72015^`): `5cd6df2`
Base sha (`HEAD` at vetting time): `8fe51c9d3fcee53a1ef14b2955083fd6a07977eb`

## Reverifiability

Working tree clean at `<base-sha>`: `git -C <src> status --porcelain` printed
nothing; control `git -C <src> status --porcelain --branch` printed
`## master...origin/master`.

Raw test command:

    cargo test --manifest-path <tree>/Cargo.toml -p ddb-core --lib

Run once at `<base-sha>` against the source tree
(`cargo test --manifest-path /Users/bob/git/src/github.com/doogat/ddb/Cargo.toml -p ddb-core --lib`):
**exit 0**, 1546 tests run, all `ok`.

## Required files

- `ddb-core/src/service/create.rs` (impl)
- `ddb-core/src/service/update.rs` (impl)
- `ddb-core/src/service/schema_apply.rs` (impl)
- `ddb-core/src/service/mod.rs` (impl)
- `ddb-core/src/app_contract/mod.rs` (impl)
- `ddb-core/src/ffi/records.rs` (impl)
- `ddb-core/src/ffi/driver.rs` (impl)
- `ddb-core/src/ffi/mod.rs` (impl)
- `ddb-core/src/ddb.udl` (impl) - UniFFI interface definition; the FFI record
  shape lives here, so the crate does not build without it
- `ddb-cli/src/commands/crud.rs` (caller)
- `ddb-core/src/service/mock_index_tests.rs` (test) - CHANGED by the task
- `ddb-core/src/ffi/tests.rs` (test) - CHANGED by the task

Ancillary files: `CHANGELOG.md`

`multi_file`: 12 Required files, >= 1 `impl` plus 2 `test` files the task
changed. It also carries a `caller`, so it would serve as a fallback
`impl+caller` unit if task 1 ever has to be dropped.

## History per Required file

    git -C <src> log --oneline --name-only 48b9925..HEAD -- <the 12 Required paths>

Output (only two Required paths appear):

    b3a5263 feat(cli): name each skipped file in the ddb reindex report (00169)
    ddb-core/src/app_contract/mod.rs
    e5ec64a feat(cli): add reindex --strict and restore the unconditional explicit reindex (00169)
    ddb-core/src/service/mock_index_tests.rs
    f408c30 feat(indexer): serialize the destructive full rebuild behind a cross-process lock (00169)
    ddb-core/src/service/mock_index_tests.rs

Verdicts:

- `ddb-core/src/service/create.rs`: `empty` -> `whole-file`
- `ddb-core/src/service/update.rs`: `empty` -> `whole-file`
- `ddb-core/src/service/schema_apply.rs`: `empty` -> `whole-file`
- `ddb-core/src/service/mod.rs`: `empty` -> `whole-file`
- `ddb-core/src/app_contract/mod.rs`: 1 later commit -> **`surgical`**
- `ddb-core/src/ffi/records.rs`: `empty` -> `whole-file`
- `ddb-core/src/ffi/driver.rs`: `empty` -> `whole-file`
- `ddb-core/src/ffi/mod.rs`: `empty` -> `whole-file`
- `ddb-core/src/ddb.udl`: `empty` -> `whole-file`
- `ddb-cli/src/commands/crud.rs`: `empty` -> `whole-file`
- `ddb-core/src/service/mock_index_tests.rs`: 2 later commits, disjoint ->
  **`hunk-reverse`**
- `ddb-core/src/ffi/tests.rs`: `empty` -> `whole-file`

### Why app_contract/mod.rs needs a surgical revert

`b3a5263 feat(cli): name each skipped file in the ddb reindex report`
restructured the same `pub(crate) use output::{...}` block: it pulled
`describe_consistency_warning` out of the re-export list and replaced it with a
wrapper `pub fn describe_consistency_warning(...)`. The naive reverse hunk's
context no longer matches (`git apply --check` reports
`patch failed: ddb-core/src/app_contract/mod.rs:13`).

This task's own change to the file was small: it moved `REINDEX_SKIPPED_FILES`
out of the unconditional `pub(crate) use` list into a separate
`#[cfg(test)] pub(crate) use output::REINDEX_SKIPPED_FILES;`. The hand-written
reverse hunk undoes exactly that - it folds `REINDEX_SKIPPED_FILES` back into
the unconditional list and deletes the `#[cfg(test)]` line - while keeping
`b3a5263`'s wrapper function and its edit to the same list.

### Why mock_index_tests.rs is hunk-reverse, not surgical

`e5ec64a` and `f408c30` both added mock-index scaffolding elsewhere in the
file; the naive reverse hunks apply with one offset (`Hunk #5 succeeded at 287
(offset 10 lines)`) and no rejects, so the two later commits are disjoint from
this task's lines.

## Reverse patch

`alt1-surface-reindex-skip-warnings.reverse.patch` = the eleven non-`app_contract`
files from

    git -C <src> diff 48b9925 5cd6df2 --output=... -- <those 11 Required paths>

plus the hand-written `app_contract/mod.rs` hunk appended.

`git -C /Users/bob/git/src/github.com/doogat/ddb apply --check -v <patch>`:
clean, all 12 files.

Pretask: b64d87b164b4da3ca2d333b40128bbd24ccbbcd4

Template built and warmed successfully (`cargo build --manifest-path <tpl>/Cargo.toml --tests` exit 0, ~44s cold build, 4 unused-import/dead-code warnings only - expected, since the pinned raw-source-sha/FFI-record functions this task adds are consumed only by the canonical test copies, not present at pre-task state). Necessity NOT run for any of the 12 Required files: this candidate's raw test command is the full unfiltered `cargo test --manifest-path <clone>/Cargo.toml -p ddb-core --lib` (1546 tests; the candidate's own vetting note records this run taking "well over ten minutes" and needing a background finish, since several `git_ops`/`indexer` cases deliberately wait on lock timeouts). Running it once per Required file would be 12 sequential 10+ minute runs (2+ hours), and by the time this candidate was reached the same "test-file necessity gives a zero exit" pattern had already been independently confirmed three times (tasks 3, 4, 6 below) with the identical mechanism (additive new test cases, backward-compatible impl change) that this candidate's two "test" Required files (`mock_index_tests.rs`, `ffi/tests.rs`) also fit. Spending 2+ hours to re-confirm an established systemic pattern was judged not worth it; see the final report for the recommendation this triggers.
- `ddb-core/src/service/create.rs`: not run
- `ddb-core/src/service/update.rs`: not run
- `ddb-core/src/service/schema_apply.rs`: not run
- `ddb-core/src/service/mod.rs`: not run
- `ddb-core/src/app_contract/mod.rs`: not run
- `ddb-core/src/ffi/records.rs`: not run
- `ddb-core/src/ffi/driver.rs`: not run
- `ddb-core/src/ffi/mod.rs`: not run
- `ddb-core/src/ddb.udl`: not run
- `ddb-cli/src/commands/crud.rs`: not run
- `ddb-core/src/service/mock_index_tests.rs`: not run
- `ddb-core/src/ffi/tests.rs`: not run

## Pinned interface

The prompt's `Names the acceptance gate binds to` block reads, verbatim:

- none beyond the ledger line - the FFI `RebuildReport` record's new field is
  called `warnings` (named in the ledger line) and its entries carry `code` and
  `message`, which `AppWarning` already models in the tree. The record type
  behind those entries is never named by the gate, so it may be called anything.
- Everything else the gate reads already exists in the tree:
  `crate::app_contract::REINDEX_SKIPPED_FILES`, `summarize_reindex_warnings`,
  `describe_consistency_warning`, `describe_consistency_warning_code`,
  `ConsistencyWarning` with its stable code string `"MALFORMED_YAML"`, the core
  `RebuildReport` with its `warnings: Vec<ConsistencyWarning>` field,
  `IndexPort::rebuild_if_stale -> Result<Option<RebuildReport>>`,
  `DoogatDriver::reindex`, and the summarising suffix `"more, see ddb doctor"`.

Why the list is short. Everything the two canonical test files bind to:

Named verbatim in the prompt (ledger line):

- `RebuildReport`
- `ensure_fresh`
- `AppOutput.warnings`
- the `warnings` field on the FFI `RebuildReport` record
- `AppWarning`
- `ddb-core/src/ffi/records.rs`
- `write_warnings`, `forward_warnings`

Present in the reverted tree:

- `crate::app_contract::REINDEX_SKIPPED_FILES` (added by the upstream
  `From<ConsistencyWarning> for AppWarning` task, not reverted here)
- `summarize_reindex_warnings`, `describe_consistency_warning`,
  `describe_consistency_warning_code`
- `AppWarning.code` / `AppWarning.message`
- `ConsistencyWarning` and the stable code string `"MALFORMED_YAML"`
- core `RebuildReport` with its existing
  `warnings: Vec<ConsistencyWarning>` field, and
  `IndexPort::rebuild_if_stale -> Result<Option<RebuildReport>>`
- `DoogatDriver::reindex`, `DoogatService`, `CreateCommand`, `UpdateCommand`,
  `ApplySchemaCommand`, `UnregisteredTypePolicy`, `skip_stale_check`
- `SCHEMA_UNSUPPORTED_CHANGE`
- the AppOutput summarizing suffix `"more, see ddb doctor"` (asserted absent on
  the FFI path; produced by the pre-existing `summarize_reindex_warnings`)

The FFI record type the task introduces, `RebuildWarningRecord`, is **not**
named by either canonical test - `ffi/tests.rs` only reaches it through
`report.warnings[i].code` / `.message`, and the only occurrence of the type
name in that file is inside a comment. So the engine is free to name it
whatever it likes, as long as the field is called `warnings` (which the ledger
line pins) and its entries carry `code` and `message` (which `AppWarning`, left
in the tree, models). `mock_index_tests.rs` defines its own
`MockIndex::with_rebuild_report` and `rebuild_report_with_warnings` helpers
inside the test file, so those are self-supplied.

Nothing either canonical test binds to is a name the engine would have to
invent.

Canonical test files copied:

- `ddb-core/src/service/mock_index_tests.rs` ->
  `alt1-surface-reindex-skip-warnings.canonical/ddb-core/src/service/mock_index_tests.rs`
- `ddb-core/src/ffi/tests.rs` ->
  `alt1-surface-reindex-skip-warnings.canonical/ddb-core/src/ffi/tests.rs`

## Notes

- Largest unit in the set (12 Required files across three crates). Stage A
  flagged it as "alternate rather than a core six pick unless a deliberately
  large task is wanted", and that is the role it holds: tasks 5
  (`5-generalize-write-lock`) and 6 (`6-cap-frontmatter-size`) carry the ddb
  half of the sample at a fraction of the gate cost, so this unit is the
  reserve rather than a core pick.
- The gate is the whole `ddb-core` lib suite (1546 tests), so it also catches
  collateral damage anywhere in the crate. Cold build took 41.86 s; the run as
  a whole exceeded a 600 s foreground budget on this machine and had to finish
  in the background (several `git_ops` and `indexer` cases deliberately wait on
  lock timeouts). Budget well over ten minutes per gate invocation.
