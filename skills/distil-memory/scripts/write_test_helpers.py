"""Pieces shared by the write test modules.

`test_write.py`, `test_write_cli.py` and `test_write_crash_safety.py` are three
parts of one split, so they need the same store fixture and the same file_text
and entry builders. They live here rather than in one of those modules because
a test module is not a fixture library: importing one test module from another
is the shape `funnel_test_helpers.py` and `docket_test_helpers.py` removed.
"""

import proposal

import pytest


def _file_text(name="widget-fact", description="a fact worth keeping", body="Body text."):
    return (
        "---\n"
        f"name: {name}\n"
        f"description: {description}\n"
        "metadata:\n"
        "  type: project\n"
        "---\n\n"
        f"{body}\n"
    )


def _entry(name="widget-fact", kind="new", file_text=None, existing_text=None):
    return {
        "name": name,
        "kind": kind,
        "file_text": file_text if file_text is not None else _file_text(name=name),
        "existing_text": existing_text,
    }


def _parser_message(file_text):
    """The message proposal.parse_frontmatter itself reports for a file_text it refuses."""
    try:
        proposal.parse_frontmatter(file_text)
    except proposal.ProposalError as exc:
        return str(exc)
    pytest.fail(f"expected proposal.parse_frontmatter to reject {file_text!r}")


@pytest.fixture
def store_path(tmp_path):
    return tmp_path / "memory"
