"""Safety rules of glean: settled verdicts stay quiet, volatile ones come back,
and check-staged refuses anything that must never reach a public remote."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

_spec = importlib.util.spec_from_file_location("glean", Path(__file__).with_name("glean.py"))
glean = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(glean)

TODAY = date.today().isoformat()


def git(home: Path, *args: str) -> str:
    return subprocess.run(
        ["git", f"--git-dir={home / '.dots'}", f"--work-tree={home}", *args],
        cwd=home, check=True, capture_output=True, text=True,
    ).stdout


@pytest.fixture
def home(tmp_path, monkeypatch, isolate_home):
    isolate_home(tmp_path)  # git must not read the developer's global excludes
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", os.devnull)
    monkeypatch.setattr(glean, "HOME", tmp_path)
    subprocess.run(["git", "init", "-q", "--bare", str(tmp_path / ".dots")], check=True)
    git(tmp_path, "config", "user.email", "t@example.com")
    git(tmp_path, "config", "user.name", "t")
    git(tmp_path, "config", "status.showUntrackedFiles", "no")
    (tmp_path / ".config").mkdir()
    (tmp_path / ".config" / "tracked.conf").write_text("x\n")
    git(tmp_path, "add", ".config/tracked.conf")
    git(tmp_path, "commit", "-qm", "init")
    return tmp_path


def write_ledger(home: Path, entries: list[dict]) -> Path:
    path = home / "ledger.json"
    path.write_text(json.dumps({"config": {"git_dir": str(home / ".dots")}, "entries": entries}))
    return path


def run(home: Path, cmd: str, entries: list[dict]) -> dict:
    cfg, all_entries = glean.load_ledgers(write_ledger(home, entries))
    return glean.cmd_scan(cfg, all_entries) if cmd == "scan" else glean.cmd_check_staged(cfg, all_entries)


def paths(result: dict, key: str) -> list[str]:
    return [c["path"] for c in result[key]]


def test_stable_verdict_silences_whole_directory(home):
    (home / ".cache").mkdir()
    (home / ".cache" / "x").write_text("x")
    r = run(home, "scan", [{"path": ".cache/", "verdict": "noise", "decided": TODAY}])
    assert ".cache/" not in paths(r, "candidates")
    assert r["counts"]["settled"] == 1


def test_unsettled_untracked_config_is_a_candidate(home):
    (home / ".config" / "tool.toml").write_text("theme = 'dark'\n")
    assert ".config/tool.toml" in paths(run(home, "scan", []), "candidates")


def test_new_tool_dir_is_one_decision(home):
    (home / ".config" / "newtool").mkdir()
    (home / ".config" / "newtool" / "a.toml").write_text("a\n")
    (home / ".config" / "newtool" / "b.toml").write_text("b\n")
    assert paths(run(home, "scan", []), "candidates") == [".config/newtool/"]


def test_skip_on_new_dir_resurfaces_when_any_file_changes(home):
    d = home / ".config" / "newtool"
    d.mkdir()
    (d / "a.toml").write_text("a\n")
    fp = run(home, "scan", [])["candidates"][0]["sha256"]
    entry = {"path": ".config/newtool/", "verdict": "skip", "decided": TODAY, "sha256": fp}
    assert run(home, "scan", [entry])["counts"]["resurfaced"] == 0
    (d / "a.toml").write_text("changed\n")
    assert paths(run(home, "scan", [entry]), "resurfaced") == [".config/newtool/"]


def test_dir_prescreen_counts_soft_hits_and_lists_hard_ones(home):
    d = home / ".config" / "newtool"
    d.mkdir()
    (d / "notes").write_text("# rotate the token yearly\n")
    (d / "key").write_text("-----BEGIN OPENSSH PRIVATE KEY-----\n")
    c = run(home, "scan", [])["candidates"][0]
    assert c["soft_hits"] == 1
    assert [h["file"] for h in c["secret_hits"]] == [".config/newtool/key"]


def test_skip_stays_quiet_while_content_unchanged(home):
    f = home / ".toolrc"
    f.write_text("a\n")
    entry = {"path": ".toolrc", "verdict": "skip", "decided": TODAY, "sha256": glean.sha256(f)}
    r = run(home, "scan", [entry])
    assert ".toolrc" not in paths(r, "candidates") + paths(r, "resurfaced")


def test_skip_resurfaces_when_content_changes(home):
    f = home / ".toolrc"
    f.write_text("a\n")
    entry = {"path": ".toolrc", "verdict": "skip", "decided": TODAY, "sha256": glean.sha256(f)}
    f.write_text("b\n")
    r = run(home, "scan", [entry])
    assert paths(r, "resurfaced") == [".toolrc"]
    assert r["resurfaced"][0]["previous"]["reason"] == "content changed"


def test_skip_resurfaces_after_180_days(home):
    f = home / ".toolrc"
    f.write_text("a\n")
    old = (date.today() - timedelta(days=181)).isoformat()
    entry = {"path": ".toolrc", "verdict": "skip", "decided": old, "sha256": glean.sha256(f)}
    assert paths(run(home, "scan", [entry]), "resurfaced") == [".toolrc"]


def test_symlink_into_a_link_root_is_settled_but_others_surface(home):
    repos = home / "repos" / "skills" / "x"
    repos.mkdir(parents=True)
    (home / ".linked").symlink_to(repos)
    (home / ".stray").symlink_to(home / ".config")
    ledger = home / "ledger.json"
    ledger.write_text(json.dumps({"config": {"git_dir": str(home / ".dots"),
                                             "link_roots": [str(home / "repos")]}, "entries": []}))
    r = glean.cmd_scan(*glean.load_ledgers(ledger))
    assert ".linked" not in paths(r, "candidates")
    assert ".stray" in paths(r, "candidates")


def test_prescreen_reports_keyword_never_value(home):
    (home / ".toolrc").write_text("api_key = hunter2-very-secret\n")
    hits = run(home, "scan", [])["candidates"][0]["secret_hits"]
    assert hits and "hunter2" not in json.dumps(hits)


def test_local_dirs_never_surface_as_candidates(home):
    (home / ".local" / "bin").mkdir(parents=True)
    (home / ".local" / "bin" / "tidy").write_text("#!/bin/sh\necho hi\n")
    (home / ".config" / ".local").mkdir()
    (home / ".config" / ".local" / "notes.md").write_text("x\n")
    r = run(home, "scan", [])
    assert not [p for p in paths(r, "candidates") if ".local" in p]


@pytest.mark.parametrize("rel", [".local/bin/tidy", ".config/.local/notes.md"])
def test_check_staged_refuses_local_dirs_without_ledger_entry(home, rel):
    f = home / rel
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("x\n")
    git(home, "add", "-f", rel)
    r = run(home, "check-staged", [])
    assert not r["ok"] and r["hard"][0]["why"] == "ledger verdict never"


def test_unmapped_secret_blob_is_flagged(home):
    (home / ".gitsecret" / "paths").mkdir(parents=True)
    (home / ".gitsecret" / "paths" / "mapping.cfg").write_text("a/tok:abc\n")
    (home / ".tok.secret").write_bytes(b"\0enc")
    assert ".tok.secret" in run(home, "scan", [])["secret_gaps"]["unmapped_blobs"]


def test_check_staged_refuses_plaintext_of_git_secret_file(home):
    (home / ".gitsecret" / "paths").mkdir(parents=True)
    (home / ".gitsecret" / "paths" / "mapping.cfg").write_text(".tok:abc\n")
    (home / ".tok").write_text("plain\n")
    git(home, "add", "-f", ".tok")
    r = run(home, "check-staged", [])
    assert not r["ok"] and r["hard"][0]["why"] == "plaintext of a git-secret file"


def test_check_staged_refuses_never_verdict(home):
    (home / ".netrc").write_text("machine x\n")
    git(home, "add", ".netrc")
    r = run(home, "check-staged", [{"path": ".netrc", "verdict": "never", "decided": TODAY}])
    assert not r["ok"]


def test_check_staged_refuses_unencrypted_secret_blob(home):
    (home / ".tok.secret").write_text("not encrypted\n")
    git(home, "add", ".tok.secret")
    assert not run(home, "check-staged", [])["ok"]


def test_check_staged_refuses_credential_pattern(home):
    (home / ".toolrc").write_text("token: ghp_" + "a" * 36 + "\n")
    git(home, "add", ".toolrc")
    r = run(home, "check-staged", [])
    assert not r["ok"] and "ghp_" + "a" * 36 not in json.dumps(r)


def test_hard_pattern_ignores_sk_inside_kebab_case_words():
    assert glean.scan_lines("see 00120-migrate-task-tracking-to-statectl-v1.md\n") == []
    assert glean.scan_lines("key: sk-" + "a" * 40 + "\n")[0][1].startswith("HARD:")


def test_check_staged_passes_comment_mentions_as_soft(home):
    (home / ".toolrc").write_text("# keep secrets out of here\n")
    git(home, "add", ".toolrc")
    r = run(home, "check-staged", [])
    assert r["ok"] and r["soft"]


def run_cli(home: Path, ledger: Path, command: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(Path(glean.__file__)), command, f"--ledger={ledger}"],
        cwd=home, capture_output=True, text=True, check=False,
    )


def write_ledger_with_public(home: Path, public_ledger: Path | None, entries: list[dict] | None = None) -> Path:
    cfg = {"git_dir": str(home / ".dots")}
    if public_ledger is not None:
        cfg["public_ledger"] = str(public_ledger)
    path = home / "ledger.json"
    path.write_text(json.dumps({"config": cfg, "entries": entries or []}))
    return path


def test_check_staged_refuses_harmless_file_when_public_ledger_is_valid(home):
    public = home / "public.json"
    public.write_text(json.dumps({"entries": [{"path": ".foorc", "verdict": "never", "decided": TODAY}]}))
    (home / ".foorc").write_text("x=1\n")
    git(home, "add", ".foorc")
    ledger = write_ledger_with_public(home, public)
    r = run_cli(home, ledger, "check-staged")
    assert r.returncode == 1
    body = json.loads(r.stdout)
    assert not body["ok"] and body["hard"][0]["why"] == "ledger verdict never"


def test_check_staged_allows_harmless_file_when_public_ledger_is_omitted(home):
    (home / ".foorc").write_text("x=1\n")
    git(home, "add", ".foorc")
    ledger = write_ledger_with_public(home, None)
    r = run_cli(home, ledger, "check-staged")
    assert r.returncode == 0
    assert json.loads(r.stdout)["ok"]


def test_check_staged_refuses_harmless_file_when_public_ledger_is_missing(home):
    (home / ".foorc").write_text("x=1\n")
    git(home, "add", ".foorc")
    # public ledger configured but the file was never written (typo'd or deleted path)
    ledger = write_ledger_with_public(home, home / "no-such-public.json")
    r = run_cli(home, ledger, "check-staged")
    assert r.returncode != 0, r.stdout
    assert "Traceback" not in r.stderr
    assert "no-such-public.json" in r.stderr
    # the bug under test: a missing public ledger must never let the staged check report success
    assert not (r.returncode == 0 and json.loads(r.stdout or "{}").get("ok"))


def test_check_staged_refuses_harmless_file_when_public_ledger_path_is_a_near_miss(home):
    public = home / "public.json"
    public.write_text(json.dumps({"entries": [{"path": ".foorc", "verdict": "never", "decided": TODAY}]}))
    (home / ".foorc").write_text("x=1\n")
    git(home, "add", ".foorc")
    # configured path shares a prefix with the real file but is not it (typo: trailing "s")
    ledger = write_ledger_with_public(home, home / "publics.json")
    r = run_cli(home, ledger, "check-staged")
    assert r.returncode != 0, r.stdout
    assert "Traceback" not in r.stderr
    assert "publics.json" in r.stderr


def test_scan_refuses_to_run_when_public_ledger_is_missing(home):
    (home / ".config" / "tool.toml").write_text("theme = 'dark'\n")
    ledger = write_ledger_with_public(home, home / "no-such-public.json")
    r = run_cli(home, ledger, "scan")
    assert r.returncode != 0, r.stdout
    assert "Traceback" not in r.stderr
    assert "no-such-public.json" in r.stderr


def test_check_staged_exits_nonzero_when_local_ledger_itself_is_missing(home):
    (home / ".foorc").write_text("x=1\n")
    git(home, "add", ".foorc")
    r = run_cli(home, home / "no-such-ledger.json", "check-staged")
    assert r.returncode != 0, r.stdout
    assert "Traceback" not in r.stderr
    assert "no-such-ledger.json" in r.stderr


def test_check_staged_flags_credential_in_non_ascii_path(home):
    (home / ".café").write_text("x=ghp_" + "a" * 36 + "\n")
    git(home, "add", ".café")
    r = run_cli(home, write_ledger(home, []), "check-staged")
    assert "Traceback" not in r.stderr, r.stderr
    assert r.returncode == 1
    body = json.loads(r.stdout)
    assert [h["path"] for h in body["hard"]] == [".café"]
    assert body["hard"][0]["why"] == "credential pattern ghp_"
    assert body["staged"] == 1


def test_check_staged_reports_safe_non_ascii_path_without_crash(home):
    (home / ".café").write_text("theme = dark\n")
    git(home, "add", ".café")
    r = run_cli(home, write_ledger(home, []), "check-staged")
    assert "Traceback" not in r.stderr, r.stderr
    assert r.returncode == 0
    body = json.loads(r.stdout)
    assert body["ok"]
    assert body["hard"] == []
    assert body["staged"] == 1


def test_check_staged_refuses_plaintext_of_git_secret_file_with_non_ascii_path(home):
    (home / ".gitsecret" / "paths").mkdir(parents=True)
    (home / ".gitsecret" / "paths" / "mapping.cfg").write_text(".tök:abc\n")
    (home / ".tök").write_text("plain\n")
    git(home, "add", "-f", ".tök")
    r = run_cli(home, write_ledger(home, []), "check-staged")
    assert "Traceback" not in r.stderr, r.stderr
    body = json.loads(r.stdout)
    assert not body["ok"]
    assert [h["path"] for h in body["hard"]] == [".tök"]
    assert body["hard"][0]["why"] == "plaintext of a git-secret file"


def test_check_staged_refuses_never_verdict_matched_against_non_ascii_path(home):
    (home / ".nëtrc").write_text("machine x\n")
    git(home, "add", ".nëtrc")
    entry = {"path": ".nëtrc", "verdict": "never", "decided": TODAY}
    r = run_cli(home, write_ledger(home, [entry]), "check-staged")
    assert "Traceback" not in r.stderr, r.stderr
    body = json.loads(r.stdout)
    assert not body["ok"]
    assert [h["path"] for h in body["hard"]] == [".nëtrc"]
    assert body["hard"][0]["why"] == "ledger verdict never"


def test_check_staged_allows_two_unrelated_non_ascii_files_with_distinct_counts(home):
    (home / ".café").write_text("x=1\n")
    (home / ".tëa").write_text("y=2\n")
    git(home, "add", ".café")
    git(home, "add", ".tëa")
    r = run_cli(home, write_ledger(home, []), "check-staged")
    assert "Traceback" not in r.stderr, r.stderr
    body = json.loads(r.stdout)
    assert body["ok"]
    assert body["staged"] == 2


def test_check_staged_reports_filename_with_space_and_combining_character(home):
    name = ".my café"  # space plus combining acute accent, git quotes by default
    (home / name).write_text("token: ghp_" + "b" * 36 + "\n")
    git(home, "add", name)
    r = run_cli(home, write_ledger(home, []), "check-staged")
    assert "Traceback" not in r.stderr, r.stderr
    body = json.loads(r.stdout)
    assert not body["ok"]
    assert [h["path"] for h in body["hard"]] == [name]


def test_check_staged_reports_renamed_non_ascii_path_not_the_original(home):
    (home / ".café").write_text("line one\nline two\nline three\n")
    git(home, "add", ".café")
    git(home, "commit", "-qm", "add café")
    git(home, "mv", ".café", ".thé")
    r = run_cli(home, write_ledger(home, []), "check-staged")
    assert "Traceback" not in r.stderr, r.stderr
    body = json.loads(r.stdout)
    assert body["ok"]
    assert body["staged"] == 1
    # numstat for a pure rename with no content change reports the new path only
