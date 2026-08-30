"""Tests for proposal.py: the memory-file proposal record, its kind helpers,
frontmatter parsing, and the model-free generic validate() contract."""

import builtins
import dataclasses
import errno
import json
import os
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
        except proposal.ProposalError as exc:
            pytest.fail(f"{path.name} fails validate(): {exc}")


def _body_with(*links):
    """A memory body carrying exactly `links` and nothing else bracket-shaped."""
    text = "\nThe pool warms on the first request, so the first import is slow.\n"
    if links:
        text += "\nSee " + " and ".join(links) + " for the neighbouring rules.\n"
    text += f"\n**Why:** long imports die halfway.\n\n**How to apply:** {_VALID_APPLY}\n"
    return text


def _distil_file(body, *, memory_type="project"):
    """A whole memory file whose text after the closing marker is exactly `body`."""
    return (
        "---\n"
        f'name: "{_VALID_NAME}"\n'
        f'description: "{_VALID_DESCRIPTION}"\n'
        "metadata:\n"
        "  node_type: memory\n"
        f"  type: {memory_type}\n"
        "---\n" + body
    )


# (label, the malformed link, a fragment of it the rejection must name).
_MALFORMED_LINKS = [
    # No capture under `\[\[([^\]]*)\]\]` yet a later `]]` exists, so a
    # capture check paired with an unclosed-`[[` check lets this one through.
    ("a closing bracket inside the name", "[[bad]target]]", "bad]target"),
    ("never closed at all", "[[un closed", "un closed"),
    ("a space in the name", "[[has space]]", "has space"),
    ("an empty name", "[[]]", "[[]]"),
]


@pytest.mark.parametrize("memory_type", ["feedback", "user", "reference"])
def test_validate_distil_output_rejects_a_memory_type_this_feature_does_not_own(
    evidence, memory_type
):
    # `feedback` belongs to the human-run encode-incident skill; `user` and
    # `reference` belong to nobody here. The link and body rules are satisfied,
    # so only the ownership rule can produce this rejection.
    candidate = _proposal(
        evidence, _distil_file(_body_with("[[cache-eviction-rule]]"), memory_type=memory_type)
    )

    with pytest.raises(proposal.ProposalError) as exc_info:
        proposal.validate_distil_output(candidate, True)

    assert "type" in str(exc_info.value)


def test_validate_distil_output_accepts_the_project_type_this_feature_owns(evidence):
    candidate = _proposal(evidence, _distil_file(_body_with("[[cache-eviction-rule]]")))

    assert proposal.validate_distil_output(candidate, True) is None


@pytest.mark.parametrize(
    ("label", "body"),
    [("nothing after the closing marker", ""), ("whitespace only", "\n   \n\t\n")],
)
def test_validate_distil_output_rejects_a_frontmatter_only_file_with_no_body(
    evidence, label, body
):
    # The index is empty, so the link rule is waived and only the body rule can
    # reject this: a fragment must fail on its own account.
    candidate = _proposal(evidence, _distil_file(body))

    with pytest.raises(proposal.ProposalError):
        proposal.validate_distil_output(candidate, False)


@pytest.mark.parametrize(("label", "link", "fragment"), _MALFORMED_LINKS)
def test_validate_distil_output_rejects_a_malformed_wiki_link_and_names_the_offending_text(
    evidence, label, link, fragment
):
    # Waiving the link requirement leaves the well-formedness rule as the only
    # rule that can fire, so a pass here is a pass on that rule alone.
    candidate = _proposal(evidence, _distil_file(_body_with(link)))

    with pytest.raises(proposal.ProposalError) as exc_info:
        proposal.validate_distil_output(candidate, False)

    assert fragment in str(exc_info.value)


def test_validate_distil_output_rejects_a_malformed_link_standing_beside_a_well_formed_one(
    evidence
):
    # Finding one good link is not enough: EVERY opening delimiter is checked.
    candidate = _proposal(
        evidence, _distil_file(_body_with("[[cache-eviction-rule]]", "[[bad]target]]"))
    )

    with pytest.raises(proposal.ProposalError) as exc_info:
        proposal.validate_distil_output(candidate, True)

    assert "bad]target" in str(exc_info.value)


