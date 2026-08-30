"""Headless integration coverage for the proposal walkthrough."""

from pathlib import Path

import queue
import write


def test_scripted_walkthrough_writes_keeps_filters_drops_and_resumes_without_gaps(
    tmp_path: Path,
) -> None:
    queue_path = tmp_path / "queue.json"
    store_path = tmp_path / "memory"
    store_path.mkdir()
    proposals = [
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
                "---\n\n"
                f"Original body {number}.\n"
            ),
            "existing_text": None,
        }
        for number in range(1, 6)
    ]

    assert queue.save(proposals, path=queue_path) == 5

    first = queue.next_undecided(path=queue_path)
    assert first is not None
    queue.decide(first["id"], "kept", path=queue_path)
    first_kept = queue.load(path=queue_path)["entries"][0]
    first_memory = write.write_memory(first_kept, store_path=store_path)
    first_pointer = write.append_pointer(store_path=store_path, entry=first_kept)

    second = queue.next_undecided(path=queue_path)
    assert second is not None
    queue.decide(second["id"], "dropped", path=queue_path)

    reloaded = queue.load(path=queue_path)
    assert [entry["decision"] for entry in reloaded["entries"]] == [
        "kept",
        "dropped",
        "undecided",
        "undecided",
        "undecided",
    ]
    assert len({entry["id"] for entry in reloaded["entries"]}) == 5

    queue.advance(path=queue_path)
    third = queue.next_undecided(path=queue_path)
    assert third is not None
    assert third["id"] == reloaded["entries"][2]["id"]
    assert third["id"] not in {first["id"], second["id"]}

    edited_file_text = (
        "---\n"
        "name: walkthrough-memory-3\n"
        "description: edited walkthrough proposal three\n"
        "---\n\n"
        "Stub re-emitted body.\n"
    )
    queue.decide(third["id"], "kept", file_text=edited_file_text, path=queue_path)
    third_kept = queue.load(path=queue_path)["entries"][2]
    assert third_kept["file_text"] == edited_file_text
    write.write_memory(third_kept, store_path=store_path)
    write.append_pointer(store_path=store_path, entry=third_kept)

    fourth = queue.next_undecided(path=queue_path)
    assert fourth is not None
    queue.decide(fourth["id"], "dropped", path=queue_path)

    fifth = queue.next_undecided(path=queue_path)
    assert fifth is not None
    queue.decide(fifth["id"], "kept", path=queue_path)
    fifth_kept = queue.load(path=queue_path)["entries"][4]
    write.write_memory(fifth_kept, store_path=store_path)
    write.append_pointer(store_path=store_path, entry=fifth_kept)

    completed = queue.load(path=queue_path)
    assert [entry["decision"] for entry in completed["entries"]] == [
        "kept",
        "dropped",
        "kept",
        "dropped",
        "kept",
    ]
    assert queue.cursor(path=queue_path) == 5

    assert first_memory.read_text() == proposals[0]["file_text"]
    assert first_pointer is not None
    assert first_pointer in (store_path / "MEMORY.md").read_text()
    assert (store_path / "walkthrough-memory-3.md").read_text() == edited_file_text

    assert queue.save(proposals, path=queue_path) == 0
    assert queue.rejected(second["id"], queue.RUBRIC_VERSION, path=queue_path)
    second_pass = queue.load(path=queue_path)
    assert sum(entry["id"] == second["id"] for entry in second_pass["entries"]) == 1
