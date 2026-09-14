"""Tests for eval_harness/events.py: summing usage over every assistant message,
reading a malformed message payload without raising, and reading is_error by
its value rather than its presence."""
import pytest

from eval_harness import events
from eval_harness import records
from eval_harness_engine_helpers import FINAL_TEXT, _assistant, _expected_usage, _stamp, _user
from test_eval_events import (DELTA_USAGE, PI_COSTS, _claude_usage, _out, _pi_assistant,
                              _pi_stamp, _pi_start, _pi_tool_call, _pi_tool_result, _pi_usage,
                              _session, _tool_result, _tool_use)

FINAL_BYTES = len(FINAL_TEXT.encode("utf-8"))

# The token counts the two messages of a one-tool pi run report: the message
# that called the tool, then the terminal answer.
CALL_TOKENS = {"input_tokens": 810, "output_tokens": 64, "cache_read_tokens": 200,
               "cache_write_tokens": 90}
ANSWER_TOKENS = {"input_tokens": 1200, "output_tokens": 36, "cache_read_tokens": 100,
                 "cache_write_tokens": 10}

# One distinct usage block per assistant message of a run that called four
# tools before answering. Every count is positive, so any proper subset of the
# five (a trailing window of two, three or four, the first and the last, the
# largest alone) sums to less than the whole: 2116/1314/325/112.
FIVE_USAGES = [CALL_TOKENS, ANSWER_TOKENS,
               {"input_tokens": 5, "output_tokens": 1204, "cache_read_tokens": 3,
                "cache_write_tokens": 7},
               {"input_tokens": 41, "output_tokens": 2, "cache_read_tokens": 9,
                "cache_write_tokens": 1},
               {"input_tokens": 60, "output_tokens": 8, "cache_read_tokens": 13,
                "cache_write_tokens": 4}]

# What a terminal message's content can look like when its payload is broken,
# beside the byte count of the well-formed text blocks that stay readable: the
# text slot holding a number, null or a list; a block that is not an object at
# all; and a content slot that is not a list. The count is 0 when nothing is
# readable and FINAL_TEXT's 52 bytes when the broken entry sits beside a good
# block, so the reader has to count the good blocks rather than give up on the
# whole message or on the whole run.
MALFORMED_CONTENTS = [([{"type": "text", "text": 42}], 0),
                      ([{"type": "text", "text": None}], 0),
                      ([{"type": "text", "text": ["all", "done"]}], 0),
                      ([{"type": "text", "text": FINAL_TEXT}, {"type": "text", "text": 42}],
                       FINAL_BYTES),
                      ([{"type": "text", "text": FINAL_TEXT}, {"type": "text", "text": None}],
                       FINAL_BYTES),
                      ([{"type": "text", "text": FINAL_TEXT}, "just a string"], FINAL_BYTES),
                      ("just a string", 0)]
MALFORMED_IDS = ["number-text", "null-text", "list-text", "number-text-beside-a-good-block",
                 "null-text-beside-a-good-block", "string-block", "string-content"]


# -- helpers ---------------------------------------------------------------


def _with_message(event, **fields):
    """The same event with these fields set on its message, whichever shape."""
    return {**event, "message": {**event["message"], **fields}}


def _claude_tool_run(first, final):
    """A Claude run that answered after one tool call: the message that called
    the tool reports `first`, the terminal message reports `final`, and a
    streaming delta claiming 9000 of everything precedes each of them."""
    return [_user("fix the parser"),
            {"type": "message_delta", "timestamp": _stamp(1), "usage": DELTA_USAGE},
            _assistant("looking at the parser", stop_reason="tool_use", stamp=_stamp(1),
                       usage=_claude_usage(**first)),
            _tool_result("t1", _stamp(2)),
            {"type": "message_delta", "timestamp": _stamp(3), "usage": DELTA_USAGE},
            _assistant(FINAL_TEXT, stamp=_stamp(3), usage=_claude_usage(**final))]


