"""Tests for eval_harness/records.py (the record contract)."""
import itertools
import os
import re

import pytest

from eval_harness import records

CLONE = os.path.abspath("/tmp/eval-harness/clone-3")
REASONS = {"prep", "baseline", "harness", "timeout", "usage-limit", "identity", "incomplete"}
EXIT_REASON = re.compile(r"^exit--?[0-9]+$")
ENGINES = ("qwen", "sonnet", "cmd1", "cmd2")
OUTCOMES = ("PASS", "FAIL", "TIMEOUT", "SUSPECT", "DISCARDED")
FAIL_CLASSES = ("test-mutation", "stray-edit", "no-edit", "dropped-a-file", "vacuous-tests",
                "logic-error")
NONZERO_RCS = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 42, 255, 1000, -1)
OFF_DOMAIN = object()  # no field of any record kind may hold this


def command_result(rc=0, timed_out=False, first_failure=None, failure_kind=None, wall_s=1.5):
    return {"rc": rc, "timed_out": timed_out, "first_failure": first_failure,
            "failure_kind": failure_kind, "wall_s": wall_s}


def failing_tests(rc=1):
    return command_result(rc=rc, first_failure="tests/test_a.py::test_x", failure_kind="test")


def usage(**over):
    base = {"input_tokens": 1200, "output_tokens": 340, "cache_read_tokens": 0,
            "cache_write_tokens": 0, "cost_usd": 0.0}
    base.update(over)
    return base


def engine_run(**over):
    base = {"argv": ["pi", "-p", "spec"], "launch": "started", "exit": 0, "timed_out": False,
            "wall_s": 42.0, "identity": "qwen3-coder-30b", "completion": "complete",
            "final_message_bytes": 512, "usage_limit": "clear", "first_edit_s": 4.0,
            "usage": usage()}
    base.update(over)
    return base


def attempt(**over):
    """A tdd attempt with complete evidence, a valid baseline and a passing gate."""
    base = {
        "task": 3, "engine": "qwen", "attempt": 1, "shape": "tdd", "clone": CLONE,
        "prep": {"status": "ok", "differing_paths": []},
        "baseline": failing_tests(),
        "engine_run": engine_run(),
        "validity": "VALID",
        "changed": [{"status": "M", "path": "src/a.py", "old_path": None}],
        "stray": [],
        "oracle_intact": True,
        "dropped": [],
        "gates": {"gate": command_result(rc=0), "own": None, "ablate": None},
        "outcome": "PASS", "class": None,
        "started": "2026-09-07T10:11:12Z", "finished": "2026-09-07T10:14:00Z",
    }
    base.update(over)
    return base


def description_attempt(**over):
    """A description attempt: no oracle, own and ablation gates both required."""
    base = attempt(shape="description", oracle_intact=None,
                   gates={"gate": command_result(rc=0), "own": command_result(rc=0),
                          "ablate": failing_tests()})
    base.update(over)
    return base


def unobserved_attempt(**over):
    """An attempt that positively failed before the helper process was created."""
    base = attempt(
        changed=None, stray=None, dropped=None, oracle_intact=None,
        engine_run=engine_run(launch="not-started", exit=None, wall_s=None, identity=None,
                              completion="unknown", final_message_bytes=None,
                              usage_limit="unchecked", first_edit_s=None,
                              usage=dict.fromkeys(records.USAGE_KEYS)),
        gates={"gate": None, "own": None, "ablate": None},
        validity="DISCARDED:harness", outcome="DISCARDED",
    )
    base.update(over)
    return base


KEYS = {
    "attempt": records.ATTEMPT_KEYS,
    "run": records.RUN_KEYS,
    "pretask": records.PRETASK_KEYS,
    "sealed": records.SEALED_KEYS,
    "vetting": records.VETTING_KEYS,
    "command_result": records.COMMAND_RESULT_KEYS,
    "engine_run": records.ENGINE_RUN_KEYS,
    "usage": records.USAGE_KEYS,
    "server": records.SERVER_KEYS,
}


def sample(kind):
    if kind == "attempt":
        return attempt()
    if kind == "command_result":
        return command_result()
    if kind == "engine_run":
        return engine_run()
    if kind == "usage":
        return usage()
    if kind == "vetting":
        vetting = dict.fromkeys(records.VETTING_KEYS)
        vetting["warmup"] = [command_result(rc=0)]
        vetting["baseline"] = failing_tests()
        vetting["necessity"] = {"src/a.py": {"result": failing_tests(), "holds": True}}
        return vetting
    return dict.fromkeys(KEYS[kind])


def vetting(**over):
    base = sample("vetting")
    base.update(over)
    return base


def is_closed_set_reason(result):
    if result == "VALID":
        return True
    if not result.startswith("DISCARDED:"):
        return False
    reason = result[len("DISCARDED:"):]
    return reason in REASONS or bool(EXIT_REASON.match(reason))


# --- key sets -------------------------------------------------------------


