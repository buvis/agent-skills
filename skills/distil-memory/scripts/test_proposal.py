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

