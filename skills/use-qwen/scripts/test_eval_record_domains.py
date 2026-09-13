"""Tests for the run, pretask, sealed and server field domains, and native clone paths.

Every path here is a literal string: the contract judges a clone by shape, never
by the host it is read on, so these cases run unskipped on any platform.
"""
import pytest

from eval_harness import records

from eval_harness_record_helpers import pretask_record, run_record, sealed_record, server_record
from test_eval_records import attempt

SHA256 = "c" * 64
NATIVE_ABSOLUTE = [
    "/tmp/eval/clone",
    "C:\\a\\evidence\\runs\\r1\\1-cmd1-a1\\clone",
    "C:/a/evidence/clone",
    "d:\\x",
    "E:\\build\\clone",
    "z:/x",
    "\\\\srv\\share\\evidence\\clone",
    "\\\\nas01\\builds\\clone",
]
NOT_ABSOLUTE = ["clones/3", "relative\\path", "C:relative", "", "C:", None, 7, "\\clone",
                "1:\\x", "::/x", " :/x", "\\\\", "\\\\srv", "\\\\srv\\"]
# Not a digest: wrong alphabet, wrong length either way, a word, the wrong
# sentinel, and the shapes int(value, 16) would still parse.
NOT_A_DIGEST = ["z" * 64, "c" * 65, "c" * 63, "banana", "x", SHA256.upper(), "ABSENT",
                "0x" + "c" * 62, "-" + "c" * 63, " " + "c" * 63, "c" * 31 + "_" + "c" * 32]


def _field_path(exc) -> str:
    """The part of a RecordError message before the value: the field it names."""
    return str(exc.value).split(": ", 1)[0]
ALL_NULL_KEYS = {"run": records.RUN_KEYS, "pretask": records.PRETASK_KEYS,
                 "sealed": records.SEALED_KEYS}


def task(**over):
    base = run_record()["tasks"][0]
    base.update(over)
    return base


def engine(**over):
    base = run_record()["engines"][0]
    base.update(over)
    return base


def rejects(kind, record, field):
    """validate_record raises a RecordError whose field path names `field`.

    The path, not the whole message: the message ends with the value's repr,
    and a whole-record repr carries every key name of the record.
    """
    with pytest.raises(records.RecordError) as exc:
        records.validate_record(kind, record)
    assert field in _field_path(exc), str(exc.value)


# --- the builders and the restore fixture ---------------------------------


@pytest.mark.parametrize("kind, record", [
    ("run", run_record()),
    ("pretask", pretask_record()),
    ("sealed", sealed_record()),
    ("server", server_record()),
])
def test_each_builder_yields_a_valid_record_of_its_kind(kind, record):
    assert records.validate_record(kind, record) is None


def test_the_restore_fixture_run_record_is_contract_valid():
    # what eval_harness_evidence_helpers._build_run writes to runs/r1/run.json
    assert records.validate_record("run", run_record(run_id="r1")) is None


# --- native absolute paths --------------------------------------------------


@pytest.mark.parametrize("path", NATIVE_ABSOLUTE)
def test_accepts_a_native_absolute_clone_from_either_platform(path):
    assert records.validate_record("attempt", attempt(clone=path)) is None


@pytest.mark.parametrize("path", NATIVE_ABSOLUTE)
def test_accepts_a_native_absolute_task_repo_from_either_platform(path):
    assert records.validate_record("run", run_record(tasks=[task(repo=path)])) is None


@pytest.mark.parametrize("path", NOT_ABSOLUTE)
def test_rejects_a_clone_that_is_not_an_absolute_path(path):
    rejects("attempt", attempt(clone=path), "clone")


@pytest.mark.parametrize("path", NOT_ABSOLUTE)
def test_rejects_a_task_repo_that_is_not_an_absolute_path(path):
    rejects("run", run_record(tasks=[task(repo=path)]), "tasks")


# --- all-null records -------------------------------------------------------


@pytest.mark.parametrize("kind", sorted(ALL_NULL_KEYS))
def test_rejects_an_all_null_record_naming_a_field(kind):
    with pytest.raises(records.RecordError) as exc:
        records.validate_record(kind, dict.fromkeys(ALL_NULL_KEYS[kind]))
    assert any(key in _field_path(exc) for key in ALL_NULL_KEYS[kind]), str(exc.value)


