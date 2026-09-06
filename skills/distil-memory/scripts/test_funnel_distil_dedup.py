"""Tests for the typing the distil stage gives each proposal: every candidate
is measured against the memory plane beside its own transcript."""

import subprocess

import dedup
import distil
import funnel
import proposal
import pytest

from funnel_test_helpers import (
    FakeClaudeCli,
    _ENTRY_CHEAP_TIER_MAP,
    _INDEX_HEADER,
    _MEMORY_CHEAP_TIER_MAP,
    _MEMORY_REPORT_DIRECTORY,
    _PROPOSAL_ONE,
    _PROPOSAL_TWO,
    _SLICE_ONE,
    _SLICE_THREE,
    _SLICE_TWO,
    _forbid_full_read,
    _published,
    _record_read_text,
    _refuse_to_distil,
    make_corpus,
    make_two_project_corpus,
)


def _fail_with_runtime_error(cmd, **kwargs):
    return subprocess.CompletedProcess(args=cmd, returncode=1, stdout="", stderr="claude cli exploded")


def _fail_with_missing_binary(cmd, **kwargs):
    raise FileNotFoundError("[Errno 2] No such file or directory: 'claude'")


def _fail_with_timeout(cmd, **kwargs):
    raise subprocess.TimeoutExpired(cmd=cmd, timeout=120)


def test_no_dedup_error_ever_embeds_the_typing_prompt(make_corpus, monkeypatch, capsys):
    """A `TimeoutExpired` from the typing call carries the whole argv it ran,
    which can hold a long prompt built from the proposal's own text and the
    shortlisted memory it was read against. The fixed timeout message must
    never leak either into the published record. The `RuntimeError` branch is
    a known boundary this test leaves unexamined: it interpolates `claude`'s
    stderr, which this test does not probe."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    fake_cli = FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE}, classify=lambda prompt: _fail_with_timeout)
    monkeypatch.setattr(funnel.subprocess, "run", fake_cli)

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    assert "dedup_errors: 1" in capsys.readouterr().out

    _out_dir, records, _discards = _published(built.audit_dir)
    dedup_error = records[0]["dedup_error"]
    assert dedup_error == "the typing call timed out after 120s"
    assert _PROPOSAL_ONE not in dedup_error
    assert _MEMORY_CHEAP_TIER_MAP not in dedup_error


def test_main_keeps_the_proposal_as_new_with_a_dedup_error_when_the_index_cannot_be_read(
    make_corpus, monkeypatch, capsys
):
    """Failure path one: the index is present but unreadable. The proposal
    survives, types as new without a model call, and says what failed."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    index = built.memory_dir / "MEMORY.md"
    index.unlink()
    index.mkdir()
    fake_cli = FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE})
    monkeypatch.setattr(funnel.subprocess, "run", fake_cli)

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    assert "dedup_errors: 1" in capsys.readouterr().out
    assert fake_cli.classified == []

    _out_dir, records, _discards = _published(built.audit_dir)
    assert [record["kind"] for record in records] == ["new"]
    assert isinstance(records[0]["dedup_error"], str)
    assert records[0]["dedup_error"].strip()


def test_main_keeps_the_proposal_as_new_with_a_dedup_error_naming_a_candidate_it_could_not_read(
    make_corpus, monkeypatch, capsys
):
    """Failure path two: the shortlisted memory exists but will not open. The
    proposal is kept and the error names the memory that stayed unread."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    candidate = built.memory_dir / "cheap-tier-map.md"
    candidate.unlink()
    candidate.mkdir()
    fake_cli = FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE})
    monkeypatch.setattr(funnel.subprocess, "run", fake_cli)

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    assert "dedup_errors: 1" in capsys.readouterr().out

    _out_dir, records, _discards = _published(built.audit_dir)
    assert [record["kind"] for record in records] == ["new"]
    assert "cheap-tier-map" in records[0]["dedup_error"]


def test_main_keeps_the_proposal_as_new_with_a_dedup_error_when_the_dedup_judge_fails(
    make_corpus, monkeypatch, capsys
):
    """Failure path three: the typing call itself errors. The distilled memory
    is not thrown away because the model that would have typed it fell over."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    fake_cli = FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE}, classify=lambda prompt: _fail_with_runtime_error)
    monkeypatch.setattr(funnel.subprocess, "run", fake_cli)

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    assert "dedup_errors: 1" in capsys.readouterr().out
    assert len(fake_cli.classified) == 1

    _out_dir, records, _discards = _published(built.audit_dir)
    assert [record["name"] for record in records] == ["cheap-tier-is-haiku"]
    assert [record["kind"] for record in records] == ["new"]
    assert isinstance(records[0]["dedup_error"], str)
    assert records[0]["dedup_error"].strip()


