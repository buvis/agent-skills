"""Regression tests for build.py's payload injection and output placement.

Both cases were found by an agoge run on 2026-08-31 and both fail against the
code as it stands, so the strict xfail is the executable record of the defect:
fix it and the marker goes stale, turning the suite red to say "delete me".

Run: python3 -m pytest test_build.py -q
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


@pytest.mark.xfail(
    strict=True,
    reason="agoge 2026-08-31: the payload escapes '</' only, so '<!--<script>' in any "
    "collected title moves the tokenizer into script-data-double-escaped state and the "
    "template's own closing tag stops closing the block, swallowing <div id=app>",
)
def test_no_collected_text_can_reach_the_html_tokenizer(tmp_path, monkeypatch):
    workdir = _workdir(
        tmp_path,
        {"repos": [{"owner": "o", "name": "n", "org": "o", "title": "benign <!--<script> tail"}]},
    )
    out = tmp_path / "page.html"
    monkeypatch.setattr(sys, "argv", ["build.py", "--dir", str(workdir), "--out", str(out)])

    build.main()

    assert "<" not in _payload_of(out.read_text())


@pytest.mark.xfail(
    strict=True,
    reason="agoge 2026-08-31: --out defaults off the home directory rather than off "
    "--dir, so building from a scratch directory overwrites the real dashboard",
)
def test_dir_without_out_writes_the_page_beside_its_own_inputs(tmp_path, monkeypatch):
    workdir = _workdir(tmp_path, {"repos": []})
    home = tmp_path / "home"
    monkeypatch.setattr(Path, "home", classmethod(lambda cls: home))
    monkeypatch.setattr(sys, "argv", ["build.py", "--dir", str(workdir)])

    build.main()

    assert (workdir / "portfolio-brief.html").is_file()
    assert not (home / ".local/share/agents/portfolio-brief/portfolio-brief.html").exists()