@pytest.mark.parametrize("kind", ["gates", "prep", "Attempt", "", "changed"])
def test_refuses_a_kind_outside_record_kinds(kind):
    assert kind not in records.RECORD_KINDS
    with pytest.raises(records.RecordError):
        records.validate_record(kind, attempt())


@pytest.mark.parametrize("kind", records.RECORD_KINDS)
def test_record_kind_accepts_its_exact_key_set(kind):
    record = sample(kind)
    assert set(record) == set(KEYS[kind])
    assert records.validate_record(kind, record) is None


@pytest.mark.parametrize("kind", records.RECORD_KINDS)
def test_record_kind_refuses_every_missing_key(kind):
    for key in KEYS[kind]:
        short = {k: v for k, v in sample(kind).items() if k != key}
        with pytest.raises(records.RecordError):
            records.validate_record(kind, short)


@pytest.mark.parametrize("kind", records.RECORD_KINDS)
def test_record_kind_refuses_an_extra_key(kind):
    fat = dict(sample(kind), unexpected_key=None)
    with pytest.raises(records.RecordError):
        records.validate_record(kind, fat)


@pytest.mark.parametrize("field, value", [
    ("prep", {"status": "ok"}),
    ("prep", {"status": "ok", "differing_paths": [], "note": None}),
    ("baseline", {k: v for k, v in failing_tests().items() if k != "wall_s"}),
    ("baseline", dict(failing_tests(), stderr=None)),
    ("gates", {"gate": command_result(rc=0), "own": None}),
    ("gates", dict({"gate": command_result(rc=0), "own": None, "ablate": None}, smoke=None)),
    ("gates", {"gate": {k: v for k, v in command_result(rc=0).items() if k != "rc"},
               "own": None, "ablate": None}),
    ("gates", {"gate": command_result(rc=0),
               "own": {k: v for k, v in command_result(rc=0).items() if k != "timed_out"},
               "ablate": None}),
    ("gates", {"gate": command_result(rc=0), "own": None,
               "ablate": dict(command_result(rc=0), stdout=None)}),
    ("engine_run", {k: v for k, v in engine_run().items() if k != "first_edit_s"}),
    ("engine_run", dict(engine_run(), retries=None)),
    ("engine_run", engine_run(usage={k: v for k, v in usage().items() if k != "cost_usd"})),
    ("engine_run", engine_run(usage=dict(usage(), tool_tokens=None))),
])
def test_refuses_a_broken_nested_key_set(field, value):
    with pytest.raises(records.RecordError):
        records.validate_record("attempt", attempt(**{field: value}))


# --- field shapes ---------------------------------------------------------


@pytest.mark.parametrize("override", [
    {"task": "3"},
    {"task": 3.0},
    {"engine": "gemini"},
    {"engine": "qwen3"},
    {"engine": ""},
    {"attempt": 3},
    {"attempt": 0},
    {"attempt": -1},
    {"attempt": 99},
    {"attempt": "1"},
    {"shape": "spec"},
    {"shape": "TDD"},
    {"clone": "clones/3"},
    {"clone": "relative/path"},
    {"clone": ""},
    {"outcome": "OK"},
    {"outcome": "pass"},
    {"outcome": "BANANA"},
    {"class": "logic-error"},
    {"outcome": "SUSPECT", "class": "logic-error"},
    {"outcome": "FAIL"},
    {"outcome": "FAIL", "class": None},
    {"outcome": "FAIL", "class": "wrong-vibes"},
    {"outcome": "FAIL", "class": "LOGIC-ERROR"},
    {"validity": "DISCARDED:teapot"},
    {"validity": "DISCARDED:"},
    {"oracle_intact": 1},
    {"changed": {}},
    {"stray": [42]},
    {"validity": "DISCARDED:banana"},
    {"validity": "discarded:prep"},
    {"started": "2026-09-07 10:11:12"},
    {"started": "2026-09-07T10:11:12"},
    {"started": "2026-09-07T10:11:12+00:00"},
    {"started": "2026-09-07T10:11:12.500Z"},
    {"finished": "yesterday"},
    {"prep": {"status": "mismatch", "differing_paths": []}},
    {"oracle_intact": "yes"},
    {"shape": "description"},
    {"engine_run": engine_run(launch="skipped")},
    {"engine_run": engine_run(completion="done")},
    {"engine_run": engine_run(usage_limit="ok")},
    {"engine_run": engine_run(argv="pi -p spec")},
    {"engine_run": engine_run(usage=usage(input_tokens=-1))},
    {"engine_run": engine_run(usage=usage(input_tokens=1.5))},
    {"engine_run": engine_run(usage=usage(output_tokens=-1))},
    {"engine_run": engine_run(usage=usage(cache_read_tokens=1.5))},
    {"engine_run": engine_run(usage=usage(cost_usd=-0.01))},
    {"gates": {"gate": command_result(rc=0, failure_kind="lint"), "own": None, "ablate": None}},
    {"gates": {"gate": command_result(rc=0), "own": command_result(rc=0, failure_kind="lint"),
               "ablate": None}},
    {"gates": {"gate": command_result(rc=0), "own": None,
               "ablate": command_result(rc="1", failure_kind="test")}},
    {"baseline": command_result(rc=1, failure_kind="lint")},
    {"baseline": command_result(rc="1", failure_kind="test")},
    {"stray": ["docs/x.md", "docs/a.md"]},
    {"stray": [None]},
    {"stray": "docs/x.md"},
    {"dropped": ["src/b.py", "src/a.py"]},
    {"dropped": ["/tmp/eval-harness/clone-3/src/b.py"]},
    {"dropped": ["src\\b.py"]},
])
def test_refuses_an_out_of_domain_field(override):
    with pytest.raises(records.RecordError):
        records.validate_record("attempt", attempt(**override))


