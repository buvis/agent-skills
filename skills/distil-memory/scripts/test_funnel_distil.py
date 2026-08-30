"""Tests for the distil stage main() drives behind --distil: what it distils,
what it discards, and what it publishes. The corpus fixtures it shares with its
two sibling distil test modules live in funnel_test_helpers."""

import subprocess

import dedup
import distil
import funnel
import proposal
import pytest

from funnel_test_helpers import (
    FakeClaudeCli,
    _INDEX_HEADER,
    _MEMORY_CHEAP_TIER_MAP,
    _MEMORY_REPORT_DIRECTORY,
    _PROPOSAL_ONE,
    _PROPOSAL_TWO,
    _SLICE_ONE,
    _SLICE_THREE,
    _SLICE_TWO,
    _published,
    make_corpus,
)


_DISTIL_LABELS = ["proposals", "discards", "new_vs_update", "skipped_by_limit", "dedup_errors"]


# An indexed memory that is NOT a project memory, named so it sorts ahead of
# every other entry: a stage that anchors on whatever the index names picks it
# up first and hands the distiller imported prose as house style.
_ENTRY_REFERENCE_NOTE = (
    "- [Reference note](aaa-reference-note.md) — the cheap judge tier resolves to the haiku model.\n"
)

_MEMORY_REFERENCE_NOTE = """---
name: aaa-reference-note
description: "An imported reference page about the judge tiers"
metadata:
  node_type: memory
  type: reference
---

Imported reference material about the judge tiers.

**Why:** a page copied in from elsewhere is not this project's own memory.

**How to apply:** read it for background, never as the shape to copy.
"""

_DISCARD_ANSWER = "DISCARD: this only repeats that a suite passed"
_DISCARD_REASON = "this only repeats that a suite passed"

# A second memory file carrying the same frontmatter name as _PROPOSAL_ONE.
_PROPOSAL_SAME_NAME = """---
name: cheap-tier-is-haiku
description: "The strong judge tier resolves to the sonnet model"
metadata:
  node_type: memory
  type: project
---

The strong tier resolves to sonnet, so a strong call never lands on haiku. See [[cheap-tier-map]].

**Why:** a run that names a model directly drifts the day the map changes.

**How to apply:** ask for the strong tier whenever a verdict needs judgement.
"""

# A memory file that is valid apart from a name aimed outside its directory.
_PROPOSAL_HOSTILE_NAME = """---
name: ../Escape Hatch
description: "Every distilled memory file is published inside the run's proposals directory"
metadata:
  node_type: memory
  type: project
---

A run publishes its memory files inside its own proposals directory. See [[report-directory]].

**Why:** a file written anywhere else is invisible to the run that produced it.

**How to apply:** open the run's proposals directory to find what it published.
"""

# A memory file that is valid on its own but links to no other memory. Whether
# that is acceptable is the plane's call, not the file's: over an index that
# names memories to link to it is a discard, over one that names none it is a
# proposal. The same answer is used for both.
_PROPOSAL_WITHOUT_A_LINK = """---
name: strong-tier-is-sonnet
description: "The strong judge tier resolves to the sonnet model"
metadata:
  node_type: memory
  type: project
---

The strong tier resolves to sonnet, so a strong call never lands on haiku.

**Why:** a run that names a model directly drifts the day the tier map changes.

**How to apply:** ask for the strong tier whenever a verdict needs judgement.
"""

# Two answers no validator accepts: one with frontmatter missing the required
# fields, one with no frontmatter at all (so not even a name can be parsed).
_MALFORMED_ANSWER = """---
name: ../../pwned
---

Sure! Here is the memory file you asked for..."""

_UNPARSEABLE_ANSWER = "Sure! Here is the memory file you asked for, without any frontmatter."


def _fail_with_runtime_error(cmd, **kwargs):
    return subprocess.CompletedProcess(
        args=cmd, returncode=1, stdout="", stderr="claude cli exploded"
    )


def test_main_with_distil_and_dry_run_distils_nothing_and_says_so_on_stderr(make_corpus, monkeypatch, capsys):
    """A dry run reaches no model of any tier, so it cannot have distilled
    anything: no proposals directory, and every distil count reads n/a."""
    built = make_corpus()

    def fail_if_called(*args, **kwargs):
        raise AssertionError("a dry run must reach no model of any tier")

    monkeypatch.setattr(funnel.subprocess, "run", fail_if_called)

    exit_code = funnel.main(["--distil", "--dry-run"])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "--distil" in captured.err
    assert "transcripts_read: 1" in captured.out
    assert "slices_kept: 2" in captured.out
    for label in _DISTIL_LABELS:
        assert f"{label}: n/a" in captured.out
    assert list(built.audit_dir.glob("*-proposals")) == []


