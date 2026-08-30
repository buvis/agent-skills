"""Tests for dedup.py's index side: read_index()'s absent-versus-unreadable
answer, parse_index()'s bullet-link shape, and shortlist()'s Jaccard ranking;
and for its decision side: read_candidates()'s exactly-the-named-files reads
and classify()'s new-versus-update typing."""

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

_PROSE_INDEX = (
    "# Memory\n"
    "\n"
    "A sentence of prose that carries no link.\n"
    "\n"
    f"{_RANKING_INDEX}"
    "\n"
    "- a plain bullet with no link at all\n"
)

# Six entries that all score identically, listed worst-name-first so index
# order and name order disagree.
_TIED_INDEX = "".join(f"- [Kestrel](entry-0{n}.md) — kestrel\n" for n in range(6, 0, -1))

# Indexes written in vocabulary that appears nowhere else in this file, so a
# ranking that recognises only wordings it has seen before cannot serve them.
_NOVEL_INDEX_A = (
    "- [Gantry Fennel Wicket](pumice-trellis.md) — loam gullet\n"
    "- [Wicket Gantry](gantry-loam.md) — fennel\n"
    "- [Cobalt Marrow](hazel-nettle.md) — plinth\n"
    "- [Spindle Quill](spindle-quill.md) — tinder\n"
)

_NOVEL_INDEX_C = (
    "- [Tinder Plinth](gullet-hazel.md) — quill\n"
    "- [Marrow](loam-spindle.md) — tinder cobalt plinth\n"
)

# Five entries whose scores are all DIFFERENT, listed in an order that is
# neither the ranked order nor its reverse, and named so that the best-scoring
# entry sorts alphabetically last.
_SCORED_INDEX = (
    "- [Cedar Bracken](cedar-mire.md) — thorn\n"
    "- [Willow Tarn Sedge](elm-thicket.md) — fen mire\n"
    "- [Sedge Willow](alder-brook.md) — bracken thorn heather\n"
    "- [Sedge Mire](dogwood-fen.md) — thorn\n"
    "- [Willow Sedge](birch-hollow.md) — tarn bracken\n"
)

# Decoy body for the novel-vocabulary proposals: tokens drawn from the index
# entries, so scoring the whole file instead of name + description reorders
# every row that reads _NOVEL_INDEX_A.
_NOVEL_BODY = "Gullet trellis pumice heather."

_SCORED_RANKING = [
    "elm-thicket",
    "dogwood-fen",
    "birch-hollow",
    "alder-brook",
    "cedar-mire",
]


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


@pytest.fixture
def memory_proposal():
    """A proposal whose frontmatter carries the query tokens `kestrel harbour
    lantern moss`. Its body repeats the decoy tokens that only the weaker index
    entry shares, so scoring the whole file instead of name + description
    reverses the ranking."""
    file_text = (
        "---\n"
        "name: kestrel harbour\n"
        "description: lantern moss\n"
        "metadata:\n"
        "  type: project\n"
        "---\n"
        "\n"
        "Beacon cinder dune atlas.\n"
    )
    return proposal.Proposal(
        file_text=file_text,
        evidence=proposal.Evidence(
            transcript=Path("transcript.jsonl"), line_no=1, text="evidence text"
        ),
    )


@pytest.fixture
def quartz_proposal():
    """A second proposal for the same index, whose frontmatter carries the
    query tokens `quartz vellum lantern dune` instead. Its body repeats the
    tokens the other proposal queries with, so scoring the whole file instead
    of name + description would collapse the two rankings into one."""
    file_text = (
        "---\n"
        "name: quartz vellum\n"
        "description: lantern dune\n"
        "metadata:\n"
        "  type: project\n"
        "---\n"
        "\n"
        "Kestrel harbour moss beacon cinder.\n"
    )
    return proposal.Proposal(
        file_text=file_text,
        evidence=proposal.Evidence(
            transcript=Path("transcript.jsonl"), line_no=2, text="evidence text"
        ),
    )


def test_shortlist_limit_constant_is_five():
    assert dedup.SHORTLIST_LIMIT == 5


def test_candidate_is_a_memory_name_and_file_text_pair():
    assert dedup.Candidate == tuple[str, str]


