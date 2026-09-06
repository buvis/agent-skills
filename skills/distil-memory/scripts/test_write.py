"""Tests for write.py: writing an approved proposal's memory file into a
memory store and upserting the store's MEMORY.md pointer line."""

from pathlib import Path

import dedup
import proposal
import write

import pytest

from write_test_helpers import _entry, _file_text, _parser_message, store_path


# file_texts the frontmatter parser refuses. The last three open and close their
# --- block correctly, so only a real YAML parse can tell they are broken. The
# last one is a _file_text() output with a defect injected into one value, so it
# carries the same name, the same description key, the same metadata/type block
# and the same body as the valid fixtures: no surface feature separates it from
# a good file, and nothing but parsing it can decide it.
MALFORMED_FILE_TEXTS = [
    pytest.param("no frontmatter here\n", id="no-opening-marker"),
    pytest.param(
        "---\nname: widget-fact\ndescription: a fact worth keeping\n", id="no-closing-marker"
    ),
    pytest.param("---\n- a\n- b\n---\n\nBody.\n", id="sequence-not-mapping"),
    pytest.param("---\nname: [unclosed\n---\n\nBody.\n", id="unparseable-yaml"),
    pytest.param(
        _file_text(description="[unclosed"), id="unparseable-yaml-with-full-metadata-block"
    ),
]


def test_write_memory_writes_new_entry_to_a_file_named_after_the_sanitised_name(store_path):
    store_path.mkdir()
    entry = _entry(name="Widget Fact", kind="new", file_text=_file_text(name="Widget Fact"))

    written = write.write_memory(entry, store_path)

    stem = proposal.sanitise_name("Widget Fact")
    assert written == store_path / f"{stem}.md"
    assert written.read_text() == entry["file_text"]


def test_write_memory_new_raises_and_does_not_touch_the_file_when_the_target_already_exists(
    store_path,
):
    store_path.mkdir()
    (store_path / "widget-fact.md").write_text("original content")
    entry = _entry(name="widget-fact", kind="new")

    with pytest.raises(write.WriteError):
        write.write_memory(entry, store_path)

    assert (store_path / "widget-fact.md").read_text() == "original content"


def test_write_memory_update_overwrites_the_existing_target_file(store_path):
    store_path.mkdir()
    (store_path / "widget-fact.md").write_text("old content")
    new_text = _file_text(name="widget-fact", description="updated description")
    entry = _entry(
        name="widget-fact", kind="update widget-fact", file_text=new_text, existing_text="old content"
    )

    written = write.write_memory(entry, store_path)

    assert written == store_path / "widget-fact.md"
    assert written.read_text() == new_text


def test_write_memory_update_raises_when_the_target_file_is_absent(store_path):
    store_path.mkdir()
    entry = _entry(name="widget-fact", kind="update widget-fact")

    with pytest.raises(write.WriteError):
        write.write_memory(entry, store_path)

    assert not (store_path / "widget-fact.md").exists()


def test_write_memory_raises_and_creates_nothing_when_the_store_path_does_not_exist(store_path):
    entry = _entry(name="widget-fact", kind="new")

    with pytest.raises(write.WriteError):
        write.write_memory(entry, store_path)

    assert not store_path.exists()


def test_write_memory_update_targets_the_file_named_by_kind_even_when_file_texts_own_name_field_differs(
    store_path,
):
    store_path.mkdir()
    (store_path / "widget-fact.md").write_text("old content")
    new_text = _file_text(name="totally-different-name", description="updated description")
    entry = _entry(
        name="widget-fact", kind="update widget-fact", file_text=new_text, existing_text="old content"
    )

    written = write.write_memory(entry, store_path)

    assert written == store_path / "widget-fact.md"
    assert written.read_text() == new_text
    assert not (store_path / "totally-different-name.md").exists()


@pytest.mark.parametrize("malformed", MALFORMED_FILE_TEXTS)
def test_write_memory_raises_the_parsers_own_message_and_leaves_the_store_empty_when_file_text_will_not_parse(
    store_path, malformed
):
    store_path.mkdir()
    parser_message = _parser_message(malformed)
    entry = _entry(name="widget-fact", kind="new", file_text=malformed)

    with pytest.raises(write.WriteError) as raised:
        write.write_memory(entry, store_path)

    assert parser_message in str(raised.value)
    assert isinstance(raised.value.__cause__, proposal.ProposalError)
    assert list(store_path.iterdir()) == []


