"""Tracked project-management documents carry no personal home prefix.

This repository is public. A path such as `/Users/<someone>/...`,
`/home/<someone>/...` or `C:\\Users\\<someone>\\...` names a person and a
machine, so documents write `~/...` or a repository-relative path instead.
Generic placeholders (`/Users/you/...`, `/Users/.../`, `<name>` forms) and the
CI runner account stay allowed.
"""

import re
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SCOPE = "docs/dev/project-management"

# Excluded until PRD 00154's autocodex host-writer task lands. The autocodex
# driver and adapter under ~/.config/autocodex/ (outside this repository) still
# write absolute paths into the loop state and hash-pinned review evidence under
# this directory, and into the receipt lines of review files below. Scrubbing
# them here would break the adapter's receipt checks, which accept only the
# absolute form today. Drop both exclusions once the host writers emit
# repo-relative paths and the readers accept both forms.
EXCLUDED_DIRECTORY = f"{SCOPE}/autopilot/"
HOST_WRITER_RECEIPT_LINE = re.compile(r"^autocodex_[a-z]+_[a-z]+_receipt: ")

HOME_PREFIX = re.compile(
    r"(?<![\w.~-])(?:/Users/|/home/|[A-Za-z]:\\{1,2}Users\\{1,2})"
    r"(?P<name>[^/\\\s\"'`)\]]+)"
)
GENERIC_NAMES = frozenset({"you", "...", "runneradmin", "RUNNER~1"})


def find_home_prefixes(text: str) -> list[int]:
    """Line numbers in `text` that carry a personal home prefix."""
    hits = []
    for line_no, line in enumerate(text.splitlines(), 1):
        if HOST_WRITER_RECEIPT_LINE.match(line):
            continue
        for match in HOME_PREFIX.finditer(line):
            name = match.group("name")
            if name in GENERIC_NAMES or name.startswith(("<", ".")):
                continue
            hits.append(line_no)
            break
    return hits


def _tracked_documents() -> list[str]:
    listing = subprocess.run(
        ["git", "-C", str(ROOT), "ls-files", "-z", "--", SCOPE],
        capture_output=True,
        check=True,
    )
    paths = [p for p in listing.stdout.decode("utf-8").split("\0") if p]
    return [p for p in paths if not p.startswith(EXCLUDED_DIRECTORY)]


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
        "autocodex_alice_openai_receipt: /Users/jdoe/receipt.json",
    ],
)
def test_find_home_prefixes_allows_generic_placeholders_and_host_writer_receipts(text):
    assert find_home_prefixes(text) == []
