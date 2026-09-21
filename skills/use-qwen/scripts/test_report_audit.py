"""Input validation in eval_harness.report: audit.jsonl rows, attempt.json records,
the run id, and the load_audit() / count() exports.

Every refusal test renders once, corrupts one input, asserts render() raises
ValueError naming the offending line or attempt, and asserts the three rendered
files are byte-identical to their pre-call state. Expectations are recomputed
from the round's records and run.json, never from report.py's own arithmetic.
Only rounds "hang", "retry", "tdd" and "r1" are used, per the task.
"""
import json
from pathlib import Path

import pytest

import run_eval_harness
from eval_harness import admission, records, report

# The last six names are fixtures: pytest resolves them from this module's own
# namespace, so they have to be imported even though nothing here calls them.
from eval_harness_run_helpers import (
    _attempts,
    drifted,
    pair,
    rounds,
    scratch,
    shim,
    slow,
    vetted,
)
from test_report import _audit_row, _files, _render, _run_json, _valid_ids, _write_audit

TALLIES = ("attempts", "PASS", "FAIL", "TIMEOUT", "SUSPECT", "DISCARDED", "INCOMPLETE")
FAIL_CLASSES = ("test-mutation", "stray-edit", "no-edit", "dropped-a-file", "vacuous-tests",
                "logic-error")
CLASS_KEYS = tuple("FAIL:%s" % cls for cls in FAIL_CLASSES)
COUNT_KEYS = {"engines", "drops", "scored", "not_started", "f", "f_audited", "f_total"}


def _expected(lineno: int, reason: str, line: str) -> str:
    """The refusal text for `line`: names its number first and its text last."""
    return "audit.jsonl line %d: %s: %r" % (lineno, reason, line)


def _audit_refusal(round_, audit_text: str) -> str:
    """Render with `audit_text` as audit.jsonl: the ValueError's message.

    Renders once first, then asserts the three files stay byte-identical.
    """
    before = _render(round_)
    audit_path = round_.run / "audit.jsonl"
    audit_path.write_text(audit_text, encoding="utf-8")
    try:
        with pytest.raises(ValueError) as failure:
            report.render(round_.root, round_.run.name)
        assert _files(round_) == before
    finally:
        audit_path.unlink()
    return str(failure.value)


def _record_refusal(round_, aid: str, text: str) -> str:
    """Render with `text` as this attempt's attempt.json: the ValueError's message."""
    before = _render(round_)
    record_path = round_.run / aid / "attempt.json"
    original = record_path.read_text(encoding="utf-8")
    record_path.write_text(text, encoding="utf-8")
    try:
        with pytest.raises(ValueError) as failure:
            report.render(round_.root, round_.run.name)
        assert _files(round_) == before
    finally:
        record_path.write_text(original, encoding="utf-8")
    return str(failure.value)


def _effort_line(attempt_dir: str, literal: str) -> str:
    """One audit line whose review_effort_s is the raw JSON text `literal`."""
    base = json.dumps(_audit_row(attempt_dir))
    line = base.replace('"review_effort_s": 0.0}', '"review_effort_s": %s}' % literal)
    assert line.endswith('"review_effort_s": %s}' % literal)
    return line


def _tree(root: Path) -> dict:
    return {
        path.relative_to(root): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in root.rglob("*") if path.is_file()
    }


# -- audit.jsonl rows: the attempt they name -----------------------------------


def test_render_rejects_an_audit_row_naming_an_attempt_dir_that_does_not_exist(rounds):
    round_ = rounds("r1")
    assert not (round_.run / "9-cmd9-a9").exists()
    line = json.dumps(_audit_row("9-cmd9-a9"))

    message = _audit_refusal(round_, line + "\n")

    assert message == _expected(1, "audits unknown/non-VALID attempt '9-cmd9-a9'", line)


def test_render_rejects_an_audit_row_naming_an_attempt_that_exists_but_is_not_valid(rounds):
    round_ = rounds("retry")
    discarded = next(aid for aid, record in _attempts(round_).items()
                     if records.derive_validity(record) != "VALID")
    assert (round_.run / discarded / "attempt.json").is_file()
    line = json.dumps(_audit_row(discarded))

    message = _audit_refusal(round_, line + "\n")

    assert message == _expected(1, "audits unknown/non-VALID attempt %r" % discarded, line)


