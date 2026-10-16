#!/usr/bin/env python3
"""Inspect repositories, seed an empty one, and check a small structural subset.

CLI entry point. Production logic lives in the sibling module ``structure_lib``;
the disposable-fixture self-test lives in ``structure_selftest`` and is imported
lazily only when ``--selftest`` is requested. All three files sit in this
directory, so running ``python3 .../structure_repo.py`` keeps them importable
regardless of the working directory.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from structure_lib import (
    check_many,
    check_repo,
    discover_repositories,
    inspect_repo,
    resolve_target,
    scaffold_repo,
)


def run_main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true", help="exercise disposable fixtures")
    commands = parser.add_subparsers(dest="command")
    for name in ("inspect", "check", "scaffold"):
        command = commands.add_parser(name)
        command.add_argument("target", help="repository path")
        if name in ("inspect", "check"):
            command.add_argument(
                "--git-dir", help="explicit Git directory for a bare-backed worktree"
            )
        if name == "check":
            command.add_argument(
                "--deviation",
                action="append",
                default=[],
                metavar="CHECK=REASON",
                help="waive one failing check as a Fit deviation; repeatable",
            )
            command.add_argument(
                "--not-applicable",
                action="append",
                default=[],
                metavar="CHECK=REASON",
                dest="not_applicable",
                help="mark one failing check out of scope for this repo kind; repeatable",
            )
            command.add_argument(
                "--nested",
                action="store_true",
                help="also check the Claude bridge for each maintained nested AGENTS.md scope",
            )
        if name == "scaffold":
            command.add_argument("--name", required=True)
            command.add_argument("--purpose", required=True)
            command.add_argument(
                "--apply", action="store_true", help="write the seed; default previews"
            )
    sweep = commands.add_parser("check-all")
    sweep.add_argument(
        "roots",
        nargs="+",
        help="parent directories of sibling repositories, or repository paths",
    )
    sweep.add_argument(
        "--nested",
        action="store_true",
        help="also check each maintained nested AGENTS.md scope in every repository",
    )
    args = parser.parse_args()
    try:
        if args.selftest:
            if args.command:
                parser.error("--selftest cannot be combined with a repository command")
            from structure_selftest import run_selftest

            return run_selftest()
        if not args.command:
            parser.error("select inspect, check, check-all or scaffold, or use --selftest")
        if args.command == "check-all":
            roots = [Path(value).expanduser().resolve() for value in args.roots]
            targets = discover_repositories(roots)
            result = check_many(targets, getattr(args, "nested", False))
            print(json.dumps(result, indent=2, ensure_ascii=True))
            return 1 if result.get("rollup_gate") == "FAIL" else 0
        target = resolve_target(args.target)
        selected_git_dir = getattr(args, "git_dir", None)
        git_dir = Path(selected_git_dir).expanduser().resolve() if selected_git_dir else None
        if args.command == "inspect":
            result = inspect_repo(target, git_dir)
        elif args.command == "check":
            def parse_waivers(items: list[str], label: str) -> dict[str, str]:
                parsed: dict[str, str] = {}
                for item in items:
                    key, sep, reason = item.partition("=")
                    key, reason = key.strip(), reason.strip()
                    if not sep or not key or not reason:
                        raise ValueError(f"Use --{label} CHECK=REASON with a nonempty reason: {item}")
                    if key in parsed:
                        raise ValueError(f"Duplicate {label} for check: {key}")
                    parsed[key] = reason
                return parsed

            deviations = parse_waivers(getattr(args, "deviation", []), "deviation")
            not_applicable = parse_waivers(getattr(args, "not_applicable", []), "not-applicable")
            result = check_repo(
                target, git_dir, deviations, not_applicable, getattr(args, "nested", False)
            )
        else:
            result = scaffold_repo(target, args.name, args.purpose, args.apply)
        print(json.dumps(result, indent=2, ensure_ascii=True))
        return 1 if result.get("structural_gate") == "FAIL" else 0
    except (OSError, ValueError, subprocess.TimeoutExpired) as error:
        print(json.dumps({"status": "ERROR", "error": str(error)}, ensure_ascii=True))
        return 2


if __name__ == "__main__":
    sys.exit(run_main())
