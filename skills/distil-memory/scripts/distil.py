"""Turn one surviving slice into a memory-file proposal.

A strong model gets the slice plus a few existing memory files as anchors, and
answers with either a discard line or a complete memory file. Everything it
sends back passes the proposal validators before it becomes a Proposal, so a
rambling or half-written answer leaves a named discard instead of a bad file.
"""

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import dedup
import funnel
import proposal

DISCARD_PREFIX = "DISCARD:"
EXAMPLE_COUNT = 4

_DISTIL_PROMPT = (
    "You are distilling one snippet of a coding session into a memory file.\n"
    "\n"
    "Decide first whether the snippet holds a durable fact: something that is\n"
    "still true after this session ends and would change how a later session\n"
    "acts. A transient detail (a test that passed, a build that succeeded, a\n"
    "step already finished) is not worth remembering.\n"
    "\n"
    "If it is transient, reply with one line: {discard} followed by the reason\n"
    "you turned it down, and nothing else.\n"
    "\n"
    "If it is durable, reply with the complete memory file and nothing else. It\n"
    "opens with YAML frontmatter fenced by ---, holding a kebab-case name, a\n"
    "quoted one-line description stating the fact itself, and a metadata\n"
    "mapping with node_type: memory and type: project. Below the fence write\n"
    "the fact, a **Why:** paragraph on what goes wrong without it, and a\n"
    "**How to apply:** paragraph naming the action to take. Where an anchor\n"
    "below covers a related rule, link it as [[its-name]] in the body.\n"
    "\n"
    "Anchors, for tone and shape:\n"
    "{examples}\n"
    "\n"
    "The snippet:\n"
    "{text}"
)


@dataclass(frozen=True)
class Discard:
    """A slice that produced no memory file, with the reason it produced none.

    The reason is written to the run's report, so it names the failure and
    never quotes the slice itself.
    """

    slice_: funnel.Slice
    reason: str


def load_examples(memory_dir: Path, index_text: str, limit: int = EXAMPLE_COUNT) -> list[str]:
    """The first `limit` project memories the index names, ordered by name.

    Only the named files are opened - the corpus is too large to read whole -
    and any file that will not parse is skipped, since one unreadable memory
    must not abort the stage before its first proposal.
    """
    examples: list[str] = []
    for name in sorted(dedup.parse_index(index_text)):
        try:
            text = (memory_dir / f"{name}.md").read_text(encoding="utf-8")
            metadata = proposal.parse_frontmatter(text).get("metadata")
        except (OSError, proposal.ProposalError):
            continue
        if isinstance(metadata, dict) and metadata.get("type") == proposal.DISTIL_TYPE:
            examples.append(text)
            if len(examples) == limit:
                break
    return examples


def distil(
    slice_: funnel.Slice,
    examples: list[str],
    index_has_names: bool = False,
    judge: Callable[[str, str], str] = funnel.judge,
) -> proposal.Proposal | Discard:
    """Ask the strong tier for a memory file covering `slice_`.

    A missing CLI fails the same way for every remaining slice, so
    FileNotFoundError propagates and aborts the stage; every other model
    failure ends as a discard naming what went wrong.
    """
    prompt = _DISTIL_PROMPT.format(
        discard=DISCARD_PREFIX, examples="\n\n".join(examples), text=slice_.text
    )
    try:
        answer = judge(prompt, "strong").strip()
    except FileNotFoundError:
        raise
    except subprocess.TimeoutExpired:
        return Discard(slice_, "the model timed out before answering")
    except OSError:
        return Discard(slice_, "the model call failed with an operating system error")
    except RuntimeError:
        return Discard(slice_, "the model call exited with an error")

    if not answer:
        return Discard(slice_, "the model returned an empty answer")
    if answer.startswith(DISCARD_PREFIX):
        return Discard(slice_, answer[len(DISCARD_PREFIX) :].strip())

    candidate = proposal.Proposal(
        file_text=answer,
        evidence=proposal.Evidence(
            transcript=slice_.transcript, line_no=slice_.line_no, text=slice_.text
        ),
    )
    try:
        proposal.validate_distil_output(candidate, index_has_names)
    except proposal.ProposalError as error:
        return Discard(slice_, f"the answer is not a usable memory file: {error}")
    return candidate