@pytest.mark.parametrize("wrap", [lambda aid: [aid], lambda aid: 7, lambda aid: None],
                         ids=["list", "int", "null"])
def test_render_rejects_a_non_string_attempt_dir(rounds, wrap):
    round_ = rounds("r1")
    line = json.dumps(_audit_row(wrap(_valid_ids(round_)[0])))

    message = _audit_refusal(round_, line + "\n")

    assert message == _expected(1, "non-string attempt_dir", line)


def test_render_rejects_a_duplicate_attempt_dir_naming_its_line_and_the_id(rounds):
    round_ = rounds("r1")
    valid_ids = _valid_ids(round_)
    assert len(valid_ids) >= 2
    lines = [json.dumps(_audit_row(valid_ids[0])), json.dumps(_audit_row(valid_ids[1])),
             json.dumps(_audit_row(valid_ids[0], verdict="unverifiable"))]

    message = _audit_refusal(round_, "".join(line + "\n" for line in lines))

    assert message == _expected(3, "duplicate attempt_dir %s" % valid_ids[0], lines[2])


# -- audit.jsonl rows: shape and keys -------------------------------------------


@pytest.mark.parametrize("line", ["[1, 2]", '"oops"', "7"])
def test_render_rejects_an_audit_line_that_is_valid_json_but_not_an_object(rounds, line):
    message = _audit_refusal(rounds("r1"), line + "\n")

    assert message == _expected(1, "not a JSON object", line)


@pytest.mark.parametrize("mutate, diff", [
    (lambda row: row.pop("claim"), "['claim']"),
    (lambda row: row.update(note="x"), "['note']"),
    (lambda row: (row.pop("review_effort_s"), row.update(effort=1)),
     "['effort', 'review_effort_s']"),
], ids=["missing", "extra", "renamed"])
def test_render_rejects_an_audit_row_with_a_missing_or_extra_key(rounds, mutate, diff):
    round_ = rounds("r1")
    row = _audit_row(_valid_ids(round_)[0])
    mutate(row)
    line = json.dumps(row)

    message = _audit_refusal(round_, line + "\n")

    assert message == _expected(1, "missing/extra key (%s)" % diff, line)


def test_an_audit_refusal_names_the_source_line_counting_blank_lines(rounds):
    round_ = rounds("r1")
    valid_ids = _valid_ids(round_)
    assert len(valid_ids) >= 2
    bad = json.dumps(_audit_row(valid_ids[1], verdict="maybe"))

    message = _audit_refusal(round_, json.dumps(_audit_row(valid_ids[0])) + "\n\n" + bad + "\n")

    assert message == _expected(3, "invalid verdict 'maybe'", bad)


# -- audit.jsonl rows: field values ----------------------------------------------


@pytest.mark.parametrize("verdict", ["maybe", "blocking"])
def test_render_rejects_a_verdict_outside_clean_flagged_unverifiable(rounds, verdict):
    round_ = rounds("r1")
    line = json.dumps(_audit_row(_valid_ids(round_)[0], verdict=verdict))

    message = _audit_refusal(round_, line + "\n")

    assert message == _expected(1, "invalid verdict %r" % verdict, line)


@pytest.mark.parametrize("review_verdict", ["maybe", "flagged"])
def test_render_rejects_a_review_verdict_outside_clean_blocking_unverifiable(
    rounds, review_verdict,
):
    round_ = rounds("r1")
    line = json.dumps(_audit_row(_valid_ids(round_)[0], review_verdict=review_verdict))

    message = _audit_refusal(round_, line + "\n")

    assert message == _expected(1, "invalid review_verdict %r" % review_verdict, line)


@pytest.mark.parametrize("over", [{"claim": "", "evidence": "e"}, {"claim": "c", "evidence": ""}],
                         ids=["no-claim", "no-evidence"])
def test_render_rejects_a_flagged_row_without_a_claim_or_evidence(rounds, over):
    round_ = rounds("r1")
    line = json.dumps(_audit_row(_valid_ids(round_)[0], verdict="flagged", **over))

    message = _audit_refusal(round_, line + "\n")

    assert message == _expected(1, "flags without a claim/evidence", line)


@pytest.mark.parametrize("over", [{"claim": 1}, {"evidence": None}, {"claim": ["c"]}],
                         ids=["int-claim", "null-evidence", "list-claim"])