def _pi_tool_run(first, final):
    """The pi mirror: the message that called the tool reports `first`, the
    terminal message reports `final`, each a cost name plus its token counts."""
    return [_pi_start(),
            _pi_assistant("looking at the parser", stop_reason="toolUse", stamp=_pi_stamp(1),
                          usage=_pi_usage(**first)),
            _pi_tool_result("c1", "read", _pi_stamp(2)),
            _pi_assistant(FINAL_TEXT, stamp=_pi_stamp(3), usage=_pi_usage(**final))]


def _claude_long_tool_run(usages):
    """A Claude run that called four tools (Read, Read, Grep, Edit) before
    answering: five finalized assistant messages, each reporting one of
    `usages`."""
    lines = [_user("fix the parser")]
    for index, name in enumerate(["Read", "Read", "Grep", "Edit"]):
        call = _tool_use(f"t{index}", name, _stamp(2 * index + 1))
        lines.append(_with_message(call, usage=_claude_usage(**usages[index])))
        lines.append(_tool_result(f"t{index}", _stamp(2 * index + 2)))
    lines.append(_assistant(FINAL_TEXT, stamp=_stamp(9), usage=_claude_usage(**usages[4])))
    return lines


def _pi_long_tool_run(usages):
    """The pi mirror: four toolUse stops, each reporting one of `usages`, then
    the stop that answers with the fifth."""
    lines = [_pi_start()]
    for index, name in enumerate(["read", "read", "grep", "edit"]):
        lines.append(_pi_assistant("looking", stop_reason="toolUse", stamp=_pi_stamp(2 * index + 1),
                                   usage=_pi_usage(**usages[index])))
        lines.append(_pi_tool_result(f"c{index}", name, _pi_stamp(2 * index + 2)))
    lines.append(_pi_assistant(FINAL_TEXT, stamp=_pi_stamp(9), usage=_pi_usage(**usages[4])))
    return lines


def _claude_malformed_run(delay, content):
    """Usage on the message that called the tool, a successful edit `delay`
    seconds in, then a terminal end_turn message whose content is `content`."""
    return [_user("fix the parser", _stamp(0)),
            _assistant("looking at the parser", stop_reason="tool_use", stamp=_stamp(1),
                       usage=_claude_usage(input_tokens=810, output_tokens=64)),
            _tool_use("t1", "Edit", _stamp(delay - 1)),
            _tool_result("t1", _stamp(delay)),
            _with_message(_assistant(FINAL_TEXT, stamp=_stamp(delay + 1)), content=content)]


def _pi_malformed_run(delay, content):
    """The pi mirror: a terminal stop message whose content is `content`."""
    return [_pi_start(),
            _pi_assistant("looking at the parser", stop_reason="toolUse", stamp=_pi_stamp(1),
                          usage=_pi_usage(input_tokens=810, output_tokens=64)),
            _pi_tool_call("c1", "edit", _pi_stamp(delay - 0.5)),
            _pi_tool_result("c1", "edit", _pi_stamp(delay)),
            _with_message(_pi_assistant(FINAL_TEXT, stamp=_pi_stamp(delay + 1)), content=content)]


def _successful_result(tool_id, stamp):
    """The user event a real Claude Code transcript writes for a result that
    succeeded: is_error is present and false, not absent."""
    block = {"type": "tool_result", "tool_use_id": tool_id, "content": "ok", "is_error": False}
    return {"type": "user", "timestamp": stamp,
            "message": {"role": "user", "content": [block]}}


def _flagged_edited_run(delay):
    """A read, the first successful edit `delay` seconds in, a second edit and
    the answer, with is_error: false written on every result."""
    return [_user("fix the parser", _stamp(0)),
            _tool_use("t1", "Read", _stamp(1)),
            _successful_result("t1", _stamp(2)),
            _tool_use("t2", "Edit", _stamp(delay - 1)),
            _successful_result("t2", _stamp(delay)),
            _tool_use("t3", "Write", _stamp(delay + 2)),
            _successful_result("t3", _stamp(delay + 4)),
            _assistant(FINAL_TEXT, stamp=_stamp(delay + 5))]


