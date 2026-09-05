"""Regression tests for build.py's payload injection and output placement.

Both cases were found by an agoge run on 2026-08-31. The tokenizer-injection
case is fixed (PRD 00011); the --out/--dir default case is fixed (PRD 00013).

Run: python3 -m pytest test_build_page.py -q
"""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

# Loaded by path under a unique name rather than via sys.path: the repo carries
# a second, unrelated scripts/build.py under skills/debrief-meeting, and a plain
# `import build` would let whichever suite ran first win in sys.modules.
_spec = importlib.util.spec_from_file_location(
    "brief_portfolio_build", Path(__file__).parent / "build.py"
)
build = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build)


def _payload_of(page: str) -> str:
    """The exact text build.py substituted for the template's placeholder."""
    head, tail = build.TEMPLATE.read_text().split(build.PLACEHOLDER)
    assert page.startswith(head) and page.endswith(tail)
    return page[len(head) : len(page) - len(tail)]


def _workdir(tmp_path: Path, data: dict) -> Path:
    workdir = tmp_path / "work"
    workdir.mkdir()
    (workdir / "data.json").write_text(json.dumps(data))
    return workdir


def test_no_collected_text_can_reach_the_html_tokenizer(tmp_path, monkeypatch):
    workdir = _workdir(
        tmp_path,
        {"repos": [{"owner": "o", "name": "n", "org": "o", "title": "benign <!--<script> tail"}]},
    )
    out = tmp_path / "page.html"
    monkeypatch.setattr(sys, "argv", ["build.py", "--dir", str(workdir), "--out", str(out)])

    build.main()

    assert "<" not in _payload_of(out.read_text())


def test_dir_without_out_writes_the_page_beside_its_own_inputs(tmp_path, monkeypatch):
    workdir = _workdir(tmp_path, {"repos": []})
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(sys, "argv", ["build.py", "--dir", str(workdir)])

    build.main()

    assert (workdir / "portfolio-brief.html").is_file()
    assert not (home / ".local/share/agents/portfolio-brief/portfolio-brief.html").exists()


def test_no_flags_writes_the_home_default(tmp_path, monkeypatch):
    home = tmp_path / "home"
    workdir = home / ".local/share/agents/portfolio-brief"
    workdir.mkdir(parents=True)
    (workdir / "data.json").write_text(json.dumps({"repos": []}))
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(sys, "argv", ["build.py"])

    build.main()

    assert (home / ".local/share/agents/portfolio-brief/portfolio-brief.html").is_file()


# Found by an agoge run on 2026-09-05. Each fails against the code as it stands,
# so the strict xfail is the executable record of the defect: fix the defect and
# the marker goes stale, turning the suite red to say "delete me".


@pytest.mark.xfail(
    strict=True,
    raises=json.JSONDecodeError,
    reason="agoge 2026-09-05: build.py json.loads every history.jsonl line unguarded, so one "
    "torn append from a killed collect run kills every later build with a traceback, and "
    "SKILL.md tells the user never to delete that file",
)
def test_a_torn_history_line_does_not_abort_the_build(tmp_path, monkeypatch):
    workdir = _workdir(tmp_path, {"repos": []})
    (workdir / "history.jsonl").write_text(
        '{"at": "2026-09-04T00:00:00+00:00", "skipped": 0, "repos": {}}\n{"at":'
    )
    out = tmp_path / "page.html"
    monkeypatch.setattr(sys, "argv", ["build.py", "--dir", str(workdir), "--out", str(out)])

    build.main()

    assert out.is_file()


@pytest.mark.xfail(
    strict=True,
    raises=json.JSONDecodeError,
    reason="agoge 2026-09-05: a truncated data.json reaches json.loads unguarded, so the "
    "user sees a traceback instead of an exit message naming the file",
)
def test_a_truncated_data_json_exits_with_a_message_naming_the_file(tmp_path, monkeypatch):
    workdir = tmp_path / "work"
    workdir.mkdir()
    (workdir / "data.json").write_text('{"repos": [{"owner": "o", "name": ')
    monkeypatch.setattr(
        sys, "argv", ["build.py", "--dir", str(workdir), "--out", str(tmp_path / "page.html")]
    )

    with pytest.raises(SystemExit) as exc:
        build.main()

    assert "data.json" in str(exc.value)
