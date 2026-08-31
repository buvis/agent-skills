"""Headless integration coverage for the proposal walkthrough."""

from pathlib import Path

import docket
import proposal
import write

import pytest


_PROPOSALS = [
    {
        "name": f"walkthrough-memory-{number}",
        "kind": "new",
        "transcript": "sessions/walkthrough.jsonl",
        "line_no": number,
        "evidence_text": f"evidence for proposal {number}",
        "file_text": (
            "---\n"
            f"name: walkthrough-memory-{number}\n"
            f"description: walkthrough proposal {number}\n"
            "metadata:\n"
            "  type: project\n"
            "---\n\n"
            f"Original body {number}.\n"
        ),
        "existing_text": None,
    }
    for number in range(1, 6)
]

_EDITED_FILE_TEXT = (
    "---\n"
    "name: walkthrough-memory-3\n"
    "description: edited walkthrough proposal three\n"
    "metadata:\n"
    "  type: project\n"
    "---\n\n"
    "Stub re-emitted body.\n"
)


def _next_entry(queue_path: Path) -> dict:
    entry = docket.next_undecided(path=queue_path)
    assert entry is not None
    return entry


def _keep_and_publish(
    entry: dict,
    queue_path: Path,
    store_path: Path,
    file_text: str | None = None,
) -> tuple[dict, Path, str | None]:
    docket.decide(entry["id"], "kept", file_text=file_text, path=queue_path)
    kept = next(
        e
        for e in reversed(docket.load(path=queue_path)["entries"])
        if e["id"] == entry["id"]
    )
    memory = write.write_memory(kept, store_path=store_path)
    pointer = write.append_pointer(store_path=store_path, entry=kept)
    return kept, memory, pointer


def test_scripted_walkthrough_writes_keeps_filters_drops_and_resumes_without_gaps(
    tmp_path: Path,
) -> None:
    queue_path = tmp_path / "queue.json"
    store_path = tmp_path / "memory"
    store_path.mkdir()
    assert docket.save(_PROPOSALS, path=queue_path) == 5
    first = _next_entry(queue_path)
    _, first_memory, first_pointer = _keep_and_publish(
        first, queue_path, store_path
    )
    second = _next_entry(queue_path)
    docket.decide(second["id"], "dropped", path=queue_path)
    reloaded = docket.load(path=queue_path)
    assert [entry["decision"] for entry in reloaded["entries"]] == [
        "kept", "dropped", "undecided",
        "undecided", "undecided",
    ]
    assert len({entry["id"] for entry in reloaded["entries"]}) == 5
    docket.advance(path=queue_path)
    third = _next_entry(queue_path)
    assert third["id"] == reloaded["entries"][2]["id"]
    assert third["id"] not in {first["id"], second["id"]}
    third_kept, _, _ = _keep_and_publish(
        third, queue_path, store_path, file_text=_EDITED_FILE_TEXT
    )
    assert third_kept["file_text"] == _EDITED_FILE_TEXT
    fourth = _next_entry(queue_path)
    docket.decide(fourth["id"], "dropped", path=queue_path)
    fifth = _next_entry(queue_path)
    _keep_and_publish(fifth, queue_path, store_path)
    completed = docket.load(path=queue_path)
    assert [entry["decision"] for entry in completed["entries"]] == [
        "kept", "dropped", "kept", "dropped", "kept",
    ]
    assert docket.cursor(path=queue_path) == 5
    assert first_memory.read_text() == _PROPOSALS[0]["file_text"]
    assert first_pointer is not None
    assert first_pointer in (store_path / "MEMORY.md").read_text()
    assert (store_path / "walkthrough-memory-3.md").read_text() == _EDITED_FILE_TEXT
    assert docket.save(_PROPOSALS, path=queue_path) == 0
    assert docket.rejected(second["id"], docket.RUBRIC_VERSION, path=queue_path)
    second_pass = docket.load(path=queue_path)
    assert sum(entry["id"] == second["id"] for entry in second_pass["entries"]) == 1


def test_edit_path_rejects_a_re_emitted_file_failing_the_frontmatter_contract_and_leaves_the_entry_undecided(
    tmp_path: Path,
) -> None:
    queue_path = tmp_path / "queue.json"
    store_path = tmp_path / "memory"
    store_path.mkdir()
    docket.save(_PROPOSALS, path=queue_path)
    entry = _next_entry(queue_path)

    invalid_file_text = (
        "---\n"
        "name: walkthrough-memory-1\n"
        "description: edited but missing the metadata block\n"
        "---\n\n"
        "Stub re-emitted body.\n"
    )
    bad_proposal = proposal.Proposal(
        file_text=invalid_file_text,
        evidence=proposal.Evidence(
            transcript=Path(entry["transcript"]),
            line_no=entry["line_no"],
            text=entry["evidence_text"],
        ),
    )

    with pytest.raises(proposal.ProposalError):
        proposal.validate(bad_proposal)

    assert list(store_path.iterdir()) == []
    reloaded = docket.load(path=queue_path)
    kept = next(e for e in reloaded["entries"] if e["id"] == entry["id"])
    assert kept["decision"] == "undecided"
