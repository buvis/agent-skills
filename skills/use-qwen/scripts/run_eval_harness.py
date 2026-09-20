#!/usr/bin/env python3
"""Command-line shim of the qwen evaluation harness: vet, verify and run.

Every flag resolves here and travels to eval_harness.attempt as a value, so a
caller of the package sees the same run a shell caller does.
"""
import argparse
import math
import sys
from pathlib import Path

# The package sits beside this file; `main` imports it once the path is set.
sys.path.insert(0, str(Path(__file__).resolve().parent))

SHAPES = ("description", "tdd")


def _positive(text: str) -> float:
    try:
        value = float(text)
    except ValueError:
        value = math.nan
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError("%r is not a finite positive number of seconds" % text)
    return value


def _csv(text: str) -> list[str]:
    return [item for item in text.split(",") if item]


def _run_id(text: str) -> str:
    from eval_harness import admission

    problem = admission.check_run_id(text)
    if problem is not None:
        raise argparse.ArgumentTypeError(problem)
    return text


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="run_eval_harness.py")
    commands = parser.add_subparsers(dest="command", required=True)
    vet = commands.add_parser("vet", help="seal and qualify every task under tasks/")
    vet.add_argument("evidence_dir", type=Path)
    vet.add_argument("--gate-bound", type=_positive, default=1800.0, metavar="SECONDS")
    vet.add_argument("--shapes", type=_csv, default=None, metavar="description[,tdd]")
    verify = commands.add_parser("verify", help="check an evidence directory's records")
    verify.add_argument("evidence_dir", type=Path)
    render = commands.add_parser(
        "render", help="render evidence.md, report.md and audit-queue.md for a run")
    render.add_argument("evidence_dir", type=Path)
    render.add_argument("--run-id", type=_run_id, required=True)
    run = commands.add_parser("run", help="run every ready task through the given engines")
    run.add_argument("evidence_dir", type=Path)
    run.add_argument("--run-id", type=_run_id, required=True)
    run.add_argument("--engines", type=_csv, required=True, metavar="a[,b]")
    run.add_argument("--shape", choices=SHAPES, required=True)
    run.add_argument("--bound", type=_positive, required=True, metavar="SECONDS")
    run.add_argument("--gate-bound", type=_positive, default=1800.0, metavar="SECONDS")
    run.add_argument("--alternate", action="store_true")
    run.add_argument("--retry-discarded", choices=("harness-only", "none"), default="none")
    run.add_argument("--server-reasoning-effort", metavar="LABEL")
    run.add_argument("--qwen-provider")
    run.add_argument("--qwen-model")
    run.add_argument("--sonnet-model")
    run.add_argument("--usage-limit-cmd", type=Path, metavar="PATH")
    return parser


def main(argv: list[str]) -> int:
    from eval_harness import attempt, engines

    args = _parser().parse_args(argv)
    if args.command == "vet":
        return attempt.vet(args.evidence_dir, args.gate_bound, shapes=args.shapes)
    if args.command == "verify":
        return attempt.verify(args.evidence_dir)
    if args.command == "render":
        from eval_harness import report

        report.render(args.evidence_dir, args.run_id)
        return 0
    settings = engines.EngineSettings(
        qwen_provider=args.qwen_provider, qwen_model=args.qwen_model,
        sonnet_model=args.sonnet_model, usage_limit_cmd=args.usage_limit_cmd,
        server_reasoning_effort=args.server_reasoning_effort)
    config = {
        "run_id": args.run_id, "engines": args.engines, "shape": args.shape, "bound": args.bound,
        "gate_bound": args.gate_bound, "alternate": args.alternate,
        "retry_discarded": args.retry_discarded,
        "server_reasoning_effort": args.server_reasoning_effort,
        "qwen_provider": args.qwen_provider, "qwen_model": args.qwen_model,
        "sonnet_model": args.sonnet_model,
        "usage_limit_cmd": None if args.usage_limit_cmd is None else str(args.usage_limit_cmd),
    }
    return attempt.run(args.evidence_dir, args.run_id, args.engines, args.shape, args.bound,
                       args.gate_bound, alternate=args.alternate,
                       retry_discarded=args.retry_discarded, settings=settings, config=config)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
