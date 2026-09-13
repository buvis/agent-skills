"""Tests for eval_harness/events.py and engines.py: transcripts and adapters."""
import http.server
import json
import os
import random
import shlex
import shutil
import socket
import subprocess
import sys
import threading
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

import pytest

import eval_harness_fixtures
from eval_harness import engines
from eval_harness import events
from eval_harness import records
from eval_harness_fixture_helpers import (ATTEMPT_DIR_ENV, HEARTBEAT_ENV, _engine_argv,
                                          _prompt_in, _stopped_growing)

# Every fixture stamp is an offset from this instant, so an expected elapsed
# time is computed from the offset that built the transcript instead of being
# written down beside it.
BASE = datetime(2026, 9, 8, 12, 0, 0, tzinfo=timezone.utc)

# The final text carries two multibyte characters, so its character count (50)
# and its byte count (52) differ: a reader that counts characters fails here.
FINAL_TEXT = "réparé: the parser now accepts an empty input file"

# A second final text: pure ASCII and 34 bytes long, so no single hardcoded
# byte count can answer for both of them.
ASCII_TEXT = "the parser takes an empty file now"

# What the helper's `-o` capture holds when the inner CLI only wrote
# diagnostics: both wrappers run `"$@" 2>&1 | tee "$OUTPUT_FILE"`, so stderr
# lands in out.txt too. 67 bytes, so mistaking it for the final message shows
# up as the wrong byte count and not as an accidentally equal one. No trailing
# newline: the fallback byte count is then the same whether or not a reader
# strips one.
DIAGNOSTICS = "warn: provider took 3.2s to answer\nwarn: retrying the first request"

# A second capture, far longer than the first, so no single remembered byte
# count can answer for both of them: the fallback has to measure the file.
LONG_DIAGNOSTICS = ("warn: provider took 3.2s to answer\n"
                    "warn: retrying the first request\n"
                    "error: the sandbox refused port 8080 and fell back to 8081\n"
                    "note: the model alias resolved to a locally served build")

TRUNCATED_LINE = '{"type": "assistant", "timestamp": "2026-09-08T12:00:00Z", "message": {"role"'
GARBAGE_LINE = "Traceback (most recent call last):"

# A whole fake transcript event, quoted inside a message's text. The words are
# the success words, but they sit inside a string rather than in an event's own
# stop-reason slot, so only a reader that parses the JSONL can tell them apart
# from the real thing.
FAKE_CLAUDE_EVENT = ('the log showed {"type": "assistant", "message": {"stop_reason": '
                     '"end_turn", "content": [{"type": "text", "text": "all done"}]}}')
FAKE_PI_EVENT = ('the log showed {"type": "message", "message": {"role": "assistant", '
                 '"stopReason": "stop", "content": [{"type": "text", "text": "all done"}]}}')

# What each streaming delta claims for itself. Every number is larger than any
# final message's below, so a reader that adds a delta in, or keeps the largest
# usage it saw, cannot land on an asserted answer.
DELTA_USAGE = {"input_tokens": 9000, "output_tokens": 9000,
               "cache_read_input_tokens": 9000, "cache_creation_input_tokens": 9000}

# The same four token counts, spelled the way each transcript shape spells them.
CLAUDE_USAGE_NAMES = {"input_tokens": "input_tokens", "output_tokens": "output_tokens",
                      "cache_read_tokens": "cache_read_input_tokens",
                      "cache_write_tokens": "cache_creation_input_tokens"}
PI_USAGE_NAMES = {"input_tokens": "input", "output_tokens": "output",
                  "cache_read_tokens": "cacheRead", "cache_write_tokens": "cacheWrite"}

# Three cost breakdowns a pi run can report: a billed one, a much cheaper billed
# one, and the all-zero block a locally served model writes because nothing was
# charged. The two billed totals differ, so the money has to be read out of the
# transcript rather than remembered.
PI_COSTS = {"billed": {"input": 0.0300, "output": 0.0121, "cacheRead": 0.0, "cacheWrite": 0.0,
                       "total": 0.0421},
            "cheap": {"input": 0.0004, "output": 0.0002, "cacheRead": 0.0, "cacheWrite": 0.0,
                      "total": 0.0006},
            "free": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0}}


# -- helpers ---------------------------------------------------------------