def test_render_rejects_a_non_string_claim_or_evidence(rounds, over):
    round_ = rounds("r1")
    line = json.dumps(_audit_row(_valid_ids(round_)[0], **over))

    message = _audit_refusal(round_, line + "\n")

    assert message == _expected(1, "non-string claim/evidence", line)


def test_render_rejects_a_blocking_review_verdict_with_no_findings(rounds):
    round_ = rounds("r1")
    line = json.dumps(_audit_row(_valid_ids(round_)[0], review_verdict="blocking",
                                 review_findings=[]))

    message = _audit_refusal(round_, line + "\n")

    assert message == _expected(1, "blocking with no review_findings", line)


@pytest.mark.parametrize("review_findings", ["x", ["a", 1], None, {"a": "b"}],
                         ids=["string", "mixed-list", "null", "object"])
def test_render_rejects_review_findings_that_are_not_a_list_of_strings(rounds, review_findings):
    round_ = rounds("r1")
    line = json.dumps(_audit_row(_valid_ids(round_)[0], review_findings=review_findings))

    message = _audit_refusal(round_, line + "\n")

    assert message == _expected(1, "non-string-list review_findings", line)


@pytest.mark.parametrize("literal, reason", [
    ("-1", "invalid review_effort_s"),
    ("true", "invalid review_effort_s"),
    ("Infinity", "malformed JSON"),
    ("1e309", "invalid review_effort_s"),
])
def test_render_rejects_a_review_effort_s_that_is_not_finite_nonnegative_seconds(
    rounds, literal, reason,
):
    round_ = rounds("r1")
    line = _effort_line(_valid_ids(round_)[0], literal)

    message = _audit_refusal(round_, line + "\n")

    assert message == _expected(1, reason, line)


@pytest.mark.parametrize("literal", ["0", "0.0", "null", "1.5", "1" + "0" * 399],
                         ids=["zero", "zero-float", "null", "fraction", "400-digit-int"])
def test_render_accepts_a_review_effort_s_of_zero_null_or_any_finite_nonnegative_number(
    rounds, literal,
):
    round_ = rounds("r1")
    valid_ids = _valid_ids(round_)
    assert len(valid_ids) >= 2
    audit_path = round_.run / "audit.jsonl"
    audit_path.write_text(_effort_line(valid_ids[0], literal) + "\n", encoding="utf-8")

    try:
        _, report_md, _ = _render(round_)
    finally:
        audit_path.unlink()

    assert ("pending (1 of %d audited)" % len(valid_ids)) in report_md


def test_render_accepts_a_fully_populated_flagged_and_blocking_row(rounds):
    round_ = rounds("r1")
    valid_ids = _valid_ids(round_)
    assert len(valid_ids) >= 2
    _write_audit(round_, [_audit_row(
        valid_ids[0], verdict="flagged", claim="c", evidence="e", review_verdict="blocking",
        review_findings=["f1", "f2"], review_effort_s=12,
    )])

    try:
        _, report_md, _ = _render(round_)
    finally:
        (round_.run / "audit.jsonl").unlink()

    assert ("pending (1 of %d audited)" % len(valid_ids)) in report_md


def test_render_accepts_an_unverifiable_review_verdict(rounds):
    round_ = rounds("r1")
    valid_ids = _valid_ids(round_)
    assert len(valid_ids) >= 2
    _write_audit(round_, [_audit_row(valid_ids[0], review_verdict="unverifiable")])

    try:
        _, report_md, _ = _render(round_)
    finally:
        (round_.run / "audit.jsonl").unlink()

    assert ("pending (1 of %d audited)" % len(valid_ids)) in report_md


# -- load_audit() ------------------------------------------------------------------


def test_load_audit_returns_an_empty_dict_when_there_is_no_audit_jsonl(rounds):
    round_ = rounds("r1")
    assert not (round_.run / "audit.jsonl").exists()

    assert report.load_audit(round_.run, _valid_ids(round_)) == {}


def test_load_audit_keys_rows_by_attempt_dir(rounds):
    round_ = rounds("r1")
    valid_ids = _valid_ids(round_)
    assert len(valid_ids) >= 2
    _write_audit(round_, [_audit_row(valid_ids[1], verdict="unverifiable"),
                          _audit_row(valid_ids[0])])

    try:
        rows = report.load_audit(round_.run, valid_ids)
    finally:
        (round_.run / "audit.jsonl").unlink()

    assert set(rows) == {valid_ids[0], valid_ids[1]}


