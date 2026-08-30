"""Tests for proposal.py: the memory-file proposal record, its kind helpers,
frontmatter parsing, and the model-free generic validate() contract."""

import dataclasses
import re
from pathlib import Path

import proposal
import pytest

_VALID_NAME = "cache-eviction-rule"
_VALID_DESCRIPTION = "Redis evicts idle sessions after ten minutes"
_VALID_APPLY = "Set the session TTL above ten minutes for long imports."

# A file in the exact shape real memory files ship in, carrying the extra
# metadata keys (node_type, originSessionId, modified) validate() must accept.
_REAL_WORLD_FILE = (
    "---\n"
    "name: some-memory-name\n"
    'description: "A one-line recall cue"\n'
    "metadata:\n"
    "  node_type: memory\n"
    "  type: project\n"
    "  originSessionId: 00000000-0000-4000-8000-000000000000\n"
    "  modified: 2026-08-17T21:45:59.066Z\n"
    "---\n"
    "\n"
    "Body prose here.\n"
    "\n"
    "**Why:** the reason this matters.\n"
    "\n"
    "**How to apply:** what a reader should actually do with it.\n"
)

# Values carrying colons. A `key: value` scraper that splits on the first colon
# truncates these; a YAML parser keeps them whole. The timestamp is quoted so it
# stays a string instead of resolving to a datetime, which makes the round-trip
# assertion exact.
_COLON_VALUES_FILE = (
    "---\n"
    "name: colon-carrying-memory\n"
    'description: "Prefer psql over the GUI: it prints the query plan"\n'
    "metadata:\n"
    "  node_type: memory\n"
    "  type: reference\n"
    "  originSessionId: 6a7c6989-198a-46da-b836-50c8d0d4f083\n"
    '  modified: "2026-08-17T21:45:59.066Z"\n'
    "---\n"
    "\n"
    "Body prose here.\n"
)

# Legitimate frontmatter that happens to contain [ and ]: a flow sequence, and a
# bracketed phrase inside a quoted scalar. Both are valid YAML and must be read,
# not mistaken for the unclosed-bracket case below.
_BRACKETS_FILE = (
    "---\n"
    "name: token-rotation-note\n"
    'description: "Prefer the [admin] console for token rotation"\n'
    "tags: [ops, security]\n"
    "metadata:\n"
    "  node_type: memory\n"
    "  type: reference\n"
    "---\n"
    "\n"
    "The console records who rotated what.\n"
    "\n"
    "**How to apply:** Ask the security team before minting a new token.\n"
)

# (label, description, an apply line that restates it, an apply line that does
# not). The description is held FIXED across the two verdicts, so the same cue
# must be rejected against one body and accepted against another. Only reading
# the apply line can produce both answers.
_CUE_CASES = [
    (
        "word for word",
        "Clear the cache before each deploy run",
        "Clear the cache before each deploy run",
        "Check the audit log after each deploy.",
    ),
    (
        "restated plus an extra clause",
        "Rotate the API token quarterly",
        "Rotate the API token quarterly using the admin console.",
        "Page the on-call engineer when the queue backs up.",
    ),
    (
        # Every word the description adds is a stopword. A rule that did not
        # strip stopwords would see a non-subset and let the tautology through.
        "differs from the apply line only by stopwords",
        "Use the cache for the tenant lookup path",
        "Use cache for tenant lookup path",
        "Warm the pool before the first request.",
    ),
    (
        # FOUR content-token occurrences but only THREE unique tokens ("then" is
        # a stopword). If _tokens returned a set, this word-for-word tautology
        # would fall under MIN_CUE_TOKENS and slip through.
        "one content word repeated",
        "Deploy staging then deploy production",
        "Deploy staging then deploy production",
        "Roll back the release when smoke tests fail.",
    ),
    (
        # The restatement only completes on the apply paragraph's second line.
        "restatement wrapped across two lines",
        "Rotate the signing key every quarter",
        "Rotate the signing key\nevery quarter using the admin console.",
        "Check the audit log after each deploy.",
    ),
]

_CUE_CASE_FIELDS = ("label", "description", "restating_apply", "unrelated_apply")

# Apply lines the restating description is derived from at run time, so no
# finite table of description literals can decide these cases.
_DERIVED_CUE_APPLY_LINES = [
    "Restart the ingest worker after every schema migration.",
    "Archive stale branches once the release tag lands.",
    "Raise the timeout when the batch exceeds ten thousand rows.",
    "Pin the browser version in the end to end suite.",
]


def _body(apply_line=_VALID_APPLY):
    text = "Redis drops idle sessions once they pass the TTL.\n\n**Why:** long imports die halfway.\n"
    if apply_line is not None:
        text += f"\n**How to apply:** {apply_line}\n"
    return text


