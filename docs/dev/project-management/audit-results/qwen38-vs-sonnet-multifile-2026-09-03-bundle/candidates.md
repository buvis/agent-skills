# Multi-file eval candidates - stage A survey

Surveyed 2026-09-02 across the eighteen gita-registered repositories whose
`dev/local/prds/done/` directories were in scope. Fourteen hold done PRDs
(`agent-skills`, `calcard-mcp`, `claude-agoge`, `claude-aegis`,
`claude-autopilot`, `claude-git-ferry`, `claude-warden`, `engram`, `gems`,
`mkdocs-zettelkasten`, `ovcaq`, `doogat/ddb`, `doogat/jink`,
`tbouska/playground`); four are empty (`agoge-gym`, `claude-checkup`,
`claude-strunk`, `container-images`). Three of the fourteen were dropped
before prospect selection because their done ledgers carry no `- [ ]`/`- [x]`
task lines with `Acceptance:` clauses (`jink`, `playground`, `ovcaq` use bare
prose bullets), and `engram`'s ledger lines are phase-sized ("Harness + model
selection") rather than one-commit units, so no prospect there can satisfy
`single_unit`. This file records **16 prospects**, of which **7 are
`promising`**: 4 `impl+test` and 1 `impl+caller` in `gems` (Python), 3
`impl+test` in `ddb` (Rust). The rejected nine include two TypeScript
(`claude-warden`) prospects, kept on the record because their rejection
reasons (task-ADDED files with later history; later refactors that moved the
added helpers) are the two failure modes stage B will hit most often.

The six tasks used in the 2026-08-31 single-file round are excluded and do not
appear below: agent-skills `collect_purge_devlocal`, gems `executor.py`
fail-loud re-exec, ddb `ConsistencyWarning::UnreadableFile` (ddb PRD 00169
ledger line 161, commit `d1ca759`), claude-warden env-danger matcher
(claude-warden PRD 00018 ledger line 90), claude-git-ferry `branch-diff.bats`,
claude-aegis `_common.py` isatty guard (claude-aegis PRD 00002 ledger line
188).

Conventions used below. `<tree>` is the disposable worktree stage B will
create; gate commands are written to run from outside it. Every history line
is the output of `git log --oneline --no-patch <last>..HEAD -- <path>` run in
the prospect's repo, where `<last>` is the last commit of the run.
`empty` means the command printed nothing. Every repository was left as
found: no checkout, no edit, no commit.

## Stage B note (2026-09-02, retry 1) - all 7 prospects eligible

Stage B consumed **all 7 `promising` prospects** and **all 7 are eligible**:
six sit in `manifest.tsv` as tasks 1-6, and the seventh is the vetted
alternate `alt1`. No prospect is disqualified any more.

| stage A | stage B artifact | verdict |
|---|---|---|
| 1 | `tasks/1-repoint-bim-doc-callers.*` | eligible (impl+caller) |
| 2 | `tasks/2-route-tui-create-note.*` | eligible, **full four-file scope** |
| 3 | `tasks/3-repoint-zettel-save.*` | eligible |
| 4 | `tasks/4-record-raw-source-sha.*` | eligible, **scope narrowed** to the `promote` pair |
| 5 | `tasks/5-generalize-write-lock.*` | eligible (re-admitted) |
| 6 | `tasks/6-cap-frontmatter-size.*` | eligible (re-admitted), narrowed to the `parser/` pair |
| 7 | `tasks/alt1-surface-reindex-skip-warnings.*` | eligible, held as the alternate |

The first pass disqualified prospects 5 and 6 and narrowed prospects 2 and 4,
all on `interface_pinned`: the canonical `<base-sha>` test copy binds a name
the bare ledger line never states and the revert removes from the tree, so no
engine could satisfy it by reading the task. Two decisions taken on the retry
change that picture.

**Decision 1 - every prompt carries an interface-pins block.** A bare ledger
line under-specifies relative to the real autopilot task mix this eval stands
in for: a planner copies a `Contract` naming every exact symbol, signature,
literal and threshold. So each `tasks/<n>-<slug>.prompt.txt` now carries a
`Names the acceptance gate binds to` block between the file list and the two
fixed closing sentences, listing every identifier, signature, literal and value
the canonical tests bind that the pre-task tree does not already contain (most
read "none - ..."). The block states names and shapes only - never the
implementation, never which file is the test, never test bodies - and it is
identical for both engines, so it changes nothing about the comparison or the
dropped-a-file signal the eval measures. `interface_pinned` is now satisfied
when the ledger line PLUS that block names everything.

That re-admits prospect 5 (pin the three-argument
`acquire(lock_dir, lock_name, timeout)`, the caller-side `.git`, and the
literal `"ddb-write.lock"`) and prospect 6 (pin `MAX_FRONTMATTER_BYTES`, its
value `256 * 1024`, its home, and the error-message contract), and it restores
prospect 2 to its full four-file scope (pin `notify_result`'s signature and the
`"Failed"` fallback). Prospect 4 stays narrowed, because its `pipeline.py` half
fails for a different reason: the canonical `test_pipeline.py` binds the
`f"_triage/{name} (pending review)"` filename format that a LATER commit
introduced. That is a real disqualifier for the wider set, not a pinning gap.
Prospect 6's `indexer/tests/mod.rs` half is likewise dropped to Ancillary for a
non-pinning reason: the `--lib parser` gate never runs it, so it could not pass
a per-file `necessity` check.

