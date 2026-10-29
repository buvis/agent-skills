#!/usr/bin/env python3
"""Regression net for brush helper scripts: classification, vetoes, moves."""

from __future__ import annotations

import datetime
import json
import os
import posixpath
import subprocess
import time
from pathlib import Path

import pytest

import collect_facts as cf
import trash_untracked as tu

OLD = time.time() - 10 * 86400


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(repo), *args], check=True,
                   capture_output=True, text=True)


@pytest.fixture()
def repo(tmp_path: Path) -> Path:
    r = tmp_path / "r"
    r.mkdir()
    _git(r, "init", "-q", "-b", "master")
    _git(r, "config", "user.email", "t@t")
    _git(r, "config", "user.name", "t")
    (r / "tracked.log").write_text("x")
    _git(r, "add", "tracked.log")
    _git(r, "commit", "-qm", "init")
    return r


@pytest.mark.parametrize("rel,expected", [
    ("docs/dev/tmp/x.bin", "development"),
    (".env.local", "secret"),
    ("a/__pycache__/m.pyc", "junk-dir"),
    (".DS_Store", "os-junk"),
    ("docs/guide.pdf", "doc"),
    ("README", "doc"),
    ("node_modules/x.js", "heavy"),
    ("foo.log", "junk"),
    ("scratch_bench.py", "scratch"),
    ("src/module.py", "other"),
])
def test_classify_path_rules(rel: str, expected: str) -> None:
    assert cf.classify_path(rel) == expected


def test_default_branch_prefers_master(repo: Path) -> None:
    assert cf.detect_default_branch(repo) == "master"


def test_ctx_flags_in_progress_merge(repo: Path) -> None:
    (repo / ".git/MERGE_HEAD").write_text("x")
    assert cf.gather_repo_ctx(repo)["in_progress_op"] == ["MERGE_HEAD"]


def test_ctx_refuses_non_repo(tmp_path: Path) -> None:
    d = tmp_path / "nogit"
    d.mkdir()
    assert cf.gather_repo_ctx(d)["refusals"]


def test_ctx_refuses_home_work_tree(repo: Path,
                                    monkeypatch: pytest.MonkeyPatch) -> None:
    """A dotfiles bare repo checks out $HOME; brush never runs there."""
    top = Path(cf.git_out(repo, "rev-parse", "--show-toplevel").strip())
    monkeypatch.setattr(cf.Path, "home", classmethod(lambda cls: top))
    assert "home work-tree" in cf.gather_repo_ctx(repo)["refusals"][0]


