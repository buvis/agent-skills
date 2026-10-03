# Task 5 - ddb / generalize the git write-lock helper for the index-rebuild lock

Stage A prospect 5. Verdict: **eligible**.

Stage B first disqualified this candidate on `interface_pinned` and wrote it up
as `tasks/dq-generalize-write-lock.vetting.md`. Retry 1's Decision 1 gives every
prompt an interface-pins block, which is exactly what the gap needed, so the
candidate is re-admitted and that `dq-` note is superseded by this one (its
substance is folded in below, under "Why this needed pinning").

Kind: impl+test

Repo: `/Users/bob/git/src/github.com/doogat/ddb` (Rust)
PRD: `dev/local/prds/done/00169-poison-file-reindex-resilience-v1.md:163`

Commit run: `fde545b..71e718d` (3 commits: `fde545b` test, `f9c1e26` refactor,
`71e718d` comment reword)
Parent of `<first>` (`fde545b^`): `9759c4c`
Base sha (`HEAD` at vetting time): `8fe51c9d3fcee53a1ef14b2955083fd6a07977eb`

## Reverifiability

Working tree clean at `<base-sha>`: `git -C <src> status --porcelain` printed
nothing; control `git -C <src> status --porcelain --branch` printed
`## master...origin/master`.

Raw test command:

    cargo test --manifest-path <tree>/Cargo.toml -p ddb-core --lib git_ops

Run once at `<base-sha>` against the source tree: **exit 0**,
`101 passed; 0 failed; 0 ignored; 0 measured; 1445 filtered out`.

The `git_ops` filter selects both test surfaces this task owns:
`git_ops::tests::*` (the sibling `tests.rs` module, which the canonical copy
replaces at gate time) and `git_ops::write_lock::tests::*` (the `#[cfg(test)]
mod tests` that lives inside `write_lock.rs` itself and stays engine-owned).

## Required files

- `ddb-core/src/git_ops/write_lock.rs` (impl)
- `ddb-core/src/git_ops/mod.rs` (caller)
- `ddb-core/src/git_ops/tests.rs` (test) - CHANGED by the task

Ancillary files: none

`multi_file`: 3 Required files, 1 `impl` + 1 `caller` + 1 `test` the task
changed. Kind is `impl+test` because a canonical test copy is graded; it would
serve as a fallback `impl+caller` unit if task 1 were ever dropped.

## History per Required file

    git -C <src> log --oneline --no-patch 71e718d..HEAD -- <each Required path>

All three printed nothing. Controls, because an empty filtered `git log` proves
nothing on its own:

- unfiltered, same range: `git -C <src> log --oneline --no-patch 71e718d..HEAD
  --max-count=4` prints `8fe51c9`, `19d6c2e`, `7452f71`, `44b95d9`, so the range
  is non-empty.
- whole history of the three paths: `git -C <src> log --oneline --no-patch -4 --
  <the 3 paths>` prints `71e718d`, `f9c1e26`, `fde545b`, `9b37ac2` - the three
  newest are the task's own commits, so nothing has touched any of them since.

Verdicts:

- `ddb-core/src/git_ops/write_lock.rs`: `empty` -> `whole-file`
- `ddb-core/src/git_ops/mod.rs`: `empty` -> `whole-file`
- `ddb-core/src/git_ops/tests.rs`: `empty` -> `whole-file`

`clean_history`: all three clean, so the whole-file revert to `9759c4c` is
exact. This also means `<base-sha>` equals the end of the commit run for
`git_ops/tests.rs`, so the canonical copy cannot bind behaviour a later commit
introduced - there are no later commits.

## Reverse patch

    git -C <src> diff 71e718d 9759c4c --output=<abs>/tasks/5-generalize-write-lock.reverse.patch -- ddb-core/src/git_ops/write_lock.rs ddb-core/src/git_ops/mod.rs ddb-core/src/git_ops/tests.rs

No hand-written hunk is needed: all three files are `whole-file`.

`git -C /Users/bob/git/src/github.com/doogat/ddb apply --check -v <patch>`:
clean, all three files.

What the revert puts back, read off `git show 9759c4c:ddb-core/src/git_ops/write_lock.rs`:

- `pub fn acquire(repo_root: &Path, timeout: Duration) -> Result<WriteLockGuard>`
  - two parameters, and the helper joins `.git` itself
  (`repo_root.join(".git").join(LOCK_FILE_NAME)`);
- a private `const LOCK_FILE_NAME: &str = "ddb-write.lock";` inside the helper;
- an inline `#[cfg(test)] mod tests` whose three cases
  (`second_acquire_blocks_until_first_guard_released`,
  `acquire_times_out_when_lock_held`, `acquire_succeeds_after_release`) all call
  the two-argument form. Those live in a Required `impl` file, so the engine
  owns them and must keep them compiling and passing under the new signature;
  the gate runs them.
