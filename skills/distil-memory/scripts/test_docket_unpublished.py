"""Tests for docket.py: unpublished(), the kept entries a store does not yet
hold, and the `unpublished --store <path> [--queue <path>]` subcommand."""

import json

import docket

import proposal

import pytest

import write

from docket_test_helpers import make_proposal as _proposal
from write_test_helpers import _entry, _file_text, _parser_message


# Every store here is a real directory and every "published" state is made by
# the real write.write_memory + write.append_pointer, so "published" means
# exactly what write.published() confirms. An entry's own store is the
# `memory` directory beside its transcript, so each project below is a
# directory holding a transcript path and a `memory/` store.
#
# Where order matters, queue order is the reverse of both name order and id
# order (names "zeta-..." before "alpha-...", line numbers falling), so a
# sorted result cannot pass for one in queue order.


def _project(parent, name="proj"):
    project = parent / name
    (project / "memory").mkdir(parents=True)
    return project


def _kept(project, line_no, name, kind="new", file_text=None, existing_text=None):
    proposal_record = _proposal(
        transcript=str(project / "session.jsonl"),
        line_no=line_no,
        name=name,
        file_text=file_text if file_text is not None else _file_text(name=name),
    )
    return dict(proposal_record, kind=kind, existing_text=existing_text)


def _id(proposal_record):
    return docket.slice_key(proposal_record["transcript"], proposal_record["line_no"])


def _queue_kept(queue_path, proposals):
    docket.save(proposals, path=queue_path)
    for proposal_record in proposals:
        docket.decide(_id(proposal_record), "kept", path=queue_path)


def _publish(entry, store):
    write.write_memory(entry, store)
    write.append_pointer(store, entry)


NOT_UTF8 = b"\xff\xfe not utf-8\n"
V1 = _file_text(name="widget-fact", description="first version of the fact")
V2 = _file_text(name="widget-fact", description="second version of the fact")
V3 = _file_text(name="widget-fact", description="third version of the fact")


def _store_holding_v1(project):
    store = project / "memory"
    _publish(_entry(name="widget-fact", file_text=V1), store)
    return store


def _update(project, line_no, file_text, existing_text, name="widget-fact"):
    return _kept(
        project, line_no, name, kind="update widget-fact", file_text=file_text, existing_text=existing_text
    )


# unpublished(): the function.


def test_unpublished_returns_only_kept_entries_missing_from_the_store_in_queue_order(tmp_path):
    queue_path = tmp_path / "queue.json"
    project = _project(tmp_path)
    store = project / "memory"
    zeta = _kept(project, 9, "zeta-missing")
    undecided = _kept(project, 8, "undecided-missing")
    published = _kept(project, 7, "published-fact")
    dropped = _kept(project, 6, "dropped-missing")
    alpha = _kept(project, 2, "alpha-missing")
    docket.save([zeta, undecided, published, dropped, alpha], path=queue_path)
    for proposal_record in (zeta, published, alpha):
        docket.decide(_id(proposal_record), "kept", path=queue_path)
    docket.decide(_id(dropped), "dropped", path=queue_path)
    _publish(published, store)

    assert docket.unpublished(store, path=queue_path) == [_id(zeta), _id(alpha)]


def test_unpublished_lists_an_update_whose_target_still_holds_the_old_text(tmp_path):
    queue_path = tmp_path / "queue.json"
    project = _project(tmp_path)
    store = _store_holding_v1(project)
    update = _update(project, 1, V2, V1)
    _queue_kept(queue_path, [update])
    assert (store / "widget-fact.md").exists()

    assert docket.unpublished(store, path=queue_path) == [_id(update)]

    _publish(update, store)

    assert docket.unpublished(store, path=queue_path) == []


def test_unpublished_lists_an_interrupted_update_whose_file_was_written_but_pointer_was_not(
    tmp_path,
):
    queue_path = tmp_path / "queue.json"
    project = _project(tmp_path)
    store = _store_holding_v1(project)
    update = _update(project, 1, V2, V1)
    _queue_kept(queue_path, [update])
    write.write_memory(update, store)
    assert (store / "widget-fact.md").read_text() == V2

    assert docket.unpublished(store, path=queue_path) == [_id(update)]


