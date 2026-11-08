#!/usr/bin/env python3
"""Copy rich text to macOS clipboard from HTML or Markdown.

Usage:
    python3 copy_rich.py -f /tmp/content.md       # Markdown file (auto-detected)
    python3 copy_rich.py -f /tmp/content.html      # HTML file
    python3 copy_rich.py '<b>Hello</b>'            # HTML string argument
    python3 copy_rich.py -                         # HTML/Markdown from stdin

Features:
- Converts Markdown to HTML (basic subset: bold, links, line breaks)
- Auto-links Jira issue keys (PROJ-123) to $JIRA_BASE_URL/<key> when that
  environment variable is set (e.g. https://jira.example.com/browse)
- Embeds local images (![alt](path)) as base64 data URIs
- Copies both HTML (carries images) and RTF (formatting fallback) to the
  clipboard via PyObjC when available, otherwise falls back to
  textutil + pbcopy (RTF only - no image support on that path).

macOS only (requires textutil and pbcopy; PyObjC/AppKit is required for images
and Teams-native code blocks, and Pygments is required for immediate syntax
colors in language-bearing fenced blocks).
"""

import base64
import html as html_module
import mimetypes
import os
import re
import subprocess
import sys
import tempfile
import uuid

try:
    import AppKit
    from Foundation import NSData

    _HAS_APPKIT = True
except ImportError:
    _HAS_APPKIT = False

try:
    from pygments import lex
    from pygments.lexers import get_lexer_by_name
    from pygments.token import Comment, Keyword, Name, String
    from pygments.util import ClassNotFound
except ImportError:
    lex = None
    get_lexer_by_name = None
    Comment = None
    Keyword = None
    Name = None
    String = None
    ClassNotFound = None

# Browse URL of the Jira instance, without a trailing slash. Empty disables
# auto-linking, so bare keys stay plain text instead of pointing nowhere.
JIRA_BASE_URL = os.environ.get("JIRA_BASE_URL", "").rstrip("/")


# Matches JIRA-style keys: 2+ uppercase letters, dash, 1+ digits
JIRA_KEY_RE = re.compile(r"\b([A-Z][A-Z0-9]+-\d+)\b")

# Existing links and code must remain byte-for-byte unchanged by auto-linking.
AUTO_LINK_PROTECTED_RE = re.compile(
    r"<(?P<tag>a|pre|code)\b[^>]*>.*?</(?P=tag)>",
    re.IGNORECASE | re.DOTALL,
)


def auto_link_jira_keys(html: str) -> str:
    """Wrap bare Jira keys in <a> tags. Skip links and source code.

    Strategy: split the HTML around existing links and code regions, then
    apply the regex only to unprotected text.
    """
    if not JIRA_BASE_URL:
        return html
    parts = []
    last_end = 0

    for m in AUTO_LINK_PROTECTED_RE.finditer(html):
        gap = html[last_end:m.start()]
        parts.append(_linkify_keys(gap))
        parts.append(m.group(0))
        last_end = m.end()

    # Process the tail after the last link
    parts.append(_linkify_keys(html[last_end:]))

    return "".join(parts)


def _linkify_keys(text: str) -> str:
    """Replace bare Jira keys with <a> links in a text fragment
    that is guaranteed to contain no protected HTML regions."""
    return JIRA_KEY_RE.sub(
        lambda m: f'<a href="{JIRA_BASE_URL}/{m.group(1)}">{m.group(1)}</a>',
        text,
    )


HEADING_SIZES = {1: "18pt", 2: "15pt", 3: "12pt"}

# Formatting is delivered to Teams through the raw-HTML clipboard type, not
# RTF. That distinction matters: Teams' RTF paste path strips <s>, color and
# background-color, but its HTML paste path preserves all three (confirmed
# empirically). So real tags are used here rather than Unicode substitution
# look-alikes. See SKILL.md "Teams-specific gotchas" for the full test matrix.


