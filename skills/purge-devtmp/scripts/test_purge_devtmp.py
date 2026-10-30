"""Tests for purge_devtmp.py."""

import os
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


def test_nested_repo_fixture_moves_as_one_unit(tmp_path, monkeypatch):
    _repo, store = repo_store(tmp_path)
    fixture = store / "fixture"
    hook = fixture / ".git" / "hooks" / "pre-commit"
    hook.parent.mkdir(parents=True)
    hook.write_text("#!/bin/sh\nexit 0\n")
    source = fixture / "src.py"
    source.write_text("answer = 42\n")
    age(hook, 8)
    age(source, 8)
    original_mkdir = Path.mkdir

    def sandbox_mkdir(path, *positional, **keywords):
        if any(pair == (".git", "hooks") for pair in zip(path.parts, path.parts[1:])):
            raise PermissionError("sandbox refuses .git/hooks creation")
        return original_mkdir(path, *positional, **keywords)

    monkeypatch.setattr(Path, "mkdir", sandbox_mkdir)
    now = time.time()
    counts = gc.process_store("repo", store, args(apply=True), now)
    batch = time.strftime("%Y-%m-%d", time.localtime(now))
    trashed = store / gc.TRASH_DIR / batch / "fixture"
    assert counts["stale-temp"] == 1
    assert not fixture.exists()
    assert (trashed / ".git" / "hooks" / "pre-commit").read_text() == "#!/bin/sh\nexit 0\n"
    assert (trashed / "src.py").read_text() == "answer = 42\n"
    assert (store / gc.TRASH_DIR / "manifest.tsv").read_text().splitlines() == [
        f"{batch}\tstale-temp\tfixture\t{gc.TRASH_DIR}/{batch}/fixture"
    ]


def test_fresh_file_inside_a_nested_repo_keeps_the_fixture(tmp_path):
    _repo, store = repo_store(tmp_path)
    fixture = store / "fixture"
    head = fixture / ".git" / "HEAD"
    head.parent.mkdir(parents=True)
    head.write_text("ref: refs/heads/main\n")
    age(head, 8)
    source = fixture / "src.py"
    source.write_text("answer = 42\n")
    counts = gc.process_store("repo", store, args(), time.time())
    assert counts["fresh"] == 1
    assert counts["stale-temp"] == 0
    assert head.read_text() == "ref: refs/heads/main\n"
    assert source.read_text() == "answer = 42\n"
    assert not (store / gc.TRASH_DIR).exists()


@pytest.mark.parametrize("name,days,payload", [("fixture", 1, "alpha"), ("fixture-copy", 2, "beta")])
def test_apply_keeps_fresh_repository_and_empty_git_directories(tmp_path, name, days, payload):
    _repo, store = repo_store(tmp_path)
    fixture = store / name
    heads = fixture / ".git" / "refs" / "heads"
    pack = fixture / ".git" / "objects" / "pack"
    heads.mkdir(parents=True)
    pack.mkdir(parents=True)
    source = fixture / "src.py"
    source.write_text(payload)
    age(source, days)
    age(fixture, 30)
    counts = gc.process_store("repo", store, args(apply=True), time.time())
    assert counts["fresh"] == 1
    assert counts["stale-temp"] == 0
    assert source.read_text() == payload
    assert heads.is_dir()
    assert list(heads.iterdir()) == []
    assert pack.is_dir()
    assert list(pack.iterdir()) == []
    manifest = store / gc.TRASH_DIR / "manifest.tsv"
    assert not manifest.exists()


def test_walk_empty_repository_units_uses_each_unit_directory_timestamp(tmp_path):
    _repo, store = repo_store(tmp_path)
    assert list(gc.walk_store(store)) == []
    first = store / "fixture"
    second = store / "fixture-copy"
    (first / ".git" / "refs" / "heads").mkdir(parents=True)
    (second / ".git" / "objects" / "pack").mkdir(parents=True)
    age(first, 2)
    age(second, 11)
    assert dict(gc.walk_store(store)) == {
        Path("fixture"): first.stat().st_mtime,
        Path("fixture-copy"): second.stat().st_mtime,
    }