def test_accepts_an_all_null_server_block():
    null_server = dict.fromkeys(records.SERVER_KEYS)
    assert records.validate_record("server", null_server) is None
    assert records.validate_record("run", run_record(server=null_server)) is None


# --- pretask and sealed -----------------------------------------------------


@pytest.mark.parametrize("kind", ["pretask", "sealed"])
@pytest.mark.parametrize("override, field", [
    ({"head_sha": None}, "head_sha"),
    ({"head_sha": 7}, "head_sha"),
    ({"head_sha": ""}, "head_sha"),
    ({"writable": {"src\\calc.py": SHA256}}, "writable"),
    ({"writable": {"/calc.py": SHA256}}, "writable"),
    ({"writable": {"": SHA256}}, "writable"),
    ({"writable": {"calc.py": None}}, "writable"),
    ({"writable": {"calc.py": 7}}, "writable"),
    ({"writable": [SHA256]}, "writable"),
    ({"oracle": {"tests\\test_calc.py": "absent"}}, "oracle"),
    ({"oracle": {"/test_calc.py": "absent"}}, "oracle"),
    ({"oracle": {"test_calc.py": None}}, "oracle"),
    ({"oracle": {"test_calc.py": 7}}, "oracle"),
    ({"oracle": ["test_calc.py"]}, "oracle"),
] + [({"writable": {"calc.py": bad}}, "writable") for bad in NOT_A_DIGEST]
  + [({"oracle": {"test_calc.py": bad}}, "oracle") for bad in NOT_A_DIGEST])
def test_rejects_an_out_of_domain_template_field(kind, override, field):
    rejects(kind, pretask_record(**override), field)


@pytest.mark.parametrize("kind", ["pretask", "sealed"])
@pytest.mark.parametrize("override", [
    {"writable": {"calc.py": "absent"}},
    {"writable": {"calc.py": SHA256, "src/pkg/util.py": "absent"}},
    {"oracle": {"tests/test_calc.py": SHA256}},
])
def test_accepts_a_hashed_or_absent_slash_form_template_path(kind, override):
    assert records.validate_record(kind, pretask_record(**override)) is None


# --- run ----------------------------------------------------------------------


@pytest.mark.parametrize("override, field", [
    ({"schema_version": 2}, "schema_version"),
    ({"schema_version": "1"}, "schema_version"),
    ({"schema_version": None}, "schema_version"),
    ({"schema_version": True}, "schema_version"),
    ({"schema_version": 1.0}, "schema_version"),
    ({"run_id": ""}, "run_id"),
    ({"run_id": None}, "run_id"),
    ({"run_id": 1}, "run_id"),
    ({"started": "2026-09-13 12:00:00"}, "started"),
    ({"started": "2026-09-13T12:00:00"}, "started"),
    ({"started": "2026-09-13T12:00:00+00:00"}, "started"),
    ({"started": "2026-09-13T12:00:00.500Z"}, "started"),
    ({"started": "Tuesday"}, "started"),
    ({"started": "YYYY-MM-DDThh:mm:ssZ"}, "started"),
    ({"started": None}, "started"),
    ({"config": []}, "config"),
    ({"config": None}, "config"),
    ({"engines": [engine(id="cmd3")]}, "engines"),
    ({"engines": [dict(engine(), extra=None)]}, "engines"),
    ({"engines": [{"id": "cmd1"}]}, "engines"),
    ({"engines": [engine(command=None)]}, "engines"),
    ({"engines": [engine(command="")]}, "engines"),
    ({"engines": engine()}, "engines"),
    ({"tasks": [task(id="1")]}, "tasks"),
    ({"tasks": [task(id=True)]}, "tasks"),
    ({"tasks": [task(slug="")]}, "tasks"),
    ({"tasks": [task(slug=None)]}, "tasks"),
    ({"tasks": [task(kind="one-file")]}, "tasks"),
    ({"tasks": [task(repo="relative/repo")]}, "tasks"),
    ({"tasks": [task(writable=["b.py", "a.py"])]}, "tasks"),
    ({"tasks": [task(writable=["src\\a.py"])]}, "tasks"),
    ({"tasks": [task(oracle=["/test_calc.py"])]}, "tasks"),
    ({"tasks": [task(oracle=["tests/b.py", "tests/a.py"])]}, "tasks"),
    ({"tasks": [task(prompt_sha256="A" * 64)]}, "tasks"),
    ({"tasks": [task(prompt_sha256="a" * 63)]}, "tasks"),
    ({"tasks": [task(prompt_sha256="z" * 64)]}, "tasks"),
    ({"tasks": [task(prompt_sha256="a" * 65)]}, "tasks"),
    ({"tasks": [task(prompt_sha256="banana")]}, "tasks"),
    # the template map's "absent" sentinel is not a prompt digest
    ({"tasks": [task(prompt_sha256="absent")]}, "tasks"),
    ({"tasks": [dict(task(), extra=None)]}, "tasks"),
    ({"tasks": [{k: v for k, v in task().items() if k != "slug"}]}, "tasks"),
    ({"tasks": task()}, "tasks"),
    ({"versions": []}, "versions"),
    ({"versions": {"pi": 7}}, "versions"),
    ({"server": None}, "server"),
    ({"server": {k: v for k, v in server_record().items() if k != "n_ctx"}}, "server"),
    ({"server": server_record(n_ctx="131072")}, "server"),
    ({"server": server_record(n_ctx=131072.5)}, "server"),
    ({"server": server_record(supports_reasoning_effort="yes")}, "server"),
    ({"server": server_record(supports_reasoning_effort=1)}, "server"),
])
def test_rejects_an_out_of_domain_run_field(override, field):
    rejects("run", run_record(**override), field)


