### Task 4 - record-raw-source-sha (gems)

- Template: `/tmp/qwen-eval-00010/4-record-raw-source-sha-tpl/`
- PRETASK_SHA: `cada08ac7fd703e95887480ee45a5811e5f8b791`
- `mise trust <tpl>/.mise.toml`: exit 0
- `mise env -C <tpl> -s bash`: exit 0
- Warmup: `uv --directory <tpl> sync --all-extras --group test`. Exit 0, 110 packages installed (fresh venv, cold).
- Necessity (2 Required files, clone rule; raw test: `uv --directory <clone> run pytest tests/tools/bim/doc/test_promote.py -q`):
  - `src/tools/bim/commands/doc/promote/promote.py`: exit 1, first failure: `assert False is True` (real assertion failure) - necessity holds.
  - `tests/tools/bim/doc/test_promote.py`: **exit 0, 14 passed** - DISQUALIFYING, same pattern as task 3: old test file has none of the two new raw-source-sha dedup cases, so it passes trivially against the canonical impl.
- Step 14 check: `git status --porcelain` empty, `git rev-parse HEAD` == PRETASK_SHA. Confirmed.
- **DISQUALIFIED** - second occurrence of the same pattern seen in task 3.
