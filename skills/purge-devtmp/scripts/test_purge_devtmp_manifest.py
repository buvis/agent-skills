"""Tests for unsafe-path refusal and emptied-batch manifest cleanup in purge_devtmp.py."""

import os
import shutil
import time
from pathlib import Path

import purge_devtmp as gc
import pytest


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


def noon_today() -> float:
    return time.mktime(time.localtime()[:3] + (12, 0, 0, 0, 0, -1))


def seed_batch(store: Path, batch: str, name: str) -> Path:
    batch_dir = store / gc.TRASH_DIR / batch
    batch_dir.mkdir(parents=True, exist_ok=True)
    target = batch_dir / name
    target.write_text("x")
    return target


def write_manifest(store: Path, lines: list[str]) -> Path:
    manifest = store / gc.TRASH_DIR / "manifest.tsv"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("\n".join(lines) + "\n" if lines else "")
    return manifest


# --- path_has_unsafe_characters -------------------------------------------------


def test_path_has_unsafe_characters_flags_a_tab():
    reason = gc.path_has_unsafe_characters(Path("notes\tbad.txt"))
    assert reason is not None
    assert "tab" in reason


def test_path_has_unsafe_characters_flags_a_newline():
    reason = gc.path_has_unsafe_characters(Path("notes\nbad.txt"))
    assert reason is not None
    assert "newline" in reason


def test_path_has_unsafe_characters_flags_a_nested_component():
    reason = gc.path_has_unsafe_characters(Path("nested") / "ba\td" / "file.txt")
    assert reason is not None


def test_path_has_unsafe_characters_accepts_an_ordinary_name():
    assert gc.path_has_unsafe_characters(Path("notes.txt")) is None


def test_path_has_unsafe_characters_does_not_flag_literal_backslash_t():
    # Two literal characters "\" and "t", not an actual tab byte.
    assert gc.path_has_unsafe_characters(Path("notes\\tbad.txt")) is None


# --- process_store refusal -------------------------------------------------------


def test_process_store_refuses_tab_path_and_still_trashes_ordinary_file(tmp_path, capsys):
    _repo, store = repo_store(tmp_path)
    ordinary = store / "old.txt"
    ordinary.write_text("x")
    age(ordinary, 8)
    unsafe = store / "bad\ttab.txt"
    unsafe.write_text("y")
    age(unsafe, 8)
    now = time.time()
    counts = gc.process_store("repo", store, args(apply=True), now)
    batch = time.strftime("%Y-%m-%d", time.localtime(now))

    assert not ordinary.exists()
    assert (store / gc.TRASH_DIR / batch / "old.txt").is_file()
    assert unsafe.exists()
    assert counts["stale-temp"] == 1
    assert counts["refused-unsafe-path"] == 1
    manifest_text = (store / gc.TRASH_DIR / "manifest.tsv").read_text()
    assert "old.txt" in manifest_text
    assert "bad\ttab.txt" not in manifest_text

    out = capsys.readouterr().out
    assert "refused-unsafe-path=1" in out
    assert "stale-temp=1" in out


def test_process_store_verbose_reports_the_refusal_reason(tmp_path, capsys):
    _repo, store = repo_store(tmp_path)
    unsafe = store / "bad\ttab.txt"
    unsafe.write_text("y")
    age(unsafe, 8)
    gc.process_store("repo", store, args(apply=True, verbose=True), time.time())
    out = capsys.readouterr().out
    assert "refused-unsafe-path:" in out


def test_dry_run_never_touches_filesystem_for_unsafe_path(tmp_path):
    _repo, store = repo_store(tmp_path)
    unsafe = store / "bad\ttab.txt"
    unsafe.write_text("y")
    age(unsafe, 8)
    gc.process_store("repo", store, args(apply=False), time.time())
    assert unsafe.is_file()
    assert not (store / gc.TRASH_DIR).exists()


# --- emptied-batch manifest cleanup ----------------------------------------------


