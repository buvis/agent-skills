"""Resolve the rg and ast-grep binaries used by the sweep-fix skill."""
import argparse
import csv
import functools
import json
import os
import re
import shutil
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, wait
from datetime import date
from pathlib import Path


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


def _run_rg(args, cwd, timeout=DEFAULT_SCAN_TIMEOUT):
    result = subprocess.run(
        ["rg", *args],
        executable=resolve_rg(),
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(f"rg failed: {result.stderr}")
    return result


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


def _scan_rg(pattern, cwd, targets, timeout=DEFAULT_SCAN_TIMEOUT):
    if not targets:
        return []
    result = _run_rg(
        ["--json", "--glob", AUDIT_RESULTS_GLOB, "--", pattern, *targets],
        cwd,
        timeout=timeout,
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


def _scan_astgrep(pattern, cwd, targets, timeout=DEFAULT_SCAN_TIMEOUT):
    if not targets:
        return []
    result = subprocess.run(
        [resolve_ast_grep(), "run", "--pattern", pattern, "--json", "--", *targets],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode not in (0, 1):
        raise RuntimeError(f"ast-grep failed: {result.stderr}")
    matches = json.loads(result.stdout) if result.stdout.strip() else []
    hits = []
    for match in matches:
        file = match["file"]
        hits.append(
            _build_hit(cwd, file, match["range"]["start"]["line"] + 1, match["lines"])
        )
    return hits


def _scan_repo(repo, pattern, kind, ast_grep_error, timeout):
    """Scan a single `repo` entry. Returns `(cwd_key, hits, error)`, where
    `error` is set (and `hits` empty) when the repo could not be scanned."""
    if isinstance(repo, dict) and "error" in repo:
        return str(repo["cwd"]), [], repo["error"]

    cwd, targets = _repo_cwd_and_targets(repo)

    if ast_grep_error is not None:
        return str(cwd), [], ast_grep_error

    try:
        if kind == "rg":
            repo_hits = _scan_rg(pattern, cwd, targets, timeout=timeout)
        else:
            repo_hits = _scan_astgrep(pattern, cwd, targets, timeout=timeout)
    except Exception as exc:
        return str(cwd), [], str(exc)

    return str(cwd), repo_hits, None


def _collect_scan_results(repos, futures, deadline, start):
    """Await each future in `repos` order, bounded by `deadline` (seconds
    from `start`, or None for no bound). Returns `(results, deadline_hit)`
    where `results` holds each repo's `(cwd_key, hits, error)` tuple and an
    unfinished repo past the deadline is recorded under DEADLINE_REASON."""
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
    awaited further, and scan() returns without waiting for its worker.
    """
    if kind not in ("rg", "astgrep"):
        raise ValueError(f"unknown kind: {kind!r}")

    ast_grep_error = None
    if kind == "astgrep":
        try:
            resolve_ast_grep()
        except Exception as exc:
            ast_grep_error = str(exc)

    repos = list(repos)
    start = time.monotonic() if deadline is not None else None
    deadline_hit = False
    # No `with` block: leaving one always waits for every worker, so a hung
    # search would block scan() past its deadline.
    executor = ThreadPoolExecutor(max_workers=8)
    try:
        futures = [
            executor.submit(_scan_repo, repo, pattern, kind, ast_grep_error, timeout)
            for repo in repos
        ]
        results, deadline_hit = _collect_scan_results(repos, futures, deadline, start)
    finally:
        executor.shutdown(wait=not deadline_hit, cancel_futures=deadline_hit)

    return _apply_scan_cap(results, cap)


def verify_control(pattern, kind, control_repo, control_term):
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
    """
    hits, _suppressed, failed = scan(pattern, kind, [control_repo])
    if failed:
        reason = " ".join(next(iter(failed.values())).split())
        raise RuntimeError(
            f"sweep unverified: control repo {control_repo} could not be scanned: {reason}"
        )
    if hits:
        return None

    try:
        result = _run_rg(["-F", "--", control_term, "."], control_repo)
    except Exception as exc:
        reason = " ".join(str(exc).split())
        raise RuntimeError(
            f'sweep unverified: could not search control term "{control_term}" in {control_repo}: {reason}'
        ) from exc
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


def _yaml_quote(value):
    """Render `value` as a YAML double-quoted scalar. A JSON string is a
    valid YAML double-quoted scalar; characters JSON leaves raw that YAML
    forbids or folds (DEL, C1 incl. U+0085, U+2028/2029, BOM, other
    non-printables) are escaped as \\uXXXX / \\UXXXXXXXX."""
    return "".join(
        ch if ch.isprintable()
        else f"\\u{ord(ch):04x}" if ord(ch) <= 0xFFFF
        else f"\\U{ord(ch):08x}"
        for ch in json.dumps(value, ensure_ascii=False)
    )


def _render_astgrep_rule_block(derivation, hits):
    lines = []
    if derivation["kind"] != "astgrep":
        return lines

    seen_langs = list(dict.fromkeys(hit["lang"] for hit in hits if hit["lang"]))
    if not seen_langs:
        return lines

    message = _yaml_quote(derivation["reason"])
    pattern = _yaml_quote(derivation["pattern"])
    rule_docs = [
        "\n".join(
            [
                f"id: sweep-{lang}",
                f"language: {lang}",
                "severity: warning",
                f"message: {message}",
                "rule:",
                f"  pattern: {pattern}",
            ]
        )
        for lang in seen_langs
    ]
    lines.append("```yaml")
    lines.append("\n---\n".join(rule_docs))
    lines.append("```")
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
    on a setup failure (scan tool, registry, control check).
    """
    args = _parse_args(argv)

    cwd_path = Path(args.cwd).resolve()
    out_path = _resolve_report_path(cwd_path, args.out, args.reason)

    try:
        resolve_rg() if args.kind == "rg" else resolve_ast_grep()
        repos, gaps = enumerate_repos(args.registry, args.cwd)
        hits, suppressed, failed = scan(args.pattern, args.kind, repos, cap=args.cap, deadline=args.deadline)
        if not hits:
            verify_control(args.pattern, args.kind, Path(args.control_repo), args.control_term)
    except RuntimeError as exc:
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