def test_missing_pgrep_reports_no_live_batch(
        repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A host without pgrep loses the batch probe, not the whole preflight."""
    real = cf.subprocess.run

    def no_pgrep(cmd, *a, **kw):
        if cmd[0] == "pgrep":
            raise FileNotFoundError(cmd[0])
        return real(cmd, *a, **kw)

    monkeypatch.setattr(cf.subprocess, "run", no_pgrep)
    assert cf.gather_repo_ctx(repo)["autopilot_live"] is False


def test_branch_drift_counts(repo: Path) -> None:
    _git(repo, "branch", "feat")
    (repo / "f2").write_text("y")
    _git(repo, "add", "f2")
    _git(repo, "commit", "-qm", "second")
    feat = [b for b in cf.gather_branches(repo, "master", fast=True)
            if b["name"] == "feat"][0]
    assert (feat["behind"], feat["ahead"]) == (1, 0)
    assert feat["merged"] is True


def _veto(repo: Path, rel: str) -> str | None:
    return tu.veto_reason(rel, repo / rel, tu.load_tracked(repo), 3)


def test_veto_tracked_file(repo: Path) -> None:
    assert "tracked" in _veto(repo, "tracked.log")


def test_veto_doc_suffix(repo: Path) -> None:
    p = repo / "notes.md"
    p.write_text("d")
    os.utime(p, (OLD, OLD))
    assert "documentation" in _veto(repo, "notes.md")


def test_veto_development_paths_protected(repo: Path) -> None:
    p = repo / "docs/dev/project-management/keep.bin"
    p.parent.mkdir(parents=True)
    p.write_text("k")
    os.utime(p, (OLD, OLD))
    assert "protected" in _veto(repo, "docs/dev/project-management/keep.bin")


def test_veto_fresh_file(repo: Path) -> None:
    (repo / "fresh.tmp").write_text("f")
    assert "fresh" in _veto(repo, "fresh.tmp")


def test_old_junk_passes_veto(repo: Path) -> None:
    p = repo / "old_junk.log"
    p.write_text("j")
    os.utime(p, (OLD, OLD))
    assert _veto(repo, "old_junk.log") is None


def test_relocate_writes_manifest_row(repo: Path) -> None:
    (repo / "old_junk.log").write_text("j")
    date = "2026-07-13"
    trash_rel = tu.relocate(repo, "old_junk.log", date)
    tu.note_manifest(repo, date, "brush-junk", "old_junk.log", trash_rel)
    assert (repo / trash_rel).is_file()
    row = (repo / "docs/dev/tmp/.trash/manifest.tsv").read_text().strip().split("\t")
    assert row == [date, "brush-junk", "old_junk.log", trash_rel]


def _tree(root: Path) -> list[tuple[str, str]]:
    return sorted((p.relative_to(root).as_posix(),
                   p.read_text() if p.is_file() else "<dir>")
                  for p in root.rglob("*"))


def test_trash_dest_joins_rel_under_the_dated_trash_dir(tmp_path: Path) -> None:
    (tmp_path / "old_junk.log").write_text("j")

    dest = tu.trash_dest(tmp_path, "old_junk.log", "2026-07-13")

    assert dest == tmp_path / "docs/dev/tmp/.trash/2026-07-13/old_junk.log"


def test_trash_dest_keeps_a_nested_rel_nested(tmp_path: Path) -> None:
    dest = tu.trash_dest(tmp_path, "charts/sub/old_junk.log", "2026-07-13")

    assert dest == (tmp_path
                    / "docs/dev/tmp/.trash/2026-07-13/charts/sub/old_junk.log")


def test_trash_dest_leaves_the_filesystem_untouched(tmp_path: Path) -> None:
    (tmp_path / "old_junk.log").write_text("j")
    before = _tree(tmp_path)

    tu.trash_dest(tmp_path, "old_junk.log", "2026-07-13")

    assert _tree(tmp_path) == before
    assert not (tmp_path / "docs").exists()


def test_trash_dest_appends_a_dup_timestamp_when_the_dest_is_taken(
        tmp_path: Path) -> None:
    (tmp_path / "old_junk.log").write_text("new")
    taken = tmp_path / "docs/dev/tmp/.trash/2026-07-13/old_junk.log"
    taken.parent.mkdir(parents=True)
    taken.write_text("earlier")
    before = _tree(tmp_path)
    t0 = int(time.time())

    dest = tu.trash_dest(tmp_path, "old_junk.log", "2026-07-13")

    t1 = int(time.time())
    assert dest.parent == taken.parent
    assert dest.name.startswith("old_junk.log.dup")
    ts = dest.name[len("old_junk.log.dup"):]
    assert ts.isdigit() and t0 <= int(ts) <= t1
    assert _tree(tmp_path) == before


def test_trash_dest_no_suffix_when_dated_dir_exists_but_name_is_free(
        tmp_path: Path) -> None:
    dated = tmp_path / "docs/dev/tmp/.trash/2026-07-13"
    dated.mkdir(parents=True)
    (dated / "other.log").write_text("unrelated")

    dest = tu.trash_dest(tmp_path, "old_junk.log", "2026-07-13")

    assert dest == dated / "old_junk.log"


def test_relocate_moves_the_file_to_the_trash_dest_path(tmp_path: Path) -> None:
    src = tmp_path / "charts/sub/old_junk.log"
    src.parent.mkdir(parents=True)
    src.write_text("j")
    expected = tu.trash_dest(tmp_path, "charts/sub/old_junk.log", "2026-07-13")

    trash_rel = tu.relocate(tmp_path, "charts/sub/old_junk.log", "2026-07-13")

    assert trash_rel == expected.relative_to(tmp_path).as_posix()
    assert trash_rel == "docs/dev/tmp/.trash/2026-07-13/charts/sub/old_junk.log"
    assert (tmp_path / trash_rel).read_text() == "j"
    assert not src.exists()


def test_relocate_keeps_the_earlier_file_on_a_dest_collision(
        tmp_path: Path) -> None:
    (tmp_path / "old_junk.log").write_text("new")
    taken = tmp_path / "docs/dev/tmp/.trash/2026-07-13/old_junk.log"
    taken.parent.mkdir(parents=True)
    taken.write_text("earlier")

    trash_rel = tu.relocate(tmp_path, "old_junk.log", "2026-07-13")

    assert trash_rel.startswith("docs/dev/tmp/.trash/2026-07-13/old_junk.log.dup")
    assert (tmp_path / trash_rel).read_text() == "new"
    assert taken.read_text() == "earlier"
    assert not (tmp_path / "old_junk.log").exists()


def test_tracked_junk_pathspec_finds_nested(repo: Path) -> None:
    p = repo / "charts/sub/.DS_Store"
    p.parent.mkdir(parents=True)
    p.write_text("x")
    _git(repo, "add", "-f", "charts/sub/.DS_Store")
    _git(repo, "commit", "-qm", "junk")
    out = subprocess.run(
        ["git", "-C", str(repo), "ls-files", "-z", "--",
         ".DS_Store", "**/.DS_Store", "Thumbs.db", "**/Thumbs.db", "*.pyc"],
        capture_output=True, text=True, check=True).stdout
    assert "charts/sub/.DS_Store" in out.split("\0")


def test_veto_development_paths_through_a_dotdot_segment(repo: Path) -> None:
    p = repo / "docs/dev/project-management/keep.bin"
    p.parent.mkdir(parents=True)
    p.write_text("k")
    os.utime(p, (OLD, OLD))
    (repo / "sub").mkdir()

    assert "protected" in _veto(repo, "sub/../docs/dev/project-management/keep.bin")


def test_main_refuses_a_protected_path_spelled_through_dotdot(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    p = repo / "docs/dev/project-management/keep.bin"
    p.parent.mkdir(parents=True)
    p.write_text("k")
    os.utime(p, (OLD, OLD))
    (repo / "sub").mkdir()

    monkeypatch.setattr(
        "sys.argv",
        ["trash_untracked.py", "--repo", str(repo),
         "sub/../docs/dev/project-management/keep.bin"])
    tu.main()
    out = json.loads(capsys.readouterr().out)

    assert out["moved"] == []
    assert out["refused"] == [{
        "path": "docs/dev/project-management/keep.bin",
        "reason": "protected path (docs/dev/project-management, docs, .git)",
    }]
    assert p.exists()


def test_manifest_row_names_the_file_that_was_moved(
        repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (repo / "old_junk.log").write_text("j")
    os.utime(repo / "old_junk.log", (OLD, OLD))
    (repo / "sub").mkdir()

    monkeypatch.setattr(
        "sys.argv",
        ["trash_untracked.py", "--repo", str(repo), "--apply",
         "sub/../old_junk.log"])
    tu.main()

    row = (repo / "docs/dev/tmp/.trash/manifest.tsv").read_text().strip().split("\t")
    assert row[2] == "old_junk.log"
    assert (repo / row[3]).is_file()


def test_a_tracked_nested_file_is_refused_by_its_slash_form_name(
        repo: Path) -> None:
    """`git ls-files` spells a nested entry with slashes on every host."""
    p = repo / "charts" / "sub" / "kept.log"
    p.parent.mkdir(parents=True)
    p.write_text("x")
    _git(repo, "add", "charts/sub/kept.log")
    _git(repo, "commit", "-qm", "nested")
    os.utime(p, (OLD, OLD))

    rel = tu.as_git_rel(repo, p)

    assert rel == "charts/sub/kept.log"
    assert "tracked" in _veto(repo, rel)


def test_an_untracked_nested_file_of_the_same_shape_is_permitted(
        repo: Path) -> None:
    p = repo / "charts" / "sub" / "old_junk.log"
    p.parent.mkdir(parents=True)
    p.write_text("j")
    os.utime(p, (OLD, OLD))

    rel = tu.as_git_rel(repo, p)

    assert rel == "charts/sub/old_junk.log"
    assert _veto(repo, rel) is None


@pytest.mark.parametrize("parts", [
    ("docs", "dev", "project-management", "keep.bin"),
    ("docs", "keep.bin"),
    (".git", "keep.bin"),
    ("docs", "dev", "tmp", "old_junk.log"),
    ("docs", "old_junk.log"),
])
def test_veto_refuses_each_protected_prefix_by_slash_form_identity(
        repo: Path, parts: tuple[str, ...]) -> None:
    p = repo.joinpath(*parts)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text("k")
    os.utime(p, (OLD, OLD))

    rel = tu.as_git_rel(repo, p)

    assert rel == "/".join(parts)
    assert "protected path" in _veto(repo, rel)


@pytest.mark.parametrize("parts", [
    ("dev", "tools", "old_junk.log"),
    ("guides", "old_junk.log"),
    ("dev", "tools", "keep.bin"),
    ("guides", "keep.bin"),
])
def test_veto_permits_a_sibling_directory_of_a_protected_prefix(
        repo: Path, parts: tuple[str, ...]) -> None:
    p = repo.joinpath(*parts)
    p.parent.mkdir(parents=True)
    p.write_text("j")
    os.utime(p, (OLD, OLD))

    rel = tu.as_git_rel(repo, p)

    assert rel == "/".join(parts)
    assert _veto(repo, rel) is None


def test_normalise_rel_reads_a_backslash_as_a_separator_only_on_nt(
        monkeypatch: pytest.MonkeyPatch) -> None:
    """Windows spells a separator there; POSIX spells a name character."""
    monkeypatch.setattr(tu.os, "name", "nt")

    assert tu.normalise_rel(
        r"docs\dev\project-management\keep.bin"
    ) == "docs/dev/project-management/keep.bin"
    assert tu.normalise_rel(r"sub\..\old_junk.log") == "old_junk.log"

    monkeypatch.setattr(tu.os, "name", "posix")

    assert tu.normalise_rel(r"dev\local\keep.bin") == r"dev\local\keep.bin"
    assert tu.normalise_rel(r"sub/../a\b.log") == r"a\b.log"


def test_normalise_rel_resolves_dot_and_dotdot_to_the_plain_name() -> None:
    assert tu.normalise_rel(
        "sub/../docs/dev/project-management/keep.bin") == "docs/dev/project-management/keep.bin"
    assert tu.normalise_rel("./sub/./../old_junk.log") == "old_junk.log"


def test_main_refuses_a_protected_path_that_contains_spaces(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    p = repo / "docs" / "dev" / "project-management" / "keep me" / "notes copy.bin"
    p.parent.mkdir(parents=True)
    p.write_text("k")
    os.utime(p, (OLD, OLD))
    spelled = str(
        Path("docs") / "dev" / "project-management" / "keep me" / "notes copy.bin"
    )

    monkeypatch.setattr(
        "sys.argv",
        ["trash_untracked.py", "--repo", str(repo), spelled])
    tu.main()
    out = json.loads(capsys.readouterr().out)

    assert out["moved"] == []
    assert out["refused"] == [{
        "path": "docs/dev/project-management/keep me/notes copy.bin",
        "reason": "protected path (docs/dev/project-management, docs, .git)",
    }]
    assert p.exists()


def test_main_reports_one_identity_for_a_moved_path_with_spaces(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """The report and the manifest name that file with one string."""
    p = repo / "old logs" / "run one.log"
    p.parent.mkdir(parents=True)
    p.write_text("j")
    os.utime(p, (OLD, OLD))
    (repo / "sub").mkdir()
    spelled = str(Path("sub") / ".." / "old logs" / "run one.log")

    monkeypatch.setattr(
        "sys.argv",
        ["trash_untracked.py", "--repo", str(repo), "--apply", spelled])
    tu.main()
    out = json.loads(capsys.readouterr().out)

    row = (repo / "docs/dev/tmp/.trash/manifest.tsv").read_text().strip().split("\t")
    assert out["refused"] == []
    assert out["moved"] == [{"path": "old logs/run one.log",
                             "trash": row[3]}]
    assert row[2] == "old logs/run one.log"
    assert row[3].startswith("docs/dev/tmp/.trash/")
    assert (repo / row[3]).is_file()
    assert not p.exists()


def test_load_tracked_reads_the_index_in_slash_form(repo: Path) -> None:
    """The tracked set is git's spelling, nested entries included."""
    assert tu.load_tracked(repo) == {"tracked.log"}

    p = repo / "charts" / "sub" / "kept.log"
    p.parent.mkdir(parents=True)
    p.write_text("x")
    _git(repo, "add", "charts/sub/kept.log")
    _git(repo, "commit", "-qm", "nested")

    assert tu.load_tracked(repo) == {"tracked.log", "charts/sub/kept.log"}


def test_a_junk_named_file_that_git_tracks_is_still_refused(
        repo: Path) -> None:
    """The index decides, not the filename."""
    p = repo / "charts" / "sub" / "old_junk.log"
    p.parent.mkdir(parents=True)
    p.write_text("j")
    _git(repo, "add", "charts/sub/old_junk.log")
    _git(repo, "commit", "-qm", "junk-shaped")
    os.utime(p, (OLD, OLD))

    rel = tu.as_git_rel(repo, p)

    assert rel == "charts/sub/old_junk.log"
    assert "tracked" in _veto(repo, rel)


def test_an_untracked_file_named_like_a_tracked_one_is_permitted(
        repo: Path) -> None:
    p = repo / "charts" / "sub" / "kept.log"
    p.parent.mkdir(parents=True)
    p.write_text("j")
    os.utime(p, (OLD, OLD))

    rel = tu.as_git_rel(repo, p)

    assert rel == "charts/sub/kept.log"
    assert _veto(repo, rel) is None


def test_as_git_rel_spells_a_deep_path_under_a_root_of_any_name(
        tmp_path: Path) -> None:
    root = tmp_path / "workspace"
    p = root / "charts" / "deep" / "nested" / "old logs" / "run one.log"
    p.parent.mkdir(parents=True)
    p.write_text("j")

    assert tu.as_git_rel(root, p) == (
        "charts/deep/nested/old logs/run one.log")


def test_as_git_rel_spells_a_path_the_way_git_ls_files_prints_it(
        tmp_path: Path) -> None:
    """Git's representation is pinned to git, not to a literal."""
    root = tmp_path / "workspace"
    root.mkdir()
    _git(root, "init", "-q", "-b", "master")
    _git(root, "config", "user.email", "t@t")
    _git(root, "config", "user.name", "t")
    p = root / "charts" / "deep" / "nested" / "kept.log"
    p.parent.mkdir(parents=True)
    p.write_text("x")
    _git(root, "add", "charts/deep/nested/kept.log")

    printed = subprocess.run(
        ["git", "-C", str(root), "ls-files", "-z"],
        capture_output=True, text=True, check=True).stdout.split("\0")

    assert tu.as_git_rel(root, p) == printed[0]
    assert printed[0] == "charts/deep/nested/kept.log"


@pytest.mark.parametrize("os_name", ["nt", "posix"])
@pytest.mark.parametrize("rel", [
    "docs/dev/project-management/",
    ".",
    "../old_junk.log",
    "sub/../../old_junk.log",
    "a//b/c",
    "a/b/../../c",
    "./sub/./../old_junk.log",
])
def test_normalise_rel_resolves_slash_input_like_posix_normpath(
        rel: str, os_name: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Same segment arithmetic on every host, slash form out."""
    monkeypatch.setattr(tu.os, "name", os_name)

    assert tu.normalise_rel(rel) == posixpath.normpath(rel)


@pytest.mark.parametrize("rel", [
    r"dev\local\keep.bin",
    r"sub\..\old_junk.log",
    r"a\\b\c",
    r"a\b\..\..\c",
    r"..\old_junk.log",
    r"charts\sub\.",
])
def test_normalise_rel_reads_a_backslash_as_a_separator_on_nt(
        rel: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tu.os, "name", "nt")

    assert tu.normalise_rel(rel) == posixpath.normpath(rel.replace("\\", "/"))


@pytest.mark.parametrize("rel", [
    r"dev\local\keep.bin",
    r"sub/../a\b.log",
    r"a\b\..\..\c",
    r"charts/sub/a\b/",
])
def test_normalise_rel_reads_a_backslash_as_a_name_character_on_posix(
        rel: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tu.os, "name", "posix")

    assert tu.normalise_rel(rel) == posixpath.normpath(rel)


def test_main_refuses_a_path_that_climbs_out_of_the_repository(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """A `..` that escapes the root is refused, and the file survives."""
    outside = repo.parent / "old_junk.log"
    outside.write_text("j")
    os.utime(outside, (OLD, OLD))

    monkeypatch.setattr(
        "sys.argv",
        ["trash_untracked.py", "--repo", str(repo), "../old_junk.log"])
    tu.main()
    out = json.loads(capsys.readouterr().out)

    assert out["moved"] == []
    assert len(out["refused"]) == 1
    assert "outside repo" in out["refused"][0]["reason"]
    assert outside.is_file()


DRY_RUN_MARKER = "DRY-RUN (use --apply)"
FROZEN_DATE = "2026-01-02"


class _FrozenDate(datetime.date):
    """`date.today()` pinned, so a run crossing midnight cannot flake."""

    @classmethod
    def today(cls) -> datetime.date:
        return cls.fromisoformat(FROZEN_DATE)


def _old_file(repo: Path, rel: str, text: str = "j") -> Path:
    p = repo / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text)
    os.utime(p, (OLD, OLD))
    return p


def _run_main(repo: Path, monkeypatch: pytest.MonkeyPatch,
              capsys: pytest.CaptureFixture[str],
              *argv: str) -> tuple[dict, str]:
    monkeypatch.setattr(
        "sys.argv", ["trash_untracked.py", "--repo", str(repo), *argv])
    monkeypatch.setattr(tu.datetime, "date", _FrozenDate)
    tu.main()
    cap = capsys.readouterr()
    return json.loads(cap.out), cap.err


def _expected_trash(repo: Path, rel: str) -> str:
    root = repo.resolve()
    return tu.trash_dest(root, rel, FROZEN_DATE).relative_to(root).as_posix()


def test_dry_run_without_apply_reports_the_trash_dest_path(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    _old_file(repo, "charts/sub/old_junk.log")
    expected = _expected_trash(repo, "charts/sub/old_junk.log")

    out, _ = _run_main(repo, monkeypatch, capsys, "charts/sub/old_junk.log")

    assert expected == (
        f"docs/dev/tmp/.trash/{FROZEN_DATE}/charts/sub/old_junk.log")
    assert out["moved"] == [{"path": "charts/sub/old_junk.log",
                             "trash": expected}]
    assert out["refused"] == []


def test_dry_run_without_apply_reports_a_dup_suffix_on_a_taken_dest(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    p = _old_file(repo, "old_junk.log", "new")
    taken = repo / "docs/dev/tmp/.trash" / FROZEN_DATE / "old_junk.log"
    taken.parent.mkdir(parents=True)
    taken.write_text("earlier")

    out, _ = _run_main(repo, monkeypatch, capsys, "old_junk.log")

    assert len(out["moved"]) == 1
    assert out["moved"][0]["path"] == "old_junk.log"
    trash = out["moved"][0]["trash"]
    prefix = f"docs/dev/tmp/.trash/{FROZEN_DATE}/old_junk.log.dup"
    assert trash.startswith(prefix) and trash[len(prefix):].isdigit()
    assert not (repo / trash).exists()
    assert taken.read_text() == "earlier"
    assert p.read_text() == "new"
    assert not (repo / "docs/dev/tmp/.trash/manifest.tsv").exists()


def test_dry_run_without_apply_prints_the_dry_run_marker(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    _old_file(repo, "old_junk.log")

    out, err = _run_main(repo, monkeypatch, capsys, "old_junk.log")

    assert DRY_RUN_MARKER in err.splitlines()
    assert DRY_RUN_MARKER not in json.dumps(out)


def test_apply_moves_the_file_and_writes_a_manifest_row(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    p = _old_file(repo, "charts/sub/old_junk.log")
    expected = _expected_trash(repo, "charts/sub/old_junk.log")

    out, _ = _run_main(repo, monkeypatch, capsys,
                       "--apply", "charts/sub/old_junk.log")

    assert out["moved"] == [{"path": "charts/sub/old_junk.log",
                             "trash": expected}]
    assert not p.exists()
    assert (repo / expected).read_text() == "j"
    row = (repo / "docs/dev/tmp/.trash/manifest.tsv").read_text().strip().split("\t")
    assert row == [FROZEN_DATE, "brush-junk",
                   "charts/sub/old_junk.log", expected]


def test_dry_run_without_apply_prints_the_marker_exactly_once_regardless_of_path_count(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    _old_file(repo, "old_junk.log")
    _old_file(repo, "charts/sub/old_junk.log")

    two, two_err = _run_main(repo, monkeypatch, capsys,
                             "old_junk.log", "charts/sub/old_junk.log")
    none, none_err = _run_main(repo, monkeypatch, capsys, "tracked.log")

    assert len(two["moved"]) == 2
    assert two_err.splitlines().count(DRY_RUN_MARKER) == 1
    assert none["moved"] == []
    assert len(none["refused"]) == 1
    assert none_err.splitlines().count(DRY_RUN_MARKER) == 1


def test_apply_honors_the_rule_flag_in_the_manifest(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    _old_file(repo, "old_junk.log")
    expected = _expected_trash(repo, "old_junk.log")

    _run_main(repo, monkeypatch, capsys,
              "--apply", "--rule", "custom-rule", "old_junk.log")

    row = (repo / "docs/dev/tmp/.trash/manifest.tsv").read_text().strip().split("\t")
    assert row[1] == "custom-rule"
    assert row == [FROZEN_DATE, "custom-rule", "old_junk.log", expected]


def test_apply_prints_no_dry_run_marker(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    _old_file(repo, "old_junk.log")

    _, err = _run_main(repo, monkeypatch, capsys, "--apply", "old_junk.log")

    assert DRY_RUN_MARKER not in err


def test_preview_moves_nothing(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    p = _old_file(repo, "charts/sub/old_junk.log")

    out, _ = _run_main(repo, monkeypatch, capsys, "charts/sub/old_junk.log")

    assert p.read_text() == "j"
    assert not (repo / "docs").exists()
    assert [e["path"] for e in out["moved"]] == ["charts/sub/old_junk.log"]


def test_preview_json_matches_the_apply_run(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    _old_file(repo, "charts/sub/old_junk.log")
    _old_file(repo, "old logs/run one.log")
    _old_file(repo, "docs/dev/project-management/keep.bin", "k")
    corpus = ["charts/sub/old_junk.log", "old logs/run one.log",
              "tracked.log", "docs/dev/project-management/keep.bin"]
    manifest = repo / "docs/dev/tmp/.trash/manifest.tsv"

    # Preview writes nothing, so the files' mtimes still clear --min-age-days.
    preview, _ = _run_main(repo, monkeypatch, capsys, *corpus)
    assert not manifest.exists()
    applied, _ = _run_main(repo, monkeypatch, capsys, "--apply", *corpus)

    assert len(preview["moved"]) == 2
    assert len(preview["refused"]) == 2
    assert preview == applied
    assert manifest.exists()
    for entry in applied["moved"]:
        assert (repo / entry["trash"]).read_text() == "j"
        assert not (repo / entry["path"]).exists()


def test_main_refuses_a_dotenv_file_passed_directly(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    p = _old_file(repo, ".env", "TOKEN=x")

    out, _ = _run_main(repo, monkeypatch, capsys, "--apply", ".env")

    assert out["moved"] == []
    assert [r["reason"] for r in out["refused"]] == ["protected name"]
    assert p.read_text() == "TOKEN=x"


def test_main_refuses_a_directory_holding_protected_files(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """A directory's own name clears every veto; its contents must not."""
    _old_file(repo, "sdir/.env", "TOKEN=x")
    _old_file(repo, "sdir/NOTES.md", "notes")
    _old_file(repo, "sdir/a.log")

    out, _ = _run_main(repo, monkeypatch, capsys, "--apply", "sdir")

    assert out["moved"] == []
    assert [r["path"] for r in out["refused"]] == ["sdir"]
    assert (repo / "sdir/.env").read_text() == "TOKEN=x"
    assert (repo / "sdir/NOTES.md").read_text() == "notes"
    assert (repo / "sdir/a.log").exists()
    assert not (repo / "docs/dev/tmp/.trash/manifest.tsv").exists()


def test_preview_refuses_a_directory_holding_protected_files(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """The same refusal happens in dry-run, before --apply is ever passed."""
    _old_file(repo, "sdir/.env", "TOKEN=x")
    _old_file(repo, "sdir/NOTES.md", "notes")
    _old_file(repo, "sdir/a.log")

    out, _ = _run_main(repo, monkeypatch, capsys, "sdir")

    assert out["moved"] == []
    assert [r["path"] for r in out["refused"]] == ["sdir"]
    assert (repo / "sdir/.env").is_file()
    assert (repo / "sdir/NOTES.md").is_file()
    assert (repo / "sdir/a.log").is_file()


def test_main_refuses_a_directory_holding_a_protected_file_nested_below_another_directory(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """The protected file sits two levels down; the whole candidate is refused."""
    _old_file(repo, "sdir/inner/.env", "TOKEN=x")
    _old_file(repo, "sdir/inner/a.log")
    _old_file(repo, "sdir/b.log")

    out, _ = _run_main(repo, monkeypatch, capsys, "--apply", "sdir")

    assert out["moved"] == []
    assert [r["path"] for r in out["refused"]] == ["sdir"]
    assert (repo / "sdir/inner/.env").read_text() == "TOKEN=x"
    assert (repo / "sdir/inner/a.log").exists()
    assert (repo / "sdir/b.log").exists()
    assert not (repo / "docs/dev/tmp/.trash/manifest.tsv").exists()


def _fake_gh_run(monkeypatch: pytest.MonkeyPatch, *, rc: int = 0,
                 stdout: str = "[]",
                 side_effect: Exception | None = None) -> None:
    """Replace cf.subprocess.run with a fake `gh pr list` seam.

    Non-`gh` commands (git, pgrep, ...) fall through to the real
    subprocess.run so the rest of collect_facts keeps working normally.
    """
    real = cf.subprocess.run

    def fake(cmd, *a, **kw):
        if cmd[0] == "gh":
            if side_effect is not None:
                raise side_effect
            return subprocess.CompletedProcess(cmd, rc, stdout=stdout,
                                               stderr="")
        return real(cmd, *a, **kw)

    monkeypatch.setattr(cf.subprocess, "run", fake)
    monkeypatch.setattr(cf.shutil, "which", lambda name: "/usr/bin/gh"
                        if name == "gh" else None)


def test_gather_prs_returns_the_parsed_list_on_success(
        repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    prs = [{"number": 1, "headRefName": "feat", "state": "OPEN"}]
    _fake_gh_run(monkeypatch, rc=0, stdout=json.dumps(prs))

    assert cf.gather_prs(repo) == prs


def test_gather_prs_returns_an_empty_list_when_there_are_no_open_prs(
        repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_gh_run(monkeypatch, rc=0, stdout="[]")

    assert cf.gather_prs(repo) == []


def test_gather_prs_raises_on_a_nonzero_exit_instead_of_hiding_it(
        repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """A failed `gh` call must never be silently read as 'no open PRs'."""
    _fake_gh_run(monkeypatch, rc=1, stdout="")

    with pytest.raises(Exception):
        cf.gather_prs(repo)


def test_gather_prs_raises_on_an_error_object_never_treating_it_as_a_list(
        repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`gh` can exit 0 with `{"message": "..."}` on some failures; that is
    not a list of PRs and must not be returned as if it were."""
    _fake_gh_run(monkeypatch, rc=0,
                stdout=json.dumps({"message": "rate limited"}))

    with pytest.raises(Exception):
        cf.gather_prs(repo)


def test_gather_prs_raises_on_a_bare_scalar_reply(
        repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """`gh` can exit 0 with valid JSON that is neither a dict nor a list
    (e.g. `null`); that must not be returned as if it were a PR list."""
    _fake_gh_run(monkeypatch, rc=0, stdout="null")

    with pytest.raises(Exception):
        cf.gather_prs(repo)


def test_gather_prs_raises_on_malformed_json(
        repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_gh_run(monkeypatch, rc=0, stdout="not json at all")

    with pytest.raises(Exception):
        cf.gather_prs(repo)


def test_gather_prs_raises_on_a_timeout(
        repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _fake_gh_run(monkeypatch,
                side_effect=subprocess.TimeoutExpired(cmd=["gh"], timeout=15))

    with pytest.raises(Exception):
        cf.gather_prs(repo)


def test_gather_prs_raises_when_gh_is_not_installed(
        repo: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing tooling is an unknown state, not '0 open PRs'."""
    monkeypatch.setattr(cf.shutil, "which", lambda name: None)

    with pytest.raises(Exception):
        cf.gather_prs(repo)


def _collect(repo: Path, monkeypatch: pytest.MonkeyPatch,
            capsys: pytest.CaptureFixture[str]) -> dict:
    """Run collect_facts.main() in-process so the gh seam monkeypatch applies."""
    monkeypatch.setattr(
        "sys.argv", ["collect_facts.py", "--repo", str(repo), "--fast"])
    cf.main()
    return json.loads(capsys.readouterr().out)


def test_collector_reports_prs_normally_on_success(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    prs = [{"number": 1, "headRefName": "feat", "state": "OPEN"}]
    _fake_gh_run(monkeypatch, rc=0, stdout=json.dumps(prs))

    facts = _collect(repo, monkeypatch, capsys)

    assert facts["open_prs"] == prs
    assert not any(w.startswith("open_prs") for w in facts["warnings"])


def test_collector_reports_no_open_prs_as_a_known_empty_list(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    _fake_gh_run(monkeypatch, rc=0, stdout="[]")

    facts = _collect(repo, monkeypatch, capsys)

    assert facts["open_prs"] == []
    assert not any(w.startswith("open_prs") for w in facts["warnings"])


def test_collector_surfaces_a_warning_and_null_prs_on_a_failed_gh_call(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    _fake_gh_run(monkeypatch, rc=1, stdout="")

    facts = _collect(repo, monkeypatch, capsys)

    assert facts["open_prs"] is None
    assert any(w.startswith("open_prs") for w in facts["warnings"])
    # the probe failing must not wipe out unrelated fact sections
    assert facts["branches"] is not None
    assert facts["stashes"] is not None


def test_collector_never_reports_an_error_object_as_the_pr_list(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    _fake_gh_run(monkeypatch, rc=0,
                stdout=json.dumps({"message": "rate limited"}))

    facts = _collect(repo, monkeypatch, capsys)

    assert facts["open_prs"] is None
    assert facts["open_prs"] != {"message": "rate limited"}
    assert any(w.startswith("open_prs") for w in facts["warnings"])


def test_collector_never_reports_a_bare_scalar_reply_as_the_pr_list(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    _fake_gh_run(monkeypatch, rc=0, stdout="null")

    facts = _collect(repo, monkeypatch, capsys)

    assert facts["open_prs"] is None
    assert any(w.startswith("open_prs") for w in facts["warnings"])


def test_collector_surfaces_a_warning_on_malformed_json(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    _fake_gh_run(monkeypatch, rc=0, stdout="not json at all")

    facts = _collect(repo, monkeypatch, capsys)

    assert facts["open_prs"] is None
    assert any(w.startswith("open_prs") for w in facts["warnings"])


def test_collector_surfaces_a_warning_on_a_timed_out_gh_call(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    _fake_gh_run(monkeypatch,
                side_effect=subprocess.TimeoutExpired(cmd=["gh"], timeout=15))

    facts = _collect(repo, monkeypatch, capsys)

    assert facts["open_prs"] is None
    assert any(w.startswith("open_prs") for w in facts["warnings"])


def test_collector_surfaces_a_warning_when_gh_is_missing_distinct_from_zero_prs(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Missing `gh` must read as unknown, never as the known-empty case."""
    monkeypatch.setattr(cf.shutil, "which", lambda name: None)

    facts = _collect(repo, monkeypatch, capsys)

    assert facts["open_prs"] is None
    assert any(w.startswith("open_prs") for w in facts["warnings"])


def test_open_prs_unknown_state_is_distinguishable_from_a_known_empty_list(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """A guard deciding branch-deletion eligibility must be able to tell
    'no open PRs confirmed' (`[]`) apart from 'could not find out' (`None`
    plus a warning) - collapsing them is exactly the regression (00096)."""
    _fake_gh_run(monkeypatch, rc=0, stdout="[]")
    known_empty = _collect(repo, monkeypatch, capsys)

    _fake_gh_run(monkeypatch, rc=1, stdout="")
    unknown = _collect(repo, monkeypatch, capsys)

    assert known_empty["open_prs"] == []
    assert unknown["open_prs"] is None
    assert not any(w.startswith("open_prs") for w in known_empty["warnings"])
    assert any(w.startswith("open_prs") for w in unknown["warnings"])


def test_main_moves_a_directory_containing_only_old_junk(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Control: an eligible junk-only directory still moves whole."""
    _old_file(repo, "sdir/a.log")
    _old_file(repo, "sdir/inner/b.log")

    out, _ = _run_main(repo, monkeypatch, capsys, "--apply", "sdir")

    assert out["refused"] == []
    assert [e["path"] for e in out["moved"]] == ["sdir"]
    assert not (repo / "sdir").exists()
    row = (repo / "docs/dev/tmp/.trash/manifest.tsv").read_text().strip().split("\t")
    assert row[2] == "sdir"


# -- shared-destination-base regression (00106): brush's manifest fourth
# field must be store-relative (relative to docs/dev/tmp, no leading
# "docs/dev/tmp/"), matching purge-devtmp's writer, while the move-location
# and the moved/preview JSON "trash" path stay repository-relative as today.

def test_manifest_fourth_field_is_store_relative_for_a_nested_path(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    _old_file(repo, "charts/sub/old_junk.log")

    out, _ = _run_main(repo, monkeypatch, capsys,
                       "--apply", "charts/sub/old_junk.log")

    row = (repo / "docs/dev/tmp/.trash/manifest.tsv").read_text().strip().split("\t")
    assert row[3] == f".trash/{FROZEN_DATE}/charts/sub/old_junk.log"
    assert not row[3].startswith("docs/")
    assert "docs/dev/tmp" not in row[3]
    # the move itself, and the moved/preview JSON, stay repository-relative
    repo_relative = f"docs/dev/tmp/.trash/{FROZEN_DATE}/charts/sub/old_junk.log"
    assert out["moved"] == [{"path": "charts/sub/old_junk.log",
                             "trash": repo_relative}]
    assert (repo / repo_relative).is_file()


def test_manifest_fourth_field_is_store_relative_for_a_top_level_file(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """Second, distinct fixture value: an un-nested path at the top level."""
    _old_file(repo, "old_junk.log")

    out, _ = _run_main(repo, monkeypatch, capsys, "--apply", "old_junk.log")

    row = (repo / "docs/dev/tmp/.trash/manifest.tsv").read_text().strip().split("\t")
    assert row[3] == f".trash/{FROZEN_DATE}/old_junk.log"
    assert not row[3].startswith("docs/")
    repo_relative = f"docs/dev/tmp/.trash/{FROZEN_DATE}/old_junk.log"
    assert out["moved"] == [{"path": "old_junk.log", "trash": repo_relative}]
    assert (repo / repo_relative).is_file()


def test_manifest_fourth_field_is_store_relative_on_a_collision_suffix(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """A dup-suffixed destination is still spelled from the store, not the repo root."""
    _old_file(repo, "old_junk.log", "new")
    taken = repo / "docs/dev/tmp/.trash" / FROZEN_DATE / "old_junk.log"
    taken.parent.mkdir(parents=True)
    taken.write_text("earlier")

    _run_main(repo, monkeypatch, capsys, "--apply", "old_junk.log")

    row = (repo / "docs/dev/tmp/.trash/manifest.tsv").read_text().strip().split("\t")
    prefix = f".trash/{FROZEN_DATE}/old_junk.log.dup"
    assert row[3].startswith(prefix) and row[3][len(prefix):].isdigit()
    assert not row[3].startswith("docs/")
    assert (repo / f"docs/dev/tmp/{row[3]}").is_file()


def test_manifest_appends_a_store_relative_row_after_an_old_repository_relative_row_unchanged(
        repo: Path, monkeypatch: pytest.MonkeyPatch,
        capsys: pytest.CaptureFixture[str]) -> None:
    """An old-format row already on disk must survive byte-identical."""
    manifest = repo / "docs/dev/tmp/.trash/manifest.tsv"
    manifest.parent.mkdir(parents=True)
    old_row = (f"2026-07-13\tbrush-junk\tprior.log\t"
              f"docs/dev/tmp/.trash/2026-07-13/prior.log\n")
    manifest.write_text(old_row)
    _old_file(repo, "old_junk.log")

    _run_main(repo, monkeypatch, capsys, "--apply", "old_junk.log")

    lines = manifest.read_text().splitlines(keepends=True)
    assert lines[0] == old_row
    new_row = lines[1].rstrip("\n").split("\t")
    assert new_row == [FROZEN_DATE, "brush-junk", "old_junk.log",
                       f".trash/{FROZEN_DATE}/old_junk.log"]
