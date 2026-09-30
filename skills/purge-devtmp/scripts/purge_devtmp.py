#!/usr/bin/env python3
"""Trash-first cleanup for globally ignored docs/dev/tmp assets."""

import argparse
import os
import re
import shutil
import sys
import time
from collections import Counter
from pathlib import Path

DAY = 86400
PRD_NUM = re.compile(r"(?<!\d)(\d{5})(?!\d)")
TRASH_DIR = ".trash"


def find_stores(home: Path) -> dict[str, Path]:
    """Return every existing docs/dev/tmp store in Go-style checkouts."""
    stores: dict[str, Path] = {}
    seen: set[str] = set()

    def add(label: str, store: Path) -> None:
        real = Path(os.path.realpath(store))
        if real.is_dir() and str(real) not in seen:
            seen.add(str(real))
            stores[label] = real

    src = home / "git" / "src"
    if src.is_dir():
        for host in sorted(src.iterdir()):
            if not host.is_dir():
                continue
            for org in sorted(host.iterdir()):
                if not org.is_dir():
                    continue
                for repo in sorted(org.iterdir()):
                    store = repo / "docs" / "dev" / "tmp"
                    label = (
                        f"{org.name}/{repo.name}"
                        if host.name == "github.com"
                        else f"{host.name}/{org.name}/{repo.name}"
                    )
                    add(label, store)
    add("~/.claude", home / ".claude" / "docs" / "dev" / "tmp")
    return stores


def resolve_store(path: Path) -> Path:
    """Accept a repo root or its docs/dev/tmp directory, nothing broader."""
    candidate = path / "docs" / "dev" / "tmp"
    if candidate.is_dir() or candidate.is_symlink():
        return Path(os.path.realpath(candidate))
    store = Path(os.path.realpath(path))
    if store.name == "tmp" and store.parent.name == "dev" and store.parent.parent.name == "docs":
        return store
    raise ValueError(f"{path}: not a repo with docs/dev/tmp or a docs/dev/tmp path")


def live_prd_numbers(store: Path) -> set[str]:
    """Numbers of backlog, wip, and hold PRDs beside this tmp store."""
    root = store.parents[2]
    prds = root / "docs" / "dev" / "project-management" / "prds"
    live: set[str] = set()
    for bucket in ("backlog", "wip", "hold"):
        directory = prds / bucket
        if not directory.is_dir():
            continue
        for entry in directory.iterdir():
            match = PRD_NUM.search(entry.name)
            if match:
                live.add(match.group(1))
    return live


def walk_store(store: Path):
    """Yield relative path and mtime for files outside .trash."""
    for base, dirs, files in os.walk(store, followlinks=False):
        if Path(base) == store:
            dirs[:] = [name for name in dirs if name != TRASH_DIR]
        for name in files:
            path = Path(base) / name
            try:
                stat = path.lstat()
            except OSError:
                continue
            yield path.relative_to(store), stat.st_mtime


def classify(rel: Path, mtime: float, live: set[str], now: float, args) -> str:
    """Return live-linked, fresh, or stale-temp."""
    tokens = set(PRD_NUM.findall(rel.as_posix()))
    if tokens & live:
        return "live-linked"
    age = (now - mtime) / DAY
    if age < args.min_age_days or age <= args.age_days:
        return "fresh"
    return "stale-temp"


def _dedup_dest(batch_root: Path, rel: Path) -> Path:
    parts = list(rel.parts)
    for depth, base in enumerate(rel.parts):
        leaf = depth == len(parts) - 1
        number = 1
        while True:
            candidate = batch_root.joinpath(*parts[: depth + 1])
            collision = (
                candidate.exists()
                if leaf
                else candidate.exists() and not candidate.is_dir()
            )
            if not collision:
                break
            number += 1
            parts[depth] = f"{base}-{number}"
    return batch_root.joinpath(*parts)


def trash_file(store: Path, rel: Path, batch: str) -> None:
    destination = _dedup_dest(store / TRASH_DIR / batch, rel)
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(store / rel), str(destination))
    manifest = store / TRASH_DIR / "manifest.tsv"
    with manifest.open("a", encoding="utf-8") as handle:
        handle.write(
            f"{batch}\tstale-temp\t{rel.as_posix()}\t"
            f"{destination.relative_to(store).as_posix()}\n"
        )


def prune_empty_dirs(store: Path) -> None:
    for base, _dirs, _files in os.walk(store, topdown=False):
        directory = Path(base)
        if directory == store or TRASH_DIR in directory.parts:
            continue
        try:
            directory.rmdir()
        except OSError:
            pass


def empty_old_trash(store: Path, now: float, days: float) -> int:
    trash = store / TRASH_DIR
    if not trash.is_dir():
        return 0
    removed = 0
    for batch in trash.iterdir():
        if not batch.is_dir():
            continue
        try:
            batch_time = time.mktime(time.strptime(batch.name, "%Y-%m-%d"))
        except ValueError:
            continue
        if (now - batch_time) / DAY > days:
            shutil.rmtree(batch)
            removed += 1
    return removed


def process_store(label: str, store: Path, args, now: float) -> Counter:
    batch = time.strftime("%Y-%m-%d", time.localtime(now))
    live = live_prd_numbers(store)
    counts: Counter = Counter()
    candidates: list[Path] = []
    for rel, mtime in sorted(walk_store(store)):
        rule = classify(rel, mtime, live, now, args)
        counts[rule] += 1
        if rule == "stale-temp":
            candidates.append(rel)
            if args.apply:
                trash_file(store, rel, batch)

    emptied = 0
    if args.apply:
        prune_empty_dirs(store)
        emptied = empty_old_trash(store, now, args.empty_trash_days)
        (store / TRASH_DIR / batch).mkdir(parents=True, exist_ok=True)

    print(
        f"{label}: trash={len(candidates)} live-linked={counts['live-linked']} "
        f"fresh={counts['fresh']} trash-batches-emptied={emptied}"
    )
    if args.verbose:
        for rel in candidates:
            print(f"  stale-temp: {rel.as_posix()}")
    return counts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Trash-first cleanup for docs/dev/tmp")
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument("--all", action="store_true")
    scope.add_argument("--repo", action="append", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--min-age-days", type=float, default=3)
    parser.add_argument("--age-days", type=float, default=7)
    parser.add_argument("--empty-trash-days", type=float, default=30)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    now = time.time()
    if args.all:
        stores = find_stores(Path.home())
    else:
        stores = {}
        for path in args.repo:
            if not path.exists():
                print(f"error: no such path: {path}", file=sys.stderr)
                return 2
            try:
                stores[str(path)] = resolve_store(path)
            except ValueError as error:
                print(f"error: {error}", file=sys.stderr)
                return 2

    total = Counter()
    for label, store in stores.items():
        total.update(process_store(label, store, args, now))
    mode = "APPLIED" if args.apply else "DRY-RUN (use --apply)"
    print(f"{mode}: trash={total['stale-temp']} across {len(stores)} store(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
