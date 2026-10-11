#!/usr/bin/env python3
"""Deterministic half of the glean skill.

  glean.py scan          untracked candidates in $HOME minus settled ledger verdicts
  glean.py check-staged  safety gate over what is staged in the dotfiles repo

Both read the local ledger (default ~/.local/state/glean/ledger.local.json),
whose "config" block names the bare repo and the public ledger. Output is JSON
on stdout. Secret prescreen hits carry keyword and line number, never values.
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import json
import re
import subprocess
import sys
from datetime import date, timedelta
from pathlib import Path

HOME = Path.home()
DEFAULT_LEDGER = HOME / ".local/state/glean/ledger.local.json"
VOLATILE = {"skip", "machine"}
STABLE = {"never", "noise", "link", "encrypted"}
RESURFACE_AFTER = timedelta(days=180)
MAX_FILE = 1_000_000
MAX_DIR_FILES = 200
LOCAL_BIN_MAX = 100_000

SOFT = re.compile(
    r"api[_-]?key|secret|token|passw|bearer|private[_-]?key|oauth|client_id|credential",
    re.I,
)
HARD = re.compile(
    r"BEGIN [A-Z ]*PRIVATE KEY|gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9_-]{20,}"
    r"|AKIA[0-9A-Z]{16}|xox[abpr]-[A-Za-z0-9-]{10,}"
)
NOISE_HINT = re.compile(
    r"cache|log|histor|session|state|\.lock$|\.sock$|tmp|backup|\.bak|\.db(-wal|-shm)?$|__pycache__",
    re.I,
)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return {}
    except json.JSONDecodeError as e:
        sys.exit(f"glean: {path} is not valid JSON: {e}")


def load_ledgers(local_path: Path) -> tuple[dict, list[dict]]:
    local = load_json(local_path)
    cfg = local.get("config")
    if not cfg or "git_dir" not in cfg:
        sys.exit(
            f"glean: no config in {local_path}. First run: create it with "
            '{"config": {"git_dir": "~/<bare-repo>", "public_ledger": "~/<path>.json"}, "entries": []}'
        )
    entries = list(local.get("entries", []))
    if cfg.get("public_ledger"):
        entries += load_json(Path(cfg["public_ledger"]).expanduser()).get("entries", [])
    for e in entries:
        v = e.get("verdict")
        if v not in VOLATILE | STABLE:
            sys.exit(f"glean: unknown verdict {v!r} for {e.get('path')}")
        if v in VOLATILE and not e.get("sha256"):
            sys.exit(f"glean: volatile entry {e.get('path')} needs sha256")
    return cfg, entries


def git_dir(cfg: dict) -> Path:
    return Path(cfg["git_dir"]).expanduser()


def git(cfg: dict, *args: str) -> str:
    cmd = ["git", f"--git-dir={git_dir(cfg)}", f"--work-tree={HOME}", *args]
    res = subprocess.run(cmd, cwd=HOME, capture_output=True, text=True)
    if res.returncode != 0:
        sys.exit(f"glean: git {' '.join(args[:2])} failed: {res.stderr.strip()}")
    return res.stdout


def matches(path: str, pattern: str) -> bool:
    if any(c in pattern for c in "*?["):
        return fnmatch.fnmatch(path.rstrip("/"), pattern.rstrip("/"))
    if pattern.endswith("/"):
        return path.startswith(pattern) or path + "/" == pattern
    return path.rstrip("/") == pattern


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def is_text(p: Path) -> bool:
    with p.open("rb") as f:
        return b"\0" not in f.read(8192)


def scan_lines(text: str) -> list[tuple[int, str]]:
    """(line, keyword) per hit. Never returns the matched value."""
    hits = []
    for n, line in enumerate(text.splitlines(), 1):
        if m := HARD.search(line):
            hits.append((n, "HARD:" + m.group(0)[:4]))
        elif m := SOFT.search(line):
            hits.append((n, m.group(0).lower()))
    return hits


def prescreen(p: Path, rel: str) -> list[dict]:
    try:
        if p.stat().st_size > MAX_FILE or not is_text(p):
            return []
        return [{"file": rel, "line": n, "keyword": k} for n, k in scan_lines(p.read_text(errors="replace"))]
    except OSError as e:
        return [{"file": rel, "line": 0, "keyword": f"unreadable: {e.strerror}"}]


def describe(rel: str) -> dict:
    p = HOME / rel.rstrip("/")
    c: dict = {"path": rel, "hints": [], "secret_hits": []}
    if NOISE_HINT.search(rel):
        c["hints"].append("noise?")
    if p.is_symlink():
        c.update(kind="symlink", target=str(p.readlink()))
        c["hints"].append("link?")
        return c
    if p.is_dir():
        files = [f for f in sorted(p.rglob("*")) if f.is_file() and not f.is_symlink()]
        c.update(kind="dir", files=len(files), soft_hits=0)
        for f in files[:MAX_DIR_FILES]:
            for hit in prescreen(f, str(f.relative_to(HOME))):
                if hit["keyword"].startswith("HARD:"):
                    c["secret_hits"].append(hit)
                else:
                    c["soft_hits"] += 1
        if len(files) > MAX_DIR_FILES:
            c["hints"].append(f"prescreen capped at {MAX_DIR_FILES} files")
        elif sum(f.stat().st_size for f in files) <= MAX_FILE:
            # ponytail: dir fingerprint = hash of (relpath, file hash); lets skip/machine cover a whole new dir
            c["sha256"] = hashlib.sha256(
                "".join(f"{f.relative_to(p)}\0{sha256(f)}\n" for f in files).encode()
            ).hexdigest()
        return c
    c.update(kind="file", size=p.stat().st_size)
    if c["size"] <= MAX_FILE:
        c["sha256"] = sha256(p)
    c["secret_hits"] = prescreen(p, rel)
    return c


def local_bin_scripts() -> list[str]:
    """~/.local is commonly ignored wholesale; surface hand-written scripts there."""
    d = HOME / ".local/bin"
    if not d.is_dir():
        return []
    return [
        str(f.relative_to(HOME))
        for f in sorted(d.iterdir())
        if f.is_file() and not f.is_symlink() and f.stat().st_size <= LOCAL_BIN_MAX and is_text(f)
    ]


def mapped_secrets() -> set[str]:
    mapping = HOME / ".gitsecret/paths/mapping.cfg"
    if not mapping.exists():
        return set()
    return {ln.split(":", 1)[0] for ln in mapping.read_text().splitlines() if ln.strip()}


def secret_gaps(cfg: dict, untracked: list[str]) -> dict:
    mapped = mapped_secrets()
    tracked = git(cfg, "ls-files", ":(top,glob)**/*.secret", ":(top,glob)*.secret").splitlines()
    blobs = set(tracked) | {p for p in untracked if p.endswith(".secret")}
    return {
        "unmapped_blobs": sorted(p for p in blobs if p[: -len(".secret")] not in mapped),
        "mapped_without_tracked_blob": sorted(m for m in mapped if m + ".secret" not in tracked),
    }


def cmd_scan(cfg: dict, entries: list[dict]) -> dict:
    out = git(
        cfg, "ls-files", "-o", "--exclude-standard", "--directory", "--no-empty-directory", "--",
        ":(top,glob).*", ":(top,glob).*/**", ":(top,glob)bin/**",
        ":(top,exclude).Trash/**", f":(top,exclude){git_dir(cfg).relative_to(HOME)}/**",
    )
    paths = sorted(set(out.splitlines()) | set(local_bin_scripts()))
    link_roots = [Path(r).expanduser().resolve() for r in cfg.get("link_roots", [])]
    today = date.today()
    candidates, resurfaced, settled = [], [], 0
    for rel in paths:
        entry = next((e for e in entries if matches(rel, e["path"])), None)
        p = HOME / rel.rstrip("/")
        if (entry and entry["verdict"] in STABLE) or (
            p.is_symlink() and any(p.resolve().is_relative_to(r) for r in link_roots)
        ):
            settled += 1
            continue
        c = describe(rel)
        if entry:  # volatile: quiet only while unchanged and recent
            changed = c.get("sha256") != entry["sha256"]
            stale = today - date.fromisoformat(entry["decided"]) > RESURFACE_AFTER
            if not changed and not stale:
                settled += 1
                continue
            c["previous"] = {
                "verdict": entry["verdict"],
                "decided": entry["decided"],
                "reason": "content changed" if changed else "decision older than 180 days",
            }
            resurfaced.append(c)
            continue
        candidates.append(c)
    return {
        "candidates": candidates,
        "resurfaced": resurfaced,
        "secret_gaps": secret_gaps(cfg, paths),
        "counts": {"new": len(candidates), "resurfaced": len(resurfaced), "settled": settled},
    }


def cmd_check_staged(cfg: dict, entries: list[dict]) -> dict:
    """Hard fail on anything that must never be pushed; report soft keyword hits."""
    hard, soft = [], []
    numstat = git(cfg, "diff", "--cached", "--numstat", "--diff-filter=ACMR").splitlines()
    mapped = mapped_secrets()
    for row in numstat:
        added, _, path = row.split("\t", 2)
        if path in mapped:
            hard.append({"path": path, "why": "plaintext of a git-secret file"})
        if any(e["verdict"] == "never" and matches(path, e["path"]) for e in entries):
            hard.append({"path": path, "why": "ledger verdict never"})
        if path.endswith(".secret"):
            if added != "-":
                hard.append({"path": path, "why": ".secret blob is text, not encrypted"})
            continue
        blob = subprocess.run(
            ["git", f"--git-dir={git_dir(cfg)}", "show", f":{path}"], capture_output=True, check=True
        ).stdout
        if b"\0" in blob[:8192]:
            continue
        for n, k in scan_lines(blob.decode(errors="replace")):
            if k.startswith("HARD:"):
                hard.append({"path": path, "line": n, "why": "credential pattern " + k[5:]})
            else:
                soft.append({"path": path, "line": n, "keyword": k})
    return {"ok": not hard, "hard": hard, "soft": soft, "staged": len(numstat)}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["scan", "check-staged"])
    ap.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    args = ap.parse_args(argv)
    cfg, entries = load_ledgers(args.ledger.expanduser())
    result = cmd_scan(cfg, entries) if args.command == "scan" else cmd_check_staged(cfg, entries)
    json.dump(result, sys.stdout, indent=1)
    print()
    return 1 if args.command == "check-staged" and not result["ok"] else 0


if __name__ == "__main__":
    sys.exit(main())