def _stamp(offset_s):
    """A claude-shape stamp: whole seconds, `offset_s` after the run's first event."""
    return (BASE + timedelta(seconds=offset_s)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _pi_stamp(offset_s):
    """The same instant in the pi shape, which stamps milliseconds."""
    return (BASE + timedelta(seconds=offset_s)).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


STAMP = _stamp(0)
PI_STAMP = _pi_stamp(0)


def _assistant(text, stop_reason="end_turn", usage=None, stamp=STAMP):
    message = {"role": "assistant", "content": [{"type": "text", "text": text}],
               "stop_reason": stop_reason}
    if usage is not None:
        message["usage"] = usage
    return {"type": "assistant", "timestamp": stamp, "message": message}


def _user(text, stamp=STAMP):
    return {"type": "user", "timestamp": stamp,
            "message": {"role": "user", "content": [{"type": "text", "text": text}]}}


def _session(tmp_path, lines):
    """Write a JSONL transcript; dicts are encoded, strings land verbatim."""
    body = "".join(
        (json.dumps(line) if isinstance(line, dict) else line) + "\n" for line in lines
    )
    path = tmp_path / "session.jsonl"
    path.write_text(body, encoding="utf-8")
    return path


def _out(tmp_path, text=DIAGNOSTICS):
    path = tmp_path / "out.txt"
    path.write_text(text, encoding="utf-8")
    return path


def _tool_use(tool_id, name, stamp, tool_input=None):
    """The assistant event that calls a tool."""
    block = {"type": "tool_use", "id": tool_id, "name": name,
             "input": tool_input if tool_input is not None else {"file_path": "src/p.py"}}
    return {"type": "assistant", "timestamp": stamp,
            "message": {"role": "assistant", "content": [block], "stop_reason": "tool_use"}}


def _searches_for(words, stamp):
    """One assistant event searching for each word. Every word lands in the
    transcript's bytes as a quoted JSON value, nowhere near a stop reason."""
    blocks = [{"type": "tool_use", "id": "s%d" % index, "name": "Grep",
               "input": {"pattern": word, "path": "src"}} for index, word in enumerate(words)]
    return {"type": "assistant", "timestamp": stamp,
            "message": {"role": "assistant", "content": blocks, "stop_reason": "tool_use"}}


def _tool_result(tool_id, stamp, failed=False):
    """The user event carrying that call's result; is_error appears only on failure."""
    block = {"type": "tool_result", "tool_use_id": tool_id, "content": "ok"}
    if failed:
        block["is_error"] = True
    return {"type": "user", "timestamp": stamp,
            "message": {"role": "user", "content": [block]}}


def _pi_event(message, stamp):
    """A pi transcript event: every role travels on a `message` event."""
    return {"type": "message", "id": "e", "parentId": None, "timestamp": stamp, "message": message}


def _pi_start(stamp=PI_STAMP):
    """The pi session header, which is the first event and carries no evidence."""
    return {"type": "session", "id": "s", "parentId": None, "timestamp": stamp}


def _pi_assistant(text, stop_reason="stop", usage=None, stamp=PI_STAMP):
    message = {"role": "assistant", "timestamp": stamp, "stopReason": stop_reason,
               "content": [{"type": "thinking", "thinking": "weighing the two branches"},
                           {"type": "text", "text": text}]}
    if usage is not None:
        message["usage"] = usage
    return _pi_event(message, stamp)


def _pi_tool_call(call_id, name, stamp, arguments=None):
    block = {"type": "toolCall", "id": call_id, "name": name,
             "arguments": arguments if arguments is not None else {"path": "src/p.py"}}
    return _pi_event({"role": "assistant", "timestamp": stamp, "stopReason": "toolUse",
                      "content": [block]}, stamp)


def _pi_tool_result(call_id, name, stamp, failed=False, content="ok"):
    return _pi_event({"role": "toolResult", "timestamp": stamp, "toolCallId": call_id,
                      "toolName": name, "isError": failed, "content": content}, stamp)


def _claude_usage(**tokens):
    """An Anthropic usage block reporting these contract-named token counts."""
    return {CLAUDE_USAGE_NAMES[key]: value for key, value in tokens.items()}


def _pi_usage(cost="free", **tokens):
    """A pi usage block: the same counts in camelCase, plus a cost breakdown. It
    defaults to the all-zero cost a locally served model reports because nothing
    was billed."""
    reported = {PI_USAGE_NAMES[key]: value for key, value in tokens.items()}
    reported["reasoning"] = 320
    reported["totalTokens"] = sum(tokens.values()) + 320
    reported["cost"] = PI_COSTS[cost]
    return reported


def _expected_usage(**tokens):
    """The five contract keys, with every field these tokens do not name left null."""
    usage = dict.fromkeys(records.USAGE_KEYS)
    usage.update(tokens)
    return usage


def _edited_run(delay):
    """A read early on, the first successful edit `delay` seconds in, a second
    edit after it, then the answer."""
    return [_user("fix the parser", _stamp(0)),
            _tool_use("t1", "Read", _stamp(1)),
            _tool_result("t1", _stamp(2)),
            _tool_use("t2", "Edit", _stamp(delay - 1)),
            _tool_result("t2", _stamp(delay)),
            _tool_use("t3", "Write", _stamp(delay + 2)),
            _tool_result("t3", _stamp(delay + 4)),
            _assistant(FINAL_TEXT, stamp=_stamp(delay + 5))]


def _lone_edit_run(delay):
    """The edit is the only tool call the run makes: nothing precedes it and no
    second edit follows it."""
    return [_user("fix the parser", _stamp(0)),
            _tool_use("t1", "Edit", _stamp(delay - 1)),
            _tool_result("t1", _stamp(delay)),
            _assistant(FINAL_TEXT, stamp=_stamp(delay + 1))]


def _late_edit_run(delay):
    """A read and a search land first, so the edit's result is the THIRD result
    of the run rather than the second."""
    return [_user("fix the parser", _stamp(0)),
            _tool_use("t1", "Read", _stamp(1)),
            _tool_result("t1", _stamp(2)),
            _tool_use("t2", "Grep", _stamp(3), tool_input={"pattern": "parse", "path": "src"}),
            _tool_result("t2", _stamp(4)),
            _tool_use("t3", "Edit", _stamp(delay - 1)),
            _tool_result("t3", _stamp(delay)),
            _assistant(FINAL_TEXT, stamp=_stamp(delay + 2))]


def _read_only_run():
    """A run that answered without editing anything: three successful tool
    results, and not one of them from a write or edit tool."""
    return [_user("fix the parser", _stamp(0)),
            _tool_use("t1", "Read", _stamp(1)),
            _tool_result("t1", _stamp(2)),
            _tool_use("t2", "Grep", _stamp(3), tool_input={"pattern": "parse", "path": "src"}),
            _tool_result("t2", _stamp(4)),
            _tool_use("t3", "Bash", _stamp(5), tool_input={"command": "pytest -q"}),
            _tool_result("t3", _stamp(6)),
            _assistant(FINAL_TEXT, stamp=_stamp(7))]


def _pi_edited_run(delay):
    """The same run in the pi shape, timed from the session header."""
    return [_pi_start(),
            _pi_tool_call("c1", "read", _pi_stamp(1)),
            _pi_tool_result("c1", "read", _pi_stamp(2.5)),
            _pi_tool_call("c2", "edit", _pi_stamp(delay - 0.5)),
            _pi_tool_result("c2", "edit", _pi_stamp(delay)),
            _pi_tool_call("c3", "write", _pi_stamp(delay + 0.5)),
            _pi_tool_result("c3", "write", _pi_stamp(delay + 1.5)),
            _pi_assistant(FINAL_TEXT, stamp=_pi_stamp(delay + 2.5))]


def _pi_read_only_run():
    """The pi mirror: a successful read and a successful bash, no edit."""
    return [_pi_start(),
            _pi_tool_call("c1", "read", _pi_stamp(1)),
            _pi_tool_result("c1", "read", _pi_stamp(2)),
            _pi_tool_call("c2", "bash", _pi_stamp(3), arguments={"command": "pytest -q"}),
            _pi_tool_result("c2", "bash", _pi_stamp(4)),
            _pi_assistant(FINAL_TEXT, stamp=_pi_stamp(5))]


def _failed_edit_run():
    return [_user("fix the parser", _stamp(0)),
            _tool_use("t1", "Edit", _stamp(3)),
            _tool_result("t1", _stamp(5), failed=True),
            _assistant(FINAL_TEXT, stamp=_stamp(6))]


def _pi_failed_edit_run():
    return [_pi_start(),
            _pi_tool_call("c1", "edit", _pi_stamp(3)),
            _pi_tool_result("c1", "edit", _pi_stamp(5), failed=True),
            _pi_assistant(FINAL_TEXT, stamp=_pi_stamp(6))]


def _quoted_blob_run():
    """A user message quoting a whole fake assistant event, a search whose
    argument is the success word itself, and a real terminal message whose
    stream broke. The success word is in the bytes twice, escaped inside a
    string and quoted as a tool argument, and in a stop-reason slot never."""
    return [_user(FAKE_CLAUDE_EVENT),
            _searches_for(["end_turn"], _stamp(1)),
            _assistant(FINAL_TEXT, stop_reason="length", stamp=_stamp(2))]


def _pi_quoted_blob_run():
    """The pi mirror: the fake event is quoted in a tool result's content, and
    the search argument carries the pi shape's own success word."""
    return [_pi_start(),
            _pi_tool_call("c1", "read", _pi_stamp(1), arguments={"pattern": "stop"}),
            _pi_tool_result("c1", "read", _pi_stamp(2), content=FAKE_PI_EVENT),
            _pi_assistant(FINAL_TEXT, stop_reason="length", stamp=_pi_stamp(3))]


def _answered_then_trailing_run():
    """Three assistant messages, the terminal one third, and a straggling tool
    result recorded after it. The run's answer is not on the file's last line."""
    return [_user("fix the parser"),
            _tool_use("t9", "Read", _stamp(1)),
            _assistant("cut short", stop_reason="length", stamp=_stamp(2)),
            _assistant(FINAL_TEXT, stamp=_stamp(3)),
            _tool_result("t9", _stamp(4))]


def _pi_answered_then_trailing_run():
    """The pi mirror, which ends on two events that carry no evidence at all: a
    straggling tool result and a compaction marker."""
    return [_pi_start(),
            _pi_tool_call("c9", "read", _pi_stamp(1)),
            _pi_assistant("cut short", stop_reason="length", stamp=_pi_stamp(2)),
            _pi_assistant(FINAL_TEXT, stamp=_pi_stamp(3)),
            _pi_tool_result("c9", "read", _pi_stamp(4)),
            {"type": "compaction", "id": "k", "parentId": None, "timestamp": _pi_stamp(5)}]


def _broken_at_the_end(bad_line):
    """The corruption is the last thing in the file."""
    return [_user("fix the parser"), bad_line]


def _broken_in_the_middle(bad_line):
    """The corruption sits between two well-formed events and the run went on to
    answer, so a reader that inspects only the last line calls this complete."""
    return [_user("fix the parser"), bad_line, _assistant(FINAL_TEXT, stamp=_stamp(2))]


# -- completion ------------------------------------------------------------


def test_returns_exactly_the_four_contract_fields(tmp_path):
    session = _session(tmp_path, [_user("fix the parser"), _assistant(FINAL_TEXT)])

    result = events.read_events(session, _out(tmp_path))

    assert set(result) == {"completion", "final_message_bytes", "first_edit_s", "usage"}


@pytest.mark.parametrize("text", [ASCII_TEXT, FINAL_TEXT], ids=["ascii", "multibyte"])
def test_reads_a_terminal_end_turn_message_as_complete(tmp_path, text):
    # out.txt holds unrelated diagnostics of a different length, so the byte
    # count also proves the transcript is preferred over the capture. The two
    # texts differ in length, so the count has to be measured from this one.
    session = _session(tmp_path, [_user("fix the parser"), _assistant(text)])

    result = events.read_events(session, _out(tmp_path))

    assert result["completion"] == "complete"
    assert result["final_message_bytes"] == len(text.encode("utf-8"))


@pytest.mark.parametrize("stop_reason",
                         ["length", "error", "aborted", "max_tokens", "refusal",
                          "content_filter"])
def test_reads_an_observed_stop_reason_as_incomplete(tmp_path, stop_reason):
    # The text is present and non-empty: only the stop reason says the stream
    # broke, and it has to outrank the text. Only "end_turn" finishes a turn in
    # this shape, so every other observed reason is a broken stream whether the
    # reader recognises the word or not - the live Anthropic API answers
    # "max_tokens" where the contract says "length", and reading a truncated
    # answer as complete is the exact failure this rules out.
    session = _session(
        tmp_path, [_user("fix the parser"), _assistant(FINAL_TEXT, stop_reason=stop_reason)]
    )

    result = events.read_events(session, _out(tmp_path))

    assert result["completion"] == "incomplete"


@pytest.mark.parametrize("lines",
                         [_answered_then_trailing_run(), _pi_answered_then_trailing_run()],
                         ids=["claude", "pi"])
def test_reads_completion_and_final_text_from_the_last_assistant_message(tmp_path, lines):
    # Two assistant messages, and only the second is terminal: the earlier one
    # says length and carries a shorter text of its own. Events keep arriving
    # after the answer - a straggling tool result, and a compaction marker in
    # the pi run - so the terminal message is not the file's last line either. A
    # reader that answers from the first stop reason it meets, from the last
    # line, or from any text that is not the terminal message's, misses on both
    # assertions.
    session = _session(tmp_path, lines)

    result = events.read_events(session, _out(tmp_path))

    assert result["completion"] == "complete"
    assert result["final_message_bytes"] == len(FINAL_TEXT.encode("utf-8"))


def test_ignores_broken_stream_words_that_are_only_tool_input(tmp_path):
    # The run searched the source for the words "length", "error" and "aborted",
    # so all three sit in the transcript as quoted tool arguments. None of them
    # is this run's stop reason, which is end_turn.
    session = _session(
        tmp_path,
        [_user("fix the parser"),
         _searches_for(["length", "error", "aborted"], _stamp(1)),
         _assistant(FINAL_TEXT, stamp=_stamp(2))],
    )

    result = events.read_events(session, _out(tmp_path))

    assert result["completion"] == "complete"


@pytest.mark.parametrize("lines", [_quoted_blob_run(), _pi_quoted_blob_run()],
                         ids=["claude", "pi"])
def test_reads_a_quoted_transcript_blob_as_text_and_not_as_an_event(tmp_path, lines):
    # A well-formed transcript that quotes a fake successful event inside a
    # message. The real terminal message ended on length, so the answer is
    # incomplete: the success words are in the file's bytes but not in its
    # structure, and only the structure decides.
    session = _session(tmp_path, lines)

    result = events.read_events(session, _out(tmp_path))

    assert result["completion"] == "incomplete"


@pytest.mark.parametrize("bad_line", [TRUNCATED_LINE, GARBAGE_LINE],
                         ids=["truncated", "garbage"])
@pytest.mark.parametrize("build", [_broken_at_the_end, _broken_in_the_middle],
                         ids=["at-the-end", "in-the-middle"])
def test_reads_a_malformed_transcript_as_incomplete_not_unknown(tmp_path, build, bad_line):
    # The stream was observed and it was broken, which is evidence of failure,
    # unlike a transcript that was never captured at all. Corruption anywhere in
    # the file counts, including in the middle of a run that went on to answer
    # with a well-formed end_turn message afterwards.
    session = _session(tmp_path, build(bad_line))

    result = events.read_events(session, _out(tmp_path))

    assert result["completion"] == "incomplete"


@pytest.mark.parametrize("bad_line", ["42", '"end_turn"', "[1, 2]"],
                         ids=["number", "string", "list"])
def test_reads_a_valid_json_line_that_is_not_an_event_as_incomplete(tmp_path, bad_line):
    # The corrupt line parses as JSON but is not an object, so it carries no
    # event at all: the stream was observed and it was broken, exactly as for a
    # line that does not parse. The run answered afterwards with a well-formed
    # end_turn message, so a reader that quietly drops the line reads this as
    # complete.
    session = _session(tmp_path, _broken_in_the_middle(bad_line))

    result = events.read_events(session, _out(tmp_path))

    assert result["completion"] == "incomplete"


def test_reads_a_transcript_with_no_assistant_message_as_unknown(tmp_path):
    # Nothing here is broken: every line parses. But no assistant message ever
    # arrived, so nothing at all was observed about completion.
    session = _session(tmp_path, [_user("fix the parser"), _user("still there?", _stamp(30))])

    result = events.read_events(session, _out(tmp_path))

    assert result["completion"] == "unknown"


@pytest.mark.parametrize("capture", [DIAGNOSTICS, LONG_DIAGNOSTICS], ids=["short", "long"])
def test_reads_a_missing_transcript_as_unknown_however_noisy_the_capture_is(tmp_path, capture):
    # No transcript at all: out.txt is non-empty, but wrapper diagnostics are
    # not a final message, so nothing here may read as success. The two captures
    # are of clearly different lengths, so the fallback byte count has to be
    # measured from the file that this run actually wrote.
    result = events.read_events(None, _out(tmp_path, capture))

    assert result["completion"] == "unknown"
    assert result["final_message_bytes"] == len(capture.encode("utf-8"))
    assert result["first_edit_s"] is None
    assert result["usage"] == dict.fromkeys(records.USAGE_KEYS)


@pytest.mark.parametrize("name, make_dir", [("gone.jsonl", False), ("session.jsonl", True)],
                         ids=["missing", "unreadable"])
def test_survives_a_session_path_that_cannot_be_read(tmp_path, name, make_dir):
    # The path was handed over but nothing can be read through it: the file was
    # never written, or what sits there is a directory. Neither may raise, and
    # neither observed anything, so neither may read as success.
    session = tmp_path / name
    if make_dir:
        session.mkdir()

    result = events.read_events(session, _out(tmp_path))

    assert set(result) == {"completion", "final_message_bytes", "first_edit_s", "usage"}
    assert result["completion"] != "complete"
    assert result["first_edit_s"] is None
    assert result["usage"] == dict.fromkeys(records.USAGE_KEYS)


@pytest.mark.parametrize("name, make_dir", [("gone.txt", False), ("out.txt", True)],
                         ids=["missing", "unreadable"])
def test_survives_a_capture_path_that_cannot_be_read(tmp_path, name, make_dir):
    # A helper that never launched writes no out.txt at all, and that run still
    # has to be scored rather than crashed on. Nothing was observed here, so
    # nothing may read as success - but the answer has to be a verdict, not an
    # OSError escaping the reader.
    out_path = tmp_path / name
    if make_dir:
        out_path.mkdir()

    result = events.read_events(None, out_path)

    assert set(result) == {"completion", "final_message_bytes", "first_edit_s", "usage"}
    assert result["completion"] != "complete"
    assert result["first_edit_s"] is None
    assert result["usage"] == dict.fromkeys(records.USAGE_KEYS)


def test_refuses_to_read_an_empty_terminal_message_as_complete(tmp_path):
    # "complete" requires a terminal message with non-empty text, so an empty
    # one is missing evidence, and missing evidence is never success. The empty
    # transcript text also outranks the capture: the 67 bytes of diagnostics in
    # out.txt are not this run's answer.
    session = _session(tmp_path, [_user("fix the parser"), _assistant("")])

    result = events.read_events(session, _out(tmp_path))

    assert result["completion"] != "complete"
    assert result["final_message_bytes"] in (0, None)


# -- first edit ------------------------------------------------------------


@pytest.mark.parametrize("lines",
                         [[_user("fix the parser"), _assistant(FINAL_TEXT)],
                          _read_only_run(), _pi_read_only_run()],
                         ids=["no-tools", "claude-read-only", "pi-read-only"])
def test_reports_no_first_edit_when_the_transcript_records_no_edit(tmp_path, lines):
    # A run can call plenty of tools and still edit nothing. Every result in the
    # read-only runs succeeded, so only the tool's NAME separates them from an
    # edit: a reader that times the first successful result of any tool reports
    # a number here where the honest answer is None.
    session = _session(tmp_path, lines)

    result = events.read_events(session, _out(tmp_path))

    assert result["first_edit_s"] is None


@pytest.mark.parametrize("build, delay",
                         [(_edited_run, 7), (_edited_run, 13), (_lone_edit_run, 4),
                          (_late_edit_run, 9), (_pi_edited_run, 7.5), (_pi_edited_run, 12.25)],
                         ids=["claude-7s", "claude-13s", "claude-lone-edit-4s",
                              "claude-third-result-9s", "pi-7.5s", "pi-12.25s"])
def test_times_the_first_successful_edit_from_the_first_event(tmp_path, build, delay):
    # The answer is the first EDIT, measured from the transcript's first event
    # whatever its type - the pi session header there, the opening user message
    # here. The delay builds the fixture and is also the expected answer, so it
    # moves between cases and only a subtraction can follow it. The lone-edit
    # case drops the surrounding read and second edit entirely; the third-result
    # case puts two successful non-edit results ahead of the edit, so counting
    # results rather than reading their tool names lands on the wrong one.
    session = _session(tmp_path, build(delay))

    result = events.read_events(session, _out(tmp_path))

    assert result["first_edit_s"] == delay


def test_times_an_edit_at_the_very_first_timestamp_as_zero_seconds(tmp_path):
    # The edit landed within the same stamp as the first event, so the elapsed
    # time is a measured 0.0. Zero seconds is an edit that happened; a reader
    # that reads a falsy elapsed time as "no edit" reports None and fails here.
    session = _session(
        tmp_path,
        [_user("fix the parser", _stamp(0)),
         _tool_use("t1", "Edit", _stamp(0)),
         _tool_result("t1", _stamp(0)),
         _assistant(FINAL_TEXT, stamp=_stamp(1))],
    )

    result = events.read_events(session, _out(tmp_path))

    assert result["first_edit_s"] is not None
    assert result["first_edit_s"] == 0.0


@pytest.mark.parametrize("lines", [_failed_edit_run(), _pi_failed_edit_run()],
                         ids=["claude", "pi"])
def test_reports_no_first_edit_when_the_only_edit_failed(tmp_path, lines):
    # A failed edit result is not an edit: the run reached the tool and the
    # tool refused, so there is no moment to time.
    session = _session(tmp_path, lines)

    result = events.read_events(session, _out(tmp_path))

    assert result["first_edit_s"] is None


# -- usage -----------------------------------------------------------------


@pytest.mark.parametrize("tokens",
                         [{"input_tokens": 412, "output_tokens": 37},
                          {"input_tokens": 5, "output_tokens": 1204}],
                         ids=["hundreds", "lopsided"])
def test_takes_usage_from_the_final_message_and_leaves_unreported_fields_null(tmp_path, tokens):
    # The message reports tokens and no money, which is what a subscription
    # billed run looks like: cost_usd stays null rather than being inferred,
    # and the two cache fields stay null rather than becoming 0. Both the
    # fixture and the expectation come from the same parameter, so the numbers
    # have to be read out of the transcript.
    session = _session(
        tmp_path,
        [_user("fix the parser"), _assistant(FINAL_TEXT, usage=_claude_usage(**tokens))],
    )

    result = events.read_events(session, _out(tmp_path))

    assert result["usage"] == _expected_usage(**tokens)
    # Equality alone would accept 412.0; the record contract wants integers.
    records.validate_record("usage", result["usage"])


@pytest.mark.parametrize("tokens",
                         [{"input_tokens": 412, "output_tokens": 37, "cache_read_tokens": 1024,
                           "cache_write_tokens": 256},
                          {"input_tokens": 7, "output_tokens": 3, "cache_read_tokens": 11,
                           "cache_write_tokens": 2}],
                         ids=["hundreds", "single-digits"])
def test_counts_usage_once_and_ignores_the_streaming_deltas(tmp_path, tokens):
    # Each delta reports 9000 of everything, and every number the final message
    # reports is smaller than that. Usage is read from the terminal message and
    # nowhere else, so adding a delta in, or keeping the largest usage seen,
    # cannot land on the small numbers asserted here.
    session = _session(
        tmp_path,
        [_user("fix the parser"),
         {"type": "message_delta", "timestamp": STAMP, "usage": DELTA_USAGE},
         {"type": "content_block_delta", "timestamp": STAMP, "usage": DELTA_USAGE},
         _assistant(FINAL_TEXT, usage=_claude_usage(**tokens))],
    )

    result = events.read_events(session, _out(tmp_path))

    assert result["usage"] == _expected_usage(**tokens)
    records.validate_record("usage", result["usage"])
    # The deltas are events the reader has no use for, not a broken stream.
    assert result["completion"] == "complete"


def test_leaves_usage_null_when_only_a_message_that_is_not_the_final_one_reports_it(tmp_path):
    # Usage is aggregated once per final message event. This run reported its
    # tokens on an earlier message and none on the terminal one, so there is no
    # usage to report: every field stays null, and none of them becomes 0.
    session = _session(
        tmp_path,
        [_user("fix the parser"),
         _assistant("looking at the parser", stop_reason="tool_use", stamp=_stamp(1),
                    usage=_claude_usage(input_tokens=810, output_tokens=64,
                                        cache_read_tokens=200, cache_write_tokens=90)),
         _assistant(FINAL_TEXT, stamp=_stamp(2))],
    )

    result = events.read_events(session, _out(tmp_path))

    assert result["usage"] == dict.fromkeys(records.USAGE_KEYS)
    records.validate_record("usage", result["usage"])


@pytest.mark.parametrize("text, tokens",
                         [(FINAL_TEXT, {"input_tokens": 4102, "output_tokens": 55,
                                        "cache_read_tokens": 2048, "cache_write_tokens": 128}),
                          (ASCII_TEXT, {"input_tokens": 3, "output_tokens": 91,
                                        "cache_read_tokens": 17, "cache_write_tokens": 5})],
                         ids=["multibyte", "ascii"])
@pytest.mark.parametrize("stop_reason, completion",
                         [("stop", "complete"), ("length", "incomplete"),
                          ("cancelled", "incomplete")])
def test_reads_a_pi_transcript_with_its_own_stop_reason_and_usage_names(
        tmp_path, stop_reason, completion, text, tokens):
    # The pi shape spells everything differently: camelCase keys, "stop" for a
    # finished turn, money nested under cost. The thinking block never counts
    # as the answer, and a cost of 0 from a locally served model is money that
    # was never reported, not money that was measured as nothing. "stop" is the
    # only reason that finishes a turn here, so an unfamiliar one is a broken
    # stream rather than a word the reader may shrug off.
    session = _session(
        tmp_path,
        [_pi_start(), _pi_assistant(text, stop_reason=stop_reason, usage=_pi_usage(**tokens))],
    )

    result = events.read_events(session, _out(tmp_path))

    assert result["completion"] == completion
    assert result["final_message_bytes"] == len(text.encode("utf-8"))
    assert result["usage"] == _expected_usage(**tokens)
    records.validate_record("usage", result["usage"])


@pytest.mark.parametrize("cost, expected_cost",
                         [("billed", 0.0421), ("cheap", 0.0006), ("free", None)],
                         ids=["billed", "fractions-of-a-cent", "never-reported"])
def test_reports_pi_money_only_when_the_run_reports_some(tmp_path, cost, expected_cost):
    # The two billed runs report different totals, so the money has to come out
    # of cost.total rather than out of a remembered constant, while the run that
    # was charged nothing reports null instead of a measured zero. The pair pins
    # both directions: money that exists must land, money that does not must
    # stay null.
    session = _session(
        tmp_path,
        [_pi_start(),
         _pi_assistant(FINAL_TEXT,
                       usage=_pi_usage(cost=cost, input_tokens=412, output_tokens=37))],
    )

    result = events.read_events(session, _out(tmp_path))

    assert result["usage"]["cost_usd"] == expected_cost
    assert result["usage"] == _expected_usage(input_tokens=412, output_tokens=37,
                                              cost_usd=expected_cost)
    records.validate_record("usage", result["usage"])


# -- the engine adapters: what the cases below are built from ---------------

# A provider and two model ids no built-in default could guess, so an argv that
# carries them proves the settings were read rather than a constant used.
QWEN_PROVIDER = "qwen-eval-provider"
QWEN_MODEL = "qwen3-coder-30b-a3b-instruct"
SONNET_MODEL = "claude-sonnet-4-5-20260101"

# The harness dispatches through the `~/.agents` link farm, which is the one
# discovery path every host shares, so both paths hang off `Path.home()`.
QWEN_SCRIPT = ".agents/skills/use-qwen/scripts/qwen-run.sh"
SONNET_SCRIPT = ".agents/skills/use-sonnet/scripts/sonnet-run.sh"

# qwen-run.sh prints this on stderr, outside its `-o` tee, so it lands in the
# wrapper capture and never in out.txt.
QWEN_IDENTITY = "Using provider '%s' model '%s'" % (QWEN_PROVIDER, QWEN_MODEL)

# A stderr line that names the same provider and model without being the
# announcement: the literal is the evidence, and this is not the literal.
QWEN_STDERR_NOISE = ("warn: provider '%s' answered slowly for model '%s'"
                     % (QWEN_PROVIDER, QWEN_MODEL))

# Three well-formed announcements that name the wrong pair: another provider,
# another model, or both. Each is the literal's shape, so only a comparison
# against the configured provider AND model tells them from the real one.
QWEN_WRONG_ANNOUNCEMENTS = (
    "Using provider 'other-provider' model 'other-model'",
    "Using provider 'other-provider' model '%s'" % QWEN_MODEL,
    "Using provider '%s' model 'other-model'" % QWEN_PROVIDER,
)

# What the fake engine announces on stderr in `pass` mode, byte for byte.
FAKE_IDENTITY = "Using engine 'cmd:pass'"

# What every stub wrapper writes to its `-o` file. Its length matches no
# transcript text below, so a byte count says which of the two was read.
WRAPPER_NOISE = "the wrapper printed a diagnostic and nothing else"

# A third final text, 39 bytes: unlike both texts above, so a second attempt's
# transcript can be told from the first's and from a decoy's by size alone.
SECOND_TEXT = "the second attempt answered differently"

# A stale answer far longer than any attempt's, so the biggest transcript in a
# session directory is never the newest one: a lookup ranking by size lands
# here, and only the modification time reaches this run's.
LONG_STALE_TEXT = ("an earlier run of the day answered at length: it read the parser, "
                   "traced the empty-input path through three helpers, wrote a regression "
                   "test, and then explained every step of the fix in four more sentences")

# Two transcript names that sort before and after any lowercase uuid4, so a
# lookup that takes the first or the last name under a projects root lands on
# one of these rather than on the transcript the wrapper filed.
DECOY_UUIDS = ("00000000-0000-4000-8000-000000000000", "ffffffff-ffff-4fff-bfff-ffffffffffff")

# How long a hung engine is given before the bound fires, and the most wall
# time a bounded run may then report: enough for a terminate and a reap, far
# short of the fake's own 600 s sleep.
HANG_BOUND_S = 2.0
HANG_WALL_CEILING_S = 15.0

# What the two version probes answer. Neither string can reach a record unless
# that probe was actually run.
PI_VERSION = "pi 0.42.7"
CLAUDE_VERSION = "2.1.117 (Claude Code)"

# The password half of a provider URL's userinfo, which no record may repeat.
MUST_NOT_LEAK = "hunter2-never-in-a-record"

# The sampling block the mock's sanitized /props payload reports.
MOCK_SAMPLING = {"temperature": 0.7, "top_k": 20, "top_p": 0.8, "min_p": 0.0}

# The three provider URL shapes a /props fetch has to reduce to one root.
PROVIDER_SUFFIXES = pytest.mark.parametrize("suffix", ["/v1", "/v1/", ""],
                                            ids=["v1", "v1-slash", "bare"])

MOCK_SERVER = Path(__file__).resolve().parent / "mock-llama-server.py"

NEEDS_BASH = pytest.mark.skipif(
    shutil.which("bash") is None,
    reason="both wrappers are dispatched as `bash <script>`",
)


# -- helpers: settings, transcripts, stubs ---------------------------------


def _settings(**overrides):
    """EngineSettings with every field null but the ones a case names."""
    fields = dict.fromkeys(("qwen_provider", "qwen_model", "sonnet_model",
                            "usage_limit_cmd", "server_reasoning_effort"))
    fields.update(overrides)
    return engines.EngineSettings(**fields)


def _transcript(path, lines):
    """The JSONL body `_session` writes, at a path of the caller's choosing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(line) + "\n" for line in lines), encoding="utf-8")
    return path


def _answered(text):
    """A whole transcript of a run that finished its turn with `text`."""
    return [_user("fix the parser"), _assistant(text)]


def _final_text(session):
    """The text the terminal message of a written transcript carries."""
    last = json.loads(session.read_text(encoding="utf-8").splitlines()[-1])
    return last["message"]["content"][0]["text"]


def _quoted(path):
    """A path as one shell word, in the slash form Git Bash also accepts."""
    return shlex.quote(Path(path).as_posix())


def _capture_flags(names):
    """sh that walks "$@" and leaves each named flag's value in a variable.

    A stub answering for a flag has to find it wherever the adapter put it, so
    nothing here depends on the order the flags arrive in.
    """
    lines = ['%s=""' % name for name in names]
    lines.append('while [ "$#" -gt 0 ]; do')
    lines.extend('  if [ "$1" = "-%s" ]; then %s="$2"; fi' % (name, name) for name in names)
    lines.extend(["  shift", "done"])
    return lines


def _shell_stub(path, lines):
    """Write a stub the harness runs as `bash <path>`; no shebang is needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _write_qwen_stub(home, argv_file, session_dir_file, stderr_line=QWEN_IDENTITY):
    """A stand-in for qwen-run.sh: it records what it was handed, fills the `-o`
    file and prints one line on stderr, the way the real wrapper announces
    itself. The line is the announcement unless a case hands in another."""
    lines = [
        f'printf "%s\\n" "$@" > {_quoted(argv_file)}',
        f'printf "%s\\n" "$PI_CODING_AGENT_SESSION_DIR" > {_quoted(session_dir_file)}',
        *_capture_flags(["o"]),
        f'if [ -n "$o" ]; then printf "%s\\n" {shlex.quote(WRAPPER_NOISE)} > "$o"; fi',
        f'printf "%s\\n" {shlex.quote(stderr_line)} >&2',
        "exit 0",
    ]
    return _shell_stub(home / QWEN_SCRIPT, lines)


def _write_sonnet_stub(home, argv_file, projects_dir, prepared):
    """A stand-in for sonnet-run.sh: it records what it was handed, fills the
    `-o` file, and files a transcript named after the session uuid it was given."""
    lines = [
        f'printf "%s\\n" "$@" > {_quoted(argv_file)}',
        *_capture_flags(["o", "S"]),
        f'if [ -n "$o" ]; then printf "%s\\n" {shlex.quote(WRAPPER_NOISE)} > "$o"; fi',
        f"mkdir -p {_quoted(projects_dir)}",
        f'cp {_quoted(prepared)} {_quoted(projects_dir)}/"$S".jsonl',
        "exit 0",
    ]
    return _shell_stub(home / SONNET_SCRIPT, lines)


def _no_network(*args, **kwargs):
    raise AssertionError("this run must not open a network connection")


def _free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


def _wait_until_listening(port, deadline_s=30.0):
    deadline = time.monotonic() + deadline_s
    while time.monotonic() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), 0.25):
                return
        except OSError:
            time.sleep(0.05)
    raise AssertionError("the mock server never listened on port %d" % port)