@pytest.mark.parametrize(
    "link", ["[[cache-eviction-rule]]", "[[signing_key_rotation]]", "[[rule-2]]", "[[n]]"]
)
def test_validate_distil_output_accepts_every_well_formed_link_shape(evidence, link):
    candidate = _proposal(evidence, _distil_file(_body_with(link)))

    assert proposal.validate_distil_output(candidate, True) is None


def test_validate_distil_output_requires_a_link_once_the_index_holds_names(evidence):
    candidate = _proposal(evidence, _distil_file(_body_with()))
    assert "[[" not in candidate.file_text

    with pytest.raises(proposal.ProposalError) as exc_info:
        proposal.validate_distil_output(candidate, True)

    assert "link" in str(exc_info.value)


def test_validate_distil_output_waives_the_link_requirement_for_an_empty_index(evidence):
    # A first memory in a fresh project has no relatives to point at, and
    # demanding one would only produce an invented link.
    candidate = _proposal(evidence, _distil_file(_body_with()))

    assert proposal.validate_distil_output(candidate, False) is None


def test_validate_distil_output_accepts_a_forward_link_no_existing_memory_answers(evidence):
    # rules/memory.md allows a link to a memory nobody has written yet, so
    # resolution is explicitly not a condition of acceptance.
    candidate = _proposal(evidence, _distil_file(_body_with("[[a-memory-nobody-wrote-yet]]")))

    assert proposal.validate_distil_output(candidate, True) is None


# Names the breakers below damage at run time, so no fixed table of malformed
# literals can decide the cases built from them.
_BREAKABLE_NAMES = ["queue-backlog", "signing_key_rotation"]

# (label, a function damaging a well-formed name, whether the closing brackets
# survive).
_LINK_BREAKERS = [
    ("a space injected into the name", lambda name: f"{name[:3]} {name[3:]}", True),
    ("a stray closing bracket inside the name", lambda name: f"{name[:3]}]{name[3:]}", True),
    ("a dot the name shape does not allow", lambda name: f"{name}.", True),
    ("closing brackets that never arrive", lambda name: name, False),
]


@pytest.mark.parametrize("name", _BREAKABLE_NAMES)
@pytest.mark.parametrize(("label", "break_name", "closed"), _LINK_BREAKERS)
def test_validate_distil_output_rejects_a_link_damaged_at_run_time_and_names_the_damage(
    evidence, label, break_name, closed, name
):
    # The index is empty, so the link requirement is waived and only the
    # well-formedness rule can fire.
    damaged = break_name(name)
    link = f"[[{damaged}]]" if closed else f"[[{damaged}"
    candidate = _proposal(evidence, _distil_file(_body_with(link)))

    with pytest.raises(proposal.ProposalError) as exc_info:
        proposal.validate_distil_output(candidate, False)

    assert damaged in str(exc_info.value)


@pytest.mark.parametrize("name", _BREAKABLE_NAMES)
def test_validate_distil_output_accepts_those_same_names_left_undamaged(evidence, name):
    # The mirror of the case above: rejection must follow from the damage, not
    # from the names themselves.
    body = _body_with(f"[[{name}]]", f"[[{name.replace('-', '_')}-2]]")
    candidate = _proposal(evidence, _distil_file(body))

    assert proposal.validate_distil_output(candidate, True) is None


def test_validate_distil_output_takes_the_type_from_metadata_not_from_elsewhere_in_the_file(
    evidence,
):
    # `type: project` appears twice as a decoy - inside the quoted description
    # and again as a body line - while the metadata declares `reference`. Only a
    # parsed frontmatter mapping can see past the decoys to the declared type.
    file_text = (
        "---\n"
        f'name: "{_VALID_NAME}"\n'
        'description: "Rejected even though type: project reads as a decoy here"\n'
        "metadata:\n"
        "  node_type: memory\n"
        "  type: reference\n"
        "---\n"
        "\n"
        "The queue drains before the deploy gate opens.\n"
        "\n"
        "  type: project\n"
        "\n"
        "See [[cache-eviction-rule]] for the neighbouring rule.\n"
        f"\n**How to apply:** {_VALID_APPLY}\n"
    )

    with pytest.raises(proposal.ProposalError) as exc_info:
        proposal.validate_distil_output(_proposal(evidence, file_text), True)

    assert "type" in str(exc_info.value)


