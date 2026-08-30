"""Tests for distil.py: load_examples()'s index-driven anchor reads and
distil()'s strong-tier call that turns one Slice into a Proposal or a Discard."""

import subprocess
from pathlib import Path

import distil
import funnel
import proposal
import pytest

_SENTINEL = "SENTINEL-TRANSCRIPT-SLICE-9f3c1a-do-not-leak"

_DESCRIPTION = (
    "The transcript cache key carries the parser version, so upgrading the parser "
    "drops stale rows instead of serving them."
)

_BODY = (
    "A cache entry written by an older parser stays readable but wrong. Keying the\n"
    "cache on the parser version makes an upgrade discard it.\n"
    "\n"
    "**Why:** a stale row reads as a fresh one, so a fixed parser bug looks like it\n"
    "survived its own fix.\n"
    "\n"
    "**How to apply:** bump the parser version whenever its output shape changes,\n"
    "and keep that version inside the cache key."
)


def _memory_file(name, type_=proposal.DISTIL_TYPE, body=_BODY, description=_DESCRIPTION):
    return (
        "---\n"
        f"name: {name}\n"
        f'description: "{description}"\n'
        "metadata:\n"
        "  node_type: memory\n"
        f"  type: {type_}\n"
        "---\n"
        "\n"
        f"{body}\n"
    )


def _index_text(*names):
    return "\n".join(f"- [{name} note]({name}.md) — hook for {name}" for name in names)


def _slice(text, marker="measured", line_no=1):
    return funnel.Slice(
        text=text, transcript=Path("transcripts/session.jsonl"), line_no=line_no, marker=marker
    )


DURABLE_FILE = _memory_file("parser-cache-key-carries-version")
DURABLE_FILE_WITH_LINK = _memory_file(
    "parser-cache-key-carries-version",
    body=_BODY + "\n\nSee [[parser-version-bump]] for the sibling rule.",
)

_MISSING_DESCRIPTION = "---\nname: missing-description\nmetadata:\n  type: project\n---\n\nbody\n"
_UNKNOWN_TYPE = _memory_file("unknown-type", type_="nonsense")
_REFERENCE_TYPE = _memory_file("reference-type", type_="reference")
_EMPTY_BODY = (
    "---\n"
    "name: empty-body\n"
    f'description: "{_DESCRIPTION}"\n'
    "metadata:\n"
    "  node_type: memory\n"
    "  type: project\n"
    "---\n"
)

# Three responses whose only defect is one a substring scan cannot see: each
# carries a `description:` line, the literal `type: project` and a non-empty
# body, so anything short of the real validators reads them as good files.
_MALFORMED_LINK = _memory_file(
    "malformed-wiki-link",
    body=_BODY + "\n\nSee [[malformed link]] for the sibling rule.",
)
_UNTERMINATED_QUOTE = (
    "---\n"
    "name: unterminated-quote\n"
    'description: "the parser cache key carries the parser version\n'
    "metadata:\n"
    "  node_type: memory\n"
    "  type: project\n"
    "---\n"
    "\n"
    f"{_BODY}\n"
)
_DESCRIPTION_RESTATES_APPLY = _memory_file(
    "description-restates-how-to-apply",
    description=(
        "Bump the parser version whenever its output shape changes, and keep that "
        "version inside the cache key."
    ),
)

_NO_FRONTMATTER = "a plain note that never opens with a frontmatter fence\n"
_INVALID_YAML = '---\ndescription: "unterminated\nmetadata:\n  type: project\n---\n\nbody\n'
_NON_MAPPING = "---\n- alpha\n- bravo\n---\n\nbody\n"
_TOP_LEVEL_TYPE = (
    "---\n"
    "name: top-level-type\n"
    f'description: "{_DESCRIPTION}"\n'
    "type: project\n"
    "---\n"
    "\n"
    "body\n"
)