def test_apply_classifies_empty_repository_units_by_their_own_age(tmp_path):
    _repo, store = repo_store(tmp_path)
    now = time.time() + 20 * gc.DAY
    units = {"fixture": 1, "fixture-copy": 2, "old-fixture": 8, "old-fixture-copy": 12}
    for name, days in units.items():
        fixture = store / name
        (fixture / ".git" / "refs" / "heads").mkdir(parents=True)
        (fixture / ".git" / "objects" / "pack").mkdir(parents=True)
        os.utime(fixture, (now - days * gc.DAY, now - days * gc.DAY))
    counts = gc.process_store("repo", store, args(apply=True), now)
    batch = time.strftime("%Y-%m-%d", time.localtime(now))
    assert counts["fresh"] == 2
    assert counts["stale-temp"] == 2
    for name in ("fixture", "fixture-copy"):
        assert (store / name / ".git" / "refs" / "heads").is_dir()
        assert (store / name / ".git" / "objects" / "pack").is_dir()
        assert not (store / gc.TRASH_DIR / batch / name).exists()
    for name in ("old-fixture", "old-fixture-copy"):
        assert not (store / name).exists()
        trashed = store / gc.TRASH_DIR / batch / name
        assert (trashed / ".git" / "refs" / "heads").is_dir()
        assert (trashed / ".git" / "objects" / "pack").is_dir()
    assert set((store / gc.TRASH_DIR / "manifest.tsv").read_text().splitlines()) == {
        f"{batch}\tstale-temp\told-fixture\t{gc.TRASH_DIR}/{batch}/old-fixture",
        f"{batch}\tstale-temp\told-fixture-copy\t{gc.TRASH_DIR}/{batch}/old-fixture-copy",
    }


def test_live_prd_number_in_the_fixture_path_keeps_it(tmp_path):
    repo, store = repo_store(tmp_path)
    prds = repo / "docs" / "dev" / "project-management" / "prds" / "wip"
    prds.mkdir(parents=True)
    (prds / "00123-feature.md").write_text("# Feature")
    fixture = store / "00123-eval" / "template"
    head = fixture / ".git" / "HEAD"
    head.parent.mkdir(parents=True)
    head.write_text("ref: refs/heads/main\n")
    age(head, 60)
    source = fixture / "src.py"
    source.write_text("answer = 42\n")
    age(source, 60)
    counts = gc.process_store("repo", store, args(), time.time())
    assert counts["live-linked"] == 1
    assert counts["stale-temp"] == 0
    assert counts["fresh"] == 0
    assert head.read_text() == "ref: refs/heads/main\n"
    assert source.read_text() == "answer = 42\n"
    assert not (store / gc.TRASH_DIR).exists()


def test_zero_day_retention_never_deletes_what_this_run_just_trashed(tmp_path, capsys):
    _repo, store = repo_store(tmp_path)
    target = store / "old.txt"
    target.write_text("x")
    age(target, 8)
    now = time.time()
    gc.process_store("repo", store, args(apply=True, empty_trash_days=0), now)
    batch = time.strftime("%Y-%m-%d", time.localtime(now))
    out = capsys.readouterr().out
    assert not target.exists()
    assert (store / gc.TRASH_DIR / batch / "old.txt").is_file()
    assert "trash=1" in out
    assert "trash-batches-emptied=0" in out

    # Same zero-day run with an expired batch already in the trash: it must go
    # in the run that trashes old.txt, and the summary must count it.
    _repo, store = repo_store(tmp_path / "with-old-batch")
    target = store / "old.txt"
    target.write_text("x")
    age(target, 8)
    expired = store / gc.TRASH_DIR / time.strftime("%Y-%m-%d", time.localtime(now - 40 * gc.DAY))
    expired.mkdir(parents=True)
    (expired / "older.txt").write_text("x")
    gc.process_store("repo", store, args(apply=True, empty_trash_days=0), now)
    tokens = capsys.readouterr().out.split()
    assert not expired.exists()
    assert not target.exists()
    assert (store / gc.TRASH_DIR / batch / "old.txt").is_file()
    assert "trash=1" in tokens
    assert "trash-batches-emptied=1" in tokens


