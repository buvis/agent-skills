"""Tests for sweep.py: scan."""
import concurrent.futures
import json
import os
import re
import subprocess
import threading
import time
from pathlib import Path

import pytest

import sweep
from sweep_test_helpers import (
    _git_status_porcelain,
    _is_running,
    _plant_matches,
    _recorded_pids,
    _still_running_after,
    _write_tree_shim,
)


# -- scan ---------------------------------------------------------------


def test_scan_caps_hits_at_default_cap_and_records_suppressed_count_for_overflow(tmp_path):
    repo = _plant_matches(tmp_path / "repo", "SWEEPMARKER", 25)

    hits, suppressed, _failed = sweep.scan("SWEEPMARKER", "rg", [repo])

    repo_hits = [hit for hit in hits if hit["repo"] == str(repo)]
    assert len(repo_hits) == 20
    assert suppressed[str(repo)] == 5
    for hit in repo_hits:
        assert hit["file"]
        assert hit["line"] == 1
        assert "SWEEPMARKER" in hit["snippet"]


def test_scan_omits_suppressed_entry_for_repo_with_hits_under_cap(tmp_path):
    repo = _plant_matches(tmp_path / "repo", "UNDERMARKER", 3)

    hits, suppressed, _failed = sweep.scan("UNDERMARKER", "rg", [repo])

    repo_hits = [hit for hit in hits if hit["repo"] == str(repo)]
    assert len(repo_hits) == 3
    assert str(repo) not in suppressed
    for hit in repo_hits:
        assert hit["line"] == 1


def test_scan_applies_cap_independently_per_repo(tmp_path):
    repo_a = _plant_matches(tmp_path / "repo_a", "MULTIMARKER", 8)
    repo_b = _plant_matches(tmp_path / "repo_b", "MULTIMARKER", 3)

    hits, suppressed, _failed = sweep.scan("MULTIMARKER", "rg", [repo_a, repo_b], cap=5)

    hits_a = [hit for hit in hits if hit["repo"] == str(repo_a)]
    hits_b = [hit for hit in hits if hit["repo"] == str(repo_b)]
    assert len(hits_a) == 5
    assert len(hits_b) == 3
    assert suppressed[str(repo_a)] == 3
    assert str(repo_b) not in suppressed


def test_scan_hit_lang_field_derived_from_ast_grep_languages_extension_map(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "sample.py").write_text("LANGMARKER python line\n")
    (repo / "sample.txt").write_text("LANGMARKER text line\n")

    hits, _suppressed, _failed = sweep.scan("LANGMARKER", "rg", [repo])

    by_ext = {Path(hit["file"]).suffix: hit["lang"] for hit in hits}
    assert by_ext[".py"] == "python"
    assert by_ext[".txt"] is None


def test_scan_is_read_only_and_leaves_repo_contents_unchanged(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    tracked = repo / "tracked.txt"
    tracked.write_text("READONLYMARKER content\n")
    subprocess.run(["git", "init", "-q"], cwd=str(repo), check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "add", "tracked.txt"], check=True, capture_output=True
    )
    original_bytes = tracked.read_bytes()
    original_status = _git_status_porcelain(repo)

    sweep.scan("READONLYMARKER", "rg", [repo])

    assert tracked.read_bytes() == original_bytes
    new_status = _git_status_porcelain(repo)
    assert new_status == original_status


def test_scan_supports_astgrep_kind_and_returns_matching_hits(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "sample.py").write_text('print("hi")\n')

    hits, _suppressed, _failed = sweep.scan("print($X)", "astgrep", [repo])

    assert len(hits) >= 1
    hit = hits[0]
    assert hit["repo"] == str(repo)
    assert hit["file"].endswith("sample.py")
    assert hit["line"] == 1
    assert hit["lang"] == "python"
    assert "print" in hit["snippet"]


# -- scan: dash-prefixed patterns --------------------------------------------


