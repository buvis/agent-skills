#!/usr/bin/env python3
"""Ground PRD claims against installed code (PRD 00075).

extract_claims pulls two claim kinds out of PRD markdown:

  1. citation: `path.ext:N`, `path.ext:N-M`, `path.ext:N-M,P-Q` (any extension;
     relative, absolute, or ~/ paths)
  2. symbol:   backtick identifiers and dotted / `::` paths

Frontmatter, fenced blocks, and lines holding the literal `link-ok:` yield no
claims. Line numbers count from the original text.

check_citations marks a citation "ok" when the file exists and every range fits
in it; when the same line names symbols, at least one must appear in the cited
lines. resolve_symbols marks a symbol "ok" when every segment of 3+ chars is a
whole word (per `rg -w`) somewhere in the repo outside docs/dev.

known_packages maps installed packages (Cargo.lock crates unpacked in the cargo
registry, node_modules dirs, .venv site-packages modules) to their source.
check_library_claims marks a library claim "ok" when every segment after the
package is a whole word in that package's source, "waived" when its line holds
LIBRARY_MARKER, else "unverified".
"""
import argparse
import functools
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

WAIVER = "link-ok:"
LIBRARY_MARKER = "(unverified library claim)"
LOCK_PACKAGE_RE = re.compile(r'^name = "([^"]+)"\nversion = "([^"]+)"', re.MULTILINE)
CITATION_RE = re.compile(
    r"(?<![\w./~-])(?:~/|/)?[\w.-]+(?:/[\w.-]+)*\.[A-Za-z]\w*:\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*"
)
BACKTICK_RE = re.compile(r"`([^`\n]+)`")
NEW_SYMBOLS_RE = re.compile(r"^\s*(?:[-*]\s*)?New symbols:\s*(.*)$")
SYMBOL_RE = re.compile(r"[A-Za-z_]\w*(?:(?:\.|::)[A-Za-z_]\w*)*")
SEGMENT_SPLIT = re.compile(r"\.|::")
# tokens that are patterns/placeholders, not real names
PLACEHOLDER = re.compile(r"[*?<>{}$]|\.\.\.|NNNNN|XXXX|YYYY")
FILE_EXTENSIONS = {
    "py", "md", "rs", "toml", "json", "jsonl", "yaml", "yml", "lock",
    "txt", "html", "sh", "js", "ts", "css",
}


class Claim(NamedTuple):
    kind: str
    token: str
    line: int


def is_symbol(token: str) -> bool:
    if len(token) < 3 or PLACEHOLDER.search(token) or not SYMBOL_RE.fullmatch(token):
        return False
    return SEGMENT_SPLIT.split(token)[-1] not in FILE_EXTENSIONS


def _scannable_lines(text: str):
    """Yield (line_number, line) pairs, skipping frontmatter, fenced blocks, and
    lines holding the WAIVER marker. Shared by extract_claims and the
    declared-new-symbol scan so both honor the same skip rules."""
    lines = text.splitlines()
    in_front = bool(lines) and lines[0] == "---"
    in_fence = False
    for ln, line in enumerate(lines, 1):
        if in_front:
            in_front = ln == 1 or line != "---"
            continue
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or WAIVER in line:
            continue
        yield ln, line


def extract_claims(text: str) -> list[Claim]:
    claims = []
    for ln, line in _scannable_lines(text):
        claims += [Claim("citation", m.group(0), ln) for m in CITATION_RE.finditer(line)]
        claims += [Claim("symbol", t, ln) for t in BACKTICK_RE.findall(line) if is_symbol(t)]
    return claims


def check_citations(
    claims: list[Claim], root: Path, reasons: dict[Claim, str] | None = None
) -> dict[Claim, str]:
    names_by_line: dict[int, list[str]] = {}
    for c in claims:
        if c.kind == "symbol":
            names_by_line.setdefault(c.line, []).append(SEGMENT_SPLIT.split(c.token)[-1])
    result = {}
    for c in claims:
        if c.kind != "citation":
            continue
        path, spans = c.token.rsplit(":", 1)
        p = Path(path).expanduser()
        if not p.is_absolute():
            p = root / p
        if not p.is_file():
            result[c] = "missing"
            if reasons is not None:
                reasons[c] = f"{path} not found"
            continue
        try:
            lines = p.read_text(errors="replace").splitlines()
        except OSError:
            result[c] = "missing"
            if reasons is not None:
                reasons[c] = f"{path} not found"
            continue
        ranges = [(int(a), int(b or a)) for a, _, b in (s.partition("-") for s in spans.split(","))]
        if not all(1 <= a <= b <= len(lines) for a, b in ranges):
            result[c] = "missing"
            if reasons is not None:
                reasons[c] = f"{path} line range exceeds file length ({len(lines)} lines)"
            continue
        names = names_by_line.get(c.line)
        if names:
            cited = [line for a, b in ranges for line in lines[a - 1:b]]
            hit = any(n in text_line for text_line in cited for n in names)
            result[c] = "ok" if hit else "missing"
            if not hit and reasons is not None:
                reasons[c] = f"no match for {', '.join(names)} in {path}:{spans}"
        else:
            result[c] = "ok"
    return result