@pytest.mark.parametrize("value", ["banana", OFF_DOMAIN])
@pytest.mark.parametrize("key", records.ATTEMPT_KEYS)
def test_refuses_an_unnamed_value_in_any_attempt_field(key, value):
    """No attempt field takes a free string or an arbitrary object: the domains are closed."""
    with pytest.raises(records.RecordError):
        records.validate_record("attempt", attempt(**{key: value}))


@pytest.mark.parametrize("record", (
    [attempt(engine=engine) for engine in ENGINES]
    + [attempt(**{"attempt": n}) for n in (1, 2)]
    + [attempt(), description_attempt()]
    + [attempt(**{"outcome": outcome, "class": None})
       for outcome in OUTCOMES if outcome != "FAIL"]
    + [attempt(**{"outcome": "FAIL", "class": cls}) for cls in FAIL_CLASSES]
    + [attempt(validity="VALID")]
    + [attempt(validity="DISCARDED:%s" % reason) for reason in sorted(REASONS)]
    + [attempt(validity="DISCARDED:exit-%d" % code) for code in (1, 2, 137)]
    + [attempt(oracle_intact=flag) for flag in (True, False)]
    + [attempt(changed=[], stray=[], dropped=[])]
))
def test_accepts_every_value_the_closed_domains_permit(record):
    assert records.validate_record("attempt", record) is None


@pytest.mark.parametrize("kind, record", [
    ("usage", usage(input_tokens=-1)),
    ("usage", usage(output_tokens=-1)),
    ("usage", usage(cache_read_tokens=1.5)),
    ("usage", usage(cost_usd=-0.01)),
    ("engine_run", engine_run(launch="skipped")),
    ("engine_run", engine_run(completion="done")),
    ("engine_run", engine_run(usage_limit="ok")),
    ("engine_run", engine_run(argv="pi -p spec")),
    ("engine_run", engine_run(usage=usage(input_tokens=-1))),
    ("command_result", command_result(failure_kind="lint")),
    ("command_result", command_result(rc="0")),
    ("command_result", command_result(wall_s=-1.0)),
    ("command_result", command_result(timed_out="no")),
    ("command_result", command_result(first_failure=42)),
    ("engine_run", engine_run(identity=42)),
    ("engine_run", engine_run(argv=["pi", 3])),
    ("engine_run", engine_run(exit="0")),
]
    # every declared key of every kind refuses a value no field may hold, so no kind
    # can fall through to "valid" on its key set alone
    + [(kind, dict(sample(kind), **{key: OFF_DOMAIN}))
       for kind in records.RECORD_KINDS for key in KEYS[kind]]
    # and the fixed-domain fields refuse an arbitrary string too
    + [("command_result", dict(command_result(), **{key: "banana"}))
       for key in records.COMMAND_RESULT_KEYS if key != "first_failure"]
    + [("engine_run", dict(engine_run(), **{key: "banana"}))
       for key in records.ENGINE_RUN_KEYS if key != "identity"]
    + [("usage", dict(usage(), **{key: "banana"})) for key in records.USAGE_KEYS])
def test_refuses_an_out_of_domain_field_in_a_standalone_record(kind, record):
    assert kind in records.RECORD_KINDS
    with pytest.raises(records.RecordError):
        records.validate_record(kind, record)


@pytest.mark.parametrize("kind, record", (
    [("engine_run", engine_run(launch=launch)) for launch in ("started", "unknown")]
    + [("engine_run", unobserved_attempt()["engine_run"])]
    + [("engine_run", engine_run(completion=done))
       for done in ("complete", "incomplete", "unknown")]
    + [("engine_run", engine_run(usage_limit=limit))
       for limit in ("clear", "hit", "unchecked")]
    + [("engine_run", engine_run(exit=code)) for code in (None, 0, 1, 137)]
    + [("engine_run", engine_run(identity=None))]
    + [("command_result", command_result(failure_kind=how))
       for how in ("test", "tool", "unknown", None)]
    + [("command_result", command_result(rc=rc)) for rc in (None, 0) + NONZERO_RCS]
    + [("command_result", command_result(timed_out=flag)) for flag in (True, False)]
    + [("command_result", command_result(wall_s=wall_s)) for wall_s in (None, 0, 0.0, 600.0)]
    + [("usage", usage(input_tokens=0, output_tokens=0, cost_usd=0)),
       ("usage", dict.fromkeys(records.USAGE_KEYS))]
))
def test_accepts_every_value_a_nested_record_domain_permits(kind, record):
    assert records.validate_record(kind, record) is None