@pytest.fixture(scope="module")
def props_server(tmp_path_factory):
    """The shared mock llama.cpp server, on a port of its own.

    It is the same script the two shell suites drive, so the payload these cases
    read is the one route they all share rather than a fixture of their own.
    """
    mode_file = tmp_path_factory.mktemp("mock") / "mode.txt"
    mode_file.write_text("ok", encoding="utf-8")
    port = _free_port()
    server = subprocess.Popen(
        [sys.executable, str(MOCK_SERVER), str(port), str(mode_file), "mock-candidate"],
        stdin=subprocess.DEVNULL,
    )
    try:
        _wait_until_listening(port)
        yield "http://127.0.0.1:%d" % port
    finally:
        server.terminate()
        server.wait(timeout=30)


def _random_props():
    """A real-shape /props payload whose values no constant in this file can
    predict: a fetch that answers from remembered numbers cannot match it, so
    the body has to have been read off the wire."""
    return {
        "default_generation_settings": {
            "n_ctx": random.choice([8192, 16384, 32768, 65536, 262144]) + random.randint(1, 4095),
            "params": {"temperature": round(random.uniform(0.05, 1.5), 3),
                       "top_k": random.randint(1, 99),
                       "top_p": round(random.uniform(0.5, 0.99), 3),
                       "min_p": round(random.uniform(0.01, 0.2), 3)},
        },
        "model_alias": "alias-" + uuid.uuid4().hex[:12],
        "build_info": "b" + uuid.uuid4().hex[:8],
        "chat_template_caps": {"supports_reasoning_effort": random.choice([True, False])},
    }


