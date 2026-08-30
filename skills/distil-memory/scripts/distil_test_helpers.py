"""Pieces shared by the distil test modules.

`test_distil.py` and `test_distil_discard.py` are two halves of one split, so
they need the same slice builder and the same malformed-file fixture. They live
here rather than in either module because a test module is not a fixture
library: importing one test module from another is the shape the funnel family
removed when `funnel_test_helpers.py` was created.
"""

from pathlib import Path

import funnel

MISSING_DESCRIPTION = "---\nname: missing-description\nmetadata:\n  type: project\n---\n\nbody\n"


def make_slice(text, marker="measured", line_no=1):
    """One Slice standing in for a transcript hit, with a stable source path."""
    return funnel.Slice(
        text=text, transcript=Path("transcripts/session.jsonl"), line_no=line_no, marker=marker
    )