def _flagged_failed_edit_run():
    """A read flagged is_error: false, then the run's only edit flagged true."""
    return [_user("fix the parser", _stamp(0)),
            _tool_use("t1", "Read", _stamp(1)),
            _successful_result("t1", _stamp(2)),
            _tool_use("t2", "Edit", _stamp(4)),
            _tool_result("t2", _stamp(5), failed=True),
            _assistant(FINAL_TEXT, stamp=_stamp(6))]


def _pi_lone_edit_run(delay, flagged=True):
    """The pi shape, where a successful result has always carried isError:
    false; with `flagged` off the result carries no isError key at all."""
    result = _pi_tool_result("c1", "edit", _pi_stamp(delay))
    if not flagged:
        del result["message"]["isError"]
    return [_pi_start(),
            _pi_tool_call("c1", "edit", _pi_stamp(delay - 0.5)),
            result,
            _pi_assistant(FINAL_TEXT, stamp=_pi_stamp(delay + 1))]


def _orphan_result_run():
    """A read, then a successful result no tool call ever announced."""
    return [_user("fix the parser", _stamp(0)),
            _tool_use("t1", "Read", _stamp(1)),
            _successful_result("t1", _stamp(2)),
            _successful_result("orphan", _stamp(4)),
            _assistant(FINAL_TEXT, stamp=_stamp(5))]


# -- usage is summed over every assistant message ---------------------------


@pytest.mark.parametrize("first, final",
                         [({"input_tokens": 810, "output_tokens": 64, "cache_read_tokens": 200,
                            "cache_write_tokens": 90},
                           {"input_tokens": 1200, "output_tokens": 36, "cache_read_tokens": 100,
                            "cache_write_tokens": 10}),
                          ({"input_tokens": 5, "output_tokens": 1204, "cache_read_tokens": 3,
                            "cache_write_tokens": 7},
                           {"input_tokens": 41, "output_tokens": 2, "cache_read_tokens": 9,
                            "cache_write_tokens": 1})],
                         ids=["hundreds", "lopsided"])
def test_sums_usage_over_both_assistant_messages_of_a_claude_tool_run(tmp_path, first, final):
    # The run answered after one tool call, so it has two finalized assistant
    # messages and its usage is what both of them cost: 2010/100/300/100 in the
    # first case. Each sum is a number neither message reports alone, the two
    # pairs sum differently, and the deltas claim 9000 of everything, so the
    # terminal message, the earlier one, the largest usage seen and a
    # remembered total all miss. The terminal message alone still decides
    # completion and the final text.
    session = _session(tmp_path, _claude_tool_run(first, final))

    result = events.read_events(session, _out(tmp_path))

    assert result["usage"] == _expected_usage(**{key: first[key] + final[key] for key in first})
    records.validate_record("usage", result["usage"])
    assert result["completion"] == "complete"
    assert result["final_message_bytes"] == FINAL_BYTES


@pytest.mark.parametrize("first, final, expected_cost",
                         [(dict(CALL_TOKENS, cost="billed"), dict(ANSWER_TOKENS, cost="cheap"),
                           pytest.approx(PI_COSTS["billed"]["total"] + PI_COSTS["cheap"]["total"])),
                          (dict(CALL_TOKENS, cost="free"), dict(ANSWER_TOKENS, cost="free"), None),
                          (dict(CALL_TOKENS, cost="billed"), dict(CALL_TOKENS, cost="billed"),
                           pytest.approx(2 * PI_COSTS["billed"]["total"]))],
                         ids=["billed-then-cheap", "never-reported", "two-identical-turns"])
