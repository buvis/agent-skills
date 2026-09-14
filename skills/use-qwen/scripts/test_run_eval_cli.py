"""Parser and gate-order tests for the run_eval_harness CLI.

The bounds: `--bound` and `--gate-bound` take only a finite number of seconds
greater than zero, so no timeout the harness promises can be infinite or
undefined. The gates: on a completed round the production driver ran every
attempt's baseline, then the gates its shape requires and no other, in the
contract's order, and recorded each. Every round runs against a copy of the
bundle vetted once per module (P13).
"""
import argparse
from pathlib import Path

import pytest

import run_eval_harness
from eval_harness import records

# The last seven names are fixtures: pytest resolves them from this module's own
# namespace, so they have to be imported even though nothing here calls them.
from eval_harness_run_helpers import (
    DESCRIPTION_SITES,
    _attempts,
    _ids,
    _logged_cwds,
    drifted,
    pair,
    rounds,
    scratch,
    shim,
    slow,
    vetted,
)

# Values no bound accepts: not finite (in every spelling float() knows, and the overflow
# `1e999` that float() reads as inf without the letters), not positive, or not a number.
REFUSED_BOUNDS = [
    "inf", "Infinity", "+inf", "INF", "infinity", "-inf", "1e999", "-1e999",
    "nan", "NaN", "NAN", "-nan",
    "0", "0.0", "-0", "-1", "-2", "abc",
]
# Values every bound parses, with the float each names: plain, fractional, exponent
# (either case, either sign), explicit sign, a bare leading or trailing dot, a literal
# longer than any other here, and the largest finite magnitude, so neither a table of
# literals nor a grammar shaped like one can stand in for float().
ACCEPTED_BOUNDS = {
    "2": 2.0, "0.5": 0.5, "1800": 1800.0, "1e3": 1000.0,
    "3": 3.0, "0.001": 0.001, "7.25e2": 725.0, "+2": 2.0, "1e308": 1e308,
    "1e-3": 0.001, "1E3": 1000.0, ".5": 0.5, "5.": 5.0, "2592000": 2592000.0,
    "3600.75": 3600.75,
}
# The two bound flags, by the `args` attribute each lands in.
BOUND_FLAGS = ["bound", "gate_bound"]
# Per shape: the completed round, the sites one attempt's commands run in (in execution
# order: the baseline first, then the gates the shape requires), and the gates recorded
# as a command result rather than null.
SHAPES = {
    "description": ("r1", DESCRIPTION_SITES, ("gate", "own", "ablate")),
    "tdd": ("tdd", ("baseline-clone", "gate-clone"), ("gate",)),
}


def _option(flag: str, value: str) -> list:
    """`--bound value` (or `--gate-bound value`) as argv tokens.

    argparse reads `-inf` (and `-nan`, `-1e999`) as a flag of its own and refuses
    `--bound -inf` for lacking an argument, so a value that starts with `-` but is no
    negative integer is joined as `--bound=-inf`: then the value reaches the type, and the
    type's refusal is what is seen. `-1`, `-2`, `-0` argparse takes as negative-number
    arguments, so they reach the type through the plain two-token form.
    """
    option = "--" + flag.replace("_", "-")
    if value.startswith("-") and not value[1:].isdigit():
        return [f"{option}={value}"]
    return [option, value]


def _argv(flag: str, directory: Path, value: str) -> list:
    """A `run` argv carrying `--bound value`, or a `vet` argv carrying `--gate-bound value`."""
    if flag == "bound":
        return [
            "run", str(directory), "--run-id", "r1", "--engines", "pass", "--shape", "tdd",
            *_option(flag, value),
        ]
    return ["vet", str(directory), *_option(flag, value)]


def _parse(argv: list):
    return run_eval_harness._parser().parse_args(argv)


# -- the bounds ---------------------------------------------------------------


