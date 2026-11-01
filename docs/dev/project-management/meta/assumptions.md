# Assumptions ledger — PRD 00163-windows-suite-residual-failures-v1

## 2: Append manifest records with newline="" in purge_devtmp.py and its fixture

- `batch` only needs to be a plausible YYYY-MM-DD-shaped string for `trash_file`'s destination path construction; it does not need to match any particular "now" since this test doesn't exercise `empty_old_trash`'s age filtering (Tess).
- Monkeypatching `Path.open` (rather than `builtins.open`) is the correct seam, since `trash_file`'s manifest append calls `manifest.open(...)` (a `Path` method), not the `open` builtin directly (Tess).
- Simulating translation by literal `str.replace("\n", "\r\n")` on `write()` is an acceptable stand-in for "the platform's text-mode translation" (Tess).

## 3: Log native realpath cwd and filter by resolved path in eval_harness_run_helpers.py

- The task did not pin an exception type for the future raise, so the test asserts only `pytest.raises(Exception)` and checks message content, not a specific exception class (Tess).
- Built a minimal `round_` via `SimpleNamespace(run=<tmp_path dir>)` rather than the module's `rounds`/`vetted` fixtures, since `_logged_cwds` only reads `round_.run` (Tess).
- Used two distinct unrelated raw lines so the message-containment assertions can't be satisfied by a stub that only echoes a single hardcoded line (Tess).
- The contract allows either an equality check or a commonpath/prefix check depending on what the fixtures need; used equality-or-prefix because the real round fixtures log cwd from inside per-attempt clone subdirectories under the run dir, not the run dir itself (Ivan).
- The raised exception's message embeds the raw lines via Python's default list repr, which satisfies the test's "message contains each raw line as a substring" check (Ivan).
- Used plain `Exception` (not a custom exception class) since the test only asserts `pytest.raises(Exception)` and the task names no specific type (Ivan).

## 4: Add -ra to the Windows suite step in ci.yml

- The "Run the suite" step under the windows job is the only `uv run --python 3.13 pytest` line in the file, so the edit matched that line only (Ivan).
