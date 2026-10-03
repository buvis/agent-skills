### Task 3 - repoint-zettel-save (gems)

- Template: `/tmp/qwen-eval-00010/3-repoint-zettel-save-tpl/`
- PRETASK_SHA: `079ccaedba67c1efa9e947d8f7d5c8a84a8a5af6`
- `mise trust <tpl>/.mise.toml`: exit 0
- `mise env -C <tpl> -s bash`: exit 0
- Warmup: `uv --directory <tpl> sync --all-extras --group test` (plain `uv sync` alone installs the `dev` dependency-group only; the `test` group, which carries `pytest` itself, is non-default in this repo's `pyproject.toml` and must be requested explicitly, or `uv run pytest` falls back to an ephemeral uv resolution that pulled an incompatible `pydantic-core` from outside the project venv). Exit 0.
- Necessity (2 Required files, clone rule; raw test: `uv --directory <clone> run pytest tests/lib/zettel/infrastructure/persistence/test_markdown_zettel_repository_writer.py -q`):
  - `src/lib/.../markdown_zettel_repository.py`: exit 1, first failure: `Failed: DID NOT RAISE OSError` (test-framework assertion failure) - necessity holds.
  - `tests/lib/.../test_markdown_zettel_repository_writer.py`: **exit 0, 6 passed** - DISQUALIFYING. Leaving the test file at pre-task content (6 happy-path tests) while the impl is canonical still passes, because the impl change is backward-compatible on the happy path and the old suite never exercises the new failure-injection case. Per the necessity rule this is a zero exit, so task 3 is single-file equivalent on its test half and must be substituted per the prep-failure rule.
- Step 14 check: `git status --porcelain` empty, `git rev-parse HEAD` == PRETASK_SHA. Confirmed.
- **DISQUALIFIED** - see orchestrator note in final report re: substitution (only one vetted alternate, alt1, exists; see whether other impl+test tasks show the same pattern before deciding).