def test_sums_usage_and_money_over_both_assistant_messages_of_a_pi_tool_run(
        tmp_path, first, final, expected_cost):
    # The pi mirror: tokens sum to 2010/100/300/100 and money sums from each
    # message's cost.total, 0.0421 + 0.0006, which neither message reports on
    # its own. A run charged nothing on either message sums to 0, and 0 is
    # money never reported: cost_usd stays null rather than a measured zero.
    # Two turns that happened to cost the same are still two turns: a pi
    # message carries no id, so identical usage blocks (the same four counts
    # and the same cost) sum to 1620/128/400/180 and twice 0.0421, and a reader
    # that collapses equal blocks reports half of that.
    session = _session(tmp_path, _pi_tool_run(first, final))

    result = events.read_events(session, _out(tmp_path))

    assert result["usage"]["cost_usd"] == expected_cost
    assert result["usage"] == _expected_usage(
        cost_usd=expected_cost, **{key: first[key] + final[key] for key in CALL_TOKENS})
    records.validate_record("usage", result["usage"])
    assert result["completion"] == "complete"


@pytest.mark.parametrize("build", [_claude_long_tool_run, _pi_long_tool_run], ids=["claude", "pi"])
def test_sums_usage_over_all_five_assistant_messages_of_a_longer_tool_run(tmp_path, build):
    # Four tool calls before the answer make five finalized assistant messages,
    # each with a distinct usage block, and the run costs all five of them:
    # 2116/1314/325/112. Every count is positive, so a reader that keeps only a
    # trailing window of two, three or four messages, the first and the last,
    # or the largest block reports less than that in every field.
    session = _session(tmp_path, build(FIVE_USAGES))

    result = events.read_events(session, _out(tmp_path))

    assert result["usage"] == _expected_usage(
        **{key: sum(usage[key] for usage in FIVE_USAGES) for key in CALL_TOKENS})
    records.validate_record("usage", result["usage"])
    assert result["completion"] == "complete"


@pytest.mark.parametrize("first, final, expected",
                         [({"input_tokens": 412, "output_tokens": 37},
                           {"input_tokens": 7, "output_tokens": 3, "cache_read_tokens": 11,
                            "cache_write_tokens": 2},
                           {"input_tokens": 419, "output_tokens": 40, "cache_read_tokens": 11,
                            "cache_write_tokens": 2}),
                          ({"input_tokens": 412, "output_tokens": 37},
                           {"input_tokens": 5, "output_tokens": 1204},
                           {"input_tokens": 417, "output_tokens": 1241}),
                          ({"input_tokens": "12", "output_tokens": 37},
                           {"input_tokens": 7, "output_tokens": 3},
                           {"input_tokens": 7, "output_tokens": 40})],
                         ids=["one-message-reports-the-cache", "neither-reports-the-cache",
                              "a-count-that-is-not-a-number-is-unreported"])
def test_sums_each_field_over_only_the_messages_that_report_it(tmp_path, first, final, expected):
    # A field one message never reported is the other message's value: 11 and
    # 2 here, not null (it was reported once) and not a sum padded with a 0
    # (nothing was reported as 0). When neither message reports the cache
    # fields they stay null, and cost_usd, which no Claude message reports,
    # stays null in both cases. A count that is not a number ("12") was not
    # reported either: it never raises out of the reader, the other message's
    # 7 is the field's value, and the field the same message reported as a
    # number still sums.
    session = _session(tmp_path, _claude_tool_run(first, final))

    result = events.read_events(session, _out(tmp_path))

    assert result["usage"] == _expected_usage(**expected)
    records.validate_record("usage", result["usage"])


@pytest.mark.parametrize("first_id, second_id, first_counted",
                         [({"id": "msg_01ABC"}, {"id": "msg_01ABC"}, 1),
                          ({"id": "msg_02QRS9x"}, {"id": "msg_02QRS9x"}, 1),
                          ({"id": "msg_01ABC"}, {"id": "msg_01XYZ"}, 2),
                          ({"id": "msg_02QRS9x"}, {"id": "msg_03LMN"}, 2),
                          ({}, {}, 2)],
                         ids=["shared-id", "another-shared-id", "distinct-ids",
                              "other-distinct-ids", "no-ids"])
