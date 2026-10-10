"""Tests for docket.py: the queue verbs stay stdlib-only, so importing docket
and running next/decide/cursor never loads the write or proposal modules."""

import subprocess
import sys
from pathlib import Path

import docket

from docket_test_helpers import make_proposal as _proposal

SCRIPTS_DIR = Path(__file__).resolve().parent

_PRELUDE = f"import sys; sys.path.insert(0, {str(SCRIPTS_DIR)!r}); import docket; "
_REPORT_LOADED = "print(sorted(m for m in ('write', 'proposal') if m in sys.modules))"


def _run_in_fresh_interpreter(code):
    return subprocess.run(
        [sys.executable, "-c", _PRELUDE + code],
        cwd=SCRIPTS_DIR,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_importing_docket_does_not_load_write_or_proposal():
    result = _run_in_fresh_interpreter(_REPORT_LOADED)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "[]"


def test_running_next_decide_and_cursor_does_not_load_write_or_proposal(tmp_path):
    queue_path = tmp_path / "q.json"
    docket.save([_proposal(transcript="t.jsonl", line_no=1, name="fact-one")], path=queue_path)
    entry_id = docket.slice_key("t.jsonl", 1)
    code = (
        f"q = {str(queue_path)!r}; "
        "codes = [docket.main(['next', '--queue', q]), "
        f"docket.main(['decide', {entry_id!r}, 'kept', '--queue', q]), "
        "docket.main(['cursor', '--queue', q])]; "
        "print(codes); "
        f"{_REPORT_LOADED}"
    )

    result = _run_in_fresh_interpreter(code)

    assert result.returncode == 0, result.stderr
    assert result.stdout.strip().splitlines()[-2:] == ["[0, 0, 0]", "[]"]
