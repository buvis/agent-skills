"""Tests for funnel.render_yield(): the yield report it formats out of a
run's counts, without touching a file or a model."""

import os
import re
from pathlib import Path

import funnel
import pytest


def test_render_yield_performs_no_subprocess_calls_or_file_io(monkeypatch):
    """The report is string formatting over the counts it was handed, and
    nothing else. Listing a directory is barred alongside reading and running,
    because a renderer that goes looking for the newest `-proposals` directory
    names whatever some other run left behind rather than what this run
    published. The counts carry the distil keys: a guard that never enters the
    distil branch guards the one branch that has no reason to touch a disk."""

    def fail_subprocess(*args, **kwargs):
        raise AssertionError("render_yield must not invoke subprocess")

    def fail_open(*args, **kwargs):
        raise AssertionError("render_yield must not perform file I/O")

    def fail_listing(*args, **kwargs):
        raise AssertionError("render_yield must not list a directory")

    monkeypatch.setattr(funnel.subprocess, "run", fail_subprocess)
    monkeypatch.setattr("builtins.open", fail_open)
    listing_calls = ((Path, "glob"), (Path, "rglob"), (Path, "iterdir"), (os, "scandir"), (os, "listdir"))
    for owner, attribute in listing_calls:
        monkeypatch.setattr(owner, attribute, fail_listing)
    counts = {
        "transcripts_read": 3,
        "slices_matched": 2,
        "slices_kept": 1,
        "survivors": 1,
        "proposals": 1,
        "discards": 0,
        "new_vs_update": (1, 0),
        "skipped_by_limit": 0,
        "dedup_errors": 0,
        "claude_checkup_version": "0.2.2",
    }

    result = funnel.render_yield(counts)

    assert isinstance(result, str)


def test_render_yield_prints_every_stage_ending_in_zero_when_a_run_finds_nothing():
    counts = {
        "transcripts_read": 0,
        "slices_matched": 0,
        "slices_kept": 0,
        "survivors": 0,
        "claude_checkup_version": "0.2.2",
    }

    result = funnel.render_yield(counts)

    lines = [line for line in result.splitlines() if line.strip()]
    count_lines = lines[:4]
    assert len(count_lines) == 4
    for line in count_lines:
        assert line.rstrip().endswith("0")


def test_render_yield_prints_key_value_line_for_each_count_when_values_are_nonzero():
    counts = {
        "transcripts_read": 12,
        "slices_matched": 8,
        "slices_kept": 5,
        "survivors": 3,
        "claude_checkup_version": "0.2.2",
    }

    result = funnel.render_yield(counts)

    assert "transcripts_read: 12" in result
    assert "slices_matched: 8" in result
    assert "slices_kept: 5" in result
    assert "survivors: 3" in result


def test_render_yield_states_the_resolved_claude_checkup_version():
    counts = {
        "transcripts_read": 12,
        "slices_matched": 8,
        "slices_kept": 5,
        "survivors": 3,
        "claude_checkup_version": "0.2.2",
    }

    result = funnel.render_yield(counts)

    assert "claude_checkup_version: 0.2.2" in result


def test_render_yield_renders_none_survivors_as_n_a_for_a_dry_run():
    counts = {
        "transcripts_read": 5,
        "slices_matched": 3,
        "slices_kept": 2,
        "survivors": None,
        "claude_checkup_version": "0.2.2",
    }

    result = funnel.render_yield(counts)

    assert "survivors: n/a" in result


def test_render_yield_ends_with_how_to_proceed_line_naming_the_audit_results_directory():
    counts = {
        "transcripts_read": 5,
        "slices_matched": 3,
        "slices_kept": 2,
        "survivors": 1,
        "claude_checkup_version": "0.2.2",
    }

    result = funnel.render_yield(counts)

    last_line = result.rstrip("\n").splitlines()[-1]
    assert last_line.startswith("How to proceed:")
    assert "dev/local/audit-results/" in last_line


_DISTIL_LABELS = ["proposals", "discards", "new_vs_update", "skipped_by_limit", "dedup_errors"]


def _five_key_counts():
    """The pre-distil counts dict every existing render_yield caller passes:
    not one of the five distil keys is present."""
    return {
        "transcripts_read": 5,
        "slices_matched": 3,
        "slices_kept": 2,
        "survivors": 1,
        "claude_checkup_version": "0.2.2",
    }


