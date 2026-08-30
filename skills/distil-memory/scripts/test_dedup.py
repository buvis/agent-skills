"""Tests for dedup.py's index side: read_index()'s absent-versus-unreadable
answer, parse_index()'s bullet-link shape, and shortlist()'s Jaccard ranking."""

import errno
import io
from pathlib import Path

import dedup
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


def _index_whose_read_fails(tmp_path, monkeypatch, error: OSError) -> Path:
    """A memory directory holding a real MEMORY.md whose every read raises
    `error`. The file is genuinely there, so a reader that checks before it
    reads sees an index and only the read itself can say otherwise - the window
    between the check and the read, made reproducible."""
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    (memory_dir / "MEMORY.md").write_text(_RANKING_INDEX)

    def failing_read(self, *args, **kwargs):
        raise error

    monkeypatch.setattr(Path, "read_text", failing_read)
    monkeypatch.setattr(Path, "open", failing_read)
    return memory_dir


@pytest.mark.parametrize(
    "error",
    [
        FileNotFoundError(errno.ENOENT, "No such file or directory"),
        FileNotFoundError("gone"),
    ],
    ids=["carrying-errno-2", "carrying-no-errno"],
)
def test_read_index_treats_an_index_gone_by_the_time_it_is_read_as_absent(
    tmp_path, monkeypatch, error
):
    """An index deleted between the check and the read is absent, not
    unreadable. The two answers pinned above stay as they are - a missing index
    yields "" and an unreadable one raises - and this is the case they leave
    open: a `FileNotFoundError` raised by the read itself still means the file
    is not there, so it yields "" instead of failing the run over a file that
    merely is not there.

    What says "not there" is the KIND of error, never its number. The second
    row carries no errno at all, so a reader that sorts errors by errno has
    nothing to sort it by and fails the run over a file that merely is gone.
    """
    memory_dir = _index_whose_read_fails(tmp_path, monkeypatch, error)

    assert dedup.read_index(memory_dir) == ""


def test_read_index_answers_with_what_the_read_returns_not_with_an_earlier_check(
    tmp_path, monkeypatch
):
    """The same window, entered from the other side: an index that lands
    between a check and the read is present. Nothing is on disk here and the
    read hands back an index anyway, so a reader that decides from a check made
    before the read reports the plane as empty - and an empty plane types every
    duplicate as new, which is the confusion this function exists to prevent.
    """
    memory_dir = tmp_path / "memory"
    memory_dir.mkdir()
    real_read_text = Path.read_text
    real_open = Path.open

    def read_text_of_an_index_that_arrived_late(self, *args, **kwargs):
        if self.name == "MEMORY.md":
            return _RANKING_INDEX
        return real_read_text(self, *args, **kwargs)

    def open_an_index_that_arrived_late(self, *args, **kwargs):
        if self.name == "MEMORY.md":
            return io.StringIO(_RANKING_INDEX)
        return real_open(self, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", read_text_of_an_index_that_arrived_late)
    monkeypatch.setattr(Path, "open", open_an_index_that_arrived_late)

    assert dedup.read_index(memory_dir) == _RANKING_INDEX


@pytest.mark.parametrize(
    "error",
    [
        PermissionError(errno.EACCES, "Permission denied"),
        OSError(errno.EIO, "Input/output error"),
        InterruptedError(errno.EINTR, "Interrupted system call"),
    ],
    ids=["permission-denied-13", "disk-io-error-5", "interrupted-4"],
)
def test_read_index_propagates_a_read_failure_that_is_not_the_index_being_gone(
    tmp_path, monkeypatch, error
):
    """The absent-versus-unreadable distinction has to hold in both directions.
    A read that fails for any reason other than the file being gone leaves the
    index unknown, and answering "" there would type a duplicate as new and
    write a second copy of a memory the plane already holds.

    A missing file carries errno 2 and a locked one carries 13, so a reader
    that swallows the small numbers and raises the large ones separates those
    two by accident. The disk error (5) and the interrupted read (4) sit
    between them: both leave the index unknown, and both are numerically small.
    The error that comes back out is the one that went in, so a reader that
    reports a disk failure as some other trouble fails too.
    """
    memory_dir = _index_whose_read_fails(tmp_path, monkeypatch, error)

    with pytest.raises(OSError) as raised:
        dedup.read_index(memory_dir)

    assert raised.value is error