def test_parse_index_maps_each_link_target_stem_to_its_title_and_hook():
    assert dedup.parse_index(_RANKING_INDEX) == {
        "harbour-atlas": "Kestrel Lantern Moss beacon cinder dune",
        "kestrel-harbour": "Lantern Kestrel harbour lantern",
        "moss-lantern": "Quartz vellum sable",
    }


@pytest.mark.parametrize(
    ("line", "expected"),
    [
        ("- [Zzz Qqq](novel-stem.md) — hook words\n", {"novel-stem": "Zzz Qqq hook words"}),
        (
            "- [Yew Fathom](brindle-glim.md) — tallow rushlight\n",
            {"brindle-glim": "Yew Fathom tallow rushlight"},
        ),
        (
            "- [Sundial](ninth-orrery-2.md) — gnomon shadow.\n",
            {"ninth-orrery-2": "Sundial gnomon shadow."},
        ),
    ],
    ids=["two-word-title", "two-word-hook", "digit-in-stem"],
)
def test_parse_index_reads_the_title_hook_and_stem_of_any_bullet_link(line, expected):
    """The title, the link target and the hook are three independent parts of
    the line, so a reader that recognises only the wordings it has seen before
    must fail on wordings that appear nowhere else."""
    assert dedup.parse_index(line) == expected


def test_parse_index_ignores_lines_that_are_not_bullet_links():
    prose_only = (
        "# Memory\n"
        "\n"
        "A sentence of prose that carries no link.\n"
        "\n"
        "- a plain bullet with no link at all\n"
    )

    assert dedup.parse_index(prose_only) == {}


@pytest.mark.parametrize(
    "line",
    [
        "See [Field Notes](field-notes.md) — the manual.\n",
        "A [Field Guide](field-guide.md) sits mid-sentence and stays prose.\n",
        "  [Field Notes](field-notes.md) — indented, still no bullet.\n",
    ],
    ids=["prose-leads", "link-mid-sentence", "indented-no-bullet"],
)
def test_parse_index_ignores_a_markdown_link_that_is_not_a_bullet_line(line):
    """Only bullet-link LINES are entries. A link the index merely mentions in
    a sentence names no memory, so a reader that scans for links anywhere on a
    line invents an entry that does not exist."""
    assert dedup.parse_index(line) == {}


@pytest.mark.parametrize(
    "line",
    [
        "- [Docs](https://example.com/page) — an external page.\n",
        "- [Field Notes](field-notes) — no suffix at all.\n",
        "- [Field Notes](field-notes.txt) — the wrong suffix.\n",
    ],
    ids=["http-target", "no-suffix", "wrong-suffix"],
)
def test_parse_index_ignores_a_bullet_link_whose_target_is_not_a_markdown_file(line):
    """The name is the link target with its `.md` suffix removed, so a target
    that never carried that suffix names no memory."""
    assert dedup.parse_index(line) == {}


def test_parse_index_keeps_the_bullet_links_that_prose_surrounds():
    assert dedup.parse_index(_PROSE_INDEX) == {
        "harbour-atlas": "Kestrel Lantern Moss beacon cinder dune",
        "kestrel-harbour": "Lantern Kestrel harbour lantern",
        "moss-lantern": "Quartz vellum sable",
    }


def test_shortlist_ranks_by_jaccard_score_not_intersection_size_or_overlap(memory_proposal):
    """q = {kestrel, harbour, lantern, moss}. Per entry, e adds the link name
    to the title and hook:

    - harbour-atlas: e has 8 tokens, 4 shared -> 4/8 = 0.5
    - kestrel-harbour: e has 3 tokens, 3 shared -> 3/4 = 0.75
    - moss-lantern: e has 5 tokens, 2 shared -> 2/7 = 0.2857

    Raw intersection would put harbour-atlas (4) first; the overlap
    coefficient would score harbour-atlas and kestrel-harbour both 1.0 and
    break that tie by name, also putting harbour-atlas first. Dropping the
    link name from e would zero moss-lantern and shorten the list.
    """
    assert dedup.shortlist(_RANKING_INDEX, memory_proposal) == [
        "kestrel-harbour",
        "harbour-atlas",
        "moss-lantern",
    ]


