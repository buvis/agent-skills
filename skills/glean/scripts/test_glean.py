"""Safety rules of glean: settled verdicts stay quiet, volatile ones come back,
and check-staged refuses anything that must never reach a public remote."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import unicodedata
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
    # git normalizes a decomposed (NFD) filename to composed (NFC) on add on some
    # platforms (e.g. macOS core.precomposeunicode); either normal form is correct.
    assert [unicodedata.normalize("NFC", h["path"]) for h in body["hard"]] == [unicodedata.normalize("NFC", name)]


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


def test_skip_on_dir_resurfaces_forever_once_grown_past_max_dir_files(home):
    """A decided directory that grows past MAX_DIR_FILES resurfaces once on
    growth (expected either way), then must settle after the operator
    re-records a fresh fingerprint - it must not keep resurfacing forever."""
    d = home / ".config" / "newtool"
    d.mkdir()
    for i in range(200):
        (d / f"f{i}.txt").write_text(f"{i}\n")
    fp = run(home, "scan", [])["candidates"][0]["sha256"]
    entry = {"path": ".config/newtool/", "verdict": "skip", "decided": TODAY, "sha256": fp}
    # settled while the directory is at the cap and unchanged since the decision
    assert run(home, "scan", [entry])["counts"]["resurfaced"] == 0

    for i in range(200, 205):
        (d / f"f{i}.txt").write_text(f"{i}\n")

    first_after_growth = run(home, "scan", [entry])
    # expected either way once the directory has grown past the cap; not evidence of the defect
    assert paths(first_after_growth, "resurfaced") == [".config/newtool/"]

    # operator re-decides after the resurface, recording whatever fingerprint
    # describe() can currently produce for the grown directory
    new_fp = describe_fingerprint(first_after_growth["resurfaced"][0])
    re_recorded = {"path": ".config/newtool/", "verdict": "skip", "decided": TODAY, **new_fp}
    second_after_growth = run(home, "scan", [re_recorded])
    # the actual assertion: with a fingerprint the re-decision can actually
    # store and zero content change since, a correctly behaving scan settles.
    # Under the present code describe() produces no fingerprint at all for an
    # over-cap directory, so new_fp is empty, re_recorded fails ledger
    # validation, and this is expected to FAIL if the suspected defect is real.
    assert ".config/newtool/" not in paths(second_after_growth, "resurfaced")


def describe_fingerprint(candidate: dict) -> dict:
    """The one fingerprint field (if any) describe() put on a scan result,
    as the entry field an operator would record when re-deciding."""
    for key in ("count_mtime", "sha256"):
        if key in candidate:
            return {key: candidate[key]}
    return {}


BASE_MTIME = 1_700_000_000


def make_dir(home: Path, rel: str, n: int, latest: int) -> Path:
    """n files at BASE_MTIME, the lexically last one (index n-1, past the
    200-file prescreen cap when n > 200) at `latest`. Whole-second mtimes keep
    the expected count_mtime independent of truncation vs rounding."""
    d = home / rel
    d.mkdir(parents=True)
    for i in range(n):
        f = d / f"f{i:03d}.txt"
        f.write_text(f"{i}\n")
        os.utime(f, (BASE_MTIME, BASE_MTIME))
    os.utime(d / f"f{n - 1:03d}.txt", (latest, latest))
    return d


def cm_entry(rel: str, verdict: str, count_mtime: str, decided: str = TODAY) -> dict:
    return {"path": rel, "verdict": verdict, "decided": decided, "count_mtime": count_mtime}


@pytest.mark.parametrize("n,latest", [(205, BASE_MTIME + 50), (230, BASE_MTIME + 777)])
def test_over_cap_dir_settles_on_unchanged_count_mtime_across_repeated_scans(home, n, latest):
    make_dir(home, ".config/newtool", n, latest)
    c = glean.describe(".config/newtool/")
    # count and latest mtime cover every file, including those past the first 200
    assert c["count_mtime"] == f"{n}:{latest}"
    assert "sha256" not in c
    entry = cm_entry(".config/newtool/", "skip", c["count_mtime"])
    for _ in range(2):
        r = run(home, "scan", [entry])
        assert r["counts"]["resurfaced"] == 0
        assert ".config/newtool/" not in paths(r, "candidates") + paths(r, "resurfaced")


@pytest.mark.parametrize("change", ["touch_beyond_cap", "touch_within_cap", "add_file"])
def test_over_cap_dir_resurfaces_when_count_or_latest_mtime_changes(home, change):
    d = make_dir(home, ".config/newtool", 205, BASE_MTIME + 50)
    entry = cm_entry(".config/newtool/", "skip", "205:1700000050")
    assert run(home, "scan", [entry])["counts"]["resurfaced"] == 0
    if change == "add_file":
        (d / "f205.txt").write_text("new\n")
        os.utime(d / "f205.txt", (BASE_MTIME, BASE_MTIME))
        expected = "206:1700000050"
    else:
        f = d / ("f203.txt" if change == "touch_beyond_cap" else "f010.txt")
        os.utime(f, (BASE_MTIME + 900, BASE_MTIME + 900))
        expected = "205:1700000900"
    r = run(home, "scan", [entry])
    assert paths(r, "resurfaced") == [".config/newtool/"]
    assert r["resurfaced"][0]["count_mtime"] == expected
    assert r["resurfaced"][0]["previous"] == {"verdict": "skip", "decided": TODAY, "reason": "content changed"}


def test_over_cap_dir_fingerprint_counts_nested_files_and_resurfaces_on_their_change(home):
    d = make_dir(home, ".config/newtool", 205, BASE_MTIME + 50)
    (d / "sub").mkdir()
    nested = d / "sub" / "x.txt"
    nested.write_text("nested\n")
    os.utime(nested, (BASE_MTIME, BASE_MTIME))
    # the nested file counts toward the total
    assert glean.describe(".config/newtool/")["count_mtime"] == "206:1700000050"
    entry = cm_entry(".config/newtool/", "skip", "206:1700000050")
    assert run(home, "scan", [entry])["counts"]["resurfaced"] == 0
    os.utime(nested, (BASE_MTIME + 900, BASE_MTIME + 900))
    r = run(home, "scan", [entry])
    assert paths(r, "resurfaced") == [".config/newtool/"]
    assert r["resurfaced"][0]["count_mtime"] == "206:1700000900"
    assert r["resurfaced"][0]["previous"] == {"verdict": "skip", "decided": TODAY, "reason": "content changed"}


def _vanish_after_first_stat(monkeypatch, vanished: Path) -> None:
    """Let the first stat() on `vanished` succeed (rglob's own is_file()
    filtering), then raise on every later one - the file is still present
    when listed but gone by the time describe()'s own loop stats it."""
    real_stat = Path.stat
    calls = {"n": 0}

    def flaky_stat(self, *a, **kw):
        if self == vanished:
            calls["n"] += 1
            if calls["n"] > 1:
                raise FileNotFoundError(2, "No such file or directory", str(self))
        return real_stat(self, *a, **kw)

    monkeypatch.setattr(Path, "stat", flaky_stat)


