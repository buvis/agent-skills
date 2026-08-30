"""Tests for dedup.py's decision side: read_candidates()'s exactly-the-named-files
reads and classify()'s new-versus-update typing."""

import builtins
import os
import subprocess
from pathlib import Path

import dedup
import funnel
import proposal
import pytest

# The separator in a real MEMORY.md bullet line is an em-dash (U+2014).
_RANKING_INDEX = (
    "- [Kestrel Lantern Moss](harbour-atlas.md) — beacon cinder dune\n"
    "- [Lantern Kestrel](kestrel-harbour.md) — harbour lantern\n"
    "- [Quartz](moss-lantern.md) — vellum sable\n"
)


def _proposal_named(name: str, description: str, body: str) -> proposal.Proposal:
    """A proposal whose frontmatter carries `name` and `description`, over a
    `body` of decoy tokens that scoring the whole file would wrongly admit."""
    file_text = (
        "---\n"
        f"name: {name}\n"
        f"description: {description}\n"
        "metadata:\n"
        "  type: project\n"
        "---\n"
        "\n"
        f"{body}\n"
    )
    return proposal.Proposal(
        file_text=file_text,
        evidence=proposal.Evidence(
            transcript=Path("transcript.jsonl"), line_no=3, text="evidence text"
        ),
    )


def _memory_text(name: str, description: str, body: str) -> str:
    """The full text of an existing memory file: frontmatter, then a body."""
    return _proposal_named(name, description, body).file_text


# Three memories that already exist. Each file's frontmatter name is the human
# wording, while the memory NAME is the link stem the index carries, so the two
# can never be confused for one another. Each body closes with a tail sentence
# that appears nowhere else, so a reader returning a file's head - or a prompt
# truncating a candidate - drops a token these tests look for.
_ATLAS_TEXT = _memory_text(
    "Harbour Atlas",
    "beacon cinder dune",
    "The atlas charts every beacon.\n\nTail sentence: sextant ledger.",
)
_MOSS_TEXT = _memory_text(
    "Moss Lantern",
    "vellum sable",
    "The lantern is kept in the moss.\n\nTail sentence: wick tallow.",
)
_KESTREL_TEXT = _memory_text(
    "Kestrel Harbour",
    "harbour lantern",
    "The kestrel nests above the harbour.\n\nTail sentence: thermal updraft.",
)

_ATLAS = ("harbour-atlas", _ATLAS_TEXT)
_MOSS = ("moss-lantern", _MOSS_TEXT)
_KESTREL = ("kestrel-harbour", _KESTREL_TEXT)


def _generated_memories(prefix: str, count: int) -> dict[str, str]:
    """`count` memories, each mapping its name to its own full file text.

    Names are built here from the caller's `prefix` and a counter rather than
    written out, so each test works in a vocabulary no other test in this file
    uses, and every expectation is computed from this mapping. Each text names
    its own memory throughout, so a reader that pairs a name with another
    memory's text returns a text naming the wrong memory.
    """
    return {
        f"{prefix}-{n:02d}": _memory_text(
            f"{prefix.title()} {n:02d}",
            f"{prefix} entry {n:02d}",
            f"The {prefix} memory numbered {n:02d}.\n\nTail sentence: {prefix}-{n:02d}-wick.",
        )
        for n in range(1, count + 1)
    }