def _is_unordered_item(line: str) -> bool:
    """Detect lines that are implicit unordered list items.

    Matches:
    - Markdown bullets: - item, * item
    - Jira key lines: PROJ-1234 - description
    """
    return bool(
        re.match(r"^[-*]\s+", line)
        or re.match(r"^[A-Z][A-Z0-9]+-\d+\s", line)
    )


def _is_ordered_item(line: str) -> bool:
    """Detect markdown ordered list items: 1. item, 2) item."""
    return bool(re.match(r"^\d+[.)]\s+", line))


def _is_table_row(line: str) -> bool:
    """Detect a markdown table row: starts and ends with | (or just has one)."""
    return "|" in line and not re.match(r"^\s*$", line)


def _is_table_separator(line: str) -> bool:
    """Detect a markdown table header separator: | --- | :---: | ---: |"""
    return bool(re.match(r"^\|?\s*:?-+:?\s*(\|\s*:?-+:?\s*)*\|?$", line))


def _is_blockquote(line: str) -> bool:
    return bool(re.match(r"^>\s?", line))


def _is_hr(line: str) -> bool:
    """Detect a horizontal rule: ---, ***, ___ (3+ chars, nothing else)."""
    return bool(re.match(r"^(-{3,}|\*{3,}|_{3,})$", line))


def _split_table_row(line: str) -> list:
    """Split a markdown table row into cell text, stripping leading/trailing pipes."""
    row = line.strip()
    if row.startswith("|"):
        row = row[1:]
    if row.endswith("|"):
        row = row[:-1]
    return [cell.strip() for cell in row.split("|")]


def _render_table(rows: list) -> str:
    """Render buffered markdown table lines (including the --- separator) as HTML."""
    if len(rows) < 2 or not _is_table_separator(rows[1]):
        # Not actually a table (no header separator) - treat as plain lines.
        return "".join(_inline_markdown(r) + "<br>" for r in rows)

    header_cells = _split_table_row(rows[0])
    body_rows = [_split_table_row(r) for r in rows[2:]]

    out = ['<table border="1" cellpadding="4" cellspacing="0">', "<tr>"]
    for cell in header_cells:
        out.append(f"<th>{_inline_markdown(cell)}</th>")
    out.append("</tr>")
    for row in body_rows:
        out.append("<tr>")
        for cell in row:
            out.append(f"<td>{_inline_markdown(cell)}</td>")
        out.append("</tr>")
    out.append("</table>")
    return "".join(out)


FENCE_RE = re.compile(r"```([^\n]*)\n(.*?)```", re.DOTALL)
TEAMS_CODE_BLOCK_ITEMTYPE = "http://schema.skype.com/CodeBlockEditor"

TEAMS_LANGUAGE_ALIASES = {
    "bash": "bash",
    "c": "c",
    "c#": "csharp",
    "c++": "cpp",
    "cpp": "cpp",
    "cs": "csharp",
    "csharp": "csharp",
    "css": "css",
    "go": "go",
    "html": "html",
    "java": "java",
    "javascript": "javascript",
    "js": "javascript",
    "json": "json",
    "kotlin": "kotlin",
    "kql": "kql",
    "less": "less",
    "lua": "lua",
    "markdown": "markdown",
    "md": "markdown",
    "objective-c": "objectivec",
    "objectivec": "objectivec",
    "objc": "objectivec",
    "perl": "perl",
    "php": "php",
    "plaintext": "plaintext",
    "powershell": "powershell",
    "ps1": "powershell",
    "py": "python",
    "python": "python",
    "r": "r",
    "rb": "ruby",
    "rs": "rust",
    "ruby": "ruby",
    "rust": "rust",
    "scss": "scss",
    "sh": "bash",
    "shell": "shell",
    "sql": "sql",
    "swift": "swift",
    "text": "plaintext",
    "ts": "typescript",
    "txt": "plaintext",
    "typescript": "typescript",
    "vb": "vbnet",
    "vb.net": "vbnet",
    "vbnet": "vbnet",
    "xml": "xml",
    "yaml": "yaml",
    "yml": "yaml",
}