def test_shortlist_reranks_the_same_index_for_a_different_proposal(quartz_proposal):
    """Same index, different query: q = {quartz, vellum, lantern, dune}.

    - moss-lantern: e has 5 tokens, 3 shared -> 3/6 = 0.5
    - harbour-atlas: e has 8 tokens, 2 shared -> 2/10 = 0.2
    - kestrel-harbour: e has 3 tokens, 1 shared -> 1/6 = 0.1667

    That is the exact reverse of the order the other proposal produces over
    these same three entries, so a ranking that never reads the proposal - a
    fixed permutation, or index order - cannot satisfy both tests.
    """
    assert dedup.shortlist(_RANKING_INDEX, quartz_proposal) == [
        "moss-lantern",
        "harbour-atlas",
        "kestrel-harbour",
    ]


def test_shortlist_drops_an_entry_only_when_it_shares_no_tokens_with_the_proposal(
    memory_proposal, quartz_proposal
):
    """`vellum-ochre` shares nothing with q = {kestrel, harbour, lantern, moss}
    (0/8), so it goes; `kestrel-harbour` scores 3/4 and stays. The same entry
    is then the TOP result for the other proposal (2 shared of 6 union = 0.333,
    against 1/6 for kestrel-harbour), so dropping it can only come from the
    token scoring, never from its name or its position in the index.
    """
    index = (
        "- [Quartz Vellum](vellum-ochre.md) — sable ochre\n"
        "- [Lantern Kestrel](kestrel-harbour.md) — harbour lantern\n"
    )

    assert dedup.shortlist(index, memory_proposal) == ["kestrel-harbour"]
    assert dedup.shortlist(index, quartz_proposal) == ["vellum-ochre", "kestrel-harbour"]


@pytest.mark.parametrize(
    ("index_text", "name", "description", "expected"),
    [
        (
            _NOVEL_INDEX_A,
            "gantry fennel",
            "wicket loam",
            ["gantry-loam", "pumice-trellis"],
        ),
        (
            _NOVEL_INDEX_A,
            "cobalt marrow",
            "plinth gantry",
            ["hazel-nettle", "gantry-loam", "pumice-trellis"],
        ),
        (
            _NOVEL_INDEX_A,
            "spindle quill",
            "gantry wicket",
            ["spindle-quill", "gantry-loam", "pumice-trellis"],
        ),
        (
            _NOVEL_INDEX_C,
            "tinder plinth",
            "cobalt marrow",
            ["loam-spindle", "gullet-hazel"],
        ),
    ],
    ids=[
        "gantry-loam-4of4-beats-pumice-trellis-4of7-zeroes-dropped",
        "hazel-nettle-3of6-beats-gantry-loam-1of7-beats-pumice-trellis-1of10",
        "spindle-quill-2of5-beats-gantry-loam-2of6-beats-pumice-trellis-2of9",
        "loam-spindle-4of6-beats-gullet-hazel-2of7",
    ],
)
def test_shortlist_ranks_indexes_and_proposals_it_has_never_seen(
    index_text, name, description, expected
):
    """Every token here appears nowhere else in this file, so nothing but the
    `len(q & e) / len(q | e)` arithmetic can produce these orders. Each id
    spells its row's scores out: `4of7` is four shared tokens over a seven-token
    union. The third row also separates Jaccard from raw intersection - `2of5`,
    `2of6` and `2of9` all tie at two shared tokens - and every row's winner
    differs from the alphabetically first name, the index's first entry, or
    both.
    """
    assert dedup.shortlist(index_text, _proposal_named(name, description, _NOVEL_BODY)) == expected


def test_shortlist_orders_distinct_scores_by_score_alone():
    """q = {willow, tarn, sedge, fen, mire}, and the five entries score five
    different values:

    - elm-thicket: e has 7 tokens, 5 shared -> 5/7 = 0.714
    - dogwood-fen: e has 5 tokens, 3 shared -> 3/7 = 0.429
    - birch-hollow: e has 6 tokens, 3 shared -> 3/8 = 0.375
    - alder-brook: e has 7 tokens, 2 shared -> 2/10 = 0.2
    - cedar-mire: e has 4 tokens, 1 shared -> 1/8 = 0.125

    That order is not alphabetical, not reverse alphabetical, not the index's
    order and not its reverse, so no arrangement of the names or the lines
    produces it. Raw intersection and the overlap coefficient both tie
    dogwood-fen with birch-hollow and would swap them.
    """
    scored_proposal = _proposal_named(
        "willow tarn", "sedge fen mire", "Bracken thorn heather cedar."
    )

    assert dedup.shortlist(_SCORED_INDEX, scored_proposal) == _SCORED_RANKING