def test_describe_over_cap_dir_ignores_file_that_vanishes_during_mtime_stat(home, monkeypatch):
    # race: rglob lists the file, then it is removed before describe() stats it
    d = make_dir(home, ".config/newtool", 205, BASE_MTIME + 50)
    _vanish_after_first_stat(monkeypatch, d / "f100.txt")
    c = glean.describe(".config/newtool/")
    assert c["count_mtime"] == "205:1700000050"


def test_describe_small_dir_ignores_file_that_vanishes_during_size_sum(home, monkeypatch):
    # same race on the under-cap, total-size path
    d = make_dir(home, ".config/newtool", 5, BASE_MTIME + 50)
    _vanish_after_first_stat(monkeypatch, d / "f000.txt")
    c = glean.describe(".config/newtool/")
    assert "sha256" in c


@pytest.mark.parametrize("stored", [{"count_mtime": "5:1700000050"}, {"sha256": "0" * 64}])
def test_volatile_entry_resurfaces_when_candidate_has_no_fingerprint(home, stored):
    # under the file cap but over MAX_FILE bytes in total: describe() yields no fingerprint
    d = make_dir(home, ".config/newtool", 5, BASE_MTIME + 50)
    (d / "f000.txt").write_text("a" * 1_100_000)
    os.utime(d / "f000.txt", (BASE_MTIME, BASE_MTIME))
    c = glean.describe(".config/newtool/")
    assert "sha256" not in c and "count_mtime" not in c
    entry = {"path": ".config/newtool/", "verdict": "skip", "decided": TODAY, **stored}
    for _ in range(2):  # never settles, scan after scan
        r = run(home, "scan", [entry])
        assert paths(r, "resurfaced") == [".config/newtool/"]
        assert r["resurfaced"][0]["previous"] == {"verdict": "skip", "decided": TODAY, "reason": "content changed"}


@pytest.mark.parametrize("stored", ["205:1700000049", "2050:1700000050", "05:1700000050",
                                    "205:17000000500", "205:1700000050.0"])
def test_over_cap_dir_resurfaces_on_near_miss_count_mtime(home, stored):
    make_dir(home, ".config/newtool", 205, BASE_MTIME + 50)
    entry = cm_entry(".config/newtool/", "skip", stored)
    assert paths(run(home, "scan", [entry]), "resurfaced") == [".config/newtool/"]


@pytest.mark.parametrize("days,resurfaces", [(181, True), (179, False)])
def test_over_cap_count_mtime_entry_expires_after_180_days(home, days, resurfaces):
    make_dir(home, ".config/newtool", 205, BASE_MTIME + 50)
    decided = (date.today() - timedelta(days=days)).isoformat()
    entry = cm_entry(".config/newtool/", "skip", "205:1700000050", decided)
    r = run(home, "scan", [entry])
    if resurfaces:
        assert paths(r, "resurfaced") == [".config/newtool/"]
        assert r["resurfaced"][0]["previous"] == {
            "verdict": "skip", "decided": decided, "reason": "decision older than 180 days"}
    else:
        assert r["counts"]["resurfaced"] == 0