def test_load_audit_itself_refuses_a_row_for_an_attempt_outside_valid_ids(rounds):
    round_ = rounds("r1")
    valid_ids = _valid_ids(round_)
    assert len(valid_ids) >= 2
    line = json.dumps(_audit_row(valid_ids[1]))
    _write_audit(round_, [_audit_row(valid_ids[0]), _audit_row(valid_ids[1])])

    try:
        with pytest.raises(ValueError) as failure:
            report.load_audit(round_.run, valid_ids[:1])
    finally:
        (round_.run / "audit.jsonl").unlink()

    assert str(failure.value) == _expected(
        2, "audits unknown/non-VALID attempt %r" % valid_ids[1], line
    )


# -- attempt.json records --------------------------------------------------------


def test_render_rejects_a_truncated_attempt_json_naming_the_attempt_directory(rounds):
    round_ = rounds("tdd")
    aid = next(iter(_attempts(round_)))

    message = _record_refusal(round_, aid, '{"task":')

    assert message.startswith("attempt %s: malformed attempt.json: " % aid)


def _validator_reason(record: dict) -> str:
    """The text records.validate_record refuses `record` with; render() must relay it."""
    with pytest.raises(records.RecordError) as failure:
        records.validate_record("attempt", record)
    return str(failure.value)


@pytest.mark.parametrize("corrupt, marker", [
    (lambda record: record.update(strated=record.pop("started")), "attempt keys"),
    (lambda record: record.pop("gates"), "attempt keys"),
    (lambda record: record.update(note="x"), "attempt keys"),
    (lambda record: record.update(task="1"), "attempt.task: '1'"),
    (lambda record: record.update(outcome="MAYBE"), "attempt.outcome: 'MAYBE'"),
], ids=["renamed-key", "missing-key", "extra-key", "task-not-int", "outcome-out-of-domain"])
def test_render_rejects_an_attempt_json_that_fails_the_record_schema_naming_the_problem(
    rounds, corrupt, marker,
):
    round_ = rounds("tdd")
    aid, record = next(iter(_attempts(round_).items()))
    record = dict(record)
    corrupt(record)
    text = json.dumps(record)
    reason = _validator_reason(json.loads(text))
    assert marker in reason

    message = _record_refusal(round_, aid, text)

    assert message.startswith("attempt %s: " % aid)
    assert message == "attempt %s: %s" % (aid, reason)


@pytest.mark.parametrize("field, other", [
    ("task", lambda record, engine_ids: 99),
    ("engine", lambda record, engine_ids: next(e for e in engine_ids if e != record["engine"])),
    ("attempt", lambda record, engine_ids: record["attempt"] + 1),
])
def test_render_rejects_an_attempt_json_whose_identity_disagrees_with_its_directory(
    rounds, field, other,
):
    round_ = rounds("tdd")
    engine_ids = [engine["id"] for engine in _run_json(round_)["engines"]]
    aid, record = next(iter(_attempts(round_).items()))
    record = dict(record)
    record[field] = other(record, engine_ids)

    message = _record_refusal(round_, aid, json.dumps(record))

    assert message == (
        "attempt %s: record identity (task=%r, engine=%r, attempt=%r) does not match its "
        "directory name" % (aid, record["task"], record["engine"], record["attempt"])
    )


# -- the run id ------------------------------------------------------------------


@pytest.mark.parametrize(
    "run_id", ["/outside", "..", "a/b", "a\\b", "", ".", "r/", "a\0b", "/tmp/x"],
    ids=["absolute", "parent", "nested", "backslash", "empty", "dot", "trailing-slash", "nul",
         "absolute-tmp"],
)
def test_render_refuses_a_run_id_that_is_not_one_directory_name_before_touching_disk(
    rounds, run_id,
):
    round_ = rounds("r1")
    _render(round_)
    before = _tree(round_.root)
    problem = admission.check_run_id(run_id)
    assert problem is not None

    with pytest.raises(ValueError) as failure:
        report.render(round_.root, run_id)

    assert str(failure.value) == "run id %r: %s" % (run_id, problem)
    assert _tree(round_.root) == before
    if run_id.startswith("/"):
        assert not (Path(run_id) / "report.md").exists()


# -- count() ------------------------------------------------------------------------