def test_scan_finds_a_dash_prefixed_pattern_via_rg(tmp_path):
    # Invariant: a pattern that starts with "-" is searched for, never parsed
    # as one of rg's own flags. scan() passes "--" before the pattern; drop
    # that separator and this test goes red.
    repo = _plant_matches(tmp_path / "repo", "-x", 1)

    hits, _suppressed, _failed = sweep.scan("-x", "rg", [repo])

    repo_hits = [hit for hit in hits if hit["repo"] == str(repo)]
    assert len(repo_hits) == 1
    assert "-x" in repo_hits[0]["snippet"]


# -- scan: one unscannable repo must not lose the others ---------------------


def test_scan_returns_good_repos_hits_when_one_repo_is_unscannable(tmp_path):
    repo_a = _plant_matches(tmp_path / "repo_a", "RESILIENCEMARKER", 1)
    bad_repo = tmp_path / "does-not-exist"
    repo_b = _plant_matches(tmp_path / "repo_b", "RESILIENCEMARKER", 1)

    hits, _suppressed, _failed = sweep.scan(
        "RESILIENCEMARKER", "rg", [repo_a, bad_repo, repo_b]
    )

    hit_repos = {hit["repo"] for hit in hits}
    assert hit_repos == {str(repo_a), str(repo_b)}


def test_scan_surfaces_an_unscannable_repo_instead_of_dropping_it_silently(
    tmp_path,
):
    # Shape assumed: scan() widens its return to a 3-tuple
    # (hits, suppressed, failed), so every existing
    # "hits, suppressed = sweep.scan(...)" call site in this file gains a
    # third, discarded element. `failed` maps str(repo) to a non-empty
    # reason string for repos that could not be scanned at all -- a
    # channel distinct from `suppressed` (which stays cap-overflow-only),
    # so a failed repo can never be misread as "scanned but truncated".
    repo_a = _plant_matches(tmp_path / "repo_a", "FAILSURFACEMARKER", 1)
    bad_repo = tmp_path / "does-not-exist"
    repo_b = _plant_matches(tmp_path / "repo_b", "FAILSURFACEMARKER", 1)

    _hits, suppressed, failed = sweep.scan(
        "FAILSURFACEMARKER", "rg", [repo_a, bad_repo, repo_b]
    )

    assert str(bad_repo) in failed
    assert failed[str(bad_repo)]  # carries a non-empty reason
    assert str(bad_repo) not in suppressed


def test_scan_records_repo_as_failed_when_search_tool_is_unresolvable(
    tmp_path, monkeypatch
):
    # resolve_ast_grep() raises RuntimeError when neither ast-grep nor mise
    # is on PATH. scan() must catch that and record the repo as failed
    # instead of letting the failure escape.
    empty_path_dir = tmp_path / "empty_path"
    empty_path_dir.mkdir()
    monkeypatch.setenv("PATH", str(empty_path_dir))  # neither ast-grep nor mise here
    repo = tmp_path / "repo"
    repo.mkdir()
    (repo / "sample.py").write_text("print(1)\n")

    hits, _suppressed, failed = sweep.scan("print($X)", "astgrep", [repo])

    assert hits == []
    assert str(repo) in failed
    assert failed[str(repo)]  # carries a non-empty reason


# -- scan: every subprocess call carries a timeout ---------------------------