def _memory_file(
    *,
    name=_VALID_NAME,
    description=_VALID_DESCRIPTION,
    memory_type="project",
    include_metadata=True,
    apply_line=_VALID_APPLY,
):
    lines = ["---"]
    if name is not None:
        lines.append(f'name: "{name}"')
    if description is not None:
        lines.append(f'description: "{description}"')
    if include_metadata:
        lines.append("metadata:")
        lines.append("  node_type: memory")
        if memory_type is not None:
            lines.append(f"  type: {memory_type}")
    lines.append("---")
    return "\n".join(lines) + "\n\n" + _body(apply_line)


@pytest.fixture
def evidence(tmp_path):
    transcript = tmp_path / "session.jsonl"
    transcript.write_text('{"type": "assistant"}\n')
    return proposal.Evidence(
        transcript=transcript,
        line_no=7,
        text="we measured the cache hit rate at 91 percent",
    )


def _proposal(evidence, file_text):
    return proposal.Proposal(file_text=file_text, evidence=evidence)


def test_module_constants_have_the_values_the_contract_pins():
    assert proposal.NEW == "new"
    assert proposal.UPDATE_PREFIX == "update "
    assert proposal.EVIDENCE_EXCERPT_CHARS == 600
    assert proposal.MIN_CUE_TOKENS == 4
    assert proposal.REQUIRED_TYPES == frozenset({"user", "feedback", "project", "reference"})
    assert proposal.DISTIL_TYPE == "project"
    assert proposal.STOPWORDS == frozenset(
        """a an and are as at be but by for from has have in into is it its of on
        or that the their then there these this to was were when which while with
        you your not no if""".split()
    )


def test_distil_type_is_one_of_the_required_types():
    assert proposal.DISTIL_TYPE in proposal.REQUIRED_TYPES


def test_proposal_error_is_a_value_error():
    assert issubclass(proposal.ProposalError, ValueError)


def test_evidence_keeps_its_source_location_and_the_full_untruncated_slice_text(tmp_path):
    transcript = tmp_path / "long-session.jsonl"
    transcript.write_text("{}\n")
    long_text = "x" * (proposal.EVIDENCE_EXCERPT_CHARS * 3)

    record = proposal.Evidence(transcript=transcript, line_no=42, text=long_text)

    assert record.transcript == transcript
    assert record.line_no == 42
    assert record.text == long_text


def test_proposal_defaults_to_a_new_kind_with_no_existing_text_and_no_dedup_error(evidence):
    file_text = _memory_file()

    candidate = proposal.Proposal(file_text=file_text, evidence=evidence)

    assert candidate.kind == proposal.NEW
    assert candidate.existing_text is None
    assert candidate.dedup_error is None
    assert candidate.evidence is evidence
    assert candidate.file_text == file_text


def test_proposal_rejects_mutation_after_construction(evidence):
    candidate = _proposal(evidence, _memory_file())

    with pytest.raises(dataclasses.FrozenInstanceError):
        candidate.kind = proposal.update_kind("other-memory")


@pytest.mark.parametrize(
    "name",
    ["cache-eviction-rule", "flush-queue-rule", "signing_key_rotation", "n", "two word memory"],
)
def test_update_kind_and_updated_name_invert_each_other_for_any_name(name):
    kind = proposal.update_kind(name)

    assert kind == proposal.UPDATE_PREFIX + name
    assert proposal.updated_name(kind) == name


@pytest.mark.parametrize(
    "kind",
    ["new", "delete cache-eviction-rule", "updated cache-eviction-rule", "update ", "update    ", ""],
)
def test_updated_name_returns_none_for_a_kind_that_names_no_existing_memory(kind):
    assert proposal.updated_name(kind) is None


def test_parse_frontmatter_returns_only_the_mapping_above_the_closing_marker():
    parsed = proposal.parse_frontmatter(_REAL_WORLD_FILE)

    assert set(parsed) == {"name", "description", "metadata"}
    assert parsed["name"] == "some-memory-name"
    assert parsed["description"] == "A one-line recall cue"
    assert parsed["metadata"]["type"] == "project"
    assert parsed["metadata"]["node_type"] == "memory"


def test_parse_frontmatter_keeps_values_that_contain_colons_whole():
    parsed = proposal.parse_frontmatter(_COLON_VALUES_FILE)

    assert parsed["metadata"]["modified"] == "2026-08-17T21:45:59.066Z"
    assert parsed["metadata"]["originSessionId"] == "6a7c6989-198a-46da-b836-50c8d0d4f083"
    assert parsed["description"] == "Prefer psql over the GUI: it prints the query plan"