def test_main_sets_the_dedup_error_on_every_proposal_from_a_directory_whose_index_cannot_be_read(
    make_corpus, monkeypatch, capsys
):
    """The index is read once for the directory, before any proposal exists, so
    the failure has to be held and handed to every proposal that follows - not
    only the one being built when it happened."""
    built = make_corpus()
    index = built.memory_dir / "MEMORY.md"
    index.unlink()
    index.mkdir()
    monkeypatch.setattr(
        funnel.subprocess, "run", FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE, _SLICE_TWO: _PROPOSAL_TWO})
    )

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    assert "dedup_errors: 2" in capsys.readouterr().out

    _out_dir, records, _discards = _published(built.audit_dir)
    assert len(records) == 2
    assert [record["kind"] for record in records] == ["new", "new"]
    errors = [record["dedup_error"] for record in records]
    assert all(isinstance(error, str) and error.strip() for error in errors)
    assert errors[0] == errors[1]


def test_main_ends_the_distil_stage_without_a_dedup_error_when_the_cli_is_missing_during_dedup(
    make_corpus, monkeypatch, capsys
):
    """A missing binary fails identically for every remaining call, so the
    stage stops rather than burning the cap. It is an abort, not a dedup
    failure: nothing is annotated, and what was already produced still ships.
    Only that - the proposal whose typing call hit the missing binary was never
    typed, so shipping it as `new` would report a verdict nobody reached."""
    built = make_corpus(slice_texts=(_SLICE_ONE, _SLICE_TWO, _SLICE_THREE))
    fake_cli = FakeClaudeCli(
        {_SLICE_ONE: _PROPOSAL_ONE, _SLICE_TWO: _PROPOSAL_TWO, _SLICE_THREE: _refuse_to_distil},
        classify=lambda prompt: _fail_with_missing_binary if "report-under-audit-results" in prompt else "new",
    )
    monkeypatch.setattr(funnel.subprocess, "run", fake_cli)

    exit_code = funnel.main(["--distil"])

    assert exit_code != 0
    assert fake_cli.distilled == [_SLICE_ONE, _SLICE_TWO]
    assert "dedup_errors: 0" in capsys.readouterr().out

    out_dir, records, _discards = _published(built.audit_dir)
    assert (out_dir / "cheap-tier-is-haiku.md").read_text() == _PROPOSAL_ONE.strip()
    assert [record["name"] for record in records] == ["cheap-tier-is-haiku"]
    assert sorted(path.name for path in out_dir.glob("*.md")) == ["cheap-tier-is-haiku.md"]
    assert all(record["dedup_error"] is None for record in records)


def test_main_ends_the_distil_stage_at_once_when_the_cli_is_missing_during_distillation(
    make_corpus, monkeypatch, capsys
):
    """The same abort at the earlier of the two strong calls. A missing binary
    fails identically for every remaining survivor, so the first distil call
    that hits it ends the stage. Recording it as a discard instead would burn
    the whole cap and fill the run's manifest with one junk discard per
    survivor, each naming a failure the model never saw."""
    built = make_corpus()
    fake_cli = FakeClaudeCli({_SLICE_ONE: _fail_with_missing_binary, _SLICE_TWO: _refuse_to_distil})
    monkeypatch.setattr(funnel.subprocess, "run", fake_cli)

    exit_code = funnel.main(["--distil"])

    assert exit_code != 0
    assert fake_cli.distilled == [_SLICE_ONE]
    out = capsys.readouterr().out
    assert "survivors: 2" in out
    assert "proposals: 0" in out
    assert "discards: 0" in out

    out_dir, records, discards = _published(built.audit_dir)
    assert discards == []
    assert records == []
    assert list(out_dir.glob("*.md")) == []