def test_scan_reports_a_hung_search_as_a_failed_repo_without_blocking(
    tmp_path, monkeypatch, write_executable_stub
):
    # Shape assumed for the failure channel, consistent with the tests
    # above: scan() returns a 3-tuple (hits, suppressed, failed), and a
    # repo whose search could not complete (here, timed out) is surfaced
    # as a key in `failed`, distinct from `suppressed` (cap-overflow-only).
    # Shape assumed for the time budget itself: scan() gains an optional
    # `timeout` keyword (seconds), mirroring the existing `cap` keyword, so
    # this test can use a small budget instead of waiting on whatever
    # production-sized default the fix picks.
    write_executable_stub(tmp_path, "rg", "hung; sleep 5")
    monkeypatch.setenv("PATH", f"{tmp_path}{os.pathsep}{os.environ['PATH']}")

    if os.name == "nt":
        # The one simulated leg in this suite. Windows has no compiler-free
        # way to build an arg-agnostic sleeping executable: `executable=`
        # refuses a .cmd, and a copied python.exe exits on the leading
        # `--json` before it can sleep. So the hang is denied at the call
        # boundary instead of inside a child. The wrapper reads its behaviour
        # off the `timeout` kwarg it receives -- sleeping the full 5s and
        # raising nothing when there is none -- because scan() catches bare
        # Exception, so an unconditional raise would keep this leg green even
        # after `timeout=` was deleted from _run_rg.
        real_run = subprocess.run

        def hung_run(*args, timeout=None, **kwargs):
            time.sleep(5 if timeout is None else timeout)
            if timeout is None:
                return real_run(*args, **kwargs)
            raise subprocess.TimeoutExpired(args[0], timeout)

        monkeypatch.setattr(subprocess, "run", hung_run)

    hung_repo = tmp_path / "hung_repo"
    hung_repo.mkdir()

    started = time.monotonic()
    hits, suppressed, failed = sweep.scan(
        "HANGMARKER", "rg", [hung_repo], timeout=0.2
    )
    elapsed = time.monotonic() - started

    assert elapsed < 3  # far short of the fake tool's 5s sleep
    assert hits == []
    assert str(hung_repo) in failed
    assert failed[str(hung_repo)]  # carries a non-empty reason
    assert str(hung_repo) not in suppressed


# -- scan: repos are searched in parallel, reported in registry order --------


def _stub_hit(repo):
    return {
        "repo": str(repo),
        "file": "match.txt",
        "line": 1,
        "snippet": "PARALLELMARKER",
        "lang": None,
    }


def _make_repos(tmp_path, names):
    repos = []
    for name in names:
        repo = tmp_path / name
        repo.mkdir()
        repos.append(repo)
    return repos


def _rg_match_lines(count):
    return "".join(
        json.dumps(
            {
                "type": "match",
                "data": {
                    "path": {"text": "match.txt"},
                    "line_number": line,
                    "lines": {"text": "PARALLELMARKER\n"},
                },
            }
        )
        + "\n"
        for line in range(1, count + 1)
    )


@pytest.mark.parametrize("repo_count", [2, 4, 5])
def test_scan_runs_repo_searches_concurrently(tmp_path, monkeypatch, repo_count):
    # Binds to overlap, never to a clock: the barrier only releases once all
    # repo searches are in flight at the same time. A serial loop leaves the
    # first search waiting alone until the barrier's own timeout breaks it,
    # so the repo either raises out of scan() or lands in `failed` -- both
    # fail this test. The barrier sits under the real _scan_repo/_scan_rg
    # path, at the rg subprocess boundary, so scan() cannot spot a test
    # double and stay serial in production. Several repo counts keep a
    # count-specific branch from passing. Each fake rg run returns one hit
    # over the cap, so the concurrent path must also truncate and count.
    repos = _make_repos(tmp_path, [f"repo_{i}" for i in range(repo_count)])
    barrier = threading.Barrier(repo_count, timeout=5)

    class OverlappingPopen(subprocess.Popen):
        # The barrier holds every rg launch until all are in flight; the real
        # rg then runs (empty repo, no matches) and its output is swapped for
        # three fake hits.
        def __init__(self, cmd, *args, **kwargs):
            self._is_rg = cmd[0] == "rg"
            if self._is_rg:
                barrier.wait()
            super().__init__(cmd, *args, **kwargs)

        def communicate(self, *args, **kwargs):
            stdout, stderr = super().communicate(*args, **kwargs)
            if self._is_rg:
                return _rg_match_lines(3), ""
            return stdout, stderr

    monkeypatch.setattr(subprocess, "Popen", OverlappingPopen)

    hits, suppressed, failed = sweep.scan("PARALLELMARKER", "rg", repos, cap=2)

    assert failed == {}
    assert suppressed == {str(repo): 1 for repo in repos}
    assert [(hit["repo"], hit["line"]) for hit in hits] == [
        (str(repo), line) for repo in repos for line in (1, 2)
    ]


