---
name: python-testing
description: Use when writing, fixing, or reviewing Python tests with pytest. Covers TDD, fixtures, mocking, parametrization, coverage. Triggers on "pytest", "python test", "conftest", "pytest.mark", "parametrize", "pytest fixture", "python mock".
compatibility: "Portable standalone compatibility copy of the strunk plugin skill for agents without that plugin; Claude Code uses the namespaced plugin skill."
---

# Python Testing

TDD: write the failing test (RED), make it pass (GREEN), refactor. One behavior per test. No logic in tests. Coverage target 80%, higher on critical paths.

## Rulings

**Mocking**
- Patch where the name is *used*, not where it's defined: `@patch("myapp.service.requests")`, not `@patch("requests")`.
- `autospec=True` so the mock rejects calls the real API would reject.
- Mock at the boundary (I/O, network, clock). Never mock the thing under test.
- Async: assert with `assert_awaited_once()`, not `assert_called_once()`.

**Fixtures**
- `yield` for teardown; the line after `yield` is the cleanup.
- Default to function scope. Widen to `module`/`session` only for genuinely expensive resources.
- `autouse` hides dependencies — use sparingly; prefer explicit injection.
- `tmp_path` for temp files (auto-cleanup, `Path` API), not `tempfile`.

**Parametrize**
- `@pytest.mark.parametrize` over loops — distinct test IDs, filterable with `-k`.
- Pass `ids=[...]` when params are objects or tuples; pytest already auto-names plain str/int/bool readably.

**Config**
- One config in `pyproject.toml` (`[tool.pytest.ini_options]`), not a separate `pytest.ini`.
- `--strict-markers` so a typo'd marker fails instead of silently passing.
- Register custom markers (`slow`, `integration`).
- Categorise with `@pytest.mark.unit` / `@pytest.mark.integration`, and register them so `--strict-markers` catches a typo.
- Coverage locally: `pytest --cov=src --cov-report=term-missing` — the missing-line report is the point; a bare percentage is not actionable.

**Async (pytest-asyncio)**
- Default mode is `strict`: an async test with no `@pytest.mark.asyncio` is silently not collected. Set `asyncio_mode = "auto"` in `[tool.pytest.ini_options]` to drop the per-test marker.
- Use `@pytest_asyncio.fixture` for async fixtures in strict mode.