def _memory_plane(tmp_path: Path, memories: dict[str, str]) -> Path:
    """A memory directory holding exactly `memories`, one `<name>.md` each."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    for name, text in memories.items():
        (memory_dir / f"{name}.md").write_text(text)
    return memory_dir


def _record_reads(monkeypatch) -> list[Path]:
    """Every door onto a file's bytes - `Path.read_text`, `Path.open` and the
    builtin `open`, any of which a correct reader may use - patched to record
    the path it was handed into the list returned."""
    read_text = Path.read_text
    path_open = Path.open
    builtin_open = builtins.open
    paths_read = []

    def recording_read_text(self, *args, **kwargs):
        paths_read.append(self)
        return read_text(self, *args, **kwargs)

    def recording_path_open(self, *args, **kwargs):
        paths_read.append(self)
        return path_open(self, *args, **kwargs)

    def recording_open(file, *args, **kwargs):
        paths_read.append(Path(file))
        return builtin_open(file, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", recording_read_text)
    monkeypatch.setattr(Path, "open", recording_path_open)
    monkeypatch.setattr(builtins, "open", recording_open)
    return paths_read


class TestDecisionSide:
    """read_candidates() reads exactly the shortlisted files, and classify()
    types the proposal `new` or `update <name>` without touching a file."""

    @pytest.fixture(autouse=True)
    def never_reaches_the_real_model(self, monkeypatch):
        """No test on this side may spend a token. `classify` binds
        `funnel.judge` as a default argument at import time, so every test here
        passes its own stub; this is the backstop that catches one that does
        not, instead of letting it call the CLI for real."""

        def fail_if_called(cmd, **kwargs):
            raise AssertionError("no decision-side test may reach the real model")

        monkeypatch.setattr(funnel.subprocess, "run", fail_if_called)

    def test_read_candidates_returns_each_named_memory_as_a_name_and_full_text_pair(self, tmp_path):
        """Each pair carries the whole file of the memory it names, tail
        sentence included. Both the directory and the expectation are built
        from one mapping this test generates, so the answer has to be computed
        from the files rather than recognised."""
        memories = _generated_memories("brindle", 4)
        memory_dir = _memory_plane(tmp_path, memories)
        asked = ["brindle-03", "brindle-01"]

        candidates, unread_names = dedup.read_candidates(memory_dir, asked)

        assert candidates == [(name, memories[name]) for name in asked]
        assert unread_names == []

    def test_read_candidates_answers_one_directory_in_whichever_order_it_is_asked(self, tmp_path):
        """The order is the shortlist's ranking, not the directory's, so the
        same three files asked for twice in two orders must come back twice in
        two orders. Sorting the names, keeping directory order, or answering
        from a remembered result serves at most one of the two calls."""
        memories = _generated_memories("wicket", 3)
        memory_dir = _memory_plane(tmp_path, memories)
        ranked = ["wicket-02", "wicket-03", "wicket-01"]
        reranked = ["wicket-03", "wicket-01", "wicket-02"]

        assert dedup.read_candidates(memory_dir, ranked) == (
            [(name, memories[name]) for name in ranked],
            [],
        )
        assert dedup.read_candidates(memory_dir, reranked) == (
            [(name, memories[name]) for name in reranked],
            [],
        )

    def test_read_candidates_answers_from_the_memory_directory_it_was_given(self, tmp_path):
        """Memory planes reuse names across projects, so the same name is a
        different memory in each one. Both planes here hold the same names over
        different texts, and the nearer plane is asked again after the farther
        one, so a reader that answers a name from whatever it read last - or
        from anything remembered under the name alone - hands the distiller
        another project's memory to diff the proposal against."""
        names = list(_generated_memories("ferrule", 3))
        here = {
            name: _memory_text(name, "ferrule entry", f"The nearer plane's {name}.")
            for name in names
        }
        there = {
            name: _memory_text(name, "ferrule entry", f"The farther plane's {name}.")
            for name in names
        }
        (tmp_path / "project-one").mkdir()
        (tmp_path / "project-two").mkdir()
        here_dir = _memory_plane(tmp_path / "project-one", here)
        there_dir = _memory_plane(tmp_path / "project-two", there)
        asked = names[:2]
        from_here = [(name, here[name]) for name in asked]
        from_there = [(name, there[name]) for name in asked]

        assert dedup.read_candidates(here_dir, asked) == (from_here, [])
        assert dedup.read_candidates(there_dir, asked) == (from_there, [])
        assert dedup.read_candidates(here_dir, asked) == (from_here, [])

    def test_read_candidates_reads_only_the_files_the_shortlist_named(self, tmp_path, monkeypatch):
        """The memory plane holds every memory and its index. Reading the plane
        to answer for one name is the cost the shortlist exists to avoid.

        Every door onto a file's bytes is recorded here - `Path.read_text`,
        `Path.open` and the builtin `open`, any of which a correct reader may
        use - and the recorded set has to be exactly the one shortlisted file.
        So an index scan, and a pass that reads the whole plane and discards
        what it was not asked for, both fail. The directory listings pathlib
        and os offer are refused outright, so reaching the files through a glob
        fails too.
        """
        memories = _generated_memories("tallow", 4)
        memory_dir = _memory_plane(tmp_path, memories)
        (memory_dir / "MEMORY.md").write_text(_RANKING_INDEX)

        paths_read = _record_reads(monkeypatch)

        def fail_if_called(*args, **kwargs):
            raise AssertionError("read_candidates must not list the memory plane")

        monkeypatch.setattr(Path, "glob", fail_if_called)
        monkeypatch.setattr(Path, "iterdir", fail_if_called)
        monkeypatch.setattr(os, "listdir", fail_if_called)
        monkeypatch.setattr(os, "scandir", fail_if_called)

        candidates, unread_names = dedup.read_candidates(memory_dir, ["tallow-02"])

        assert set(paths_read) == {memory_dir / "tallow-02.md"}
        assert candidates == [("tallow-02", memories["tallow-02"])]
        assert unread_names == []

    def test_read_candidates_reports_an_unreadable_memory_and_skips_a_missing_one(self, tmp_path):
        """A name the index lists but the plane no longer holds is a stale
        entry, not a failure, so it leaves no trace. A file that is there but
        unreadable is the dangerous case - nothing can be compared against it -
        so it is named, and the caller turns that into a dedup error."""
        memories = _generated_memories("gantry", 3)
        memory_dir = _memory_plane(tmp_path, memories)
        missing = "gantry-04"
        locked = memory_dir / "gantry-03.md"
        locked.chmod(0o000)

        try:
            locked.read_text()
        except OSError:
            pass
        else:
            locked.chmod(0o600)
            pytest.skip("this user reads a 0o000 file anyway, so unreadable cannot be exercised")

        try:
            candidates, unread_names = dedup.read_candidates(
                memory_dir, ["gantry-01", missing, "gantry-03", "gantry-02"]
            )
        finally:
            locked.chmod(0o600)

        assert candidates == [
            ("gantry-01", memories["gantry-01"]),
            ("gantry-02", memories["gantry-02"]),
        ]
        assert unread_names == ["gantry-03"]

    @pytest.mark.parametrize(
        "traversing_name",
        ["../outside/secret", "nested/../../outside/secret"],
        ids=["separator-leads", "separator-in-the-middle"],
    )
    def test_read_candidates_skips_a_name_carrying_a_path_separator(
        self, tmp_path, traversing_name
    ):
        """A memory name is a plain filename stem, so a name carrying a
        separator names no memory in this plane and is as absent as a stale
        index entry. The readable file it points at outside the plane proves
        the reader never went there: it would come back as a candidate, text
        and all. The ordinary name asked for beside it still answers, so
        refusing every name is no way to pass.

        The second row opens with a directory the plane really holds and hides
        its separators in the middle, so it reads as an ordinary name to anyone
        who inspects only where it starts - and walks out of the plane all the
        same, onto the same file as the first row.
        """
        memories = _generated_memories("trestle", 2)
        memory_dir = _memory_plane(tmp_path, memories)
        (memory_dir / "nested").mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "secret.md").write_text("A file the memory plane does not hold.\n")

        candidates, unread_names = dedup.read_candidates(
            memory_dir, [traversing_name, "trestle-01"]
        )

        assert candidates == [("trestle-01", memories["trestle-01"])]
        assert unread_names == []

    def test_read_candidates_skips_a_name_carrying_a_windows_style_separator(self, tmp_path):
        """A separator is a separator wherever a memory plane is read, so a
        name built with backslashes is no plain stem either. A file sits here
        at exactly the name a check written for `/` alone lets through - inside
        the plane, real and readable - so such a reader returns its text as a
        candidate rather than skipping the name.
        """
        memories = _generated_memories("mullion", 2)
        memory_dir = _memory_plane(tmp_path, memories)
        (memory_dir / "..\\outside\\secret.md").write_text("A file no memory name reaches.\n")

        candidates, unread_names = dedup.read_candidates(
            memory_dir, ["..\\outside\\secret", "mullion-01"]
        )

        assert candidates == [("mullion-01", memories["mullion-01"])]
        assert unread_names == []

    def test_read_candidates_reads_no_path_that_resolves_outside_the_memory_directory(
        self, tmp_path, monkeypatch
    ):
        """The rows above each name one shape of escape; this is the rule they
        are instances of, so an escape shaped like nothing anyone wrote a row
        for still fails here. Every door onto a file's bytes is recorded, and
        every path that reaches one has to resolve inside the plane - which a
        reader passes by refusing the name, never by reading the file and
        discarding what came back.
        """
        memories = _generated_memories("corbel", 2)
        memory_dir = _memory_plane(tmp_path, memories)
        (memory_dir / "nested").mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "secret.md").write_text("A file the memory plane does not hold.\n")

        paths_read = _record_reads(monkeypatch)

        candidates, unread_names = dedup.read_candidates(
            memory_dir,
            [
                "../outside/secret",
                "nested/../../outside/secret",
                str(outside / "secret"),
                "corbel-01",
            ],
        )

        plane = memory_dir.resolve()
        assert [path for path in paths_read if not path.resolve().is_relative_to(plane)] == []
        assert candidates == [("corbel-01", memories["corbel-01"])]
        assert unread_names == []

    def test_read_candidates_skips_a_dot_dot_name_rather_than_reporting_it_unread(self, tmp_path):
        """A name that is no stem is absent, not unread. The difference is what
        the caller does with each: `unread_names` becomes a dedup error, so a
        malformed index entry landing there mistypes the proposal over a memory
        nobody named. `..` carries no separator and, suffixed, lands on a
        directory here, which fails to read rather than reading as missing - so
        a reader that only watches for separators reports it unread.
        """
        memories = _generated_memories("lintel", 2)
        memory_dir = _memory_plane(tmp_path, memories)
        (memory_dir / "...md").mkdir()

        candidates, unread_names = dedup.read_candidates(memory_dir, ["..", "lintel-02"])

        assert candidates == [("lintel-02", memories["lintel-02"])]
        assert unread_names == []

    def test_read_candidates_skips_an_absolute_name(self, tmp_path):
        """Joining an absolute name onto the plane's path discards the plane
        and leaves the absolute path, so an absolute name reaches outside with
        no `..` in it at all. It is no stem either, so it names no memory here.
        """
        memories = _generated_memories("quoin", 2)
        memory_dir = _memory_plane(tmp_path, memories)
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "secret.md").write_text("A file the memory plane does not hold.\n")

        candidates, unread_names = dedup.read_candidates(
            memory_dir, [str(outside / "secret"), "quoin-01"]
        )

        assert candidates == [("quoin-01", memories["quoin-01"])]
        assert unread_names == []

    @pytest.mark.parametrize("position", [0, 1, 2], ids=["first", "middle", "last"])
    def test_classify_types_a_name_collision_as_an_update_without_asking_the_judge(self, position):
        """A proposal whose frontmatter name is a memory name already in use is
        a settled collision, not a judgement. Letting it through as NEW would
        have the writing step overwrite the memory holding that name. The
        colliding candidate takes each position of the shortlist in turn, so
        comparing against only its first or its last entry fails a row, and the
        names are generated here, so recognising a remembered one fails all
        three."""
        memories = _generated_memories("plinth", 3)
        candidates = list(memories.items())
        colliding_name = list(memories)[position]
        colliding = _proposal_named(colliding_name, "vellum sable", "Restated fact.")

        def fail_if_called(prompt, tier):
            raise AssertionError("a name collision is settled without a model call")

        assert dedup.classify(
            colliding, candidates, judge=fail_if_called
        ) == proposal.update_kind(colliding_name)

    def test_classify_asks_the_judge_about_a_proposal_whose_name_no_candidate_holds(self):
        """The short-circuit is name EQUALITY, not resemblance. A proposal
        named in the shortlist's own naming scheme, but by a name no candidate
        holds, is still an open question, so it must reach the judge - a
        classifier that answers every well-shaped name from the names alone
        never asks."""
        memories = _generated_memories("marrow", 4)
        candidates = list(memories.items())[:3]
        unheld_name = list(memories)[3]
        fresh = _proposal_named(unheld_name, "cobalt spindle", "An unrelated fact.")
        calls = []

        def stub_judge(prompt, tier):
            calls.append(prompt)
            return proposal.NEW

        assert dedup.classify(fresh, candidates, judge=stub_judge) == proposal.NEW
        assert len(calls) == 1

    @pytest.mark.parametrize(
        "shape",
        ["{stem}", "{held}-extra"],
        ids=["name-inside-a-candidate-name", "name-around-a-candidate-name"],
    )
    def test_classify_asks_the_judge_when_the_proposal_name_only_overlaps_a_candidate_name(
        self, shape
    ):
        """The short-circuit is name EQUALITY. One row proposes a name that is
        a strict SUBSTRING of a candidate's name, the other a name that strictly
        CONTAINS one, and neither is the name of any memory that exists - so
        neither is the settled collision that would let the writing step
        overwrite a memory. Both are open questions the judge must be asked,
        and a short-circuit that fires on `in` either way answers both from the
        names alone and never asks."""
        memories = _generated_memories("plinth", 3)
        candidates = list(memories.items())
        held = list(memories)[0]
        stem = held.rpartition("-")[0]
        overlapping = _proposal_named(shape.format(stem=stem, held=held), "vellum sable", "A fact.")
        calls = []

        def stub_judge(prompt, tier):
            calls.append(prompt)
            return proposal.NEW

        assert dedup.classify(overlapping, candidates, judge=stub_judge) == proposal.NEW
        assert len(calls) == 1

    @pytest.mark.parametrize(
        ("prefix", "size", "answered"),
        [
            ("cinnabar", 3, 0),
            ("cinnabar", 3, 2),
            ("orpiment", 4, 1),
            ("verdigris", 1, 0),
        ],
        ids=["first-of-three", "last-of-three", "middle-of-four", "only-candidate"],
    )
    def test_classify_types_the_proposal_an_update_of_the_candidate_the_judge_names(
        self, prefix, size, answered
    ):
        """The answer AND the shortlist it names both move between rows, and
        every name is generated from the row's own prefix, so it appears
        nowhere else in this file. A classifier that always returns the first
        candidate, the last one, or a name from a set it was written with
        satisfies at most one row."""
        memories = _generated_memories(prefix, size)
        candidates = list(memories.items())
        answer = list(memories)[answered]
        fresh = _proposal_named("quartz vellum", "lantern dune", "Kestrel harbour moss.")

        def stub_judge(prompt, tier):
            return answer

        assert dedup.classify(fresh, candidates, judge=stub_judge) == proposal.update_kind(answer)

    def test_classify_reads_the_answer_through_the_trailing_newline_the_cli_returns(self):
        """`funnel.judge` hands back the CLI's raw stdout, newline and all, so
        an answer compared byte for byte would never name a candidate once a
        real model is on the other end."""
        memories = _generated_memories("rushlight", 2)
        candidates = list(memories.items())
        answered = list(memories)[1]
        fresh = _proposal_named("quartz vellum", "lantern dune", "Kestrel harbour moss.")

        def stub_judge(prompt, tier):
            return f"{answered}\n"

        assert dedup.classify(fresh, candidates, judge=stub_judge) == proposal.update_kind(answered)

    @pytest.mark.parametrize(
        "answer",
        ["new", "New.", "", "none of them", "I cannot tell from what you gave me"],
        ids=["exact-new", "decorated-new", "empty", "names-nothing", "unparseable"],
    )
    def test_classify_types_the_proposal_new_when_the_answer_names_no_candidate(self, answer):
        """Fail open toward a new memory, matching triage's stance: an answer
        that names nothing is not evidence of a duplicate."""
        fresh = _proposal_named("quartz vellum", "lantern dune", "Kestrel harbour moss.")

        def stub_judge(prompt, tier):
            return answer

        assert dedup.classify(fresh, [_ATLAS, _MOSS, _KESTREL], judge=stub_judge) == proposal.NEW

    def test_classify_types_a_proposal_with_no_candidates_new_without_a_model_call(self):
        """Nothing to compare against is not a question worth paying for."""
        fresh = _proposal_named("quartz vellum", "lantern dune", "Kestrel harbour moss.")

        def fail_if_called(prompt, tier):
            raise AssertionError("an empty shortlist is settled without a model call")

        assert dedup.classify(fresh, [], judge=fail_if_called) == proposal.NEW

    @pytest.mark.parametrize(
        "error",
        [
            RuntimeError("claude cli exploded"),
            subprocess.TimeoutExpired(cmd=["claude"], timeout=120),
            OSError("the model route is gone"),
            FileNotFoundError("claude"),
        ],
        ids=["runtime-error", "timeout", "os-error", "missing-binary"],
    )
    def test_classify_propagates_a_judge_failure_instead_of_typing_the_proposal_new(self, error):
        """A swallowed failure is indistinguishable from a real NEW answer and
        would file a duplicate as a fresh memory. The caller records a dedup
        error and keeps the proposal; classify does not decide for it."""
        fresh = _proposal_named("quartz vellum", "lantern dune", "Kestrel harbour moss.")

        def failing_judge(prompt, tier):
            raise error

        with pytest.raises(type(error)):
            dedup.classify(fresh, [_ATLAS, _MOSS], judge=failing_judge)

    def test_classify_asks_the_strong_tier_judge_once_for_the_whole_shortlist(self):
        """One question about three candidates, not one question each."""
        fresh = _proposal_named("quartz vellum", "lantern dune", "Kestrel harbour moss.")
        calls = []

        def stub_judge(prompt, tier):
            calls.append((prompt, tier))
            return "new"

        dedup.classify(fresh, [_ATLAS, _MOSS, _KESTREL], judge=stub_judge)

        assert [tier for _, tier in calls] == ["strong"]

    def test_classify_shows_the_judge_the_proposal_and_every_candidate_in_full(self):
        """Spotting a restatement is impossible from names alone or from a
        truncated candidate, so the prompt carries the proposal's own text and
        every candidate's whole file. The answer has to be one candidate's
        NAME, so each text is also labelled with the name that goes with it:
        the name falls in the few characters that run up to its own text.

        Every generated memory repeats its own name inside its body, so a
        prompt that strings the texts together under no names at all still
        contains all three names. Only checking each name against the window
        that runs up to its own text rules such a prompt out.
        """
        memories = _generated_memories("fathom", 3)
        candidates = list(memories.items())
        fresh = _proposal_named("quartz vellum", "lantern dune", "Kestrel harbour moss.")
        # Shorter than the shortest generated memory file, so a name found in
        # this window labels the text that follows it and cannot be a stray
        # mention carried inside the candidate before it.
        label_window = 64
        prompts = []

        def stub_judge(prompt, tier):
            prompts.append(prompt)
            return proposal.NEW

        dedup.classify(fresh, candidates, judge=stub_judge)

        (prompt,) = prompts
        assert fresh.file_text in prompt
        for name, text in candidates:
            assert text in prompt
            start = prompt.index(text)
            assert name in prompt[max(0, start - label_window) : start]

    def test_classify_tells_the_judge_to_answer_with_a_memory_name_or_the_word_new(self):
        """The texts alone are a blob, not a task: a model handed them without
        an instruction has no reason to answer with a bare name, and every
        answer this side can read is either a candidate's name or the literal
        `new`. Strike out the proposal, every candidate text and every
        candidate name, and what remains is the prompt's own wording: it has to
        be a spoken instruction - long enough to be a sentence, asking for an
        answer - that states both legal answers. Two bare nouns dropped between
        the texts satisfy a reader looking for keywords, and tell a model
        nothing.
        """
        memories = _generated_memories("sextant", 2)
        candidates = list(memories.items())
        fresh = _proposal_named("quartz vellum", "lantern dune", "Kestrel harbour moss.")
        # A sentence that poses the question and states both legal answers runs
        # to about twenty words; this is the floor below which no such sentence
        # fits.
        min_instruction_words = 12
        prompts = []

        def stub_judge(prompt, tier):
            prompts.append(prompt)
            return proposal.NEW

        dedup.classify(fresh, candidates, judge=stub_judge)

        (prompt,) = prompts
        instruction = prompt.replace(fresh.file_text, "")
        for _name, text in candidates:
            instruction = instruction.replace(text, "")
        for name, _text in candidates:
            instruction = instruction.replace(name, "")
        instruction = instruction.lower()

        assert len(instruction.split()) >= min_instruction_words
        assert any(verb in instruction for verb in ("answer", "reply", "respond"))
        assert "name" in instruction
        assert proposal.NEW in instruction