@pytest.mark.parametrize("override", [
    {"engines": [{"id": name, "command": "x"} for name in ("qwen", "sonnet", "cmd1", "cmd2")]},
    {"tasks": [task(kind="multi-file", writable=["a.py", "b.py"], oracle=[])]},
    {"tasks": [task(), task(id=2, slug="other", writable=["src/pkg/b.py"])]},
    {"config": {"nested": [1, {"x": None}], "flag": True}},
    {"versions": {"pi": "0.9.1", "claude": None}},
    {"server": server_record(n_ctx=131072, model_alias="qwen3-coder-30b", build_info="b6000",
                             sampling={"temperature": 0.7}, supports_reasoning_effort=True,
                             declared_effort="high", metadata_error="404")},
])
def test_accepts_every_value_the_run_domains_permit(override):
    assert records.validate_record("run", run_record(**override)) is None


# --- server -------------------------------------------------------------------


@pytest.mark.parametrize("override, field", [
    ({"n_ctx": "131072"}, "n_ctx"),
    ({"n_ctx": True}, "n_ctx"),
    ({"n_ctx": 131072.5}, "n_ctx"),
    ({"model_alias": 7}, "model_alias"),
    ({"build_info": 7}, "build_info"),
    ({"sampling": [0.7]}, "sampling"),
    ({"supports_reasoning_effort": "yes"}, "supports_reasoning_effort"),
    ({"supports_reasoning_effort": 1}, "supports_reasoning_effort"),
    ({"supports_reasoning_effort": 0}, "supports_reasoning_effort"),
    ({"declared_effort": 7}, "declared_effort"),
    ({"metadata_error": 404}, "metadata_error"),
])
def test_rejects_an_out_of_domain_server_field(override, field):
    rejects("server", server_record(**override), field)


@pytest.mark.parametrize("record", [
    server_record(n_ctx=131072, model_alias="qwen3-coder-30b", build_info="b6000",
                  sampling={"temperature": 0.7}, supports_reasoning_effort=False,
                  declared_effort="high", metadata_error="404"),
    # the shape eval_harness_run_helpers._spy_engine_probes builds: two fields set, rest null
    dict(dict.fromkeys(records.SERVER_KEYS), model_alias="spy r1", declared_effort="high"),
])
def test_accepts_a_server_block_with_any_field_null(record):
    assert records.validate_record("server", record) is None
