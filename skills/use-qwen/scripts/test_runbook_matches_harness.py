"""The eval runbook names every harness subcommand, flag, and vetting key.

Section 7 ("Harness rounds") is the operator's reference for running
run_eval_harness.py by hand. If the CLI grows a subcommand, flag, or the
record contract grows a vetting key, the runbook must name it or an operator
following it will not know it exists.
"""
import argparse
import re
from pathlib import Path

import run_eval_harness
from eval_harness import records


def _section_seven() -> str:
    path = Path(__file__).resolve().parents[1] / "references" / "eval-runbook.md"
    lines = path.read_text().splitlines()
    start = next((i for i, line in enumerate(lines) if line == "## 7. Harness rounds"), None)
    assert start is not None, "eval-runbook.md lost the '## 7. Harness rounds' heading"
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    return "\n".join(lines[start:end])


def _subparsers_action() -> argparse.Action:
    parser = run_eval_harness._parser()
    return next(action for action in parser._actions if action.choices is not None)


def _subparser(name: str) -> argparse.ArgumentParser:
    return _subparsers_action().choices[name]


def _long_flags(subparser: argparse.ArgumentParser):
    for action in subparser._actions:
        for option in action.option_strings:
            if option.startswith("--") and option != "--help":
                yield option


def test_runbook_names_every_harness_subcommand():
    section = _section_seven()
    for name in _subparsers_action().choices:
        assert f"run_eval_harness.py {name} " in section, name


def test_runbook_names_every_vet_flag():
    section = _section_seven()
    for flag in _long_flags(_subparser("vet")):
        assert re.search(rf"{re.escape(flag)}(?![\w-])", section), flag


def test_runbook_names_every_run_flag():
    section = _section_seven()
    for flag in _long_flags(_subparser("run")):
        assert re.search(rf"{re.escape(flag)}(?![\w-])", section), flag


def test_runbook_lists_every_vetting_key():
    section = _section_seven()
    for key in records.VETTING_KEYS:
        assert f"`{key}`" in section, key