def test_validate_distil_output_reads_a_body_that_opens_with_a_horizontal_rule(evidence):
    # Everything after the closing marker is the body, horizontal rule included.
    # A body extractor that counts `---` occurrences instead of finding the
    # closing marker sees only the blank line before the rule and calls this
    # complete file a fragment.
    body = (
        "\n"
        "---\n"
        "\n"
        "The pool warms on the first request, so the first import is slow.\n"
        "\n"
        "See [[cache-eviction-rule]] for the neighbouring rule.\n"
        f"\n**How to apply:** {_VALID_APPLY}\n"
    )
    candidate = _proposal(evidence, _distil_file(body))

    assert proposal.validate_distil_output(candidate, True) is None


@pytest.mark.parametrize(
    ("label", "name", "expected"),
    [
        ("a path-like name", "Projects/Cache Eviction", "projects-cache-eviction"),
        ("trailing punctuation", "Rotate the token!!", "rotate-the-token"),
        ("a run of replaced characters", "cache // eviction", "cache-eviction"),
        ("a run of hyphens already present", "cache---eviction", "cache-eviction"),
        ("underscores and digits, which survive", "Signing_Key_2", "signing_key_2"),
        ("surrounding whitespace", "  spaced out  ", "spaced-out"),
    ],
)
def test_sanitise_name_reduces_a_name_to_a_safe_lowercase_stem(label, name, expected):
    assert proposal.sanitise_name(name) == expected


@pytest.mark.parametrize(
    ("label", "name"),
    [
        ("empty", ""),
        ("whitespace only", "   "),
        ("punctuation only", "!!! ???"),
        ("slashes only", "///"),
        ("hyphens only", "---"),
    ],
)
def test_sanitise_name_rejects_a_name_with_nothing_safe_left(label, name):
    with pytest.raises(proposal.ProposalError):
        proposal.sanitise_name(name)


# Words that survive sanitising untouched apart from case, and the unsafe runs
# spliced between and around them. Names are assembled from the two at run time,
# so no finite table of accepted literals can answer these.
_STEM_WORDS = ["Cache", "Eviction", "Rule2", "Signing_Key"]
_UNSAFE_FILLERS = ["/", " ", "!", ": ", " // ", "---", "%", "..", "  ", " & "]


@pytest.mark.parametrize("filler", _UNSAFE_FILLERS)
def test_sanitise_name_collapses_every_unsafe_run_into_one_hyphen(filler):
    name = filler + filler.join(_STEM_WORDS) + filler

    stem = proposal.sanitise_name(name)

    assert stem == "-".join(word.lower() for word in _STEM_WORDS)
    assert re.fullmatch(r"[a-z0-9_]+(-[a-z0-9_]+)*", stem)
    # A stem is already safe, so sanitising it again must change nothing.
    assert proposal.sanitise_name(stem) == stem


_MARKER = "measured"

# Every marker the window must anchor on. Anchoring is asserted against each of
# them, so a window that looks for one hardcoded word cannot answer these.
_MARKERS = ["measured", "benchmarked", "91 percent"]

# The contract says "an ellipsis" without pinning the glyph, so both spellings
# count wherever a cut end is asserted.
_ELLIPSES = ("...", "…")