def test_unpublished_lists_a_new_entry_whose_file_is_written_but_has_no_pointer(tmp_path):
    queue_path = tmp_path / "queue.json"
    project = _project(tmp_path)
    store = project / "memory"
    anchor = _kept(project, 1, "anchor-fact")
    unpointed = _kept(project, 2, "unpointed-fact")
    _queue_kept(queue_path, [anchor, unpointed])
    _publish(anchor, store)
    write.write_memory(unpointed, store)
    assert (store / "MEMORY.md").exists()
    assert (store / "unpointed-fact.md").exists()

    assert docket.unpublished(store, path=queue_path) == [_id(unpointed)]


def test_unpublished_checks_only_the_last_kept_update_of_a_target_and_never_lists_an_earlier_one(
    tmp_path,
):
    # The later update is named differently from the file it targets, so the
    # two share a target only through `kind`, never through `name`.
    queue_path = tmp_path / "queue.json"
    project = _project(tmp_path)
    store = _store_holding_v1(project)
    earlier = _update(project, 1, V2, V1)
    later = _update(project, 2, V3, V2, name="renamed-widget")
    _queue_kept(queue_path, [earlier, later])

    _publish(earlier, store)

    assert docket.unpublished(store, path=queue_path) == [_id(later)]

    _publish(later, store)

    assert write.published(earlier, store) is False
    assert docket.unpublished(store, path=queue_path) == []


def test_unpublished_never_lists_a_kept_new_entry_superseded_by_a_later_update_of_its_target(
    tmp_path,
):
    queue_path = tmp_path / "queue.json"
    project = _project(tmp_path)
    store = project / "memory"
    created = _kept(project, 1, "widget-fact", file_text=V1)
    updated = _update(project, 2, V2, V1, name="renamed-widget")
    _queue_kept(queue_path, [created, updated])
    _publish(created, store)
    _publish(updated, store)

    assert write.published(created, store) is False
    assert docket.unpublished(store, path=queue_path) == []


def test_unpublished_lists_a_superseding_owner_at_its_own_queue_position(tmp_path):
    # A1, B1, A2: A2 replaces A1 as the owner of A's target, so it is listed
    # after B1, where it sits in the queue, not in A1's earlier slot.
    queue_path = tmp_path / "queue.json"
    project = _project(tmp_path)
    store = project / "memory"
    a1 = _kept(project, 3, "widget-fact", file_text=V1)
    b1 = _kept(project, 2, "other-fact")
    a2 = _update(project, 1, V2, V1)
    _queue_kept(queue_path, [a1, b1, a2])

    assert docket.unpublished(store, path=queue_path) == [_id(b1), _id(a2)]


@pytest.mark.parametrize("later_decision", ["undecided", "dropped"])
def test_unpublished_lets_only_a_kept_entry_supersede_another_for_the_same_target(
    tmp_path, later_decision
):
    queue_path = tmp_path / "queue.json"
    project = _project(tmp_path)
    store = project / "memory"
    kept = _kept(project, 1, "widget-fact", file_text=V1)
    later = _kept(project, 2, "widget-fact", file_text=V2)
    docket.save([kept, later], path=queue_path)
    docket.decide(_id(kept), "kept", path=queue_path)
    if later_decision == "dropped":
        docket.decide(_id(later), "dropped", path=queue_path)

    assert docket.unpublished(store, path=queue_path) == [_id(kept)]


def test_unpublished_ignores_kept_entries_of_another_store_even_for_the_same_target(tmp_path):
    queue_path = tmp_path / "queue.json"
    own_project = _project(tmp_path, "own")
    other_project = _project(tmp_path, "other")
    namesake_project = _project(tmp_path / "elsewhere", "own")
    own = _kept(own_project, 1, "widget-fact")
    other_same_target = _kept(other_project, 2, "widget-fact")
    other_elsewhere = _kept(other_project, 3, "other-fact")
    namesake = _kept(namesake_project, 4, "namesake-fact")
    _queue_kept(queue_path, [own, other_same_target, other_elsewhere, namesake])
    (own_project / "sub").mkdir()
    store_spelled_another_way = own_project / "sub" / ".." / "memory"

    assert docket.unpublished(str(store_spelled_another_way), path=queue_path) == [_id(own)]


def test_unpublished_lists_a_kept_entry_whose_envelope_has_no_kind_without_raising(tmp_path):
    queue_path = tmp_path / "queue.json"
    project = _project(tmp_path)
    store = project / "memory"
    published = _kept(project, 1, "published-fact")
    kindless = {k: v for k, v in _kept(project, 2, "kindless-fact").items() if k != "kind"}
    _queue_kept(queue_path, [published, kindless])
    _publish(published, store)

    assert docket.unpublished(store, path=queue_path) == [_id(kindless)]


