"""Tests for the distil stage main() drives behind --distil: what it distils,
what it discards, and what it publishes. Holds the corpus fixtures the two
sibling distil test modules import."""

import json
import os
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import ModuleType, SimpleNamespace

import corpus
import dedup
import distil
import funnel
import proposal
import pytest


class FakeSessionData:
    """Stand-in for the real claude-checkup parser's SessionData: an object
    with `.earliest`/`.latest` datetime-or-None attributes."""

    def __init__(self, latest=None, earliest=None):
        self.latest = latest
        self.earliest = earliest


def make_transcript_parser_module(results_by_filename, *, version="0.3.0"):
    """A parser module stub whose parse_session(path) looks up its result by
    the transcript's filename, and which satisfies assert_contract()."""
    module = ModuleType("stub_transcript_parser")
    module.parse_session = lambda path: results_by_filename[Path(path).name]
    module.SessionData = FakeSessionData
    return module, version


def write_transcript(project_dir: Path, filename: str, content: str = "") -> Path:
    project_dir.mkdir(parents=True, exist_ok=True)
    transcript_path = project_dir / filename
    transcript_path.write_text(content)
    return transcript_path


_DISTIL_LABELS = ["proposals", "discards", "new_vs_update", "skipped_by_limit", "dedup_errors"]


_SLICE_ONE = "we measured that the cheap judge tier resolves to haiku"
_SLICE_TWO = "we verified that the yield report lands under audit results"
_SLICE_THREE = "we confirmed the suite passed again"

_INDEX_HEADER = "# Project memory\n\n"
_ENTRY_CHEAP_TIER_MAP = (
    "- [Cheap tier map](cheap-tier-map.md) — the cheap judge tier resolves to the haiku model.\n"
)
_ENTRY_REPORT_DIRECTORY = (
    "- [Report directory](report-directory.md) — the yield report lands under audit results.\n"
)
_INDEX = _INDEX_HEADER + _ENTRY_CHEAP_TIER_MAP + _ENTRY_REPORT_DIRECTORY

_MEMORY_CHEAP_TIER_MAP = """---
name: cheap-tier-map
description: "The cheap judge tier maps to the haiku model"
metadata:
  node_type: memory
  type: project
---

The cheap tier maps to haiku.

**Why:** the wrong tier picks the wrong model and every call costs more.

**How to apply:** read the tier map before naming a model.
"""

_MEMORY_REPORT_DIRECTORY = """---
name: report-directory
description: "The yield report is written under the audit results directory"
metadata:
  node_type: memory
  type: project
---

The yield report lands under dev/local/audit-results.

**Why:** a reader who looks anywhere else finds nothing.

**How to apply:** open that directory after a run.
"""

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

_PROPOSAL_ONE = """---
name: cheap-tier-is-haiku
description: "The cheap judge tier resolves to the haiku model"
metadata:
  node_type: memory
  type: project
---

The cheap tier resolves to haiku, so a cheap call never reaches sonnet. See [[cheap-tier-map]].

**Why:** a run that picks the strong tier for triage pays for every slice.

**How to apply:** name the tier, never the model, when asking for a verdict.
"""

_PROPOSAL_TWO = """---
name: report-under-audit-results
description: "The yield report is written under the audit results directory"
metadata:
  node_type: memory
  type: project
---

Every run writes its yield report under dev/local/audit-results. See [[report-directory]].

**Why:** a reader who looks in the skill directory finds nothing.

**How to apply:** open the audit results folder to read the newest report.
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


def _tier_note(number):
    """One more indexed memory sharing the proposal's words, so a long index
    offers a shortlist far more candidates than it is allowed to read."""
    name = f"tier-note-{number}"
    entry = (
        f"- [Tier note {number}]({name}.md) — "
        f"the cheap judge tier resolves to the haiku model, note {number}.\n"
    )
    text = f"""---
name: {name}
description: "The cheap judge tier resolves to the haiku model, note {number}"
metadata:
  node_type: memory
  type: project
---

Note {number} on the cheap tier.

**Why:** the tier map reads as settled while a note still disagrees with it.