# Placeholder marker - control characters never appear in normal text input,
# so fenced blocks can't collide with user content during the line-by-line pass.
_FENCE_PLACEHOLDER = "\x00FENCE{}\x00"


def _escape_code_text(value: str) -> str:
    normalized = value.replace("\r\n", "\n").replace("\r", "\n")
    escaped = html_module.escape(normalized)
    return escaped.replace("\t", "&nbsp;" * 4).replace(" ", "&nbsp;").replace(
        "\n", "<br>"
    )


def _teams_token_class(token_type) -> str | None:
    if token_type in Keyword or token_type in Name.Tag:
        return "hljs-keyword"
    if token_type in Comment:
        return "hljs-comment"
    if token_type in String:
        return "hljs-string"
    if (
        token_type in Name.Function
        or token_type in Name.Class
        or token_type in Name.Builtin
        or token_type in Name.Attribute
    ):
        return "hljs-function"
    return None


def _highlight_code(code: str, language: str) -> str:
    if not language or language in {"plaintext", "text", "txt"}:
        return _escape_code_text(code)
    if lex is None or get_lexer_by_name is None:
        raise RuntimeError(
            "Pygments is required to copy fenced code with immediate Teams "
            "syntax highlighting"
        )
    try:
        lexer = get_lexer_by_name(language, stripnl=False, ensurenl=False)
    except ClassNotFound as exc:
        raise RuntimeError(
            f"No Pygments lexer is available for fenced language {language!r}; "
            "use a plaintext fence or install a lexer that supports it"
        ) from exc

    segments = []
    for token_type, value in lex(code, lexer):
        token_class = _teams_token_class(token_type)
        if not value.strip():
            token_class = None
        if segments and segments[-1][0] == token_class:
            previous_class, previous_value = segments[-1]
            segments[-1] = (previous_class, previous_value + value)
        else:
            segments.append((token_class, value))

    rendered = []
    for token_class, value in segments:
        escaped = _escape_code_text(value)
        if token_class:
            rendered.append(f'<span class="{token_class}">{escaped}</span>')
        else:
            rendered.append(escaped)
    return "".join(rendered)


def _render_code_block(code: str, language: str = "") -> str:
    """Render a fence using Teams' native compose-editor clipboard schema."""
    code = code.rstrip("\n")
    raw_language = (
        language.strip().split()[0].lower() if language.strip() else ""
    )
    teams_language = TEAMS_LANGUAGE_ALIASES.get(raw_language, "plaintext")
    highlighted = _highlight_code(code, raw_language)
    header_id = f"x_x_{uuid.uuid4().hex}"
    block_id = f"codeBlockEditor-{uuid.uuid4()}"
    return (
        "<p>&nbsp;</p>"
        f'<p itemtype="{TEAMS_CODE_BLOCK_ITEMTYPE}" '
        f'id="{header_id}">&nbsp;</p>'
        f'<pre class="language-{teams_language} skipProofing" '
        f'itemid="{block_id}" corrected="true" spellcheck="false"><code>'
        f"{highlighted}"
        "</code></pre><p>&nbsp;</p>"
    )


def _extract_fenced_code_blocks(text: str) -> tuple:
    """Pull out ```fenced``` code blocks before line-based parsing runs.

    Returns (text_with_placeholders, {placeholder: rendered_html}).
    """
    blocks = {}

    def _replace(match):
        index = len(blocks)
        placeholder = _FENCE_PLACEHOLDER.format(index)
        blocks[placeholder] = _render_code_block(match.group(2), match.group(1))
        return placeholder

    return FENCE_RE.sub(_replace, text), blocks