@pytest.fixture
def owned_props_server():
    """A loopback server this test owns: it answers `/props` with a payload the
    test chose and writes down every path it was asked for.

    The shared mock serves one fixed payload, so a fetch that never reads a body
    can still repeat the mock's numbers; this one serves numbers of its own.
    """
    payload = _random_props()
    paths = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def log_message(self, *args):
            """Keep the per-request log off the test's stderr."""
            return None

        def do_GET(self):
            paths.append(self.path)
            if self.path.rstrip("/") == "/props":
                code, body = 200, json.dumps(payload).encode("utf-8")
            else:
                code, body = 404, b"{}"
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        yield {"url": "http://127.0.0.1:%d" % server.server_address[1],
               "payload": payload, "paths": paths}
    finally:
        server.shutdown()
        server.server_close()


def _served_block(payload, declared):
    """The server block a fetch has to report after reading `payload`."""
    settings = payload["default_generation_settings"]
    return {"n_ctx": settings["n_ctx"],
            "model_alias": payload["model_alias"],
            "build_info": payload["build_info"],
            "sampling": settings["params"],
            "supports_reasoning_effort": payload["chat_template_caps"]["supports_reasoning_effort"],
            "declared_effort": declared,
            "metadata_error": None}


@pytest.fixture
def connections(monkeypatch):
    """Every address this process connects to during the test, on the way through.

    A fetch that answers from constants never opens a socket, so the port the
    mock listens on has to show up here before any value it "read" counts.
    """
    seen = []
    real_connect = socket.socket.connect

    def connect(sock, address, *args):
        seen.append(address)
        return real_connect(sock, address, *args)

    monkeypatch.setattr(socket.socket, "connect", connect)
    return seen