# Two usable project memories a substring scan for the indented `node_type:` and
# `type:` lines would wrongly skip: one omits the optional `node_type` key, the
# other writes its metadata mapping in flow style.
_NO_NODE_TYPE = (
    "---\n"
    "name: no-node-type\n"
    f'description: "{_DESCRIPTION}"\n'
    "metadata:\n"
    "  type: project\n"
    "---\n"
    "\n"
    f"{_BODY}\n"
)
_FLOW_STYLE_METADATA = (
    "---\n"
    "name: flow-style-metadata\n"
    f'description: "{_DESCRIPTION}"\n'
    "metadata: {type: project, node_type: memory}\n"
    "---\n"
    "\n"
    f"{_BODY}\n"
)

# A second, unrelated durable memory. Nothing about it resembles the parser-cache
# anchor above except that both are valid project memories, so an accept path
# keyed on one remembered name cannot let it through.
_REPLAY_DESCRIPTION = (
    "A queue worker restarted mid-batch replays the whole batch, so every handler "
    "has to survive running twice."
)
_REPLAY_BODY = (
    "The broker redelivers an unacknowledged batch after a worker restart, so a\n"
    "handler that writes twice doubles its rows.\n"
    "\n"
    "**Why:** the redelivery looks like a fresh batch, and nothing upstream\n"
    "remembers the half-finished one.\n"
    "\n"
    "**How to apply:** key each write on the message id and ignore a second\n"
    "arrival carrying an id already written."
)
_SECOND_DURABLE_FILE = _memory_file(
    "queue-handlers-survive-redelivery",
    body=_REPLAY_BODY,
    description=_REPLAY_DESCRIPTION,
)

# A valid project memory whose prose happens to quote the discard token. The
# model's answer is a discard only when a LINE STARTS with it; this file's
# mention sits mid-line, inside a paragraph, and the file must survive.
_DISCARD_TOKEN_IN_BODY = _memory_file(
    "triage-log-keeps-its-rejection-rows",
    description=(
        "The triage log keeps one row per rejected slice, so a run's rejections stay "
        "readable once the run has ended."
    ),
    body=(
        "Every rejected slice leaves a row behind. The triage log writes DISCARD: rows\n"
        "for them, one per line, beside the rows it accepted.\n"
        "\n"
        "**Why:** a rejection nobody recorded reads the same as a slice nobody looked\n"
        "at, and the two want opposite follow-ups.\n"
        "\n"
        "**How to apply:** emit the rejected rows into the same report as the accepted\n"
        "ones, and name the rule that turned each away."
    ),
)

# Two anchors that only real YAML parsing rejects: one whose type merely STARTS
# with the wanted value, one whose type is `reference` while its body quotes a
# fenced block that reads like a project frontmatter.
_PREFIX_TYPE = _memory_file("prefix-type", type_="project-notes")
_QUOTED_PROJECT_TYPE = _memory_file(
    "quoted-project-type",
    type_="reference",
    body=(
        "A memory file names its own kind in the frontmatter:\n"
        "\n"
        "```yaml\n"
        "metadata:\n"
        "  type: project\n"
        "```\n"
        "\n"
        "**Why:** the loader reads that key, not the prose around it."
    ),
)


@pytest.fixture(autouse=True)
def never_reach_the_real_model(monkeypatch):
    """No test in this file may invoke the claude CLI. distil() captures its
    judge as a default argument bound at import time, so the seam that actually
    stops a real call is funnel's subprocess.run, not funnel.judge."""

    def fail_if_called(cmd, **kwargs):
        raise AssertionError("no test may reach the real claude CLI")

    monkeypatch.setattr(funnel.subprocess, "run", fail_if_called)


@pytest.fixture
def memory_dir(tmp_path):
    directory = tmp_path / "memory"
    directory.mkdir()
    return directory


def test_discard_prefix_and_example_count_have_expected_values():
    assert distil.DISCARD_PREFIX == "DISCARD:"
    assert distil.EXAMPLE_COUNT == 4


