"""Tests for eval_harness.report.render: evidence.md, report.md, audit-queue.md.

Every test drives `render()` against a completed fixture round (see
eval_harness_run_helpers.rounds) and recomputes its own expectations from the
round's attempt records and run.json, using the same pure records.derive_validity
/records.classify the production render() reuses, rather than trusting report.py's
own arithmetic. Only rounds "hang", "retry", "tdd" and "r1" are used, per the task.
"""
import json
import re
from pathlib import Path

import pytest

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

SECTIONS = ("## Run", "## Scores", "## Counts", "## Classification", "## Vetting",
            "## Measurements")


def _run_json(round_) -> dict:
    return json.loads((round_.run / "run.json").read_text(encoding="utf-8"))


def _files(round_) -> tuple:
    return (
        (round_.run / "evidence.md").read_text(encoding="utf-8"),
        (round_.run / "report.md").read_text(encoding="utf-8"),
        (round_.run / "audit-queue.md").read_text(encoding="utf-8"),
    )


def _render(round_) -> tuple:
    report.render(round_.root, round_.run.name)
    return _files(round_)


def _valid_ids(round_) -> list:
    attempts = _attempts(round_)
    return [aid for aid, record in attempts.items()
            if records.derive_validity(record) == "VALID"]


def _write_audit(round_, rows: list) -> None:
    body = "".join(json.dumps(row) + "\n" for row in rows)
    (round_.run / "audit.jsonl").write_text(body, encoding="utf-8")


def _audit_row(attempt_dir: str, verdict="clean", **over) -> dict:
    row = {
        "attempt_dir": attempt_dir, "verdict": verdict, "claim": "", "evidence": "",
        "review_verdict": "clean", "review_findings": [], "review_effort_s": 0.0,
    }
    row.update(over)
    return row


def _block(text: str, ids_in_order: list, target: str) -> str:
    """The slice of `text` from `target`'s first occurrence to the next id's."""
    positions = sorted((text.index(aid), aid) for aid in ids_in_order)
    for i, (pos, aid) in enumerate(positions):
        if aid == target:
            end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
            return text[pos:end]
    raise AssertionError("%r not found in text" % target)


# -- what render writes, and only what render writes -------------------------


@pytest.mark.parametrize("run_id", ["hang", "retry", "tdd", "r1"])
def test_render_writes_only_the_three_files_under_runs_run_id(rounds, run_id):
    round_ = rounds(run_id)
    before = {p.relative_to(round_.root) for p in round_.root.rglob("*") if p.is_file()}

    report.render(round_.root, run_id)

    after = {p.relative_to(round_.root) for p in round_.root.rglob("*") if p.is_file()}
    prefix = Path("runs") / run_id
    assert after - before == {
        prefix / "evidence.md", prefix / "report.md", prefix / "audit-queue.md",
    }


def test_render_is_idempotent_byte_identical_on_repeated_calls(rounds):
    round_ = rounds("r1")
    first = _render(round_)
    second = _render(round_)
    assert first == second


def test_render_never_overwrites_a_consumer_authored_comparison_md(rounds):
    round_ = rounds("tdd")
    sentinel = round_.run / "comparison.md"
    sentinel.write_text("hand-written notes\n", encoding="utf-8")

    _render(round_)
    _render(round_)

    assert sentinel.read_text(encoding="utf-8") == "hand-written notes\n"


# -- evidence.md ---------------------------------------------------------------


def test_evidence_md_has_one_setup_block_per_task_before_any_attempt_block(rounds):
    round_ = rounds("r1")
    run = _run_json(round_)
    evidence, _, _ = _render(round_)

    assert evidence.count("## Setup") == len(run["tasks"])
    first_attempt_pos = min(evidence.index(aid) for aid in _attempts(round_))
    assert evidence.index("## Setup") < first_attempt_pos


def test_evidence_md_blocks_are_ordered_by_task_then_engine_then_attempt(rounds):
    round_ = rounds("retry")
    evidence, _, _ = _render(round_)
    engine_order = [engine["id"] for engine in _run_json(round_)["engines"]]
    attempts = _attempts(round_)

    order = sorted(
        attempts,
        key=lambda aid: (
            int(aid.split("-", 1)[0]),
            engine_order.index(attempts[aid]["engine"]),
            attempts[aid]["attempt"],
        ),
    )
    positions = [evidence.index(aid) for aid in order]
    assert positions == sorted(positions)