def test_main_with_distil_publishes_the_proposals_directory_and_reports_integer_counts(
    make_corpus, monkeypatch, capsys
):
    """The wiring pin: a real --distil run (no --dry-run) over a one-slice
    corpus. A main() that parses the flag and ignores it renders every distil
    count as n/a and writes no proposals directory, so both are asserted.

    The two numbers are also asserted against each other, not only against a
    literal each: what the run reports has to be what its own manifests hold, or
    a run that quietly drops a proposal on the way to disk still reports having
    published it."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    fake_cli = FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE})
    monkeypatch.setattr(funnel.subprocess, "run", fake_cli)

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "proposals: 1" in out
    assert "discards: 0" in out
    assert "new_vs_update: 1/0" in out
    assert "skipped_by_limit: 0" in out
    assert "dedup_errors: 0" in out
    for label in _DISTIL_LABELS:
        assert f"{label}: n/a" not in out

    out_dir, records, discards = _published(built.audit_dir)
    assert f"proposals: {len(records)}" in out
    assert f"discards: {len(discards)}" in out
    assert sorted(p.name for p in out_dir.glob("*.md")) == ["cheap-tier-is-haiku.md"]
    assert (out_dir / "cheap-tier-is-haiku.md").read_text() == _PROPOSAL_ONE.strip()
    assert discards == []
    assert [record["name"] for record in records] == ["cheap-tier-is-haiku"]
    assert [record["kind"] for record in records] == ["new"]
    assert records[0]["dedup_error"] is None
    assert records[0]["transcript"] == str(built.transcript)
    assert records[0]["line_no"] == 1
    assert records[0]["evidence_text"] == _SLICE_ONE

    for published_file in out_dir.glob("*.md"):
        proposal.validate(
            proposal.Proposal(
                file_text=published_file.read_text(),
                evidence=proposal.Evidence(transcript=built.transcript, line_no=1, text=_SLICE_ONE),
            )
        )


def test_main_with_distil_publishes_nothing_and_counts_nothing_when_the_triage_call_fails(
    make_corpus, monkeypatch, capsys
):
    """A triage that fell over hands the distil stage no survivors, so the stage
    never ran. `0` is the report's word for "ran and yielded nothing" and n/a is
    its word for "did not run", so five zeroes describe a pass that never
    happened - and a proposals directory holding two empty manifests is that
    same claim written to disk, where the next reader opens it as a finished
    run.

    Refusing to publish is not licence to go quiet: the counts the run did
    reach still print, the triage failure still reaches stderr, and the exit
    code still reports it."""
    built = make_corpus()
    monkeypatch.setattr(funnel.subprocess, "run", _fail_with_runtime_error)

    exit_code = funnel.main(["--distil"])

    assert exit_code != 0
    captured = capsys.readouterr()
    assert "transcripts_read: 1" in captured.out
    assert "slices_kept: 2" in captured.out
    assert "survivors: n/a" in captured.out
    for label in _DISTIL_LABELS:
        assert f"{label}: n/a" in captured.out
        assert f"{label}: 0" not in captured.out
    assert "claude cli exploded" in captured.err
    assert list(built.audit_dir.rglob("*proposals*")) == []


def test_main_with_distil_still_distils_and_publishes_when_the_triage_call_answers(
    make_corpus, monkeypatch, capsys
):
    """The companion to the failed triage: withholding the stage from a run
    that has no survivors must not become withholding it from every run. The
    same two-slice corpus with a triage that answers distils both survivors,
    publishes them, and reports integers rather than n/a."""
    built = make_corpus()
    fake_cli = FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE, _SLICE_TWO: _PROPOSAL_TWO})
    monkeypatch.setattr(funnel.subprocess, "run", fake_cli)

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "survivors: 2" in out
    assert "proposals: 2" in out
    assert "discards: 0" in out
    for label in _DISTIL_LABELS:
        assert f"{label}: n/a" not in out

    _out_dir, records, discards = _published(built.audit_dir)
    assert sorted(record["name"] for record in records) == [
        "cheap-tier-is-haiku",
        "report-under-audit-results",
    ]
    assert discards == []


def test_main_with_distil_reports_zero_rather_than_n_a_when_a_triage_that_answers_keeps_nobody(
    make_corpus, monkeypatch, capsys
):
    """The other half of the same distinction: a triage that answered and kept
    nobody is not a triage that fell over. It ran, the distil stage ran after it
    with nothing to work on, and `0` is the report's word for exactly that - so
    every distil line carries a number and the run publishes the pass it made,
    empty manifests and all.

    Withholding the stage on an empty survivor list instead of on the triage
    error reads this run as one that was never requested: five n/a where the
    counts belong, and nothing on disk for the next reader to open."""
    built = make_corpus()
    fake_cli = FakeClaudeCli({}, transient_texts=(_SLICE_ONE, _SLICE_TWO))
    monkeypatch.setattr(funnel.subprocess, "run", fake_cli)

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "slices_kept: 2" in out
    assert "survivors: 0" in out
    assert "proposals: 0" in out
    assert "discards: 0" in out
    assert "new_vs_update: 0/0" in out
    assert "skipped_by_limit: 0" in out
    assert "dedup_errors: 0" in out
    for label in _DISTIL_LABELS:
        assert f"{label}: n/a" not in out

    out_dir, records, discards = _published(built.audit_dir)
    assert records == []
    assert discards == []
    assert sorted(path.name for path in out_dir.iterdir()) == ["discards.json", "proposals.json"]


def test_main_asks_the_distiller_with_the_discard_convention_and_the_planes_anchors(
    make_corpus, monkeypatch
):
    """The slice alone is not a prompt. Without the discard convention the model
    has no way to turn a transient snippet down, and without anchors it has no
    house style to copy, so both have to reach the strong tier with the text.

    The anchors are the ones the plane offers: capped, and project memories
    only. A stage that anchors on everything the index names grows its prompt
    with the size of the memory plane and quotes imported reference pages back
    at the model as the shape to copy.
    """
    built = make_corpus(slice_texts=(_SLICE_ONE,), extra_memories=8)
    index = built.memory_dir / "MEMORY.md"
    (built.memory_dir / "aaa-reference-note.md").write_text(_MEMORY_REFERENCE_NOTE)
    index.write_text(index.read_text() + _ENTRY_REFERENCE_NOTE)
    index_text = index.read_text()
    anchors = distil.load_examples(built.memory_dir, index_text)
    ignored = [
        text
        for text in (
            (built.memory_dir / f"{name}.md").read_text() for name in sorted(dedup.parse_index(index_text))
        )
        if text not in anchors
    ]
    fake_cli = FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE})
    monkeypatch.setattr(funnel.subprocess, "run", fake_cli)

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    assert len(fake_cli.distil_prompts) == 1
    prompt = fake_cli.distil_prompts[0]
    assert "DISCARD:" in prompt
    assert _SLICE_ONE in prompt

    assert len(anchors) == distil.EXAMPLE_COUNT
    assert _MEMORY_CHEAP_TIER_MAP in anchors
    for anchor in anchors:
        assert anchor in prompt
    assert _MEMORY_REFERENCE_NOTE in ignored, "the fixture must offer a non-project memory to ignore"
    assert len(ignored) > 1, "the fixture must name more memories than the anchor cap allows"
    for text in ignored:
        assert text not in prompt
    assert list(built.audit_dir.glob("distil-memory-*-proposals"))


def test_main_with_distil_reports_the_new_update_split_and_names_the_reason_each_discard_carries(
    make_corpus, monkeypatch, capsys
):
    """Three survivors, three outcomes: one memory the plane does not hold, one
    that restates an existing memory, and one the distiller turns down. The
    split and the discard's reason both have to reach disk."""
    built = make_corpus(slice_texts=(_SLICE_ONE, _SLICE_TWO, _SLICE_THREE))
    fake_cli = FakeClaudeCli(
        {_SLICE_ONE: _PROPOSAL_ONE, _SLICE_TWO: _PROPOSAL_TWO, _SLICE_THREE: _DISCARD_ANSWER},
        classify=lambda prompt: "report-directory" if "report-under-audit-results" in prompt else "new",
    )
    monkeypatch.setattr(funnel.subprocess, "run", fake_cli)

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "proposals: 2" in out
    assert "discards: 1" in out
    assert "new_vs_update: 1/1" in out

    _out_dir, records, discards = _published(built.audit_dir)
    by_name = {record["name"]: record for record in records}
    assert set(by_name) == {"cheap-tier-is-haiku", "report-under-audit-results"}
    assert by_name["cheap-tier-is-haiku"]["kind"] == "new"
    assert by_name["cheap-tier-is-haiku"]["existing_text"] is None
    assert by_name["report-under-audit-results"]["kind"] == "update report-directory"
    assert by_name["report-under-audit-results"]["existing_text"] == _MEMORY_REPORT_DIRECTORY
    assert discards == [
        {"transcript": str(built.transcript), "line_no": 3, "reason": _DISCARD_REASON}
    ]