def test_parse_frontmatter_reads_frontmatter_that_legitimately_contains_brackets():
    parsed = proposal.parse_frontmatter(_BRACKETS_FILE)

    assert parsed["tags"] == ["ops", "security"]
    assert parsed["description"] == "Prefer the [admin] console for token rotation"
    assert parsed["metadata"]["type"] == "reference"


@pytest.mark.parametrize(
    ("label", "file_text"),
    [
        ("no opening marker", "name: some-memory-name\n---\n\nBody.\n"),
        ("no closing marker", "---\nname: some-memory-name\n\nBody.\n"),
        ("unclosed bracket", "---\nname: [unclosed\n---\n\nBody.\n"),
        ("unterminated quote", '---\nname: "unterminated\n---\n\nBody.\n'),
        ("mapping value inside a plain scalar", "---\nname: one\n  bad: indent\n---\n\nBody.\n"),
        ("bare list", "---\n- one\n- two\n---\n\nBody.\n"),
        ("bare string", "---\njust a string\n---\n\nBody.\n"),
    ],
)
def test_parse_frontmatter_rejects_text_that_is_not_a_yaml_mapping_between_markers(label, file_text):
    with pytest.raises(proposal.ProposalError):
        proposal.parse_frontmatter(file_text)


def test_validate_accepts_a_well_formed_memory_file(evidence):
    assert proposal.validate(_proposal(evidence, _memory_file())) is None


def test_validate_rejects_a_file_whose_frontmatter_does_not_parse(evidence):
    with pytest.raises(proposal.ProposalError):
        proposal.validate(_proposal(evidence, "no frontmatter at all, just prose\n"))


@pytest.mark.parametrize(("label", "name"), [("missing", None), ("empty", "")])
def test_validate_rejects_a_file_without_a_usable_name_and_names_that_field(evidence, label, name):
    candidate = _proposal(evidence, _memory_file(name=name))

    with pytest.raises(proposal.ProposalError) as exc_info:
        proposal.validate(candidate)

    assert "name" in str(exc_info.value)


@pytest.mark.parametrize(("label", "description"), [("missing", None), ("empty", "")])
def test_validate_rejects_a_file_without_a_usable_description_and_names_that_field(
    evidence, label, description
):
    candidate = _proposal(evidence, _memory_file(description=description))

    with pytest.raises(proposal.ProposalError) as exc_info:
        proposal.validate(candidate)

    assert "description" in str(exc_info.value)


@pytest.mark.parametrize(
    ("label", "kwargs"),
    [
        ("no metadata block", {"include_metadata": False}),
        ("metadata without a type key", {"memory_type": None}),
    ],
)
def test_validate_rejects_a_file_without_a_metadata_type_and_names_that_field(evidence, label, kwargs):
    candidate = _proposal(evidence, _memory_file(**kwargs))

    with pytest.raises(proposal.ProposalError) as exc_info:
        proposal.validate(candidate)

    assert "type" in str(exc_info.value)


@pytest.mark.parametrize("memory_type", ["note", "Project", "memory"])
def test_validate_rejects_a_metadata_type_outside_the_required_set(evidence, memory_type):
    candidate = _proposal(evidence, _memory_file(memory_type=memory_type))

    with pytest.raises(proposal.ProposalError) as exc_info:
        proposal.validate(candidate)

    assert "type" in str(exc_info.value)


@pytest.mark.parametrize("memory_type", ["user", "feedback", "project", "reference"])
def test_validate_accepts_every_required_metadata_type(evidence, memory_type):
    assert proposal.validate(_proposal(evidence, _memory_file(memory_type=memory_type))) is None


def test_validate_accepts_the_extra_frontmatter_keys_real_memory_files_carry(evidence):
    assert proposal.validate(_proposal(evidence, _REAL_WORLD_FILE)) is None


def test_validate_accepts_a_file_whose_frontmatter_contains_brackets(evidence):
    assert proposal.validate(_proposal(evidence, _BRACKETS_FILE)) is None


@pytest.mark.parametrize(_CUE_CASE_FIELDS, _CUE_CASES)
def test_validate_rejects_a_description_its_apply_line_restates(
    evidence, label, description, restating_apply, unrelated_apply
):
    candidate = _proposal(
        evidence, _memory_file(description=description, apply_line=restating_apply)
    )

    with pytest.raises(proposal.ProposalError) as exc_info:
        proposal.validate(candidate)

    assert str(exc_info.value) == "description restates **How to apply:**"


