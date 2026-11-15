"""Tracked project-management documents carry no personal home prefix.

This repository is public. A path such as `/Users/<someone>/...`,
`/home/<someone>/...` or `C:\\Users\\<someone>\\...` names a person and a
machine, so documents write `~/...` or a repository-relative path instead.
Generic placeholders (`/Users/you/...`, `/Users/.../`, `<name>` forms) and the
CI runner account stay allowed.

The same prefix also hides in directory names that encode a path by turning
each separator into `-`, such as `~/.claude/projects/-Users-<someone>-git-...`.
"""

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCOPE = "docs/dev/project-management"

HOME_PREFIX = re.compile(
    r"(?<![\w.~-])(?:/Users/|/home/|[A-Za-z]:\\{1,2}Users\\{1,2})"
    r"(?P<name>[^/\\\s\"'`)\]]+)"
)
# A home path with every separator written as `-`. The name ends at the next
# `-`, so a name that itself holds one is still caught by its first part.
ENCODED_HOME_PREFIX = re.compile(r"(?<![\w.~])-(?:Users|home)-(?P<name>\w+)")
GENERIC_NAMES = frozenset({"you", "...", "runneradmin", "RUNNER~1"})


def _is_personal(name: str) -> bool:
    return name not in GENERIC_NAMES and not name.startswith(("<", "."))


def find_home_prefixes(text: str) -> list[int]:
    """Line numbers in `text` that carry a personal home prefix."""
    hits = []
    for line_no, line in enumerate(text.splitlines(), 1):
        names = (
            match.group("name")
            for pattern in (HOME_PREFIX, ENCODED_HOME_PREFIX)
            for match in pattern.finditer(line)
        )
        if any(_is_personal(name) for name in names):
            hits.append(line_no)
    return hits


def _tracked_documents() -> list[str]:
    listing = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z", "--", SCOPE],
        capture_output=True,
        check=True,
    )
    return [p for p in listing.stdout.decode("utf-8").split("\0") if p]


def test_tracked_project_management_documents_carry_no_personal_home_prefix():
    documents = _tracked_documents()
    assert documents, f"git ls-files found nothing under {SCOPE}"
    offenders = []
    for relative in documents:
        text = (ROOT / relative).read_bytes().decode("utf-8", errors="replace")
        offenders.extend(f"{relative}:{line_no}" for line_no in find_home_prefixes(text))
    # Only the relative path and line are reported, never the matching text.
    assert offenders == []


@pytest.mark.parametrize(
    "text",
    [
        "see /Users/janedoe/notes.md",
        "cwd='/home/jdoe/project'",
        "file:///Users/jdoe/x",
        "C:\\Users\\jdoe\\AppData",
        '{"path": "C:\\\\Users\\\\jdoe\\\\x"}',
        "~/.claude/projects/-Users-jdoe-git-src-example/session.jsonl",
        "/private/tmp/claude-501/-Users-jdoe/scratchpad/x.txt",
        "`-home-jdoe-project`",
        "projects/C--Users-jdoe-project",
        "autocodex_alice_openai_receipt: /Users/jdoe/receipt.json",
    ],
)
def test_find_home_prefixes_flags_a_personal_prefix_from_any_platform(text):
    assert find_home_prefixes(text) == [1]


@pytest.mark.parametrize(
    "text",
    [
        "write examples as /Users/you/project",
        "a path such as /Users/.../x",
        "the 8.3 form C:\\Users\\RUNNER~1\\AppData",
        "`<S>/home/.config/gita/repos.csv`",
        "repo github.com/buvis/home/.config/x",
        "~/git/src/github.com/example/repo",
        "~/.claude/projects/-Users-you-git-src-example/session.jsonl",
        "`~/.claude/projects/-Users-<name>-git-...`",
        "a stay-at-home-office day, and the take-home-jdoe exam",
    ],
)
def test_find_home_prefixes_allows_generic_placeholders(text):
    assert find_home_prefixes(text) == []
