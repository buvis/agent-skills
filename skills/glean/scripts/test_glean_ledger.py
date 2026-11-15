"""Ledger validation of glean: a malformed local or public ledger stops the
run with a message naming the file, never a traceback.

Split from test_glean.py for size; the `home` fixture and CLI helpers come
from there.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_glean import TODAY, home, run_cli, write_ledger_with_public


def write_raw(path: Path, data) -> Path:
    path.write_text(json.dumps(data))
    return path


def test_load_ledgers_rejects_list_root_instead_of_crashing(home):
    ledger = write_raw(home / "ledger.json", [])
    r = run_cli(home, ledger, "scan")
    assert r.returncode == 1, r.stdout
    assert "Traceback" not in r.stderr
    assert str(ledger) in r.stderr


def test_load_ledgers_rejects_other_list_root_shape_instead_of_crashing(home):
    # a different shape of the same mistake (a hand-edited list, not an empty one)
    ledger = write_raw(home / "other.json", [{"config": {}}])
    r = run_cli(home, ledger, "scan")
    assert r.returncode == 1, r.stdout
    assert "Traceback" not in r.stderr
    assert str(ledger) in r.stderr


def test_load_ledgers_rejects_non_object_entry_among_valid_ones(home):
    ledger = write_raw(home / "ledger.json", {
        "config": {"git_dir": str(home / ".dots")},
        "entries": [
            {"path": ".ok", "verdict": "never", "decided": TODAY},
            "x",
            {"path": ".also-ok", "verdict": "noise", "decided": TODAY},
        ],
    })
    r = run_cli(home, ledger, "scan")
    assert r.returncode == 1, r.stdout
    assert "Traceback" not in r.stderr
    assert ".ok" not in r.stderr  # the valid entries are not what's being blamed
    assert str(ledger) in r.stderr or "entries" in r.stderr.lower()


@pytest.mark.parametrize("verdict", [["skip"], {"skip": 1}], ids=["list", "object"])
def test_load_ledgers_rejects_a_non_string_verdict_instead_of_crashing(home, verdict):
    ledger = write_raw(home / "ledger.json", {
        "config": {"git_dir": str(home / ".dots")},
        "entries": [{"path": ".odd-verdict", "verdict": verdict, "decided": TODAY}],
    })
    r = run_cli(home, ledger, "scan")
    assert r.returncode == 1, r.stdout
    assert "Traceback" not in r.stderr
    assert ".odd-verdict" in r.stderr
    assert str(ledger) in r.stderr


def test_load_ledgers_rejects_volatile_entry_missing_decided(home):
    ledger = write_raw(home / "ledger.json", {
        "config": {"git_dir": str(home / ".dots")},
        "entries": [{"path": ".missing-decided", "verdict": "skip", "sha256": "abc123"}],
    })
    r = run_cli(home, ledger, "scan")
    assert r.returncode == 1, r.stdout
    assert "Traceback" not in r.stderr
    assert ".missing-decided" in r.stderr


def test_load_ledgers_rejects_volatile_entry_with_invalid_decided_date(home):
    ledger = write_raw(home / "ledger.json", {
        "config": {"git_dir": str(home / ".dots")},
        "entries": [{"path": ".bad-date", "verdict": "skip", "decided": "yesterday", "sha256": "abc123"}],
    })
    r = run_cli(home, ledger, "scan")
    assert r.returncode == 1, r.stdout
    assert "Traceback" not in r.stderr
    assert ".bad-date" in r.stderr


def test_load_ledgers_rejects_volatile_entry_with_malformed_iso_date(home):
    # near-miss: looks like an ISO date but has an out-of-range month/day
    ledger = write_raw(home / "ledger.json", {
        "config": {"git_dir": str(home / ".dots")},
        "entries": [{"path": ".bad-iso", "verdict": "machine", "decided": "2026-13-45", "sha256": "abc123"}],
    })
    r = run_cli(home, ledger, "scan")
    assert r.returncode == 1, r.stdout
    assert "Traceback" not in r.stderr
    assert ".bad-iso" in r.stderr


def test_load_ledgers_rejects_git_dir_outside_supported_home_layout(home):
    outside = home.parent / "outside-dots"
    ledger = write_raw(home / "ledger.json", {
        "config": {"git_dir": str(outside)},
        "entries": [],
    })
    r = run_cli(home, ledger, "scan")
    assert r.returncode == 1, r.stdout
    assert "Traceback" not in r.stderr
    assert str(outside) in r.stderr


def test_load_ledgers_rejects_list_root_in_public_ledger(home):
    public = write_raw(home / "public.json", [])
    ledger = write_ledger_with_public(home, public)
    r = run_cli(home, ledger, "scan")
    assert r.returncode == 1, r.stdout
    assert "Traceback" not in r.stderr
    assert str(public) in r.stderr


def test_load_ledgers_rejects_non_object_entry_in_public_ledger(home):
    public = write_raw(home / "public.json", {
        "entries": [
            {"path": ".pub-ok", "verdict": "never", "decided": TODAY},
            "x",
            {"path": ".pub-also-ok", "verdict": "noise", "decided": TODAY},
        ],
    })
    ledger = write_ledger_with_public(home, public)
    r = run_cli(home, ledger, "scan")
    assert r.returncode == 1, r.stdout
    assert "Traceback" not in r.stderr
    assert ".pub-ok" not in r.stderr


def test_load_ledgers_rejects_public_ledger_volatile_entry_missing_decided(home):
    public = write_raw(home / "public.json", {
        "entries": [{"path": ".pub-missing-decided", "verdict": "skip", "sha256": "abc123"}],
    })
    ledger = write_ledger_with_public(home, public)
    r = run_cli(home, ledger, "scan")
    assert r.returncode == 1, r.stdout
    assert "Traceback" not in r.stderr
    assert ".pub-missing-decided" in r.stderr


def test_load_ledgers_rejects_public_ledger_volatile_entry_with_invalid_date(home):
    public = write_raw(home / "public.json", {
        "entries": [{"path": ".pub-bad-date", "verdict": "machine", "decided": "not-a-date", "sha256": "abc123"}],
    })
    ledger = write_ledger_with_public(home, public)
    r = run_cli(home, ledger, "scan")
    assert r.returncode == 1, r.stdout
    assert "Traceback" not in r.stderr
    assert ".pub-bad-date" in r.stderr


def test_load_ledgers_still_accepts_valid_entries_alongside_validation(home):
    # control: the new validation must not reject a well-formed ledger
    (home / ".config" / "tool.toml").write_text("theme = 'dark'\n")
    ledger = write_raw(home / "ledger.json", {
        "config": {"git_dir": str(home / ".dots")},
        "entries": [{"path": ".netrc", "verdict": "never", "decided": TODAY}],
    })
    r = run_cli(home, ledger, "scan")
    assert r.returncode == 0, r.stderr
    assert "Traceback" not in r.stderr
    body = json.loads(r.stdout)
    assert ".config/tool.toml" in [c["path"] for c in body["candidates"]]


def test_load_ledgers_rejects_non_dict_config_instead_of_crashing(home):
    ledger = write_raw(home / "ledger.json", {"config": ["git_dir"], "entries": []})
    r = run_cli(home, ledger, "scan")
    assert r.returncode == 1, r.stdout
    assert "Traceback" not in r.stderr
    assert str(ledger) in r.stderr


def test_load_ledgers_rejects_non_string_git_dir_instead_of_crashing(home):
    ledger = write_raw(home / "ledger.json", {"config": {"git_dir": 5}, "entries": []})
    r = run_cli(home, ledger, "scan")
    assert r.returncode == 1, r.stdout
    assert "Traceback" not in r.stderr
    assert str(ledger) in r.stderr


@pytest.mark.parametrize("bad", [5, None, ["~/x"], {"a": 1}])
def test_load_ledgers_rejects_non_string_link_roots_element_instead_of_crashing(home, bad):
    ledger = write_raw(
        home / "ledger.json",
        {"config": {"git_dir": str(home / ".dots"), "link_roots": ["~/ok", bad]}, "entries": []},
    )
    r = run_cli(home, ledger, "scan")
    assert r.returncode == 1, r.stdout
    assert "Traceback" not in r.stderr
    assert str(ledger) in r.stderr
    assert "link_roots" in r.stderr


def test_scan_accepts_relative_git_dir_under_home(home):
    ledger = write_raw(home / "ledger.json", {"config": {"git_dir": ".dots"}, "entries": []})
    r = run_cli(home, ledger, "scan")
    assert "Traceback" not in r.stderr, r.stderr
    assert r.returncode == 0, r.stderr


def test_load_ledgers_rejects_entry_missing_path_instead_of_crashing(home):
    (home / ".untracked-file").write_text("x\n")
    ledger = write_raw(home / "ledger.json", {
        "config": {"git_dir": str(home / ".dots")},
        "entries": [{"verdict": "never", "sha256": "abc123", "decided": TODAY}],
    })
    r = run_cli(home, ledger, "scan")
    assert r.returncode == 1, r.stdout
    assert "Traceback" not in r.stderr
    assert str(ledger) in r.stderr