@pytest.mark.parametrize("verdict", ["skip", "machine"])
def test_volatile_verdict_validates_and_settles_with_only_count_mtime(home, verdict):
    make_dir(home, ".config/newtool", 205, BASE_MTIME + 50)
    make_dir(home, ".config/othertool", 230, BASE_MTIME + 777)
    baseline_settled = run(home, "scan", [])["counts"]["settled"]
    entries = [cm_entry(".config/newtool/", verdict, "205:1700000050"),
               cm_entry(".config/othertool/", verdict, "230:1700000777")]
    cfg, loaded = glean.load_ledgers(write_ledger(home, entries))
    assert [e for e in loaded if e["path"] in {".config/newtool/", ".config/othertool/"}] == entries
    r = glean.cmd_scan(cfg, loaded)
    assert r["counts"]["resurfaced"] == 0
    assert r["counts"]["settled"] == baseline_settled + 2
    # swap the stored fingerprints: each directory now disagrees and must resurface
    swapped = [cm_entry(".config/newtool/", verdict, "230:1700000777"),
               cm_entry(".config/othertool/", verdict, "205:1700000050")]
    assert sorted(paths(run(home, "scan", swapped), "resurfaced")) == [".config/newtool/", ".config/othertool/"]


@pytest.mark.parametrize("verdict", ["skip", "machine"])
def test_legacy_sha256_entry_validates_and_resurfaces_once_dir_is_over_cap(home, verdict):
    d = make_dir(home, ".config/newtool", 200, BASE_MTIME + 50)
    fp = glean.describe(".config/newtool/")["sha256"]
    entry = {"path": ".config/newtool/", "verdict": verdict, "decided": TODAY, "sha256": fp}
    assert run(home, "scan", [entry])["counts"]["resurfaced"] == 0
    for i in range(200, 205):
        (d / f"f{i:03d}.txt").write_text(f"{i}\n")
    cfg, loaded = glean.load_ledgers(write_ledger(home, [entry]))  # sha256 alone still validates
    r = glean.cmd_scan(cfg, loaded)
    assert paths(r, "resurfaced") == [".config/newtool/"]
    assert r["resurfaced"][0]["previous"] == {"verdict": verdict, "decided": TODAY, "reason": "content changed"}
    assert "count_mtime" in r["resurfaced"][0] and "sha256" not in r["resurfaced"][0]


@pytest.mark.parametrize("n,fingerprint", [(5, "sha256"), (200, "sha256"), (201, "count_mtime")])
def test_dir_fingerprint_switches_from_sha256_to_count_mtime_only_past_cap(home, n, fingerprint):
    make_dir(home, ".config/newtool", n, BASE_MTIME + 50)
    c = glean.describe(".config/newtool/")
    other = {"sha256", "count_mtime"} - {fingerprint}
    assert c.get(fingerprint) and not other & c.keys()
    if fingerprint == "count_mtime":
        assert c["count_mtime"] == f"{n}:1700000050"


@pytest.mark.parametrize("verdict", ["skip", "machine"])
def test_small_dir_sha256_entry_behaves_as_before(home, verdict):
    d = make_dir(home, ".config/newtool", 5, BASE_MTIME + 50)
    fp = glean.describe(".config/newtool/")["sha256"]
    entry = {"path": ".config/newtool/", "verdict": verdict, "decided": TODAY, "sha256": fp}
    for _ in range(2):
        assert run(home, "scan", [entry])["counts"]["resurfaced"] == 0
    # content change with the mtime pinned: the small-dir hash still catches it
    (d / "f002.txt").write_text("changed\n")
    os.utime(d / "f002.txt", (BASE_MTIME, BASE_MTIME))
    r = run(home, "scan", [entry])
    assert paths(r, "resurfaced") == [".config/newtool/"]
    assert "count_mtime" not in r["resurfaced"][0]


@pytest.mark.parametrize("fingerprint", [{}, {"count_mtime": None}, {"sha256": ""}])
@pytest.mark.parametrize("verdict", ["skip", "machine"])
def test_volatile_entry_without_any_fingerprint_is_refused(home, verdict, fingerprint):
    # a falsy fingerprint value counts the same as an absent key
    entry = {"path": ".config/newtool/", "verdict": verdict, "decided": TODAY, **fingerprint}
    with pytest.raises(SystemExit) as exc:
        glean.load_ledgers(write_ledger(home, [entry]))
    assert str(exc.value.code) == "glean: volatile entry .config/newtool/ needs sha256 or count_mtime"
    r = run_cli(home, write_ledger(home, [entry]), "scan")
    assert r.returncode != 0
    assert "Traceback" not in r.stderr
    assert "glean: volatile entry .config/newtool/ needs sha256 or count_mtime" in r.stderr


def test_stable_entry_needs_no_fingerprint(home):
    entry = {"path": ".config/newtool/", "verdict": "noise", "decided": TODAY}
    _, loaded = glean.load_ledgers(write_ledger(home, [entry]))
    assert entry in loaded