def test_main_types_a_proposal_as_new_when_the_typing_answer_names_no_shortlisted_memory(
    make_corpus, monkeypatch, capsys
):
    """The typing verdict is a choice from the shortlist, not prose to copy into
    the kind. An answer naming no memory the plane holds means there is nothing
    to update, so the proposal ships as new instead of as an update to a
    sentence nobody can resolve to a file."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    fake_cli = FakeClaudeCli(
        {_SLICE_ONE: _PROPOSAL_ONE}, classify=lambda prompt: "I think this one is brand new."
    )
    monkeypatch.setattr(funnel.subprocess, "run", fake_cli)

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "proposals: 1" in out
    assert "new_vs_update: 1/0" in out
    assert "dedup_errors: 0" in out
    assert len(fake_cli.classified) == 1

    _out_dir, records, _discards = _published(built.audit_dir)
    assert [record["kind"] for record in records] == ["new"]
    assert records[0]["existing_text"] is None
    assert records[0]["dedup_error"] is None


def test_main_reads_no_more_memories_than_the_anchor_cap_and_the_shortlist_allow(
    make_corpus, monkeypatch, capsys
):
    """The anchor cap and the shortlist together are what bound the cost of a
    run. With an index naming ten memories, the WHOLE run over one survivor -
    anchors and candidates alike - opens at most the anchor cap plus the
    shortlist limit, so the price does not grow with the size of the plane."""
    built = make_corpus(slice_texts=(_SLICE_ONE,), extra_memories=8)
    reads = _record_read_text(monkeypatch)
    fake_cli = FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE})
    monkeypatch.setattr(funnel.subprocess, "run", fake_cli)

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    assert "proposals: 1" in capsys.readouterr().out
    assert fake_cli.distilled == [_SLICE_ONE], "the survivor was never distilled"

    memory_reads = [
        path for path in reads if path.parent == built.memory_dir and path.name != "MEMORY.md"
    ]
    assert len(memory_reads) <= dedup.SHORTLIST_LIMIT + distil.EXAMPLE_COUNT


def test_main_types_a_proposal_without_ever_reading_a_memory_the_index_does_not_name(
    make_corpus, monkeypatch, capsys
):
    """The no-full-read pin over the whole pipeline. The memory plane holds an
    unindexed decoy that explodes when opened, and listing the directory is
    refused outright, so any step that walks the plane instead of following the
    index fails here - anchors, shortlist, candidates and typing alike."""
    built = make_corpus(slice_texts=(_SLICE_ONE,))
    expected_existing = (built.memory_dir / "cheap-tier-map.md").read_text()
    _forbid_full_read(monkeypatch, built.memory_dir, built.decoy)
    monkeypatch.setattr(
        funnel.subprocess,
        "run",
        FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE}, classify=lambda prompt: "cheap-tier-map"),
    )

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    assert "proposals: 1" in capsys.readouterr().out

    _out_dir, records, _discards = _published(built.audit_dir)
    assert [record["kind"] for record in records] == ["update cheap-tier-map"]
    assert records[0]["existing_text"] == expected_existing
    assert records[0]["dedup_error"] is None


def test_main_reads_a_memory_directorys_index_once_however_many_survivors_it_holds(
    make_corpus, monkeypatch
):
    """The index, the anchors and the has-names flag are cached per memory
    directory. Re-reading MEMORY.md per survivor costs a file read for every
    slice and lets two survivors of one directory disagree about its index."""
    built = make_corpus()
    reads = _record_read_text(monkeypatch)
    monkeypatch.setattr(
        funnel.subprocess, "run", FakeClaudeCli({_SLICE_ONE: _PROPOSAL_ONE, _SLICE_TWO: _PROPOSAL_TWO})
    )

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    assert reads.count(built.memory_dir / "MEMORY.md") == 1


def test_main_types_each_projects_proposal_against_that_projects_own_memory_plane(
    make_two_project_corpus, monkeypatch, capsys
):
    """A run spanning two projects meets two memory planes, and the plane a
    proposal is typed against is the one beside its own transcript. A stage that
    settles on one directory for the whole run types the second project's
    proposal against the first project's memories: it would find nothing to
    update there, and would never open the second project's index at all."""
    built = make_two_project_corpus()
    reads = _record_read_text(monkeypatch)
    fake_cli = FakeClaudeCli(
        {_SLICE_ONE: _PROPOSAL_ONE, _SLICE_TWO: _PROPOSAL_TWO},
        classify=lambda prompt: (
            "report-directory" if "report-under-audit-results" in prompt else "cheap-tier-map"
        ),
    )
    monkeypatch.setattr(funnel.subprocess, "run", fake_cli)

    exit_code = funnel.main(["--distil"])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "transcripts_read: 2" in out
    assert "proposals: 2" in out
    assert "new_vs_update: 0/2" in out
    assert "dedup_errors: 0" in out

    _out_dir, records, discards = _published(built.audit_dir)
    assert discards == []
    by_name = {record["name"]: record for record in records}
    assert by_name["cheap-tier-is-haiku"]["kind"] == "update cheap-tier-map"
    assert by_name["cheap-tier-is-haiku"]["existing_text"] == _MEMORY_CHEAP_TIER_MAP
    assert by_name["report-under-audit-results"]["kind"] == "update report-directory"
    assert by_name["report-under-audit-results"]["existing_text"] == _MEMORY_REPORT_DIRECTORY
    assert reads.count(built.one.memory_dir / "MEMORY.md") == 1
    assert reads.count(built.two.memory_dir / "MEMORY.md") == 1