def test_empty_old_trash_drops_only_rows_for_the_emptied_batch(tmp_path):
    _repo, store = repo_store(tmp_path)
    now = noon_today()
    old_batch = time.strftime("%Y-%m-%d", time.localtime(now - 40 * gc.DAY))
    kept_batch = time.strftime("%Y-%m-%d", time.localtime(now))
    seed_batch(store, old_batch, "junk.txt")
    seed_batch(store, kept_batch, "keep.txt")
    write_manifest(
        store,
        [
            f"{old_batch}\tstale-temp\tjunk.txt\t{gc.TRASH_DIR}/{old_batch}/junk.txt",
            f"{kept_batch}\tstale-temp\tkeep.txt\t{gc.TRASH_DIR}/{kept_batch}/keep.txt",
            f"{kept_batch}\tbrush-junk\tother.txt\t{gc.TRASH_DIR}/{kept_batch}/other.txt",
        ],
    )
    removed = gc.empty_old_trash(store, now, 30, keep=kept_batch)
    assert removed == 1
    assert not (store / gc.TRASH_DIR / old_batch).exists()
    assert (store / gc.TRASH_DIR / kept_batch).exists()
    manifest_lines = (store / gc.TRASH_DIR / "manifest.tsv").read_text().splitlines()
    assert not any(line.startswith(old_batch) for line in manifest_lines)
    assert any(f"{kept_batch}\tstale-temp\tkeep.txt" in line for line in manifest_lines)
    assert any(f"{kept_batch}\tbrush-junk\tother.txt" in line for line in manifest_lines)


def test_keep_spares_an_expired_batch_and_its_manifest_rows(tmp_path):
    _repo, store = repo_store(tmp_path)
    now = noon_today()
    expired_but_kept = time.strftime("%Y-%m-%d", time.localtime(now - 3 * gc.DAY))
    seed_batch(store, expired_but_kept, "mine.txt")
    write_manifest(
        store,
        [f"{expired_but_kept}\tstale-temp\tmine.txt\t{gc.TRASH_DIR}/{expired_but_kept}/mine.txt"],
    )
    removed = gc.empty_old_trash(store, now, 1, keep=expired_but_kept)
    assert removed == 0
    assert (store / gc.TRASH_DIR / expired_but_kept).exists()
    manifest_lines = (store / gc.TRASH_DIR / "manifest.tsv").read_text().splitlines()
    assert any(line.startswith(expired_but_kept) for line in manifest_lines)


def test_failed_batch_deletion_keeps_its_directory_and_manifest_rows(tmp_path, monkeypatch):
    _repo, store = repo_store(tmp_path)
    now = noon_today()
    locked = time.strftime("%Y-%m-%d", time.localtime(now - 40 * gc.DAY))
    removable = time.strftime("%Y-%m-%d", time.localtime(now - 45 * gc.DAY))
    seed_batch(store, locked, "stuck.txt")
    seed_batch(store, removable, "gone.txt")
    write_manifest(
        store,
        [
            f"{locked}\tstale-temp\tstuck.txt\t{gc.TRASH_DIR}/{locked}/stuck.txt",
            f"{removable}\tstale-temp\tgone.txt\t{gc.TRASH_DIR}/{removable}/gone.txt",
        ],
    )
    original_rmtree = shutil.rmtree

    def flaky_rmtree(path, *a, **k):
        if Path(path).name == locked:
            raise OSError("permission denied")
        return original_rmtree(path, *a, **k)

    monkeypatch.setattr(shutil, "rmtree", flaky_rmtree)
    removed = gc.empty_old_trash(store, now, 30, keep=None)
    assert removed == 1
    assert (store / gc.TRASH_DIR / locked).exists()
    assert not (store / gc.TRASH_DIR / removable).exists()
    manifest_lines = (store / gc.TRASH_DIR / "manifest.tsv").read_text().splitlines()
    assert any(line.startswith(locked) for line in manifest_lines)
    assert not any(line.startswith(removable) for line in manifest_lines)


def test_manifest_update_failure_leaves_manifest_unchanged_and_does_not_raise(tmp_path, monkeypatch):
    _repo, store = repo_store(tmp_path)
    now = noon_today()
    old_batch = time.strftime("%Y-%m-%d", time.localtime(now - 40 * gc.DAY))
    seed_batch(store, old_batch, "junk.txt")
    original_line = f"{old_batch}\tstale-temp\tjunk.txt\t{gc.TRASH_DIR}/{old_batch}/junk.txt"
    write_manifest(store, [original_line])
    original_text = (store / gc.TRASH_DIR / "manifest.tsv").read_text()

    def failing_replace(*a, **k):
        raise OSError("disk full")

    monkeypatch.setattr(os, "replace", failing_replace)
    removed = gc.empty_old_trash(store, now, 30, keep=None)
    assert removed == 1
    assert not (store / gc.TRASH_DIR / old_batch).exists()
    assert (store / gc.TRASH_DIR / "manifest.tsv").read_text() == original_text


