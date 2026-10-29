"""Resolve the rg and ast-grep binaries used by the sweep-fix skill."""
import argparse
import csv
import functools
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import date
from pathlib import Path

from sweep_rule_pack import _render_astgrep_rule_block

@functools.lru_cache()
def resolve_rg():
    """Resolve the path to invoke for `rg`.

    Returns the real `rg` binary if one is on PATH. Otherwise falls back to
    the claude binary (CLAUDE_CODE_EXECPATH, or ~/.local/bin/claude), which
    bundles ripgrep and dispatches based on argv[0].

    In this environment `rg` is a shell function, not a PATH binary, so a
    bare `subprocess.run(["rg", ...])` raises FileNotFoundError. Callers
    must instead pass the resolved path as `executable=` while keeping
    "rg" as argv[0]:

        subprocess.run(["rg", ...], executable=resolve_rg())

    The `executable=` argument is required exactly when the returned path
    is the claude-binary fallback, but the call above works unconditionally,
    so callers can always use it. Exits with status 1, naming both
    candidates checked, if neither resolves.
    """
    path = shutil.which("rg")
    if path:
        return path

    cc_bin = os.environ.get("CLAUDE_CODE_EXECPATH", "")
    if not (cc_bin and os.access(cc_bin, os.X_OK)):
        cc_bin = os.path.expanduser("~/.local/bin/claude")

    if os.access(cc_bin, os.X_OK):
        return cc_bin

    raise RuntimeError(
        "Could not resolve rg: not on PATH and no claude binary found "
        f"(checked CLAUDE_CODE_EXECPATH and {cc_bin})"
    )


@functools.lru_cache()
def resolve_ast_grep():
    """Resolve the path to invoke for `ast-grep`.

    Returns the real `ast-grep` binary if one is on PATH. Otherwise falls
    back to `mise which ast-grep` to locate a mise-managed install. Exits
    with status 1, naming both candidates checked, if neither resolves.
    """
    path = shutil.which("ast-grep")
    if path:
        return path

    if not shutil.which("mise"):
        raise RuntimeError(
            "Could not resolve ast-grep: not on PATH and mise is not available"
        )

    try:
        result = subprocess.run(
            ["mise", "which", "ast-grep"],
            capture_output=True,
            text=True,
            timeout=DEFAULT_SCAN_TIMEOUT,
        )
    except (subprocess.TimeoutExpired, OSError) as exc:
        raise RuntimeError(
            f"Could not resolve ast-grep: `mise which ast-grep` failed: {exc}"
        ) from exc
    if result.returncode != 0:
        raise RuntimeError(
            "Could not resolve ast-grep: not on PATH and `mise which ast-grep` failed"
        )

    return result.stdout.strip()


DEFAULT_SCAN_TIMEOUT = 30

KILL_TREE_TIMEOUT = 5
"""Bound a single `taskkill` call at deadline cleanup. Registry cleanup on
Windows runs `_kill_tree` serially across every still-registered process;
using DEFAULT_SCAN_TIMEOUT here let cleanup alone overrun the sweep deadline
by up to 30s per process."""

DEADLINE_REASON = "sweep deadline expired"

PORTFOLIO_ROOT = Path.home() / "git" / "src" / "github.com"

GITA_CSV = Path.home() / ".config" / "gita" / "repos.csv"

BUVIS_BARE = {
    "git_dir": Path.home() / ".buvis",
    "work_tree": Path.home(),
}


def _buvis_bare_entry():
    """Build the scan-scope entry for the buvis bare dotfiles work tree:
    `{"cwd": work_tree, "files": [...]}`, restricted to its tracked files
    (via `git ls-files` against `BUVIS_BARE["git_dir"]`). If that `git
    ls-files` call fails or times out, returns `{"cwd": work_tree, "error":
    reason}` instead, so `scan()` can surface the bare repo as failed rather
    than the exception aborting `enumerate_repos`."""
    work_tree = BUVIS_BARE["work_tree"]
    git_dir = BUVIS_BARE["git_dir"]
    try:
        result = subprocess.run(
            ["git", f"--git-dir={git_dir}", f"--work-tree={work_tree}", "ls-files", "-z"],
            cwd=work_tree,
            capture_output=True,
            text=True,
            check=True,
            timeout=DEFAULT_SCAN_TIMEOUT,
        )
    except Exception as exc:
        return {"cwd": work_tree, "error": str(exc)}
    files = [rel for rel in result.stdout.split("\0") if rel]
    return {"cwd": work_tree, "files": files}