def noon_today() -> float:
    """Local noon keeps every batch half a day clear of the day boundary."""
    return time.mktime(time.localtime()[:3] + (12, 0, 0, 0, 0, -1))


def seed_trash(store, now: float, *ages: int) -> dict[int, str]:
    """Create one trash batch per age in days. Returns {days: batch name}."""
    names: dict[int, str] = {}
    for days in ages:
        names[days] = time.strftime("%Y-%m-%d", time.localtime(now - days * gc.DAY))
        batch_dir = store / gc.TRASH_DIR / names[days]
        batch_dir.mkdir(parents=True)
        (batch_dir / "old.txt").write_text("x")
    return names


def present(store, names: dict[int, str]) -> set[int]:
    """The ages, in days, whose seeded batch is still on disk."""
    return {
        days
        for days, name in names.items()
        if (store / gc.TRASH_DIR / name / "old.txt").is_file()
    }


def test_empty_trash_ages_out_old_batches_only(tmp_path):
    _repo, store = repo_store(tmp_path)
    now = noon_today()
    names = seed_trash(store, now, 40, 2, 0)
    assert gc.empty_old_trash(store, now, 30, keep=names[0]) == 1
    assert not (store / gc.TRASH_DIR / names[40]).exists()
    assert (store / gc.TRASH_DIR / names[2] / "old.txt").is_file()
    assert (store / gc.TRASH_DIR / names[0] / "old.txt").is_file()


def test_keep_spares_an_expired_batch(tmp_path):
    """`keep` is matched by name, so it survives however far past the window."""
    _repo, store = repo_store(tmp_path)
    now = noon_today()
    names = seed_trash(store, now, 3, 2)
    # A one-day window expires both batches; only the kept one survives.
    assert gc.empty_old_trash(store, now, 1, keep=names[2]) == 1
    assert present(store, names) == {2}
    # Zero-day retention: the kept batch survives with no window at all.
    assert gc.empty_old_trash(store, now, 0, keep=names[2]) == 0
    assert present(store, names) == {2}


def test_empty_trash_window_boundaries(tmp_path):
    _repo, store = repo_store(tmp_path)
    now = noon_today()
    names = seed_trash(store, now, 45, 35, 31, 29, 3, 2, 0)
    assert gc.empty_old_trash(store, now, 50, keep=names[0]) == 0
    assert present(store, names) == {45, 35, 31, 29, 3, 2, 0}
    assert gc.empty_old_trash(store, now, 30, keep=names[0]) == 3
    assert present(store, names) == {29, 3, 2, 0}
    # keep spares a batch past the window while a non-kept neighbour goes.
    assert gc.empty_old_trash(store, now, 1, keep=names[2]) == 2
    assert present(store, names) == {2, 0}
    assert gc.empty_old_trash(store, now, 1, keep=names[0]) == 1
    assert present(store, names) == {0}
    assert gc.empty_old_trash(store, now, 0, keep=names[0]) == 0
    assert present(store, names) == {0}


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


def linked_repo_store(tmp_path: Path, name: str = "repo") -> tuple[Path, Path]:
    """A repo whose docs/dev/tmp symlinks to a scratch store outside it."""
    repo = tmp_path / name
    real_store = tmp_path / "linked-store" / name / "docs" / "dev" / "tmp"
    real_store.mkdir(parents=True)
    (repo / "docs" / "dev").mkdir(parents=True)
    (repo / "docs" / "dev" / "tmp").symlink_to(real_store, target_is_directory=True)
    return repo, real_store


def add_prd(repo: Path, bucket: str, number: str) -> None:
    prds = repo / "docs" / "dev" / "project-management" / "prds" / bucket
    prds.mkdir(parents=True)
    (prds / f"{number}-feature.md").write_text("# Feature")


@pytest.mark.parametrize("bucket,number", [("backlog", "00111"), ("wip", "00112"), ("hold", "00113")])
def test_linked_store_dry_run_reports_live_linked_per_bucket(tmp_path, capsys, bucket, number):
    repo, store = linked_repo_store(tmp_path, name=f"repo-{bucket}")
    add_prd(repo, bucket, number)
    note = store / f"{number}-review-prompt.md"
    note.write_text("x")
    age(note, 60)
    assert gc.main(["--repo", str(repo)]) == 0
    out = capsys.readouterr().out
    assert "live-linked=1" in out
    assert "stale-temp=0" in out
    assert note.is_file()


