"""Pieces shared by the docket test modules.

`test_docket.py` and `test_docket_cli.py` are two halves of one split, so
they need the same proposal builder. It lives here rather than in either
module because a test module is not a fixture library: importing one test
module from another is the shape the funnel family removed when
`funnel_test_helpers.py` was created.
"""


def make_proposal(transcript="t.jsonl", line_no=1, name=None, file_text=None):
    label = name or f"name-{line_no}"
    return {
        "name": label,
        "kind": "new",
        "transcript": transcript,
        "line_no": line_no,
        "evidence_text": f"evidence for line {line_no}",
        "file_text": file_text or f"file text for {label}",
        "existing_text": None,
    }
