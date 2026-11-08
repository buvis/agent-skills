#!/usr/bin/env python3
"""Create a note in the BIM vault zettelkasten from a template ported from the vault.

Prints a JSON report on success. Prints an error to stderr and exits non-zero
on failure. Never overwrites a file. Standard library only, Python 3.9+.
"""
from __future__ import annotations

import argparse
import fcntl
import json
import os
import re
import string
import sys
import time
import unicodedata
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, quote, urlparse

from vault_links import append_daily_log, contact_names, daily_log_entry, link_contacts

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "assets" / "templates"
BODY_SENTINEL = "\x00BODY\x00"
MAX_ID_ATTEMPTS = 5

# Same on every machine relative to home; expanded at run time.
PROJECTS_ROOT = "~/Documents/reference/10-projects"
ARTICLES_ROOT = "~/Documents/reference/40-archives/articles"

# kind -> template file, `type` value, folder under the vault, default tags,
# and whether the file is named by slug instead of id.
KINDS = {
    "note": {"template": "generic-note.md", "type": "note", "folder": "notes", "tags": [], "slug_name": False},
    "illustrated": {"template": "illustrated-note.md", "type": "illustrated-note", "folder": "notes", "tags": [], "slug_name": False},
    "meeting": {"template": "meeting-minutes.md", "type": "meeting-minutes", "folder": "notes", "tags": [], "slug_name": False},
    "youtube": {"template": "notes-on-youtube-video.md", "type": "note", "folder": "notes", "tags": [], "slug_name": False},
    "prr": {"template": "problem-resolution-report.md", "type": "problem-resolution-report", "folder": "notes", "tags": [], "slug_name": False},
    "project": {"template": "project.md", "type": "project", "folder": "notes", "tags": [], "slug_name": False},
    "book": {"template": "book.md", "type": "book", "folder": "notes/book", "tags": ["book"], "slug_name": True},
    "contact": {"template": "contact-person.md", "type": "contact", "folder": "notes/contact", "tags": ["person"], "slug_name": True},
}
DEDICATED_TYPES = {"illustrated-note", "meeting-minutes", "problem-resolution-report", "project", "book", "contact", "budget"}
MOVER_TAGS = {"person": "contact", "book": "book"}  # Auto Note Mover relocates notes with these tags.
LOCATIONS = ["webex", "teams", "phone", "face to face"]
DELIVERABLES = ["fix", "enhancement", "support"]
RESERVED_FIELDS = {"id", "title", "date", "tags", "type"}
YAML_WORDS = {"~", "null", "true", "false", "yes", "no", "on", "off", "y", "n"}
YOUTUBE_ID = re.compile(r"[A-Za-z0-9_-]{11}")
ID_LINE = re.compile(rb"^id: *[\"']?(\d{14})[\"']?[ \t\r]*$", re.M)


class CreateNoteError(Exception):
    pass


def current_time() -> datetime:
    return datetime.now().astimezone()


def capitalize_first(text: str) -> str:
    return text[:1].upper() + text[1:]


def capitalize_words(text: str) -> str:
    return " ".join(capitalize_first(word) for word in text.split(" "))


def slugify(text: str) -> str:
    """Port of the slug expression in page.convert-to-book.tpl and page.convert-to-contact-person.tpl."""
    slug = unicodedata.normalize("NFKD", text)
    slug = re.sub(r"[\u0300-\u036f]", "", slug).strip().lower()
    slug = re.sub(r"[^a-z0-9 -]", "", slug)
    slug = re.sub(r"\s+", "-", slug)
    return re.sub(r"-+", "-", slug)


def yaml_scalar(value: str) -> str:
    plain_ok = (
        value
        and value == value.strip()
        and value.lower() not in YAML_WORDS
        and value[0] not in "-?:,[]{}#&*!|>'\"%@`"
        and not any(token in value for token in (":", " #", "\n", "\t"))
        and not re.fullmatch(r"[-+]?(\d[\d_]*\.?\d*|\.\d+)([eE][-+]?\d+)?|0[xob][0-9a-fA-F]+|\d{4}-\d{1,2}-\d{1,2}", value)
    )
    return value if plain_ok else json.dumps(value, ensure_ascii=False)