@pytest.mark.parametrize(
    "answer",
    [_MALFORMED_ANSWER, _UNPARSEABLE_ANSWER],
    ids=["frontmatter_missing_fields", "no_frontmatter_at_all"],
)
def test_main_discards_an_answer_that_is_not_a_usable_memory_file_and_still_reports(
    answer, tmp_path, make_corpus, monkeypatch, capsys
):
    """Nothing the model sends back is published unchecked. An answer that
    breaks the memory-file contract leaves a named discard and no file, and the
    run still ends in a report: an answer nobody can even parse a name out of
    must not take the run down with it."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    monkeypatch.setattr(funnel.subprocess, "run", FakeClaudeCli({_SLICE_ONE: answer}))

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "proposals: 0" in out
    assert "discards: 1" in out
    assert "new_vs_update: 0/0" in out
    assert len(sorted(built.audit_dir.glob("distil-memory-*.md"))) == 1

    out_dir, records, discards = _published(built.audit_dir)
    assert records == []
    assert sorted(path.name for path in out_dir.iterdir()) == ["discards.json", "proposals.json"]
    assert len(discards) == 1
    assert discards[0]["transcript"] == str(built.transcript)
    assert discards[0]["line_no"] == 1
    assert discards[0]["reason"].strip()
    assert list(tmp_path.rglob("*pwned*")) == []


def test_main_discards_an_answer_that_links_to_nothing_when_the_index_names_memories_to_link(
    make_corpus, monkeypatch, capsys
):
    """A memory that joins a populated plane has to link into it, so an answer
    carrying no [[link]] is not a usable memory file there. The rule can only
    fire if the plane's own names reach the validator: a stage that always says
    the index is empty publishes this answer instead."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    monkeypatch.setattr(
        funnel.subprocess, "run", FakeClaudeCli({_SLICE_ONE: _PROPOSAL_WITHOUT_A_LINK})
    )

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "proposals: 0" in out
    assert "discards: 1" in out

    out_dir, records, discards = _published(built.audit_dir)
    assert records == []
    assert list(out_dir.glob("*.md")) == []
    assert len(discards) == 1
    assert discards[0]["line_no"] == 1
    assert "link" in discards[0]["reason"]


