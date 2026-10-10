"""Tests for docket.py: unpublished(), the kept entries a store does not yet
hold, and the `unpublished --store <path> [--queue <path>]` subcommand."""

import docket

import pytest

import write

from docket_test_helpers import make_proposal as _proposal
from write_test_helpers import _entry, _file_text


# Every store here is a real directory and every "published" state is made by
# the real write.write_memory + write.append_pointer, so "published" means
# exactly what write.published() confirms. An entry's own store is the
# `memory` directory beside its transcript, so each project below is a
# directory holding a transcript path and a `memory/` store.


def _project(tmp_path, name="proj"):
    project = tmp_path / name
    (project / "memory").mkdir(parents=True)
    return project


def _kept(project, line_no, name, kind="new", file_text=None, existing_text=None):
    proposal = _proposal(
        transcript=str(project / "session.jsonl"),
        line_no=line_no,
        name=name,
        file_text=file_text if file_text is not None else _file_text(name=name),
    )
    return dict(proposal, kind=kind, existing_text=existing_text)


def _id(proposal):
    return docket.slice_key(proposal["transcript"], proposal["line_no"])


def _queue_kept(queue_path, proposals):
    docket.save(proposals, path=queue_path)
    for proposal in proposals:
        docket.decide(_id(proposal), "kept", path=queue_path)


def _publish(entry, store):
    write.write_memory(entry, store)
    write.append_pointer(store, entry)


V1 = _file_text(name="widget-fact", description="first version of the fact")
V2 = _file_text(name="widget-fact", description="second version of the fact")
V3 = _file_text(name="widget-fact", description="third version of the fact")


def _store_holding_v1(project):
    store = project / "memory"
    _publish(_entry(name="widget-fact", file_text=V1), store)
    return store


# unpublished(): the function.


def test_unpublished_returns_only_kept_entries_missing_from_the_store_in_queue_order(tmp_path):
    queue_path = tmp_path / "queue.json"
    project = _project(tmp_path)
    store = project / "memory"
    first_missing = _kept(project, 9, "first-missing")
    undecided = _kept(project, 8, "undecided-missing")
    published = _kept(project, 7, "published-fact")
    dropped = _kept(project, 6, "dropped-missing")
    last_missing = _kept(project, 2, "last-missing")
    docket.save([first_missing, undecided, published, dropped, last_missing], path=queue_path)
    for proposal in (first_missing, published, last_missing):
        docket.decide(_id(proposal), "kept", path=queue_path)
    docket.decide(_id(dropped), "dropped", path=queue_path)
    _publish(published, store)

    assert docket.unpublished(store, path=queue_path) == [_id(first_missing), _id(last_missing)]


def test_unpublished_lists_an_update_whose_target_still_holds_the_old_text(tmp_path):
    queue_path = tmp_path / "queue.json"
    project = _project(tmp_path)
    store = _store_holding_v1(project)
    update = _kept(project, 1, "widget-fact", kind="update widget-fact", file_text=V2, existing_text=V1)
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
    update = _kept(project, 1, "widget-fact", kind="update widget-fact", file_text=V2, existing_text=V1)
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
    queue_path = tmp_path / "queue.json"
    project = _project(tmp_path)
    store = _store_holding_v1(project)
    earlier = _kept(project, 1, "widget-fact", kind="update widget-fact", file_text=V2, existing_text=V1)
    later = _kept(project, 2, "widget-fact", kind="update widget-fact", file_text=V3, existing_text=V2)
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
    updated = _kept(project, 2, "widget-fact", kind="update widget-fact", file_text=V2, existing_text=V1)
    _queue_kept(queue_path, [created, updated])
    _publish(created, store)
    _publish(updated, store)

    assert write.published(created, store) is False
    assert docket.unpublished(store, path=queue_path) == []


def test_unpublished_ignores_kept_entries_of_another_store_even_for_the_same_target(tmp_path):
    queue_path = tmp_path / "queue.json"
    own_project = _project(tmp_path, "own")
    other_project = _project(tmp_path, "other")
    own = _kept(own_project, 1, "widget-fact")
    other_same_target = _kept(other_project, 2, "widget-fact")
    other_elsewhere = _kept(other_project, 3, "other-fact")
    _queue_kept(queue_path, [own, other_same_target, other_elsewhere])
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


def test_unpublished_raises_a_write_error_for_an_unreadable_index_even_when_every_target_is_missing(
    tmp_path,
):
    queue_path = tmp_path / "queue.json"
    project = _project(tmp_path)
    store = project / "memory"
    (store / "MEMORY.md").write_bytes(b"\xff\xfe not utf-8\n")
    _queue_kept(queue_path, [_kept(project, 1, "first-missing"), _kept(project, 2, "second-missing")])

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


def test_unpublished_lists_kept_entries_whose_file_is_missing_and_exits_one(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    project = _project(tmp_path)
    store = project / "memory"
    first_missing = _kept(project, 1, "first-missing")
    published = _kept(project, 2, "published-fact")
    second_missing = _kept(project, 3, "second-missing")
    _queue_kept(None, [first_missing, published, second_missing])
    _publish(published, store)
    capsys.readouterr()

    exit_code = docket.main(["unpublished", "--store", str(store)])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == f"{_id(first_missing)}\n{_id(second_missing)}\n"


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


def test_main_unpublished_exits_one_with_no_stdout_when_the_index_is_unreadable_and_every_target_is_missing(
    tmp_path, monkeypatch, capsys
):
    monkeypatch.chdir(tmp_path)
    queue_path = tmp_path / "q.json"
    project = _project(tmp_path)
    store = project / "memory"
    (store / "MEMORY.md").write_bytes(b"\xff\xfe not utf-8\n")
    _queue_kept(queue_path, [_kept(project, 1, "first-missing"), _kept(project, 2, "second-missing")])
    capsys.readouterr()

    exit_code = docket.main(["unpublished", "--store", str(store), "--queue", str(queue_path)])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert f"cannot check the store {store}: " in captured.err
    assert "Traceback" not in captured.err


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
    (store / "unreadable-fact.md").write_bytes(b"\xff\xfe not utf-8\n")
    capsys.readouterr()

    exit_code = docket.main(["unpublished", "--store", str(store), "--queue", str(queue_path)])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert f"cannot check the store {store}: " in captured.err
    assert "Traceback" not in captured.err
