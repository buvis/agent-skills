"""Tests for docket.py: main()'s exit codes when the queue cannot be read."""

import json
import subprocess
import sys

import docket

import pytest


def _proposal(line_no):
    label = f"name-{line_no}"
    return {
        "name": label,
        "kind": "new",
        "transcript": "t.jsonl",
        "line_no": line_no,
        "evidence_text": f"evidence for line {line_no}",
        "file_text": f"file text for {label}",
        "existing_text": None,
    }


# main() exit codes for an unreadable queue. Exit 1 means "nothing left to
# decide" (drained or capped), exit 2 means "the queue could not be read", so a
# caller polling `next` can tell a finished walkthrough from a broken one.
#
# Two techniques below, on purpose. `next` (the primary caller) goes through a
# REAL corrupt file on disk, over every corruption shape load() recognises, so
# the unmocked path is proved end to end and no single byte string can be
# special-cased. `cursor`, `start`, `save`, and `decide`'s refusal-shaped case
# make load() raise a QueueError carrying a sentinel string this file could not
# otherwise produce, which pins the reported message to the exception that was
# actually raised rather than to one the test (or the implementation) could
# reconstruct from the queue file. `decide` (the only other subcommand with an
# exit 1 of its own) also gets one real corrupt file, to prove its own
# real-file path shares `next`'s unreadable-queue handling without re-sweeping
# every shape `next` already covers.


_CORRUPT_QUEUE_SHAPES = {
    "truncated-json": '{"cursor": 0, "entries": [',
    "truncated-json-trailing-newline": '{"cursor": 0, "entries": [\n',
    "empty-file": "",
    "top-level-list": "[]",
    "missing-entries-key": '{"cursor": 0}',
    "non-list-entries": '{"cursor": 0, "entries": {}}',
    "non-dict-entry": '{"cursor": 0, "entries": ["not-a-dict"]}',
}


def _the_working_directory_queue_path(tmp_path):
    return tmp_path / "docs" / "dev" / "project-management" / "audit-results" / "distil-memory-queue.json"


def _write_the_working_directory_queue_bytes(tmp_path, data):
    queue_file = _the_working_directory_queue_path(tmp_path)
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


# What each corruption class has to SAY, written out rather than asked for.
# The test below also compares stderr against whatever load() itself raised, and
# that comparison alone would be satisfied for all seven shapes at once by a
# load() that answered every corruption with one blanket sentence - the
# implementation acting as its own oracle. Naming the words here is what keeps
# the classes distinguishable to whoever reads stderr. "entries is missing" and
# "entries is present but not a list" are deliberately one class, and share
# their wording.
_CORRUPT_QUEUE_DIAGNOSTICS = {
    "truncated-json": "cannot read the review queue",
    "truncated-json-trailing-newline": "cannot read the review queue",
    "empty-file": "file is empty",
    "top-level-list": "expected a JSON object (dict), not a list",
    "missing-entries-key": "entries must be a list",
    "non-list-entries": "entries must be a list",
    "non-dict-entry": "entries must contain only dict entries",
}