def test_unpublished_lists_a_kept_entry_whose_file_text_frontmatter_does_not_parse(tmp_path):
    queue_path = tmp_path / "queue.json"
    project = _project(tmp_path)
    store = project / "memory"
    published = _kept(project, 1, "published-fact")
    broken_text = "Body only, no frontmatter.\n"
    _parser_message(broken_text)
    broken = _kept(project, 2, "broken-fact", file_text=broken_text)
    _queue_kept(queue_path, [published, broken])
    _publish(published, store)
    (store / "broken-fact.md").write_text(broken_text)
    with pytest.raises(proposal.ProposalError):
        write.published(broken, store)

    assert docket.unpublished(store, path=queue_path) == [_id(broken)]


# A store whose index is not UTF-8, two ways: with every kept target missing,
# and with a kept update's target present but still holding the old text. In
# neither may a missing or stale target hide the unreadable index.


def _index_unreadable_with_every_target_missing(tmp_path):
    queue_path = tmp_path / "q.json"
    project = _project(tmp_path)
    store = project / "memory"
    (store / "MEMORY.md").write_bytes(NOT_UTF8)
    _queue_kept(queue_path, [_kept(project, 2, "zeta-missing"), _kept(project, 1, "alpha-missing")])
    return store, queue_path


def _index_unreadable_with_an_update_target_holding_the_old_text(tmp_path):
    queue_path = tmp_path / "q.json"
    project = _project(tmp_path)
    store = _store_holding_v1(project)
    _queue_kept(queue_path, [_update(project, 1, V2, V1)])
    (store / "MEMORY.md").write_bytes(NOT_UTF8)
    assert (store / "widget-fact.md").read_text() == V1
    return store, queue_path


_UNREADABLE_INDEX_STORES = {
    "every-target-missing": _index_unreadable_with_every_target_missing,
    "update-target-holds-old-text": _index_unreadable_with_an_update_target_holding_the_old_text,
}


@pytest.mark.parametrize(
    "build_store", list(_UNREADABLE_INDEX_STORES.values()), ids=list(_UNREADABLE_INDEX_STORES)
)
def test_unpublished_raises_a_write_error_for_an_unreadable_index(tmp_path, build_store):
    store, queue_path = build_store(tmp_path)

    with pytest.raises(write.WriteError):
        docket.unpublished(store, path=queue_path)


def test_unpublished_raises_a_queue_error_for_an_unreadable_queue(tmp_path):
    queue_path = tmp_path / "queue.json"
    queue_path.write_text('{"cursor": 0, "entries": [')
    store = _project(tmp_path) / "memory"

    with pytest.raises(docket.QueueError):
        docket.unpublished(store, path=queue_path)


# main(["unpublished", ...]): the subcommand.


def _the_working_directory_report_dir(tmp_path):
    return tmp_path / "docs" / "dev" / "project-management" / "audit-results"


def _assert_the_store_diagnostic_names(err, store, unreadable_path):
    prefix = f"cannot check the store {store}: "
    assert prefix in err
    assert str(unreadable_path) in err.split(prefix, 1)[1]
    assert "Traceback" not in err