**Decision 2 - task 1's gate is the ledger's own acceptance, as a command.**
The acceptance clause reads "the only `atomic_write` references under
`src/tools/bim` import from `buvis.pybase.filesystem`; bim doc tests pass", and
the manifest command is now exactly that, as an `&&`-chain
(`test ! -e` the deleted module, then `! rg` for the old import, then the doc
pytest run). The bare pytest command that stood there before passes on the
pre-task tree too - the revert restores both the old module and the old test
that covered it - so its baseline could not fail and the `necessity` check
would have disqualified the only `impl+caller` unit in the pool. All three
segments are verified at `<base-sha>` in
`tasks/1-repoint-bim-doc-callers.vetting.md`.

Stage A's observation 1 was right about the mechanism but named the wrong
symptom. It is not only that repos churn a file after the ledger line closes;
it is that in-crate Rust unit tests (`#[cfg(test)] mod tests`, sibling
`tests.rs`) bind private and crate-internal names freely. Under Decision 1 that
is a pinning cost, not a disqualifier, which is what lets both ddb prospects
back in.

---

## Prospect 1: gems / repoint bim doc callers to pybase.filesystem

- **repo**: `/Users/bob/git/src/github.com/buvis/gems` (Python)
- **PRD**: `dev/local/prds/done/00041-atomic-write-foundation-v1.md:42`
- **ledger line (verbatim)**:
  `- [ ] Repoint `bim/commands/doc/shared/` callers to `pybase.filesystem`; delete `doc/shared/atomic_write.py` (depends on: Phase 0) — Acceptance: the only `atomic_write` references under `src/tools/bim` import from `buvis.pybase.filesystem`; bim doc tests pass.`
- **commit**: contiguous run `d29dab6f..4d23c02d` (7 commits: `d29dab6f`,
  `3fd57f22`, `c1d56718`, `0297744b`, `9acda22c`, `1cc94082`, `4d23c02d`).
  Parent of `<first>`: `84e994cd`.
- **Required files**
  - `src/tools/bim/commands/doc/shared/atomic_write.py` - `impl` (deleted by the task)
  - `src/tools/bim/commands/doc/shared/zettel_writer.py` - `caller`
  - `src/tools/bim/commands/doc/shared/issuers.py` - `caller`
  - `src/tools/bim/commands/doc/shared/ocr.py` - `caller`
  - `src/tools/bim/commands/doc/shared/triage.py` - `caller`
  - `src/tools/bim/commands/doc/shared/pipeline.py` - `caller`
  - `src/tools/bim/commands/doc/audit/reporter.py` - `caller`
  - `tests/tools/bim/doc/test_atomic_write.py` - `test` (deleted by the task)
- **Ancillary files**: none
- **kind**: `impl+caller` (no test file was added or changed; the task removed
  one along with the module it covered)
- **gate command**:
  `uv --directory <tree> run pytest tests/tools/bim/doc -q`
- **file-level history** (`4d23c02d..HEAD`)
  - `atomic_write.py`: `empty`
  - `zettel_writer.py`: `empty`
  - `issuers.py`: `empty`
  - `ocr.py`: `empty`
  - `triage.py`: `empty`
  - `pipeline.py`: `26d2def6 fix(bim): treat a non-text claimed_at as an abandoned claim instead of raising` / `f6ecadd1 fix(bim): tell the truth about a document still awaiting triage review` / `b919d7ad fix(bim): record raw source sha on triage and promote` / `fc87d99f fix(bim): release ingest claim on any exit and reclaim stale claims` / `bdcc8e1a refactor(bim): relocate collision resolver to shared naming module`
  - `audit/reporter.py`: `empty`
  - `tests/tools/bim/doc/test_atomic_write.py`: `empty`
- **verdict**: `promising` - the only Required file with later history is
  `pipeline.py`, and all five later commits touch claim/triage logic, not the
  one-line `atomic_write_text` import this task changed, so a surgical revert
  of the import block is available.

---

## Prospect 2: gems / route TUI create through CommandCreateNote

- **repo**: `/Users/bob/git/src/github.com/buvis/gems` (Python)
- **PRD**: `dev/local/prds/done/00054-bim-serve-tui-convergence-v1.md:82`
- **ledger line (verbatim)**:
  `- [ ] Route `tui/create_note.py` through `CommandCreateNote` (depends on: Phase 0) — Acceptance: TUI create runs the same validation/defaults as CLI; empty required answer is rejected.`
- **commit**: contiguous run `c084d88c..cb2e1c55` (3 commits: `c084d88c`
  test, `3c6493fa` feat, `cb2e1c55` slop prune). Parent of `<first>`:
  `2ba5be3a`.
- **Required files**
  - `src/tools/bim/tui/create_note.py` - `impl`
  - `src/lib/buvis/pybase/result.py` - `impl` (the `notify_result` helper this
    task added)
  - `tests/tools/bim/tui/test_create_note.py` - `test`, CHANGED by the task
  - `tests/lib/pybase/test_result.py` - `test`, CHANGED by the task
- **Ancillary files**: none
- **kind**: `impl+test`
- **gate command**:
  `uv --directory <tree> run pytest tests/tools/bim/tui/test_create_note.py tests/lib/pybase/test_result.py -q`
- **file-level history** (`cb2e1c55..HEAD`)
  - `src/tools/bim/tui/create_note.py`: `empty`
  - `src/lib/buvis/pybase/result.py`: `empty`
  - `tests/tools/bim/tui/test_create_note.py`: `empty`
  - `tests/lib/pybase/test_result.py`: `empty`
- **verdict**: `promising` - every Required file has empty later history, so a
  whole-file revert to `2ba5be3a` restores the exact pre-task state. Strongest
  prospect in the survey.

