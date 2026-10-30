#!/usr/bin/env python3
"""Convert Markdown to Confluence storage format (XHTML) with neutral styling.

Usage: python3 md_to_confluence.py input.md [--output file.html]

Without --output, prints the Confluence storage markup to stdout
(ready to paste into create_page / update_page tools).
"""
import sys
import re
import yaml
from pathlib import Path

# Neutral style constants for inline styles
ACCENT_COLOR = "#334155"
STYLE_DARK = "#333333"
STYLE_GRAY = "#666666"
STYLE_TABLE_HDR_BG = "#334155"
STYLE_TABLE_ALT_BG = "#F5F5F5"
STYLE_WHITE = "#FFFFFF"
STYLE_BORDER = "#CCCCCC"


def parse_front_matter(text: str) -> tuple:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            return yaml.safe_load(parts[1]) or {}, parts[2].strip()
    return {}, text


def escape_html(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def inline_format(text: str) -> str:
    """Convert inline markdown to HTML."""
    # Code spans first
    text = re.sub(r"`([^`]+)`", r'<code>\1</code>', text)
    # Bold+italic
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", text)
    # Bold
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    # Italic
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    # Links
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
    return text


def convert_table(lines: list) -> str:
    """Convert markdown table to Confluence table with neutral styling."""
    if len(lines) < 2:
        return ""
    headers = [c.strip() for c in lines[0].strip("|").split("|")]
    rows = []
    for line in lines[2:]:
        rows.append([c.strip() for c in line.strip("|").split("|")])

    out = ['<table><colgroup>' + '<col/>' * len(headers) + '</colgroup><tbody>']
    # Header row
    out.append("<tr>")
    for h in headers:
        out.append(
            f'<th style="background-color:{STYLE_TABLE_HDR_BG};color:{STYLE_WHITE};'
            f'font-family:Arial;font-weight:bold;padding:8px;">'
            f'{inline_format(escape_html(h))}</th>'
        )
    out.append("</tr>")
    # Data rows
    for i, row in enumerate(rows):
        bg = f' style="background-color:{STYLE_TABLE_ALT_BG};"' if i % 2 == 1 else ""
        out.append(f"<tr{bg}>")
        for cell in row:
            out.append(
                f'<td style="font-family:Arial;padding:6px;border:1px solid {STYLE_BORDER};">'
                f'{inline_format(escape_html(cell))}</td>'
            )
        out.append("</tr>")
    out.append("</tbody></table>")
    return "".join(out)


def convert(input_path: str, output_path: str | None = None):
    text = Path(input_path).read_text(encoding="utf-8")
    meta, body = parse_front_matter(text)
    lines = body.split("\n")
    html_parts = []

    # Info panel with metadata
    if meta:
        panel = (
            f'<ac:structured-macro ac:name="info"><ac:rich-text-body>'
            f'<p style="font-family:Arial;color:{STYLE_GRAY};">'
        )
        for k in ["date", "author", "version", "classification", "jira_story"]:
            if meta.get(k):
                panel += f"<strong>{k.replace('_',' ').title()}</strong>: {escape_html(str(meta[k]))} &nbsp; "
        panel += "</p></ac:rich-text-body></ac:structured-macro>"
        html_parts.append(panel)

    # TOC macro
    html_parts.append('<ac:structured-macro ac:name="toc"><ac:parameter ac:name="maxLevel">3</ac:parameter></ac:structured-macro>')

    i = 0
    in_code = False
    code_lines = []
    code_lang = ""
    in_list = False
    list_type = ""

    while i < len(lines):
        line = lines[i]

        # Code blocks → Confluence code macro
        if line.strip().startswith("```"):
            if not in_code:
                in_code = True
                code_lang = line.strip().lstrip("`").strip() or "none"
                code_lines = []
            else:
                in_code = False
                code_content = escape_html("\n".join(code_lines))
                html_parts.append(
                    f'<ac:structured-macro ac:name="code">'
                    f'<ac:parameter ac:name="language">{code_lang}</ac:parameter>'
                    f'<ac:parameter ac:name="theme">Confluence</ac:parameter>'
                    f'<ac:plain-text-body><![CDATA[{chr(10).join(code_lines)}]]></ac:plain-text-body>'
                    f'</ac:structured-macro>'
                )
            i += 1
            continue

        if in_code:
            code_lines.append(line)
            i += 1
            continue

        # Close open list if line is not a list item
        is_bullet = bool(re.match(r"^\s*[-*]\s+", line))
        is_numbered = bool(re.match(r"^\s*\d+\.\s+", line))
        if in_list and not is_bullet and not is_numbered:
            html_parts.append(f"</{list_type}>")
            in_list = False

        # Tables
        if "|" in line and i + 1 < len(lines) and re.match(r"^\s*\|[\s\-:|]+\|\s*$", lines[i + 1]):
            table_lines = []
            while i < len(lines) and "|" in lines[i]:
                table_lines.append(lines[i])
                i += 1
            html_parts.append(convert_table(table_lines))
            continue

        # Headings
        m = re.match(r"^(#{1,6})\s+(.+)$", line)
        if m:
            level = len(m.group(1))
            heading_text = inline_format(escape_html(m.group(2)))
            color = ACCENT_COLOR if level <= 2 else STYLE_DARK
            html_parts.append(
                f'<h{level} style="color:{color};font-family:Arial;">{heading_text}</h{level}>'
            )
            i += 1
            continue

        # Bullet list
        if is_bullet:
            text = re.sub(r"^\s*[-*]\s+", "", line)
            if not in_list or list_type != "ul":
                if in_list:
                    html_parts.append(f"</{list_type}>")
                html_parts.append("<ul>")
                in_list = True
                list_type = "ul"
            html_parts.append(f"<li>{inline_format(escape_html(text))}</li>")
            i += 1
            continue

        # Numbered list
        if is_numbered:
            text = re.sub(r"^\s*\d+\.\s+", "", line)
            if not in_list or list_type != "ol":
                if in_list:
                    html_parts.append(f"</{list_type}>")
                html_parts.append("<ol>")
                in_list = True
                list_type = "ol"
            html_parts.append(f"<li>{inline_format(escape_html(text))}</li>")
            i += 1
            continue

        # Horizontal rule
        if re.match(r"^---+$", line.strip()):
            html_parts.append("<hr/>")
            i += 1
            continue

        # Regular paragraph
        stripped = line.strip()
        if stripped:
            html_parts.append(
                f'<p style="font-family:Arial;color:{STYLE_DARK};">{inline_format(escape_html(stripped))}</p>'
            )
        i += 1

    if in_list:
        html_parts.append(f"</{list_type}>")

    result = "\n".join(html_parts)
    if output_path:
        Path(output_path).write_text(result, encoding="utf-8")
        print(f"Created: {output_path}")
    else:
        print(result)
    return result


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        print(f"Usage: {sys.argv[0]} input.md [--output file.html]")
        sys.exit(1)
    inp = args[0]
    out = None
    if "--output" in args:
        out = args[args.index("--output") + 1]
    convert(inp, out)