- in `git_ops/mod.rs`: `mod write_lock;` (private) and
  `write_lock::acquire(&self.path, WRITE_LOCK_TIMEOUT)?`.

Pretask: c9e60b8341923874002f4076aa0c49ba3f8073fd

Necessity: not run - DISQUALIFIED at prep step 12 (dependency warmup). `cargo build --manifest-path <tpl>/Cargo.toml --tests` fails with 14 compile errors: `ddb-core/src/indexer/tests/mod.rs` (NOT a Required file, kept at `<base-sha>`'s today's-state) already calls `crate::git_ops::write_lock::acquire(dir, "ddb-rebuild.lock", timeout)` - the pinned 3-argument post-task signature - and requires `write_lock` to be `pub(crate)` (`E0603: module write_lock is private`, `E0061: this function takes 2 arguments but 3 arguments were supplied`, at indexer/tests/mod.rs:4935-5934). The revert restores `write_lock.rs`/`mod.rs`/`tests.rs` to the pre-task 2-argument/private-module shape, but `indexer/tests/mod.rs` was never accounted for in this task's Required/Ancillary file list even though it is compiled as part of the same `--lib` test target and already depends on the post-task interface (evidently a later, undocumented commit wired the index-rebuild lock to this task's generalized `acquire`). This is a vetting gap: "History per Required file" only checked the 3 Required paths' own history, not whether other compiled files reference them. The pre-task tree does not compile, so step 12 fails outright; per the prep-failure rule this disqualifies task 5.
- `ddb-core/src/git_ops/write_lock.rs`: not run (build failed before necessity clones)
- `ddb-core/src/git_ops/mod.rs`: not run (build failed before necessity clones)
- `ddb-core/src/git_ops/tests.rs`: not run (build failed before necessity clones)

## Pinned interface

The prompt's `Names the acceptance gate binds to` block reads, verbatim:

- `pub fn acquire(lock_dir: &Path, lock_name: &str, timeout: Duration) -> Result<WriteLockGuard>`
  in `ddb-core/src/git_ops/write_lock.rs` - exactly three parameters, in that
  order.
- `acquire` uses `lock_dir` as given (`lock_dir.join(lock_name)`); it must NOT
  join `.git` itself any more. Callers pass the repository's `.git` directory
  as `lock_dir`.
- The lock file name is a caller-supplied argument, and the git write path
  passes the literal `"ddb-write.lock"` - e.g. in `ddb-core/src/git_ops/mod.rs`:
  `write_lock::acquire(&self.path.join(".git"), "ddb-write.lock", WRITE_LOCK_TIMEOUT)`.
- The guard type stays `WriteLockGuard` and still releases the OS lock on drop.
- The module stays reachable from the `git_ops` test module as
  `super::write_lock`.

### Why this needed pinning

The canonical `ddb-core/src/git_ops/tests.rs` calls, twice
(`merge_blocks_while_write_lock_held`, `commit_merge_blocks_while_write_lock_held`):

    super::write_lock::acquire(
        &dir_b_path.join(".git"),
        "ddb-write.lock",
        Duration::from_secs(10),
    )

That binds three things the ledger line never states: the three-parameter
signature and its order; the caller-side `.join(".git")`, which matters because
the pre-task helper joined `.git` internally, so an engine that keeps the repo
root as the first argument compiles fine and then locks
`.git/.git/ddb-write.lock` and both tests silently stop blocking; and the
literal `"ddb-write.lock"` as a caller-supplied argument. All three are now in
the prompt.

Everything else either canonical case reaches is already in the reverted tree:
`GitRepo` and its merge/commit methods, `WRITE_LOCK_TIMEOUT`, `DoogatError`,
`fs2::FileExt`, `tempfile::TempDir`, `Duration`.

Canonical test files copied:

- `ddb-core/src/git_ops/tests.rs` ->
  `5-generalize-write-lock.canonical/ddb-core/src/git_ops/tests.rs`

## Notes

- The task also changed `mod write_lock;` to `pub(crate) mod write_lock;` in
  `git_ops/mod.rs`. That is NOT pinned, deliberately: `git_ops::tests` is a
  child module of `git_ops`, so `super::write_lock` resolves under either
  visibility, and no other Required file needs the wider one. An engine that
  leaves the module private still passes the gate.
- The one structural risk on this candidate is shared by every Rust unit test in
  ddb: they live inside the crate, so they bind private and crate-internal names
  freely. Here the pins block covers all of them; that is the whole reason the
  candidate is back.
