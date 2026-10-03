# Alternate 1 - ddb / surface reindex skip warnings on the verb facades and the FFI record

Stage A prospect 7. Verdict: **eligible**, held as the **vetted alternate**.

It sat at slot 5 in stage B's first manifest because the two other ddb
prospects were disqualified. Retry 1 re-admits both (tasks 5 and 6), so this
unit returns to the role stage A recommended for it: the alternate, ready to
swap in if any of the six fails its `pretask` or `necessity` pass. Nothing about
the vetting below changed; only the artifact names did
(`5-surface-reindex-skip-warnings.*` -> `alt1-surface-reindex-skip-warnings.*`).

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

Raw test command (narrowed, gate feedback retry 1, promoted to slot 5):

    cargo test -p ddb-core --lib -- service::mock_index_tests ffi::tests

The full unfiltered `cargo test --manifest-path <tree>/Cargo.toml -p ddb-core
--lib` (the alternate's original raw test command, still exit 0 at
`<base-sha>` with 1546 tests run, all `ok`) was replaced by the two positional
filters above - libtest ORs multiple positional filters, so this selects
exactly the two canonical test modules this task's diff touches
(`service::mock_index_tests`, `ffi::tests`) instead of the whole crate.

Verified once against the canonical source tree
(`cargo test --manifest-path /Users/bob/git/src/github.com/doogat/ddb/Cargo.toml -p ddb-core --lib -- service::mock_index_tests ffi::tests`):
**exit 0**, `44 passed; 0 failed; 0 ignored; 0 measured; 1502 filtered out`
(10 `service::mock_index_tests::*` cases, 34 `ffi::tests::*` cases - both
modules ran).

## Required files

- `ddb-core/src/service/create.rs` (impl)
- `ddb-core/src/service/update.rs` (impl)
- `ddb-core/src/service/schema_apply.rs` (impl)
- `ddb-core/src/service/mod.rs` (impl)
- `ddb-core/src/ffi/records.rs` (impl)
- `ddb-core/src/ffi/driver.rs` (impl)
- `ddb-core/src/ffi/mod.rs` (impl)
- `ddb-core/src/ddb.udl` (impl) - UniFFI interface definition; the FFI record
  shape lives here. Correction (necessity re-run, retry 1): `ddb-core` has no
  `build.rs`, so this claim about build-breakage is wrong - `cargo build`/
  `cargo test` never reads this file at all; see the necessity result below
- `ddb-cli/src/commands/crud.rs` (caller)
- `ddb-core/src/service/mock_index_tests.rs` (test) - CHANGED by the task
- `ddb-core/src/ffi/tests.rs` (test) - CHANGED by the task

Ancillary files: `CHANGELOG.md`, `ddb-core/src/app_contract/mod.rs` (R2: the
task's whole diff to this file moves `REINDEX_SKIPPED_FILES` from an
unconditional `pub(crate) use` into a `#[cfg(test)] pub(crate) use` - a
visibility-only metadata edit no `cargo test` invocation can observe, since
`cfg(test)` is active either way. `git -C <src> grep -n REINDEX_SKIPPED_FILES
5cd6df2 -- ddb-core/src ddb-cli/src` confirms the constant has no non-test
consumer outside `app_contract/output.rs` itself at the pre-task commit, so
keeping the file at today's state compiles in both test and non-test builds.
Necessity for this file exited 0, 44 passed, per R2 that does not disqualify
the task - it disqualifies the file from Required status instead.)

`multi_file`: 11 Required files, >= 1 `impl` plus 2 `test` files the task
changed. It also carries a `caller`, so it would serve as a fallback
`impl+caller` unit if task 1 ever has to be dropped.

### `ffi/mod.rs` considered for R2 and rejected

`ffi/mod.rs`'s whole task diff also adds one symbol, `RebuildWarningRecord`,
to the `pub use records::{...}` re-export list - superficially R2's own named
example ("a re-export reshuffle"), and its necessity run (below) also exits 0.
It was reclassified as Ancillary and excluded from the reverse patch, then
un-reclassified after the rebuilt template failed `cargo build --tests` with
`error[E0432]: unresolved import 'records::RebuildWarningRecord'`. Unlike
`app_contract/mod.rs` (whose dependency, `output.rs`'s `REINDEX_SKIPPED_FILES`
constant, lives in a file that is never reverted), `ffi/mod.rs`'s canonical
form re-exports a struct defined in `ffi/records.rs` - a sibling Required
file that stays reverted at pre-task in the sealed template. Kept at "today's
state" while `records.rs` is reverted, the re-export points at nothing.
R2 requires a file's canonical content to compile independently of its
Required siblings' revert state; `ffi/mod.rs` fails that precondition, so it
stays Required and reverted alongside `records.rs`, and its necessity zero
exit is treated under the plain (pre-R2) rule below.

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