@pytest.mark.parametrize("over", [
    {"necessity": {"src/a.py": {"result": failing_tests()}}},
    {"necessity": {"src/a.py": {"result": failing_tests(), "holds": True, "why": None}}},
    {"necessity": {"src/a.py": {"result": None, "holds": True}}},
    {"necessity": {"src/a.py": {"result": command_result(rc=0, failure_kind="test"),
                                "holds": True}}},
    {"necessity": {"src/a.py": {"result": command_result(rc=None, failure_kind="test"),
                                "holds": True}}},
    {"necessity": {"src/a.py": {"result": command_result(rc=1, timed_out=True,
                                                         failure_kind="test"), "holds": True}}},
    {"necessity": {"src/a.py": {"result": command_result(rc=1, failure_kind="tool"),
                                "holds": True}}},
    {"necessity": {"src/a.py": {"result": command_result(rc=1, failure_kind=None),
                                "holds": True}}},
    {"necessity": {"src/a.py": {"result": failing_tests(), "holds": "yes"}}},
    {"necessity": {"src/a.py": None}},
    {"necessity": {"src\\a.py": {"result": failing_tests(), "holds": True}}},
    {"necessity": {"/tmp/eval-harness/clone-3/src/a.py": {"result": failing_tests(),
                                                          "holds": True}}},
    {"necessity": [{"result": failing_tests(), "holds": True}]},
    {"necessity": {"src/a.py": {"result": {k: v for k, v in failing_tests().items()
                                           if k != "rc"}, "holds": True}}},
    {"warmup": command_result(rc=0)},
    {"warmup": [command_result(rc=0, failure_kind="lint")]},
    {"warmup": [{k: v for k, v in command_result().items() if k != "wall_s"}]},
    {"warmup": [dict(command_result(), stdout=None)]},
])
def test_refuses_a_malformed_necessity_or_warmup_entry(over):
    with pytest.raises(records.RecordError):
        records.validate_record("vetting", vetting(**over))


@pytest.mark.parametrize("over", [
    {"necessity": {}},
    {"necessity": {"src/a.py": {"result": None, "holds": False}}},
    {"necessity": {"src/a.py": {"result": command_result(rc=0, failure_kind="test"),
                                "holds": False}}},
    {"necessity": {"src/a.py": {"result": failing_tests(rc=42), "holds": True},
                   "src/pkg/b.py": {"result": failing_tests(), "holds": True}}},
    {"warmup": []},
    {"warmup": [command_result(rc=0), failing_tests()]},
])
def test_accepts_a_well_formed_necessity_and_warmup(over):
    assert records.validate_record("vetting", vetting(**over)) is None


@pytest.mark.parametrize("entry", [
    {"status": "M", "path": "src/a.py", "old_path": None},
    {"status": "A", "path": "src/a.py", "old_path": None},
    {"status": "D", "path": "src/a.py", "old_path": None},
    {"status": "T", "path": "src/a.py", "old_path": None},
    {"status": "U", "path": "src/a.py", "old_path": None},
    {"status": "X", "path": "src/a.py", "old_path": None},
    {"status": "B", "path": "src/a.py", "old_path": None},
    {"status": "R100", "path": "src/a.py", "old_path": "src/old.py"},
    {"status": "R50", "path": "src/a.py", "old_path": "src/old.py"},
    {"status": "R", "path": "src/a.py", "old_path": "src/old.py"},
    {"status": "C75", "path": "src/a.py", "old_path": "src/old.py"},
    {"status": "C100", "path": "src/a.py", "old_path": "src/old.py"},
    {"status": "C", "path": "src/a.py", "old_path": "src/old.py"},
])
def test_accepts_the_git_name_status_letters(entry):
    assert records.validate_record("attempt", attempt(changed=[entry])) is None