def render_value(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return yaml_scalar(value)
    raise CreateNoteError(f"unsupported field value {value!r}: use a string, number, boolean, null, or list of those")


def render_field(key: str, value: object) -> list[str]:
    if value is None:
        return [f"{key}:"]
    if isinstance(value, list):
        if not value:
            return [f"{key}: []"]
        return [f"{key}:"] + [f"  - {render_value(item)}" for item in value]
    return [f"{key}: {render_value(value)}"]


def parse_fields(raw: str | None) -> dict:
    if not raw:
        return {}
    try:
        fields = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise CreateNoteError(f"--fields is not valid JSON: {exc}") from exc
    if not isinstance(fields, dict):
        raise CreateNoteError("--fields must be a JSON object")
    for key in fields:
        if key in RESERVED_FIELDS:
            raise CreateNoteError(f"--fields cannot set '{key}'; use the dedicated option")
        if not re.fullmatch(r"[a-z][a-z0-9-]*", key):
            raise CreateNoteError(f"--fields key '{key}' must be lowercase kebab-case")
    return fields


def apply_fields(frontmatter: str, fields: dict) -> str:
    """Replace template keys in place and append new keys at the end."""
    lines = frontmatter.split("\n")
    pending = dict(fields)
    out: list[str] = []
    i = 0
    while i < len(lines):
        end = i + 1
        while end < len(lines) and lines[end].startswith((" ", "\t")):
            end += 1
        match = re.match(r"([a-z][a-z0-9-]*):", lines[i])
        if match and match.group(1) in pending:
            out.extend(render_field(match.group(1), pending.pop(match.group(1))))
        else:
            out.extend(lines[i:end])
        i = end
    for key, value in pending.items():
        out.extend(render_field(key, value))
    return "\n".join(out)


def parse_tags(raw: str | None, kind: str) -> list[str]:
    tags = list(KINDS[kind]["tags"])
    for item in (raw or "").split(","):
        tag = item.strip().lstrip("#").lower()
        if not tag:
            continue
        if not re.fullmatch(r"[\w-]+(/[\w-]+)*", tag) or re.fullmatch(r"[\d/]+", tag):
            raise CreateNoteError(f"invalid tag '{item.strip()}': use letters, digits, '-', '_', and '/' for nesting")
        if MOVER_TAGS.get(tag, kind) != kind:
            raise CreateNoteError(f"tag '{tag}' is reserved for the {MOVER_TAGS[tag]} kind (Auto Note Mover relocates it)")
        if tag not in tags:
            tags.append(tag)
    return tags


def youtube_id(value: str) -> str:
    value = value.strip()
    if YOUTUBE_ID.fullmatch(value):
        return value
    url = urlparse(value if "://" in value else "https://" + value)
    host = (url.hostname or "").lower()
    candidate = ""
    if host == "youtu.be":
        candidate = url.path.strip("/").split("/")[0]
    elif host == "youtube.com" or host.endswith(".youtube.com") or host.endswith("youtube-nocookie.com"):
        parts = [p for p in url.path.split("/") if p]
        if parts == ["watch"]:
            candidate = parse_qs(url.query).get("v", [""])[0]
        elif len(parts) >= 2 and parts[0] in ("live", "shorts", "embed", "v"):
            candidate = parts[1]
    if not YOUTUBE_ID.fullmatch(candidate):
        raise CreateNoteError(f"cannot find a YouTube video id in '{value}'")
    return candidate


def file_url(path: str) -> str:
    """Port of toFileUrl() in page.create-project.tpl (encodeURIComponent per segment)."""
    return "file:///" + "%2F".join(quote(seg, safe="!*'()") for seg in path.split("/"))


def resolve_vault(raw: str | None) -> Path:
    vault = Path(raw or os.environ.get("BIM_VAULT") or "~/bim").expanduser().resolve()
    missing = [name for name in ("notes", "notes/system") if not (vault / name).is_dir()]
    if missing:
        raise CreateNoteError(f"{vault} is not a BIM vault (missing {', '.join(missing)}/); set --vault or BIM_VAULT")
    return vault


def used_ids(zettelkasten: Path) -> set[str]:
    ids = set()
    for path in zettelkasten.rglob("*.md"):
        if re.fullmatch(r"\d{14}", path.stem):
            ids.add(path.stem)
        try:
            with path.open("rb") as handle:
                head = handle.read(512)
        except FileNotFoundError:  # broken symlink or file removed during the scan
            continue
        ids.update(match.decode() for match in ID_LINE.findall(head))
    return ids


def allocate_id(zettelkasten: Path, reserved: frozenset[str] = frozenset()) -> tuple[str, datetime]:
    taken = used_ids(zettelkasten) | reserved
    for _ in range(MAX_ID_ATTEMPTS):
        now = current_time().replace(microsecond=0)
        note_id = now.strftime("%Y%m%d%H%M%S")
        if note_id not in taken:
            return note_id, now
        time.sleep(1.0)
    raise CreateNoteError(f"no free id after {MAX_ID_ATTEMPTS} attempts")


def read_body(args: argparse.Namespace, vault: Path) -> tuple[str, Path | None, bool]:
    if args.source:
        source = vault / Path(args.source).expanduser()  # relative paths are relative to the vault
        source = source.resolve()
        inbox = (vault / "inbox").resolve()
        if inbox not in source.parents:
            raise CreateNoteError(f"--source must be a file inside {inbox}")
        if not source.is_file() or source.suffix != ".md":
            raise CreateNoteError(f"--source {source} is not a Markdown file")
        text = source.read_text(encoding="utf-8").replace("\r\n", "\n")
        stripped = re.sub(r"\A---\n[\s\S]*?\n---\n", "", text, count=1)
        return stripped, source, stripped != text
    if args.body_file == "-":
        return sys.stdin.read(), None, False
    if args.body_file:
        return Path(args.body_file).expanduser().read_text(encoding="utf-8"), None, False
    return "", None, False


def clean_body(body: str) -> str:
    body = body.replace("\r\n", "\n")
    return re.sub(r"\A(?:[ \t]*\n)+", "", body).rstrip()


def clean_title(raw: str | None, source: Path | None) -> str:
    title = (raw if raw is not None else source.stem if source else "").strip()
    if not title:
        raise CreateNoteError("--title is required (or --source to take it from the file name)")
    if "\n" in title or "\r" in title:
        raise CreateNoteError("--title must be a single line")
    return title


def build_title(kind: str, title: str, now: datetime) -> str:
    if kind == "contact":
        return capitalize_words(title)
    if kind == "meeting":
        subject = re.sub(r"\s*meeting minutes$", "", title, flags=re.IGNORECASE)
        if not subject:
            raise CreateNoteError("meeting --title needs a subject, not just 'meeting minutes'")
        return f"{now:%Y-%m-%d} | {capitalize_first(subject)} meeting minutes"
    return capitalize_first(title)


def note_type(args: argparse.Namespace) -> str:
    if args.kind != "note":
        return KINDS[args.kind]["type"]
    if not re.fullmatch(r"[a-z][a-z0-9-]*", args.type):
        raise CreateNoteError(f"--type '{args.type}' must be lowercase kebab-case")
    if args.type in DEDICATED_TYPES:
        raise CreateNoteError(f"type '{args.type}' has its own template; use that kind instead of 'note'")
    return args.type


def render(kind: str, values: dict, fields: dict, body: str) -> str:
    template = (TEMPLATES_DIR / KINDS[kind]["template"]).read_text(encoding="utf-8")
    text = string.Template(template).substitute(values, body=BODY_SENTINEL)
    match = re.match(r"---\n(.*?)\n---\n", text, re.S)
    text = "---\n" + apply_fields(match.group(1), fields) + "\n---\n" + text[match.end():]
    if body:
        text = text.replace(BODY_SENTINEL, body)
    else:
        text = re.sub(r"\n*" + re.escape(BODY_SENTINEL) + r"\n*", "\n\n", text)
    return text.rstrip("\n") + "\n"


def trash(vault: Path, source: Path) -> Path:
    trash_dir = vault / ".trash"
    trash_dir.mkdir(exist_ok=True)
    target = trash_dir / source.name
    counter = 1
    while target.exists():
        target = trash_dir / f"{source.stem} {counter}{source.suffix}"
        counter += 1
    source.rename(target)
    return target


@contextmanager
def vault_lock(zettelkasten: Path):
    """Serialise runs from id scan to write, so parallel runs cannot take the same id."""
    fd = os.open(zettelkasten, os.O_RDONLY)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        os.close(fd)


def log_in_daily_note(args: argparse.Namespace, vault: Path, now: datetime, wikilink: str, report: dict) -> list[str]:
    """Record the new note in the daily note's log; return errors instead of raising, as the note already exists."""
    if not args.daily_log:
        return []
    if args.dry_run:
        report["daily_log"] = {"status": "not written (dry run)", "entry": daily_log_entry(now, wikilink)}
        return []
    try:
        report["daily_log"] = append_daily_log(vault, now, wikilink)
    except (OSError, UnicodeError) as exc:
        return [f"cannot add the daily note log entry: {exc}"]
    return []


def create(args: argparse.Namespace) -> dict:
    vault = resolve_vault(args.vault)
    with vault_lock(vault / "notes"):
        if args.kind == "article":
            return create_article_locked(args, vault)
        return create_locked(args, vault)


def write_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(path, "xb")
    try:
        with handle:
            handle.write(data)
    except BaseException:
        path.unlink()  # the exclusive open made this file ours; never leave it partial
        raise


def render_linked(values: dict, body: str, backmatter: list[str]) -> str:
    content = render("note", values, {}, body).rstrip("\n")
    return content + "\n\n" + "\n".join(backmatter) + "\n"


def archive_file_name(title: str) -> str:
    """The original title, not slugified; only characters a macOS path cannot hold are replaced."""
    name = re.sub(r"[/\\:\x00-\x1f]", "-", title).strip().rstrip(".")
    if not name:
        raise CreateNoteError(f"title '{title}' cannot be used as a file name")
    return name


def create_article_locked(args: argparse.Namespace, vault: Path) -> dict:
    """Archive the original text outside the vault and write a `note` zettel with the core facts that links to it."""
    tags = parse_tags(args.tags, "note")
    raw_body, source, stripped_frontmatter = read_body(args, vault)
    original = clean_body(raw_body)
    if not original:
        raise CreateNoteError("article needs the original text: pass --body-file or --source")
    summary = clean_body(Path(args.summary_file).expanduser().read_text(encoding="utf-8"))
    if not summary:
        raise CreateNoteError("--summary-file is empty; write the core facts first")
    title = clean_title(args.title, source)
    web = (args.web or "").strip()
    if "\n" in web:
        raise CreateNoteError("--web must be a single line")
    summary, linked = link_contacts(summary, contact_names(vault)) if args.link_contacts else (summary, [])

    archive_root = Path(args.archive_root or ARTICLES_ROOT).expanduser()
    if not archive_root.parent.is_dir():
        raise CreateNoteError(f"{archive_root.parent} does not exist; set --archive-root")

    note_id, now = allocate_id(vault / "notes")
    note_title = capitalize_first(title)
    note_relative = f"notes/{note_id}.md"
    note_path = vault / note_relative
    archive_path = archive_root / f"{now:%Y}" / f"{now:%Y%m}00" / f"{archive_file_name(title)}.md"
    for path in (note_path, archive_path):
        if path.exists():
            raise CreateNoteError(f"{path} already exists; not overwriting")

    archive_text = f"# {title}\n\n{original}\n" + (f"\n---\n\nSource: {web}\n" if web else "")
    values = {
        "id": note_id,
        "title": note_title,
        "title_yaml": yaml_scalar(note_title),
        "date": now.isoformat(),
        "tags": "[" + ", ".join(tags) + "]",
        "type": "note",
    }
    backmatter = [f"- article:: [{title}](file://{quote(str(archive_path), safe='/')})"]
    if web:
        backmatter.append(f"- web:: [{title}]({web})")
    note_text = render_linked(values, summary, backmatter)

    report = {
        "kind": "article",
        "archive": {"path": str(archive_path)},
        "note": {
            "id": note_id, "type": "note", "title": note_title, "path": str(note_path),
            "relative_path": note_relative, "wikilink": f"[[{note_relative[:-3]}|{note_title}]]",
        },
    }
    if stripped_frontmatter:
        report["stripped_frontmatter"] = True
    if linked:
        report["linked_contacts"] = linked
    if args.dry_run:
        report["dry_run"] = True
        report["archive"]["content"] = archive_text
        report["note"]["content"] = note_text
        log_in_daily_note(args, vault, now, report["note"]["wikilink"], report)
        return report

    write_new(archive_path, archive_text.encode("utf-8"))
    try:
        write_new(note_path, note_text.encode("utf-8"))
    except BaseException:
        archive_path.unlink()  # never leave the archive copy without its note
        raise
    errors = log_in_daily_note(args, vault, now, report["note"]["wikilink"], report)
    if source:
        try:
            report["trashed_source"] = str(trash(vault, source))
        except OSError as exc:
            errors.append(f"cannot move {source} to .trash/: {exc}")
    if errors:
        report["errors"] = errors
    return report


def create_locked(args: argparse.Namespace, vault: Path) -> dict:
    fields = parse_fields(args.fields)
    tags = parse_tags(args.tags, args.kind)
    kind_type = note_type(args)
    raw_body, source, stripped_frontmatter = read_body(args, vault)
    body = clean_body(raw_body)
    linked: list[str] = []
    if args.link_contacts and args.kind != "contact":
        body, linked = link_contacts(body, contact_names(vault))
    title_input = clean_title(args.title, source)
    video = youtube_id(args.video) if args.kind == "youtube" else ""
    ticket = (args.ticket or "").strip() if args.kind == "project" else ""
    if "\n" in ticket:
        raise CreateNoteError("--ticket must be a single line")

    note_id, now = allocate_id(vault / "notes")
    title = build_title(args.kind, title_input, now)
    slug = slugify(title)
    if not slug and (KINDS[args.kind]["slug_name"] or args.kind == "project"):
        raise CreateNoteError(f"title '{title}' gives an empty slug; use a title with Latin letters or digits")

    folder = KINDS[args.kind]["folder"]
    stem = slug if KINDS[args.kind]["slug_name"] else note_id
    relative = f"{folder}/{stem}.md"
    path = vault / relative
    if path.exists():
        raise CreateNoteError(f"{relative} already exists; not overwriting")

    resources_path = ""
    if args.kind == "project":
        resources_path = f"{Path(PROJECTS_ROOT).expanduser()}/{note_id}-{slug}"
    values = {
        "id": note_id,
        "title": title,
        "title_yaml": yaml_scalar(title),
        "date": now.isoformat(),
        "tags": "[" + ", ".join(tags) + "]",
        "type": kind_type,
        "slug": slug,
        "video_id": video,
        "location": getattr(args, "location", "") or "",
        "deliverable": getattr(args, "deliverable", "") or "",
        "resources_url": file_url(resources_path) if resources_path else "",
        "log_timestamp": f"{now:%Y-%m-%d %H:%M}",
        "today": f"{now:%Y-%m-%d}",
        "ticket_line": f"\n- ticket:: {ticket}" if ticket else "",
    }
    content = render(args.kind, values, fields, body)
    try:
        data = content.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise CreateNoteError(f"note text is not valid utf-8 (undecodable bytes in --title, --fields, or the body?): {exc}")

    report = {
        "kind": args.kind,
        "type": kind_type,
        "id": note_id,
        "title": title,
        "path": str(path),
        "relative_path": relative,
        "wikilink": f"[[{relative[:-3]}|{title}]]",
    }
    if stripped_frontmatter:
        report["stripped_frontmatter"] = True
    if linked:
        report["linked_contacts"] = linked
    if args.dry_run:
        report.update({"dry_run": True, "content": content})
        if resources_path:
            report["resources_folder"] = {"path": resources_path, "status": "not created (dry run)"}
        log_in_daily_note(args, vault, now, report["wikilink"], report)
        return report

    path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(path, "xb")
    try:
        with handle:
            handle.write(data)
    except BaseException:
        path.unlink()  # the exclusive open made this file ours; never leave it partial
        raise
    # The note exists from here on, so later failures go into the report instead of aborting.
    errors = []
    if resources_path:
        root = Path(PROJECTS_ROOT).expanduser()
        if root.is_dir():
            try:
                Path(resources_path).mkdir(exist_ok=True)
                status = "created"
            except OSError as exc:
                status = "failed"
                errors.append(f"cannot create resources folder: {exc}")
        else:
            status = f"skipped: {root} does not exist on this machine"
        report["resources_folder"] = {"path": resources_path, "status": status}
    errors.extend(log_in_daily_note(args, vault, now, report["wikilink"], report))
    if source:
        try:
            report["trashed_source"] = str(trash(vault, source))
        except OSError as exc:
            errors.append(f"cannot move {source} to .trash/: {exc}")
    if errors:
        report["errors"] = errors
    return report


def build_parser() -> argparse.ArgumentParser:
    base = argparse.ArgumentParser(add_help=False)
    base.add_argument("--vault", help="vault root (default: $BIM_VAULT or ~/bim)")
    base.add_argument("--title", help="note title; defaults to the --source file name")
    base.add_argument("--tags", help="comma-separated tags, '#' optional")
    base.add_argument("--dry-run", action="store_true", help="print the note in the report instead of writing it")
    base.add_argument(
        "--no-link-contacts", dest="link_contacts", action="store_false",
        help="keep the body verbatim: do not wikilink names that match notes in notes/contact/ (use for exact copies)",
    )
    base.add_argument(
        "--no-daily-log", dest="daily_log", action="store_false",
        help="do not add a log entry linking the new note to today's daily note",
    )
    body = base.add_mutually_exclusive_group()
    body.add_argument("--body-file", help="Markdown file with the body, or '-' for stdin")
    body.add_argument("--source", help="inbox file to convert; moved to .trash/ after the note is written")
    common = argparse.ArgumentParser(add_help=False, parents=[base])
    common.add_argument("--fields", help="JSON object of extra or replaced frontmatter keys")

    parser = argparse.ArgumentParser(description="Create a BIM zettelkasten note from a ported vault template.")
    sub = parser.add_subparsers(dest="kind", required=True)
    note = sub.add_parser("note", parents=[common], help="generic note (any type without its own template)")
    note.add_argument("--type", default="note", help="frontmatter type, e.g. list, procedure, definition")
    sub.add_parser("illustrated", parents=[common], help="Excalidraw illustrated note")
    meeting = sub.add_parser("meeting", parents=[common], help="meeting minutes")
    meeting.add_argument("--location", required=True, choices=LOCATIONS)
    youtube = sub.add_parser("youtube", parents=[common], help="notes on a YouTube video")
    youtube.add_argument("--video", required=True, help="YouTube URL or 11-character video id")
    sub.add_parser("prr", parents=[common], help="problem resolution report")
    sub.add_parser("book", parents=[common], help="book note in notes/book/")
    sub.add_parser("contact", parents=[common], help="person in notes/contact/")
    article = sub.add_parser(
        "article", parents=[base],
        help="archive the original text (--body-file/--source) under 40-archives/articles and write a linked `note` zettel with the core facts",
    )
    article.add_argument("--summary-file", required=True, help="Markdown file with the core facts for the note zettel")
    article.add_argument("--web", help="URL of the original article, kept in the archive copy and as a web:: field in the note")
    article.add_argument("--archive-root", help=f"articles archive root (default: {ARTICLES_ROOT})")
    project = sub.add_parser("project", parents=[common], help="project loop file plus resources folder")
    project.add_argument("--deliverable", required=True, choices=DELIVERABLES)
    project.add_argument("--ticket", help="service request or ticket id for the ticket:: field")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = create(args)
    except (CreateNoteError, OSError, UnicodeError) as exc:
        print(f"create-note: error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if report.get("errors"):
        print("create-note: error: note created, but: " + "; ".join(report["errors"]), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