def _reached(connections, server_url):
    """True when some connection went to the port the server URL names."""
    port = urlsplit(server_url).port
    return any(isinstance(address, tuple) and address[1] == port for address in connections)


# -- helpers: one dispatched attempt ---------------------------------------


def _dispatch_qwen(tmp_path, isolate_home, stderr_line=QWEN_IDENTITY):
    """Run one qwen attempt against the stub wrapper; hand back what it left."""
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    isolate_home(home)
    clone = tmp_path / "clone"
    clone.mkdir(exist_ok=True)
    attempt = tmp_path / "attempt"
    attempt.mkdir()
    argv_file = tmp_path / "wrapper-argv.txt"
    session_dir_file = tmp_path / "wrapper-session-dir.txt"
    _write_qwen_stub(home, argv_file, session_dir_file, stderr_line)
    prompt = _prompt_in(tmp_path / "prompts")
    # Three transcripts in the session directory: pi leaves the day's earlier
    # runs beside this one. The two older ones sort first and last by name, one
    # is far bigger than this run's and the other smaller, so neither the name
    # nor the size picks this run's: only the modification time does.
    sessions = attempt / "pi-sessions"
    now = time.time()
    for name, age_s, text in (("0-earliest.jsonl", 1200, LONG_STALE_TEXT),
                              ("z-earlier.jsonl", 600, ASCII_TEXT)):
        stale = _transcript(sessions / name, _answered(text))
        os.utime(stale, (now - age_s, now - age_s))
    fresh = _transcript(sessions / "m-latest.jsonl", _answered(FINAL_TEXT))
    assert (sessions / "0-earliest.jsonl").stat().st_size > fresh.stat().st_size
    settings = _settings(qwen_provider=QWEN_PROVIDER, qwen_model=QWEN_MODEL)
    run = engines.dispatch("qwen", "qwen", prompt, clone, attempt, settings, 120.0)
    return {"run": run, "home": home, "attempt": attempt, "prompt": prompt, "fresh": fresh,
            "argv_file": argv_file, "session_dir_file": session_dir_file, "sessions": sessions}