def test_distil_discards_a_transient_slice_and_emits_a_complete_file_for_a_durable_slice():
    transient = _slice("all 264 tests pass", marker="pass", line_no=12)
    durable = _slice("we measured the parser cache at 4ms per transcript", line_no=41)

    def stub_judge(prompt, tier):
        if transient.text in prompt:
            return f"{distil.DISCARD_PREFIX} verifies a test run that already passed"
        return DURABLE_FILE

    discarded = distil.distil(transient, [], judge=stub_judge)
    kept = distil.distil(durable, [], judge=stub_judge)

    assert isinstance(discarded, distil.Discard)
    assert discarded.slice_ is transient
    assert discarded.reason.strip() == "verifies a test run that already passed"
    assert isinstance(kept, proposal.Proposal)
    assert kept.file_text.strip() == DURABLE_FILE.strip()
    assert kept.kind == proposal.NEW


@pytest.mark.parametrize(
    "response",
    [
        DURABLE_FILE,
        _SECOND_DURABLE_FILE,
        _NO_NODE_TYPE,
        _FLOW_STYLE_METADATA,
        _DISCARD_TOKEN_IN_BODY,
    ],
    ids=[
        "the-parser-cache-anchor",
        "an-unrelated-memory-under-another-name",
        "no-node-type-key",
        "flow-style-metadata-mapping",
        "body-quotes-the-discard-token",
    ],
)
def test_distil_keeps_every_response_the_memory_file_contract_accepts(response):
    """Acceptance is the contract's verdict, not a shape this file happens to
    show twice. These five differ in name, description, body, and how their
    frontmatter is written; the last one's prose quotes the discard token
    mid-line, which is a memory about triage, not a request to discard. Only a
    real pass through both validators keeps all five."""
    slice_ = _slice("we measured the cache at 4ms")

    def stub_judge(prompt, tier):
        return response

    result = distil.distil(slice_, [], judge=stub_judge)

    assert isinstance(result, proposal.Proposal)
    assert result.file_text.strip() == response.strip()
    assert result.kind == proposal.NEW


def test_distil_calls_the_judge_once_with_the_strong_tier_and_a_prompt_carrying_slice_and_examples():
    calls = []
    slice_ = _slice("we measured the parser cache key against the parser version")
    examples = [_memory_file("anchor-one"), _memory_file("anchor-two")]

    def stub_judge(prompt, tier):
        calls.append((prompt, tier))
        return DURABLE_FILE

    distil.distil(slice_, examples, judge=stub_judge)

    assert len(calls) == 1
    prompt, tier = calls[0]
    assert tier == "strong"
    assert slice_.text in prompt
    assert examples[0] in prompt
    assert examples[1] in prompt


def test_distil_tells_the_judge_to_answer_with_a_discard_line_or_a_memory_file():
    """The slice text and the anchors are raw material, not a task: a model
    handed them with no instruction has no reason to emit either legal answer.
    Strike out the slice text and every example, and what remains is the
    prompt's own wording. It has to be spoken instruction - long enough to
    carry the durable-vs-transient rubric and the memory-file contract, asking
    for an answer - and it has to state the discard route by the literal token
    the model is required to emit. A bare `judge(slice_.text, "strong")` leaves
    nothing behind after the strike-out.

    The words are counted DISTINCT, so a keyword repeated into a wall of text
    counts once, and the rubric has to name both sides of the call it asks for:
    a prompt that says only what shape to answer in never says what to answer.
    """
    slice_ = _slice("we measured the parser cache key against the parser version")
    examples = [_memory_file("anchor-one"), _memory_file("anchor-two")]
    # A rubric, a statement of the memory-file contract and the two-way choice
    # cannot be said in fewer distinct words than this.
    min_distinct_instruction_words = 20
    durable_side = ("durable", "lasting", "enduring", "permanent", "reusable")
    transient_side = ("transient", "temporary", "ephemeral", "one-off", "throwaway", "passing")
    prompts = []

    def stub_judge(prompt, tier):
        prompts.append(prompt)
        return DURABLE_FILE

    distil.distil(slice_, examples, judge=stub_judge)

    (prompt,) = prompts
    instruction = prompt.replace(slice_.text, "")
    for example in examples:
        instruction = instruction.replace(example, "")

    assert distil.DISCARD_PREFIX in instruction
    instruction = instruction.lower()
    assert len(set(instruction.split())) >= min_distinct_instruction_words
    assert any(verb in instruction for verb in ("answer", "reply", "respond", "emit", "return"))
    assert any(word in instruction for word in ("reason", "why", "because"))
    assert "memory" in instruction
    assert "file" in instruction
    assert any(word in instruction for word in durable_side)
    assert any(word in instruction for word in transient_side)