def markdown_to_html(text: str) -> str:
    """Convert a useful Markdown subset to HTML.

    Handles: **bold**, *italic*, ~~strikethrough~~, `code`, fenced ``` code
    blocks ``` (indentation preserved), [text](url), blank-line paragraph
    breaks, single newlines as <br>, headings (# ## ###) with distinct sizes,
    unordered lists (- item), ordered lists (1. item) - both with arbitrary
    space-indented nesting, consecutive Jira-key lines (auto-wrapped in
    <ul><li>), blockquotes (> text), horizontal rules (---), and pipe tables.

    Spacing model: a blank source line sets a "pending gap" flag rather than
    emitting <br> immediately. The next real content flushes exactly one
    <br> for it. Headings and horizontal rules always force that pending
    gap themselves (so there's a visible gap below a heading even with no
    blank line in the source) and swallow one following blank line from the
    source (so it never doubles up into two gaps).
    """
    text, fence_blocks = _extract_fenced_code_blocks(text)
    lines = text.split("\n")
    html_lines = []
    table_buffer = []
    list_stack = []  # [{'type': 'ul'|'ol', 'indent': int}, ...], outer to inner

    pending_blank = False
    swallow_next_blank = False

    def take_blank():
        nonlocal pending_blank, swallow_next_blank
        if swallow_next_blank:
            swallow_next_blank = False
            return
        pending_blank = True

    def emit(line_html):
        nonlocal pending_blank, swallow_next_blank
        if pending_blank:
            html_lines.append("<br>")
        pending_blank = False
        swallow_next_blank = False
        html_lines.append(line_html)

    def close_list_level():
        top = list_stack.pop()
        html_lines.append(f"</li></{top['type']}>")

    def close_all_lists():
        while list_stack:
            close_list_level()

    def handle_list_item(indent, list_type, content):
        nonlocal pending_blank, swallow_next_blank
        starting_new_list = not list_stack
        if starting_new_list:
            if pending_blank:
                html_lines.append("<br>")
            pending_blank = False
            swallow_next_blank = False

        while list_stack and (
            indent < list_stack[-1]["indent"]
            or (indent == list_stack[-1]["indent"] and list_stack[-1]["type"] != list_type)
        ):
            close_list_level()

        if list_stack and indent == list_stack[-1]["indent"]:
            html_lines.append("</li>")
        else:
            list_stack.append({"type": list_type, "indent": indent})
            html_lines.append(f"<{list_type}>")
        html_lines.append(f"<li>{content}")

    def flush_table():
        if table_buffer:
            close_all_lists()
            emit(_render_table(list(table_buffer)))
            table_buffer.clear()

    for line in lines:
        stripped = line.strip()
        indent = len(line) - len(line.lstrip(" "))

        # Fenced code block placeholder - already rendered, pass through as-is
        if stripped in fence_blocks:
            flush_table()
            close_all_lists()
            emit(stripped)
            continue

        # Pipe tables: buffer consecutive table rows, render as a block
        if _is_table_row(stripped):
            close_all_lists()
            table_buffer.append(stripped)
            continue
        flush_table()

        # Horizontal rule - a section break is already its own visual gap,
        # so it consumes any pending gap instead of stacking one on top.
        if _is_hr(stripped):
            close_all_lists()
            pending_blank = False
            html_lines.append("<hr>")
            swallow_next_blank = True
            continue

        # Blockquote
        if _is_blockquote(stripped):
            close_all_lists()
            content = _inline_markdown(re.sub(r"^>\s?", "", stripped))
            emit(f"<i>{content}</i><br>")
            continue

        # Ordered list items (any space-indentation nests under the last
        # shallower item)
        if _is_ordered_item(stripped):
            item = re.sub(r"^\d+[.)]\s+", "", stripped)
            handle_list_item(indent, "ol", _inline_markdown(item))
            continue

        # Unordered list items (explicit markdown bullets or Jira key lines)
        if _is_unordered_item(stripped):
            item = re.sub(r"^[-*]\s+", "", stripped)
            handle_list_item(indent, "ul", _inline_markdown(item))
            continue

        close_all_lists()

        # Blank line = paragraph break
        if not stripped:
            take_blank()
            continue

        # Headings - distinct sizes so hierarchy survives the paste. Always
        # force a gap below (even with no blank line in the source).
        heading_match = re.match(r"^(#{1,3})\s+(.*)", stripped)
        if heading_match:
            level = len(heading_match.group(1))
            content = _inline_markdown(heading_match.group(2))
            size = HEADING_SIZES[level]
            emit(f'<b><span style="font-size:{size}">{content}</span></b><br>')
            pending_blank = True
            swallow_next_blank = True
            continue

        # Regular line
        emit(_inline_markdown(stripped) + "<br>")

    flush_table()
    close_all_lists()

    result = "\n".join(html_lines)
    for placeholder, rendered in fence_blocks.items():
        result = result.replace(placeholder, rendered)
    if fence_blocks:
        result = f'<span data-teams="true">{result}</span>'
    return result


