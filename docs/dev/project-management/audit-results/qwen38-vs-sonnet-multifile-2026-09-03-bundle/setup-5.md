### Task 5 - generalize-write-lock (ddb)

- Template: `/tmp/qwen-eval-00010/5-generalize-write-lock-tpl/`
- PRETASK_SHA: `c9e60b8341923874002f4076aa0c49ba3f8073fd`
- `mise trust <tpl>/.mise.toml`: exit 0
- `mise env -C <tpl> -s bash`: exit 0
- Warmup: `cargo build --manifest-path <tpl>/Cargo.toml --tests` - **FAILS, exit 101**, 14 compile errors (E0603 module `write_lock` is private, E0061 wrong arg count) in `ddb-core/src/indexer/tests/mod.rs`, which is not a Required file for this task but already calls the post-task 3-argument `write_lock::acquire` and expects `pub(crate)` visibility. The revert only touches the 3 Required files; it never accounted for this downstream coupling.
- Necessity: not run - blocked by the build failure.
- **DISQUALIFIED at prep step 12** (dependency warmup / build), a different and more fundamental failure mode than tasks 3/4's necessity-based disqualification: the pre-task tree here does not even compile.