def test_render_yield_still_renders_a_legacy_five_key_counts_dict_without_a_key_error():
    """Pins the counts.get contract directly, so rewriting a distil line to
    counts["..."] fails here instead of in eleven unrelated tests.

    Also pins the caller's dict as read-only. `counts.setdefault(label, None)`
    renders the same text but hands a five-key caller back a ten-key dict,
    which is not what "pure string formatting" means: anything that reuses,
    compares or re-serialises the dict after the call sees the five keys the
    renderer invented."""
    counts = _five_key_counts()
    before = dict(counts)

    result = funnel.render_yield(counts)

    assert "survivors: 1" in result
    assert "claude_checkup_version: 0.2.2" in result
    assert counts == before


def test_render_yield_orders_the_distil_lines_after_survivors_and_before_the_version():
    result = funnel.render_yield(_five_key_counts())

    labels = [
        match.group(1)
        for match in (re.match(r"([a-z_]+): ", line) for line in result.splitlines())
        if match
    ]

    assert labels == [
        "transcripts_read",
        "slices_matched",
        "slices_kept",
        "survivors",
        *_DISTIL_LABELS,
        "claude_checkup_version",
    ]


@pytest.mark.parametrize("set_to_none", [False, True], ids=["key_missing", "key_none"])
@pytest.mark.parametrize("label", _DISTIL_LABELS)
def test_render_yield_renders_a_distil_line_as_n_a_when_the_stage_did_not_produce_it(label, set_to_none):
    counts = _five_key_counts()
    if set_to_none:
        counts[label] = None

    result = funnel.render_yield(counts)

    assert f"{label}: n/a" in result


@pytest.mark.parametrize(
    "distil_counts, expected_lines",
    [
        (
            {"proposals": 4, "discards": 2, "new_vs_update": (5, 3), "skipped_by_limit": 7, "dedup_errors": 1},
            ["proposals: 4", "discards: 2", "new_vs_update: 5/3", "skipped_by_limit: 7", "dedup_errors: 1"],
        ),
        (
            {"proposals": 0, "discards": 0, "new_vs_update": (0, 0), "skipped_by_limit": 0, "dedup_errors": 0},
            ["proposals: 0", "discards: 0", "new_vs_update: 0/0", "skipped_by_limit: 0", "dedup_errors: 0"],
        ),
    ],
    ids=["nonzero", "all_zero"],
)
def test_render_yield_renders_the_integer_distil_counts_the_stage_produced(distil_counts, expected_lines):
    """A stage that ran and yielded nothing reports 0, never n/a: n/a means
    the stage did not run. `skipped_by_limit: 0` is the normal uncapped run,
    so treating a zero as "missing" mislabels the most common case."""
    counts = _five_key_counts()
    counts.update(distil_counts)

    result = funnel.render_yield(counts)

    for expected in expected_lines:
        assert expected in result


@pytest.mark.parametrize(
    "pair, expected",
    [((3, 1), "new_vs_update: 3/1"), ((7, 4), "new_vs_update: 7/4"), ((0, 2), "new_vs_update: 0/2")],
    ids=["three_one", "seven_four", "zero_two"],
)
def test_render_yield_joins_a_populated_new_vs_update_pair_with_a_slash(pair, expected):
    """`new_vs_update` carries the (new, update) counts as a pair of ints, not
    a pre-formatted "3/1" string: render_yield owns the presentation, so a
    later "simplification" that moves the slash into the caller fails here.
    Both elements must be read: `(7, 4)` cannot be reconstructed from the
    first element and the pair's length, and `(0, 2)` cannot be reconstructed
    by treating a zero as absent."""
    counts = _five_key_counts()
    counts["new_vs_update"] = pair

    result = funnel.render_yield(counts)

    assert expected in result


def test_render_yield_names_no_proposals_path_when_the_distil_stage_did_not_run():
    """A five-key caller ran no distil stage, so there is no published
    proposals directory for the paragraph to point at. It used to name a fixed
    `dev/local/audit-results/proposals/` here whatever the run did - a
    directory nothing ever creates, so a reader who follows the report finds
    nothing. The report destination is still named, because that file was
    written, but no path-shaped token may claim a proposals directory.

    Where the stage DID run, the directory it published is the one that has to
    be named. That is pinned end to end in test_funnel_distil_publication.py,
    against the directory on disk rather than against a counts key here."""
    result = funnel.render_yield(_five_key_counts())

    how_to_proceed = [line for line in result.splitlines() if line.startswith("How to proceed:")]

    assert len(how_to_proceed) == 1
    line = how_to_proceed[0]
    path_tokens = {token.strip(".,;:()'\"") for token in line.split() if "/" in token}
    assert any("dev/local/audit-results" in token for token in path_tokens)
    assert [token for token in path_tokens if "proposal" in token.lower()] == []
    assert "audit-results/proposals" not in result
