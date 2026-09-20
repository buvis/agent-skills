"""Field-content assertions for eval_harness.report.render.

Companion to test_report.py, which covers structural properties (block counts,
section order, counts recount). Every test here recomputes the exact rendered
line for one block or section kind straight from the round's real attempt.json,
run.json, vetting.json, audit.jsonl and sibling out.txt/wrapper.txt/gate.txt/
session.jsonl files - never from a rendered file, never hardcoded from a run
looked at once. Rounds used: "r1" (description, two engines), "tdd" (tdd, one
PASS and one FAIL:test-mutation engine), "stray" (single engine).
"""
import re
import shlex

from eval_harness import records, report

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
from test_report import _audit_row, _block, _render, _run_json, _valid_ids, _write_audit

FAIL_CLASSES = ("test-mutation", "stray-edit", "no-edit", "dropped-a-file", "vacuous-tests",
                "logic-error")
# The record field whose value decided each FAIL class (report.py's own comment names the
# same source: records._judge_evidence/_judge_gates). A fixed contract, not a computed value.
CLASS_FIELD = {
    "test-mutation": "oracle_intact", "stray-edit": "stray", "no-edit": "changed",
    "dropped-a-file": "dropped", "vacuous-tests": "gates.ablate", "logic-error": "gates",
}


def _or(value, fallback: str):
    return fallback if value is None else value


def _engine_block(counts_section: str, engine: str) -> str:
    """The chunk of a ## Counts section between two blank lines that belongs to `engine`."""
    for chunk in counts_section.split("\n\n"):
        first = chunk.splitlines()[0] if chunk else ""
        if first in (engine, "%s: not_started (NOT_STARTED)" % engine):
            return chunk
    raise AssertionError("no Counts block for %r in %r" % (engine, counts_section))


# -- evidence.md: per-attempt field content, a real (non-INCOMPLETE) record each time --------


def test_evidence_tree_line_renders_the_records_clone_path(rounds):
    round_ = rounds("r1")
    attempts = _attempts(round_)
    aid, record = next(iter(attempts.items()))

    evidence, _, _ = _render(round_)

    block = _block(evidence, list(attempts), aid)
    assert ("Tree: %s" % record["clone"]) in block.splitlines()


def test_evidence_engine_identity_line_renders_the_records_identity(rounds):
    round_ = rounds("r1")
    attempts = _attempts(round_)
    aid, record = next(iter(attempts.items()))
    identity = _or(record["engine_run"]["identity"], "n/a")

    evidence, _, _ = _render(round_)

    block = _block(evidence, list(attempts), aid)
    assert ("Engine identity: `%s`" % identity) in block.splitlines()


def test_evidence_dispatch_line_renders_the_records_argv_shlex_joined(rounds):
    round_ = rounds("r1")
    attempts = _attempts(round_)
    aid, record = next(iter(attempts.items()))

    evidence, _, _ = _render(round_)

    block = _block(evidence, list(attempts), aid)
    assert ("Dispatch: `%s`" % shlex.join(record["engine_run"]["argv"])) in block.splitlines()


def test_evidence_baseline_line_renders_baseline_rc_and_first_failure_from_the_record(rounds):
    round_ = rounds("r1")
    attempts = _attempts(round_)
    aid, record = next((a, r) for a, r in attempts.items() if r["baseline"] is not None)
    baseline = record["baseline"]

    evidence, _, _ = _render(round_)

    block = _block(evidence, list(attempts), aid)
    expected = "Baseline exit code: %s; first failure: `%s`" % (
        _or(baseline["rc"], "n/a"), _or(baseline["first_failure"], "n/a"),
    )
    assert expected in block.splitlines()


def test_evidence_own_gate_ablate_exit_codes_line_renders_the_records_gate_rcs(rounds):
    round_ = rounds("r1")
    attempts = _attempts(round_)
    aid, record = next(
        (a, r) for a, r in attempts.items()
        if r["gates"]["own"] is not None and r["gates"]["gate"] is not None
        and r["gates"]["ablate"] is not None
    )
    gates = record["gates"]

    evidence, _, _ = _render(round_)

    block = _block(evidence, list(attempts), aid)
    expected = "Own/gate/ablation exit codes: %s / %s / %s" % (
        _or(gates["own"]["rc"], "n/a"), _or(gates["gate"]["rc"], "n/a"),
        _or(gates["ablate"]["rc"], "n/a"),
    )
    assert expected in block.splitlines()