def test_scan_orders_hits_by_registry_position_not_completion_order(
    tmp_path, monkeypatch
):
    # Registry order is deliberately not alphabetical, so sorting by path
    # cannot pass. Completion order is forced to the exact reverse of it:
    # each repo waits until the repo listed after it has returned. Hits,
    # `failed` keys and `suppressed` keys must all still follow the order
    # `repos` listed them, and capped repos must be truncated to their
    # first `cap` hits with the overflow counted.
    repo_e, repo_b, repo_d, repo_a, repo_c = repos = _make_repos(
        tmp_path, ["repo_e", "repo_b", "repo_d", "repo_a", "repo_c"]
    )
    hit_counts = {repo_e: 3, repo_d: 4, repo_c: 1}  # cap=2: e and d overflow
    failing = {repo_b, repo_a}
    returned = {repo: threading.Event() for repo in repos}

    def reversed_completion_scan_repo(repo, *args, **kwargs):
        position = repos.index(repo)
        if position < len(repos) - 1:
            successor = repos[position + 1]
            if not returned[successor].wait(timeout=5):
                raise AssertionError(f"{repo} searched before {successor} could finish")
            time.sleep(0.05)
        returned[repo].set()
        if repo in failing:
            return str(repo), [], f"{repo.name} unreadable"
        repo_hits = [
            {**_stub_hit(repo), "line": line} for line in range(1, hit_counts[repo] + 1)
        ]
        return str(repo), repo_hits, None

    monkeypatch.setattr(sweep, "_scan_repo", reversed_completion_scan_repo)

    hits, suppressed, failed = sweep.scan("PARALLELMARKER", "rg", repos, cap=2)

    assert [(h["repo"], h["line"]) for h in hits] == [
        (str(repo_e), 1),
        (str(repo_e), 2),
        (str(repo_d), 1),
        (str(repo_d), 2),
        (str(repo_c), 1),
    ]
    assert failed == {str(repo_b): "repo_b unreadable", str(repo_a): "repo_a unreadable"}
    assert list(failed) == [str(repo_b), str(repo_a)]
    assert suppressed == {str(repo_e): 1, str(repo_d): 2}
    assert list(suppressed) == [str(repo_e), str(repo_d)]


def test_scan_waits_for_a_slow_repo_when_no_deadline_is_set(tmp_path, monkeypatch):
    # repo_b outlasts every time budget scan() is given here: the per-call
    # `timeout` is 0.2s and no sweep deadline is set. Without a deadline a
    # finished repo must be reported, so a worker pool that gives up on a
    # slow future (a join timeout, a daemon thread) and drops it from both
    # `hits` and `failed` fails this test.
    repo_a, repo_b, repo_c = repos = _make_repos(tmp_path, ["repo_a", "repo_b", "repo_c"])

    def slow_scan_repo(repo, *args, **kwargs):
        if repo == repo_b:
            time.sleep(1.0)
        return str(repo), [_stub_hit(repo)], None

    monkeypatch.setattr(sweep, "_scan_repo", slow_scan_repo)

    hits, _suppressed, failed = sweep.scan("PARALLELMARKER", "rg", repos, timeout=0.2)

    assert failed == {}
    assert [h["repo"] for h in hits] == [str(repo_a), str(repo_b), str(repo_c)]


class _SearchCrashed(Exception):
    pass