def _render_image(alt: str, src: str) -> str:
    """Render a Markdown image as an <img> tag.

    Remote URLs and data: URIs pass through untouched. A local file path is
    read and inlined as a base64 data URI, since the image must travel with
    the clipboard content itself (Teams paste can't fetch a local file:// or
    relative path - confirmed working for data: URIs, confirmed broken for
    bare file paths).
    """
    if re.match(r"^(https?:|data:)", src, re.IGNORECASE):
        return f'<img src="{src}" alt="{alt}">'

    path = os.path.expanduser(src)
    if not os.path.isfile(path):
        return f"[image not found: {src}]"
    mime = mimetypes.guess_type(path)[0] or "application/octet-stream"
    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("ascii")
    return f'<img src="data:{mime};base64,{b64}" alt="{alt}">'


def _inline_markdown(text: str) -> str:
    """Convert inline Markdown: **bold**, *italic*, ~~strikethrough~~, `code`,
    ![alt](src), [text](url).

    Inline code becomes a real <code> element and strikethrough a real <s>
    element. Both survive Teams' HTML paste path (<code> renders as a boxed
    monospace span, <s> as true strikethrough), which is the path this script
    delivers on - the RTF path strips both, which is why these were previously
    faked with Unicode look-alike characters.
    """
    # Inline code first, pulled out behind placeholders so its contents can't
    # be re-matched by the bold/italic regexes below (e.g. "copy_rich.py"
    # getting mangled into "copy<i>rich</i>.py").
    code_spans = {}

    def _stash_code(m):
        index = len(code_spans)
        placeholder = f"\x00ICODE{index}\x00"
        code_spans[placeholder] = (
            f"<code>{html_module.escape(m.group(1))}</code>"
        )
        return placeholder

    text = re.sub(r"`([^`]+)`", _stash_code, text)
    # Images: ![alt](src) - before the link regex, so the leading "!" isn't
    # left stranded in front of an <a> tag.
    text = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        lambda m: _render_image(m.group(1), m.group(2)),
        text,
    )
    # Strikethrough: ~~text~~ (before bold/italic - no marker overlap with * or _)
    text = re.sub(r"~~(.+?)~~", r"<s>\1</s>", text)
    # Bold: **text** or __text__
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"__(.+?)__", r"<b>\1</b>", text)
    # Italic: *text* or _text_ (single marker, after bold is consumed)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<i>\1</i>", text)
    # CommonMark forbids "_" emphasis from opening/closing mid-word, so a
    # lone underscore inside a filename like "copy_rich.py" is never treated
    # as an emphasis marker, even if another lone underscore appears later
    # in the same line (e.g. "scripts/copy_rich.py -f assets/test_payload.md").
    text = re.sub(
        r"(?<![\w_])_(?!_)(.+?)(?<!_)_(?![\w_])", r"<i>\1</i>", text
    )
    # Links: [text](url)
    text = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        r'<a href="\2">\1</a>',
        text,
    )
    for placeholder, rendered in code_spans.items():
        text = text.replace(placeholder, rendered)
    return text




def is_html(text: str) -> bool:
    """Detect whether content is HTML (has actual tags)."""
    if FENCE_RE.search(text):
        return False
    return bool(re.search(r"<(b|i|s|a|p|ul|ol|li|br|hr|span|code|pre|div|img|"
                          r"blockquote|table|tr|td|th|h[1-6])\b",
                          text, re.IGNORECASE))


