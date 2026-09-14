"""Read one attempt's session transcript and its captured output.

Answers four questions about a run: did the engine finish, how big was its
final message, how long until its first successful edit, and what did it cost.
These answers gate validity, so missing evidence never reads as success. Two
transcript shapes are accepted, Anthropic's and pi's; a transcript is one or
the other, never a mix.
"""
import json
from datetime import datetime
from pathlib import Path

from eval_harness.records import USAGE_KEYS

# An allowlist: only these stop reasons finish a turn, so every other observed
# one, recognised or not, is a broken stream.
_FINISHED = {"claude": "end_turn", "pi": "stop"}
_STOP_KEY = {"claude": "stop_reason", "pi": "stopReason"}
_EDIT_TOOLS = {"claude": ("Write", "Edit", "MultiEdit", "NotebookEdit"),
               "pi": ("edit", "write")}
_TOKEN_NAMES = {"claude": {"input_tokens": "input_tokens", "output_tokens": "output_tokens",
                           "cache_read_tokens": "cache_read_input_tokens",
                           "cache_write_tokens": "cache_creation_input_tokens"},
                "pi": {"input_tokens": "input", "output_tokens": "output",
                       "cache_read_tokens": "cacheRead", "cache_write_tokens": "cacheWrite"}}


def read_events(session_path: Path | None, out_path: Path) -> dict:
    """Answer the four evidence questions about one attempt's run."""
    transcript = _read_transcript(session_path) if session_path is not None else None
    if transcript is None:
        # No transcript to read: the capture is all there is, and wrapper
        # diagnostics are not a final message, so this cannot read as success.
        # A helper that never launched writes no capture either, and that run
        # is still scored rather than crashed on.
        try:
            captured = len(out_path.read_bytes())
        except OSError:
            captured = None
        return {"completion": "unknown", "final_message_bytes": captured,
                "first_edit_s": None, "usage": dict.fromkeys(USAGE_KEYS)}
    events, malformed = transcript
    message, shape = _terminal_message(events)
    text, unreadable = _final_text(message)
    return {"completion": _completion(message, shape, text, malformed or unreadable),
            "final_message_bytes": len(text.encode("utf-8")) if message else None,
            "first_edit_s": _first_edit_s(events),
            "usage": _usage(events)}


def _read_transcript(session_path: Path) -> tuple[list, bool] | None:
    """The transcript's events and whether any line was unreadable, or None
    when nothing can be read through the path at all."""
    try:
        text = session_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None
    events, malformed = [], False
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except ValueError:
            malformed = True
            continue
        if isinstance(event, dict):
            events.append(event)
        else:
            # Parsed, but carries no event: the stream was observed broken.
            malformed = True
    return events, malformed


def _assistant_shape(event: dict) -> str | None:
    """The shape whose assistant message this event carries, or None when it
    carries none: a streaming delta is not an assistant message."""
    message = event.get("message")
    if not isinstance(message, dict):
        return None
    if event.get("type") == "assistant":
        return "claude"
    if event.get("type") == "message" and message.get("role") == "assistant":
        return "pi"
    return None


def _terminal_message(events: list) -> tuple[dict | None, str | None]:
    """The last assistant message and the shape it arrived in, found by
    scanning: events keep arriving after a run has answered."""
    for event in reversed(events):
        shape = _assistant_shape(event)
        if shape is not None:
            return event["message"], shape
    return None, None


def _final_text(message: dict | None) -> tuple[str, bool]:
    """The message's well-formed text blocks joined, and whether any of its
    content was unreadable; a thinking block is never the answer."""
    if message is None:
        return "", False
    content = message.get("content")
    if not isinstance(content, list):
        return "", True
    texts, unreadable = [], False
    for block in content:
        if not isinstance(block, dict):
            unreadable = True
        elif block.get("type") == "text":
            if isinstance(block.get("text"), str):
                texts.append(block["text"])
            else:
                unreadable = True
    return "".join(texts), unreadable


def _completion(message: dict | None, shape: str | None, text: str, malformed: bool) -> str:
    """A stream observed to break outranks whatever text it left behind."""
    if malformed:
        return "incomplete"
    if message is None:
        return "unknown"
    if text and message.get(_STOP_KEY[shape]) == _FINISHED[shape]:
        return "complete"
    return "incomplete"


def _usage(events: list) -> dict:
    """Every assistant message's usage summed once; streaming deltas never
    count. Claude Code writes one assistant line per content block of an API
    message, each carrying its id and usage, so lines sharing an id are one
    message. A field is the sum over the messages that report it as a number
    and stays None when none does."""
    usage = dict.fromkeys(USAGE_KEYS)
    seen: set = set()
    for event in events:
        shape = _assistant_shape(event)
        if shape is None:
            continue
        message = event["message"]
        message_id = message.get("id")
        if message_id is not None:
            if message_id in seen:
                continue
            seen.add(message_id)
        reported = message.get("usage")
        if not isinstance(reported, dict):
            continue
        values = {key: reported.get(name) for key, name in _TOKEN_NAMES[shape].items()}
        if shape == "pi":
            cost = reported.get("cost")
            values["cost_usd"] = cost.get("total") if isinstance(cost, dict) else None
        for key, value in values.items():
            if isinstance(value, (int, float)):
                usage[key] = (usage[key] or 0) + value
    # A locally served model bills zero for every field, which is money that
    # was never reported rather than money measured as nothing.
    usage["cost_usd"] = usage["cost_usd"] or None
    return usage


def _first_edit_s(events: list) -> float | None:
    """Seconds from the transcript's first event to the first successful write
    or edit result, or None when the run never landed one."""
    start = _event_time(events[0]) if events else None
    edited = _first_edit_time(events)
    if start is None or edited is None:
        return None
    return (edited - start).total_seconds()


def _first_edit_time(events: list) -> datetime | None:
    called: dict = {}
    for event in events:
        message = event.get("message")
        if not isinstance(message, dict):
            continue
        if event.get("type") == "message":
            if _is_pi_edit(message):
                return _event_time(event)
        elif _carries_claude_edit(message, called):
            return _event_time(event)
    return None


def _is_pi_edit(message: dict) -> bool:
    return (message.get("role") == "toolResult" and not message.get("isError")
            and message.get("toolName") in _EDIT_TOOLS["pi"])


def _carries_claude_edit(message: dict, called: dict) -> bool:
    """Record this message's tool calls by name, then answer whether it carries
    a successful result of one of them that was an edit."""
    content = message.get("content")
    for block in content if isinstance(content, list) else []:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "tool_use":
            called[block.get("id")] = block.get("name")
        elif (block.get("type") == "tool_result" and not block.get("is_error")
                and called.get(block.get("tool_use_id")) in _EDIT_TOOLS["claude"]):
            return True
    return False


def _event_time(event: dict) -> datetime | None:
    """The event's own timestamp, in either shape's spelling of ISO-8601."""
    value = event.get("timestamp")
    if not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