def _git_root(path):
    """Nearest ancestor of `path` (itself included) holding `.git`, or
    `path` itself when none does."""
    for candidate in (path, *path.parents):
        if (candidate / ".git").exists():
            return candidate
    return path


def enumerate_repos(registry, cwd):
    """Enumerate the repos sweep should operate on.

    `registry` is a text file with one repo path per line (blank lines
    skipped); a missing registry raises `RuntimeError`. `cwd` is first made
    absolute and walked up to its git root (nearest ancestor holding
    `.git`). Returns `(repos, gaps)`:

    - `repos`: registered paths that have a `.git` dir, plus `cwd` if it is
      not already covered. If `cwd` or a registered row is the buvis bare
      dotfiles work tree (`BUVIS_BARE["work_tree"]`), it is represented by a
      single scan-scope entry (`{"cwd": work_tree, "files": [...]}`, built by
      `_buvis_bare_entry`) restricted to its tracked files, added exactly
      once even when both are true, so the bare repo counts as one repo
      rather than one entry per tracked file, since a directory walk would
      not find files living outside the home-relative repo layout (and would
      pull in untracked files sweep must not search).
    - `gaps`: `.git` repos found on disk at `PORTFOLIO_ROOT/<org>/<repo>`
      that are missing from the registry, as path strings.

    The registry file is only ever read, never written.
    """
    registry = Path(registry)
    cwd = _git_root(Path(os.path.abspath(cwd)))
    if not registry.is_file():
        raise RuntimeError(f"registry not found: {registry}")

    try:
        with registry.open() as fh:
            registered = [Path(row[0].strip()) for row in csv.reader(fh) if row and row[0].strip()]
    except (OSError, UnicodeDecodeError) as exc:
        raise RuntimeError(f"registry unreadable: {registry}: {exc}") from exc

    work_tree = BUVIS_BARE["work_tree"]
    repos = [path for path in registered if path != work_tree and (path / ".git").exists()]

    if work_tree in registered or cwd == work_tree:
        repos.append(_buvis_bare_entry())
    if cwd != work_tree and cwd not in repos:
        repos.append(cwd)

    gaps = []
    if PORTFOLIO_ROOT.is_dir():
        for repo_dir in sorted(PORTFOLIO_ROOT.glob("*/*")):
            if repo_dir.is_dir() and (repo_dir / ".git").exists() and repo_dir not in repos:
                gaps.append(str(repo_dir))

    return repos, gaps


AST_GREP_LANGUAGES = {
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".py": "python",
    ".rs": "rust",
    ".go": "go",
}


def _build_hit(repo, file, line, snippet):
    return {
        "repo": str(repo),
        "file": file,
        "line": line,
        "snippet": snippet,
        "lang": AST_GREP_LANGUAGES.get(Path(file).suffix),
    }


def _kill_tree(proc):
    """Terminate `proc` and its descendants (its process group on POSIX,
    `taskkill /T` on Windows), falling back to `proc.kill()`. Never raises."""
    try:
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                capture_output=True,
                timeout=KILL_TREE_TIMEOUT,
            )
        else:
            os.killpg(proc.pid, signal.SIGKILL)
    except (OSError, subprocess.SubprocessError):
        pass
    try:
        proc.kill()
    except OSError:
        pass


def _popen_new_group_kwargs():
    """Popen kwargs that launch a search into its own killable group."""
    if os.name == "nt":
        return {"creationflags": subprocess.CREATE_NEW_PROCESS_GROUP}
    return {"start_new_session": True}