def test_scan_never_silently_drops_a_repo_whose_search_raises(tmp_path, monkeypatch):
    # The serial loop let an exception out of _scan_repo escape scan()
    # loudly. A worker pool must not swallow it: scan() either re-raises it
    # or records the repo in `failed`. Losing the repo from both is the bug.
    repo_a, repo_b, repo_c = repos = _make_repos(tmp_path, ["repo_a", "repo_b", "repo_c"])

    def crashing_scan_repo(repo, *args, **kwargs):
        if repo == repo_b:
            raise _SearchCrashed(f"{repo} search crashed")
        return str(repo), [_stub_hit(repo)], None

    monkeypatch.setattr(sweep, "_scan_repo", crashing_scan_repo)

    with pytest.raises(_SearchCrashed, match=re.escape(str(repo_b))):
        sweep.scan("PARALLELMARKER", "rg", repos)


# -- scan: a sweep deadline stops waiting on unfinished repos ----------------


def test_scan_records_an_unfinished_repo_when_the_deadline_expires(
    tmp_path, monkeypatch
):
    # repo_b's future never resolves: the patched submit() hands back a bare
    # Future() with no thread behind it, so nothing can hang at interpreter
    # exit. repo_a and repo_c go through the real submit() and are awaited
    # before submit() returns, so they are finished when scan() collects
    # them. The clock's first reading sets `start`; every later reading sits
    # far past `start + deadline`. scan() must give up on repo_b under
    # DEADLINE_REASON and still report the hits of the repos that finished.
    repo_a, repo_b, repo_c = repos = _make_repos(tmp_path, ["repo_a", "repo_b", "repo_c"])

    def stub_scan_repo(repo, *args, **kwargs):
        return str(repo), [_stub_hit(repo)], None

    monkeypatch.setattr(sweep, "_scan_repo", stub_scan_repo)

    real_submit = sweep.ThreadPoolExecutor.submit

    def submit_leaving_repo_b_pending(self, fn, *args, **kwargs):
        repo = args[0] if args else kwargs.get("repo")
        if repo == repo_b:
            return concurrent.futures.Future()
        future = real_submit(self, fn, *args, **kwargs)
        future.result()
        return future

    monkeypatch.setattr(sweep.ThreadPoolExecutor, "submit", submit_leaving_repo_b_pending)

    readings = []

    def expiring_monotonic():
        readings.append(None)
        return 0.0 if len(readings) == 1 else 1000.0

    monkeypatch.setattr(sweep.time, "monotonic", expiring_monotonic)

    hits, _suppressed, failed = sweep.scan("PARALLELMARKER", "rg", repos, deadline=5)

    assert sweep.DEADLINE_REASON == "sweep deadline expired"
    assert failed == {str(repo_b): sweep.DEADLINE_REASON}
    assert [h["repo"] for h in hits] == [str(repo_a), str(repo_c)]


def test_scan_keeps_repos_that_finish_within_the_deadline(tmp_path, monkeypatch):
    # Real clock. Every repo takes 0.3s, far inside the 5s deadline, so each
    # is still running when scan() first reaches it. Setting `deadline` must
    # not expire a repo by itself: scan() has to wait for an unfinished repo
    # while time remains, and keep its hits.
    repos = _make_repos(tmp_path, ["repo_a", "repo_b", "repo_c"])

    def quick_scan_repo(repo, *args, **kwargs):
        time.sleep(0.3)
        return str(repo), [_stub_hit(repo)], None

    monkeypatch.setattr(sweep, "_scan_repo", quick_scan_repo)

    hits, _suppressed, failed = sweep.scan("PARALLELMARKER", "rg", repos, deadline=5)

    assert failed == {}
    assert [h["repo"] for h in hits] == [str(repo) for repo in repos]