def test_shortlist_truncates_by_score_rather_than_by_name():
    """The best-scoring entry, elm-thicket, sorts alphabetically LAST of the
    five, so a `limit` applied to alphabetised names returns alder-brook and
    birch-hollow - the two WORST entries - instead of the two best."""
    scored_proposal = _proposal_named(
        "willow tarn", "sedge fen mire", "Bracken thorn heather cedar."
    )

    assert dedup.shortlist(_SCORED_INDEX, scored_proposal, limit=2) == [
        "elm-thicket",
        "dogwood-fen",
    ]


def test_shortlist_ignores_the_order_the_index_lists_its_entries_in():
    """The same five entries, lines reversed. Ranking reads scores, not
    positions, so reversing the index must change nothing - which pins the
    result against index order and against reverse index order at once."""
    reversed_index = "".join(reversed(_SCORED_INDEX.splitlines(keepends=True)))
    scored_proposal = _proposal_named(
        "willow tarn", "sedge fen mire", "Bracken thorn heather cedar."
    )

    assert dedup.shortlist(reversed_index, scored_proposal) == _SCORED_RANKING


def test_shortlist_returns_no_names_for_an_empty_index(memory_proposal):
    assert dedup.shortlist("", memory_proposal) == []


def test_shortlist_returns_at_most_shortlist_limit_names(memory_proposal):
    result = dedup.shortlist(_TIED_INDEX, memory_proposal)

    assert len(result) == dedup.SHORTLIST_LIMIT


def test_shortlist_orders_equal_scores_by_name_not_by_index_order(memory_proposal):
    assert dedup.shortlist(_TIED_INDEX, memory_proposal) == [
        "entry-01",
        "entry-02",
        "entry-03",
        "entry-04",
        "entry-05",
    ]


def test_shortlist_honours_an_explicit_limit_below_the_default(memory_proposal):
    assert dedup.shortlist(_TIED_INDEX, memory_proposal, limit=2) == ["entry-01", "entry-02"]


def test_shortlist_reads_no_files_while_ranking(monkeypatch, memory_proposal):
    def fail_if_called(self, *args, **kwargs):
        raise AssertionError(f"shortlist must not read {self}")

    monkeypatch.setattr(Path, "read_text", fail_if_called)

    assert dedup.shortlist(_RANKING_INDEX, memory_proposal) == [
        "kestrel-harbour",
        "harbour-atlas",
        "moss-lantern",
    ]


def test_read_index_returns_empty_string_when_the_index_is_absent(tmp_path):
    """A memory plane with memories but no index is still an absent index, so
    the decoy memory file next to it must not be mistaken for one."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    (memory_dir / "AAA-decoy.md").write_text("a memory file, not the index\n")

    assert dedup.read_index(memory_dir) == ""


def test_read_index_returns_the_index_text_when_it_is_present(tmp_path):
    """The decoy sorts before MEMORY.md, so reading whichever file comes first
    in the directory returns the wrong text."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    (memory_dir / "AAA-decoy.md").write_text("a memory file, not the index\n")
    (memory_dir / "MEMORY.md").write_text(_RANKING_INDEX)

    assert dedup.read_index(memory_dir) == _RANKING_INDEX


def test_read_index_raises_oserror_when_the_index_exists_but_cannot_be_read(tmp_path):
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    index = memory_dir / "MEMORY.md"
    index.write_text(_RANKING_INDEX)
    index.chmod(0o000)

    try:
        index.read_text()
    except OSError:
        pass
    else:
        index.chmod(0o600)
        pytest.skip("this user reads a 0o000 file anyway, so unreadable cannot be exercised")

    try:
        with pytest.raises(OSError):
            dedup.read_index(memory_dir)
    finally:
        index.chmod(0o600)


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

        def fail_if_called(*args, **kwargs):
            raise AssertionError("read_candidates must not list the memory plane")

        monkeypatch.setattr(Path, "read_text", recording_read_text)
        monkeypatch.setattr(Path, "open", recording_path_open)
        monkeypatch.setattr(builtins, "open", recording_open)
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