@pytest.mark.parametrize("shape", list(_CORRUPT_QUEUE_SHAPES), ids=list(_CORRUPT_QUEUE_SHAPES))
def test_main_next_returns_two_and_reports_the_error_when_the_queue_is_unreadable(
    shape, tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    _corrupt_the_working_directory_queue(tmp_path, _CORRUPT_QUEUE_SHAPES[shape])
    expected_message = _corrupt_queue_error_message()

    exit_code = docket.main(["next"])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert expected_message in captured.err
    assert _CORRUPT_QUEUE_DIAGNOSTICS[shape] in captured.err
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


def test_main_decide_returns_two_rather_than_one_when_the_queue_file_is_corrupt(
    tmp_path, monkeypatch, capsys
):
    # A refused decision against a readable queue stays exit 1 (tested above);
    # a queue that cannot be read at all is a different failure and must not be
    # reported as one more refusal, whatever its message says. `next`'s
    # parametrized test above already sweeps every corruption shape load()
    # recognises; this proves decide's own real-file path shares that same
    # unreadable-queue handling.
    monkeypatch.chdir(tmp_path)
    _corrupt_the_working_directory_queue(tmp_path, _CORRUPT_QUEUE_SHAPES["empty-file"])
    expected_message = _corrupt_queue_error_message()

    exit_code = docket.main(["decide", docket.slice_key("t.jsonl", 1), "kept"])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert expected_message in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


def test_main_decide_returns_two_rather_than_one_for_a_refusal_shaped_message(
    tmp_path, monkeypatch, capsys
):
    # A sentinel worded like a refused decision ("no undecided entry with id
    # ..." is what a refusal reads like). The split between exit 1 and exit 2
    # has to follow which call failed, not which words the message happens to
    # carry, so this must still be exit 2.
    monkeypatch.chdir(tmp_path)
    sentinel = "decide-entry-lookup-failed-6a41ef"
    monkeypatch.setattr(docket, "load", _load_raising(sentinel))

    exit_code = docket.main(["decide", docket.slice_key("t.jsonl", 1), "kept"])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert sentinel in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


def test_main_decide_does_not_report_a_missing_file_argument_as_an_unreadable_queue(
    tmp_path, monkeypatch, capsys
):
    # Exit 2 means "the queue could not be read", not "something went wrong":
    # a --file path that does not exist has nothing to do with the queue, so it
    # must not be swallowed into that exit code. It is answered on its own
    # terms instead - the refusal, exit 1, with the fault on stderr.
    monkeypatch.chdir(tmp_path)
    docket.save([_proposal(1)])
    entry_id = docket.slice_key("t.jsonl", 1)

    exit_code = docket.main(
        ["decide", entry_id, "kept", "--file", str(tmp_path / "does-not-exist.md")]
    )

    assert exit_code == 1
    assert exit_code != 2
    assert capsys.readouterr().err.strip() != ""


def test_main_decide_reads_the_queue_once_so_no_later_read_can_be_taken_for_a_refusal(
    tmp_path, monkeypatch, capsys
):
    # main() used to read the queue as a gate, throw the result away, and let
    # decide() read it again. A QueueError from that second read landed in the
    # inner handler and came back as exit 1 - "the decision was refused" - for a
    # queue that had merely become unreadable between the two reads. Reading
    # once closes the window instead of guarding it: there is no second read
    # left to fail, and the count is what proves it rather than a message.
    monkeypatch.chdir(tmp_path)
    docket.save([_proposal(1)])
    real_load = docket.load
    reads = []

    def _load_once_then_refuse_to_read(path=None):
        reads.append(path)
        if len(reads) > 1:
            raise docket.QueueError("the queue stopped being readable after the gate read")
        return real_load(path=path)

    monkeypatch.setattr(docket, "load", _load_once_then_refuse_to_read)

    exit_code = docket.main(["decide", docket.slice_key("t.jsonl", 1), "kept"])

    assert reads == [None]
    assert exit_code == 0
    assert capsys.readouterr().err == ""


def test_main_next_still_returns_one_with_empty_stdout_when_every_entry_is_decided(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    docket.save([_proposal(n) for n in range(1, 3)])
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
#
# Both are also swept over a family of payloads rather than one literal, for the
# same reason the corruption shapes above are: recognising one byte string, or
# one spelling of `null`, is not the behaviour being asked for. The last
# undecodable payload is built from the bytes save() wrote during the run, so it
# cannot be enumerated by an implementation at all.


def _reason_without_the_queue_path(message, queue_file):
    """The diagnosis with the queue path cut out. The path is built from the
    test's own name, so left in it could satisfy an assertion about the
    diagnosis on its own."""
    return message.replace(str(queue_file), "").lower()


def _break_one_byte_of_a_saved_queue(tmp_path):
    """Undecodable bytes that are not knowable when this test is written: let
    save() write a real queue, then knock one byte of its output out of UTF-8."""
    docket.save([_proposal(1)])
    written = _the_working_directory_queue_path(tmp_path).read_bytes()
    return written.replace(b"}", b"\xff}", 1)


_INVALID_UTF8_QUEUE_PAYLOADS = {
    "an-entries-list-of-raw-bytes": lambda tmp_path: b'{"cursor": 0, "entries": [\xff\xfe]}',
    "a-lone-undecodable-byte": lambda tmp_path: b"\xff",
    "a-stray-continuation-byte": lambda tmp_path: b"\x80",
    "a-truncated-multibyte-sequence": lambda tmp_path: b'{"cursor": 0, "entries": [\xc3\x28]}',
    "a-queue-encoded-as-latin1": lambda tmp_path: '{"cursor": 0, "note": "caf\xe9"}'.encode(
        "latin-1"
    ),
    "a-saved-queue-with-one-byte-knocked-out": _break_one_byte_of_a_saved_queue,
}


@pytest.mark.parametrize(
    "build_payload",
    list(_INVALID_UTF8_QUEUE_PAYLOADS.values()),
    ids=list(_INVALID_UTF8_QUEUE_PAYLOADS),
)
def test_main_next_returns_two_when_the_queue_file_is_not_valid_utf8(
    build_payload, tmp_path, monkeypatch, capsys
):
    # Bytes that do not decode leave the queue unreadable, which is exit 2.
    # Exiting 1 with empty stdout would be byte-for-byte "nothing left to
    # decide", so a caller polling `next` would call the sitting finished when
    # in fact it never read a single entry.
    monkeypatch.chdir(tmp_path)
    queue_file = _write_the_working_directory_queue_bytes(tmp_path, build_payload(tmp_path))
    capsys.readouterr()
    expected_message = _corrupt_queue_error_message()

    exit_code = docket.main(["next"])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert str(queue_file) in expected_message
    assert expected_message in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


@pytest.mark.parametrize(
    "read_the_queue", [docket.load, docket.next_undecided], ids=["load", "next_undecided"]
)
@pytest.mark.parametrize(
    "build_payload",
    list(_INVALID_UTF8_QUEUE_PAYLOADS.values()),
    ids=list(_INVALID_UTF8_QUEUE_PAYLOADS),
)
def test_the_queue_layer_raises_queue_error_when_the_queue_file_is_not_valid_utf8(
    build_payload, read_the_queue, tmp_path, monkeypatch
):
    # The decoding failure has to be converted at the queue layer, not left to
    # escape as whatever the decoder raises: main() only turns QueueError into
    # exit 2, and only a QueueError carries a reason worth printing. "A reason"
    # means one a reader can act on, so it has to name the file that could not
    # be read and the fact that it could not be decoded.
    monkeypatch.chdir(tmp_path)
    queue_file = _write_the_working_directory_queue_bytes(tmp_path, build_payload(tmp_path))

    with pytest.raises(docket.QueueError) as raised:
        read_the_queue(path=queue_file)

    message = str(raised.value)
    assert str(queue_file) in message
    reason = _reason_without_the_queue_path(message, queue_file)
    assert "utf-8" in reason
    assert "decode" in reason


_NON_OBJECT_QUEUE_PAYLOADS = {
    "null": "null",
    "null-as-an-editor-writes-it": "null\n",
    "null-with-surrounding-space": " null ",
    "true": "true",
    "a-number": "123",
    "a-string": '"a string"',
}


@pytest.mark.parametrize(
    "payload_text",
    list(_NON_OBJECT_QUEUE_PAYLOADS.values()),
    ids=list(_NON_OBJECT_QUEUE_PAYLOADS),
)
def test_main_next_names_a_non_object_queue_payload_rather_than_calling_the_file_empty(
    payload_text, tmp_path, monkeypatch, capsys
):
    # `null` is valid JSON, so the file is not empty: it holds a payload that
    # is not the queue object. Naming it "empty" names the wrong corruption
    # class, and the name on stderr is the entire product of exit 2. The rule is
    # about the payload, not about a spelling, so a trailing newline or a pad of
    # spaces (what a real editor leaves behind) must read the same way.
    monkeypatch.chdir(tmp_path)
    queue_file = _corrupt_the_working_directory_queue(tmp_path, payload_text)
    expected_message = _corrupt_queue_error_message()
    reason = _reason_without_the_queue_path(expected_message, queue_file)

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


# A root/entries-container queue can parse and still be damaged: an entry
# missing "id" or "decision", or a counter ("cursor"/"session_decided") that
# is not an int. load() is supposed to reject these the same way it rejects
# the container-shape corruptions above, but today it only checks the
# container, not the entries or the counters - a command built on load() can
# crash instead (exit 1, indistinguishable from drained/capped) or write the
# damaged queue back out as if it were fine. Every case below is run against
# a REAL queue file on disk, through every command whose happy path reads the
# queue, with otherwise-valid arguments, so the invalid queue is the only
# thing that can make the command fail.
_MALFORMED_ENTRY_AND_COUNTER_QUEUES = {
    "entry-missing-decision": (
        '{"cursor": 0, "entries": [{"id": "t.jsonl:1"}]}',
        "decision",
    ),
    "entry-missing-id": (
        '{"cursor": 0, "entries": [{"decision": "undecided"}]}',
        "id",
    ),
    # Shares the "decision" prefix with the valid key: a check that matches
    # by substring or prefix instead of an exact key would wrongly accept
    # this as having a decision.
    "entry-has-decisions-not-decision": (
        '{"cursor": 0, "entries": [{"id": "t.jsonl:1", "decisions": "undecided"}]}',
        "decision",
    ),
    "cursor-is-a-string": (
        '{"cursor": "0", "entries": []}',
        "cursor",
    ),
    "session-decided-is-a-string": (
        '{"cursor": 0, "entries": [], "session_decided": "0"}',
        "session_decided",
    ),
}


def _assert_rejected_without_mutating(exit_code, captured, queue_file, original_bytes, expected_word):
    assert exit_code == 2
    assert expected_word in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""
    assert queue_file.read_bytes() == original_bytes


@pytest.mark.parametrize(
    "shape", list(_MALFORMED_ENTRY_AND_COUNTER_QUEUES), ids=list(_MALFORMED_ENTRY_AND_COUNTER_QUEUES)
)
def test_main_next_rejects_a_malformed_entry_or_counter_without_touching_the_file(
    shape, tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    text, expected_word = _MALFORMED_ENTRY_AND_COUNTER_QUEUES[shape]
    queue_file = _corrupt_the_working_directory_queue(tmp_path, text)
    original_bytes = queue_file.read_bytes()

    exit_code = docket.main(["next"])

    _assert_rejected_without_mutating(exit_code, capsys.readouterr(), queue_file, original_bytes, expected_word)


@pytest.mark.parametrize(
    "shape", list(_MALFORMED_ENTRY_AND_COUNTER_QUEUES), ids=list(_MALFORMED_ENTRY_AND_COUNTER_QUEUES)
)
def test_main_decide_rejects_a_malformed_entry_or_counter_without_touching_the_file(
    shape, tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    text, expected_word = _MALFORMED_ENTRY_AND_COUNTER_QUEUES[shape]
    queue_file = _corrupt_the_working_directory_queue(tmp_path, text)
    original_bytes = queue_file.read_bytes()

    exit_code = docket.main(["decide", docket.slice_key("t.jsonl", 1), "kept"])

    _assert_rejected_without_mutating(exit_code, capsys.readouterr(), queue_file, original_bytes, expected_word)


@pytest.mark.parametrize(
    "shape", list(_MALFORMED_ENTRY_AND_COUNTER_QUEUES), ids=list(_MALFORMED_ENTRY_AND_COUNTER_QUEUES)
)
def test_main_cursor_rejects_a_malformed_entry_or_counter_without_touching_the_file(
    shape, tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    text, expected_word = _MALFORMED_ENTRY_AND_COUNTER_QUEUES[shape]
    queue_file = _corrupt_the_working_directory_queue(tmp_path, text)
    original_bytes = queue_file.read_bytes()

    exit_code = docket.main(["cursor"])

    _assert_rejected_without_mutating(exit_code, capsys.readouterr(), queue_file, original_bytes, expected_word)


@pytest.mark.parametrize(
    "shape", list(_MALFORMED_ENTRY_AND_COUNTER_QUEUES), ids=list(_MALFORMED_ENTRY_AND_COUNTER_QUEUES)
)
def test_main_start_rejects_a_malformed_entry_or_counter_without_touching_the_file(
    shape, tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    text, expected_word = _MALFORMED_ENTRY_AND_COUNTER_QUEUES[shape]
    queue_file = _corrupt_the_working_directory_queue(tmp_path, text)
    original_bytes = queue_file.read_bytes()

    exit_code = docket.main(["start"])

    _assert_rejected_without_mutating(exit_code, capsys.readouterr(), queue_file, original_bytes, expected_word)


@pytest.mark.parametrize(
    "shape", list(_MALFORMED_ENTRY_AND_COUNTER_QUEUES), ids=list(_MALFORMED_ENTRY_AND_COUNTER_QUEUES)
)
def test_main_save_rejects_a_malformed_entry_or_counter_without_touching_the_file(
    shape, tmp_path, monkeypatch, capsys
):
    # save() reads the existing queue before it appends, so a damaged queue on
    # disk must block the append rather than being overwritten with the
    # merged result of the new proposals and the old damage.
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
    text, expected_word = _MALFORMED_ENTRY_AND_COUNTER_QUEUES[shape]
    queue_file = proposals_dir.parent / "distil-memory-queue.json"
    queue_file.write_text(text)
    original_bytes = queue_file.read_bytes()

    exit_code = docket.main(["save", "--proposals-dir", str(proposals_dir)])

    _assert_rejected_without_mutating(exit_code, capsys.readouterr(), queue_file, original_bytes, expected_word)


@pytest.mark.parametrize(
    "shape", list(_MALFORMED_ENTRY_AND_COUNTER_QUEUES), ids=list(_MALFORMED_ENTRY_AND_COUNTER_QUEUES)
)
def test_main_unpublished_rejects_a_malformed_entry_or_counter_without_touching_the_file(
    shape, tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    text, expected_word = _MALFORMED_ENTRY_AND_COUNTER_QUEUES[shape]
    queue_file = _corrupt_the_working_directory_queue(tmp_path, text)
    original_bytes = queue_file.read_bytes()
    store_dir = tmp_path / "store"

    exit_code = docket.main(["unpublished", "--store", str(store_dir)])

    _assert_rejected_without_mutating(exit_code, capsys.readouterr(), queue_file, original_bytes, expected_word)


def test_main_next_rejects_a_kept_entry_with_a_missing_transcript(
    tmp_path, monkeypatch, capsys
):
    # _check_entry()'s kept/transcript rule used to run only inside
    # unpublished(); every other command went through load() alone and
    # accepted a kept entry with no transcript. next() is one such command.
    monkeypatch.chdir(tmp_path)
    text = json.dumps({"cursor": 0, "entries": [{"id": "t.jsonl:1", "decision": "kept"}]})
    queue_file = _corrupt_the_working_directory_queue(tmp_path, text)
    original_bytes = queue_file.read_bytes()

    exit_code = docket.main(["next"])

    _assert_rejected_without_mutating(exit_code, capsys.readouterr(), queue_file, original_bytes, "transcript")


def test_main_next_rejects_a_malformed_entry_anywhere_in_a_multi_entry_list(
    tmp_path, monkeypatch, capsys
):
    # A check that only inspects the first or last entry (a truncation
    # shortcut) would miss damage sitting in the middle of the list.
    monkeypatch.chdir(tmp_path)
    text = json.dumps(
        {
            "cursor": 0,
            "entries": [
                {"id": "t.jsonl:1", "decision": "kept", "transcript": "t.jsonl"},
                {"id": "t.jsonl:2"},
                {"id": "t.jsonl:3", "decision": "undecided"},
            ],
        }
    )
    queue_file = _corrupt_the_working_directory_queue(tmp_path, text)
    original_bytes = queue_file.read_bytes()

    exit_code = docket.main(["next"])

    _assert_rejected_without_mutating(exit_code, capsys.readouterr(), queue_file, original_bytes, "decision")


def test_main_cursor_accepts_a_queue_with_valid_entries_and_integer_counters(
    tmp_path, monkeypatch, capsys
):
    # The counterpart to the reject-cases above: a queue whose entries and
    # counters are the right shape must still work. Two distinct counter
    # values (not 0/0) so a hardcoded return can't pass by accident.
    monkeypatch.chdir(tmp_path)
    text = json.dumps(
        {
            "cursor": 5,
            "session_decided": 3,
            "entries": [{"id": "t.jsonl:1", "decision": "kept", "transcript": "t.jsonl"}],
        }
    )
    _corrupt_the_working_directory_queue(tmp_path, text)

    exit_code = docket.main(["cursor"])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "5"
    assert captured.err == ""


def test_main_next_accepts_an_empty_entries_list_with_valid_integer_counters(
    tmp_path, monkeypatch, capsys
):
    # An empty entries list is a valid, merely-drained queue, not a malformed
    # one: the per-entry and counter checks must not reject it.
    monkeypatch.chdir(tmp_path)
    text = json.dumps({"cursor": 0, "session_decided": 0, "entries": []})
    _corrupt_the_working_directory_queue(tmp_path, text)

    exit_code = docket.main(["next"])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == ""


def test_main_next_names_the_explicit_queue_path_argument_in_the_diagnostic(
    tmp_path, monkeypatch, capsys
):
    # The --queue argument must actually reach load(): if main() silently fell
    # back to the default working-directory path, the diagnostic would name
    # that path instead of the one passed on the command line.
    monkeypatch.chdir(tmp_path)
    explicit_queue = tmp_path / "elsewhere" / "custom-queue.json"
    explicit_queue.parent.mkdir(parents=True)
    explicit_queue.write_text('{"cursor": 0, "entries": [{"id": "t.jsonl:1"}]}')
    original_bytes = explicit_queue.read_bytes()

    exit_code = docket.main(["next", "--queue", str(explicit_queue)])

    captured = capsys.readouterr()
    assert exit_code == 2
    assert str(explicit_queue) in captured.err
    assert "Traceback" not in captured.err
    assert explicit_queue.read_bytes() == original_bytes


def test_cli_next_returns_two_for_an_entry_without_a_decision(tmp_path):
    # Ported from the agoge strict-xfail regression (branch
    # agoge/authored-tests-2026-10-26): runs docket.py as a real subprocess
    # rather than through docket.main(), so the CLI's own argv/exit-code
    # plumbing is exercised too, not just the in-process call.
    queue_file = tmp_path / "queue.json"
    queue_file.write_text(json.dumps({"entries": [{"id": "a"}]}))

    proc = subprocess.run(
        [sys.executable, docket.__file__, "next", "--queue", str(queue_file)],
        capture_output=True, text=True, check=False,
    )

    assert proc.returncode == 2, proc.stderr
    assert "Traceback" not in proc.stderr
    assert proc.stderr.strip()
    assert proc.stdout == ""