def test_unpublished_lists_kept_entries_whose_file_is_missing_and_exits_one(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    project = _project(tmp_path)
    store = project / "memory"
    zeta = _kept(project, 9, "zeta-missing")
    published = _kept(project, 5, "published-fact")
    alpha = _kept(project, 2, "alpha-missing")
    _queue_kept(None, [zeta, published, alpha])
    _publish(published, store)
    capsys.readouterr()

    exit_code = docket.main(["unpublished", "--store", str(store)])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == f"{_id(zeta)}\n{_id(alpha)}\n"


def test_main_unpublished_prints_nothing_and_exits_zero_when_every_kept_entry_is_published(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    project = _project(tmp_path)
    store = project / "memory"
    entries = [_kept(project, 1, "first-fact"), _kept(project, 2, "second-fact")]
    _queue_kept(None, entries)
    for entry in entries:
        _publish(entry, store)
    capsys.readouterr()

    exit_code = docket.main(["unpublished", "--store", str(store)])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""


def test_main_unpublished_with_queue_flag_reads_the_given_queue(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    queue_path = tmp_path / "elsewhere" / "q.json"
    project = _project(tmp_path)
    store = project / "memory"
    missing = _kept(project, 1, "missing-fact")
    _queue_kept(queue_path, [missing])
    capsys.readouterr()

    exit_code = docket.main(["unpublished", "--store", str(store), "--queue", str(queue_path)])

    assert exit_code == 1
    assert capsys.readouterr().out == f"{_id(missing)}\n"
    assert not _the_working_directory_report_dir(tmp_path).exists()


def test_main_unpublished_exits_two_with_a_diagnostic_when_the_queue_is_unreadable(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    queue_path = tmp_path / "q.json"
    queue_path.write_text("")
    store = _project(tmp_path) / "memory"
    with pytest.raises(docket.QueueError) as raised:
        docket.load(path=queue_path)

    exit_code = docket.main(["unpublished", "--store", str(store), "--queue", str(queue_path)])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert str(raised.value) in captured.err
    assert "Traceback" not in captured.err
    assert captured.out == ""


@pytest.mark.parametrize(
    "build_store", list(_UNREADABLE_INDEX_STORES.values()), ids=list(_UNREADABLE_INDEX_STORES)
)
def test_main_unpublished_exits_one_with_no_stdout_when_the_index_is_unreadable(
    tmp_path, monkeypatch, capsys, build_store
):
    monkeypatch.chdir(tmp_path)
    store, queue_path = build_store(tmp_path)
    capsys.readouterr()

    exit_code = docket.main(["unpublished", "--store", str(store), "--queue", str(queue_path)])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    _assert_the_store_diagnostic_names(captured.err, store, store / "MEMORY.md")


def test_main_unpublished_prints_no_partial_list_when_a_later_target_cannot_be_read(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    queue_path = tmp_path / "q.json"
    project = _project(tmp_path)
    store = project / "memory"
    missing = _kept(project, 1, "missing-fact")
    unreadable = _kept(project, 2, "unreadable-fact")
    _queue_kept(queue_path, [missing, unreadable])
    _publish(unreadable, store)
    (store / "unreadable-fact.md").write_bytes(NOT_UTF8)
    capsys.readouterr()

    exit_code = docket.main(["unpublished", "--store", str(store), "--queue", str(queue_path)])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    _assert_the_store_diagnostic_names(captured.err, store, store / "unreadable-fact.md")


# A malformed queue entry is a malformed queue: QueueError, exit 2, no traceback.


def _queue_with_one_kept_entry_broken(tmp_path, break_entry):
    queue_path = tmp_path / "q.json"
    project = _project(tmp_path)
    entry = _kept(project, 1, "broken-fact")
    _queue_kept(queue_path, [entry])
    data = json.loads(queue_path.read_text())
    break_entry(data["entries"][0])
    queue_path.write_text(json.dumps(data))
    return project / "memory", queue_path, _id(entry)


def _drop_key(key):
    return lambda stored: stored.pop(key)


def _set_key(key, value):
    return lambda stored: stored.__setitem__(key, value)


_BROKEN_ENTRIES = {
    "transcript missing": _drop_key("transcript"),
    "transcript null": _set_key("transcript", None),
    "transcript not a string": _set_key("transcript", 7),
    "decision missing": _drop_key("decision"),
}


@pytest.mark.parametrize("break_entry", list(_BROKEN_ENTRIES.values()), ids=list(_BROKEN_ENTRIES))
def test_unpublished_raises_queue_error_naming_the_entry_when_a_queue_entry_is_malformed(
    tmp_path, break_entry
):
    store, queue_path, entry_id = _queue_with_one_kept_entry_broken(tmp_path, break_entry)

    with pytest.raises(docket.QueueError) as raised:
        docket.unpublished(store, path=queue_path)

    assert entry_id in str(raised.value)


def test_unpublished_raises_queue_error_when_a_queue_entry_has_no_id(tmp_path):
    store, queue_path, _ = _queue_with_one_kept_entry_broken(tmp_path, _drop_key("id"))

    with pytest.raises(docket.QueueError):
        docket.unpublished(store, path=queue_path)


@pytest.mark.parametrize("break_entry", list(_BROKEN_ENTRIES.values()), ids=list(_BROKEN_ENTRIES))
def test_main_unpublished_exits_two_with_a_diagnostic_when_a_queue_entry_is_malformed(
    tmp_path, monkeypatch, capsys, break_entry
):
    monkeypatch.chdir(tmp_path)
    store, queue_path, _ = _queue_with_one_kept_entry_broken(tmp_path, break_entry)
    capsys.readouterr()

    exit_code = docket.main(["unpublished", "--store", str(store), "--queue", str(queue_path)])

    assert exit_code == 2
    captured = capsys.readouterr()
    assert captured.err.strip() != ""
    assert "Traceback" not in captured.err
    assert captured.out == ""