@pytest.mark.parametrize(_CUE_CASE_FIELDS, _CUE_CASES)
def test_validate_accepts_the_same_description_when_the_apply_line_does_not_restate_it(
    evidence, label, description, restating_apply, unrelated_apply
):
    candidate = _proposal(
        evidence, _memory_file(description=description, apply_line=unrelated_apply)
    )

    assert proposal.validate(candidate) is None


@pytest.mark.parametrize("apply_line", _DERIVED_CUE_APPLY_LINES)
def test_validate_rejects_a_description_trimmed_out_of_its_own_apply_line(evidence, apply_line):
    # The cue is built here rather than written out: drop the apply line's last
    # word, prepend a stopword. What is left still restates the apply line.
    description = "the " + " ".join(apply_line.rstrip(".").split()[:-1])
    candidate = _proposal(evidence, _memory_file(description=description, apply_line=apply_line))

    with pytest.raises(proposal.ProposalError) as exc_info:
        proposal.validate(candidate)

    assert str(exc_info.value) == "description restates **How to apply:**"


def test_validate_stops_calling_a_cue_a_restatement_once_the_token_floor_is_above_it(
    evidence, monkeypatch
):
    candidate = _proposal(
        evidence,
        _memory_file(
            description="Rotate the API token quarterly",
            apply_line="Rotate the API token quarterly using the admin console.",
        ),
    )
    with pytest.raises(proposal.ProposalError):
        proposal.validate(candidate)

    monkeypatch.setattr(proposal, "MIN_CUE_TOKENS", 99)

    assert proposal.validate(candidate) is None


def test_validate_stops_seeing_a_restatement_when_no_word_counts_as_a_stopword(
    evidence, monkeypatch
):
    # With stopwords stripped this cue's tokens are a subset of the apply line's.
    # With nothing treated as a stopword, the two extra "the"s make it a non-subset.
    candidate = _proposal(
        evidence,
        _memory_file(
            description="Use the cache for the tenant lookup path",
            apply_line="Use cache for tenant lookup path",
        ),
    )
    with pytest.raises(proposal.ProposalError):
        proposal.validate(candidate)

    monkeypatch.setattr(proposal, "STOPWORDS", frozenset())

    assert proposal.validate(candidate) is None


@pytest.mark.parametrize(
    ("label", "description"),
    [("punctuation only", "... !!! ???"), ("all stopwords", "the and of it")],
)
def test_validate_reports_a_contentless_description_as_empty_not_as_a_restatement(
    evidence, label, description
):
    # An empty token list is a subset of every apply line, so a rule that ran the
    # subset test first would hand back the wrong diagnosis here.
    candidate = _proposal(
        evidence,
        _memory_file(description=description, apply_line="Clear the cache before each deploy run"),
    )

    with pytest.raises(proposal.ProposalError) as exc_info:
        proposal.validate(candidate)

    assert str(exc_info.value) == "description has no content words"


def test_validate_accepts_a_cue_shorter_than_the_minimum_token_floor(evidence):
    # "Cache" is trivially a subset of the apply line. MIN_CUE_TOKENS exists so
    # that short, unrelated cues are not read as restatements.
    candidate = _proposal(
        evidence, _memory_file(description="Cache", apply_line="Clear cache after updates")
    )

    assert proposal.validate(candidate) is None


def test_validate_accepts_a_description_that_only_mostly_overlaps_the_apply_line(evidence):
    # Three of the four content tokens appear in the apply line; "quarterly" does not.
    candidate = _proposal(
        evidence,
        _memory_file(
            description="Rotate the signing key quarterly",
            apply_line="Rotate the signing key using the admin console.",
        ),
    )

    assert proposal.validate(candidate) is None


def test_validate_accepts_a_body_with_no_apply_line(evidence):
    candidate = _proposal(evidence, _memory_file(apply_line=None))

    assert "**How to apply:**" not in candidate.file_text
    assert proposal.validate(candidate) is None


def test_validate_accepts_every_memory_file_in_the_calibration_corpus(evidence):
    # The corpus is one project's memory directory, derived rather than written
    # out: this repository is public and carries no personal paths. The encoding
    # replaces BOTH "/" and "." in the project root with "-".
    root = Path.home() / ".claude"
    corpus = root / "projects" / re.sub(r"[/.]", "-", str(root)) / "memory"
    if not corpus.is_dir():
        pytest.skip("calibration corpus directory is not present on this machine")

    # MEMORY.md is the index, not a memory file: it ships no frontmatter at all.
    files = [path for path in sorted(corpus.glob("*.md")) if path.name != "MEMORY.md"]
    assert files, "calibration corpus exists but holds no memory files"

    for path in files:
        try:
            proposal.validate(_proposal(evidence, path.read_text()))
        except proposal.ProposalError as exc_info:
            pytest.fail(f"{path.name} fails validate(): {exc_info}")