---

## Prospect 3: gems / repoint MarkdownZettelRepository.save to atomic_write_text

- **repo**: `/Users/bob/git/src/github.com/buvis/gems` (Python)
- **PRD**: `dev/local/prds/done/00041-atomic-write-foundation-v1.md:40`
- **ledger line (verbatim)**:
  `- [ ] Repoint `MarkdownZettelRepository.save` (`:55`) to `atomic_write_text` (depends on: Phase 0) — Acceptance: regression test proves an interrupted save leaves the original note intact.`
- **commit**: contiguous run `a4fa75b1..30b42c3b` (2 commits: `a4fa75b1`
  test, `30b42c3b` fix). Parent of `<first>`: `fc7df0c3`.
- **Required files**
  - `src/lib/buvis/pybase/zettel/infrastructure/persistence/markdown_zettel_repository/markdown_zettel_repository.py` - `impl`
  - `tests/lib/zettel/infrastructure/persistence/test_markdown_zettel_repository_writer.py` - `test`, CHANGED by the task
- **Ancillary files**: none
- **kind**: `impl+test`
- **gate command**:
  `uv --directory <tree> run pytest tests/lib/zettel/infrastructure/persistence/test_markdown_zettel_repository_writer.py -q`
- **file-level history** (`30b42c3b..HEAD`)
  - `markdown_zettel_repository.py`: `67f777ac fix(zettel): isolate non-mapping parse failures and keep bracketed filenames in the warning` / `757235f1 fix(zettel): surface find_all parse errors across Rust and Python backends` / `b636774e refactor(bim): split sync_note execute into per-branch helpers and drop redundant encoding args`
  - `test_markdown_zettel_repository_writer.py`: `empty`
- **verdict**: `promising` - the test file is untouched since the task; the
  three later commits on the impl file all sit in `find_all`/`sync_note`, not
  in `save`, so a function-level revert of `save` is clean. Stage B must
  confirm `save` itself is byte-identical to its post-task form.

---

## Prospect 4: gems / record raw source sha on triage and promote

- **repo**: `/Users/bob/git/src/github.com/buvis/gems` (Python)
- **PRD**: `dev/local/prds/done/00044-bim-doc-claim-dedup-integrity-v1.md:43`
- **ledger line (verbatim)**:
  `- [ ] Record the raw source sha on triage (`pipeline.py:627`) and promote (`promote.py:236-237`) (depends on: Phase 0) — Acceptance: re-ingesting the same source PDF after promote is detected as duplicate, no second archive copy.`
- **commit**: contiguous run `0188270a..b919d7ad` (2 commits: `0188270a`
  test, `b919d7ad` fix). Parent of `<first>`: `fc87d99f`.
- **Required files**
  - `src/tools/bim/commands/doc/shared/pipeline.py` - `impl`
  - `src/tools/bim/commands/doc/promote/promote.py` - `impl`
  - `tests/tools/bim/doc/test_pipeline.py` - `test`, CHANGED by the task
  - `tests/tools/bim/doc/test_promote.py` - `test`, CHANGED by the task
- **Ancillary files**: none
- **kind**: `impl+test`
- **gate command**:
  `uv --directory <tree> run pytest tests/tools/bim/doc/test_pipeline.py tests/tools/bim/doc/test_promote.py -q`
- **file-level history** (`b919d7ad..HEAD`)
  - `pipeline.py`: `26d2def6 fix(bim): treat a non-text claimed_at as an abandoned claim instead of raising` / `f6ecadd1 fix(bim): tell the truth about a document still awaiting triage review`
  - `promote.py`: `55678673 refactor(bim): build promote's two processed rows from one literal`
  - `test_pipeline.py`: `6e9c0e20 test(bim): share pipeline test scaffolding and split the claim suites out` / `668a4cdb test(bim): move claim release and reclaim tests to their own module` / `fac918c0 test(bim): pin claim-integrity hardening for task 5` / `27f37de9 test(bim): pin pending-triage dedup row legibility for task 4`
  - `test_promote.py`: `empty`
- **verdict**: `promising`, with one caveat for stage B: `55678673` rebuilt
  the very `promote.py` rows this task added, so the surgical revert there is
  a rewrite of a later shape, not a straight undo. The `pipeline.py` and
  `test_pipeline.py` churn is in claim handling and test scaffolding, clear of
  the sha-recording lines.

---

## Prospect 5: ddb / generalize the git write-lock helper for the index-rebuild lock

- **repo**: `/Users/bob/git/src/github.com/doogat/ddb` (Rust)
- **PRD**: `dev/local/prds/done/00169-poison-file-reindex-resilience-v1.md:163`
- **ledger line (verbatim)**:
  `- [ ] Extend/reuse the 00162 lock helper (`git_ops/write_lock.rs`) for an index-rebuild lock file; define and document the lock-ordering rule vs the git write lock (no deps) - Acceptance: a unit test proves two handles serialize and the guard releases on drop; the ordering rule is written down (module doc).`
- **commit**: contiguous run `fde545b..71e718d` (3 commits: `fde545b` test,
  `f9c1e26` refactor, `71e718d` comment reword). Parent of `<first>`:
  `9759c4c`.
- **Required files**
  - `ddb-core/src/git_ops/write_lock.rs` - `impl`
  - `ddb-core/src/git_ops/mod.rs` - `caller`
  - `ddb-core/src/git_ops/tests.rs` - `test`, CHANGED by the task
- **Ancillary files**: none
- **kind**: `impl+test` (also carries a `caller`, which makes it a usable
  fallback if stage B needs a second `impl+caller`)