def test_write_memory_writes_file_text_whose_frontmatter_parses_even_when_it_is_not_the_usual_shape(
    store_path,
):
    store_path.mkdir()
    # A valid _file_text() with one unremarkable extra line in the frontmatter:
    # the parser accepts it, so the write must too. Rejecting whatever looks
    # unfamiliar is as wrong as accepting whatever looks familiar.
    unusual_but_valid = _file_text(name="widget-fact").replace(
        "---\n\n", "# a note for whoever reads this next\n---\n\n"
    )
    assert unusual_but_valid != _file_text(name="widget-fact")
    proposal.parse_frontmatter(unusual_but_valid)
    entry = _entry(name="widget-fact", kind="new", file_text=unusual_but_valid)

    written = write.write_memory(entry, store_path)

    assert written == store_path / "widget-fact.md"
    assert written.read_text() == unusual_but_valid
    assert [p.name for p in store_path.iterdir()] == ["widget-fact.md"]


def test_write_memory_rejects_malformed_file_text_for_an_update_without_touching_the_existing_file(
    store_path,
):
    store_path.mkdir()
    target_path = store_path / "widget-fact.md"
    original_text = _file_text(name="widget-fact", description="old description")
    target_path.write_text(original_text)
    malformed = "---\n- a\n- b\n---\n\nBody.\n"
    parser_message = _parser_message(malformed)
    entry = _entry(
        name="widget-fact",
        kind="update widget-fact",
        file_text=malformed,
        existing_text=original_text,
    )

    with pytest.raises(write.WriteError) as raised:
        write.write_memory(entry, store_path)

    assert parser_message in str(raised.value)
    assert isinstance(raised.value.__cause__, proposal.ProposalError)
    assert target_path.read_text() == original_text
    assert [p.name for p in store_path.iterdir()] == ["widget-fact.md"]


def test_append_pointer_new_creates_memory_md_with_one_parseable_line_when_it_is_absent(store_path):
    store_path.mkdir()
    entry = _entry(
        name="widget-fact",
        kind="new",
        file_text=_file_text(name="widget-fact", description="keeps facts about widgets straight"),
    )

    line = write.append_pointer(store_path, entry)

    assert line == "- [Widget fact](widget-fact.md) — keeps facts about widgets straight"
    index_text = (store_path / "MEMORY.md").read_text()
    assert index_text.count("widget-fact.md") == 1
    parsed = dedup.parse_index(index_text)
    assert parsed["widget-fact"] == "Widget fact keeps facts about widgets straight"


def test_append_pointer_new_appends_after_existing_lines_without_disturbing_them(store_path):
    store_path.mkdir()
    existing_line = "- [Other thing](other-thing.md) — something unrelated"
    (store_path / "MEMORY.md").write_text(existing_line + "\n")
    entry = _entry(
        name="widget-fact",
        kind="new",
        file_text=_file_text(name="widget-fact", description="keeps facts about widgets straight"),
    )

    line = write.append_pointer(store_path, entry)

    lines = (store_path / "MEMORY.md").read_text().splitlines()
    assert lines == [existing_line, line]


def test_append_pointer_new_always_appends_even_when_a_line_for_the_same_stem_already_exists(
    store_path,
):
    store_path.mkdir()
    index_path = store_path / "MEMORY.md"
    index_path.write_text("- [Widget fact](widget-fact.md) — a stale line\n")
    entry = _entry(
        name="widget-fact",
        kind="new",
        file_text=_file_text(name="widget-fact", description="a fresh description"),
    )

    line = write.append_pointer(store_path, entry)

    lines = index_path.read_text().splitlines()
    assert lines == ["- [Widget fact](widget-fact.md) — a stale line", line]


def test_append_pointer_title_replaces_hyphens_with_spaces_and_capitalises_only_the_first_letter(
    store_path,
):
    store_path.mkdir()
    entry = _entry(
        name="queue-cursor-is-lifetime",
        kind="new",
        file_text=_file_text(name="queue-cursor-is-lifetime", description="the cursor never resets"),
    )

    line = write.append_pointer(store_path, entry)

    assert line == "- [Queue cursor is lifetime](queue-cursor-is-lifetime.md) — the cursor never resets"


def test_append_pointer_new_names_the_pointer_after_the_sanitised_stem_not_the_raw_name(store_path):
    store_path.mkdir()
    entry = _entry(
        name="Widget Fact",
        kind="new",
        file_text=_file_text(name="Widget Fact", description="keeps facts about widgets straight"),
    )

    line = write.append_pointer(store_path, entry)

    assert line == "- [Widget fact](widget-fact.md) — keeps facts about widgets straight"
    index_text = (store_path / "MEMORY.md").read_text()
    parsed = dedup.parse_index(index_text)
    assert parsed["widget-fact"] == "Widget fact keeps facts about widgets straight"


def test_append_pointer_update_returns_none_and_leaves_memory_md_unchanged_when_description_is_identical(
    store_path,
):
    store_path.mkdir()
    old_text = _file_text(name="widget-fact", description="keeps facts about widgets straight")
    index_path = store_path / "MEMORY.md"
    index_path.write_text(
        "- [Something](something.md) — unrelated\n"
        "- [Widget fact](widget-fact.md) — keeps facts about widgets straight\n"
        "- [Another](another.md) — also unrelated\n"
    )
    original_bytes = index_path.read_bytes()
    new_text = _file_text(
        name="widget-fact", description="keeps facts about widgets straight", body="New body."
    )
    entry = _entry(
        name="widget-fact", kind="update widget-fact", file_text=new_text, existing_text=old_text
    )

    result = write.append_pointer(store_path, entry)

    assert result is None
    assert index_path.read_bytes() == original_bytes