class _ProcessRegistry:
    """In-flight search processes by repo key, so an expired repo's process
    tree can be killed from outside the worker thread that owns it. After
    `kill_all()` the registry is closed: a process registered later is
    killed on the spot, so no search outlives the deadline cleanup."""

    def __init__(self):
        self._lock = threading.Lock()
        self._procs = {}
        self._closed = False

    def register(self, key, proc):
        with self._lock:
            if not self._closed:
                self._procs.setdefault(key, []).append(proc)
                return
        _kill_tree(proc)

    def unregister(self, key, proc):
        with self._lock:
            procs = self._procs.get(key, [])
            if proc in procs:
                procs.remove(proc)
            if not procs:
                self._procs.pop(key, None)

    def kill(self, key):
        with self._lock:
            procs = self._procs.pop(key, [])
        for proc in procs:
            _kill_tree(proc)

    def kill_all(self):
        with self._lock:
            self._closed = True
            keys = list(self._procs)
        for key in keys:
            self.kill(key)


def _communicate_tracked(proc, timeout, registry, key):
    """`proc.communicate(timeout)` with `proc` registered under `key` while
    it runs. On timeout the whole tree is killed before re-raising."""
    if registry is not None:
        registry.register(key, proc)
    try:
        try:
            return proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            _kill_tree(proc)
            proc.communicate()
            raise
    finally:
        if registry is not None:
            registry.unregister(key, proc)


def _run_rg(args, cwd, timeout=DEFAULT_SCAN_TIMEOUT, registry=None, key=None):
    proc = subprocess.Popen(
        ["rg", *args],
        executable=resolve_rg(),
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        **_popen_new_group_kwargs(),
    )
    stdout, stderr = _communicate_tracked(proc, timeout, registry, key)
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"rg failed: {stderr}")
    return subprocess.CompletedProcess(proc.args, proc.returncode, stdout, stderr)


def _repo_cwd_and_targets(repo):
    """Split a `repos` entry into `(cwd, targets)` for a search subprocess.

    A plain `Path` repo is searched recursively (target "."). A bare-repo
    scan-scope entry (`{"cwd": ..., "files": [...]}`) is searched by naming
    its tracked files explicitly, so untracked files stay out of scope and
    the entry never needs a directory walk of its own.
    """
    if isinstance(repo, dict):
        # An error entry (`{"cwd": ..., "error": ...}`) carries no file list;
        # it is never searched, but the deadline path still asks for its cwd.
        return repo["cwd"], repo.get("files", [])
    return repo, ["."]


AUDIT_RESULTS_GLOB = "!docs/dev/project-management/audit-results/**"


def _scan_rg(pattern, cwd, targets, timeout=DEFAULT_SCAN_TIMEOUT, registry=None, key=None):
    if not targets:
        return []
    result = _run_rg(
        ["--json", "--glob", AUDIT_RESULTS_GLOB, "--", pattern, *targets],
        cwd,
        timeout=timeout,
        registry=registry,
        key=key,
    )
    hits = []
    for line in result.stdout.splitlines():
        event = json.loads(line)
        if event.get("type") != "match":
            continue
        data = event["data"]
        file = data["path"]["text"]
        hits.append(
            _build_hit(cwd, file, data["line_number"], data["lines"]["text"].rstrip("\n"))
        )
    return hits


def _scan_astgrep(pattern, cwd, targets, timeout=DEFAULT_SCAN_TIMEOUT, registry=None, key=None):
    if not targets:
        return []
    proc = subprocess.Popen(
        [resolve_ast_grep(), "run", "--pattern", pattern, "--json", "--", *targets],
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        **_popen_new_group_kwargs(),
    )
    stdout, stderr = _communicate_tracked(proc, timeout, registry, key)
    if proc.returncode not in (0, 1):
        raise RuntimeError(f"ast-grep failed: {stderr}")
    matches = json.loads(stdout) if stdout.strip() else []
    hits = []
    for match in matches:
        file = match["file"]
        hits.append(
            _build_hit(cwd, file, match["range"]["start"]["line"] + 1, match["lines"])
        )
    return hits


