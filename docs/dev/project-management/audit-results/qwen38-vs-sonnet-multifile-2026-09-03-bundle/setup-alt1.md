### alt1 - surface-reindex-skip-warnings (ddb, vetted alternate)

- Template: `/tmp/qwen-eval-00010/alt1-surface-reindex-skip-warnings-tpl/`
- PRETASK_SHA: `b64d87b164b4da3ca2d333b40128bbd24ccbbcd4`
- `mise trust <tpl>/.mise.toml`: exit 0
- `mise env -C <tpl> -s bash`: exit 0
- Warmup: `cargo build --manifest-path <tpl>/Cargo.toml --tests`. Exit 0, ~44s cold build, 4 unused-import/dead-code warnings only (expected: the functions this task's canonical tests exercise aren't called by anything else at pre-task state).
- Necessity: NOT RUN for any of the 12 Required files. alt1's raw test command is the full unfiltered `cargo test -p ddb-core --lib` (1546 tests), which alt1's own vetting note already measured at well over 10 minutes per invocation. Running it 12 times (once per Required file) would cost 2+ hours, and the systemic "test-file necessity gives a zero exit" pattern (see tasks 3, 4, 6) was already independently confirmed three times by the time this candidate was reached, with the same underlying mechanism applying to alt1's two test files (`mock_index_tests.rs`, `ffi/tests.rs`, both additive). Judged not worth the wall-clock cost to re-confirm; flagged in the final report instead.
- Step 14 check: `git status --porcelain` empty, `git rev-parse HEAD` == PRETASK_SHA. Confirmed.
- **NOT usable as a clean substitute** for any of tasks 3/4/6's slots without first confirming its own necessity - which is exactly what's skipped above. Even if run, it would likely need the identical waiver task 3/4/6 need.