- **gate command**:
  `cargo test --manifest-path <tree>/Cargo.toml -p ddb-core --lib git_ops`
- **file-level history** (`71e718d..HEAD`)
  - `ddb-core/src/git_ops/write_lock.rs`: `empty`
  - `ddb-core/src/git_ops/mod.rs`: `empty`
  - `ddb-core/src/git_ops/tests.rs`: `empty`
- **verdict**: `promising` - all three Required files untouched since the
  task, so a whole-file revert to `9759c4c` is exact. Best Rust prospect.

---

## Prospect 6: ddb / cap frontmatter size at the parse boundary

- **repo**: `/Users/bob/git/src/github.com/doogat/ddb` (Rust)
- **PRD**: `dev/local/prds/done/00169-poison-file-reindex-resilience-v1.md:175`
- **ledger line (verbatim)**:
  `- [ ] Cap frontmatter size at the parse boundary so an oversized synced file degrades into the lenient skip path, never a fatal error or unbounded parse (depends on: Phase 0 collect-and-skip) - Acceptance: a file with an over-cap frontmatter block is skipped with a warning naming the path and reason; normal files unaffected; `--strict` hard-fails it; unit-tested.`
- **commit**: contiguous run `38577e7..b1bc2ed` (3 commits: `38577e7` test,
  `7d28653` feat, `b1bc2ed` test tidy). Parent of `<first>`: `e5ec64a`.
- **Required files**
  - `ddb-core/src/parser/mod.rs` - `impl`
  - `ddb-core/src/parser/tests.rs` - `test`, CHANGED by the task
  - `ddb-core/src/indexer/tests/mod.rs` - `test`, CHANGED by the task
- **Ancillary files**: `CHANGELOG.md`
- **kind**: `impl+test`
- **gate command**:
  `cargo test --manifest-path <tree>/Cargo.toml -p ddb-core --lib parser`
- **file-level history** (`b1bc2ed..HEAD`)
  - `ddb-core/src/parser/mod.rs`: `empty`
  - `ddb-core/src/parser/tests.rs`: `empty`
  - `ddb-core/src/indexer/tests/mod.rs`: `0a9a9f5 test(indexer): cover the post-lock re-check and assert the cold-start index directly (00169)` / `a946357 test(indexer): raise survivor and HEAD-convergence assertions in the eviction tests (00169)` / `6202bcb test(indexer): close adversarial gaps in the eviction tests (00169)` / `f555cb5 test(indexer): add eviction regression tests for poisoned modified files (00169)`
- **verdict**: `promising` - the impl file and its own test module are
  untouched. The four later commits on `indexer/tests/mod.rs` all add eviction
  tests, clear of the frontmatter-cap cases, so a function-level revert works;
  alternatively stage B can narrow the Required set to the `parser/` pair and
  keep the indexer test at today's state as Ancillary, since the gate runs
  `--lib parser`.

---

## Prospect 7: ddb / surface reindex skip warnings on the verb facades and the FFI record

- **repo**: `/Users/bob/git/src/github.com/doogat/ddb` (Rust)
- **PRD**: `dev/local/prds/done/00169-poison-file-reindex-resilience-v1.md:172`
- **ledger line (verbatim)**:
  `- [ ] Capture the `RebuildReport` in `ensure_fresh` and merge its skip warnings into the verb `AppOutput.warnings` via the facade; add a `warnings` field to the FFI `RebuildReport` record (`ddb-core/src/ffi/records.rs:173-177`) (depends on: mapping) - Acceptance: after a poison file lands, a create AND a search both succeed and each carries a skip `AppWarning`; the warning reaches CLI stderr (`write_warnings`) and the GraphQL warnings extension (`forward_warnings`); the FFI reindex report exposes the skip.`
- **commit**: contiguous run `7d72015..48b9925` (4 commits: `7d72015` test,
  `085f096` feat, `153c405` test, `48b9925` feat). Parent of `<first>`:
  `5cd6df2`.
- **Required files**
  - `ddb-core/src/service/create.rs` - `impl`
  - `ddb-core/src/service/update.rs` - `impl`
  - `ddb-core/src/service/schema_apply.rs` - `impl`
  - `ddb-core/src/service/mod.rs` - `impl`
  - `ddb-core/src/app_contract/mod.rs` - `impl`
  - `ddb-core/src/ffi/records.rs` - `impl`
  - `ddb-core/src/ffi/driver.rs` - `impl`
  - `ddb-core/src/ffi/mod.rs` - `impl`
  - `ddb-core/src/ddb.udl` - `impl` (UniFFI interface definition; the FFI
    record shape lives here, so the gate needs it)
  - `ddb-cli/src/commands/crud.rs` - `caller`
  - `ddb-core/src/service/mock_index_tests.rs` - `test`, CHANGED by the task
  - `ddb-core/src/ffi/tests.rs` - `test`, CHANGED by the task
- **Ancillary files**: `CHANGELOG.md`
- **kind**: `impl+test`
- **gate command**:
  `cargo test --manifest-path <tree>/Cargo.toml -p ddb-core --lib`
