#!/usr/bin/env python3
"""Convert PDF to Markdown with YAML front matter.

Usage: python3 pdf_to_md.py input.pdf output.md
"""
import sys
import re
from pathlib import Path
from datetime import date

import pymupdf  # PyMuPDF


def extract_metadata(doc: pymupdf.Document) -> dict:
    """Extract PDF metadata into front matter dict."""
    meta = doc.metadata or {}
    return {
        "title": meta.get("title", "").strip() or Path(sys.argv[1]).stem,
        "author": meta.get("author", "").strip() or "Unknown",
        "date": meta.get("creationDate", "")[:10] or str(date.today()),
        "classification": "Unclassified",
        "source": "pdf",
        "source_file": Path(sys.argv[1]).name,
    }


def build_front_matter(meta: dict) -> str:
    lines = ["---"]
    for k, v in meta.items():
        if v:
            lines.append(f'{k}: "{v}"')
    lines.append("---\n")
    return "\n".join(lines)


def extract_tables(page: pymupdf.Page) -> list[dict]:
    """Extract tables from a page, returning list of {bbox, markdown}."""
    tables = page.find_tables()
    results = []
    for table in tables:
        rows = table.extract()
        if not rows:
            continue
        # Build markdown table
        md_rows = []
        header = rows[0]
        md_rows.append("| " + " | ".join(c or "" for c in header) + " |")
        md_rows.append("| " + " | ".join("---" for _ in header) + " |")
        for row in rows[1:]:
            md_rows.append("| " + " | ".join(c or "" for c in row) + " |")
        results.append({"bbox": table.bbox, "markdown": "\n".join(md_rows)})
    return results


def spans_in_table(span_bbox, table_bboxes) -> bool:
    """Check if a text span falls inside any table bounding box."""
    x0, y0, x1, y1 = span_bbox
    for tb in table_bboxes:
        tx0, ty0, tx1, ty1 = tb
        if x0 >= tx0 - 2 and y0 >= ty0 - 2 and x1 <= tx1 + 2 and y1 <= ty1 + 2:
            return True
    return False


def classify_block(block_dict: dict) -> str:
    """Heuristic: detect heading vs body from font size and bold flag."""
    spans = []
    for line in block_dict.get("lines", []):
        spans.extend(line.get("spans", []))
    if not spans:
        return "body"
    max_size = max(s["size"] for s in spans)
    is_bold = any("bold" in s.get("font", "").lower() for s in spans)
    if max_size >= 18:
        return "h1"
    if max_size >= 14 and is_bold:
        return "h2"
    if max_size >= 12 and is_bold:
        return "h3"
    return "body"


def block_text(block_dict: dict) -> str:
    """Extract text from a block, preserving bold/italic spans."""
    parts = []
    for line in block_dict.get("lines", []):
        line_parts = []
        for span in line.get("spans", []):
            txt = span.get("text", "")
            if not txt.strip():
                line_parts.append(txt)
                continue
            font = span.get("font", "").lower()
            is_bold = "bold" in font
            is_italic = "italic" in font or "oblique" in font
            if is_bold and is_italic:
                txt = f"***{txt.strip()}***"
            elif is_bold:
                txt = f"**{txt.strip()}**"
            elif is_italic:
                txt = f"*{txt.strip()}*"
            line_parts.append(txt)
        parts.append("".join(line_parts))
    return " ".join(parts)


def convert_page(page: pymupdf.Page) -> str:
    """Convert a single PDF page to markdown."""
    output = []
    tables = extract_tables(page)
    table_bboxes = [t["bbox"] for t in tables]
    table_inserted = [False] * len(tables)

    blocks = page.get_text("dict", flags=pymupdf.TEXT_PRESERVE_WHITESPACE)["blocks"]

    for block in blocks:
        if block["type"] != 0:  # skip image blocks
            continue
        bbox = (block["bbox"][0], block["bbox"][1], block["bbox"][2], block["bbox"][3])
        if spans_in_table(bbox, table_bboxes):
            # Insert table markdown once when we first encounter its area
            for i, tb in enumerate(table_bboxes):
                if not table_inserted[i] and bbox[1] >= tb[1] - 2:
                    output.append("\n" + tables[i]["markdown"] + "\n")
                    table_inserted[i] = True
            continue

        text = block_text(block).strip()
        if not text:
            continue

        kind = classify_block(block)
        if kind == "h1":
            output.append(f"\n# {text}\n")
        elif kind == "h2":
            output.append(f"\n## {text}\n")
        elif kind == "h3":
            output.append(f"\n### {text}\n")
        else:
            # Detect bullet points
            if re.match(r"^[•●▪◦‣–-]\s", text):
                text = re.sub(r"^[•●▪◦‣–-]\s*", "", text)
                output.append(f"- {text}")
            elif re.match(r"^\d+[.)]\s", text):
                output.append(text)
            else:
                output.append(text)

    # Insert any remaining tables not yet placed
    for i, inserted in enumerate(table_inserted):
        if not inserted:
            output.append("\n" + tables[i]["markdown"] + "\n")

    return "\n".join(output)


def clean_markdown(text: str) -> str:
    """Post-process: collapse blank lines, fix spacing."""
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"(\*\*)\s+(\*\*)", r"\1\2", text)  # merge adjacent bold markers
    return text.strip() + "\n"


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 pdf_to_md.py input.pdf output.md", file=sys.stderr)
        sys.exit(1)

    pdf_path, md_path = sys.argv[1], sys.argv[2]
    doc = pymupdf.open(pdf_path)

    meta = extract_metadata(doc)
    pages_md = []
    for page in doc:
        pages_md.append(convert_page(page))

    content = build_front_matter(meta) + "\n" + clean_markdown("\n\n".join(pages_md))
    Path(md_path).write_text(content, encoding="utf-8")
    print(f"Converted {doc.page_count} pages → {md_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