def _scan_repo(repo, pattern, kind, ast_grep_error, timeout, registry=None, deadline=None, start=None):
    """Scan a single `repo` entry. Returns `(cwd_key, hits, error)`, where
    `error` is set (and `hits` empty) when the repo could not be scanned.
    The search process is tracked in `registry` under `cwd_key`.

    When `deadline` (seconds from `start`) has already passed by the time a
    queued worker picks this repo up, the repo is recorded under
    DEADLINE_REASON without ever calling Popen -- a freed worker thread must
    not launch a fresh search after the sweep has already expired."""
    if isinstance(repo, dict) and "error" in repo:
        return str(repo["cwd"]), [], repo["error"]

    cwd, targets = _repo_cwd_and_targets(repo)

    if deadline is not None and time.monotonic() - start >= deadline:
        return str(cwd), [], DEADLINE_REASON

    if ast_grep_error is not None:
        return str(cwd), [], ast_grep_error

    try:
        if kind == "rg":
            repo_hits = _scan_rg(pattern, cwd, targets, timeout=timeout, registry=registry, key=str(cwd))
        else:
            repo_hits = _scan_astgrep(pattern, cwd, targets, timeout=timeout, registry=registry, key=str(cwd))
    except Exception as exc:
        return str(cwd), [], str(exc)

    return str(cwd), repo_hits, None


def _collect_scan_results(repos, futures, deadline, start, registry=None):
    """Await each future in `repos` order, bounded by `deadline` (seconds
    from `start`, or None for no bound). Returns `(results, deadline_hit)`
    where `results` holds each repo's `(cwd_key, hits, error)` tuple and an
    unfinished repo past the deadline is recorded under DEADLINE_REASON and
    has its search process tree killed through `registry`."""
    results = []
    deadline_hit = False
    for repo, future in zip(repos, futures):
        if deadline is None:
            results.append(future.result())
            continue
        remaining = deadline - (time.monotonic() - start)
        if not wait([future], timeout=max(remaining, 0)).done:
            cwd_key = str(_repo_cwd_and_targets(repo)[0])
            results.append((cwd_key, [], DEADLINE_REASON))
            deadline_hit = True
            if registry is not None:
                registry.kill(cwd_key)
            continue
        try:
            results.append(future.result())
        except Exception as exc:
            cwd_key = str(_repo_cwd_and_targets(repo)[0])
            results.append((cwd_key, [], str(exc)))
    return results, deadline_hit


def _apply_scan_cap(results, cap):
    """Split `results` (each a `(cwd_key, hits, error)` tuple) into the
    `(hits, suppressed, failed)` shape `scan()` returns, truncating each
    repo's hits at `cap` and recording the overflow count."""
    hits = []
    suppressed = {}
    failed = {}
    for cwd_key, repo_hits, error in results:
        if error is not None:
            failed[cwd_key] = error
            continue

        if len(repo_hits) > cap:
            suppressed[cwd_key] = len(repo_hits) - cap
            repo_hits = repo_hits[:cap]

        hits.extend(repo_hits)
    return hits, suppressed, failed


def _probe_ast_grep(kind):
    """Why ast-grep cannot run for an "astgrep" `kind`, or None."""
    if kind != "astgrep":
        return None
    try:
        resolve_ast_grep()
    except Exception as exc:
        return str(exc)
    return None