@pytest.mark.parametrize("entry", [
    {"status": "MM", "path": "src/a.py", "old_path": None},
    {"status": "Z", "path": "src/a.py", "old_path": None},
    {"status": "R1000", "path": "src/a.py", "old_path": "src/old.py"},
    {"status": "C1234", "path": "src/a.py", "old_path": "src/old.py"},
    {"status": "R100", "path": "src/a.py", "old_path": None},
    {"status": "C75", "path": "src/a.py", "old_path": None},
    {"status": "M", "path": "src/a.py", "old_path": "src/old.py"},
    {"status": "A", "path": "src/a.py", "old_path": "src/old.py"},
    {"status": "M", "path": "src/a.py"},
    {"status": "M", "path": "src/a.py", "old_path": None, "score": None},
    # no two-letter status is a git name-status code, whatever the letters are
] + [{"status": letter * 2, "path": "src/a.py", "old_path": None}
     for letter in "ACDMRTUXBZ"]
    # the rename and copy letters need a source path, every other letter forbids one
    + [{"status": letter, "path": "src/a.py", "old_path": "src/old.py"}
       for letter in "DTUXB"]
    + [{"status": score, "path": "src/a.py", "old_path": None}
       for score in ("R", "R50", "R100", "C", "C75", "C100")]
    # the status letter itself must be one of git's, spelled exactly
    + [{"status": bad, "path": "src/a.py", "old_path": None}
       for bad in ("", " M", "M ", "m", "r100", "banana", "100", 42, None, OFF_DOMAIN)]
    # path is always a slash-form relative string; old_path is a string or null
    + [{"status": "M", "path": bad, "old_path": None}
       for bad in (42, None, ["src/a.py"], "src\\a.py", "/tmp/eval-harness/clone-3/src/a.py",
                   OFF_DOMAIN)]
    + [{"status": "R100", "path": "src/a.py", "old_path": bad}
       for bad in (42, ["nope"], OFF_DOMAIN)]
    # an entry is an object, never a bare path
    + ["src/a.py", 42, None, OFF_DOMAIN])
def test_refuses_a_malformed_changed_entry(entry):
    with pytest.raises(records.RecordError):
        records.validate_record("attempt", attempt(changed=[entry]))


def test_tdd_oracle_intact_may_be_null_after_an_early_failure():
    assert records.validate_record("attempt", unobserved_attempt()) is None


def test_a_no_launch_attempt_still_writes_the_whole_engine_run_object():
    record = unobserved_attempt()
    assert set(record["engine_run"]) == set(records.ENGINE_RUN_KEYS)
    assert record["engine_run"]["launch"] == "not-started"
    assert records.validate_record("attempt", record) is None
    assert records.derive_validity(record) == "DISCARDED:harness"


@pytest.mark.parametrize("record", [
    attempt(),
    description_attempt(),
    attempt(attempt=2),
    attempt(engine="sonnet"),
    attempt(engine="cmd1"),
    attempt(engine="cmd2"),
    attempt(started="2030-01-01T00:00:00Z", finished="2030-01-01T00:05:00Z"),
    attempt(changed=[{"status": "R100", "path": "src/b.py", "old_path": "src/a.py"}]),
])
def test_an_attempt_carries_everything_needed_to_rederive_its_verdict(record):
    assert set(record) == set(records.ATTEMPT_KEYS)
    assert records.validate_record("attempt", record) is None
    assert records.derive_validity(record) == record["validity"]
    assert records.classify(record) == (record["outcome"], record["class"])


# --- baseline -------------------------------------------------------------


@pytest.mark.parametrize("baseline, expected", [
    (failing_tests(), True),
    (failing_tests(rc=2), True),
    (command_result(rc=0, failure_kind="test"), False),
    (command_result(rc=None, failure_kind="test"), False),
    (command_result(rc=1, timed_out=True, failure_kind="test"), False),
    (command_result(rc=1, failure_kind="tool"), False),
    (command_result(rc=1, failure_kind="unknown"), False),
    (command_result(rc=1, failure_kind=None), False),
    (None, False),
    # any non-zero rc is a real test failure, however large, however signed
] + [(command_result(rc=n, failure_kind="test"), True) for n in NONZERO_RCS]
    + [(command_result(rc=n, failure_kind="tool"), False) for n in NONZERO_RCS]
    + [(command_result(rc=n, failure_kind=None), False) for n in NONZERO_RCS]
    + [(command_result(rc=n, timed_out=True, failure_kind="test"), False) for n in NONZERO_RCS])
def test_is_valid_baseline(baseline, expected):
    assert records.is_valid_baseline(baseline) is expected


# --- derive_validity ------------------------------------------------------


