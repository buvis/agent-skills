#!/usr/bin/env python3
"""Convert Word (.docx/.doc) to Markdown with YAML front matter.

Usage: python3 docx_to_md.py input.docx output.md
       python3 docx_to_md.py input.doc output.md  (requires libreoffice for .doc)
"""
import sys
import re
import subprocess
import tempfile
from pathlib import Path
from datetime import date

from docx import Document
from docx.oxml.ns import qn


def convert_doc_to_docx(doc_path: str) -> str:
    """Convert legacy .doc to .docx via LibreOffice."""
    tmp = tempfile.mkdtemp()
    subprocess.run(
        ["libreoffice", "--headless", "--convert-to", "docx", "--outdir", tmp, doc_path],
        check=True, capture_output=True,
    )
    return str(Path(tmp) / (Path(doc_path).stem + ".docx"))


def extract_tables(table) -> str:
    """Convert a docx table to markdown pipe table."""
    rows = []
    for row in table.rows:
        cells = [cell.text.strip().replace("|", "\\|") for cell in row.cells]
        rows.append(cells)
    if not rows:
        return ""
    col_count = len(rows[0])
    lines = ["| " + " | ".join(rows[0]) + " |"]
    lines.append("| " + " | ".join(["---"] * col_count) + " |")
    for row in rows[1:]:
        padded = row + [""] * (col_count - len(row))
        lines.append("| " + " | ".join(padded[:col_count]) + " |")
    return "\n".join(lines)


def para_to_md(para) -> str:
    """Convert a paragraph to markdown."""
    style = (para.style.name or "").lower()

    # Headings
    for level in range(1, 7):
        if style == f"heading {level}" or style == f"heading{level}":
            return f"{'#' * level} {para.text.strip()}"

    # List items
    numPr = para._element.find(qn("w:pPr"))
    if numPr is not None and numPr.find(qn("w:numPr")) is not None:
        return f"- {para.text.strip()}"
    if "list" in style:
        if "number" in style or "ordered" in style:
            return f"1. {para.text.strip()}"
        return f"- {para.text.strip()}"

    # Inline formatting
    parts = []
    for run in para.runs:
        text = run.text
        if not text:
            continue
        if run.bold and run.italic:
            text = f"***{text}***"
        elif run.bold:
            text = f"**{text}**"
        elif run.italic:
            text = f"*{text}*"
        if run.font.name and "consol" in run.font.name.lower():
            text = f"`{run.text}`"
        parts.append(text)

    return "".join(parts)


def convert(input_path: str, output_path: str):
    """Convert docx to markdown."""
    src = Path(input_path)
    if src.suffix.lower() == ".doc":
        input_path = convert_doc_to_docx(input_path)

    doc = Document(input_path)
    lines = []

    # Extract core properties for front matter
    props = doc.core_properties
    title = props.title or src.stem.replace("-", " ").replace("_", " ")
    author = props.author or ""
    created = props.created

    front_matter = [
        "---",
        f'title: "{title}"',
        f'date: "{created.strftime("%Y-%m-%d") if created else date.today().isoformat()}"',
        f'author: "{author}"',
        'classification: "Unclassified"',
        f'source_file: "{src.name}"',
        "---",
    ]
    lines.extend(front_matter)
    lines.append("")

    for element in doc.element.body:
        tag = element.tag.split("}")[-1]
        if tag == "p":
            from docx.text.paragraph import Paragraph
            para = Paragraph(element, doc)
            md = para_to_md(para)
            if md.strip():
                lines.append(md)
                lines.append("")
        elif tag == "tbl":
            from docx.table import Table
            tbl = Table(element, doc)
            lines.append(extract_tables(tbl))
            lines.append("")

    Path(output_path).write_text("\n".join(lines), encoding="utf-8")
    print(f"Created: {output_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} input.docx output.md")
        sys.exit(1)
    convert(sys.argv[1], sys.argv[2])
