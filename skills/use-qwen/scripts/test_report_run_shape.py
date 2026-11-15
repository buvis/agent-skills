"""run.json fields that render() dereferences: each is refused as a ValueError, never a traceback."""
import json

import pytest

import run_eval_harness
from eval_harness import records

# The last six names are fixtures: pytest resolves them from this module's own
# namespace, so they have to be imported even though nothing here calls them.
from eval_harness_run_helpers import (
    drifted,
    pair,
    rounds,
    scratch,
    shim,
    slow,
    vetted,
)
from test_report_audit import _names_field, _run_json_refusal


def _set(path, value):
    def mutate(run):
        target = run
        for step in path[:-1]:
            target = target[step]
        target[path[-1]] = value
    return mutate


def _pop(path):
    def mutate(run):
        target = run
        for step in path[:-1]:
            target = target[step]
        target.pop(path[-1])
    return mutate


_FIRST_SERVER_KEY = records.SERVER_KEYS[0]

RUN_JSON_UNRENDERABLE = [
    pytest.param(_set(("tasks", 0, "id"), [1]), "id", id="task-id-is-a-list"),
    pytest.param(_set(("tasks", 0, "id"), "1"), "id", id="task-id-is-a-string"),
    pytest.param(_pop(("tasks", 0, "slug")), "slug", id="task-missing-slug"),
    pytest.param(_pop(("tasks", 0, "repo")), "repo", id="task-missing-repo"),
    pytest.param(_pop(("tasks", 0, "kind")), "kind", id="task-missing-kind"),
    pytest.param(_set(("engines", 0, "id"), 7), "id", id="engine-id-is-not-a-string"),
    pytest.param(_pop(("config",)), "config", id="run-missing-config"),
    pytest.param(_pop(("versions",)), "versions", id="run-missing-versions"),
    pytest.param(_pop(("server",)), "server", id="run-missing-server"),
    pytest.param(_set(("config",), []), "config", id="config-is-a-list"),
    pytest.param(_set(("versions",), "x"), "versions", id="versions-is-a-string"),
    pytest.param(_set(("server",), None), "server", id="server-is-null"),
    pytest.param(_pop(("server", _FIRST_SERVER_KEY)), _FIRST_SERVER_KEY, id="server-missing-a-key"),
]


def _mutated(round_, mutate) -> str:
    run = json.loads((round_.run / "run.json").read_text(encoding="utf-8"))
    mutate(run)
    return json.dumps(run)


@pytest.mark.parametrize("mutate, field", RUN_JSON_UNRENDERABLE)
def test_render_refuses_a_run_json_missing_a_field_the_renderer_reads(rounds, mutate, field):
    round_ = rounds("r1")

    message = _run_json_refusal(round_, _mutated(round_, mutate))

    assert round_.run.name in message
    assert _names_field(message, field)


@pytest.mark.parametrize("mutate, field", RUN_JSON_UNRENDERABLE)
def test_main_render_refuses_an_unrenderable_run_json_with_no_traceback(
    rounds, capsys, mutate, field,
):
    round_ = rounds("r1")
    run_path = round_.run / "run.json"
    original = run_path.read_text(encoding="utf-8")
    run_path.write_text(_mutated(round_, mutate), encoding="utf-8")
    try:
        exit_code = run_eval_harness.main(["render", str(round_.root), "--run-id", round_.run.name])
    finally:
        run_path.write_text(original, encoding="utf-8")
    stderr = capsys.readouterr().err

    assert exit_code == 1
    assert stderr.startswith("render refused: ")
    assert "Traceback" not in stderr
    assert _names_field(stderr, field)
