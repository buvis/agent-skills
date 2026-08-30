"""The memory-file proposal record and the generic memory-file contract.

`validate()` checks only what every existing memory file already satisfies:
parseable frontmatter, a name, a description, a known `metadata.type`, and a
recall cue that does not merely restate the body's `**How to apply:**` line.

`validate_distil_output()` adds the rules this feature owns on top of that.
"""

import json
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import yaml

NEW = "new"
UPDATE_PREFIX = "update "
EVIDENCE_EXCERPT_CHARS = 600
MIN_CUE_TOKENS = 4
REQUIRED_TYPES = frozenset({"user", "feedback", "project", "reference"})
DISTIL_TYPE = "project"

STOPWORDS = frozenset(
    """a an and are as at be but by for from has have in into is it its of on
    or that the their then there these this to was were when which while with
    you your not no if""".split()
)

APPLY_MARKER = "**How to apply:**"


class ProposalError(ValueError):
    """A proposal that must not reach the queue. The message names the field
    or rule that rejected it."""


@dataclass(frozen=True)
class Evidence:
    transcript: Path
    line_no: int
    text: str


@dataclass(frozen=True)
class Proposal:
    file_text: str
    evidence: Evidence
    kind: str = NEW
    existing_text: str | None = None
    dedup_error: str | None = None


def update_kind(name: str) -> str:
    """The kind string for an update proposal."""
    return f"{UPDATE_PREFIX}{name}"


def updated_name(kind: str) -> str | None:
    """The existing memory name inside an "update <name>" kind, else None."""
    if not kind.startswith(UPDATE_PREFIX):
        return None
    name = kind[len(UPDATE_PREFIX) :]
    return name if name.strip() else None