def scan(pattern, kind, repos, cap=20, timeout=DEFAULT_SCAN_TIMEOUT, deadline=None):
    """Search `pattern` across `repos` using `kind` ("rg" or "astgrep").

    Read-only: never writes to a repo. Returns `(hits, suppressed, failed)`.
    Each hit is a dict with `repo`, `file`, `line`, `snippet`, and `lang`
    (looked up in AST_GREP_LANGUAGES by file extension, None when unmapped).
    Hits are capped at `cap` per repo; `suppressed` maps `str(repo)` to the
    number of hits dropped beyond the cap, for repos that exceeded it only.

    Each subprocess search is bounded by `timeout` seconds. A repo whose
    search raises for any reason (crashes, times out, does not exist) does
    not abort the sweep: it is recorded in `failed` (`str(repo)` -> reason
    string) and the remaining repos are still scanned.

    Repos are searched concurrently (up to 8 at a time); `hits`, `suppressed`
    and `failed` still follow the order of `repos`, not completion order.

    `deadline` is an optional wall-clock budget in seconds for the whole
    sweep, measured with `time.monotonic()` from the start of this call.
    When set, a repo whose search has not finished by the time the deadline
    passes is recorded in `failed` under DEADLINE_REASON instead of being
    awaited further. Its search process tree is killed, queued repos are
    never started, and no search scan() launched outlives its return.
    """
    if kind not in ("rg", "astgrep"):
        raise ValueError(f"unknown kind: {kind!r}")

    ast_grep_error = _probe_ast_grep(kind)
    repos = list(repos)
    start = time.monotonic() if deadline is not None else None
    deadline_hit = False
    registry = _ProcessRegistry()
    # No `with` block: on a deadline every live search must be killed before
    # waiting for the workers, or a hung search would block scan() past it.
    executor = ThreadPoolExecutor(max_workers=8)
    try:
        futures = [
            executor.submit(
                _scan_repo, repo, pattern, kind, ast_grep_error, timeout, registry, deadline, start
            )
            for repo in repos
        ]
        results, deadline_hit = _collect_scan_results(repos, futures, deadline, start, registry)
    finally:
        if deadline_hit:
            registry.kill_all()
        executor.shutdown(wait=True, cancel_futures=deadline_hit)

    return _apply_scan_cap(results, cap)


