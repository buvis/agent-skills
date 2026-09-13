"""Constants and builders shared by the eval_harness events and engines test modules."""
from datetime import datetime, timedelta, timezone

from eval_harness import engines
from eval_harness import records

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

# A provider and two model ids no built-in default could guess, so an argv that
# carries them proves the settings were read rather than a constant used.
QWEN_PROVIDER = "qwen-eval-provider"
QWEN_MODEL = "qwen3-coder-30b-a3b-instruct"
SONNET_MODEL = "claude-sonnet-4-5-20260101"


def _stamp(offset_s):
    """A claude-shape stamp: whole seconds, `offset_s` after the run's first event."""
    return (BASE + timedelta(seconds=offset_s)).strftime("%Y-%m-%dT%H:%M:%SZ")


STAMP = _stamp(0)


def _assistant(text, stop_reason="end_turn", usage=None, stamp=STAMP):
    message = {"role": "assistant", "content": [{"type": "text", "text": text}],
               "stop_reason": stop_reason}
    if usage is not None:
        message["usage"] = usage
    return {"type": "assistant", "timestamp": stamp, "message": message}


def _user(text, stamp=STAMP):
    return {"type": "user", "timestamp": stamp,
            "message": {"role": "user", "content": [{"type": "text", "text": text}]}}


def _expected_usage(**tokens):
    """The five contract keys, with every field these tokens do not name left null."""
    usage = dict.fromkeys(records.USAGE_KEYS)
    usage.update(tokens)
    return usage


def _settings(**overrides):
    """EngineSettings with every field null but the ones a case names."""
    fields = dict.fromkeys(("qwen_provider", "qwen_model", "sonnet_model",
                            "usage_limit_cmd", "server_reasoning_effort"))
    fields.update(overrides)
    return engines.EngineSettings(**fields)