@pytest.mark.parametrize("record, expected", [
    (attempt(), "VALID"),
    (attempt(prep={"status": "PREP_MISMATCH", "differing_paths": ["src/a.py"]}),
     "DISCARDED:prep"),
    (attempt(prep={"status": "PREP_MISMATCH", "differing_paths": ["src/a.py"]}, baseline=None,
             engine_run=engine_run(launch="not-started")), "DISCARDED:prep"),
    (attempt(baseline=command_result(rc=0, failure_kind="test")), "DISCARDED:baseline"),
    (attempt(baseline=None), "DISCARDED:baseline"),
    (attempt(engine_run=engine_run(launch="not-started")), "DISCARDED:harness"),
    (attempt(engine_run=engine_run(launch="not-started", timed_out=True, usage_limit="hit",
                                   exit=2, identity=None)), "DISCARDED:harness"),
    (attempt(engine_run=engine_run(timed_out=True)), "DISCARDED:timeout"),
    (attempt(engine_run=engine_run(timed_out=True, usage_limit="hit", exit=2, identity=None)),
     "DISCARDED:timeout"),
    (attempt(engine_run=engine_run(usage_limit="hit")), "DISCARDED:usage-limit"),
    (attempt(engine_run=engine_run(usage_limit="hit", exit=2, identity=None)),
     "DISCARDED:usage-limit"),
    # unchecked usage detection stays recorded as unchecked; only a hit discards (PRD: VALID
    # requires usage_limit != hit, and a cmd: engine with no checker is unchecked by contract)
    (attempt(engine_run=engine_run(usage_limit="unchecked")), "VALID"),
    (attempt(engine_run=engine_run(exit=1)), "DISCARDED:exit-1"),
    (attempt(engine_run=engine_run(exit=137, identity=None)), "DISCARDED:exit-137"),
    (attempt(engine_run=engine_run(identity=None)), "DISCARDED:identity"),
    (attempt(engine_run=engine_run(completion="unknown")), "DISCARDED:incomplete"),
    (attempt(engine_run=engine_run(completion="incomplete")), "DISCARDED:incomplete"),
    (attempt(engine_run=engine_run(final_message_bytes=0)), "DISCARDED:incomplete"),
    (attempt(engine_run=engine_run(final_message_bytes=-1)), "DISCARDED:incomplete"),
    (attempt(engine_run=engine_run(final_message_bytes=-20)), "DISCARDED:incomplete"),
    (attempt(engine_run=engine_run(final_message_bytes=None)), "DISCARDED:incomplete"),
    (attempt(engine_run=engine_run(launch="unknown", exit=0)), "DISCARDED:incomplete"),
    # the reason names the exit code the engine actually returned, not a known few
] + [(attempt(engine_run=engine_run(exit=code)), "DISCARDED:exit-%d" % code)
     for code in (2, 3, 42, 99, 255, -1)])
def test_derive_validity_walks_the_rejection_ladder(record, expected):
    assert records.derive_validity(record) == expected


def test_derive_validity_scores_a_lost_exit_code_incomplete_never_harness():
    record = attempt(engine_run=engine_run(launch="started", exit=None))
    assert records.derive_validity(record) == "DISCARDED:incomplete"


def test_derive_validity_is_total_over_the_permitted_domains():
    domains = itertools.product(
        ("not-started", "started", "unknown"),
        (None, 0, 1, 2, 137),
        ("complete", "incomplete", "unknown"),
        (None, -1, 0, 7),
        (None, "qwen3-coder-30b"),
        ("clear", "hit", "unchecked"),
    )
    for launch, exit_code, completion, message_bytes, identity, usage_limit in domains:
        combo = (launch, exit_code, completion, message_bytes, identity, usage_limit)
        record = attempt(engine_run=engine_run(
            launch=launch, exit=exit_code, completion=completion,
            final_message_bytes=message_bytes, identity=identity, usage_limit=usage_limit))
        result = records.derive_validity(record)
        assert is_closed_set_reason(result), (result, combo)
        if result == "VALID":
            assert launch == "started" and completion == "complete", combo
            assert isinstance(message_bytes, int) and message_bytes > 0, combo
            assert exit_code == 0 and usage_limit != "hit", combo
        if launch == "not-started":
            assert result == "DISCARDED:harness", combo
        elif usage_limit == "hit":
            assert result == "DISCARDED:usage-limit", combo
        elif isinstance(exit_code, int) and exit_code != 0:
            assert result == "DISCARDED:exit-%d" % exit_code, combo
        elif identity is None:
            assert result == "DISCARDED:identity", combo
        elif exit_code is None:
            assert result == "DISCARDED:incomplete", combo
        else:
            expected = "VALID" if (
                launch == "started"
                and completion == "complete"
                and isinstance(message_bytes, int) and message_bytes > 0
                and exit_code == 0
                and usage_limit != "hit"
            ) else "DISCARDED:incomplete"
            assert result == expected, combo


# --- classify -------------------------------------------------------------