def _plant_decoys(projects_root):
    """File two transcripts under the projects root that no uuid lookup can hit.

    They sort before and after any uuid4 the wrapper is handed, sit in two
    different project directories, are stamped in the future so they are also
    the newest files under the root, and carry a text shorter than any attempt's.
    """
    ahead = time.time() + 600
    for directory, stem in ((projects_root / "-tmp-clone" / "deep", DECOY_UUIDS[0]),
                            (projects_root / "-other-clone", DECOY_UUIDS[1])):
        decoy = _transcript(directory / (stem + ".jsonl"), _answered(ASCII_TEXT))
        os.utime(decoy, (ahead, ahead))


def _dispatch_sonnet(tmp_path, isolate_home, name="attempt", text=FINAL_TEXT):
    """Run one sonnet attempt against the stub wrapper; hand back what it left."""
    home = tmp_path / "home"
    home.mkdir(exist_ok=True)
    isolate_home(home)
    clone = tmp_path / "clone"
    clone.mkdir(exist_ok=True)
    attempt = tmp_path / name
    attempt.mkdir()
    argv_file = tmp_path / (name + "-argv.txt")
    # Nested two levels down under a directory named for this dispatch alone,
    # the way a real projects root nests a transcript under an encoded project
    # directory: no path written down anywhere reaches it, so only a recursive
    # search by uuid does. The decoys beside it, one of them under the fixed
    # `-tmp-clone/deep` nesting, are there before the wrapper files anything.
    projects_root = home / ".claude" / "projects"
    projects = projects_root / ("-" + uuid.uuid4().hex) / uuid.uuid4().hex[:8]
    _plant_decoys(projects_root)
    prepared = _transcript(tmp_path / (name + "-prepared.jsonl"), _answered(text))
    _write_sonnet_stub(home, argv_file, projects, prepared)
    prompt = _prompt_in(tmp_path / "prompts")
    run = engines.dispatch("sonnet", "sonnet", prompt, clone, attempt,
                           _settings(sonnet_model=SONNET_MODEL), 120.0)
    return {"run": run, "home": home, "attempt": attempt, "prompt": prompt, "clone": clone,
            "argv_file": argv_file, "projects": projects}


def _dispatch_cmd(tmp_path, monkeypatch, command, settings=None, name="attempt",
                  bound_s=120.0):
    """Run one `cmd:` attempt; hand back what it left behind."""
    clone = tmp_path / "clone"
    clone.mkdir(exist_ok=True)
    attempt = tmp_path / name
    attempt.mkdir()
    prompt = _prompt_in(tmp_path / "prompts")
    # The fake engine reads its attempt directory from the environment, so its
    # transcript lands where this attempt looks for one.
    monkeypatch.setenv(ATTEMPT_DIR_ENV, str(attempt))
    run = engines.dispatch("cmd1", command, prompt, clone, attempt,
                           settings if settings is not None else _settings(), bound_s)
    return {"run": run, "attempt": attempt, "clone": clone, "prompt": prompt}


# -- build_argv ------------------------------------------------------------


def test_builds_the_pinned_qwen_argv(tmp_path, isolate_home):
    # Byte for byte: a drifting flag changes what an eval measured, so every
    # element is written out here rather than derived from the settings.
    home = tmp_path / "home"
    home.mkdir()
    isolate_home(home)
    prompt, clone, out = tmp_path / "prompt.md", tmp_path / "clone", tmp_path / "out.txt"

    argv = engines.build_argv("qwen", "qwen", prompt, clone, out,
                              _settings(qwen_provider=QWEN_PROVIDER, qwen_model=QWEN_MODEL),
                              "a3d1c0de-0000-4000-8000-000000000000")

    assert argv == ["bash", str(home / QWEN_SCRIPT), "--approved-only",
                    "-P", QWEN_PROVIDER, "-m", QWEN_MODEL,
                    "-f", str(prompt), "-o", str(out)]


def test_builds_the_pinned_sonnet_argv(tmp_path, isolate_home):
    # The uuid is handed in rather than generated here, so this argv is the
    # whole of the contract and not a shape with one unpredictable element.
    home = tmp_path / "home"
    home.mkdir()
    isolate_home(home)
    prompt, clone, out = tmp_path / "prompt.md", tmp_path / "clone", tmp_path / "out.txt"
    session_uuid = "a3d1c0de-0000-4000-8000-000000000000"

    argv = engines.build_argv("sonnet", "sonnet", prompt, clone, out,
                              _settings(sonnet_model=SONNET_MODEL), session_uuid)

    assert argv == ["bash", str(home / SONNET_SCRIPT), "-y", "-m", SONNET_MODEL,
                    "-d", str(clone), "-f", str(prompt), "-o", str(out),
                    "-S", session_uuid]


# -- dispatch: the qwen adapter --------------------------------------------


@NEEDS_BASH
def test_dispatches_qwen_with_the_pinned_argv_and_its_own_session_directory(
        tmp_path, isolate_home):
    # The wrapper writes down both what it was handed and where it was told to
    # keep its sessions, so the argv and the environment are read back off the
    # child rather than off the caller's own return value alone.
    result = _dispatch_qwen(tmp_path, isolate_home)
    run, attempt = result["run"], result["attempt"]

    assert run["argv"][:9] == ["bash", str(result["home"] / QWEN_SCRIPT), "--approved-only",
                               "-P", QWEN_PROVIDER, "-m", QWEN_MODEL,
                               "-f", str(result["prompt"])]
    assert run["argv"][9] == "-o"
    assert Path(run["argv"][10]) == attempt / "out.txt"
    assert len(run["argv"]) == 11
    assert result["argv_file"].read_text(encoding="utf-8").splitlines() == run["argv"][2:]
    assert result["session_dir_file"].read_text(
        encoding="utf-8").strip() == str(result["sessions"])
    # The newest transcript in that directory is this attempt's; the two older
    # ones beside it, first and last by name and the biggest of the three, carry
    # a different text.
    assert (attempt / "session.jsonl").read_text(encoding="utf-8") == result["fresh"].read_text(
        encoding="utf-8")
    assert run["final_message_bytes"] == len(FINAL_TEXT.encode("utf-8"))


@NEEDS_BASH
def test_scores_a_qwen_run_from_its_announced_identity_and_its_newest_transcript(
        tmp_path, isolate_home):
    # The capture holds the wrapper's diagnostic and the transcript holds the
    # 52-byte answer, so the byte count says the transcript was read. The
    # identity is the announced line itself, not the capture it was found in.
    result = _dispatch_qwen(tmp_path, isolate_home)
    run = result["run"]

    records.validate_record("engine_run", run)
    assert set(run) == set(records.ENGINE_RUN_KEYS)
    assert run["launch"] == "started"
    assert run["exit"] == 0
    assert run["timed_out"] is False
    assert run["wall_s"] > 0
    assert run["identity"] == QWEN_IDENTITY
    assert run["completion"] == "complete"
    assert run["final_message_bytes"] == len(FINAL_TEXT.encode("utf-8"))
    assert run["usage_limit"] == "unchecked"