def test_distil_evidence_carries_the_transcript_line_no_and_the_untruncated_slice_text():
    long_text = "we measured the cache hit rate at 94 percent on every rerun. " * 40
    slice_ = funnel.Slice(
        text=long_text, transcript=Path("transcripts/other.jsonl"), line_no=137, marker="measured"
    )

    def stub_judge(prompt, tier):
        return DURABLE_FILE

    result = distil.distil(slice_, [], judge=stub_judge)

    assert len(long_text) > 600
    assert result.evidence.text == long_text
    assert result.evidence.transcript == Path("transcripts/other.jsonl")
    assert result.evidence.line_no == 137


@pytest.mark.parametrize(
    ("response", "expected_words"),
    [
        ("", ("empty", "nothing", "blank", "no response")),
        ("   \n", ("empty", "nothing", "blank", "no response")),
        (
            "the model rambled instead of answering",
            ("discard", "memory file", "frontmatter", "neither"),
        ),
        (_MISSING_DESCRIPTION, ("description",)),
        (_UNKNOWN_TYPE, ("type",)),
        (_UNTERMINATED_QUOTE, ("yaml",)),
        (_DESCRIPTION_RESTATES_APPLY, ("restates",)),
    ],
    ids=[
        "empty",
        "whitespace",
        "garbage",
        "no-description",
        "unknown-type",
        "frontmatter-is-not-valid-yaml",
        "description-restates-how-to-apply",
    ],
)
def test_distil_returns_a_discard_naming_the_failure_when_the_response_is_not_a_valid_memory_file(
    response, expected_words
):
    """"Naming the failure" is not "being non-empty". Seven defects can share
    one constant string, and a reason written to disk then tells its reader
    nothing. Each case demands a word the defect itself supplies - the rejected
    field, the broken rule - which a reason can only carry by passing the
    validator's own complaint through."""
    slice_ = _slice("we measured the cache at 4ms")

    def stub_judge(prompt, tier):
        return response

    result = distil.distil(slice_, [], judge=stub_judge)

    assert isinstance(result, distil.Discard)
    assert result.slice_ is slice_
    assert result.reason.strip() != ""
    assert any(word in result.reason.lower() for word in expected_words)


@pytest.mark.parametrize(
    ("response", "expected_word"),
    [(_REFERENCE_TYPE, "type"), (_EMPTY_BODY, "body"), (_MALFORMED_LINK, "link")],
    ids=["type-is-not-project", "no-body-below-frontmatter", "malformed-wiki-link"],
)
def test_distil_returns_a_discard_when_a_valid_memory_file_breaks_this_features_own_rules(
    response, expected_word
):
    slice_ = _slice("we measured the cache at 4ms")

    def stub_judge(prompt, tier):
        return response

    result = distil.distil(slice_, [], judge=stub_judge)

    assert isinstance(result, distil.Discard)
    assert result.reason.strip() != ""
    assert expected_word in result.reason.lower()


def test_distil_discards_a_file_without_a_wiki_link_when_the_index_already_has_names():
    slice_ = _slice("we measured the cache at 4ms")

    def stub_judge(prompt, tier):
        return DURABLE_FILE

    result = distil.distil(slice_, [], index_has_names=True, judge=stub_judge)

    assert isinstance(result, distil.Discard)
    assert result.reason.strip() != ""
    assert "link" in result.reason.lower()


def test_distil_keeps_a_file_carrying_a_wiki_link_when_the_index_already_has_names():
    slice_ = _slice("we measured the cache at 4ms")

    def stub_judge(prompt, tier):
        return DURABLE_FILE_WITH_LINK

    result = distil.distil(slice_, [], index_has_names=True, judge=stub_judge)

    assert isinstance(result, proposal.Proposal)
    assert result.file_text.strip() == DURABLE_FILE_WITH_LINK.strip()


