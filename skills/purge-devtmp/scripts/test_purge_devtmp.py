"""Tests for purge_devtmp.py."""

import os
import time
from pathlib import Path

import purge_devtmp as gc


def args(**overrides):
    values = {
        "apply": False,
        "min_age_days": 3,
        "age_days": 7,
        "empty_trash_days": 30,
        "verbose": False,
    }
    values.update(overrides)
    return type("Args", (), values)()


def repo_store(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    store = repo / "docs" / "dev" / "tmp"
    store.mkdir(parents=True)
    return repo, store


def age(path: Path, days: int) -> None:
    when = time.time() - days * gc.DAY
    os.utime(path, (when, when))


def test_resolve_store_accepts_repo_and_store(tmp_path):
    repo, store = repo_store(tmp_path)
    assert gc.resolve_store(repo) == store
    assert gc.resolve_store(store) == store


def test_resolve_store_refuses_other_tmp_directory(tmp_path):
    other = tmp_path / "tmp"
    other.mkdir()
    try:
        gc.resolve_store(other)
    except ValueError as error:
        assert "docs/dev/tmp" in str(error)
    else:
        raise AssertionError("broad tmp directory accepted")


def test_old_unlinked_file_is_candidate(tmp_path):
    _repo, store = repo_store(tmp_path)
    target = store / "notes.txt"
    target.write_text("x")
    age(target, 8)
    assert gc.classify(target.relative_to(store), target.stat().st_mtime, set(), time.time(), args()) == "stale-temp"


def test_fresh_file_is_kept(tmp_path):
    _repo, store = repo_store(tmp_path)
    target = store / "notes.txt"
    target.write_text("x")
    assert gc.classify(target.relative_to(store), target.stat().st_mtime, set(), time.time(), args()) == "fresh"


def test_live_prd_link_is_kept_even_when_old(tmp_path):
    repo, store = repo_store(tmp_path)
    prds = repo / "docs" / "dev" / "project-management" / "prds" / "wip"
    prds.mkdir(parents=True)
    (prds / "00123-feature.md").write_text("# Feature")
    target = store / "00123-review-prompt.md"
    target.write_text("x")
    age(target, 60)
    live = gc.live_prd_numbers(store)
    assert live == {"00123"}
    assert gc.classify(target.relative_to(store), target.stat().st_mtime, live, time.time(), args()) == "live-linked"


def test_apply_moves_to_trash_and_records_manifest(tmp_path):
    _repo, store = repo_store(tmp_path)
    target = store / "nested" / "old.txt"
    target.parent.mkdir()
    target.write_text("x")
    age(target, 8)
    now = time.time()
    gc.process_store("repo", store, args(apply=True), now)
    batch = time.strftime("%Y-%m-%d", time.localtime(now))
    assert not target.exists()
    assert (store / gc.TRASH_DIR / batch / "nested" / "old.txt").is_file()
    assert "stale-temp\tnested/old.txt" in (store / gc.TRASH_DIR / "manifest.tsv").read_text()


def test_dry_run_does_not_move(tmp_path):
    _repo, store = repo_store(tmp_path)
    target = store / "old.txt"
    target.write_text("x")
    age(target, 8)
    gc.process_store("repo", store, args(), time.time())
    assert target.is_file()
    assert not (store / gc.TRASH_DIR).exists()


def test_main_refuses_unscoped_directory(tmp_path, capsys):
    assert gc.main(["--repo", str(tmp_path)]) == 2
    assert "not a repo with docs/dev/tmp" in capsys.readouterr().err