def parse_frontmatter(file_text: str) -> dict:
    """The YAML frontmatter of a memory file as a dict."""
    if not file_text.startswith("---"):
        raise ProposalError("file does not open with a --- frontmatter marker")
    match = re.match(r"^---\n(.*?)\n---", file_text, re.DOTALL)
    if not match:
        raise ProposalError("frontmatter has no closing --- marker")
    try:
        parsed = yaml.safe_load(match.group(1))
    except yaml.YAMLError as exc:
        raise ProposalError(f"frontmatter is not valid YAML: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ProposalError("frontmatter is not a YAML mapping")
    return parsed


def _tokens(text: str) -> list[str]:
    """Content words of `text`, in order, duplicates kept."""
    cleaned = re.sub(r"[^a-z0-9 ]", " ", text.lower())
    return [word for word in cleaned.split() if word not in STOPWORDS]


def _apply_paragraph(file_text: str) -> str | None:
    """The `**How to apply:**` paragraph, whitespace-collapsed, else None."""
    _, marker, rest = file_text.partition(APPLY_MARKER)
    if not marker:
        return None
    paragraph = re.split(r"\n[ \t]*\n", rest, maxsplit=1)[0]
    return " ".join(paragraph.split())


def validate(proposal: Proposal) -> None:
    """Raise ProposalError when `proposal` breaks the memory-file contract."""
    frontmatter = parse_frontmatter(proposal.file_text)

    name = frontmatter.get("name")
    if not isinstance(name, str) or not name:
        raise ProposalError("name is missing or empty")

    description = frontmatter.get("description")
    if not isinstance(description, str) or not description:
        raise ProposalError("description is missing or empty")

    metadata = frontmatter.get("metadata")
    memory_type = metadata.get("type") if isinstance(metadata, dict) else None
    if memory_type not in REQUIRED_TYPES:
        raise ProposalError(f"metadata.type must be one of {sorted(REQUIRED_TYPES)}")

    cue = _tokens(description)
    if not cue:
        raise ProposalError("description has no content words")

    apply_paragraph = _apply_paragraph(proposal.file_text)
    if apply_paragraph is None:
        return
    if len(cue) >= MIN_CUE_TOKENS and set(cue) <= set(_tokens(apply_paragraph)):
        raise ProposalError(f"description restates {APPLY_MARKER}")


_LINK_NAME = re.compile(r"[\w-]+")


def _has_well_formed_link(body: str) -> bool:
    """True when `body` carries a [[link]]. Raise on any malformed one."""
    found = False
    for opener in re.finditer(r"\[\[", body):
        rest = body[opener.end() :].split("\n", 1)[0]
        name, closer, _ = rest.partition("]]")
        if not closer or not _LINK_NAME.fullmatch(name):
            raise ProposalError(f"malformed wiki link: [[{name}]]")
        found = True
    return found


def validate_distil_output(proposal: Proposal, index_has_names: bool) -> None:
    """Raise ProposalError when `proposal` breaks this feature's own rules.

    The name is checked for a safe filename stem here, where a refusal is
    still an ordinary reasoned discard. Left to the publisher it would abort
    a run that had already produced usable proposals.
    """
    validate(proposal)

    frontmatter = parse_frontmatter(proposal.file_text)
    sanitise_name(frontmatter["name"])

    memory_type = frontmatter["metadata"]["type"]
    if memory_type != DISTIL_TYPE:
        raise ProposalError(f"metadata.type must be {DISTIL_TYPE}")

    body = re.split(r"\n---\n?", proposal.file_text, maxsplit=1)[1]
    if not body.strip():
        raise ProposalError("file has no body below the frontmatter")

    if not _has_well_formed_link(body) and index_has_names:
        raise ProposalError("body links to no other memory")


def sanitise_name(name: str) -> str:
    """`name` reduced to a safe lowercase filename stem."""
    stem = re.sub(r"[^a-z0-9_]+", "-", name.lower()).strip("-")
    if not stem:
        raise ProposalError(f"name leaves nothing safe to use: {name!r}")
    return stem


def excerpt(text: str, marker: str, max_chars: int = EVIDENCE_EXCERPT_CHARS) -> str:
    """A `max_chars`-character window of `text` around `marker`, each cut end
    marked with an ellipsis. The leading window when `marker` is absent."""
    if len(text) <= max_chars:
        return text
    found = text.find(marker)
    start = 0 if found < 0 else found + len(marker) // 2 - max_chars // 2
    start = max(0, min(start, len(text) - max_chars))
    window = text[start : start + max_chars]
    return ("..." if start else "") + window + ("..." if start + max_chars < len(text) else "")


def _write_proposal_files(proposals: list[Proposal], staging: Path) -> list[dict]:
    """Write one markdown file per proposal into `staging` and return the
    records naming them, in the order the proposals arrived.

    A stem an earlier proposal in the run already took is handed a `-2`, `-3`
    suffix, so two proposals sharing a name never land on one file.
    """
    records = []
    taken: set[str] = set()
    for candidate in proposals:
        name = parse_frontmatter(candidate.file_text)["name"]
        stem = sanitise_name(name)
        unique = stem
        collisions = 1
        while unique in taken:
            collisions += 1
            unique = f"{stem}-{collisions}"
        taken.add(unique)
        filename = f"{unique}.md"
        (staging / filename).write_text(candidate.file_text)
        records.append(
            {
                "name": name,
                "kind": candidate.kind,
                "transcript": str(candidate.evidence.transcript),
                "line_no": candidate.evidence.line_no,
                "evidence_text": candidate.evidence.text,
                "existing_text": candidate.existing_text,
                "dedup_error": candidate.dedup_error,
                "file": filename,
            }
        )
    return records


class PublishedDiscard(Protocol):
    """The three fields `write_proposals` reads off every discard it writes.

    Structural, so a caller satisfies it by carrying the fields and nothing
    here has to import the caller that builds them.
    """

    transcript: Path
    line_no: int
    reason: str


def write_proposals(
    proposals: list[Proposal], discards: list[PublishedDiscard], out_dir: Path
) -> Path:
    """Publish `proposals` and `discards` as `out_dir`, and return it.

    `out_dir` is reserved with an exclusive mkdir, so a second run landing on
    the same name fails with EEXIST rather than overwriting it. The run's files
    are built in an `<out_dir>.partial-<pid>` sibling and moved onto the
    reservation by a single `os.replace`, so a reader never sees a half-filled
    directory. Any failure rolls the whole run back: no sibling, no directory.
    """
    out_dir.mkdir(parents=True)
    staging = out_dir.parent / f"{out_dir.name}.partial-{os.getpid()}"
    try:
        staging.mkdir()
    except OSError:
        out_dir.rmdir()
        raise

    try:
        records = _write_proposal_files(proposals, staging)
        (staging / "proposals.json").write_text(json.dumps(records, indent=2))
        (staging / "discards.json").write_text(
            json.dumps(
                [
                    {
                        "transcript": str(discard.transcript),
                        "line_no": discard.line_no,
                        "reason": discard.reason,
                    }
                    for discard in discards
                ],
                indent=2,
            )
        )
        os.replace(staging, out_dir)
    except Exception:
        shutil.rmtree(staging)
        out_dir.rmdir()
        raise

    return out_dir