@pytest.mark.parametrize(
    "error",
    [
        RuntimeError("claude cli exploded"),
        subprocess.TimeoutExpired(
            cmd=["claude", "--print", "--model", "sonnet", "prompt"], timeout=120
        ),
        OSError("[Errno 5] Input/output error"),
    ],
    ids=["runtime-error", "timeout", "os-error"],
)
def test_distil_returns_a_discard_instead_of_propagating_a_judge_failure(error):
    slice_ = _slice("we measured the cache at 4ms")

    def stub_judge(prompt, tier):
        raise error

    result = distil.distil(slice_, [], judge=stub_judge)

    assert isinstance(result, distil.Discard)
    assert result.slice_ is slice_
    assert result.reason.strip() != ""


def test_distil_propagates_file_not_found_error_so_a_missing_cli_aborts_the_stage():
    slice_ = _slice("we measured the cache at 4ms")

    def stub_judge(prompt, tier):
        raise FileNotFoundError("[Errno 2] No such file or directory: 'claude'")

    with pytest.raises(FileNotFoundError):
        distil.distil(slice_, [], judge=stub_judge)


def _judge_raising_runtime_error(prompt, tier):
    raise RuntimeError(f"claude cli exploded while handling {_SENTINEL}")


def _judge_raising_timeout(prompt, tier):
    raise subprocess.TimeoutExpired(
        cmd=["claude", "--print", "--model", "sonnet", _SENTINEL], timeout=120
    )


def _judge_raising_os_error(prompt, tier):
    raise OSError(f"[Errno 5] Input/output error on {_SENTINEL}")


def _judge_returning_nothing(prompt, tier):
    return ""


def _judge_returning_garbage(prompt, tier):
    return "the model rambled instead of answering"


def _judge_returning_invalid_file(prompt, tier):
    return _MISSING_DESCRIPTION


def _judge_returning_a_bare_discard(prompt, tier):
    return distil.DISCARD_PREFIX


def _judge_returning_a_bare_discard_then_the_slice(prompt, tier):
    return (
        f"{distil.DISCARD_PREFIX}\n"
        f"For reference, the snippet said: we measured {_SENTINEL} at four milliseconds"
    )


def _judge_returning_a_padded_discard_then_the_slice(prompt, tier):
    """The same answer with whitespace between the token and the newline: the
    line still states no reason, and the snippet still sits underneath it."""
    return (
        f"{distil.DISCARD_PREFIX}  \t \n"
        f"For reference, the snippet said: we measured {_SENTINEL} at four milliseconds"
    )


@pytest.mark.parametrize(
    "stub_judge",
    [
        _judge_raising_runtime_error,
        _judge_raising_timeout,
        _judge_raising_os_error,
        _judge_returning_garbage,
        _judge_returning_invalid_file,
        _judge_returning_a_bare_discard,
        _judge_returning_a_bare_discard_then_the_slice,
        _judge_returning_a_padded_discard_then_the_slice,
    ],
    ids=[
        "runtime-error",
        "timeout",
        "os-error",
        "garbage",
        "invalid-file",
        "bare-discard",
        "bare-discard-then-the-slice",
        "padded-discard-then-the-slice",
    ],
)
def test_no_discard_reason_ever_embeds_the_slice_text(stub_judge):
    slice_ = _slice(f"we measured {_SENTINEL} at four milliseconds")

    result = distil.distil(slice_, [], judge=stub_judge)

    assert isinstance(result, distil.Discard)
    assert _SENTINEL not in result.reason


def test_a_discard_reason_stops_at_the_end_of_the_discard_line():
    """The reason is the rest of the LINE, not the rest of the answer. A model
    that states its verdict and then restates the snippet it turned down writes
    that snippet into a reason that is saved to disk and read later by whoever
    triages the run, which is exactly what the no-slice-text rule forbids."""
    slice_ = _slice(f"we measured {_SENTINEL} at four milliseconds")

    def stub_judge(prompt, tier):
        return (
            f"{distil.DISCARD_PREFIX} verifies a test run that already passed\n"
            f"For reference, the snippet said: we measured {_SENTINEL} at four milliseconds"
        )

    result = distil.distil(slice_, [], judge=stub_judge)

    assert isinstance(result, distil.Discard)
    assert result.reason == "verifies a test run that already passed"
    assert _SENTINEL not in result.reason


