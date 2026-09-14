"""The per-attempt artifacts `evidence.verify` asks of a restored bundle.

An attempt record proves which stages ran, and each stage that ran left files
beside the record: the prompt and status for every attempt, the baseline's
output and exit code (and the sealed record it was measured against, once it
was a valid baseline), the observed patch, and each gate's output and exit
code. A bundle that lost one of them is not whole. Clone directories are
reconstructible and never checked.
"""
import json
from collections.abc import Callable
from pathlib import Path

from eval_harness.records import GATE_KEYS, is_valid_baseline, validate_record


def check_artifacts(lines: list[str], where: Path, prefix: str, record: dict,
                    note: Callable[..., None]) -> None:
    """Report each artifact `record` implies but `where` lacks, and a sealed.json
    the record contract rejects; `note` is how a finding lands in `lines`."""
    names = ["prompt.txt", "status.txt"]
    if record["baseline"] is not None:
        names += ["baseline.txt", "baseline.rc"]
        if is_valid_baseline(record["baseline"]):
            names.append("sealed.json")
    if record["changed"] is not None:
        names.append("diff.patch")
    for label in GATE_KEYS:
        if record["gates"][label] is not None:
            names += ["%s.txt" % label, "%s.rc" % label]
    for name in names:
        if not (where / name).is_file():
            note(lines, "%s/%s" % (prefix, name), "missing")
    if (where / "sealed.json").is_file():
        try:
            validate_record("sealed", json.loads((where / "sealed.json").read_bytes()))
        except (OSError, ValueError) as exc:
            note(lines, prefix + "/sealed.json", "invalid", str(exc))