def test_evidence_result_line_renders_bare_outcome_or_outcome_colon_class_for_real_records(
    rounds,
):
    round_ = rounds("tdd")
    attempts = _attempts(round_)
    pass_aid, pass_record = next((a, r) for a, r in attempts.items() if r["class"] is None)
    fail_aid, fail_record = next((a, r) for a, r in attempts.items() if r["class"] is not None)

    evidence, _, _ = _render(round_)

    ids_in_order = list(attempts)
    pass_block = _block(evidence, ids_in_order, pass_aid)
    fail_block = _block(evidence, ids_in_order, fail_aid)
    assert ("Result: %s" % pass_record["outcome"]) in pass_block.splitlines()
    assert (
        "Result: %s:%s" % (fail_record["outcome"], fail_record["class"])
    ) in fail_block.splitlines()


# -- report.md: section field content, one row each ------------------------------------------


def test_run_section_renders_run_id_started_tasks_engines_flags_versions_and_server(rounds):
    round_ = rounds("r1")
    run = _run_json(round_)
    engine_order = [engine["id"] for engine in run["engines"]]

    _, report_md, _ = _render(round_)
    lines = report_md.split("## Run", 1)[1].split("## Scores", 1)[0].splitlines()

    assert ("run_id: %s" % run["run_id"]) in lines
    assert ("started: %s" % run["started"]) in lines
    assert ("tasks: %d" % len(run["tasks"])) in lines
    assert ("engines: %s" % ", ".join(engine_order)) in lines
    for key, value in sorted(run["config"].items()):
        assert ("%s: %s" % (key, value)) in lines
    for key, value in sorted(run["versions"].items()):
        assert ("%s: %s" % (key, _or(value, "unavailable"))) in lines
    for key in records.SERVER_KEYS:
        assert ("%s: %s" % (key, _or(run["server"][key], "unavailable"))) in lines


def test_vetting_section_renders_baseline_canonical_rc_and_necessity_holds_for_a_task(rounds):
    round_ = rounds("r1")
    vetting = report._load_vetting(round_.root, _run_json(round_)["tasks"][0])
    baseline, canonical = vetting["baseline"], vetting["canonical"]

    _, report_md, _ = _render(round_)
    lines = report_md.split("## Vetting", 1)[1].split("## Measurements", 1)[0].splitlines()

    assert ("  baseline rc: %s" % _or(baseline["rc"] if baseline else None, "unavailable")
            ) in lines
    assert ("  canonical rc: %s" % _or(canonical["rc"] if canonical else None, "unavailable")
            ) in lines
    for path, necessity in sorted(vetting["necessity"].items()):
        assert ("  necessity %s: holds=%s" % (path, necessity["holds"])) in lines


def test_classification_section_renders_engine_task_class_and_field_for_a_fail_record(rounds):
    round_ = rounds("tdd")
    attempts = _attempts(round_)
    _, record = next((a, r) for a, r in attempts.items() if r["outcome"] == "FAIL")

    _, report_md, _ = _render(round_)
    section = report_md.split("## Classification", 1)[1].split("## Vetting", 1)[0]

    expected = "engine: %s | task: %d | class: %s | field: %s" % (
        record["engine"], record["task"], record["class"], CLASS_FIELD[record["class"]],
    )
    assert expected in section.splitlines()


# -- report.md: exact counts recount, a single-engine run, a retry-then-incomplete pair ------


def _expected_drops(round_) -> int:
    return sum(1 for r in _attempts(round_).values()
              if r["outcome"] == "FAIL" and r["class"] == "dropped-a-file")


def _expected_scored(round_) -> int:
    """Tasks whose every engine's highest-numbered attempt has a launched record."""
    run = _run_json(round_)
    attempts = _attempts(round_)
    names = [p.name for p in round_.run.iterdir() if p.is_dir()]
    scored = 0
    for task in run["tasks"]:
        launched = True
        for engine in run["engines"]:
            prefix = "%d-%s-a" % (task["id"], engine["id"])
            numbers = [int(n[len(prefix):]) for n in names
                      if n.startswith(prefix) and n[len(prefix):].isdigit()]
            record = attempts.get("%s%d" % (prefix, max(numbers))) if numbers else None
            if record is None or record["engine_run"]["launch"] not in ("started", "unknown"):
                launched = False
        scored += launched
    return scored


def _expected_not_started(round_) -> int:
    run = _run_json(round_)
    attempts = _attempts(round_)
    return sum(
        1 for task in run["tasks"] for engine in run["engines"]
        if not any(aid.startswith("%d-%s-a" % (task["id"], engine["id"])) for aid in attempts)
    )