def _search_control_term(control_repo, control_term, deadline, verify_start, expired):
    """Search `control_repo` for `control_term` within what `deadline` left
    since `verify_start`. Raises `TimeoutError(expired)` when that budget
    runs out, `RuntimeError` when the search fails for any other reason."""
    timeout = DEFAULT_SCAN_TIMEOUT
    if deadline is not None:
        remaining = deadline - (time.monotonic() - verify_start)
        if remaining <= 0:
            raise TimeoutError(expired)
        timeout = min(remaining, DEFAULT_SCAN_TIMEOUT)
    try:
        return _run_rg(["-F", "--", control_term, "."], control_repo, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        if timeout < DEFAULT_SCAN_TIMEOUT:
            raise TimeoutError(expired) from exc
        reason = " ".join(str(exc).split())
        raise RuntimeError(
            f'sweep unverified: could not search control term "{control_term}" in {control_repo}: {reason}'
        ) from exc
    except Exception as exc:
        reason = " ".join(str(exc).split())
        raise RuntimeError(
            f'sweep unverified: could not search control term "{control_term}" in {control_repo}: {reason}'
        ) from exc


def verify_control(pattern, kind, control_repo, control_term, deadline=None):
    """Verify `pattern` actually matches in `control_repo` before trusting a
    sweep run elsewhere.

    Searches `control_repo` for `pattern`. If it finds hits, the pattern is
    confirmed working and this returns None. If it finds none, searches
    `control_repo` for `control_term` (a string known to be present when the
    pattern's intended target is present). If `control_term` also finds no
    hits, the control repo is inconclusive and this returns None. If
    `control_term` finds hits but `pattern` did not, `pattern` is broken
    (e.g. the Rust-regex `\\|` literal-pipe trap): prints a message naming
    `control_term` and `control_repo`, then exits with status 1.

    Raises `RuntimeError` (one-line message) when the control repo cannot be
    scanned or the control-term search cannot run.

    `deadline` (seconds) is one budget shared by both searches, measured
    from entry: the control-term search gets only what the scan left. When
    the budget runs out first, raises `TimeoutError` instead.
    """
    verify_start = time.monotonic()
    expired = (
        f"sweep unverified: deadline expired before control verification "
        f"could confirm the result in {control_repo}"
    )
    hits, _suppressed, failed = scan(pattern, kind, [control_repo], deadline=deadline)
    if failed:
        raw_reason = next(iter(failed.values()))
        if raw_reason == DEADLINE_REASON:
            raise TimeoutError(expired)
        reason = " ".join(raw_reason.split())
        raise RuntimeError(
            f"sweep unverified: control repo {control_repo} could not be scanned: {reason}"
        )
    if hits:
        return None

    result = _search_control_term(control_repo, control_term, deadline, verify_start, expired)
    if result.returncode == 1:
        return None

    message = (
        f'sweep unverified: pattern found 0 hits but control term "{control_term}" is present in {control_repo} '
        "-- the pattern shape is likely broken (e.g. `\\|` alternation, which rg's Rust regex treats as a literal backslash-pipe)"
    )
    print(message, file=sys.stderr)
    raise SystemExit(1)


def _render_hits_section(hits, kind):
    lines = [f"Hits ({len(hits)}):"]
    for hit in hits:
        lines.append(f"- {hit['repo']} {hit['file']}:{hit['line']}: {hit['snippet']}")
    lines.append("")

    if kind == "astgrep":
        uncovered_exts = sorted({Path(hit["file"]).suffix or hit["file"] for hit in hits if hit["lang"] is None})
        if uncovered_exts:
            lines.append(f"Uncovered languages (no ast-grep lang mapping): {', '.join(uncovered_exts)}")
            lines.append("")

    return lines


def _render_suppressed_section(suppressed):
    lines = []
    if suppressed:
        lines.append("Suppressed:")
        for repo, count in suppressed.items():
            lines.append(f"- {repo}: {count} more hits suppressed (cap reached)")
        lines.append("")
    return lines


def _render_partial_section(failed):
    partial_count = sum(1 for reason in failed.values() if reason == DEADLINE_REASON)
    if not partial_count:
        return []
    return [f"Partial: {partial_count} repos not scanned (sweep deadline expired)", ""]


def _render_failed_section(failed):
    lines = []
    if failed:
        lines.append("Failed:")
        for repo, reason in failed.items():
            collapsed_reason = " ".join(reason.split())
            lines.append(f"- {repo}: could not be scanned ({collapsed_reason})")
        lines.append("")
    return lines


def _render_gaps_section(gaps):
    lines = [f"Gaps ({len(gaps)}):"]
    for gap in gaps:
        lines.append(f"- {gap}")
    lines.append("")
    return lines


def render_report(derivation, hits, gaps, suppressed, failed):
    """Render a plain-text sweep report from scan results.

    Pure string formatting: no subprocess calls, no file I/O. `derivation`
    carries `kind`, `pattern`, `reason`, `control_term` describing the sweep
    that was run. `failed` maps `str(repo)` to a reason string for repos
    that could not be scanned at all, distinct from `suppressed` (repos that
    were scanned but had hits truncated at the cap). When `kind` is
    "astgrep", appends an ast-grep rule-pack YAML block (one document per
    distinct language seen in `hits`, joined with `---`) that can be saved
    to a `.yml` file and run unedited with `ast-grep scan --rule`.
    """
    lines = [
        f"Kind: {derivation['kind']}",
        f"Pattern: {derivation['pattern']}",
        f"Reason: {derivation['reason']}",
        "",
    ]
    lines.extend(_render_hits_section(hits, derivation["kind"]))
    lines.extend(_render_suppressed_section(suppressed))
    lines.extend(_render_partial_section(failed))
    lines.extend(_render_failed_section(failed))
    lines.extend(_render_gaps_section(gaps))
    lines.extend(_render_astgrep_rule_block(derivation, hits))

    lines.append("How to proceed:")
    lines.append(
        "Review each hit above. Fixes land only in the repo this sweep was "
        "invoked from. Every other repo's hits stay report-only rows. Apply "
        "a fix only after the operator approves it. Rerun this sweep after "
        "making changes to confirm the fix landed."
    )

    return "\n".join(lines)


def _positive_int(flag_name):
    def _parse(value):
        try:
            parsed = int(value)
        except ValueError:
            parsed = 0
        if parsed <= 0:
            raise argparse.ArgumentTypeError(f"{flag_name} must be a positive integer")
        return parsed
    return _parse


def _parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", required=True, choices=["astgrep", "rg"])
    parser.add_argument("--pattern", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--control-term", required=True)
    parser.add_argument("--control-repo", required=True)
    parser.add_argument("--registry", default=str(GITA_CSV))
    parser.add_argument("--cwd", default=str(Path.cwd()))
    parser.add_argument("--cap", type=_positive_int("--cap"), default=20)
    parser.add_argument("--deadline", type=_positive_int("--deadline"), default=300)
    parser.add_argument("--out")
    return parser.parse_args(argv)


def _resolve_report_path(cwd_path, out, reason):
    """Resolve `--out` under `cwd_path`, defaulting to a slugged report
    name; refuses (exit 1) if it would land outside `cwd_path`. A default
    name that already exists gets the first free `-2`, `-3`, ... suffix so
    a same-day same-reason sweep never overwrites an earlier report; an
    explicit `--out` is never suffixed."""
    if not out:
        slug = re.sub(r"[^a-z0-9]+", "-", reason[:40].lower()).strip("-")
        stem = f"docs/dev/project-management/audit-results/sweep-{slug}-{date.today().isoformat()}"
        out = f"{stem}.md"
        n = 2
        while (cwd_path / out).exists():
            out = f"{stem}-{n}.md"
            n += 1

    out_path = (cwd_path / out).resolve()
    if not out_path.is_relative_to(cwd_path):
        print(
            f"sweep: --out {out!r} resolves to {out_path}, which is outside "
            f"the --cwd repo {cwd_path}",
            file=sys.stderr,
        )
        raise SystemExit(1)

    return out_path


def _verify_zero_hit_sweep(args, start):
    """Run the control check on what `--deadline` left since `start`.
    Raises `TimeoutError` when nothing is left for it to run."""
    remaining = args.deadline - (time.monotonic() - start)
    if remaining <= 0:
        raise TimeoutError(
            "sweep unverified: deadline expired before control "
            f"verification could run in {args.control_repo}"
        )
    verify_control(
        args.pattern, args.kind, Path(args.control_repo), args.control_term, deadline=remaining
    )


def main(argv=None):
    """CLI entry point: wire enumerate_repos, scan and render_report
    together, then write the rendered report to `--out`.

    `verify_control` runs after `scan`, and only when the scan found no hits
    at all: a sweep that found something has already proved the pattern
    works, so only an all-zero result can hide a broken pattern behind a
    false "clean" report.

    The report is written under `--cwd`; an `--out` resolving outside that
    repo is refused.

    Returns 0 on success. Returns 1 with one stderr line, writing no report,
    on a setup failure (scan tool, registry, control check) or when
    `--deadline` runs out before the control check can confirm a zero-hit
    sweep: the deadline bounds the sweep and the control check together.
    """
    args = _parse_args(argv)

    cwd_path = Path(args.cwd).resolve()
    out_path = _resolve_report_path(cwd_path, args.out, args.reason)

    try:
        start = time.monotonic()
        resolve_rg() if args.kind == "rg" else resolve_ast_grep()
        repos, gaps = enumerate_repos(args.registry, args.cwd)
        # Setup (resolve + enumerate) already spent part of --deadline; the
        # scan budget is what is left of it, not the full flag value, so
        # total wall time stays bounded by --deadline instead of setup+deadline.
        scan_deadline = max(args.deadline - (time.monotonic() - start), 0)
        hits, suppressed, failed = scan(args.pattern, args.kind, repos, cap=args.cap, deadline=scan_deadline)
        if not hits:
            _verify_zero_hit_sweep(args, start)
    except (RuntimeError, TimeoutError) as exc:
        print(exc, file=sys.stderr)
        return 1

    derivation = {
        "kind": args.kind,
        "pattern": args.pattern,
        "reason": args.reason,
        "control_term": args.control_term,
    }
    report = render_report(derivation, hits, gaps, suppressed, failed)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report)

    print(out_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
