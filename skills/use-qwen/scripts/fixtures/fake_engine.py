"""A fake coding engine: one named failure mode per run, no model anywhere.

Run as `python fake_engine.py <mode> <prompt-file>` with the cwd set to a repo
built by `eval_harness_fixtures.build_fixture_repo`. The attempt directory and
the heartbeat path come from the environment, so a test can point them
anywhere. This file is a script; nothing imports it.
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

IMPL = Path("calc.py")
ORACLE = Path("test_calc.py")
STRAY = Path("stray.txt")
NOTES = Path("notes.md")

BEAT_SECONDS = 600.0

# eval_harness_fixtures.FIXED_IMPL, byte for byte: the impl the task commit
# carries, not merely text the oracle happens to accept.
FIXED_IMPL = '''"""Arithmetic the oracle test checks."""


def add(left, right):
    return left + right
'''

# Green against the *broken* impl: the oracle is rewritten to match the bug.
MATCHING_ORACLE = '''from calc import add


def test_add_returns_the_sum_of_its_arguments():
    assert add(2, 3) == -1
'''

VACUOUS_ORACLE = '''from calc import add


def test_add_returns_the_sum_of_its_arguments():
    """It describes the sum instead of checking it."""
    add(2, 3)
'''

# No two modes may report the same thing: one sentence cannot honestly cover
# both a fix and a run that edited nothing.
MESSAGES = {
    "pass": "Fixed add() so the oracle test passes.",
    "noop": "I read the prompt and decided nothing needed changing.",
    "stray": "Fixed add() and dropped a scratch file beside it.",
    "drop": "Wrote up the notes but never got to add().",
    "mutate-test": "Rewrote the oracle test to match what add() already returns.",
    "vacuous": "Rewrote the oracle test to describe add() instead of checking it.",
    "exit1": "I gave up before touching add().",
    "spawn-and-exit": "Fixed add() and left a background job running.",
    "silent-edit": "Fixed add() and then ran out of room mid-",
}


def _beat(heartbeat: Path) -> None:
    deadline = time.monotonic() + BEAT_SECONDS
    while time.monotonic() < deadline:
        with heartbeat.open("a", encoding="utf-8") as beats:
            beats.write("beat\n")
        time.sleep(0.1)


def _spawn_heartbeat() -> None:
    """Start the heartbeat child, which outlives its parent.

    No `setsid`: the child stays in the process group it was born into, so a
    group kill still contains it.
    """
    subprocess.Popen(
        [sys.executable, __file__, "heartbeat"],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _edit_working_tree(mode: str) -> None:
    """Leave behind exactly what this mode is named for, relative to the cwd."""
    if mode in ("pass", "stray", "silent-edit", "spawn-and-exit"):
        IMPL.write_text(FIXED_IMPL, encoding="utf-8")
    if mode == "stray":
        STRAY.write_text("scratch output nothing asked for\n", encoding="utf-8")
    if mode == "drop":
        NOTES.write_text("what I would have changed in calc.py\n", encoding="utf-8")
    if mode == "mutate-test":
        ORACLE.write_text(MATCHING_ORACLE, encoding="utf-8")
    if mode == "vacuous":
        ORACLE.write_text(VACUOUS_ORACLE, encoding="utf-8")


def _write_session(prompt: str, text: str, stop_reason: str) -> None:
    stamp = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
    events = [
        {
            "type": "user",
            "timestamp": stamp,
            "message": {"role": "user", "content": [{"type": "text", "text": prompt}]},
        },
        {
            "type": "assistant",
            "timestamp": stamp,
            "message": {
                "role": "assistant",
                "content": [{"type": "text", "text": text}],
                "stop_reason": stop_reason,
                "usage": {"input_tokens": 412, "output_tokens": 37},
            },
        },
    ]
    session = Path(os.environ["FAKE_ENGINE_ATTEMPT_DIR"]) / "session.jsonl"
    session.write_text(
        "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8"
    )


def main() -> int:
    mode = sys.argv[1]
    if mode == "heartbeat":
        _beat(Path(os.environ["FAKE_ENGINE_HEARTBEAT"]))
        return 0

    prompt = Path(sys.argv[2]).read_text(encoding="utf-8")
    if mode != "silent-edit":
        print(f"Using engine 'cmd:{mode}'", file=sys.stderr, flush=True)
    if mode == "hang":
        _spawn_heartbeat()
        time.sleep(BEAT_SECONDS)
        return 0

    _edit_working_tree(mode)
    if mode == "silent-edit":
        # The truncation shows in the transcript and nowhere else.
        _write_session(prompt, MESSAGES[mode], "length")
    else:
        print(MESSAGES[mode], flush=True)
        _write_session(prompt, MESSAGES[mode], "end_turn")
    if mode == "spawn-and-exit":
        _spawn_heartbeat()
    return 1 if mode == "exit1" else 0


if __name__ == "__main__":
    sys.exit(main())