def copy_html_as_rich_text(html: str) -> None:
    """Copy HTML and an RTF fallback to the macOS clipboard.

    Without an explicit charset, textutil guesses the file's encoding and
    regularly guesses wrong for UTF-8 - it then decodes each UTF-8 byte as
    its own Latin-1/MacRoman character, turning non-ASCII text into mojibake.
    Wrapping in a declared UTF-8 document forces the correct decode.
    """
    if re.search(r"<html\b", html, re.IGNORECASE):
        # Caller passed a full document already - just make sure it declares
        # UTF-8 so textutil doesn't guess wrong and mangle non-ASCII text.
        if not re.search(r"charset", html, re.IGNORECASE):
            html = re.sub(
                r"<head[^>]*>",
                lambda m: m.group(0) + '<meta charset="utf-8">',
                html,
                count=1,
                flags=re.IGNORECASE,
            )
        document = html
    else:
        document = (
            '<html><head><meta charset="utf-8"></head><body>'
            f"{html}</body></html>"
        )

    if not _HAS_APPKIT:
        html_only_features = []
        if TEAMS_CODE_BLOCK_ITEMTYPE in document:
            html_only_features.append("Teams-native code blocks")
        if re.search(r"<img\b", document, re.IGNORECASE):
            html_only_features.append("embedded images")
        if html_only_features:
            features = " and ".join(html_only_features)
            raise RuntimeError(
                f"PyObjC/AppKit is required for {features}; "
                "the RTF-only fallback cannot preserve them"
            )

    with tempfile.NamedTemporaryFile(
        suffix=".html", mode="w", delete=False, encoding="utf-8"
    ) as f:
        f.write(document)
        tmp_path = f.name

    try:
        rtf = subprocess.run(
            ["textutil", "-convert", "rtf", "-stdout", tmp_path],
            capture_output=True,
            check=True,
        )
    finally:
        os.unlink(tmp_path)

    if _HAS_APPKIT:
        # Offer both representations: HTML (the only one that carries
        # embedded images - textutil's RTF conversion silently drops <img>
        # regardless of file:// or data: URI source, confirmed empirically)
        # and RTF (a fallback for apps that prefer RTF over HTML). Teams uses
        # the HTML representation, which is also what carries Teams' native
        # CodeBlockEditor clipboard schema.
        pb = AppKit.NSPasteboard.generalPasteboard()
        pb.clearContents()
        pb.declareTypes_owner_(
            [AppKit.NSPasteboardTypeHTML, AppKit.NSPasteboardTypeRTF], None
        )
        pb.setString_forType_(document, AppKit.NSPasteboardTypeHTML)
        pb.setData_forType_(
            NSData.dataWithBytes_length_(rtf.stdout, len(rtf.stdout)),
            AppKit.NSPasteboardTypeRTF,
        )
    else:
        # No PyObjC - fall back to RTF-only via pbcopy (no image support).
        subprocess.run(["pbcopy"], input=rtf.stdout, check=True)


def main() -> None:
    if len(sys.argv) < 2:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    # Read input
    if sys.argv[1] == "-f" and len(sys.argv) >= 3:
        file_path = sys.argv[2]
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
    elif sys.argv[1] == "-":
        content = sys.stdin.read()
    else:
        content = sys.argv[1]

    if not content.strip():
        print("Error: empty input", file=sys.stderr)
        sys.exit(1)

    try:
        # Detect format by content, not file extension.
        # If it has HTML tags, treat as HTML. Otherwise, convert from Markdown.
        if is_html(content):
            html = content
        else:
            html = markdown_to_html(content)

        # Auto-link bare Jira keys without touching links or source code.
        html = auto_link_jira_keys(html)
        copy_html_as_rich_text(html)
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    print("Rich text copied to clipboard.")


if __name__ == "__main__":
    main()