def test_a_missing_attempt_json_renders_an_incomplete_block_and_becomes_the_effective_outcome(
    rounds,
):
    round_ = rounds("r1")
    attempts = _attempts(round_)
    cmd1_ids = sorted(
        (aid for aid, record in attempts.items() if record["engine"] == "cmd1"),
        key=lambda aid: attempts[aid]["attempt"],
    )
    last = cmd1_ids[-1]
    stem, last_no = last.rsplit("-a", 1)
    incomplete_id = "%s-a%d" % (stem, int(last_no) + 1)
    incomplete_dir = round_.run / incomplete_id
    incomplete_dir.mkdir()

    try:
        evidence, report_md, _ = _render(round_)

        block = _block(evidence, [*attempts, incomplete_id], incomplete_id)
        assert "INCOMPLETE" in block
        assert "n/a" in block
        # never falls back to the older, real attempt's PASS/FAIL verdict for this engine
        assert stem in report_md
        assert "INCOMPLETE" in report_md
    finally:
        incomplete_dir.rmdir()


# -- report.md: section order, counts, not-started pairs ----------------------


def test_report_md_carries_the_six_sections_in_order(rounds):
    round_ = rounds("r1")
    _, report_md, _ = _render(round_)

    found = [line for line in report_md.splitlines() if line.strip() in SECTIONS]
    assert found == list(SECTIONS)


def _expected_by_engine(round_) -> dict:
    by_engine = {}
    for record in _attempts(round_).values():
        tallies = by_engine.setdefault(record["engine"], dict.fromkeys(
            ("attempts", "PASS", "FAIL", "TIMEOUT", "SUSPECT", "DISCARDED", "INCOMPLETE"), 0))
        tallies["attempts"] += 1
        tallies[record["outcome"]] += 1
    return by_engine


@pytest.mark.parametrize("run_id", ["hang", "retry", "tdd", "r1"])
def test_report_md_counts_match_an_independent_recount_of_the_attempt_records(rounds, run_id):
    round_ = rounds(run_id)
    expected = _expected_by_engine(round_)

    _, report_md, _ = _render(round_)
    counts_section = report_md.split("## Counts", 1)[1].split("## Classification", 1)[0]

    for engine, tallies in expected.items():
        engine_block = re.search(
            re.escape(engine) + r"([\s\S]{0,400}?)(?=\bcmd\d\b|\Z)", counts_section
        )
        assert engine_block, (run_id, engine, counts_section)
        block = engine_block.group(1)
        for label, value in tallies.items():
            assert re.search(r"\b%s\b\D{0,12}?\b%d\b" % (re.escape(label), value), block), (
                run_id, engine, label, value, block,
            )


def test_a_planned_engine_with_no_attempt_directory_is_not_started_and_not_an_attempt(rounds):
    round_ = rounds("r1")
    run_path = round_.run / "run.json"
    original = run_path.read_text(encoding="utf-8")
    run = json.loads(original)
    run["engines"] = [*run["engines"], {"id": "cmd3", "command": "cmd:/nonexistent/engine"}]
    run_path.write_text(json.dumps(run), encoding="utf-8")

    try:
        _, report_md, _ = _render(round_)

        assert "NOT_STARTED" in report_md
        counts_section = report_md.split("## Counts", 1)[1].split("## Classification", 1)[0]
        assert re.search(r"cmd3[\s\S]{0,200}?\bnot_started\b", counts_section) or re.search(
            r"not_started[\s\S]{0,200}?\bcmd3\b", counts_section
        ), counts_section
    finally:
        run_path.write_text(original, encoding="utf-8")


# -- the f (flagged-audit) field -----------------------------------------------


def test_f_is_pending_zero_of_n_with_the_audit_incomplete_sentence_when_no_audit_jsonl(rounds):
    round_ = rounds("r1")
    valid_ids = _valid_ids(round_)
    assert valid_ids  # the fixture must carry at least one VALID attempt, or this proves nothing

    _, report_md, _ = _render(round_)

    assert ("pending (0 of %d audited)" % len(valid_ids)) in report_md
    assert "Audit incomplete: no decision rule may be applied to these counts." in report_md


def test_f_is_pending_k_of_n_with_a_partial_audit_file(rounds):
    round_ = rounds("r1")
    valid_ids = _valid_ids(round_)
    assert len(valid_ids) >= 2
    _write_audit(round_, [_audit_row(valid_ids[0])])

    _, report_md, _ = _render(round_)

    assert ("pending (1 of %d audited)" % len(valid_ids)) in report_md
    assert "Audit incomplete: no decision rule may be applied to these counts." in report_md


