import os
import signal

import pytest

import sweep
from sweep_test_helpers import _is_running, _recorded_pids


@pytest.fixture(autouse=True)
def _clear_resolver_caches():
    sweep.resolve_rg.cache_clear()
    sweep.resolve_ast_grep.cache_clear()
    yield
    sweep.resolve_rg.cache_clear()
    sweep.resolve_ast_grep.cache_clear()


@pytest.fixture
def shim_pid_dir(tmp_path):
    # Kills any shim or grandchild a failing test left behind, so a red run
    # never leaks 10s sleepers.
    pid_dir = tmp_path / "shim-pids"
    pid_dir.mkdir()
    yield pid_dir
    for pid in _recorded_pids(pid_dir, "shim") + _recorded_pids(pid_dir, "grandchild"):
        if _is_running(pid):
            try:
                os.kill(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError):
                pass