def test_append_pointer_update_replaces_the_existing_line_in_place_when_description_differs(
    store_path,
):
    store_path.mkdir()
    old_text = _file_text(name="widget-fact", description="old description")
    index_path = store_path / "MEMORY.md"
    index_path.write_text(
        "- [Something](something.md) — unrelated\n"
        "- [Widget fact](widget-fact.md) — old description\n"
        "- [Another](another.md) — also unrelated\n"
    )
    new_text = _file_text(name="widget-fact", description="new, more accurate description")
    entry = _entry(
        name="widget-fact", kind="update widget-fact", file_text=new_text, existing_text=old_text
    )

    line = write.append_pointer(store_path, entry)

    assert line == "- [Widget fact](widget-fact.md) — new, more accurate description"
    lines = index_path.read_text().splitlines()
    assert lines == [
        "- [Something](something.md) — unrelated",
        line,
        "- [Another](another.md) — also unrelated",
    ]


def test_append_pointer_update_replaces_the_line_named_by_kind_even_when_file_texts_own_name_field_differs(
    store_path,
):
    store_path.mkdir()
    old_text = _file_text(name="widget-fact", description="old description")
    index_path = store_path / "MEMORY.md"
    index_path.write_text(
        "- [Something](something.md) — unrelated\n"
        "- [Widget fact](widget-fact.md) — old description\n"
        "- [Another](another.md) — also unrelated\n"
    )
    new_text = _file_text(name="totally-different-name", description="new, more accurate description")
    entry = _entry(
        name="widget-fact", kind="update widget-fact", file_text=new_text, existing_text=old_text
    )

    line = write.append_pointer(store_path, entry)

    assert line == "- [Widget fact](widget-fact.md) — new, more accurate description"
    lines = index_path.read_text().splitlines()
    assert lines == [
        "- [Something](something.md) — unrelated",
        line,
        "- [Another](another.md) — also unrelated",
    ]
    assert not any("totally-different-name" in existing_line for existing_line in lines)


def test_append_pointer_update_appends_when_description_differs_but_no_existing_line_matches_the_stem(
    store_path,
):
    store_path.mkdir()
    old_text = _file_text(name="widget-fact", description="old description")
    index_path = store_path / "MEMORY.md"
    index_path.write_text("- [Something](something.md) — unrelated\n")
    new_text = _file_text(name="widget-fact", description="new description")
    entry = _entry(
        name="widget-fact", kind="update widget-fact", file_text=new_text, existing_text=old_text
    )

    line = write.append_pointer(store_path, entry)

    lines = index_path.read_text().splitlines()
    assert lines == ["- [Something](something.md) — unrelated", line]


def test_new_proposal_written_file_passes_the_frontmatter_contract_and_exactly_one_line_is_appended(
    store_path,
):
    store_path.mkdir()
    entry = _entry(
        name="widget-fact",
        kind="new",
        file_text=_file_text(name="widget-fact", description="keeps facts about widgets straight"),
    )

    written = write.write_memory(entry, store_path)
    line = write.append_pointer(store_path, entry)

    written_proposal = proposal.Proposal(
        file_text=written.read_text(),
        evidence=proposal.Evidence(transcript=Path("t.jsonl"), line_no=1, text="evidence"),
    )
    proposal.validate(written_proposal)

    index_text = (store_path / "MEMORY.md").read_text()
    assert index_text.count("widget-fact.md") == 1
    assert line in index_text


def test_update_proposal_replaces_the_named_file_and_leaves_memory_md_unchanged_when_description_is_unchanged(
    store_path,
):
    store_path.mkdir()
    old_text = _file_text(name="widget-fact", description="keeps facts about widgets straight")
    (store_path / "widget-fact.md").write_text(old_text)
    index_path = store_path / "MEMORY.md"
    index_path.write_text("- [Widget fact](widget-fact.md) — keeps facts about widgets straight\n")
    original_index_bytes = index_path.read_bytes()
    new_text = _file_text(
        name="widget-fact", description="keeps facts about widgets straight", body="Updated body."
    )
    entry = _entry(
        name="widget-fact", kind="update widget-fact", file_text=new_text, existing_text=old_text
    )

    written = write.write_memory(entry, store_path)
    result = write.append_pointer(store_path, entry)

    assert written.read_text() == new_text
    assert result is None
    assert index_path.read_bytes() == original_index_bytes


def test_write_error_is_a_value_error():
    assert issubclass(write.WriteError, ValueError)