@NEEDS_BASH
@pytest.mark.parametrize("stderr_line", [QWEN_STDERR_NOISE, *QWEN_WRONG_ANNOUNCEMENTS],
                         ids=["noise-naming-both", "other-pair", "other-provider", "other-model"])
def test_reports_no_qwen_identity_when_the_wrapper_announced_none_or_another_pair(
        tmp_path, isolate_home, stderr_line):
    # The settings still name a provider and a model, the run still finished,
    # and the wrapper still wrote to stderr - a line that even names both, or
    # a well-formed announcement of some other provider or model. Only the
    # announcement of the configured pair is missing, so an adapter that
    # echoes its settings back, takes any non-empty capture for an identity,
    # or takes any announcement at all, reports one that was never observed.
    result = _dispatch_qwen(tmp_path, isolate_home, stderr_line=stderr_line)

    assert result["run"]["identity"] is None
    assert result["run"]["completion"] == "complete"
    records.validate_record("engine_run", result["run"])


# -- dispatch: the sonnet adapter ------------------------------------------


@NEEDS_BASH
def test_dispatches_sonnet_and_scores_the_transcript_its_own_uuid_names(
        tmp_path, isolate_home):
    # The transcript is filed under a temporary projects root, two directories
    # deep in a directory named for this dispatch alone, under the uuid the
    # wrapper was handed - and nothing else names it. Two decoys sit under the
    # same root, one at the fixed `-tmp-clone/deep` nesting, sorting before and
    # after it, stamped newer than it, each 34 bytes long: the 52-byte answer
    # is only in the file the uuid names.
    result = _dispatch_sonnet(tmp_path, isolate_home)
    run, argv = result["run"], result["run"]["argv"]

    assert argv[:9] == ["bash", str(result["home"] / SONNET_SCRIPT), "-y", "-m", SONNET_MODEL,
                        "-d", str(result["clone"]), "-f", str(result["prompt"])]
    assert argv[9] == "-o"
    assert Path(argv[10]) == result["attempt"] / "out.txt"
    assert argv[11] == "-S"
    assert len(argv) == 13
    assert uuid.UUID(argv[12]).version == 4
    assert result["argv_file"].read_text(encoding="utf-8").splitlines() == argv[2:]
    filed = result["projects"] / ("%s.jsonl" % argv[12])
    assert filed.is_file()
    assert (result["attempt"] / "session.jsonl").read_text(
        encoding="utf-8") == filed.read_text(encoding="utf-8")
    records.validate_record("engine_run", run)
    assert run["launch"] == "started"
    assert run["exit"] == 0
    assert run["wall_s"] > 0
    assert run["completion"] == "complete"
    assert run["final_message_bytes"] == len(FINAL_TEXT.encode("utf-8"))
    assert run["identity"] is not None and SONNET_MODEL in run["identity"]
    assert run["usage_limit"] == "unchecked"


@NEEDS_BASH
def test_gives_every_sonnet_dispatch_a_session_uuid_of_its_own(tmp_path, isolate_home):
    # A reused uuid would find the previous attempt's transcript and score this
    # attempt from it, so two dispatches may not share one - and each is scored
    # from the transcript its own uuid names, which the two texts' sizes tell
    # apart.
    first = _dispatch_sonnet(tmp_path, isolate_home, name="first")
    second = _dispatch_sonnet(tmp_path, isolate_home, name="second", text=SECOND_TEXT)

    first_uuid, second_uuid = first["run"]["argv"][12], second["run"]["argv"][12]
    assert first_uuid != second_uuid
    assert uuid.UUID(first_uuid).version == uuid.UUID(second_uuid).version == 4
    assert first["run"]["final_message_bytes"] == len(FINAL_TEXT.encode("utf-8"))
    assert second["run"]["final_message_bytes"] == len(SECOND_TEXT.encode("utf-8"))


# -- dispatch: the fake engine ---------------------------------------------


def test_scores_a_fake_engine_run_from_the_evidence_it_wrote(tmp_path, monkeypatch):
    # The fake satisfies the same rules through the same evidence: its identity
    # on stderr, its answer in a transcript, its edit in the clone it ran in.
    result = _dispatch_cmd(tmp_path, monkeypatch,
                           eval_harness_fixtures.fake_engine_command("pass"))
    run = result["run"]
    answered = _final_text(result["attempt"] / "session.jsonl")

    records.validate_record("engine_run", run)
    assert run["argv"] == _engine_argv("pass", result["prompt"])
    assert run["argv"][0] == sys.executable
    assert run["launch"] == "started"
    assert run["exit"] == 0
    assert run["timed_out"] is False
    assert run["wall_s"] > 0
    assert run["identity"] == FAKE_IDENTITY
    assert run["completion"] == "complete"
    assert run["final_message_bytes"] == len(answered.encode("utf-8"))
    assert run["usage"] == _expected_usage(input_tokens=412, output_tokens=37)
    assert run["first_edit_s"] is None
    assert run["usage_limit"] == "unchecked"
    # The edit landed in the clone, which is the directory the engine ran in.
    assert (result["clone"] / "calc.py").read_text(
        encoding="utf-8") == eval_harness_fixtures.FIXED_IMPL


def test_reports_no_identity_and_an_incomplete_stream_for_a_silent_fake_run(
        tmp_path, monkeypatch):
    # The silent mode announces nothing and its transcript ends on "length": the
    # run exited 0 and edited the tree, and neither of those is evidence enough.
    result = _dispatch_cmd(tmp_path, monkeypatch,
                           eval_harness_fixtures.fake_engine_command("silent-edit"))
    run = result["run"]

    records.validate_record("engine_run", run)
    assert run["launch"] == "started"
    assert run["exit"] == 0
    assert run["identity"] is None
    assert run["completion"] == "incomplete"


def test_stops_a_hung_fake_run_at_the_bound_and_reaps_what_it_spawned(tmp_path, monkeypatch):
    # The hang mode announces itself, starts a heartbeat child and sleeps for
    # ten minutes. The bound fires long before that: the run is marked timed
    # out with no exit of its own, its wall time is the bound plus a reap, and
    # the heartbeat it left behind is dead by the time dispatch returns.
    heartbeat = tmp_path / "beat.txt"
    monkeypatch.setenv(HEARTBEAT_ENV, str(heartbeat))

    result = _dispatch_cmd(tmp_path, monkeypatch,
                           eval_harness_fixtures.fake_engine_command("hang"),
                           bound_s=HANG_BOUND_S)
    run = result["run"]

    records.validate_record("engine_run", run)
    assert run["launch"] == "started"
    assert run["timed_out"] is True
    assert run["exit"] is None
    assert HANG_BOUND_S <= run["wall_s"] < HANG_WALL_CEILING_S
    # The heartbeat was beating before the bound fired, and is not any more.
    assert heartbeat.is_file()
    assert _stopped_growing(heartbeat)


# -- dispatch: the usage-limit checker -------------------------------------


@pytest.mark.parametrize("exit_code, verdict",
                         [(0, "hit"), (1, "clear"), (2, "clear")],
                         ids=["exit-0-is-limit-stuck", "exit-1-is-clear", "exit-2-is-clear"])
def test_reads_the_usage_limit_checker_the_way_the_checker_answers(
        tmp_path, monkeypatch, exit_code, verdict):
    # The checker prints a reset epoch and exits 0 when the account is STUCK, so
    # the intuitive reading of an exit code is the wrong one here.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    argv_file = tmp_path / "checker-argv.txt"
    checker = eval_harness_fixtures.write_argv_recording_stub(
        bin_dir, "usage-limit-check", argv_file, exit_code=exit_code, stdout="1900000000")

    result = _dispatch_cmd(tmp_path, monkeypatch,
                           eval_harness_fixtures.fake_engine_command("pass"),
                           settings=_settings(usage_limit_cmd=checker))

    assert result["run"]["usage_limit"] == verdict
    recorded = argv_file.read_text(encoding="utf-8").splitlines()
    assert "--log" in recorded
    assert Path(recorded[recorded.index("--log") + 1]) == result["attempt"] / "out.txt"
    records.validate_record("engine_run", result["run"])


def test_leaves_usage_limit_unchecked_when_the_configured_checker_is_not_there(
        tmp_path, monkeypatch):
    # A checker that cannot be run observed nothing, and nothing observed is
    # neither "clear" nor "hit".
    result = _dispatch_cmd(tmp_path, monkeypatch,
                           eval_harness_fixtures.fake_engine_command("pass"),
                           settings=_settings(usage_limit_cmd=tmp_path / "no-such-checker"))

    assert result["run"]["usage_limit"] == "unchecked"
    records.validate_record("engine_run", result["run"])