@pytest.mark.skipif(os.name == "nt", reason="the hanging search is a POSIX sh shim")
def test_scan_returns_promptly_past_the_deadline_while_a_repo_still_hangs(
    tmp_path, monkeypatch
):
    # Real clock, real hung search process. The fake rg on PATH sleeps 5s in
    # repo_b and prints one hit anywhere else. scan() must stop waiting at
    # the 0.3s deadline and must not wait out the still-running search on
    # the way out: the deadline kills it, so pool shutdown stays prompt.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    shim = bin_dir / "rg"
    shim.write_text(
        "\n".join(
            [
                "#!/bin/sh",
                'if [ "$(basename "$(pwd -P)")" = "repo_b" ]; then exec sleep 5; fi',
                f"printf '%s' '{_rg_match_lines(1)}'",
                "",
            ]
        )
    )
    shim.chmod(0o755)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    repo_a, repo_b, repo_c = repos = _make_repos(tmp_path, ["repo_a", "repo_b", "repo_c"])

    started = time.monotonic()
    hits, _suppressed, failed = sweep.scan(
        "PARALLELMARKER", "rg", repos, deadline=0.3
    )
    elapsed = time.monotonic() - started

    assert elapsed < 2  # far short of the hung search's own 5s sleep
    assert failed == {str(repo_b): sweep.DEADLINE_REASON}
    assert [h["repo"] for h in hits] == [str(repo_a), str(repo_c)]


def test_scan_deadline_budget_runs_from_scan_start_not_per_repo(
    tmp_path, monkeypatch
):
    # Real clock, deadline 2.0s for the whole sweep. repo_a finishes at 1.0s,
    # inside the budget, so its hit is kept. repo_b finishes at 3.0s: past
    # the sweep deadline, so it must expire. A budget that restarts when
    # scan() reaches repo_b (at 1.0s) would wait until 4.0s, see repo_b
    # finish, and keep it -- that fails here. The gaps are a full second
    # each so a loaded runner cannot flip the outcome.
    repo_a, repo_b, repo_c = repos = _make_repos(tmp_path, ["repo_a", "repo_b", "repo_c"])
    release = threading.Event()

    def staggered_scan_repo(repo, *args, **kwargs):
        if repo == repo_a:
            time.sleep(1.0)
        elif repo == repo_b:
            release.wait(timeout=3.0)
        return str(repo), [_stub_hit(repo)], None

    monkeypatch.setattr(sweep, "_scan_repo", staggered_scan_repo)

    try:
        hits, _suppressed, failed = sweep.scan(
            "PARALLELMARKER", "rg", repos, deadline=2.0
        )
    finally:
        release.set()

    assert failed == {str(repo_b): sweep.DEADLINE_REASON}
    assert [h["repo"] for h in hits] == [str(repo_a), str(repo_c)]


# -- scan: iterator repos and deadline attribution ---------------------------


def test_scan_accepts_a_one_shot_iterator_of_repos(tmp_path):
    repo_a = _plant_matches(tmp_path / "repo_a", "ITERMARKER", 2)
    repo_b = _plant_matches(tmp_path / "repo_b", "ITERMARKER", 2)

    list_hits, _s, _f = sweep.scan("ITERMARKER", "rg", [repo_a, repo_b])
    iter_hits, _s, _f = sweep.scan("ITERMARKER", "rg", iter([repo_a, repo_b]))

    # rg's order within one repo is not guaranteed, so compare the hit sets:
    # the claim under test is that no repo is lost, not how rg sorts matches.
    def key(hits):
        return sorted((h["repo"], h["file"], h["line"]) for h in hits)

    assert len(list_hits) == 4
    assert key(iter_hits) == key(list_hits)


def test_scan_does_not_report_a_workers_own_timeout_as_a_deadline_hit(
    tmp_path, monkeypatch
):
    repo_a, repo_b = repos = _make_repos(tmp_path, ["repo_a", "repo_b"])

    def timing_out_scan_repo(repo, *args, **kwargs):
        if repo == repo_b:
            raise TimeoutError("boom")
        return str(repo), [_stub_hit(repo)], None

    monkeypatch.setattr(sweep, "_scan_repo", timing_out_scan_repo)

    hits, _suppressed, failed = sweep.scan("PARALLELMARKER", "rg", repos, deadline=60)

    assert failed[str(repo_b)] != sweep.DEADLINE_REASON
    assert "boom" in failed[str(repo_b)]
    assert [h["repo"] for h in hits] == [str(repo_a)]