`5-surface-reindex-skip-warnings.reverse.patch` (retry 1, R2 reclassification)
= the eleven Required files excluding `app_contract/mod.rs`, regenerated
directly rather than composed with a hand-written hunk:

    git -C <src> diff 48b9925 5cd6df2 --output=... -- <those 11 Required paths>

`app_contract/mod.rs` is no longer in the patch at all - it is Ancillary now
and stays at today's (archived) state, never reverted. The previous
hand-written `app_contract/mod.rs` hunk (see "Why app_contract/mod.rs needs a
surgical revert" above) is obsolete history, kept for context only.

`git -C /Users/bob/git/src/github.com/doogat/ddb apply --check <patch>`:
clean, all 11 files (`mock_index_tests.rs` applies with an offset, no
rejects, as before).

Pretask: 84012329912e3ca78cfd037505e6e982a84948da (retry 1, R2 rebuild: template
excludes `app_contract/mod.rs` from the reverse patch, keeping it at today's
archived state)

Template built and warmed successfully (`cargo build --manifest-path <tpl>/Cargo.toml --tests` exit 0, ~46s cold build; `cargo check --manifest-path <tpl>/Cargo.toml -p ddb-core` also exit 0, ~13s. Both show the same 4 unused-import/dead-code warnings only, no `REINDEX_SKIPPED_FILES` visibility errors - expected, since the pinned raw-source-sha/FFI-record functions this task adds are consumed only by the canonical test copies, not present at pre-task state).

**Necessity re-run (gate feedback, retry 1, after promotion to slot 5), narrowed command, clone rule (`cp -Rpc <tpl> <tpl>-necessity-<i>`, `git apply -R --exclude=<f> reverse.patch`, `timeout -k 30 900 cargo test --manifest-path <clone>/Cargo.toml -p ddb-core --lib -- service::mock_index_tests ffi::tests`), one clone at a time:**

- `ddb-core/src/service/create.rs`: exit 101, first failure: `assertion \`left == right\` failed: create must summarize a multi-file skip into exactly one REINDEX_SKIPPED_FILES warning, got: []` (`service::mock_index_tests::create_facade_includes_exactly_one_reindex_warning_when_files_are_skipped`, mock_index_tests.rs:395) - necessity holds.
- `ddb-core/src/service/update.rs`: exit 101, first failure: `assertion \`left == right\` failed: update must summarize a multi-file skip into exactly one REINDEX_SKIPPED_FILES warning, got: []` (`service::mock_index_tests::update_facade_includes_exactly_one_reindex_warning_when_files_are_skipped`, mock_index_tests.rs:461) - necessity holds.
- `ddb-core/src/service/schema_apply.rs`: exit 101, first failure: `assertion \`left == right\` failed: apply_schema's dry_run return point must also summarize a multi-file skip into exactly one REINDEX_SKIPPED_FILES warning, got: []` (`service::mock_index_tests::apply_schema_dry_run_return_point_also_carries_the_reindex_warning`, mock_index_tests.rs:567) - necessity holds.
- `ddb-core/src/service/mod.rs`: exit 101, first failure: `error[E0308]: mismatched types` - `summarize_reindex_warnings(reindex_warnings)` expected `Vec<ConsistencyWarning>`, found `()` (compile error, `ddb-core/src/service/create.rs:63`, surfaced because the pre-task `mod.rs`'s `rebuild_if_stale` still returns `()`) - necessity holds.
- `ddb-core/src/app_contract/mod.rs`: exit 0, 44 passed. R2 applies (see "Ancillary files" above): the task's only change moves `REINDEX_SKIPPED_FILES` from an unconditional `pub(crate) use` into a `#[cfg(test)] pub(crate) use`, and `cargo test -p ddb-core --lib` compiles with `cfg(test)` active regardless of which use-site gates the re-export - the two states are functionally identical under any `cargo test` invocation. Verified additionally: `cargo check -p ddb-core` and `cargo build --tests` both exit 0 with the file held at today's (unconditional-then-cfg(test)) archived state alongside the other 11 files reverted. **Reclassified as Ancillary, no longer Required, no longer necessity-scored.**
- `ddb-core/src/ffi/records.rs`: exit 101 (necessity-6 clone). First failure: `error[E0432]: unresolved import \`super::records::RebuildWarningRecord\`` at `ddb-core/src/ffi/driver.rs:13`, plus `E0560`/`E0609` field errors in `driver.rs` and `ffi/tests.rs`. Necessity holds.
- `ddb-core/src/ffi/driver.rs`: exit 101 (necessity-7 clone). First failure: `error[E0063]: missing field `warnings`` in initializer of `records::RebuildReport` at `ddb-core/src/ffi/driver.rs:120`. Necessity holds.
- `ddb-core/src/ffi/mod.rs`: **exit 0, 44 passed** (necessity-8 clone) - does NOT hold. The task's whole diff to this file adds one symbol, `RebuildWarningRecord`, to the `pub use records::{...}` re-export list (verified: `git diff 48b9925 5cd6df2 -- ddb-core/src/ffi/mod.rs` is a single 3-line hunk, nothing else). Neither canonical test names the type (`ffi/driver.rs` imports it directly from `super::records`, bypassing this re-export entirely), which is why the run passes. **R2 was attempted and does not hold for this file**: reclassifying it "kept at today's state, never reverted" and rebuilding the template made `cargo build --tests` fail with `error[E0432]: unresolved import 'records::RebuildWarningRecord'` in `ffi/mod.rs:16`, because (unlike `app_contract/mod.rs`, whose dependency lives in a file that is never reverted) this file's canonical content re-exports a struct defined in `ffi/records.rs` - a sibling Required file that stays reverted at pre-task in the sealed template. R2 requires a file's canonical form to compile independently of its Required siblings' revert state; this file fails that precondition (see "`ffi/mod.rs` considered for R2 and rejected" above). The file was restored to Required/reverted status and the template rebuilt back to the 84012329... state. This is an unresolved zero-exit on an `impl` Required file.
- `ddb-core/src/ddb.udl`: **exit 0, 44 passed** (necessity-9 clone) - does NOT hold, and for a different reason than any file above: `ddb-core` has **no `build.rs`**, so this crate's `cargo build`/`cargo test` never parses or consumes `ddb.udl` at all (verified: `rg --files ddb-core -g build.rs` finds nothing). The file's task diff (6 lines removed: the `RebuildWarningRecord` dictionary and its use in `RebuildReport.warnings`) is real interface-definition content, structurally invisible to this raw test command regardless of whether the change is metadata or logic - this is not the R2 pattern (an observably-inert reshuffle) but a gate-scope gap (the gate never reads this file format at all). Not reclassified; reported as a blocker below.
- `ddb-cli/src/commands/crud.rs`: **exit 0, 44 passed** (necessity-10 clone) - does NOT hold, and for a third distinct reason: the raw test command is `cargo test -p ddb-core --lib -- ...`, scoped to the `ddb-core` package only, so it never compiles or runs anything in the `ddb-cli` crate. The task's diff here (`svc.rebuild_if_stale()?;` plus an 11-line explanatory comment in the `create` command, per its own text a defence-in-depth call that is "redundant today") is a real code change, not a metadata reshuffle - R2 does not apply. This is a caller-role Required file the chosen gate can never exercise, by construction of the `-p ddb-core` filter. Not reclassified; reported as a blocker below.
- `ddb-core/src/service/mock_index_tests.rs`: n/a (test file - necessity is enforced at scoring by dropped/own/ablate)
- `ddb-core/src/ffi/tests.rs`: n/a (test file - necessity is enforced at scoring by dropped/own/ablate)

**Verdict: ELIGIBLE (orchestrator decision, design C2 `necessity` refinement).** `app_contract/mod.rs` is rescued by R2 and reclassified Ancillary. Of the 9 Required `impl`/`caller` files, 6 record `holds` (`create.rs`, `update.rs`, `schema_apply.rs`, `service/mod.rs`, `ffi/records.rs`, `ffi/driver.rs`) and 3 record `gate-invisible`: `ffi/mod.rs` (re-export whose only consumers lie outside the gate's test modules; its canonical form depends on the reverted `ffi/records.rs`, so R2 cannot apply), `ddb.udl` (no `build.rs` in `ddb-core`, so no cargo target reads the file), `ddb-cli/src/commands/crud.rs` (package outside the gate's `-p ddb-core` filter). All three are real code changes the narrowed raw test command structurally cannot observe. Per the refinement, they stay Required (reverted in the template, listed in the prompt, so the pre-task tree remains self-consistent: the udl and the record it declares agree) and are scored only by `dropped` (untouched or no-op) and `stray`, never by the gate; the two test files are `n/a`. The eligibility bar of at least two `holds` `impl`/`caller` files is met three times over (6). Options rejected: widening the gate to `-p ddb-cli` plus a udl-reading step (no such build step exists in this crate; `ddb-cli` compiles but has no test that exercises the new call) and reverting to DISQUALIFIED (would discard the only 11-file task in the manifest over files the gate could never see under any command). The report discloses the 6 / 3 / 2 split for this task.

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
