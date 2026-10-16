"""Pieces shared by the survey test modules.

`test_survey.py`, `test_survey_scan.py` and `test_survey_brief.py` are three
parts of one split. Plain helpers and constants they share live here rather
than in any one module, because a test module is not a fixture library. The
`git_repo` fixture lives in `conftest.py` beside them.
"""

import subprocess
from pathlib import Path

import pytest

import run


# tree-sitter is an optional dependency. Everything the skill itself owns is
# tested either way; the two cases below assert on what the parser resolves
# (an indented method as kind 'method'), which the regex fallback cannot see.
requires_tree_sitter = pytest.mark.skipif(
    run.try_import_tree_sitter() is None,
    reason="needs the optional tree_sitter_language_pack",
)


PINNED_KINDS = {"function", "class", "method", "type", "interface"}


def _init_git_repo(path: Path) -> str:
    """Init a git repo with one commit; return HEAD sha."""
    subprocess.run(["git", "init"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.email", "t@t.com"], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "T"], cwd=path, check=True, capture_output=True)
    (path / "main.py").write_text("def hello():\n    return 'hello'\n")
    subprocess.run(["git", "add", "."], cwd=path, check=True, capture_output=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=path, check=True, capture_output=True)
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=path, check=True, capture_output=True, text=True
    )
    return result.stdout.strip()


def _section_body(content: str, header: str) -> str:
    """Return the text between `header` and the next ## heading (or EOF)."""
    start = content.find(f"## {header}")
    assert start != -1, f"Section '## {header}' not found in the brief"
    after = content.find("\n## ", start + 1)
    return content[start: after] if after != -1 else content[start:]