- **file-level history** (`48b9925..HEAD`)
  - `ddb-core/src/service/create.rs`: `empty`
  - `ddb-core/src/service/update.rs`: `empty`
  - `ddb-core/src/service/schema_apply.rs`: `empty`
  - `ddb-core/src/service/mod.rs`: `empty`
  - `ddb-core/src/app_contract/mod.rs`: `b3a5263 feat(cli): name each skipped file in the ddb reindex report (00169)`
  - `ddb-core/src/ffi/records.rs`: `empty`
  - `ddb-core/src/ffi/driver.rs`: `empty`
  - `ddb-core/src/ffi/mod.rs`: `empty`
  - `ddb-core/src/ddb.udl`: `empty`
  - `ddb-cli/src/commands/crud.rs`: `empty`
  - `ddb-core/src/service/mock_index_tests.rs`: `e5ec64a feat(cli): add reindex --strict and restore the unconditional explicit reindex (00169)` / `f408c30 feat(indexer): serialize the destructive full rebuild behind a cross-process lock (00169)`
  - `ddb-core/src/ffi/tests.rs`: `empty`
- **verdict**: `promising` on history (ten of twelve Required files are
  untouched), but flagged for size: twelve Required files across three crates
  is the largest unit in the survey. Stage B should treat it as an alternate
  rather than a core six pick unless a deliberately large task is wanted.

---

## Prospect 8: gems / create pybase.filesystem atomic_write

- **repo**: `/Users/bob/git/src/github.com/buvis/gems` (Python)
- **PRD**: `dev/local/prds/done/00041-atomic-write-foundation-v1.md:37`
- **ledger line (verbatim)**:
  `- [ ] Create `pybase/filesystem/atomic_write.py` by lifting the impl from `doc/shared/atomic_write.py`; export in `filesystem/__init__.py` — Acceptance: `from buvis.pybase.filesystem import atomic_write_text, atomic_write_bytes` works; unit test covers happy-path replace and same-dir tempfile.`
- **commit**: contiguous run `565e351a..fc7df0c3` (2 commits: `565e351a`
  test, `fc7df0c3` feat). Parent of `<first>`: `fa574f1d`.
- **Required files**
  - `src/lib/buvis/pybase/filesystem/atomic_write.py` - `impl`, ADDED by the task
  - `src/lib/buvis/pybase/filesystem/__init__.py` - `caller` (export)
  - `tests/lib/pybase/filesystem/test_atomic_write.py` - `test`, ADDED by the task
- **Ancillary files**: `docs/source/filesystem.rst`
- **kind**: `impl+test`
- **gate command**:
  `uv --directory <tree> run pytest tests/lib/pybase/filesystem/test_atomic_write.py -q`
- **file-level history** (`fc7df0c3..HEAD`)
  - `atomic_write.py`: `34825cbb refactor(filesystem): let fdopen own the descriptor and name the mode params` / `e17239ec docs(filesystem): record atomic-write scope, limits and closed invariant gap` / `8c1e69da refactor(filesystem): probe target permissions once instead of check-then-act` / `7cedc768 fix(filesystem): clean up temp file on any exit and stop masking write errors`
  - `filesystem/__init__.py`: `empty`
  - `test_atomic_write.py`: `34825cbb ...` / `e17239ec ...` / `8b4dbe19 test(filesystem): bind atomic-write tests to the atomic protocol and its callers` / `a21b0896 test(filesystem): pin atomic_write cleanup, fd ownership and error-masking behaviour`
- **verdict**: `rejected: task-ADDED files src/lib/buvis/pybase/filesystem/atomic_write.py and tests/lib/pybase/filesystem/test_atomic_write.py both have later history` - the pre-task state of each is "absent", and no revert can both delete them and keep the four later commits' work.

---

## Prospect 9: gems / delegate the PATCH route and handle_patch to CommandEditNote

- **repo**: `/Users/bob/git/src/github.com/buvis/gems` (Python)
- **PRD**: `dev/local/prds/done/00054-bim-serve-tui-convergence-v1.md:81`
- **ledger line (verbatim)**:
  `- [ ] Delete the PATCH route body; delegate to `UpdateZettelUseCase`, preserving the 00042 security layer on the route (`confine_path` + `X-Buvis-Token` check) (depends on: Phase 0) — Acceptance: PATCH and `handle_patch` share one code path; section-replace exists once; an out-of-vault or tokenless PATCH still returns 403/401.`
- **commit**: contiguous run `33689cc4..2ba5be3a` (2 commits: `33689cc4`
  test, `2ba5be3a` feat). Parent of `<first>`: `ca3e56cb`.
- **Required files**
  - `src/tools/bim/commands/serve/_actions.py` - `impl`
  - `src/tools/bim/commands/serve/_routes.py` - `caller`
  - `tests/tools/bim/test_serve.py` - `test`, CHANGED by the task
- **Ancillary files**: none
- **kind**: `impl+test`
- **gate command**:
  `uv --directory <tree> run pytest tests/tools/bim/test_serve.py -q`
- **file-level history** (`2ba5be3a..HEAD`)
  - `_actions.py`: `empty`
  - `_routes.py`: `7a173cd3 fix(bim): fail closed on error responses and announce open failures`
  - `tests/tools/bim/test_serve.py`: `09b8ff03 test(bim): split test_serve.py by route family and parametrize the action matrix` / `06cbdac1 test(bim): assert the PATCH route persists through the real repository`
- **verdict**: `rejected: Required test file tests/tools/bim/test_serve.py no longer exists at HEAD` - `09b8ff03` deleted it and split its cases into five `test_serve_*.py` modules, so the gate command cannot be run against today's tree and restoring the file would duplicate the split suite.

---

## Prospect 10: gems / surface CommandResult failures in the WebUI and the TUI screens