def _count(round_) -> dict:
    """count() fed the same inputs render() builds, per the design's data flow."""
    run = _run_json(round_)
    engine_order = [engine["id"] for engine in run["engines"]]
    entries = report._load_entries(round_.run, engine_order)
    groups = report._group_by_task_engine(entries)
    valid_ids = [entry["id"] for entry in entries
                 if entry["record"] is not None
                 and records.derive_validity(entry["record"]) == "VALID"]
    audit_rows = report.load_audit(round_.run, valid_ids)
    return report.count(run, engine_order, entries, groups, valid_ids, audit_rows)


def _recount(round_) -> dict:
    """Per engine: every tally and every one of the six FAIL classes, zero included."""
    by_engine = {}
    for record in _attempts(round_).values():
        tallies = by_engine.setdefault(record["engine"], dict.fromkeys((*TALLIES, *CLASS_KEYS), 0))
        tallies["attempts"] += 1
        tallies[record["outcome"]] += 1
        if record["outcome"] == "FAIL":
            tallies["FAIL:%s" % record["class"]] += 1
    return by_engine


def _expected_drops(round_) -> int:
    return sum(record["outcome"] == "FAIL" and record["class"] == "dropped-a-file"
               for record in _attempts(round_).values())


def _expected_scored(round_) -> int:
    """Tasks whose every engine's highest-numbered attempt has a launched record."""
    run = _run_json(round_)
    attempts = _attempts(round_)
    names = [path.name for path in round_.run.iterdir() if path.is_dir()]
    scored = 0
    for task in run["tasks"]:
        launched = []
        for engine in run["engines"]:
            prefix = "%d-%s-a" % (task["id"], engine["id"])
            numbers = [int(name[len(prefix):]) for name in names
                       if name.startswith(prefix) and name[len(prefix):].isdigit()]
            record = attempts.get("%s%d" % (prefix, max(numbers))) if numbers else None
            launched.append(record is not None
                            and record["engine_run"]["launch"] in ("started", "unknown"))
        scored += all(launched)
    return scored


@pytest.mark.parametrize("run_id", ["hang", "retry", "tdd", "r1"])
def test_count_tallies_every_engine_from_the_records_in_engine_order(rounds, run_id):
    round_ = rounds(run_id)
    expected = _recount(round_)
    engine_ids = [engine["id"] for engine in _run_json(round_)["engines"]]

    counts = _count(round_)

    assert set(counts) == COUNT_KEYS
    assert list(counts["engines"]) == engine_ids
    assert set(expected) == set(engine_ids)
    for engine, tallies in expected.items():
        got = counts["engines"][engine]
        assert set(got) == {"not_started", *TALLIES, *CLASS_KEYS}, (run_id, engine)
        assert got["not_started"] is False, (run_id, engine)
        for label, value in tallies.items():
            assert got[label] == value, (run_id, engine, label)
        by_class = {key: got[key] for key in CLASS_KEYS}
        assert sum(by_class.values()) == tallies["FAIL"], (run_id, engine, by_class)
    assert counts["not_started"] == 0
    for key in ("drops", "scored"):
        assert isinstance(counts[key], int) and not isinstance(counts[key], bool), key
    assert counts["drops"] == _expected_drops(round_), run_id
    assert counts["scored"] == _expected_scored(round_), run_id


def test_count_reports_a_planned_engine_with_no_attempt_directory_as_not_started(rounds):
    round_ = rounds("r1")
    run_path = round_.run / "run.json"
    original = run_path.read_text(encoding="utf-8")
    run = json.loads(original)
    assert len(run["tasks"]) == 1
    planned = [engine["id"] for engine in run["engines"]]
    missing = ["sonnet", "gemini"]
    run["engines"] = [*run["engines"],
                      *({"id": eid, "command": "cmd:/nonexistent/engine"} for eid in missing)]
    run_path.write_text(json.dumps(run), encoding="utf-8")

    try:
        counts = _count(round_)
    finally:
        run_path.write_text(original, encoding="utf-8")

    assert list(counts["engines"]) == [*planned, *missing]
    assert counts["not_started"] == 2
    zeroed = dict.fromkeys((*TALLIES, *CLASS_KEYS), 0)
    for eid in missing:
        tallies = counts["engines"][eid]
        assert tallies["not_started"] is True, eid
        assert {key: tallies[key] for key in zeroed} == zeroed, eid
        assert not any(isinstance(tallies[key], bool) for key in zeroed), eid
    assert [eid for eid in planned if counts["engines"][eid]["not_started"]] == []