**How to apply:** open note {number} beside the tier map.
"""
    return name, entry, text


def _deliver(cmd, answer):
    """One fake CLI answer: a string is stdout from a clean exit, a callable
    is a failing `subprocess.run` stand-in (the module already defines three)."""
    if callable(answer):
        return answer(cmd)
    return subprocess.CompletedProcess(args=cmd, returncode=0, stdout=answer, stderr="")


class FakeClaudeCli:
    """Stands in for the `claude` binary at funnel.subprocess.run, so the whole
    pipeline runs for real while no test reaches a model.

    Routes on what actually arrived: the cheap tier is always triage, a
    strong-tier prompt ending in a slice's text is the distil call (the distil
    prompt puts the snippet last), and any other strong-tier prompt is dedup's
    classify call. Records what it was asked, so a test can pin what the stage
    did NOT ask for.
    """

    def __init__(self, distil_answers, classify=None, transient_texts=()):
        self.distil_answers = dict(distil_answers)
        self.classify = classify if classify is not None else (lambda prompt: "new")
        self.transient_texts = tuple(transient_texts)
        self.distilled = []
        self.distil_prompts = []
        self.classified = []

    def __call__(self, cmd, **kwargs):
        prompt = cmd[-1]
        if cmd[3] == "haiku":
            verdict = "transient" if prompt.endswith(self.transient_texts) else "durable"
            return _deliver(cmd, verdict)
        for text, answer in self.distil_answers.items():
            if prompt.endswith(text):
                self.distilled.append(text)
                self.distil_prompts.append(prompt)
                return _deliver(cmd, answer)
        self.classified.append(prompt)
        return _deliver(cmd, self.classify(prompt))


def _refuse_to_distil(cmd, **kwargs):
    raise AssertionError("the stage must stop after the CLI goes missing, not distil the next survivor")


@pytest.fixture
def make_corpus(tmp_path, monkeypatch):
    """Build a one-project corpus under tmp_path and return its landmarks.

    Each `slice_texts` entry becomes one assistant text block on its own JSONL
    line of a single transcript, so slice N carries line_no N. The project's
    memory plane sits where the distil stage looks for it - beside the
    transcript, at `<project>/memory` - and holds an index naming two memories,
    both on disk, plus an unindexed decoy no step is allowed to open.
    `extra_memories` adds that many further indexed memories, for a plane whose
    index outgrows the shortlist.
    """

    def build(slice_texts=(_SLICE_ONE, _SLICE_TWO), extra_memories=0):
        monkeypatch.chdir(tmp_path)
        projects_root = tmp_path / "claude_projects"
        monkeypatch.setattr(corpus, "_PROJECTS_ROOT", projects_root)
        project_dir = projects_root / "aaaa-myproj"
        transcript = write_transcript(
            project_dir,
            "t1.jsonl",
            "".join(
                json.dumps({"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}) + "\n"
                for text in slice_texts
            ),
        )
        memory_dir = project_dir / "memory"
        memory_dir.mkdir()
        notes = [_tier_note(number) for number in range(1, extra_memories + 1)]
        (memory_dir / "MEMORY.md").write_text(_INDEX + "".join(entry for _, entry, _ in notes))
        for name, _entry, text in notes:
            (memory_dir / f"{name}.md").write_text(text)
        (memory_dir / "cheap-tier-map.md").write_text(_MEMORY_CHEAP_TIER_MAP)
        (memory_dir / "report-directory.md").write_text(_MEMORY_REPORT_DIRECTORY)
        (memory_dir / "unindexed-decoy.md").write_text("---\nname: unindexed-decoy\n---\n\nnot in the index\n")

        module, version = make_transcript_parser_module(
            {"t1.jsonl": FakeSessionData(latest=datetime.now(timezone.utc) - timedelta(days=1))}
        )
        monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (module, version))
        return SimpleNamespace(
            transcript=transcript,
            memory_dir=memory_dir,
            decoy=memory_dir / "unindexed-decoy.md",
            audit_dir=tmp_path / "dev" / "local" / "audit-results",
            version=version,
        )

    return build


# The two projects make_two_project_corpus builds, one row each: directory,
# transcript filename, the slice it carries, the index entry, and the memory
# that entry names.
_TWO_PROJECT_PLAN = (
    (
        "aaaa-projone",
        "t1.jsonl",
        _SLICE_ONE,
        _ENTRY_CHEAP_TIER_MAP,
        "cheap-tier-map",
        _MEMORY_CHEAP_TIER_MAP,
    ),
    (
        "bbbb-projtwo",
        "t2.jsonl",
        _SLICE_TWO,
        _ENTRY_REPORT_DIRECTORY,
        "report-directory",
        _MEMORY_REPORT_DIRECTORY,
    ),
)


@pytest.fixture
def make_two_project_corpus(tmp_path, monkeypatch):
    """Build a corpus of two projects and return both projects' landmarks.

    Each project owns a transcript carrying one slice, its own index naming one
    memory, and that memory on disk. Nothing is shared between the planes, so a
    proposal typed against the wrong one cannot resolve to an update.
    """

    def build():
        monkeypatch.chdir(tmp_path)
        projects_root = tmp_path / "claude_projects"
        monkeypatch.setattr(corpus, "_PROJECTS_ROOT", projects_root)

        projects = []
        for directory, filename, slice_text, entry, memory_name, memory_text in _TWO_PROJECT_PLAN:
            project_dir = projects_root / directory
            transcript = write_transcript(
                project_dir,
                filename,
                json.dumps(
                    {"type": "assistant", "message": {"content": [{"type": "text", "text": slice_text}]}}
                )
                + "\n",
            )
            memory_dir = project_dir / "memory"
            memory_dir.mkdir()
            (memory_dir / "MEMORY.md").write_text(_INDEX_HEADER + entry)
            (memory_dir / f"{memory_name}.md").write_text(memory_text)
            projects.append(SimpleNamespace(transcript=transcript, memory_dir=memory_dir))

        recent = FakeSessionData(latest=datetime.now(timezone.utc) - timedelta(days=1))
        module, version = make_transcript_parser_module({"t1.jsonl": recent, "t2.jsonl": recent})
        monkeypatch.setattr(corpus, "resolve_parser", lambda *a, **kw: (module, version))
        return SimpleNamespace(
            one=projects[0],
            two=projects[1],
            audit_dir=tmp_path / "dev" / "local" / "audit-results",
        )

    return build


def _published(audit_dir):
    """The single proposals directory a distil run publishes, with both of its
    manifests already parsed."""
    directories = sorted(audit_dir.glob("distil-memory-*-proposals"))
    assert len(directories) == 1, f"expected one proposals directory, found {[p.name for p in directories]}"
    out_dir = directories[0]
    return (
        out_dir,
        json.loads((out_dir / "proposals.json").read_text()),
        json.loads((out_dir / "discards.json").read_text()),
    )


def _record_read_text(monkeypatch):
    """Every path opened with Path.read_text from now on, in order."""
    reads = []
    real_read_text = Path.read_text

    def recording_read_text(self, *args, **kwargs):
        reads.append(Path(self))
        return real_read_text(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", recording_read_text)
    return reads


def _forbid_full_read(monkeypatch, memory_dir, decoy):
    """Make `decoy` explode when read and `memory_dir` explode when listed.

    An exception the pipeline could swallow would prove nothing, so both raise
    AssertionError, which no handler on the path catches.
    """
    real_read_text = Path.read_text
    real_scandir = os.scandir
    real_listdir = os.listdir

    def refuse_walk(path):
        try:
            walked = Path(path)
        except TypeError:
            return
        if walked == memory_dir:
            raise AssertionError(f"{memory_dir} must never be listed: only the names the index gives may be opened")

    def guarded_read_text(self, *args, **kwargs):
        if Path(self) == decoy:
            raise AssertionError(f"{decoy.name} is not named by the index and must never be read")
        return real_read_text(self, *args, **kwargs)

    def guarded_scandir(path=".", *args, **kwargs):
        refuse_walk(path)
        return real_scandir(path, *args, **kwargs)

    def guarded_listdir(path=".", *args, **kwargs):
        refuse_walk(path)
        return real_listdir(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", guarded_read_text)
    monkeypatch.setattr(os, "scandir", guarded_scandir)
    monkeypatch.setattr(os, "listdir", guarded_listdir)


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
