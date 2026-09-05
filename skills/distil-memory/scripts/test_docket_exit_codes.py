"""Tests for docket.py: main()'s exit codes when the queue cannot be read."""

import json

import docket

import pytest


def _proposal(transcript="t.jsonl", line_no=1, name=None, file_text=None):
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


# main() exit codes for an unreadable queue. Exit 1 means "nothing left to
# decide" (drained or capped), exit 2 means "the queue could not be read", so a
# caller polling `next` can tell a finished walkthrough from a broken one.
#
# Two techniques below, on purpose. `next` (the primary caller) and `decide`
# (the only subcommand that also has an exit 1 of its own) go through a REAL
# corrupt file on disk, over every corruption shape load() recognises, so the
# unmocked path is proved end to end and no single byte string can be
# special-cased. `cursor`, `start`, `save` and one extra `decide` case make
# load() raise a QueueError carrying a sentinel string this file could not
# otherwise produce, which pins the reported message to the exception that was
# actually raised rather than to one the test (or the implementation) could
# reconstruct from the queue file.


_CORRUPT_QUEUE_SHAPES = {
    "truncated-json": '{"cursor": 0, "entries": [',
    "truncated-json-trailing-newline": '{"cursor": 0, "entries": [\n',
    "empty-file": "",
    "top-level-list": "[]",
    "missing-entries-key": '{"cursor": 0}',
    "non-dict-entry": '{"cursor": 0, "entries": ["not-a-dict"]}',
}


def _write_the_working_directory_queue_bytes(tmp_path, data):
    queue_file = tmp_path / "dev" / "local" / "audit-results" / "distil-memory-queue.json"
    queue_file.parent.mkdir(parents=True, exist_ok=True)
    queue_file.write_bytes(data)
    return queue_file


def _corrupt_the_working_directory_queue(tmp_path, text):
    return _write_the_working_directory_queue_bytes(tmp_path, text.encode())


def _corrupt_queue_error_message():
    try:
        docket.load()
    except docket.QueueError as exc:
        return str(exc)
    pytest.fail("expected docket.load to raise QueueError for a corrupt queue file")


def _load_raising(message):
    """A stand-in for docket.load() that fails the way a corrupt queue file
    makes it fail, with a message no other code path could invent."""

    def _explode(path=None):
        raise docket.QueueError(message)

    return _explode


