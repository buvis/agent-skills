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
import functools
import re
import subprocess
from pathlib import Path
from typing import NamedTuple

WAIVER = "link-ok:"
LIBRARY_MARKER = "(unverified library claim)"
LOCK_PACKAGE_RE = re.compile(r'^name = "([^"]+)"\nversion = "([^"]+)"', re.MULTILINE)
CITATION_RE = re.compile(
    r"(?<![\w./~-])(?:~/|/)?[\w.-]+(?:/[\w.-]+)*\.[A-Za-z]\w*:\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*"
)
BACKTICK_RE = re.compile(r"`([^`\n]+)`")
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


def extract_claims(text: str) -> list[Claim]:
    claims = []
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
        claims += [Claim("citation", m.group(0), ln) for m in CITATION_RE.finditer(line)]
        claims += [Claim("symbol", t, ln) for t in BACKTICK_RE.findall(line) if is_symbol(t)]
    return claims


def check_citations(claims: list[Claim], root: Path) -> dict[Claim, str]:
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
            continue
        try:
            lines = p.read_text(errors="replace").splitlines()
        except OSError:
            result[c] = "missing"
            continue
        ranges = [(int(a), int(b or a)) for a, _, b in (s.partition("-") for s in spans.split(","))]
        if not all(1 <= a <= b <= len(lines) for a, b in ranges):
            result[c] = "missing"
            continue
        names = names_by_line.get(c.line)
        if names:
            cited = [line for a, b in ranges for line in lines[a - 1:b]]
            hit = any(n in text_line for text_line in cited for n in names)
            result[c] = "ok" if hit else "missing"
        else:
            result[c] = "ok"
    return result


def resolve_symbols(claims: list[Claim], root: Path, declared: set[str]) -> dict[Claim, str]:
    result = {}
    for c in claims:
        if c.token in declared:
            result[c] = "declared-new"
            continue
        result[c] = "ok"
        for s in SEGMENT_SPLIT.split(c.token):
            if len(s) < 3:
                continue
            # cwd=root: rg matches --glob against paths relative to cwd, not the search root
            rg = ["rg", "-F", "-w", "-q", "--no-messages", "--glob", "!docs/dev/**", "--", s, "."]
            code = subprocess.run(rg, cwd=root).returncode
            if code == 2:
                raise RuntimeError(f"rg failed searching {s!r} in {root}")
            if code == 1:
                result[c] = "unresolved"
                break
    return result


@functools.lru_cache(maxsize=None)
def known_packages(root: Path, registry: Path) -> dict[str, dict]:
    packages: dict[str, dict] = {}
    lock = root / "Cargo.lock"
    if lock.is_file():
        for name, version in LOCK_PACKAGE_RE.findall(lock.read_text(errors="replace")):
            unpacked = [d for d in registry.glob(f"*/{name}-{version}") if d.is_dir()]
            packages[name] = {"version": version, "source": unpacked[0] if unpacked else None}
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
            # --no-ignore: .venv and node_modules are usually gitignored
            rg = ["rg", "-F", "-w", "-q", "--no-messages", "--no-ignore", "--", s, str(source)]
            code = subprocess.run(rg).returncode
            if code == 2:
                raise RuntimeError(f"rg failed searching {s!r} in {source}")
            if code == 1:
                result[c] = "unverified"
                break
    return result