def test_linked_store_distinguishes_live_numbers_from_near_miss_and_fresh(tmp_path, capsys):
    repo, store = linked_repo_store(tmp_path)
    add_prd(repo, "backlog", "00123")
    add_prd(repo, "wip", "00456")
    live_a = store / "00123-prompt.md"
    live_a.write_text("x")
    age(live_a, 60)
    live_b = store / "00456-notes.md"
    live_b.write_text("x")
    age(live_b, 60)
    near_miss = store / "000123-unrelated.md"
    near_miss.write_text("x")
    age(near_miss, 60)
    fresh = store / "scratch.md"
    fresh.write_text("x")
    assert gc.main(["--repo", str(repo)]) == 0
    out = capsys.readouterr().out
    assert "live-linked=2" in out
    assert "stale-temp=1" in out
    assert "fresh=1" in out


def test_linked_store_with_no_prds_treats_everything_by_age_only(tmp_path, capsys):
    repo, store = linked_repo_store(tmp_path)
    old = store / "old.md"
    old.write_text("x")
    age(old, 60)
    assert gc.main(["--repo", str(repo)]) == 0
    out = capsys.readouterr().out
    assert "live-linked=0" in out
    assert "stale-temp=1" in out


def test_linked_store_dry_run_works_via_explicit_store_path_input(tmp_path, capsys):
    repo, store = linked_repo_store(tmp_path)
    add_prd(repo, "hold", "00789")
    note = store / "00789-prompt.md"
    note.write_text("x")
    age(note, 60)
    assert gc.main(["--repo", str(repo / "docs" / "dev" / "tmp")]) == 0
    out = capsys.readouterr().out
    assert "live-linked=1" in out
    assert "stale-temp=0" in out


def test_all_discovery_reports_live_linked_for_symlinked_store(tmp_path, monkeypatch, capsys):
    home = tmp_path / "scratch-home"
    repo = home / "git" / "src" / "github.com" / "an-org" / "a-repo"
    real_store = tmp_path / "outside" / "a-repo" / "docs" / "dev" / "tmp"
    real_store.mkdir(parents=True)
    (repo / "docs" / "dev").mkdir(parents=True)
    (repo / "docs" / "dev" / "tmp").symlink_to(real_store, target_is_directory=True)
    add_prd(repo, "backlog", "00321")
    note = real_store / "00321-prompt.md"
    note.write_text("x")
    age(note, 60)
    monkeypatch.setattr(gc.Path, "home", classmethod(lambda cls: home))
    assert gc.main(["--all"]) == 0
    out = capsys.readouterr().out
    assert "an-org/a-repo" in out
    assert "live-linked=1" in out
    assert "stale-temp=0" in out


def test_relative_repo_argument_from_inside_docs_dev_does_not_crash(tmp_path, monkeypatch, capsys):
    repo, store = repo_store(tmp_path)
    note = store / "old.md"
    note.write_text("x")
    age(note, 60)
    monkeypatch.chdir(repo / "docs" / "dev")
    assert gc.main(["--repo", "tmp"]) == 0
    out = capsys.readouterr().out
    assert "live-linked=0" in out
    assert "stale-temp=1" in out


def test_apply_keeps_live_linked_note_but_trashes_ordinary_stale_file(tmp_path, capsys):
    repo, store = linked_repo_store(tmp_path)
    add_prd(repo, "wip", "00999")
    note = store / "00999-prompt.md"
    note.write_text("linked")
    age(note, 60)
    stale = store / "unrelated-old.txt"
    stale.write_text("stale")
    age(stale, 60)
    assert gc.main(["--repo", str(repo), "--apply"]) == 0
    out = capsys.readouterr().out
    assert "live-linked=1" in out
    assert "stale-temp=1" in out
    assert note.is_file()
    assert note.read_text() == "linked"
    assert not stale.exists()
    batch = time.strftime("%Y-%m-%d", time.localtime())
    assert (store / gc.TRASH_DIR / batch / "unrelated-old.txt").is_file()
