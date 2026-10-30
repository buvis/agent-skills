#!/usr/bin/env python3
"""Trash-first cleanup for globally ignored docs/dev/tmp assets."""

import argparse
import os
import re
import shutil
import sys
import time
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from stat import S_ISREG

DAY = 86400
PRD_NUM = re.compile(r"(?<!\d)(\d{5})(?!\d)")
TRASH_DIR = ".trash"


def find_stores(home: Path) -> dict[str, tuple[Path, Path]]:
    """Return every existing docs/dev/tmp store in Go-style checkouts."""
    stores: dict[str, tuple[Path, Path]] = {}
    seen: set[str] = set()

    def add(label: str, repo_root: Path, store: Path) -> None:
        real = Path(os.path.realpath(store))
        if real.is_dir() and str(real) not in seen:
            seen.add(str(real))
            stores[label] = (real, repo_root)

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
                    add(label, repo, store)
    add("~/.claude", home / ".claude", home / ".claude" / "docs" / "dev" / "tmp")
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


def resolve_repo_root(path: Path) -> Path:
    """Repo root for a --repo argument, without collapsing a symlinked store."""
    candidate = path / "docs" / "dev" / "tmp"
    if candidate.is_dir() or candidate.is_symlink():
        return path
    return Path(os.path.abspath(path)).parents[2]


def _live_prd_numbers_from_root(repo_root: Path) -> set[str]:
    prds = repo_root / "docs" / "dev" / "project-management" / "prds"
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


def live_prd_numbers(store: Path) -> set[str]:
    """Numbers of backlog, wip, and hold PRDs beside this tmp store."""
    return _live_prd_numbers_from_root(store.parents[2])


def is_repo_unit(dirs: list[str], files: list[str]) -> bool:
    """Return whether a directory contains a repository marker."""
    return ".git" in dirs or ".git" in files


def newest_file_mtime(directory: Path) -> float:
    """Return the newest regular-file mtime, or the directory mtime if empty."""
    mtimes = []
    for base, _dirs, files in os.walk(directory, followlinks=False):
        for name in files:
            try:
                entry_stat = (Path(base) / name).lstat()
            except OSError:
                continue
            if S_ISREG(entry_stat.st_mode):
                mtimes.append(entry_stat.st_mtime)
    return max(mtimes, default=directory.stat().st_mtime)


def walk_store(store: Path) -> Iterator[tuple[Path, float]]:
    """Yield relative path and mtime for files and repository units outside .trash."""
    for base, dirs, files in os.walk(store, followlinks=False):
        if Path(base) == store:
            dirs[:] = [name for name in dirs if name != TRASH_DIR]
        elif is_repo_unit(dirs, files):
            yield Path(base).relative_to(store), newest_file_mtime(Path(base))
            dirs[:] = []
            continue
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


def path_has_unsafe_characters(path: Path) -> str | None:
    """Return a reason if any path component has a tab or any line-break
    character (any `str.splitlines` separator), else None."""
    for part in path.parts:
        if "\t" in part:
            return f"{part!r}: contains a tab"
        if "\n" in part:
            return f"{part!r}: contains a newline"
        if part.splitlines() != [part]:
            return f"{part!r}: contains a line break"
    return None


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
    directories = []
    for base, dirs, files in os.walk(store, followlinks=False):
        directory = Path(base)
        if directory == store:
            dirs[:] = [name for name in dirs if name != TRASH_DIR]
            continue
        if is_repo_unit(dirs, files):
            dirs[:] = []
            continue
        directories.append(directory)
    for directory in reversed(directories):
        try:
            directory.rmdir()
        except OSError:
            pass


def empty_old_trash(store: Path, now: float, days: float, keep: str | None = None) -> int:
    """Remove batches older than days, never the batch named keep.

    Manifest rows for successfully removed batches are dropped; rows for
    retained batches, malformed historical rows, and rows whose batch
    failed to delete are left untouched.
    """
    trash = store / TRASH_DIR
    if not trash.is_dir():
        return 0
    removed = 0
    removed_batches: set[str] = set()
    for batch in trash.iterdir():
        if not batch.is_dir() or batch.name == keep:
            continue
        try:
            batch_time = time.mktime(time.strptime(batch.name, "%Y-%m-%d"))
        except ValueError:
            continue
        if (now - batch_time) / DAY > days:
            try:
                shutil.rmtree(batch)
            except OSError:
                continue
            removed += 1
            removed_batches.add(batch.name)

    if removed_batches:
        manifest = trash / "manifest.tsv"
        if manifest.is_file():
            with manifest.open("r", encoding="utf-8", newline="") as handle:
                text = handle.read()
            lines = text.split("\n")
            if lines and lines[-1] == "":
                lines.pop()
            kept_lines = []
            for line in lines:
                fields = line.split("\t")
                if len(fields) >= 4 and fields[0] in removed_batches:
                    continue
                kept_lines.append(line)
            if len(kept_lines) != len(lines):
                try:
                    text = "".join(f"{line}\n" for line in kept_lines)
                    tmp = manifest.with_name(manifest.name + ".tmp")
                    tmp.write_text(text, encoding="utf-8")
                    os.replace(tmp, manifest)
                except OSError:
                    pass
    return removed


def process_store(label: str, store: Path, args, now: float, repo_root: Path | None = None) -> Counter:
    batch = time.strftime("%Y-%m-%d", time.localtime(now))
    live = live_prd_numbers(store) if repo_root is None else _live_prd_numbers_from_root(repo_root)
    counts: Counter = Counter()
    candidates: list[Path] = []
    refused: list[tuple[Path, str]] = []
    for rel, mtime in sorted(walk_store(store)):
        rule = classify(rel, mtime, live, now, args)
        if rule == "stale-temp":
            reason = path_has_unsafe_characters(rel)
            if reason is not None:
                counts["refused-unsafe-path"] += 1
                refused.append((rel, reason))
                continue
        counts[rule] += 1
        if rule == "stale-temp":
            candidates.append(rel)
            if args.apply:
                trash_file(store, rel, batch)

    emptied = 0
    if args.apply:
        prune_empty_dirs(store)
        emptied = empty_old_trash(store, now, args.empty_trash_days, keep=batch)
        (store / TRASH_DIR / batch).mkdir(parents=True, exist_ok=True)

    print(
        f"{label}: trash={len(candidates)} live-linked={counts['live-linked']} "
        f"fresh={counts['fresh']} trash-batches-emptied={emptied} "
        f"stale-temp={counts['stale-temp']} refused-unsafe-path={counts['refused-unsafe-path']}"
    )
    if args.verbose:
        for rel in candidates:
            print(f"  stale-temp: {rel.as_posix()}")
        for rel, reason in refused:
            print(f"  refused-unsafe-path: {rel.as_posix()} ({reason})")
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
                stores[str(path)] = (resolve_store(path), resolve_repo_root(path))
            except ValueError as error:
                print(f"error: {error}", file=sys.stderr)
                return 2

    total = Counter()
    for label, (store, repo_root) in stores.items():
        total.update(process_store(label, store, args, now, repo_root=repo_root))
    mode = "APPLIED" if args.apply else "DRY-RUN (use --apply)"
    print(f"{mode}: trash={total['stale-temp']} across {len(stores)} store(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