@functools.lru_cache(maxsize=None)
def _rg_hit(segment: str, root: Path, exclude_globs: tuple[str, ...]) -> int:
    # cwd=root: rg matches --glob against paths relative to cwd, not the search root
    rg = [
        "rg", "-F", "-w", "-q", "--no-messages", "--glob", "!docs/dev/**",
        *exclude_globs, "--", segment, ".",
    ]
    code = subprocess.run(rg, cwd=root).returncode
    if code == 2:
        raise RuntimeError(f"rg failed searching {segment!r} in {root}")
    return code


def resolve_symbols(
    claims: list[Claim], root: Path, declared: set[str], exclude: frozenset[Path] = frozenset()
) -> dict[Claim, str]:
    # exclude: PRD files being graded, so a claim can't self-confirm by quoting its own token
    exclude_globs = []
    for p in exclude:
        try:
            # a relative path came from the CLI, so it is relative to cwd, not to root
            rel = Path(p).resolve().relative_to(Path(root).resolve())
        except ValueError:
            continue
        exclude_globs += ["--glob", f"!{rel}"]
    exclude_globs = tuple(exclude_globs)
    result = {}
    for c in claims:
        if c.token in declared:
            result[c] = "declared-new"
            continue
        result[c] = "ok"
        for s in SEGMENT_SPLIT.split(c.token):
            if len(s) < 3:
                continue
            code = _rg_hit(s, Path(root), exclude_globs)
            if code == 1:
                result[c] = "unresolved"
                break
    return result


@functools.lru_cache(maxsize=None)
def known_packages(root: Path, registry: Path) -> dict[str, dict]:
    packages: dict[str, dict] = {}
    lock = root / "Cargo.lock"
    if lock.is_file():
        # split on the block header: a path/workspace-local crate has no `source =`
        # line in its own block and must not be registered
        for block in lock.read_text(errors="replace").split("[[package]]")[1:]:
            m = LOCK_PACKAGE_RE.search(block)
            if not m or "source = " not in block:
                continue
            name, version = m.group(1), m.group(2)
            unpacked = [d for d in registry.glob(f"*/{name}-{version}") if d.is_dir()]
            packages[name] = {"version": version, "source": unpacked[0] if unpacked else None}
            # Rust code names a hyphenated crate with underscores (tree_sitter::Parser)
            packages[name.replace("-", "_")] = packages[name]
    node_modules = root / "node_modules"
    if node_modules.is_dir():
        packages.update({d.name: {"source": d} for d in node_modules.iterdir() if d.is_dir()})
    for site in root.glob(".venv/lib/python*/site-packages"):
        for p in site.iterdir():
            if p.is_dir() and p.name.isidentifier():
                packages[p.name] = {"source": p}
            elif p.suffix == ".py":
                packages[p.stem] = {"source": p}
    return packages


@functools.lru_cache(maxsize=None)
def _rg_hit_in_source(segment: str, source: Path) -> int:
    # --no-ignore: .venv and node_modules are usually gitignored
    rg = ["rg", "-F", "-w", "-q", "--no-messages", "--no-ignore", "--", segment, str(source)]
    code = subprocess.run(rg).returncode
    if code == 2:
        raise RuntimeError(f"rg failed searching {segment!r} in {source}")
    return code


def check_library_claims(
    claims: list[Claim], root: Path, registry: Path, line_text: dict[int, str] | None = None
) -> dict[Claim, str]:
    packages = known_packages(root, registry)
    result = {}
    for c in claims:
        if c.kind != "library":
            continue
        if line_text and LIBRARY_MARKER in line_text.get(c.line, ""):
            result[c] = "waived"
            continue
        package, *names = SEGMENT_SPLIT.split(c.token)
        source = packages.get(package, {}).get("source")
        if source is None:
            result[c] = "unverified"
            continue
        result[c] = "ok"
        for s in names:
            code = _rg_hit_in_source(s, Path(source))
            if code == 1:
                result[c] = "unverified"
                break
    return result