def test_counts_section_renders_exact_fail_class_lines_and_drops_scored_not_started(rounds):
    round_ = rounds("tdd")
    attempts = _attempts(round_)
    engine_order = [e["id"] for e in _run_json(round_)["engines"]]

    _, report_md, _ = _render(round_)
    counts_section = report_md.split("## Counts", 1)[1].split("## Classification", 1)[0]

    for engine in engine_order:
        block = _engine_block(counts_section, engine)
        recs = [r for r in attempts.values() if r["engine"] == engine]
        for cls in FAIL_CLASSES:
            n = sum(1 for r in recs if r["outcome"] == "FAIL" and r["class"] == cls)
            assert ("  FAIL:%s: %d" % (cls, n)) in block.splitlines(), (engine, cls)

    lines = counts_section.splitlines()
    assert ("drops: %d" % _expected_drops(round_)) in lines
    assert ("scored: %d" % _expected_scored(round_)) in lines
    assert ("not_started: %d" % _expected_not_started(round_)) in lines


def test_single_engine_run_renders_the_one_configured_engine_and_never_invents_a_second(rounds):
    round_ = rounds("stray")
    run = _run_json(round_)
    assert len(run["engines"]) == 1
    only_engine = run["engines"][0]["id"]
    assert {r["engine"] for r in _attempts(round_).values()} == {only_engine}

    evidence, report_md, audit_queue = _render(round_)

    for text in (evidence, report_md, audit_queue):
        assert only_engine in text
        assert set(re.findall(r"cmd\d+", text)) <= {only_engine}


def test_retry_then_incomplete_pair_renders_exact_scores_and_counts_lines_and_excludes_scored(
    rounds,
):
    round_ = rounds("r1")
    attempts = _attempts(round_)
    cmd1_ids = [aid for aid, r in attempts.items() if r["engine"] == "cmd1"]
    assert len(cmd1_ids) == 1
    stem, last_no = cmd1_ids[0].rsplit("-a", 1)
    incomplete_dir = round_.run / ("%s-a%d" % (stem, int(last_no) + 1))
    incomplete_dir.mkdir()

    try:
        _, report_md, _ = _render(round_)

        scores_section = report_md.split("## Scores", 1)[1].split("## Counts", 1)[0]
        assert "  cmd1: INCOMPLETE (attempts: 2)" in scores_section.splitlines()

        counts_section = report_md.split("## Counts", 1)[1].split("## Classification", 1)[0]
        cmd1_block = _engine_block(counts_section, "cmd1")
        assert "  attempts: 2" in cmd1_block.splitlines()
        assert "  INCOMPLETE: 1" in cmd1_block.splitlines()
        assert ("scored: %d" % _expected_scored(round_)) in counts_section.splitlines()
    finally:
        incomplete_dir.rmdir()


# -- report.md: Measurements null/zero telemetry ----------------------------------------------


def test_measurements_section_renders_unavailable_for_null_usage_and_zero_for_a_real_effort(
    rounds,
):
    round_ = rounds("r1")
    attempts = _attempts(round_)
    valid_ids = _valid_ids(round_)
    assert valid_ids
    aid = next(
        a for a in valid_ids if any(v is None for v in attempts[a]["engine_run"]["usage"].values())
    )
    null_key = next(k for k, v in attempts[aid]["engine_run"]["usage"].items() if v is None)
    _write_audit(round_, [_audit_row(aid, review_effort_s=0)])

    try:
        _, report_md, _ = _render(round_)
    finally:
        (round_.run / "audit.jsonl").unlink()

    section = report_md.split("## Measurements", 1)[1]
    lines = _block(section, list(attempts), aid).splitlines()
    assert ("  %s: unavailable" % null_key) in lines
    assert "  review_effort_s: 0" in lines


# -- audit-queue.md: field content for one VALID attempt's real files -------------------------


def test_audit_queue_renders_final_message_session_log_gate_exit_and_changed_files(rounds):
    round_ = rounds("r1")
    attempts = _attempts(round_)
    valid_ids = _valid_ids(round_)
    assert valid_ids
    aid = valid_ids[0]
    record = attempts[aid]
    attempt_dir = round_.run / aid
    out_path, session_log_path = attempt_dir / "out.txt", attempt_dir / "session.jsonl"
    gate = record["gates"]["gate"]
    changed = [c["path"] for c in record["changed"]] if record["changed"] else []
    _write_audit(round_, [_audit_row(aid, verdict="unverifiable")])

    try:
        _, _, audit_queue = _render(round_)
    finally:
        (round_.run / "audit.jsonl").unlink()

    lines = _block(audit_queue, valid_ids, aid).splitlines()
    assert ("final message: %s (%s bytes)" % (
        out_path if out_path.is_file() else "unavailable",
        _or(record["engine_run"]["final_message_bytes"], "unavailable"),
    )) in lines
    assert ("session log: %s" % (session_log_path if session_log_path.is_file() else "none")
            ) in lines
    assert ("gate exit code: %s" % (_or(gate["rc"], "n/a") if gate else "n/a")) in lines
    assert ("changed files: %s" % (", ".join(changed) if changed else "none")) in lines
    assert "verdict: unverifiable" in lines