def _filler(total):
    """`total` characters of prose with no repeating substring, so "this window
    reached offset N" is a real assertion rather than a filler coincidence."""
    return " ".join(f"w{index:04d}" for index in range(total // 6 + 2))[:total]


def _text_with_marker_at(offset, total, marker=_MARKER):
    base = _filler(total)
    return base[:offset] + marker + base[offset + len(marker) :]


def _without_ellipses(text):
    for mark in _ELLIPSES:
        if text.startswith(mark):
            text = text[len(mark) :]
            break
    for mark in _ELLIPSES:
        if text.endswith(mark):
            text = text[: -len(mark)]
            break
    return text


@pytest.mark.parametrize(
    ("label", "length"),
    [
        ("under the limit", proposal.EVIDENCE_EXCERPT_CHARS - 1),
        ("exactly at the limit", proposal.EVIDENCE_EXCERPT_CHARS),
    ],
)
def test_excerpt_returns_text_within_the_limit_unchanged_and_unmarked(label, length):
    text = _text_with_marker_at(length - len(_MARKER) - 1, length)

    assert proposal.excerpt(text, _MARKER) == text


@pytest.mark.parametrize("marker", _MARKERS)
def test_excerpt_keeps_a_marker_that_sits_past_the_leading_window(marker):
    # Head truncation would cut this marker away entirely: it starts well past
    # EVIDENCE_EXCERPT_CHARS, and the sentence around it is what justifies the slice.
    width = proposal.EVIDENCE_EXCERPT_CHARS
    offset = width * 2 + 300
    text = _text_with_marker_at(offset, width * 5, marker)

    window = proposal.excerpt(text, marker)

    assert marker in window
    assert text[offset - 100 : offset] in window
    assert text[offset + len(marker) : offset + len(marker) + 100] in window
    assert window.startswith(_ELLIPSES)
    assert window.endswith(_ELLIPSES)
    assert _without_ellipses(window) in text


@pytest.mark.parametrize("marker", _MARKERS)
def test_excerpt_gives_a_marker_near_the_start_a_full_width_window_anchored_there(marker):
    width = proposal.EVIDENCE_EXCERPT_CHARS
    text = _text_with_marker_at(10, width * 5, marker)

    window = proposal.excerpt(text, marker)

    assert window.startswith(text[:60])
    assert not window.startswith(_ELLIPSES)
    assert window.endswith(_ELLIPSES)
    # A window merely centred on offset 10 would stop around offset 310. A
    # clamped, full-width one runs to the far end of the budget.
    assert text[width - 60 : width - 10] in window


@pytest.mark.parametrize("marker", _MARKERS)
def test_excerpt_gives_a_marker_near_the_end_a_full_width_window_anchored_there(marker):
    width = proposal.EVIDENCE_EXCERPT_CHARS
    total = width * 5
    text = _text_with_marker_at(total - len(marker) - 5, total, marker)

    window = proposal.excerpt(text, marker)

    assert window.endswith(text[-60:])
    assert not window.endswith(_ELLIPSES)
    assert window.startswith(_ELLIPSES)
    assert text[total - width + 10 : total - width + 60] in window


def test_excerpt_falls_back_to_the_leading_window_when_the_marker_is_absent():
    width = proposal.EVIDENCE_EXCERPT_CHARS
    text = _filler(width * 5)
    assert "reproduced" not in text

    window = proposal.excerpt(text, "reproduced")

    assert window.startswith(text[:60])
    assert not window.startswith(_ELLIPSES)
    assert window.endswith(_ELLIPSES)
    assert text[width - 60 : width - 10] in window


def test_excerpt_sizes_the_window_from_the_caller_supplied_width():
    text = _text_with_marker_at(1500, proposal.EVIDENCE_EXCERPT_CHARS * 5)

    window = proposal.excerpt(text, _MARKER, 80)

    assert _MARKER in window
    assert len(window) < proposal.EVIDENCE_EXCERPT_CHARS
    assert _without_ellipses(window) in text


# A run directory name in the shape the run stamps: UTC, second resolution. The
# parent is deliberately absent so the reservation has to create it.
_RUN_DIR_NAME = "proposals-20260830T120000Z"

# Longer than NAME_MAX (255) on every filesystem this runs on, and made only of
# characters sanitise_name keeps, so the stem survives whole and the failure
# lands where the file is written rather than earlier.
_UNWRITEABLE_NAME = "n" * 300

_PROPOSAL_RECORD_FIELDS = {
    "name",
    "kind",
    "transcript",
    "line_no",
    "evidence_text",
    "existing_text",
    "dedup_error",
    "file",
}


@dataclasses.dataclass(frozen=True)
class _Discard:
    """The smallest stand-in for the Discard record: the three fields
    discards.json is specified to carry. Discard's own module does not exist
    yet, and write_proposals only ever reads these three."""

    transcript: Path
    line_no: int
    reason: str


def _run_dir(tmp_path):
    return tmp_path / "runs" / _RUN_DIR_NAME


def _named(evidence, name, description=_VALID_DESCRIPTION, **kwargs):
    """A proposal whose frontmatter `name` is `name` - the value that becomes
    both the filename stem and the `name` field in proposals.json."""
    return proposal.Proposal(
        file_text=_memory_file(name=name, description=description), evidence=evidence, **kwargs
    )


def _staged_siblings(out_dir):
    """Every `<out_dir>.partial-*` directory the contract stages into. A
    published run leaves none behind, and a failed one leaves none either."""
    if not out_dir.parent.is_dir():
        return []
    return sorted(out_dir.parent.glob(f"{out_dir.name}.partial-*"))


def _read_json(published, filename):
    return json.loads((published / filename).read_text())


def _by_name(records):
    return {record["name"]: record for record in records}


@dataclasses.dataclass(frozen=True)
class _WriteView:
    """One mid-run observation: the path the run is about to write, what the
    final directory holds at that instant, and which staging siblings stand."""

    target: Path
    out_dir_contents: list[str]
    staged: list[str]


def _resolved(path):
    """Symlinks resolved, so a path recorded as `/var/...` and the same
    directory known as `/private/var/...` (macOS tmp_path) compare equal."""
    return Path(os.path.realpath(path))


def _staging_root(target, reservation):
    """The `<out_dir>.partial-*` sibling that `target` sits under, or None when
    the write landed anywhere else."""
    prefix = f"{reservation.name}.partial-"
    for parent in target.parents:
        if parent.parent == reservation.parent and parent.name.startswith(prefix):
            return parent
    return None


def _watch_publication(monkeypatch, out_dir):
    """Mid-run views taken at every write the run makes, through every vector it
    can write through - `Path.write_text`, `Path.open`, the builtin `open`,
    `os.open`, and the `os.replace`/`os.rename` that publishes. Each view keeps
    WHERE the write lands, what `out_dir` holds at that instant, and which
    staging siblings exist.

    This is what a reader watching `out_dir` while the run is in flight would
    see. A run that stages elsewhere and publishes by rename writes only inside
    a live sibling and leaves `out_dir` empty in every view; a run that builds in
    place fills `out_dir` file by file, which is the failure the contract forbids
    and which no after-the-fact inspection can tell apart from a rename."""
    views = []
    real_write_text = Path.write_text
    real_path_open = Path.open
    real_builtin_open = builtins.open
    real_os_open = os.open
    real_replace = os.replace
    real_rename = os.rename

    def record(target):
        contents = sorted(path.name for path in out_dir.iterdir()) if out_dir.is_dir() else []
        views.append(
            _WriteView(
                target=_resolved(target),
                out_dir_contents=contents,
                staged=[path.name for path in _staged_siblings(out_dir)],
            )
        )

    def is_write(mode):
        return any(flag in str(mode) for flag in "wxa+")

    def watched_write_text(self, *args, **kwargs):
        record(self)
        return real_write_text(self, *args, **kwargs)

    def watched_path_open(self, mode="r", *args, **kwargs):
        if is_write(mode):
            record(self)
        return real_path_open(self, mode, *args, **kwargs)

    def watched_builtin_open(file, mode="r", *args, **kwargs):
        if is_write(mode) and isinstance(file, (str, bytes, os.PathLike)):
            record(os.fsdecode(file))
        return real_builtin_open(file, mode, *args, **kwargs)

    def watched_os_open(path, flags, *args, **kwargs):
        if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT):
            record(path)
        return real_os_open(path, flags, *args, **kwargs)

    def watched_replace(src, dst, *args, **kwargs):
        record(dst)
        return real_replace(src, dst, *args, **kwargs)

    def watched_rename(src, dst, *args, **kwargs):
        record(dst)
        return real_rename(src, dst, *args, **kwargs)

    monkeypatch.setattr(Path, "write_text", watched_write_text)
    monkeypatch.setattr(Path, "open", watched_path_open)
    monkeypatch.setattr(builtins, "open", watched_builtin_open)
    monkeypatch.setattr(os, "open", watched_os_open)
    monkeypatch.setattr(os, "replace", watched_replace)
    monkeypatch.setattr(os, "rename", watched_rename)
    return views


def _assert_never_built_in_place(views, out_dir, published=None):
    """Every observed write landed inside a staging sibling while `out_dir` stood
    empty, and - for a run that published - those staged writes are exactly the
    files the reader ends up seeing. Watching timing alone is not enough: a run
    can leave `out_dir` empty at the one instant it writes a decoy file into a
    sibling and put every real file straight into `out_dir`, so the destination
    of each write is checked too."""
    assert views, (
        "no write was observed: the run must write through Path.write_text, "
        "Path.open, the builtin open, or os.open"
    )
    # Every mid-run view of out_dir is empty: the reservation and nothing more.
    assert [view.out_dir_contents for view in views] == [[] for _ in views]
    # ...and a staging sibling was standing at each of them, so the files were
    # really built elsewhere rather than merely cleaned up afterwards.
    assert all(view.staged for view in views)

    reservation = _resolved(out_dir)
    staged_writes = set()
    for view in views:
        # The publishing rename moves the staging directory onto the
        # reservation: the one write whose target IS the final directory.
        if view.target == reservation:
            continue
        assert reservation not in view.target.parents, (
            f"{view.target.name} was written straight into the final directory"
        )
        root = _staging_root(view.target, reservation)
        assert root is not None, f"{view.target} was written outside the run's staging sibling"
        staged_writes.add(view.target.relative_to(root))
    if published is not None:
        # Every published file is one of those staged writes, so the staging
        # directory held the run's real content rather than a decoy beside it.
        assert staged_writes == {Path(entry.name) for entry in published.iterdir()}


def _watch_reservation(monkeypatch, out_dir):
    """Every directory the run creates, paired with whether the reservation on
    `out_dir` was standing at that moment. Proves the reservation was taken
    before staging was attempted, so releasing it later is a real release."""
    attempts = []
    real_mkdir = Path.mkdir

    def watched_mkdir(self, *args, **kwargs):
        attempts.append((Path(self), out_dir.is_dir()))
        return real_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", watched_mkdir)
    return attempts


def test_write_proposals_publishes_a_markdown_file_per_proposal_and_returns_the_directory(
    evidence, monkeypatch, tmp_path
):
    first = _named(evidence, "cache-eviction-rule")
    second = _named(evidence, "Signing Key Rotation")
    out_dir = _run_dir(tmp_path)
    views = _watch_publication(monkeypatch, out_dir)

    published = proposal.write_proposals([first, second], [], out_dir)

    # The directory a reader sees appears in one step, holding everything: no
    # view taken while the run was writing showed a partly filled out_dir, and
    # every file it now holds was written into the staging sibling instead.
    _assert_never_built_in_place(views, out_dir, published)
    assert published == out_dir
    # The whole published surface, so a leftover staging file inside it fails here.
    assert sorted(path.name for path in published.iterdir()) == [
        "cache-eviction-rule.md",
        "discards.json",
        "proposals.json",
        "signing-key-rotation.md",
    ]
    assert (published / "cache-eviction-rule.md").read_text() == first.file_text
    assert (published / "signing-key-rotation.md").read_text() == second.file_text
    assert not _staged_siblings(out_dir)


def test_proposals_json_records_each_proposal_with_its_evidence_and_published_file(
    evidence, tmp_path
):
    candidate = _named(evidence, "cache-eviction-rule", dedup_error="the index would not parse")
    out_dir = _run_dir(tmp_path)

    published = proposal.write_proposals([candidate], [], out_dir)

    records = _read_json(published, "proposals.json")
    assert len(records) == 1
    record = records[0]
    assert set(record) == _PROPOSAL_RECORD_FIELDS
    assert record["name"] == "cache-eviction-rule"
    assert record["kind"] == proposal.NEW
    assert record["transcript"] == str(evidence.transcript)
    assert record["line_no"] == evidence.line_no
    assert record["evidence_text"] == evidence.text
    assert record["existing_text"] is None
    assert record["dedup_error"] == "the index would not parse"
    # `file` names the proposal's file inside the published directory; joining
    # tolerates either a bare filename or an absolute path.
    assert (published / record["file"]).read_text() == candidate.file_text


def test_proposals_json_carries_existing_text_for_an_update_and_null_for_a_new_proposal(
    evidence, tmp_path
):
    # Slice 3 shows both texts side by side, so the current file's text has to
    # survive the round trip; a new proposal has no current text to show.
    existing = _memory_file(
        name="cache-eviction-rule", description="The cue already sitting on disk"
    )
    updated = proposal.Proposal(
        file_text=_memory_file(name="cache-eviction-rule"),
        evidence=evidence,
        kind=proposal.update_kind("cache-eviction-rule"),
        existing_text=existing,
    )
    fresh = _named(evidence, "queue-backlog-rule")
    out_dir = _run_dir(tmp_path)

    published = proposal.write_proposals([updated, fresh], [], out_dir)

    records = _read_json(published, "proposals.json")
    # Records keep the order the proposals came in, so slice 3 can walk them
    # beside the run's own list without re-sorting.
    assert [record["name"] for record in records] == ["cache-eviction-rule", "queue-backlog-rule"]
    for record in records:
        assert set(record) == _PROPOSAL_RECORD_FIELDS
    by_name = _by_name(records)
    assert by_name["cache-eviction-rule"]["kind"] == "update cache-eviction-rule"
    assert by_name["cache-eviction-rule"]["existing_text"] == existing
    assert by_name["queue-backlog-rule"]["kind"] == "new"
    assert by_name["queue-backlog-rule"]["existing_text"] is None


def test_proposals_json_carries_the_full_slice_text_not_the_display_excerpt(evidence, tmp_path):
    # The marker sits past the leading window, so excerpt() returns a cut,
    # ellipsis-marked window. The machine surface must carry neither cut.
    long_text = _text_with_marker_at(
        proposal.EVIDENCE_EXCERPT_CHARS * 2, proposal.EVIDENCE_EXCERPT_CHARS * 5
    )
    candidate = proposal.Proposal(
        file_text=_memory_file(),
        evidence=proposal.Evidence(transcript=evidence.transcript, line_no=3, text=long_text),
    )
    out_dir = _run_dir(tmp_path)

    published = proposal.write_proposals([candidate], [], out_dir)

    record = _read_json(published, "proposals.json")[0]
    assert record["evidence_text"] == long_text
    assert record["evidence_text"] != proposal.excerpt(long_text, _MARKER)
    assert len(record["evidence_text"]) > proposal.EVIDENCE_EXCERPT_CHARS


def test_write_proposals_records_every_discard_with_its_location_and_reason(evidence, tmp_path):
    discards = [
        _Discard(transcript=evidence.transcript, line_no=12, reason="no measured claim"),
        _Discard(transcript=evidence.transcript, line_no=41, reason="already in memory"),
    ]
    out_dir = _run_dir(tmp_path)

    published = proposal.write_proposals(
        [_named(evidence, "cache-eviction-rule")], discards, out_dir
    )

    assert _read_json(published, "discards.json") == [
        {"transcript": str(evidence.transcript), "line_no": 12, "reason": "no measured claim"},
        {"transcript": str(evidence.transcript), "line_no": 41, "reason": "already in memory"},
    ]


@pytest.mark.parametrize(
    ("label", "leftover"),
    [("empty", None), ("holding an earlier run's file", "cache-eviction-rule.md")],
)
def test_write_proposals_refuses_to_publish_over_a_directory_that_already_exists(
    evidence, tmp_path, label, leftover
):
    # The empty case is the one a same-second second run produces, and the one a
    # plain os.replace onto the name would swallow without a word.
    out_dir = _run_dir(tmp_path)
    out_dir.mkdir(parents=True)
    if leftover is not None:
        (out_dir / leftover).write_text("an earlier run wrote this\n")
    before = sorted(path.name for path in out_dir.iterdir())

    with pytest.raises(FileExistsError) as excinfo:
        proposal.write_proposals([_named(evidence, "cache-eviction-rule")], [], out_dir)

    # EEXIST comes from the mkdir syscall itself, so the name was claimed in one
    # atomic step. A hand-raised FileExistsError behind an out_dir.exists() test
    # carries errno None, and leaves the check-then-write race the contract
    # names: two runs in the same UTC second would both pass that test.
    assert excinfo.value.errno == errno.EEXIST
    assert sorted(path.name for path in out_dir.iterdir()) == before
    assert not _staged_siblings(out_dir)


def test_write_proposals_leaves_no_directory_and_no_staged_sibling_when_a_write_fails(
    evidence, monkeypatch, tmp_path
):
    # One proposal writes cleanly and the other cannot: its stem is longer than
    # the filesystem allows, so the run fails with the directory half built.
    # A reader must find no directory at all rather than the surviving half.
    proposals = [_named(evidence, "cache-eviction-rule"), _named(evidence, _UNWRITEABLE_NAME)]
    out_dir = _run_dir(tmp_path)
    views = _watch_publication(monkeypatch, out_dir)

    with pytest.raises(OSError):
        proposal.write_proposals(proposals, [], out_dir)

    # The half that did get written never reached out_dir, so the survivor was
    # never visible to a reader: this is a rollback of a staged run, not a
    # deletion of a directory that was briefly wrong.
    _assert_never_built_in_place(views, out_dir)
    assert not out_dir.exists()
    assert not _staged_siblings(out_dir)


def test_write_proposals_removes_its_reservation_when_the_staging_directory_cannot_be_built(
    evidence, monkeypatch, tmp_path
):
    # A regular file already occupying the staged sibling's exact path makes the
    # staging mkdir fail AFTER the reservation is taken, which is the only way to
    # reach the rmdir of the reservation from outside the module.
    out_dir = _run_dir(tmp_path)
    out_dir.parent.mkdir(parents=True)
    blocker = out_dir.parent / f"{out_dir.name}.partial-{os.getpid()}"
    blocker.write_text("a file, not a staging directory\n")
    attempts = _watch_reservation(monkeypatch, out_dir)

    with pytest.raises(OSError) as excinfo:
        proposal.write_proposals([_named(evidence, "cache-eviction-rule")], [], out_dir)

    # EEXIST: the staging mkdir ran and hit the blocker, rather than a probe
    # deciding to raise on its own.
    assert excinfo.value.errno == errno.EEXIST
    assert [path for path, _held in attempts if path == out_dir], "the run took no reservation"
    staging = [
        (path, held) for path, held in attempts if path.name.startswith(f"{out_dir.name}.partial-")
    ]
    assert staging, "the run never tried to stage"
    # The reservation was standing when staging was attempted, so there really
    # was one to release - and it is gone now.
    assert staging[0][1] is True
    assert not out_dir.exists()


def test_write_proposals_renames_a_stem_an_earlier_proposal_in_the_run_already_took(
    evidence, tmp_path
):
    # Five distinct names, one shared stem: sanitise_name maps all five onto
    # "cache-eviction", so the suffixes have to be generated from the number of
    # collisions seen rather than drawn from a fixed table. ASSUMED SHAPE for
    # "the collision is counted": the contract returns only the published Path,
    # so the count the report states is derived from proposals.json - a record
    # whose file stem is not sanitise_name(name) is one counted collision. Here
    # that count is four, and the last proposal proves a non-colliding stem is
    # not counted.
    colliding_names = [
        "Cache Eviction",
        "cache/eviction",
        "cache!!eviction",
        "CACHE.EVICTION",
        "cache+eviction",
    ]
    assert {proposal.sanitise_name(name) for name in colliding_names} == {"cache-eviction"}
    colliding = [
        _named(evidence, name, description=f"Cue number {position} on the shared stem")
        for position, name in enumerate(colliding_names, start=1)
    ]
    separate = _named(evidence, "queue-backlog-rule")
    out_dir = _run_dir(tmp_path)

    published = proposal.write_proposals([*colliding, separate], [], out_dir)

    assert sorted(path.name for path in published.glob("*.md")) == [
        "cache-eviction-2.md",
        "cache-eviction-3.md",
        "cache-eviction-4.md",
        "cache-eviction-5.md",
        "cache-eviction.md",
        "queue-backlog-rule.md",
    ]
    # Each file holds its own proposal's text, so the suffixes are not merely
    # present but handed out in INPUT order: the descriptions differ, so a run
    # that ordered the collisions any other way lands the wrong text here.
    suffixed = [
        "cache-eviction.md",
        "cache-eviction-2.md",
        "cache-eviction-3.md",
        "cache-eviction-4.md",
        "cache-eviction-5.md",
    ]
    for candidate, filename in zip(colliding, suffixed, strict=True):
        assert (published / filename).read_text() == candidate.file_text
    records = _read_json(published, "proposals.json")
    assert [record["name"] for record in records] == [*colliding_names, "queue-backlog-rule"]
    for record in records:
        assert set(record) == _PROPOSAL_RECORD_FIELDS
    by_name = _by_name(records)
    # Every record points at the file holding its OWN text, not a sibling's:
    # inside a collision group the filenames are interchangeable, the texts are not.
    for candidate, name in zip(colliding, colliding_names, strict=True):
        assert (published / by_name[name]["file"]).read_text() == candidate.file_text
    renamed = [
        record
        for record in records
        if Path(record["file"]).stem != proposal.sanitise_name(record["name"])
    ]
    assert len(renamed) == 4
    assert sorted(Path(record["file"]).name for record in renamed) == [
        "cache-eviction-2.md",
        "cache-eviction-3.md",
        "cache-eviction-4.md",
        "cache-eviction-5.md",
    ]
    assert Path(by_name["queue-backlog-rule"]["file"]).name == "queue-backlog-rule.md"