@pytest.mark.parametrize(
    "corrupt_text", list(_CORRUPT_QUEUE_SHAPES.values()), ids=list(_CORRUPT_QUEUE_SHAPES)
)
def test_main_next_returns_two_and_reports_the_error_when_the_queue_is_unreadable(
    corrupt_text, tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    _corrupt_the_working_directory_queue(tmp_path, corrupt_text)
    expected_message = _corrupt_queue_error_message()

    exit_code = docket.main(["next"])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert expected_message in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


def test_main_cursor_returns_two_and_reports_the_error_when_the_queue_is_unreadable(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    sentinel = "cursor-cannot-read-the-queue-9f3c1a"
    monkeypatch.setattr(docket, "load", _load_raising(sentinel))

    exit_code = docket.main(["cursor"])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert sentinel in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


def test_main_start_returns_two_and_reports_the_error_when_the_queue_is_unreadable(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    sentinel = "start-cannot-read-the-queue-2b7e40"
    monkeypatch.setattr(docket, "load", _load_raising(sentinel))

    exit_code = docket.main(["start"])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert sentinel in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


def test_main_save_returns_two_and_reports_the_error_when_the_queue_is_unreadable(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    proposals_dir = tmp_path / "proposals"
    proposals_dir.mkdir()
    (proposals_dir / "widget-fact.md").write_text("---\nname: widget-fact\n---\n\nBody text.\n")
    record = {
        "name": "widget-fact",
        "kind": "new",
        "transcript": "t.jsonl",
        "line_no": 7,
        "evidence_text": "evidence for widget",
        "existing_text": None,
        "file": "widget-fact.md",
    }
    (proposals_dir / "proposals.json").write_text(json.dumps([record]))
    sentinel = "save-cannot-read-the-queue-c05d86"
    monkeypatch.setattr(docket, "load", _load_raising(sentinel))

    exit_code = docket.main(["save", "--proposals-dir", str(proposals_dir)])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert sentinel in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


_DECIDE_UNREADABLE_QUEUE_CASES = {
    **{
        f"corrupt-file-{shape}": ("corrupt-file", text)
        for shape, text in _CORRUPT_QUEUE_SHAPES.items()
    },
    # A sentinel worded like a refused decision ("no undecided entry with id
    # ..." is what a refusal reads like). The split between exit 1 and exit 2
    # has to follow which call failed, not which words the message happens to
    # carry, so this must still be exit 2.
    "load-raises-a-refusal-shaped-message": (
        "load-raises",
        "decide-entry-lookup-failed-6a41ef",
    ),
}


@pytest.mark.parametrize(
    "failure,payload",
    list(_DECIDE_UNREADABLE_QUEUE_CASES.values()),
    ids=list(_DECIDE_UNREADABLE_QUEUE_CASES),
)
def test_main_decide_returns_two_rather_than_one_when_the_queue_is_unreadable(
    failure, payload, tmp_path, monkeypatch, capsys
):
    # A refused decision against a readable queue stays exit 1 (tested above);
    # a queue that cannot be read at all is a different failure and must not be
    # reported as one more refusal, whatever its message says.
    monkeypatch.chdir(tmp_path)
    if failure == "corrupt-file":
        _corrupt_the_working_directory_queue(tmp_path, payload)
        expected_message = _corrupt_queue_error_message()
    else:
        monkeypatch.setattr(docket, "load", _load_raising(payload))
        expected_message = payload

    exit_code = docket.main(["decide", docket.slice_key("t.jsonl", 1), "kept"])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert expected_message in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


def test_main_decide_does_not_report_a_missing_file_argument_as_an_unreadable_queue(
    tmp_path, monkeypatch
):
    # Exit 2 means "the queue could not be read", not "something went wrong":
    # a --file path that does not exist has nothing to do with the queue, so it
    # must not be swallowed into that exit code.
    monkeypatch.chdir(tmp_path)
    docket.save([_proposal(transcript="t.jsonl", line_no=1)])
    entry_id = docket.slice_key("t.jsonl", 1)

    with pytest.raises(FileNotFoundError):
        docket.main(["decide", entry_id, "kept", "--file", str(tmp_path / "does-not-exist.md")])


def test_main_next_still_returns_one_with_empty_stdout_when_every_entry_is_decided(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    docket.save([_proposal(transcript="t.jsonl", line_no=n) for n in range(1, 3)])
    for n in range(1, 3):
        docket.decide(docket.slice_key("t.jsonl", n), "kept")
    capsys.readouterr()

    exit_code = docket.main(["next"])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""


# Two corruption shapes the queue layer diagnoses wrongly. Both are about how
# the bytes on disk are interpreted, so both go through a real file rather than
# a stand-in load(): a mocked loader would decide the answer the test is asking
# for.


_INVALID_UTF8_QUEUE_BYTES = b'{"cursor": 0, "entries": [\xff\xfe]}'


def test_main_next_returns_two_when_the_queue_file_is_not_valid_utf8(
    tmp_path, monkeypatch, capsys
):
    # Bytes that do not decode leave the queue unreadable, which is exit 2.
    # Exiting 1 with empty stdout would be byte-for-byte "nothing left to
    # decide", so a caller polling `next` would call the sitting finished when
    # in fact it never read a single entry.
    monkeypatch.chdir(tmp_path)
    _write_the_working_directory_queue_bytes(tmp_path, _INVALID_UTF8_QUEUE_BYTES)
    expected_message = _corrupt_queue_error_message()

    exit_code = docket.main(["next"])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert expected_message.strip() != ""
    assert expected_message in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


@pytest.mark.parametrize(
    "read_the_queue", [docket.load, docket.next_undecided], ids=["load", "next_undecided"]
)
def test_the_queue_layer_raises_queue_error_when_the_queue_file_is_not_valid_utf8(
    read_the_queue, tmp_path
):
    # The decoding failure has to be converted at the queue layer, not left to
    # escape as whatever the decoder raises: main() only turns QueueError into
    # exit 2, and only a QueueError carries a reason worth printing.
    queue_file = _write_the_working_directory_queue_bytes(tmp_path, _INVALID_UTF8_QUEUE_BYTES)

    with pytest.raises(docket.QueueError) as raised:
        read_the_queue(path=queue_file)

    assert str(raised.value).strip() != ""


def test_main_next_diagnoses_a_null_queue_payload_as_a_payload_that_is_not_an_object(
    tmp_path, monkeypatch, capsys
):
    # `null` is valid JSON, so the file is not empty: it holds a payload that
    # is not the queue object. Naming it "empty" names the wrong corruption
    # class, and the name on stderr is the entire product of exit 2.
    monkeypatch.chdir(tmp_path)
    queue_file = _corrupt_the_working_directory_queue(tmp_path, "null")
    expected_message = _corrupt_queue_error_message()
    # The queue path is part of the message and carries the test's own name, so
    # drop it before reading the diagnosis: otherwise the path could satisfy
    # these assertions on its own.
    reason = expected_message.replace(str(queue_file), "").lower()

    exit_code = docket.main(["next"])

    assert exit_code == 2
    assert "empty" not in reason
    assert "object" in reason
    captured = capsys.readouterr()
    assert expected_message in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


def test_main_next_still_diagnoses_a_zero_byte_queue_file_as_empty(
    tmp_path, monkeypatch, capsys
):
    # The other half of the pair above: fixing the `null` diagnosis must not be
    # done by dropping the empty-file one. "empty" appears in this message and
    # not in the `null` message, which is what keeps the two distinguishable.
    monkeypatch.chdir(tmp_path)
    queue_file = _corrupt_the_working_directory_queue(tmp_path, "")
    assert queue_file.stat().st_size == 0
    expected_message = _corrupt_queue_error_message()
    reason = expected_message.replace(str(queue_file), "").lower()

    exit_code = docket.main(["next"])

    assert exit_code == 2
    assert "empty" in reason
    captured = capsys.readouterr()
    assert expected_message in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""