# A DISCARD line states no reason whenever nothing but whitespace follows the
# token on it. The answers are built from those two parts - the padding that
# ends the line, and whatever prose the model wrote underneath - so the rule
# covers the shapes this file never wrote down. Three hand-picked literals can
# be memorised; a padding one space wider than the fixtures cannot.
_BLANK_DISCARD_PADDINGS = (
    ("", "nothing-after-the-token"),
    (" ", "one-space-after-the-token"),
    ("\t", "one-tab-after-the-token"),
    ("  \t  ", "mixed-whitespace-after-the-token"),
)
_BLANK_DISCARD_TAILS = (
    ("", "end-of-answer"),
    ("\nwe clocked the reindex at nine hundred milliseconds", "prose-on-the-next-line"),
    (
        "\n\nwe clocked the reindex at nine hundred milliseconds"
        "\nplus a stray remark about zsh completions",
        "prose-further-down",
    ),
)
_BLANK_DISCARD_ANSWERS = [
    pytest.param(f"{distil.DISCARD_PREFIX}{padding}{tail}", id=f"{padding_id}-{tail_id}")
    for padding, padding_id in _BLANK_DISCARD_PADDINGS
    for tail, tail_id in _BLANK_DISCARD_TAILS
]

# Long enough that no reason shares one by accident, short enough that a
# truncated quotation of the model's later prose still trips it.
_SHINGLE_LENGTH = 12


@pytest.mark.parametrize("answer", _BLANK_DISCARD_ANSWERS)
def test_a_discard_whose_line_states_no_reason_still_carries_one_saying_so(answer):
    """Every discard carries a reason: the run's report promises "discards with
    reasons", and an empty string is not one. A model that ends its DISCARD line
    without words states no reason, so the discard says that instead of
    persisting a blank field nobody can act on.

    Whitespace does not make it a different case, and neither does prose
    underneath. The reason is the rest of the DISCARD LINE, so a line holding
    nothing but padding states nothing however much follows below, and reaching
    onto a later line to fill the gap is how the model's own restatement of the
    snippet ends up on disk.

    So the reason these answers produce is pinned to the one the bare token
    produces - identical, whatever the padding, whatever came after. That admits
    no borrowed tail at all, not even a truncated one, which the loop underneath
    then says twice: no run of twelve characters from any later line survives
    into a reason that is written to `discards.json` and read by whoever triages
    the run."""
    slice_ = _slice("we measured the cache at 4ms")

    def stub_judge(prompt, tier):
        return answer

    result = distil.distil(slice_, [], judge=stub_judge)
    bare = distil.distil(slice_, [], judge=_judge_returning_a_bare_discard)

    assert isinstance(result, distil.Discard)
    assert result.slice_ is slice_
    assert result.reason.strip() != ""
    assert any(word in result.reason.lower() for word in ("reason", "explanation", "unexplained"))
    assert result.reason == bare.reason
    for later_line in answer.split("\n")[1:]:
        if not later_line.strip():
            continue
        assert later_line.strip() not in result.reason
        for start in range(len(later_line) - _SHINGLE_LENGTH + 1):
            assert later_line[start : start + _SHINGLE_LENGTH] not in result.reason


def test_a_discard_reason_the_model_states_reaches_the_discard_unchanged():
    """Filling in the blank case must not become overwriting every case. One
    constant reason on every discard reads as an empty one to whoever triages
    the run: the words the model chose are the only thing that says WHY this
    slice was turned down, so they survive verbatim and differ from what a
    reasonless answer leaves behind."""
    slice_ = _slice("we measured the cache at 4ms")
    stated = "the snippet names a build that has already finished"

    def stub_judge_with_a_reason(prompt, tier):
        return f"{distil.DISCARD_PREFIX} {stated}"

    with_reason = distil.distil(slice_, [], judge=stub_judge_with_a_reason)
    without_reason = distil.distil(slice_, [], judge=_judge_returning_a_bare_discard)

    assert isinstance(with_reason, distil.Discard)
    assert isinstance(without_reason, distil.Discard)
    assert with_reason.reason == stated
    assert without_reason.reason.strip() != ""
    assert without_reason.reason != with_reason.reason