def test_path_has_unsafe_characters_flags_a_carriage_return():
    reason = gc.path_has_unsafe_characters(Path("notes\rbad.txt"))
    assert reason is not None


def test_manifest_rewrite_preserves_an_unrelated_row_containing_a_carriage_return(
    tmp_path,
):
    _repo, store = repo_store(tmp_path)
    now = noon_today()
    old_batch = time.strftime("%Y-%m-%d", time.localtime(now - 40 * gc.DAY))
    kept_batch = time.strftime("%Y-%m-%d", time.localtime(now))
    seed_batch(store, old_batch, "junk.txt")
    seed_batch(store, kept_batch, "keep.txt")
    cr_line = f"{kept_batch}\tstale-temp\tweird\rname.txt\t{gc.TRASH_DIR}/{kept_batch}/weird\rname.txt"
    old_line = f"{old_batch}\tstale-temp\tjunk.txt\t{gc.TRASH_DIR}/{old_batch}/junk.txt"
    write_manifest(store, [cr_line, old_line])
    removed = gc.empty_old_trash(store, now, 30, keep=kept_batch)
    assert removed == 1
    with (store / gc.TRASH_DIR / "manifest.tsv").open(
        "r", encoding="utf-8", newline=""
    ) as handle:
        manifest_lines = handle.read().split("\n")
    assert cr_line in manifest_lines
    assert not any(line.startswith(old_batch) for line in manifest_lines)


def test_malformed_row_sharing_a_removed_batch_name_is_preserved(tmp_path):
    _repo, store = repo_store(tmp_path)
    now = noon_today()
    old_batch = time.strftime("%Y-%m-%d", time.localtime(now - 40 * gc.DAY))
    seed_batch(store, old_batch, "junk.txt")
    malformed_line = f"{old_batch}\tonly-two-fields"
    well_formed_line = f"{old_batch}\tstale-temp\tjunk.txt\t{gc.TRASH_DIR}/{old_batch}/junk.txt"
    write_manifest(store, [malformed_line, well_formed_line])
    removed = gc.empty_old_trash(store, now, 30, keep=None)
    assert removed == 1
    manifest_lines = (store / gc.TRASH_DIR / "manifest.tsv").read_text().splitlines()
    assert malformed_line in manifest_lines
    assert well_formed_line not in manifest_lines


def test_well_formed_row_with_an_extra_tab_in_its_path_field_is_still_removed(tmp_path):
    _repo, store = repo_store(tmp_path)
    now = noon_today()
    old_batch = time.strftime("%Y-%m-%d", time.localtime(now - 40 * gc.DAY))
    seed_batch(store, old_batch, "junk.txt")
    extra_field_line = f"{old_batch}\tbrush-junk\tweird\tname.txt\t{gc.TRASH_DIR}/{old_batch}/weird\tname.txt"
    truly_malformed_line = f"{old_batch}\tonly-two-fields"
    write_manifest(store, [extra_field_line, truly_malformed_line])
    gc.empty_old_trash(store, now, 30, keep=None)
    manifest_lines = (store / gc.TRASH_DIR / "manifest.tsv").read_text().splitlines()
    assert extra_field_line not in manifest_lines
    assert truly_malformed_line in manifest_lines


def test_historical_malformed_row_is_preserved_byte_for_byte(tmp_path):
    _repo, store = repo_store(tmp_path)
    now = noon_today()
    old_batch = time.strftime("%Y-%m-%d", time.localtime(now - 40 * gc.DAY))
    seed_batch(store, old_batch, "junk.txt")
    malformed_line = "2020-01-01\tsome-rel-path-with-no-tabs"
    well_formed_line = f"{old_batch}\tstale-temp\tjunk.txt\t{gc.TRASH_DIR}/{old_batch}/junk.txt"
    write_manifest(store, [malformed_line, well_formed_line])
    gc.empty_old_trash(store, now, 30, keep=None)
    manifest_lines = (store / gc.TRASH_DIR / "manifest.tsv").read_text().splitlines()
    assert malformed_line in manifest_lines
    assert well_formed_line not in manifest_lines