- **repo**: `/Users/bob/git/src/github.com/buvis/gems` (Python + TypeScript/Svelte)
- **PRD**: `dev/local/prds/done/00054-bim-serve-tui-convergence-v1.md:88`
- **ledger line (verbatim)**:
  `- [ ] `api.ts` / `ActionBar` check the envelope `status` (keeping the 00042 `X-Buvis-Token` header); `EditScreen._save` and the query-TUI screens `notify(severity="error")` on `CommandResult` failure (depends on: Phase 1) — Acceptance: a failing action returns non-2xx with the envelope (route test) and the TUI notifies on failure (Textual test); `api.ts`/`ActionBar` changes are verified indirectly (frontend has no test harness — manual WebUI smoke post-merge).`
- **commit**: contiguous run `7a5f07e0..a96a595d` (4 commits: `7a5f07e0`,
  `6d5c3368`, `67cb582c`, `a96a595d`, plus the Ancillary `fd3f2fcd`). Parent
  of `<first>`: `cb2e1c55`.
- **Required files** (as the pytest gate would need them)
  - `src/tools/bim/tui/edit_note.py` - `impl`
  - `src/tools/bim/tui/query.py` - `impl`
  - `tests/tools/bim/tui/test_edit_note.py` - `test`, CHANGED by the task
  - `tests/tools/bim/tui/test_query.py` - `test`, CHANGED by the task
  - `tests/tools/bim/tui/test_kanban.py` - `test`, CHANGED by the task
- **Ancillary files**: `CHANGELOG.md` (`fd3f2fcd`)
- **kind**: `impl+test`
- **gate command**:
  `uv --directory <tree> run pytest tests/tools/bim/tui -q`
- **file-level history** (`a96a595d..HEAD`)
  - `src/tools/bim/tui/edit_note.py`: `4f57423f fix(bim): report EditNoteApp save failures through notify_result`
  - `src/tools/bim/tui/query.py`: `empty`
  - `tests/tools/bim/tui/test_edit_note.py`: `92cc9a69 test(bim): pin EditNoteApp save-failure notification severity`
  - `tests/tools/bim/tui/test_query.py`: `empty`
  - `tests/tools/bim/tui/test_kanban.py`: `empty`
- **verdict**: `rejected: extra code files src/tools/bim/commands/serve/frontend/src/lib/api.ts, .../components/ItemPanel.svelte, .../components/MarkdownEditor.svelte, .../components/widgets/LinkWidget.svelte` - the same ledger task changed four real frontend files that the pytest gate neither needs nor scores (the ledger line itself says the frontend has no test harness), so the Required set cannot be exactly the set the gate needs.

---

## Prospect 11: gems / repoint the updater state write to atomic_write_text

- **repo**: `/Users/bob/git/src/github.com/buvis/gems` (Python)
- **PRD**: `dev/local/prds/done/00041-atomic-write-foundation-v1.md:41`
- **ledger line (verbatim)**:
  `- [ ] Repoint `updater/state.py._write_state` (`:36-42`) to `atomic_write_text`, keeping error-swallow (depends on: Phase 0) — Acceptance: state write is atomic; existing updater tests pass.`
- **commit**: single commit `84e994cd`. Parent: `30b42c3b`.
- **Required files**
  - `src/lib/buvis/pybase/updater/state.py` - `impl`
- **Ancillary files**: none
- **kind**: `impl` only - neither `impl+test` nor `impl+caller` (no test file
  added or changed, no second code file)
- **gate command**:
  `uv --directory <tree> run pytest tests/lib/pybase/updater -q`
- **file-level history** (`84e994cd..HEAD`)
  - `src/lib/buvis/pybase/updater/state.py`: `empty`
- **verdict**: `rejected: multi_file fails - 1 Required file` - clean history and a real gate, but the task changed exactly one code file and added or changed no test, so it is a single-file task and belongs to the 2026-08-31 round's shape, not this one.

---

## Prospect 12: gems / surface find_all parse errors across both zettel backends

- **repo**: `/Users/bob/git/src/github.com/buvis/gems` (Python)
- **PRD**: `dev/local/prds/done/00050-zettel-scanner-error-surfacing-v1.md:36`
- **ledger line (verbatim)**:
  `- [ ] Wrap the Python fallback loop to collect per-file errors matching Rust semantics — Acceptance: parametrized test shows both backends report the bad file and return the rest.`
- **commit**: contiguous run `17d92ef6..757235f1` (2 commits: `17d92ef6`
  test, `757235f1` fix). Parent of `<first>`: `91bd122e`.
- **Required files**
  - `src/lib/buvis/pybase/zettel/infrastructure/persistence/markdown_zettel_repository/markdown_zettel_repository.py` - `impl`
  - `tests/lib/zettel/infrastructure/persistence/test_markdown_zettel_repository_reader.py` - `test`, CHANGED by the task
- **Ancillary files**: `CHANGELOG.md` (added separately in `c8a44d3a`)
- **kind**: `impl+test`
- **gate command**:
  `uv --directory <tree> run pytest tests/lib/zettel/infrastructure/persistence/test_markdown_zettel_repository_reader.py -q`
- **file-level history** (`757235f1..HEAD`)
  - `markdown_zettel_repository.py`: `67f777ac fix(zettel): isolate non-mapping parse failures and keep bracketed filenames in the warning` / `b636774e refactor(bim): split sync_note execute into per-branch helpers and drop redundant encoding args`
  - `test_markdown_zettel_repository_reader.py`: `7ce22f01 test(zettel): add malformed-YAML-frontmatter parse-error test` / `e98f234b test(zettel): add regression tests for non-mapping parse errors and bracketed filenames` / `67f777ac fix(zettel): isolate non-mapping parse failures and keep bracketed filenames in the warning`
- **verdict**: `rejected: later fix 67f777ac reworks the same parse-error path in both Required files` - the follow-up changed the warning text and the error-isolation logic this task introduced, so neither a whole-file nor a function-level revert yields a pre-task state that today's tests describe.