def test_discard_reasons_distinguish_the_failure_modes_they_name():
    """A reason is written to disk and read later by whoever triages the run.
    One constant string - "discarded", "no proposal" - satisfies every
    not-empty assertion in this file and tells that reader nothing about which
    of these six ways the slice failed. Two constants, one per code path, tell
    them barely more, so each of the six failures needs its own reason, and the
    timeout has to say it timed out rather than just differ from its
    neighbours."""
    slice_ = _slice("we measured the cache at 4ms")
    failures = {
        "empty-response": _judge_returning_nothing,
        "garbage-response": _judge_returning_garbage,
        "invalid-file": _judge_returning_invalid_file,
        "runtime-error": _judge_raising_runtime_error,
        "timeout": _judge_raising_timeout,
        "os-error": _judge_raising_os_error,
    }

    reasons = {}
    for failure, stub_judge in failures.items():
        result = distil.distil(slice_, [], judge=stub_judge)
        assert isinstance(result, distil.Discard)
        reasons[failure] = result.reason.strip()

    assert len(set(reasons.values())) == len(failures)
    assert any(word in reasons["timeout"].lower() for word in ("timeout", "timed out"))


@pytest.mark.parametrize(
    "index_text",
    ["", "# Memory\n\nprose with no bullet links at all\n"],
    ids=["empty", "no-links"],
)
def test_load_examples_returns_no_anchors_when_the_index_names_nothing(memory_dir, index_text):
    (memory_dir / "alpha.md").write_text(_memory_file("alpha"), encoding="utf-8")

    assert distil.load_examples(memory_dir, index_text) == []


def test_load_examples_keeps_only_project_type_files(memory_dir):
    """`metadata.type` is a parsed key compared whole. The last two files are
    the ones a scan for the literal `type: project` cannot tell apart from a
    project memory: one only starts with that value, the other is a reference
    memory that quotes a project frontmatter inside a fenced block."""
    project_text = _memory_file("alpha")
    (memory_dir / "alpha.md").write_text(project_text, encoding="utf-8")
    (memory_dir / "bravo.md").write_text(_memory_file("bravo", type_="reference"), encoding="utf-8")
    (memory_dir / "charlie.md").write_text(_memory_file("charlie", type_="user"), encoding="utf-8")
    (memory_dir / "prefix-type.md").write_text(_PREFIX_TYPE, encoding="utf-8")
    (memory_dir / "quoted-project-type.md").write_text(_QUOTED_PROJECT_TYPE, encoding="utf-8")

    index_text = _index_text("alpha", "bravo", "charlie", "prefix-type", "quoted-project-type")

    assert distil.load_examples(memory_dir, index_text) == [project_text]


def test_load_examples_keeps_a_project_file_however_its_frontmatter_is_written(memory_dir):
    """`metadata.type` is a YAML key, not a line of text. One live memory file
    in three carries no `node_type`, and nothing forbids a flow-style mapping;
    both are ordinary project memories and both belong in the anchors."""
    (memory_dir / "no-node-type.md").write_text(_NO_NODE_TYPE, encoding="utf-8")
    (memory_dir / "flow-style-metadata.md").write_text(_FLOW_STYLE_METADATA, encoding="utf-8")

    index_text = _index_text("no-node-type", "flow-style-metadata")

    assert distil.load_examples(memory_dir, index_text) == [_FLOW_STYLE_METADATA, _NO_NODE_TYPE]


def test_load_examples_orders_anchors_by_name_and_returns_the_same_list_on_every_call(memory_dir):
    names = ["alpha", "bravo", "charlie", "delta", "echo"]
    texts = {name: _memory_file(name) for name in names}
    for name, text in texts.items():
        (memory_dir / f"{name}.md").write_text(text, encoding="utf-8")

    index_text = _index_text(*reversed(names))
    first = distil.load_examples(memory_dir, index_text)
    second = distil.load_examples(memory_dir, index_text)

    assert first == [texts["alpha"], texts["bravo"], texts["charlie"], texts["delta"]]
    assert second == first