# -- dispatch: what launched and what did not ------------------------------


def test_records_a_no_launch_attempt_whole_with_null_measurements(tmp_path, monkeypatch):
    # Nothing was created, so nothing was measured - but the attempt still has
    # to be scoreable, which means the whole block is written anyway.
    result = _dispatch_cmd(tmp_path, monkeypatch, "cmd:" + str(tmp_path / "no-such-engine"))
    run = result["run"]

    records.validate_record("engine_run", run)
    assert run["launch"] == "not-started"
    assert run["argv"] != []
    assert run["exit"] is None
    assert run["timed_out"] is False
    assert run["wall_s"] is None
    assert run["identity"] is None
    assert run["completion"] == "unknown"
    assert run["final_message_bytes"] is None
    assert run["first_edit_s"] is None
    assert run["usage"] == dict.fromkeys(records.USAGE_KEYS)
    assert run["usage_limit"] == "unchecked"


def test_records_a_created_process_as_started_even_when_the_engine_never_ran(
        tmp_path, monkeypatch):
    # The interpreter exists and was created; the script it was pointed at does
    # not. Only a pre-creation failure may be blamed on the harness, so this is
    # a started run that failed rather than a launch that never happened.
    result = _dispatch_cmd(tmp_path, monkeypatch, "cmd:" + str(tmp_path / "absent_engine.py"))
    run = result["run"]

    records.validate_record("engine_run", run)
    assert run["launch"] == "started"
    assert run["exit"] is not None and run["exit"] != 0
    assert run["identity"] is None
    assert run["completion"] == "unknown"


# -- record_versions -------------------------------------------------------


@pytest.mark.parametrize("engine_ids, probes_pi, probes_claude",
                         [(["qwen"], True, False),
                          (["sonnet"], False, True),
                          (["qwen", "sonnet"], True, True),
                          (["cmd1", "cmd2"], False, False)],
                         ids=["qwen-only", "sonnet-only", "both", "fake-only"])
def test_probes_a_version_only_for_the_engines_the_run_uses(
        tmp_path, monkeypatch, engine_ids, probes_pi, probes_claude):
    # A fake-only run has to work on a host with neither CLI installed and no
    # server reachable, so it may run no probe and open no connection at all.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    pi_argv, claude_argv = tmp_path / "pi-argv.txt", tmp_path / "claude-argv.txt"
    eval_harness_fixtures.write_argv_recording_stub(bin_dir, "pi", pi_argv, stdout=PI_VERSION)
    eval_harness_fixtures.write_argv_recording_stub(bin_dir, "claude", claude_argv,
                                                    stdout=CLAUDE_VERSION)
    monkeypatch.setenv("PATH", str(bin_dir) + os.pathsep + os.environ["PATH"])
    monkeypatch.setattr(socket.socket, "connect", _no_network)

    versions = engines.record_versions(engine_ids, _settings(qwen_provider=QWEN_PROVIDER,
                                                             qwen_model=QWEN_MODEL,
                                                             sonnet_model=SONNET_MODEL))

    assert set(versions) == {"pi", "claude"}
    assert pi_argv.exists() is probes_pi
    assert claude_argv.exists() is probes_claude
    if probes_pi:
        assert pi_argv.read_text(encoding="utf-8").splitlines() == ["--version"]
        assert PI_VERSION in versions["pi"]
    else:
        assert versions["pi"] is None
    if probes_claude:
        assert claude_argv.read_text(encoding="utf-8").splitlines() == ["--version"]
        assert CLAUDE_VERSION in versions["claude"]
    else:
        assert versions["claude"] is None


def test_records_a_null_version_when_the_probed_cli_is_not_installed(tmp_path, monkeypatch):
    # A host without pi cannot answer `pi --version`; the run still has to be
    # recorded, so the probe that found nothing reports null and raises nothing.
    empty_bin = tmp_path / "empty-bin"
    empty_bin.mkdir()
    monkeypatch.setenv("PATH", str(empty_bin))
    monkeypatch.setattr(socket.socket, "connect", _no_network)

    versions = engines.record_versions(["qwen"], _settings(qwen_provider=QWEN_PROVIDER,
                                                           qwen_model=QWEN_MODEL))

    assert versions == {"pi": None, "claude": None}


# -- server_root -----------------------------------------------------------


@pytest.mark.parametrize("provider_url, expected",
                         [("http://h:8002/v1", "http://h:8002"),
                          ("http://h:8002/v1/", "http://h:8002"),
                          ("http://h/proxy/v1/", "http://h/proxy"),
                          ("http://h/v1/v1", "http://h/v1"),
                          ("http://h:8002", "http://h:8002"),
                          ("http://h:8002/", "http://h:8002")],
                         ids=["v1", "v1-slash", "proxy-path", "two-v1", "bare", "bare-slash"])
def test_strips_exactly_one_trailing_v1_from_a_provider_url(provider_url, expected):
    # One component, and only a trailing one: a proxy path above it is part of
    # the address, and a URL that never named /v1 keeps all but its slash.
    assert engines.server_root(provider_url) == expected


# -- fetch_server_props ----------------------------------------------------


@pytest.mark.parametrize("declared", ["xhigh", None], ids=["declared", "unset"])
def test_reads_the_server_block_from_a_v1_provider_url(props_server, connections, declared):
    # The provider URL ends in /v1 and the server answers /props only, so a
    # request to /v1/props reaches a 404 and reports nothing. The values are
    # the mock's, and the mock has to have been asked for them: a fetch that
    # never connected to its port read nothing. The declared effort is the
    # operator's own label: it is carried and never verified, while what the
    # server says about supporting one is reported separately.
    record = engines.fetch_server_props(props_server + "/v1", declared)

    assert _reached(connections, props_server)
    records.validate_record("server", record)
    assert set(record) == set(records.SERVER_KEYS)
    assert record["n_ctx"] == 131072
    assert record["model_alias"] == "mock-candidate"
    assert record["build_info"] == "mock-b0000"
    assert record["sampling"] == MOCK_SAMPLING
    assert record["supports_reasoning_effort"] is True
    assert record["declared_effort"] == declared
    assert record["metadata_error"] is None


@PROVIDER_SUFFIXES
@pytest.mark.parametrize("declared", ["xhigh", None], ids=["declared", "unset"])
def test_reports_the_values_the_server_actually_served(owned_props_server, suffix, declared):
    # This server answers /props with numbers drawn for this test alone, so the
    # only way to report them is to read the body it sent: a 200 status and a
    # remembered payload look the same on the mock and different here. It also
    # writes down what it was asked for, which has to be /props at the root
    # whatever the provider URL's tail - never /v1/props.
    record = engines.fetch_server_props(owned_props_server["url"] + suffix, declared)

    assert set(owned_props_server["paths"]) == {"/props"}
    records.validate_record("server", record)
    assert record == _served_block(owned_props_server["payload"], declared)


def test_reports_null_metadata_with_a_diagnostic_when_props_is_unavailable(
        props_server, connections):
    # A live server that serves no /props under the root this URL implies: the
    # run still has to be recordable, so every value is null and the reason is
    # kept beside them. The server was asked, and answered with the 404 the
    # diagnostic reports; nothing here is decided from the URL's shape alone.
    record = engines.fetch_server_props(props_server + "/v1/models", "xhigh")

    assert _reached(connections, props_server)
    records.validate_record("server", record)
    assert isinstance(record["metadata_error"], str) and record["metadata_error"]
    assert record["declared_effort"] == "xhigh"
    assert [record[key] for key in records.SERVER_KEYS[:5]] == [None] * 5


@pytest.mark.parametrize("tail, served", [("/v1", True), ("/v1/models", False)],
                         ids=["props-served", "props-unavailable"])
def test_keeps_a_credential_out_of_the_server_record(owned_props_server, tail, served):
    # An operator's provider URL can carry a password. The fetch still reaches
    # the server the URL names and reads the metadata it served - this test's
    # own numbers, not the mock's - and nothing stored may repeat the password:
    # not a value, and not the diagnostic a 404 leaves behind either.
    url = owned_props_server["url"].replace("http://", "http://evaluser:%s@" % MUST_NOT_LEAK)

    record = engines.fetch_server_props(url + tail, "xhigh")

    assert owned_props_server["paths"]
    records.validate_record("server", record)
    if served:
        assert record == _served_block(owned_props_server["payload"], "xhigh")
    else:
        assert isinstance(record["metadata_error"], str) and record["metadata_error"]
        assert [record[key] for key in records.SERVER_KEYS[:5]] == [None] * 5
    assert MUST_NOT_LEAK not in json.dumps(record)