---

## Prospect 13: ddb / stamp the index schema version and lock the schema-upgrade drop

- **repo**: `/Users/bob/git/src/github.com/doogat/ddb` (Rust)
- **PRD**: `dev/local/prds/done/00169-poison-file-reindex-resilience-v1.md:174`
- **ledger line (verbatim)**:
  `- [ ] Stamp an index schema version (`PRAGMA user_version` or a `_ddb_meta` key) written on every rebuild and checked at connection/configure; a mismatch takes the locked destructive-rebuild path; retire or demote the FTS-column probe (`needs_schema_upgrade`, `indexer/mod.rs:159-180`) (depends on: locked destructive rebuild) - Acceptance: opening an index stamped with an older version triggers exactly one locked drop-rebuild and a current version triggers none; unit-tested.`
- **commit**: contiguous run `6bc2cde..9df1643` (4 commits: `6bc2cde` test,
  `bc328dd` feat, `0537b18` fix, `9df1643` docs). Parent of `<first>`:
  `08ed093`.
- **Required files**
  - `ddb-core/src/indexer/mod.rs` - `impl`
  - `ddb-core/src/indexer/rebuild.rs` - `impl`
  - `ddb-core/src/indexer/tests/mod.rs` - `test`, CHANGED by the task
- **Ancillary files**: `CHANGELOG.md`
- **kind**: `impl+test`
- **gate command**:
  `cargo test --manifest-path <tree>/Cargo.toml -p ddb-core --lib indexer`
- **file-level history** (`9df1643..HEAD`)
  - `ddb-core/src/indexer/mod.rs`: `47c826b refactor(indexer): extract the rebuild-lock helper, the per-path parse step, and schema-version detection (00169)`
  - `ddb-core/src/indexer/rebuild.rs`: `47c826b ...` / `681b24c fix(indexer): evict stale rows for files an incremental reindex skips (00169)` / `e5ec64a feat(cli): add reindex --strict and restore the unconditional explicit reindex (00169)`
  - `ddb-core/src/indexer/tests/mod.rs`: `0a9a9f5 test(indexer): cover the post-lock re-check and assert the cold-start index directly (00169)` / `a946357 ...` / `6202bcb ...` / `f555cb5 ...` / `38577e7 test(parser): add frontmatter byte-cap tests (00169)` / `c255d4d test(indexer): pin strict rebuild and unconditional explicit reindex (00169)`
  - (ordering above is newest-first as `git log` prints it)
- **verdict**: `rejected: later refactor 47c826b moved the schema-version detection this task added into a new module ddb-core/src/indexer/schema_version.rs` - the added code no longer lives where the task put it, so there is no function-level revert and a whole-file revert would drop the extraction.

---

## Prospect 14: ddb / add the consistency-warning to AppWarning mapping

- **repo**: `/Users/bob/git/src/github.com/doogat/ddb` (Rust)
- **PRD**: `dev/local/prds/done/00169-poison-file-reindex-resilience-v1.md:171`
- **ledger line (verbatim)**:
  `- [ ] Add `From<ConsistencyWarning> for AppWarning` in `ddb-core/src/app_contract/output.rs` (depends on: Phase 0) - Acceptance: each variant maps to a stable `code` + human `message`; unit-tested.`
- **commit**: contiguous run `ef2165c..5cd6df2` (2 commits: `ef2165c` test,
  `5cd6df2` chore). Parent of `<first>`: `71e718d`.
- **Required files**
  - `ddb-core/src/app_contract/output.rs` - `impl` (its `#[cfg(test)]` module
    is in the same file, so the task added no separate test file)
  - `ddb-core/src/app_contract/mod.rs` - `caller` (re-exports the helpers)
- **Ancillary files**: none
- **kind**: `impl+caller`
- **gate command**:
  `cargo test --manifest-path <tree>/Cargo.toml -p ddb-core --lib app_contract`
- **file-level history** (`5cd6df2..HEAD`)
  - `ddb-core/src/app_contract/output.rs`: `c732e9a fix(app_contract): point the truncated reindex summary at ddb reindex (00169)` / `5e4f5db test(app_contract): require the truncated reindex summary to name a real remedy (00169)` / `d5b5a33 fix(app_contract): report only skipped files in the reindex warning, deduplicated by path (00169)` / `f2dbaf2 test(app_contract): pin the skip-only deduplicated reindex warning summary (00169)`
  - `ddb-core/src/app_contract/mod.rs`: `b3a5263 feat(cli): name each skipped file in the ddb reindex report (00169)` / `48b9925 feat(ffi): surface per-file reindex skip warnings on the RebuildReport record (00169)`
- **verdict**: `rejected: four later commits rewrote the summarizing helpers this task added in ddb-core/src/app_contract/output.rs` - the mapping's message and dedup behaviour were changed twice afterwards, so a revert of those functions would delete work the current tests depend on.

---

## Prospect 15: claude-warden / diagnose scaffolding and the native-permission shadowing check

- **repo**: `/Users/bob/git/src/github.com/buvis/claude-warden` (TypeScript)
- **PRD**: `dev/local/prds/done/00015-diagnose-setup-issues-v1.md:110`
- **ledger line (verbatim)**:
  `- [ ] Implement the native-permission shadowing check across the three settings files (no deps) - Acceptance: fixture settings with `Bash(rm:*)` in deny fails with file+entry named; `Bash(*)` in allow passes with info; missing files pass.`