def test_load_examples_returns_no_more_anchors_than_limit(memory_dir):
    names = ["alpha", "bravo", "charlie", "delta", "echo"]
    texts = {name: _memory_file(name) for name in names}
    for name, text in texts.items():
        (memory_dir / f"{name}.md").write_text(text, encoding="utf-8")

    result = distil.load_examples(memory_dir, _index_text(*names), limit=2)

    assert result == [texts["alpha"], texts["bravo"]]


def test_load_examples_reads_no_more_than_twice_the_limit_of_indexed_names(memory_dir, monkeypatch):
    """Reading a bounded number of files is why this stage takes an already-read
    index instead of the directory. A sparse index therefore yields FEWER
    anchors than asked for - the project memory here sits past the read bound,
    so it never becomes an anchor - and the rubric alone carries the prompt. An
    implementation that keeps opening files until it has collected `limit`
    survivors reads the whole index whenever the good files sit late in it."""
    decoys = ["aaa-01", "aaa-02", "aaa-03", "aaa-04", "aaa-05"]
    for name in decoys:
        (memory_dir / f"{name}.md").write_text(
            _memory_file(name, type_="reference"), encoding="utf-8"
        )
    (memory_dir / "zzz-project.md").write_text(_memory_file("zzz-project"), encoding="utf-8")

    read_names = []
    unpatched_read_text = Path.read_text

    def spy_read_text(self, *args, **kwargs):
        read_names.append(self.name)
        return unpatched_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", spy_read_text)

    result = distil.load_examples(memory_dir, _index_text(*decoys, "zzz-project"), limit=1)

    assert result == []
    assert len(read_names) == 2


def test_load_examples_reads_only_the_files_the_index_names(memory_dir, monkeypatch):
    """Filtering the returned list is not the same as never opening the file.
    The PRD forbids this stage from touching every memory file, so the reads
    themselves are watched: an implementation that globs the directory, reads
    all four entries and only then keeps the indexed two is exactly the
    behaviour being ruled out."""
    alpha_text = _memory_file("alpha")
    bravo_text = _memory_file("bravo")
    (memory_dir / "alpha.md").write_text(alpha_text, encoding="utf-8")
    (memory_dir / "bravo.md").write_text(bravo_text, encoding="utf-8")
    (memory_dir / "aaa-decoy.md").write_text(_memory_file("aaa-decoy"), encoding="utf-8")
    (memory_dir / "zzz-decoy.md").mkdir()

    read_names = []
    unpatched_read_text = Path.read_text

    def spy_read_text(self, *args, **kwargs):
        read_names.append(self.name)
        return unpatched_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", spy_read_text)

    result = distil.load_examples(memory_dir, _index_text("alpha", "bravo"))

    assert result == [alpha_text, bravo_text]
    assert "name: aaa-decoy" not in "".join(result)
    assert set(read_names) == {"alpha.md", "bravo.md"}


def test_load_examples_skips_unusable_files_instead_of_raising(memory_dir):
    foxtrot_text = _memory_file("foxtrot")
    golf_text = _memory_file("golf")
    (memory_dir / "alpha.md").mkdir()
    (memory_dir / "bravo.md").write_text(_NO_FRONTMATTER, encoding="utf-8")
    (memory_dir / "charlie.md").write_text(_INVALID_YAML, encoding="utf-8")
    (memory_dir / "delta.md").write_text(_NON_MAPPING, encoding="utf-8")
    (memory_dir / "echo.md").write_text(_TOP_LEVEL_TYPE, encoding="utf-8")
    (memory_dir / "foxtrot.md").write_text(foxtrot_text, encoding="utf-8")
    (memory_dir / "golf.md").write_text(golf_text, encoding="utf-8")

    index_text = _index_text("alpha", "bravo", "charlie", "delta", "echo", "foxtrot", "golf")

    assert distil.load_examples(memory_dir, index_text) == [foxtrot_text, golf_text]
