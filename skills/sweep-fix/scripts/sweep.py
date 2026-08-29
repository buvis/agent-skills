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

    result = subprocess.run(
        ["mise", "which", "ast-grep"],
        capture_output=True,
        text=True,
        timeout=DEFAULT_SCAN_TIMEOUT,
    )
    if result.returncode != 0:
        raise RuntimeError(
            "Could not resolve ast-grep: not on PATH and `mise which ast-grep` failed"
        )

    return result.stdout.strip()


DEFAULT_SCAN_TIMEOUT = 30

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


def enumerate_repos(registry, cwd):
    """Enumerate the repos sweep should operate on.

    `registry` is a text file with one repo path per line (blank lines
    skipped). Returns `(repos, gaps)`:

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
    cwd = Path(cwd)

    registered = [Path(row[0].strip()) for row in csv.reader(registry.open()) if row and row[0].strip()]

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
        return repo["cwd"], repo["files"]
    return repo, ["."]


def _scan_rg(pattern, cwd, targets, timeout=DEFAULT_SCAN_TIMEOUT):
    if not targets:
        return []
    result = _run_rg(["--json", "--", pattern, *targets], cwd, timeout=timeout)
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


def scan(pattern, kind, repos, cap=20, timeout=DEFAULT_SCAN_TIMEOUT):
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
    """
    if kind not in ("rg", "astgrep"):
        raise ValueError(f"unknown kind: {kind!r}")

    ast_grep_error = None
    if kind == "astgrep":
        try:
            resolve_ast_grep()
        except Exception as exc:
            ast_grep_error = str(exc)

    hits = []
    suppressed = {}
    failed = {}
    for repo in repos:
        cwd_key, repo_hits, error = _scan_repo(repo, pattern, kind, ast_grep_error, timeout)
        if error is not None:
            failed[cwd_key] = error
            continue

        if len(repo_hits) > cap:
            suppressed[cwd_key] = len(repo_hits) - cap
            repo_hits = repo_hits[:cap]

        hits.extend(repo_hits)

    return hits, suppressed, failed


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
    """
    hits, _suppressed, _failed = scan(pattern, kind, [control_repo])
    if hits:
        return None

    try:
        result = _run_rg(["-F", "--", control_term, "."], control_repo)
    except Exception as exc:
        print(
            f"sweep: could not verify control term \"{control_term}\" in "
            f"{control_repo}: {exc}",
            file=sys.stderr,
        )
        return None
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


_YAML_INDICATOR_CHARS = "-?:,[]{}#&*!|>'\"%@`"
_YAML_RESERVED_WORDS = {"null", "~", "true", "false", "yes", "no", "on", "off"}


_YAML_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_YAML_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")
_YAML_INF_NAN_RE = re.compile(r"^[-+]?\.(inf|nan)$", re.IGNORECASE)


def _needs_yaml_quoting(value):
    """True if `value` cannot be emitted as a bare YAML plain scalar: it
    would either fail to parse (a colon-space, a trailing colon, a leading
    indicator character, an embedded newline or other control character) or
    silently parse back as a different type (an empty string; a whole value
    that is itself a YAML null/bool token; leading/trailing whitespace; or a
    value that resolves implicitly to a number or a date)."""
    if value == "" or _YAML_CONTROL_CHARS_RE.search(value):
        return True
    if value[0] in _YAML_INDICATOR_CHARS:
        return True
    if ": " in value or value.endswith(":"):
        return True
    if " #" in value:
        return True
    if value.lower() in _YAML_RESERVED_WORDS:
        return True
    if value != value.strip():
        return True
    if _YAML_DATE_RE.match(value):
        return True
    try:
        int(value, 0)
        return True
    except ValueError:
        pass
    try:
        float(value)
        return True
    except ValueError:
        pass
    if _YAML_INF_NAN_RE.match(value):
        return True
    return False


_YAML_SCALAR_ESCAPES = {chr(code): f"\\x{code:02x}" for code in range(0x20)}
_YAML_SCALAR_ESCAPES[chr(0x7F)] = "\\x7f"
_YAML_SCALAR_ESCAPES.update(
    {"\\": "\\\\", '"': '\\"', "\n": "\\n", "\r": "\\r", "\t": "\\t"}
)


def _yaml_scalar(value):
    """Render `value` as a YAML scalar: bare when it is safe as a plain
    scalar, double-quoted with escapes otherwise."""
    if not _needs_yaml_quoting(value):
        return value
    escaped = "".join(_YAML_SCALAR_ESCAPES.get(ch, ch) for ch in value)
    return f'"{escaped}"'


def _render_astgrep_rule_block(derivation, hits):
    lines = []
    if derivation["kind"] != "astgrep":
        return lines

    seen_langs = list(dict.fromkeys(hit["lang"] for hit in hits if hit["lang"]))
    if not seen_langs:
        return lines

    message = _yaml_scalar(derivation["reason"])
    pattern = _yaml_scalar(derivation["pattern"])
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


def _positive_int(value):
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("--cap must be a positive integer")
    return parsed


def _parse_args(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", required=True, choices=["astgrep", "rg"])
    parser.add_argument("--pattern", required=True)
    parser.add_argument("--reason", required=True)
    parser.add_argument("--control-term", required=True)
    parser.add_argument("--control-repo", required=True)
    parser.add_argument("--registry", default=str(GITA_CSV))
    parser.add_argument("--cwd", default=str(Path.cwd()))
    parser.add_argument("--cap", type=_positive_int, default=20)
    parser.add_argument("--out")
    return parser.parse_args(argv)


def _resolve_report_path(cwd_path, out, reason):
    """Resolve `--out` under `cwd_path`, defaulting to a slugged report
    name; refuses (exit 1) if it would land outside `cwd_path`."""
    if not out:
        slug = re.sub(r"[^a-z0-9]+", "-", reason[:40].lower()).strip("-")
        out = f"dev/local/audit-results/sweep-{slug}-{date.today().isoformat()}.md"

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

    Returns 0 on success.
    """
    args = _parse_args(argv)

    try:
        repos, gaps = enumerate_repos(args.registry, args.cwd)
        hits, suppressed, failed = scan(args.pattern, args.kind, repos, cap=args.cap)
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

    cwd_path = Path(args.cwd).resolve()
    out_path = _resolve_report_path(cwd_path, args.out, args.reason)

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report)

    print(out_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