def test_count_reports_f_pending_with_k_of_n_until_every_valid_attempt_is_audited(rounds):
    round_ = rounds("r1")
    valid_ids = _valid_ids(round_)
    assert len(valid_ids) >= 2
    n = len(valid_ids)
    flagged = _audit_row(valid_ids[0], verdict="flagged", claim="c", evidence="e")

    pending = _count(round_)
    _write_audit(round_, [flagged])
    try:
        partial = _count(round_)
        _write_audit(round_, [flagged, *(_audit_row(aid) for aid in valid_ids[1:])])
        full = _count(round_)
    finally:
        (round_.run / "audit.jsonl").unlink()

    assert (pending["f"], pending["f_audited"], pending["f_total"]) == (None, 0, n)
    assert (partial["f"], partial["f_audited"], partial["f_total"]) == (None, 1, n)
    assert (full["f"], full["f_audited"], full["f_total"]) == (1, n, n)


def test_count_reports_f_as_zero_of_zero_when_no_attempt_is_valid(rounds):
    round_ = rounds("hang")
    assert not _valid_ids(round_)

    counts = _count(round_)

    assert (counts["f"], counts["f_audited"], counts["f_total"]) == (0, 0, 0)


# -- run.json / vetting.json / the CLI ---------------------------------------------


def _run_json_refusal(round_, text: str) -> str:
    """Render with `text` as this round's run.json: the ValueError's message."""
    before = _render(round_)
    run_path = round_.run / "run.json"
    original = run_path.read_text(encoding="utf-8")
    run_path.write_text(text, encoding="utf-8")
    try:
        with pytest.raises(ValueError) as failure:
            report.render(round_.root, round_.run.name)
        assert _files(round_) == before
    finally:
        run_path.write_text(original, encoding="utf-8")
    return str(failure.value)


def _vetting_refusal(round_, task_dir: Path, text: str) -> str:
    """Render with `text` as `task_dir`'s vetting.json: the ValueError's message."""
    before = _render(round_)
    vetting_path = task_dir / "vetting.json"
    original = vetting_path.read_text(encoding="utf-8")
    vetting_path.write_text(text, encoding="utf-8")
    try:
        with pytest.raises(ValueError) as failure:
            report.render(round_.root, round_.run.name)
        assert _files(round_) == before
    finally:
        vetting_path.write_text(original, encoding="utf-8")
    return str(failure.value)


def test_render_rejects_a_malformed_run_json_naming_the_run_and_file(rounds):
    round_ = rounds("r1")

    message = _run_json_refusal(round_, "{not json")

    assert round_.run.name in message
    assert "run.json" in message
    assert "malformed" in message


def test_render_rejects_a_malformed_vetting_json_naming_the_task_directory(rounds):
    round_ = rounds("r1")
    task_dir = sorted((round_.root / "tasks").iterdir())[0]

    message = _vetting_refusal(round_, task_dir, "{not json")

    assert task_dir.name in message
    assert "vetting.json" in message
    assert "malformed" in message


def test_main_render_returns_1_and_one_stderr_line_with_no_traceback_on_a_refusal(
    rounds, capsys,
):
    round_ = rounds("r1")
    before = _render(round_)
    aid = _valid_ids(round_)[0]
    _write_audit(round_, [_audit_row(aid, verdict="maybe")])

    try:
        exit_code = run_eval_harness.main(
            ["render", str(round_.root), "--run-id", round_.run.name]
        )
        captured = capsys.readouterr()
        assert _files(round_) == before
    finally:
        (round_.run / "audit.jsonl").unlink()

    assert exit_code == 1
    lines = captured.err.splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("render refused: ")
    assert "audit.jsonl line 1" in lines[0]
    assert "invalid verdict 'maybe'" in lines[0]
    assert "Traceback" not in captured.err


def test_main_render_returns_0_with_empty_stderr_on_a_clean_round(rounds, capsys):
    round_ = rounds("r1")
    assert not (round_.run / "audit.jsonl").exists()

    exit_code = run_eval_harness.main(
        ["render", str(round_.root), "--run-id", round_.run.name]
    )

    assert exit_code == 0
    assert capsys.readouterr().err == ""