@pytest.mark.parametrize("record, expected", [
    # 1: the engine itself timed out
    (attempt(engine_run=engine_run(timed_out=True), validity="DISCARDED:timeout"),
     ("TIMEOUT", None)),
    # 2: a measurement command timed out
    (attempt(gates={"gate": command_result(rc=None, timed_out=True, wall_s=600.0),
                    "own": None, "ablate": None}), ("SUSPECT", None)),
    (attempt(baseline=command_result(rc=None, timed_out=True), validity="DISCARDED:baseline"),
     ("SUSPECT", None)),
    # a timeout in own or ablate is just as untrustworthy, even carrying a usable rc
    (attempt(gates={"gate": command_result(rc=0),
                    "own": command_result(rc=1, timed_out=True, failure_kind="test"),
                    "ablate": None}), ("SUSPECT", None)),
    (description_attempt(gates={"gate": command_result(rc=0),
                                "own": command_result(rc=1, timed_out=True,
                                                      failure_kind="test"),
                                "ablate": failing_tests()}), ("SUSPECT", None)),
    (description_attempt(gates={"gate": command_result(rc=0), "own": command_result(rc=0),
                                "ablate": command_result(rc=1, timed_out=True,
                                                         failure_kind="test")}),
     ("SUSPECT", None)),
    (attempt(gates={"gate": command_result(rc=0), "own": None,
                    "ablate": command_result(rc=None, timed_out=True, wall_s=600.0)}),
     ("SUSPECT", None)),
    # 3: the clone or the baseline never gave a usable starting point
    (attempt(prep={"status": "PREP_MISMATCH", "differing_paths": ["src/a.py"]},
             validity="DISCARDED:prep"), ("DISCARDED", None)),
    (attempt(baseline=command_result(rc=0, failure_kind="test"),
             validity="DISCARDED:baseline"), ("DISCARDED", None)),
    (attempt(baseline=None, validity="DISCARDED:baseline"), ("DISCARDED", None)),
    # 4: the attempt is not valid evidence
    (attempt(engine_run=engine_run(completion="incomplete"), validity="DISCARDED:incomplete"),
     ("DISCARDED", None)),
    # 5: candidate behaviour violations, in precedence order
    (attempt(oracle_intact=False, stray=["docs/x.md"], changed=[], dropped=["src/b.py"]),
     ("FAIL", "test-mutation")),
    (attempt(stray=["docs/x.md"], changed=[], dropped=["src/b.py"]), ("FAIL", "stray-edit")),
    (attempt(changed=[], dropped=["src/b.py"]), ("FAIL", "no-edit")),
    (attempt(dropped=["src/b.py"]), ("FAIL", "dropped-a-file")),
    (description_attempt(gates={"gate": command_result(rc=0), "own": command_result(rc=0),
                                "ablate": command_result(rc=0)}), ("FAIL", "vacuous-tests")),
    # a decided vacuous-tests violation outranks a required gate that never ran, whichever
    # of the rung-6 gates is the missing one
    (description_attempt(gates={"gate": command_result(rc=0), "own": None,
                                "ablate": command_result(rc=0)}), ("FAIL", "vacuous-tests")),
    (description_attempt(gates={"gate": None, "own": command_result(rc=0),
                                "ablate": command_result(rc=0)}), ("FAIL", "vacuous-tests")),
    (description_attempt(gates={"gate": None, "own": None,
                                "ablate": command_result(rc=0)}), ("FAIL", "vacuous-tests")),
    # a passing ablation is no violation in tdd shape, where ablate is not asked for
    (attempt(gates={"gate": command_result(rc=0), "own": None,
                    "ablate": command_result(rc=0)}), ("PASS", None)),
    # 6: a required gate never produced a usable test verdict
    (description_attempt(gates={"gate": command_result(rc=0), "own": None,
                                "ablate": failing_tests()}), ("SUSPECT", None)),
    # 7: the gates back a real pass
    (attempt(), ("PASS", None)),
    (description_attempt(), ("PASS", None)),
    # 8: the candidate simply got it wrong
    (attempt(gates={"gate": failing_tests(), "own": None, "ablate": None}),
     ("FAIL", "logic-error")),
    # a test failure is a usable verdict at any non-zero rc, exactly as for the baseline
    (attempt(gates={"gate": failing_tests(rc=2), "own": None, "ablate": None}),
     ("FAIL", "logic-error")),
    (attempt(gates={"gate": failing_tests(rc=10), "own": None, "ablate": None}),
     ("FAIL", "logic-error")),
    (attempt(gates={"gate": failing_tests(rc=255), "own": None, "ablate": None}),
     ("FAIL", "logic-error")),
    (description_attempt(gates={"gate": command_result(rc=0),
                                "own": failing_tests(rc=10), "ablate": failing_tests()}),
     ("FAIL", "logic-error")),
    (description_attempt(gates={"gate": command_result(rc=0), "own": command_result(rc=0),
                                "ablate": failing_tests(rc=2)}), ("PASS", None)),
    (description_attempt(gates={"gate": command_result(rc=0), "own": command_result(rc=0),
                                "ablate": failing_tests(rc=255)}), ("PASS", None)),
])
def test_classify_walks_the_precedence_ladder(record, expected):
    outcome, cls = records.classify(record)
    assert (outcome, cls) == expected
    derived = {**record, "validity": records.derive_validity(record),
               "outcome": outcome, "class": cls}
    assert records.validate_record("attempt", derived) is None


def test_classify_ignores_a_stored_pass_on_an_attempt_that_edited_nothing():
    record = attempt(changed=[])
    record["outcome"], record["class"] = "PASS", None
    assert records.classify(record) == ("FAIL", "no-edit")


def test_classify_ignores_a_stored_failure_on_an_attempt_the_gates_cleared():
    record = attempt()
    record["outcome"], record["class"] = "FAIL", "logic-error"
    assert records.classify(record) == ("PASS", None)