def test_f_is_a_plain_number_without_the_sentence_once_every_valid_attempt_is_audited(rounds):
    round_ = rounds("r1")
    valid_ids = _valid_ids(round_)
    assert valid_ids
    _write_audit(round_, [_audit_row(aid) for aid in valid_ids])

    _, report_md, _ = _render(round_)

    assert "Audit incomplete" not in report_md
    assert "pending (" not in report_md


def test_f_counts_only_flagged_verdicts_on_valid_attempts(rounds):
    round_ = rounds("r1")
    valid_ids = _valid_ids(round_)
    assert len(valid_ids) >= 2
    rows = [_audit_row(valid_ids[0], verdict="flagged", claim="c", evidence="e")]
    rows += [_audit_row(aid) for aid in valid_ids[1:]]
    _write_audit(round_, rows)

    _, report_md, _ = _render(round_)

    counts_section = report_md.split("## Counts", 1)[1].split("## Classification", 1)[0]
    assert re.search(r"\bf\b\D{0,12}?\b1\b", counts_section), counts_section


def test_f_is_zero_with_no_audit_file_when_there_are_zero_valid_attempts(rounds):
    round_ = rounds("hang")
    assert not _valid_ids(round_)

    _, report_md, _ = _render(round_)

    counts_section = report_md.split("## Counts", 1)[1].split("## Classification", 1)[0]
    assert re.search(r"\bf\b\D{0,12}?\b0\b", counts_section), counts_section
    assert "Audit incomplete" not in report_md


# -- malformed / duplicate / contradictory input is refused --------------------


def test_render_rejects_a_malformed_audit_line_naming_it_and_leaves_output_unchanged(rounds):
    round_ = rounds("r1")
    before = _render(round_)
    audit_path = round_.run / "audit.jsonl"
    audit_path.write_text(
        '{"attempt_dir": SENTINEL_BROKEN_JSON\n', encoding="utf-8"
    )

    try:
        with pytest.raises(Exception) as failure:
            report.render(round_.root, round_.run.name)

        assert "SENTINEL_BROKEN_JSON" in str(failure.value)
        assert _files(round_) == before
    finally:
        audit_path.unlink()


def test_render_rejects_a_duplicate_attempt_dir_in_audit_jsonl_naming_it(rounds):
    round_ = rounds("r1")
    valid_ids = _valid_ids(round_)
    assert valid_ids
    _write_audit(
        round_,
        [_audit_row(valid_ids[0]), _audit_row(valid_ids[0], verdict="unverifiable")],
    )

    try:
        with pytest.raises(Exception) as failure:
            report.render(round_.root, round_.run.name)

        assert valid_ids[0] in str(failure.value)
    finally:
        (round_.run / "audit.jsonl").unlink()


def test_render_rejects_a_contradictory_stored_outcome_via_classify_rederivation(rounds):
    round_ = rounds("tdd")
    attempts = _attempts(round_)
    fail_id = next(aid for aid, r in attempts.items() if r["outcome"] == "FAIL")
    record_path = round_.run / fail_id / "attempt.json"
    original = record_path.read_text(encoding="utf-8")
    record = json.loads(original)
    record["outcome"], record["class"] = "PASS", None
    record_path.write_text(json.dumps(record), encoding="utf-8")

    try:
        with pytest.raises(Exception) as failure:
            report.render(round_.root, round_.run.name)

        assert fail_id in str(failure.value)
    finally:
        record_path.write_text(original, encoding="utf-8")


# -- audit-queue.md --------------------------------------------------------------


def test_audit_queue_lists_every_valid_attempt_pending_where_no_row_exists(rounds):
    round_ = rounds("r1")
    valid_ids = _valid_ids(round_)
    assert valid_ids

    _, _, audit_queue = _render(round_)

    for aid in valid_ids:
        assert aid in audit_queue
    assert audit_queue.count("PENDING") == len(valid_ids)


def test_audit_queue_shows_the_stored_verdict_once_a_row_exists(rounds):
    round_ = rounds("r1")
    valid_ids = _valid_ids(round_)
    assert len(valid_ids) >= 1
    _write_audit(round_, [_audit_row(valid_ids[0], verdict="unverifiable")])

    _, _, audit_queue = _render(round_)

    block = _block(audit_queue, valid_ids, valid_ids[0])
    assert "unverifiable" in block
    assert "PENDING" not in block
