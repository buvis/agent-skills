#!/usr/bin/env python3
"""Convert Confluence storage format (XHTML) to Markdown.

Usage: python3 confluence_to_md.py input.html output.md
       echo '<html>...</html>' | python3 confluence_to_md.py - output.md
"""
import sys
import re
from pathlib import Path
from datetime import date
from html.parser import HTMLParser


class ConfluenceToMd(HTMLParser):
    def __init__(self):
        super().__init__()
        self.md = []
        self.tag_stack = []
        self.in_code_macro = False
        self.code_lang = ""
        self.code_body = []
        self.in_table = False
        self.table_rows = []
        self.current_row = []
        self.current_cell = []
        self.is_header_row = False
        self.list_stack = []  # track nested ul/ol
        self.inline_buf = []
        self.href_stack = []  # one entry per open <a>; "" when it has no href
        self.skip = False
        self.macro_name = ""

    def handle_starttag(self, tag, attrs):
        attrs_d = dict(attrs)
        tag = tag.lower()
        self.tag_stack.append(tag)

        # Confluence macros
        if tag == "ac:structured-macro":
            self.macro_name = attrs_d.get("ac:name", "")
            if self.macro_name == "code":
                self.in_code_macro = True
                self.code_lang = ""
                self.code_body = []
            elif self.macro_name in ("toc", "info", "note", "warning", "tip"):
                self.skip = True
            return

        if tag == "ac:parameter" and self.in_code_macro:
            return
        if tag == "ac:plain-text-body" and self.in_code_macro:
            return

        if self.skip:
            return

        self._flush_inline()  # pending inline text precedes any block markup

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            level = int(tag[1])
            self.md.append(f"\n{'#' * level} ")
        elif tag == "p":
            pass
        elif tag == "strong" or tag == "b":
            self._emit("**")
        elif tag == "em" or tag == "i":
            self._emit("*")
        elif tag == "code":
            self._emit("`")
        elif tag == "a":
            href = attrs_d.get("href", "")
            self.href_stack.append(href)
            if href:
                self._emit("[")
        elif tag == "ul":
            self.list_stack.append("ul")
        elif tag == "ol":
            self.list_stack.append("ol")
        elif tag == "li":
            indent = "  " * max(0, len(self.list_stack) - 1)
            if self.list_stack and self.list_stack[-1] == "ol":
                self.md.append(f"\n{indent}1. ")
            else:
                self.md.append(f"\n{indent}- ")
        elif tag == "table":
            self.in_table = True
            self.table_rows = []
        elif tag == "tr":
            self.current_row = []
            self.is_header_row = False
        elif tag in ("th", "td"):
            self.current_cell = []
            if tag == "th":
                self.is_header_row = True
        elif tag == "br":
            self.md.append("  \n")
        elif tag == "hr":
            self.md.append("\n---\n")

    def handle_endtag(self, tag):
        tag = tag.lower()
        if self.tag_stack:
            self.tag_stack.pop()

        if tag == "ac:structured-macro":
            if self.in_code_macro:
                self.in_code_macro = False
                self.md.append(f"\n```{self.code_lang}\n")
                self.md.append("\n".join(self.code_body))
                self.md.append("\n```\n")
            if self.skip and self.macro_name in ("toc", "info", "note", "warning", "tip"):
                self.skip = False
            self.macro_name = ""
            return

        if self.skip:
            return

        self._flush_inline()  # close inline markers before block separators

        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self.md.append("\n")
        elif tag == "p":
            self.md.append("\n\n")
        elif tag == "strong" or tag == "b":
            self._emit("**")
        elif tag == "em" or tag == "i":
            self._emit("*")
        elif tag == "code" and not self.in_code_macro:
            self._emit("`")
        elif tag == "a":
            href = self.href_stack.pop() if self.href_stack else ""
            if href:
                self._emit(f"]({href})")
        elif tag in ("ul", "ol"):
            if self.list_stack:
                self.list_stack.pop()
            self.md.append("\n")
        elif tag in ("th", "td"):
            self.current_row.append("".join(self.current_cell).strip())
            self.current_cell = []
        elif tag == "tr":
            self.table_rows.append((self.is_header_row, self.current_row))
        elif tag == "table":
            self.in_table = False
            self._flush_table()

    def handle_data(self, data):
        if self.in_code_macro and self.tag_stack and "ac:plain-text-body" in self.tag_stack[-1:]:
            self.code_body.append(data)
            return
        if self.in_code_macro:
            # Could be parameter value
            if self.tag_stack and "ac:parameter" in self.tag_stack[-1:]:
                self.code_lang = data.strip()
            elif "ac:plain-text-body" in str(self.tag_stack):
                self.code_body.append(data)
            return
        if self.skip:
            return
        self._emit(data)
        self._flush_inline()

    def _emit(self, text):
        """Route inline text to the open table cell, else to the inline buffer."""
        if self.in_table:
            self.current_cell.append(text)
        else:
            self.inline_buf.append(text)

    def _flush_inline(self):
        if self.inline_buf:
            self.md.append("".join(self.inline_buf))
            self.inline_buf = []

    def _flush_table(self):
        if not self.table_rows:
            return
        # Find header row
        header = None
        data_rows = []
        for is_hdr, row in self.table_rows:
            if is_hdr and header is None:
                header = row
            else:
                data_rows.append(row)
        if header is None and data_rows:
            header = data_rows.pop(0)
        if not header:
            return
        cols = len(header)
        self.md.append("\n| " + " | ".join(header) + " |\n")
        self.md.append("| " + " | ".join(["---"] * cols) + " |\n")
        for row in data_rows:
            padded = (row + [""] * cols)[:cols]
            self.md.append("| " + " | ".join(padded) + " |\n")
        self.md.append("\n")

    def get_markdown(self) -> str:
        self._flush_inline()
        text = "".join(self.md)
        # Clean up excessive newlines
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


def convert(input_text: str, output_path: str, title: str = ""):
    parser = ConfluenceToMd()
    parser.feed(input_text)
    md = parser.get_markdown()

    front_matter = "\n".join([
        "---",
        f'title: "{title or "Confluence Page"}"',
        f'date: "{date.today().isoformat()}"',
        'classification: "Unclassified"',
        'source: "confluence"',
        "---",
        "",
    ])
    Path(output_path).write_text(front_matter + md + "\n", encoding="utf-8")
    print(f"Created: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <input.html | -> output.md [--title 'Page Title']")
        sys.exit(1)
    inp = sys.argv[1]
    out = sys.argv[2]
    title = ""
    if "--title" in sys.argv:
        title = sys.argv[sys.argv.index("--title") + 1]
    if inp == "-":
        text = sys.stdin.read()
    else:
        text = Path(inp).read_text(encoding="utf-8")
    convert(text, out, title)