@pytest.mark.parametrize("flag", BOUND_FLAGS)
@pytest.mark.parametrize("value", REFUSED_BOUNDS)
def test_a_bound_that_is_not_a_finite_positive_number_is_refused(tmp_path, capsys, flag, value):
    with pytest.raises(SystemExit) as stop:
        _parse(_argv(flag, tmp_path, value))

    err = capsys.readouterr().err
    assert stop.value.code == 2
    # the refusal names the flag, the value it would not take, and why: the one reason
    # every refusal carries, not argparse's fallback for a bare ValueError, which leaks
    # the type function's name and says nothing about what a bound is. It travels
    # argparse's own error path (the usage line, then `error: argument <flag>: <why>`),
    # not a hand-written stderr line and a bare SystemExit.
    option = "--" + flag.replace("_", "-")
    assert err.startswith("usage: run_eval_harness.py"), err
    assert "error: argument %s: %r is not a finite positive number of seconds" % (
        option, value) in err, err
    assert "_positive" not in err, err


@pytest.mark.parametrize("value", REFUSED_BOUNDS)
def test_the_bound_type_refuses_with_the_argparse_error_argparse_reports(value):
    # The type is what argparse calls, so its refusal is an ArgumentTypeError naming the
    # value and the reason; anything else (a SystemExit of its own, a bare ValueError)
    # takes the wrong exit path.
    with pytest.raises(argparse.ArgumentTypeError) as refused:
        run_eval_harness._positive(value)

    assert "%r is not a finite positive number of seconds" % value == str(refused.value)


@pytest.mark.parametrize("flag", BOUND_FLAGS)
@pytest.mark.parametrize("value", list(ACCEPTED_BOUNDS))
def test_a_finite_positive_bound_parses_to_its_float(tmp_path, flag, value):
    args = _parse(_argv(flag, tmp_path, value))

    parsed = getattr(args, flag)
    assert isinstance(parsed, float)
    assert parsed == ACCEPTED_BOUNDS[value]


def test_a_gate_bound_left_out_defaults_to_thirty_minutes_on_run_and_on_vet(tmp_path):
    run_args = _parse(_argv("bound", tmp_path, "2"))
    vet_args = _parse(["vet", str(tmp_path)])

    assert run_args.bound == 2.0
    assert run_args.gate_bound == 1800.0
    assert vet_args.gate_bound == 1800.0


# -- the gates on the production path ----------------------------------------


@pytest.mark.parametrize("shape", list(SHAPES))
def test_every_attempt_runs_its_baseline_then_the_shape_s_gates_in_order_and_no_other(
    rounds, vetted, shape
):
    run_id, sites, _ = SHAPES[shape]
    round_ = rounds(run_id)

    assert round_.rc == 0
    assert _ids(round_) == ["1-cmd1-a1", "1-cmd2-a1"]
    # P15's log in execution order: one attempt's sites, then the next attempt's, never
    # interleaved; inside an attempt the baseline, then gate, own, ablate as far as the
    # shape requires. A site missing from `sites` has no line at all: that gate never ran.
    assert _logged_cwds(round_, vetted.log) == [
        str((round_.run / attempt_id / site).resolve())
        for attempt_id in _ids(round_)
        for site in sites
    ]


@pytest.mark.parametrize("shape", list(SHAPES))
def test_every_record_holds_a_result_per_required_gate_and_null_for_the_rest(rounds, shape):
    run_id, _, required = SHAPES[shape]
    round_ = rounds(run_id)
    attempts = _attempts(round_)

    assert list(attempts) == _ids(round_)
    for attempt_id, record in attempts.items():
        gates = record["gates"]
        # the record is written with its keys sorted, so the file pins the set of gate
        # labels; the order they ran in is the log's to pin
        assert sorted(gates) == sorted(records.GATE_KEYS), attempt_id
        for label in records.GATE_KEYS:
            if label in required:
                assert records.validate_record("command_result", gates[label]) is None, (
                    attempt_id, label,
                )
            else:
                assert gates[label] is None, (attempt_id, label)