def test_classify_ignores_a_stored_validity_the_evidence_contradicts():
    record = attempt(engine_run=engine_run(completion="incomplete"), validity="VALID")
    record["outcome"], record["class"] = "PASS", None
    assert records.derive_validity(record) == "DISCARDED:incomplete"
    assert records.classify(record) == ("DISCARDED", None)


@pytest.mark.parametrize("record, expected", [
    (attempt(changed=None), ("SUSPECT", None)),
    (attempt(changed=[]), ("FAIL", "no-edit")),
    (attempt(stray=None), ("SUSPECT", None)),
    (attempt(stray=[]), ("PASS", None)),
    (attempt(stray=["docs/x.md"]), ("FAIL", "stray-edit")),
    # any stray edit counts, not one blessed path
    (attempt(stray=["README.md"]), ("FAIL", "stray-edit")),
    (attempt(stray=["tests/conftest.py"]), ("FAIL", "stray-edit")),
    (attempt(stray=["docs/a.md", "docs/b.md"]), ("FAIL", "stray-edit")),
    (attempt(dropped=None), ("SUSPECT", None)),
    (attempt(dropped=[]), ("PASS", None)),
    (attempt(dropped=["src/b.py"]), ("FAIL", "dropped-a-file")),
    # and any dropped file counts
    (attempt(dropped=["tests/test_z.py"]), ("FAIL", "dropped-a-file")),
    (attempt(dropped=["src/pkg/deep/y.py"]), ("FAIL", "dropped-a-file")),
    (attempt(dropped=["src/x.py", "src/y.py"]), ("FAIL", "dropped-a-file")),
    (attempt(oracle_intact=None), ("SUSPECT", None)),
    (attempt(oracle_intact=False), ("FAIL", "test-mutation")),
    # an edit somewhere else entirely is still an edit
    (attempt(changed=[{"status": "A", "path": "src/pkg/new.py", "old_path": None},
                      {"status": "D", "path": "src/pkg/old.py", "old_path": None}]),
     ("PASS", None)),
])
def test_classify_reads_null_as_undecidable_and_empty_as_observed(record, expected):
    assert records.classify(record) == expected


def test_required_gates_are_the_ones_the_shape_asks_for():
    unrun = {"gate": command_result(rc=0), "own": None, "ablate": None}
    assert records.classify(attempt(gates=unrun)) == ("PASS", None)
    assert records.classify(description_attempt(gates=unrun)) == ("SUSPECT", None)

    # the published mapping is the one classify obeys: drop each gate in turn and the
    # verdict must be SUSPECT exactly for the gates REQUIRED_GATES lists for that shape
    build = {"tdd": attempt, "description": description_attempt}
    assert set(records.REQUIRED_GATES) == set(build)
    for shape, make in build.items():
        required = records.REQUIRED_GATES[shape]
        assert set(required) <= {"gate", "own", "ablate"}
        for name in ("gate", "own", "ablate"):
            record = make()
            record = make(gates=dict(record["gates"], **{name: None}))
            outcome, cls = records.classify(record)
            if name in required:
                assert (outcome, cls) == ("SUSPECT", None), (shape, name)
            else:
                assert outcome != "SUSPECT", (shape, name)


def test_shape_inapplicable_nulls_do_not_make_an_attempt_suspect():
    assert records.classify(attempt(oracle_intact=True)) == ("PASS", None)
    assert records.classify(description_attempt(oracle_intact=None)) == ("PASS", None)


@pytest.mark.parametrize("record", [
    description_attempt(gates={"gate": command_result(rc=0), "own": command_result(rc=0),
                               "ablate": command_result(rc=None, failure_kind="test")}),
    attempt(gates={"gate": command_result(rc=None, failure_kind=None), "own": None,
                   "ablate": None}),
    attempt(gates={"gate": command_result(rc=1, failure_kind=None), "own": None,
                   "ablate": None}),
    attempt(gates={"gate": command_result(rc=1, failure_kind="tool"), "own": None,
                   "ablate": None}),
    attempt(gates={"gate": command_result(rc=1, failure_kind="unknown"), "own": None,
                   "ablate": None}),
    # the rc that carries the non-test failure makes no difference, small or large
    attempt(gates={"gate": command_result(rc=10, failure_kind="tool"), "own": None,
                   "ablate": None}),
    attempt(gates={"gate": command_result(rc=255, failure_kind=None), "own": None,
                   "ablate": None}),
    description_attempt(gates={"gate": command_result(rc=0),
                               "own": command_result(rc=10, failure_kind="tool"),
                               "ablate": failing_tests()}),
    description_attempt(gates={"gate": command_result(rc=0), "own": command_result(rc=0),
                               "ablate": command_result(rc=42, failure_kind="unknown")}),
])
def test_a_gate_without_a_test_verdict_is_suspect(record):
    assert records.classify(record) == ("SUSPECT", None)