def test_scan_reports_an_error_entry_unfinished_at_the_deadline_by_cwd(
    tmp_path, monkeypatch
):
    # An error entry carries no "files" key; the deadline path still has to
    # name it rather than raising KeyError.
    error_entry = {"cwd": tmp_path / "bare", "error": "ls-files failed"}
    release = threading.Event()

    def blocking_scan_repo(repo, *args, **kwargs):
        release.wait(timeout=5)
        return str(repo), [], None

    monkeypatch.setattr(sweep, "_scan_repo", blocking_scan_repo)

    hits, _suppressed, failed = sweep.scan(
        "PARALLELMARKER", "rg", [error_entry], deadline=0
    )
    release.set()

    assert hits == []
    assert failed[str(tmp_path / "bare")] == sweep.DEADLINE_REASON


# -- scan: the deadline ends every search process tree it started ------------

_POSIX_SHIM = pytest.mark.skipif(
    os.name == "nt",
    reason="the search shim is a POSIX sh script that forks a grandchild; "
    "Windows has no compiler-free arg-agnostic equivalent (see the hung-search test)",
)


@_POSIX_SHIM
def test_scan_kills_a_hung_search_and_its_grandchild_at_the_deadline_and_keeps_finished_hits(
    tmp_path, monkeypatch, shim_pid_dir
):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_tree_shim(bin_dir, shim_pid_dir, "repo_fast", _rg_match_lines(2))
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    repo_slow, repo_fast = repos = _make_repos(tmp_path, ["repo_slow", "repo_fast"])

    started = time.monotonic()
    # The fast repo has 2 hits: cap=1 proves the per-repo cap still applies
    # on a run the deadline cut short.
    hits, suppressed, failed = sweep.scan("PARALLELMARKER", "rg", repos, cap=1, deadline=1)
    elapsed = time.monotonic() - started
    spawned = _recorded_pids(shim_pid_dir, "shim") + _recorded_pids(shim_pid_dir, "grandchild")

    assert elapsed < 3  # 1s deadline + 2s cleanup tolerance; the shim sleeps 10s
    assert failed == {str(repo_slow): sweep.DEADLINE_REASON}
    assert suppressed == {str(repo_fast): 1}
    assert [(h["repo"], h["line"]) for h in hits] == [(str(repo_fast), 1)]
    # The slow repo really went through the process-launch path.
    assert _recorded_pids(shim_pid_dir, "grandchild")
    # Grace covers signal delivery only; an unkilled sleeper lives 10s.
    assert _still_running_after(spawned, grace=1.0) == []
    assert list(shim_pid_dir.glob("finished-*")) == []


@_POSIX_SHIM
def test_scan_kills_a_hung_ast_grep_search_and_its_grandchild_at_the_deadline(
    tmp_path, monkeypatch, shim_pid_dir
):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    shim = _write_tree_shim(bin_dir, shim_pid_dir, tool="ast-grep")
    monkeypatch.setattr(sweep, "resolve_ast_grep", lambda: str(shim))
    (repo_slow,) = repos = _make_repos(tmp_path, ["repo_slow"])
    (repo_slow / "sample.py").write_text("print(1)\n")

    started = time.monotonic()
    hits, suppressed, failed = sweep.scan("print($X)", "astgrep", repos, deadline=1)
    elapsed = time.monotonic() - started
    spawned = _recorded_pids(shim_pid_dir, "shim") + _recorded_pids(shim_pid_dir, "grandchild")

    assert elapsed < 3  # 1s deadline + 2s cleanup tolerance; the shim sleeps 10s
    assert (hits, suppressed) == ([], {})
    assert failed == {str(repo_slow): sweep.DEADLINE_REASON}
    assert _recorded_pids(shim_pid_dir, "grandchild")  # the shim really ran
    assert _still_running_after(spawned, grace=1.0) == []
    assert list(shim_pid_dir.glob("finished-*")) == []


