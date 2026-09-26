#!/usr/bin/env python3
"""Inject data.json (+ optional epics.json) into the SPA template.

Usage: build.py [--dir DIR] [--out FILE]
--dir defaults to ~/.local/share/agents/portfolio-brief; --out defaults to <dir>/portfolio-brief.html
"""
import argparse
import json
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent.parent / "assets/template.html"
PLACEHOLDER = "__PORTFOLIO_PAYLOAD__"


def _load_json_or_exit(path):
    try:
        return json.loads(path.read_text())
    except json.JSONDecodeError as e:
        sys.exit(f"{path}: {e}")


def _load_data(workdir):
    data_file = workdir / "data.json"
    if not data_file.is_file():
        sys.exit(f"missing {data_file} — run collect.py first")
    return _load_json_or_exit(data_file)


def _load_epics(workdir):
    epics_file = workdir / "epics.json"
    if not epics_file.is_file():
        print(f"WARN: {epics_file} not found — building without epic grouping", file=sys.stderr)
        return {"summary": "", "repos": {}}
    return _load_json_or_exit(epics_file)


def _load_prev(workdir):
    prev_file = workdir / "data-prev.json"
    if not prev_file.is_file():
        return None
    return _load_json_or_exit(prev_file)


def _load_history(workdir):
    hist_file = workdir / "history.jsonl"
    history = []
    if hist_file.is_file():
        numbered = [
            (i, l)
            for i, l in enumerate(hist_file.read_text().splitlines(), start=1)
            if l.strip()
        ]
        for i, l in numbered[-60:]:
            try:
                history.append(json.loads(l))
            except json.JSONDecodeError as e:
                print(f"WARN: history.jsonl line {i} skipped: {e}", file=sys.stderr)
    return history


def main():
    ap = argparse.ArgumentParser()
    default_dir = Path.home() / ".local/share/agents/portfolio-brief"
    ap.add_argument("--dir", default=str(default_dir))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    workdir = Path(args.dir)
    out = Path(args.out) if args.out else workdir / "portfolio-brief.html"

    data = _load_data(workdir)
    epics = _load_epics(workdir)
    prev = _load_prev(workdir)
    history = _load_history(workdir)

    template = TEMPLATE.read_text()
    if PLACEHOLDER not in template:
        sys.exit(f"template {TEMPLATE} has no {PLACEHOLDER} marker")
    # < keeps any commit subject from moving the tokenizer into script-data-double-escaped state
    payload = json.dumps({"data": data, "epics": epics, "prev": prev,
                          "history": history}).replace("<", "\\u003c")
    out.write_text(template.replace(PLACEHOLDER, payload))
    print(f"wrote {out} ({out.stat().st_size // 1024} kB)")


if __name__ == "__main__":
    main()