class _DedupClassifyRaises:
    """A `dedup`-shaped stub that shortlists and reads the one memory
    `_typing_candidate` always writes to disk, with no read failures, so
    `_type_proposal` reaches its typing call - and whose `classify` then
    always raises `exc`. `_type_proposal` can be exercised directly this way,
    without ever reaching the real `dedup.classify` or a `claude` CLI call."""

    def __init__(self, exc):
        self._exc = exc

    def shortlist(self, *args, **kwargs):
        return ["cheap-tier-map"]

    def read_candidates(self, *args, **kwargs):
        return [("cheap-tier-map", _MEMORY_CHEAP_TIER_MAP)], []

    def classify(self, *args, **kwargs):
        raise self._exc


def _typing_candidate(tmp_path):
    """One `Proposal` plus the memory plane beside it - just enough for
    `_type_proposal` to reach its call into `dedup` before that call raises."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    (memory_dir / "cheap-tier-map.md").write_text(_MEMORY_CHEAP_TIER_MAP)
    candidate = proposal.Proposal(
        file_text=_PROPOSAL_ONE,
        evidence=proposal.Evidence(transcript=tmp_path / "t1.jsonl", line_no=1, text=_SLICE_ONE),
    )
    index_text = _INDEX_HEADER + _ENTRY_CHEAP_TIER_MAP
    return candidate, memory_dir, index_text


def test_type_proposal_reports_a_fixed_message_when_the_typing_call_times_out(tmp_path):
    """A `TimeoutExpired` carries the whole argv it ran, which can hold a long
    prompt built from the candidate's own text. Echoing that into the
    published proposal would leak it, so the report holds a fixed message
    naming only the timeout, never the command or the prompt."""
    candidate, memory_dir, index_text = _typing_candidate(tmp_path)
    long_prompt = "classify this candidate against the shortlist: " + "x" * 500
    timeout = subprocess.TimeoutExpired(cmd=["claude", "-p", "sonnet", long_prompt], timeout=120)
    dedup_stub = _DedupClassifyRaises(timeout)

    typed = funnel._type_proposal(candidate, memory_dir, index_text, None, dedup_stub)

    assert typed.dedup_error == "the typing call timed out after 120s"


@pytest.mark.parametrize("exc_type", [RuntimeError, OSError])
def test_type_proposal_reports_the_error_message_unchanged(tmp_path, exc_type):
    """Neither a `RuntimeError` nor an `OSError` from the typing call is a leak
    risk the way a timeout's argv is, so each keeps its message flowing into
    the report unchanged. Only the timeout branch is rewritten to a fixed
    string."""
    candidate, memory_dir, index_text = _typing_candidate(tmp_path)
    dedup_stub = _DedupClassifyRaises(exc_type("boom"))

    typed = funnel._type_proposal(candidate, memory_dir, index_text, None, dedup_stub)

    assert typed.dedup_error == "the typing call failed: boom"