def _rows_for_file(
    p: Path,
    text: str,
    root: Path,
    registry: Path,
    packages: dict,
    declared: set[str],
    paths: list[Path],
) -> list[dict]:
    claims = extract_claims(text)
    line_text = dict(enumerate(text.splitlines(), 1))
    citation_reasons: dict[Claim, str] = {}
    citation_result = check_citations(claims, root, citation_reasons)
    reclassified = [
        c._replace(kind="library")
        if c.kind == "symbol" and SEGMENT_SPLIT.split(c.token)[0] in packages
        else c
        for c in claims
    ]
    symbols = [c for c in reclassified if c.kind == "symbol"]
    libraries = [c for c in reclassified if c.kind == "library"]
    symbol_result = resolve_symbols(symbols, root, declared, exclude=frozenset(paths))
    library_result = check_library_claims(libraries, root, registry, line_text)

    rows = []
    for orig, rc in zip(claims, reclassified):
        if rc.kind == "citation":
            status = citation_result[orig]
            detail = citation_reasons.get(orig, f"citation {rc.token}") if status == "missing" else f"citation {rc.token}"
        elif rc.kind == "symbol":
            status = symbol_result[rc]
            detail = f"symbol {rc.token}"
        else:
            status = library_result[rc]
            detail = f"library {rc.token}"
        rows.append(
            {
                "file": str(p),
                "kind": rc.kind,
                "token": rc.token,
                "line": rc.line,
                "status": status,
                "detail": detail,
                "prd:line": f"{p}:{rc.line}",
            }
        )
    return rows


def run(files: list[Path], root: Path, registry: Path) -> dict:
    paths = [Path(f) for f in files]
    texts = {p: p.read_text() for p in paths}

    declared: set[str] = set()
    for text in texts.values():
        for _, line in _scannable_lines(text):
            m = NEW_SYMBOLS_RE.match(line)
            if m:
                declared.update(
                    piece.strip().strip("`")
                    for piece in m.group(1).split(",")
                    if piece.strip()
                )

    packages = known_packages(root, registry)
    rows = []
    blocking = 0
    unverified = 0
    for p in paths:
        file_rows = _rows_for_file(p, texts[p], root, registry, packages, declared, paths)
        rows.extend(file_rows)
        for row in file_rows:
            if row["status"] in ("missing", "unresolved"):
                blocking += 1
            elif row["status"] == "unverified":
                unverified += 1

    return {"rows": rows, "blocking": blocking, "unverified": unverified}


SORT_ORDER = {
    "missing": 0, "unresolved": 1, "unverified": 2, "waived": 3, "ok": 4, "declared-new": 5,
}


def render_table(result: dict) -> None:
    rows = sorted(result["rows"], key=lambda r: (SORT_ORDER[r["status"]], r["file"], r["line"]))
    for row in rows:
        status, kind, token, file, line, detail = (
            row["status"], row["kind"], row["token"], row["file"], row["line"], row["detail"],
        )
        print(f"{status:10} {kind:9} {token:40} {file}:{line}  {detail}")
    declared_new = sum(1 for r in result["rows"] if r["status"] == "declared-new")
    print(f"{result['blocking']} blocking, {result['unverified']} unverified, {declared_new} declared new")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--root", default=".")
    parser.add_argument("--cargo-registry", dest="registry", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if shutil.which("rg") is None:
        print("ground_prd: rg not found on PATH", file=sys.stderr)
        sys.exit(2)

    registry = Path(args.registry) if args.registry else Path.home() / ".cargo" / "registry" / "src"

    files = []
    missing = []
    for raw in args.paths:
        p = Path(raw)
        if p.is_dir():
            files += sorted(p.glob("*.md"))
        elif p.is_file():
            files.append(p)
        else:
            missing.append(p)

    for f in files:
        try:
            f.read_text()
        except (OSError, UnicodeDecodeError):
            missing.append(f)

    if missing:
        for m in missing:
            print(f"ground_prd: {m}: not found or unreadable", file=sys.stderr)
        sys.exit(2)

    root = Path(args.root)
    if not root.is_dir():
        print(f"ground_prd: --root {root}: not a directory", file=sys.stderr)
        sys.exit(2)

    try:
        result = run(files, root, registry)
    except (RuntimeError, OSError) as e:
        print(f"ground_prd: {e}", file=sys.stderr)
        sys.exit(2)

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        render_table(result)

    sys.exit(1 if result["blocking"] else 0)


if __name__ == "__main__":
    main()
