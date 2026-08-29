import pytest

import sweep


@pytest.fixture(autouse=True)
def _clear_resolver_caches():
    sweep.resolve_rg.cache_clear()
    sweep.resolve_ast_grep.cache_clear()
    yield
    sweep.resolve_rg.cache_clear()
    sweep.resolve_ast_grep.cache_clear()

