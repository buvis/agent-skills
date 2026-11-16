"""The docs quote the SDK pins; they must match pyproject.toml, the one source CI tests."""

import re
from pathlib import Path

SKILL = Path(__file__).resolve().parents[1]
PIN = re.compile(r"\b(mcp|httpx2)(?:\[cli\])?==(\d+(?:\.\d+)*)")


def test_quoted_sdk_pins_match_pyproject():
    pinned = dict(PIN.findall((SKILL / "pyproject.toml").read_text(encoding="utf-8")))
    assert set(pinned) == {"mcp", "httpx2"}
    stale = [
        f"{path.relative_to(SKILL)}: {name}=={version} (pyproject: {pinned[name]})"
        for path in sorted(SKILL.rglob("*"))
        if path.suffix in {".md", ".py"}
        and not any(part.startswith(".") for part in path.relative_to(SKILL).parts)
        for name, version in PIN.findall(path.read_text(encoding="utf-8"))
        if version != pinned[name]
    ]
    assert not stale, "docs drifted from pyproject pins:\n" + "\n".join(stale)