def test_main_publishes_an_answer_that_links_to_nothing_when_the_index_names_no_memory(
    make_corpus, monkeypatch, capsys
):
    """The companion: the same answer over a plane whose index names nothing.
    There is no memory to link to, so demanding a link would discard the first
    memory every project ever distils. A stage that always says the index has
    names throws this one away."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    (built.memory_dir / "MEMORY.md").write_text(_INDEX_HEADER)
    monkeypatch.setattr(
        funnel.subprocess, "run", FakeClaudeCli({_SLICE_ONE: _PROPOSAL_WITHOUT_A_LINK})
    )

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "proposals: 1" in out
    assert "discards: 0" in out
    assert "dedup_errors: 0" in out

    out_dir, records, discards = _published(built.audit_dir)
    assert discards == []
    assert [record["name"] for record in records] == ["strong-tier-is-sonnet"]
    assert (out_dir / "strong-tier-is-sonnet.md").read_text() == _PROPOSAL_WITHOUT_A_LINK.strip()


def test_main_publishes_a_proposal_named_for_another_directory_inside_its_own(
    tmp_path, make_corpus, monkeypatch, capsys
):
    """A frontmatter name is model output, so it reaches the filesystem only as
    a sanitised stem. A name carrying `../` must not steer the file out of the
    run's proposals directory, where nothing would ever find it again."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    monkeypatch.setattr(
        funnel.subprocess, "run", FakeClaudeCli({_SLICE_ONE: _PROPOSAL_HOSTILE_NAME})
    )

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    assert "proposals: 1" in capsys.readouterr().out

    out_dir, records, _discards = _published(built.audit_dir)
    assert len(records) == 1
    assert sorted(path.name for path in out_dir.glob("*.md")) == ["escape-hatch.md"]
    assert (out_dir / "escape-hatch.md").read_text() == _PROPOSAL_HOSTILE_NAME.strip()
    strays = [path for path in tmp_path.rglob("*scape*") if path.parent != out_dir]
    assert strays == []


def test_main_publishes_two_proposals_that_share_a_name_as_two_files(
    make_corpus, monkeypatch, capsys
):
    """Two survivors can distil to the same frontmatter name, and each one is a
    separate proposal about a separate slice. Writing both to one path keeps the
    later text only and leaves two records pointing at a file one of them never
    wrote."""
    built = make_corpus()
    monkeypatch.setattr(
        funnel.subprocess,
        "run",
        FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE, _SLICE_TWO: _PROPOSAL_SAME_NAME}),
    )

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    assert "proposals: 2" in capsys.readouterr().out

    out_dir, records, _discards = _published(built.audit_dir)
    assert len(records) == 2
    assert sorted(path.read_text() for path in out_dir.glob("*.md")) == sorted(
        [_PROPOSAL_ONE.strip(), _PROPOSAL_SAME_NAME.strip()]
    )