- **commit**: contiguous run `f888af1..be09cab` (2 commits: `f888af1` test,
  `be09cab` feat). Parent of `<first>`: `261e80d`.
- **Required files**
  - `src/diagnose.ts` - `impl`, ADDED by the task
  - `src/__tests__/diagnose.test.ts` - `test`, ADDED by the task
- **Ancillary files**: none
- **kind**: `impl+test`
- **gate command**: `npm --prefix <tree> test -- diagnose`
- **file-level history** (`be09cab..HEAD`)
  - `src/diagnose.ts`: 13 later commits, newest first `9f8f4ab` / `c29a560` / `ee1a93b` / `e6c3387` / `4fcd8c7` / `85aafee` / `8522a41` / `81f5b53` / `553968e` / `d6da2e4` / `3d6073d` / `2b76827` / `085c1ab`
  - `src/__tests__/diagnose.test.ts`: 8 later commits, newest first `cb24fb4` / `421216d` / `d6ef4f8` / `ad20dfa` / `2d5ca54` / `d6da2e4` / `3d6073d` / `b735496`
- **verdict**: `rejected: task-ADDED files src/diagnose.ts and src/__tests__/diagnose.test.ts both have later history` - their pre-task state is "absent" and the module grew ten more checks afterwards.

---

## Prospect 16: claude-warden / hook-registration, binary, and config-health checks

- **repo**: `/Users/bob/git/src/github.com/buvis/claude-warden` (TypeScript)
- **PRD**: `dev/local/prds/done/00015-diagnose-setup-issues-v1.md:111`
- **ledger line (verbatim)**:
  `- [ ] Implement hook-registration, binary, and config-health checks (no deps) - Acceptance: missing `dist/index.cjs` fails; absent PreToolUse Bash matcher fails; unparseable fixture yaml fails with the parse error.`
- **commit**: contiguous run `b735496..085c1ab` (3 commits: `b735496` test,
  `3e1d6da` test trim, `085c1ab` feat). Parent of `<first>`: `be09cab`.
- **Required files**
  - `src/diagnose.ts` - `impl`
  - `src/__tests__/diagnose.test.ts` - `test`, CHANGED by the task
- **Ancillary files**: none
- **kind**: `impl+test`
- **gate command**: `npm --prefix <tree> test -- diagnose`
- **file-level history** (`085c1ab..HEAD`)
  - `src/diagnose.ts`: `9f8f4ab` / `c29a560` / `ee1a93b` / `e6c3387` / `4fcd8c7` / `85aafee` / `8522a41 refactor(diagnose): extract binary/plugin-root helpers under 50-line limit` / `81f5b53 refactor(diagnose): extract stamp/permission/hook helpers to satisfy 50-line limit` / `553968e` / `d6da2e4` / `3d6073d` / `2b76827`
  - `src/__tests__/diagnose.test.ts`: `cb24fb4` / `421216d` / `d6ef4f8` / `ad20dfa test(diagnose): split diagnose.test.ts under 800 lines; skip EACCES tests on root` / `2d5ca54` / `d6da2e4` / `3d6073d`
- **verdict**: `rejected: later refactors 81f5b53 and 8522a41 extracted the very hook, binary and plugin-root helpers this task added` - the code moved out of the functions the task wrote, and `ad20dfa` split the test file, so no clean revert of either Required file exists.

---

## Stage A tally

| # | repo | language | kind | verdict |
|---|---|---|---|---|
| 1 | gems | Python | `impl+caller` | promising |
| 2 | gems | Python | `impl+test` | promising |
| 3 | gems | Python | `impl+test` | promising |
| 4 | gems | Python | `impl+test` | promising |
| 5 | ddb | Rust | `impl+test` | promising |
| 6 | ddb | Rust | `impl+test` | promising |
| 7 | ddb | Rust | `impl+test` | promising |
| 8 | gems | Python | `impl+test` | rejected |
| 9 | gems | Python | `impl+test` | rejected |
| 10 | gems | Python + TS | `impl+test` | rejected |
| 11 | gems | Python | - | rejected |
| 12 | gems | Python | `impl+test` | rejected |
| 13 | ddb | Rust | `impl+test` | rejected |
| 14 | ddb | Rust | `impl+caller` | rejected |
| 15 | claude-warden | TypeScript | `impl+test` | rejected |
| 16 | claude-warden | TypeScript | `impl+test` | rejected |

Promising: 7 - six `impl+test` and one `impl+caller`, across 2 repos and 2
languages (Python, Rust). That clears the composition floor for stage B (6
picks needing >= 3 `impl+test`, >= 1 `impl+caller`, >= 2 repos, >= 2
languages) with one spare, but leaves no slack for two alternates and no third
language.

Two observations stage B should carry forward:

1. **Language spread is the binding constraint, not count.** Every repo in the
   portfolio that runs a test-first, review-fix workflow (claude-autopilot,
   claude-warden, claude-aegis) churns the same file two to five more times
   after the ledger task closes, and the churn lands inside the functions the
   task wrote. That is why both TypeScript prospects and the Python
   `claude-aegis`/`claude-autopilot` candidates fell out, while `gems` and
   `ddb` - which close a ledger line and move to the next file - survived. If
   a third language is required, the place to look is a repo's newest done PRD
   only.
2. **Ledger granularity decides `single_unit`.** `engram`, `jink`,
   `playground` and `ovcaq` were unusable not for history reasons but because
   their done ledgers state phase-sized goals rather than one-commit tasks.
   `ddb` PRD 00169 and `gems` PRD 00041/00044/00054 were productive precisely
   because each `- [ ]` line maps to one test commit plus one implementation
   commit.
