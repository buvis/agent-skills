### Task 6 - cap-frontmatter-size (ddb)

- Template: `/tmp/qwen-eval-00010/6-cap-frontmatter-size-tpl/`
- PRETASK_SHA: `dea40bd2749e1edbb5f22e16a13ce53eecdc7a39`
- `mise trust <tpl>/.mise.toml`: exit 0
- `mise env -C <tpl> -s bash`: exit 0
- Warmup: `cargo build --manifest-path <tpl>/Cargo.toml --tests`. Exit 0, cold build ~41s (shares base sha with task 5, no downstream-coupling problem here since the frontmatter cap is independent of write_lock).
- Necessity (2 Required files, clone rule; raw test: `cargo test --manifest-path <clone>/Cargo.toml -p ddb-core --lib parser`):
  - `ddb-core/src/parser/mod.rs`: exit 101, compile error `E0425: cannot find value MAX_FRONTMATTER_BYTES` - necessity holds.
  - `ddb-core/src/parser/tests.rs`: **exit 0, 94 passed** - DISQUALIFYING, same pattern as tasks 3 and 4: the pre-task test file has none of the 3 new cap cases, so it passes trivially against the canonical, backward-compatible impl.
- Step 14 check: `git status --porcelain` empty, `git rev-parse HEAD` == PRETASK_SHA. Confirmed.
- **DISQUALIFIED** - third confirmed occurrence of the systemic test-file-necessity pattern (after tasks 3 and 4).