@_POSIX_SHIM
def test_scan_leaves_no_search_running_for_repos_still_queued_at_the_deadline(
    tmp_path, monkeypatch, shim_pid_dir
):
    # More repos than any worker pool runs at once, all hanging. Every
    # process launch is timed, so a queued repo whose search starts after
    # scan() returns is caught even if it dies before leaving a pid file.
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_tree_shim(bin_dir, shim_pid_dir)
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}{os.environ['PATH']}")
    repos = _make_repos(tmp_path, [f"repo_{i:02d}" for i in range(40)])
    launched_at = []

    class TimedPopen(subprocess.Popen):
        def __init__(self, *args, **kwargs):
            launched_at.append(time.monotonic())
            super().__init__(*args, **kwargs)

    monkeypatch.setattr(subprocess, "Popen", TimedPopen)

    started_at = time.monotonic()
    hits, _suppressed, failed = sweep.scan("PARALLELMARKER", "rg", repos, deadline=1)
    time.sleep(1.5)
    spawned = _recorded_pids(shim_pid_dir, "shim") + _recorded_pids(shim_pid_dir, "grandchild")

    assert hits == []
    assert failed == {str(repo): sweep.DEADLINE_REASON for repo in repos}
    assert list(failed) == [str(repo) for repo in repos]
    assert spawned  # searches really started
    assert launched_at  # and went through subprocess.Popen, so the timing is real
    # Checked against the 1s deadline itself (plus signal/scheduling slack),
    # not against when scan() happened to return: a queued repo picked up by
    # a freed worker thread must not launch a search after expiry, even if
    # scan()'s own cleanup (killing hung trees, shutting the pool down) takes
    # a while longer to return (R2).
    expiry = started_at + 1
    assert [t for t in launched_at if t > expiry + 0.5] == []
    assert _still_running_after(spawned, grace=0) == []
    assert list(shim_pid_dir.glob("finished-*")) == []


def test_scan_repo_never_launches_a_search_once_its_own_deadline_has_expired(
    tmp_path, monkeypatch
):
    # Deterministic complement to the timing test above: _scan_repo itself
    # must refuse to call _scan_rg/_scan_astgrep (and therefore Popen) once
    # `deadline` has already passed, independent of real elapsed time.
    repo = tmp_path / "repo"
    repo.mkdir()

    def _boom(*args, **kwargs):
        raise AssertionError("_scan_rg must not run past the deadline")

    monkeypatch.setattr(sweep, "_scan_rg", _boom)

    cwd_key, hits, error = sweep._scan_repo(
        repo, "PATTERN", "rg", None, sweep.DEFAULT_SCAN_TIMEOUT, deadline=1, start=time.monotonic() - 2
    )

    assert cwd_key == str(repo)
    assert hits == []
    assert error == sweep.DEADLINE_REASON


# -- _kill_tree: Windows cleanup is bounded by KILL_TREE_TIMEOUT -------------


def test_kill_tree_bounds_windows_taskkill_to_kill_tree_timeout_not_scan_timeout(
    monkeypatch,
):
    monkeypatch.setattr(sweep.os, "name", "nt")
    calls = []

    def _fake_run(*args, **kwargs):
        calls.append(kwargs)
        return subprocess.CompletedProcess(args, 0, "", "")

    monkeypatch.setattr(subprocess, "run", _fake_run)

    proc = object.__new__(subprocess.Popen)
    proc.pid = 4242
    monkeypatch.setattr(subprocess.Popen, "kill", lambda self: None, raising=False)

    sweep._kill_tree(proc)

    assert len(calls) == 1
    assert calls[0]["timeout"] == sweep.KILL_TREE_TIMEOUT
    assert calls[0]["timeout"] < sweep.DEFAULT_SCAN_TIMEOUT