def test_counts_the_lines_of_one_api_message_once_by_their_shared_id(
        tmp_path, first_id, second_id, first_counted):
    # Claude Code writes one assistant line per content block of the same API
    # message, every line carrying the same message.id and the same usage: the
    # text line and the tool_use line below share msg_01ABC, so 412/37 counts
    # once and the run costs 419/40, not 831/77. The same holds for any id
    # (msg_02QRS9x shares nothing with msg_01ABC but its two lines are still
    # one message), so a reader that recognises one literal id misses it.
    # Lines with distinct ids, whatever prefix they share, or with no id at
    # all, are each a message of their own and count once each even though
    # their usage matches, so a reader that collapses equal usage blocks, or
    # equal missing ids, undercounts those runs.
    shared = _claude_usage(input_tokens=412, output_tokens=37)
    text_line = _with_message(
        _assistant("looking at the parser", stop_reason="tool_use", stamp=_stamp(1)),
        usage=shared, **first_id)
    call_line = _with_message(_tool_use("t1", "Read", _stamp(1)), usage=shared, **second_id)
    terminal = _with_message(
        _assistant(FINAL_TEXT, stamp=_stamp(3),
                   usage=_claude_usage(input_tokens=7, output_tokens=3)),
        id="msg_01DEF")
    session = _session(
        tmp_path,
        [_user("fix the parser"), text_line, call_line, _tool_result("t1", _stamp(2)), terminal],
    )

    result = events.read_events(session, _out(tmp_path))

    assert result["usage"] == _expected_usage(input_tokens=412 * first_counted + 7,
                                              output_tokens=37 * first_counted + 3)
    records.validate_record("usage", result["usage"])


# -- a malformed message payload never raises --------------------------------


@pytest.mark.parametrize("content, well_formed_bytes", MALFORMED_CONTENTS, ids=MALFORMED_IDS)
@pytest.mark.parametrize("build, delay",
                         [(_claude_malformed_run, 7), (_pi_malformed_run, 7.5)],
                         ids=["claude", "pi"])
def test_reads_a_malformed_terminal_message_as_incomplete_and_keeps_the_other_evidence(
        tmp_path, build, delay, content, well_formed_bytes):
    # The terminal message says end_turn (stop in pi) but its text cannot be
    # read, so it did not finish cleanly: incomplete, never a TypeError out of
    # the reader and never complete. The byte count is measured from the text
    # blocks that are readable, an int even when that is 0, because a terminal
    # message was found. Everything the transcript proved before that message
    # stays: the edit that succeeded `delay` seconds in and the usage the
    # earlier message reported.
    session = _session(tmp_path, build(delay, content))

    result = events.read_events(session, _out(tmp_path))

    assert result["completion"] == "incomplete"
    assert result["final_message_bytes"] == well_formed_bytes
    assert result["first_edit_s"] == delay
    assert result["usage"] == _expected_usage(input_tokens=810, output_tokens=64)
    records.validate_record("usage", result["usage"])


# -- is_error is read by its value ------------------------------------------


@pytest.mark.parametrize("lines, expected",
                         [(_flagged_edited_run(7), 7), (_flagged_edited_run(13), 13),
                          (_flagged_failed_edit_run(), None), (_pi_lone_edit_run(7.5), 7.5),
                          (_pi_lone_edit_run(7.5, flagged=False), 7.5),
                          (_orphan_result_run(), None)],
                         ids=["claude-7s", "claude-13s", "claude-true-flag", "pi-false-flag",
                              "pi-no-flag", "claude-orphan-result"])
def test_reads_is_error_by_its_value_and_not_by_its_presence(tmp_path, lines, expected):
    # A real Claude Code transcript writes is_error: false on every successful
    # result, so a reader that takes the key's presence for failure never times
    # an edit in a real run. Only a true flag marks a failed result: the run
    # whose only edit carries one has no edit to time, even though the read
    # before it succeeded with the same key set to false. The pi shape has
    # always spelled success as isError: false, and an absent flag there is
    # success too, the same reading in both shapes. A result no tool call ever
    # announced is not an edit, whatever its flag says: nothing names the tool.
    session = _session(tmp_path, lines)

    result = events.read_events(session, _out(tmp_path))

    assert result["first_edit_s"] == expected
