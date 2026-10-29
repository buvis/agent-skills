---
name: publish-confluence-docs
description: Convert Word, PDF, Markdown, and Confluence documents, render Mermaid diagrams, and publish attachments. Use when publishing to Confluence, converting downloaded SharePoint documents, exporting pages to Word, or embedding diagrams.
compatibility: "Portable; needs Python 3.12+ with uv, Node 18.19+ or 20+ with npm for Mermaid (plus its Chromium prerequisites), curl for uploads, LibreOffice for legacy .doc, and caller-supplied Confluence access."
---

# Publish Confluence Docs

Bidirectional document conversion between downloaded SharePoint/Word files,
Markdown, and Confluence. Outputs use neutral document styling. Markdown is the
intermediate format. SharePoint retrieval requires a separately configured reader.

## Conversion Pipelines

```
SharePoint (.docx/.doc) → Markdown → Confluence (publish)
PDF (.pdf)              → Markdown → Confluence (publish) or Word (.docx)
Confluence (read page)  → Markdown → Word (.docx) with neutral styling
Markdown (author)       → Confluence (publish) or Word (.docx)
Markdown (mermaid)      → PNG (mmdc) → Confluence attachment → embedded in page
```

## Scripts

All scripts live in this skill's `scripts/` directory. Examples below run from
this skill's root. From another directory, use the resolved absolute skill path
for both `--project` and the script, not a hardcoded agent configuration directory.

| Script | Pipeline | Usage |
|--------|----------|-------|
| `docx_to_md.py` | Word → Markdown | `uv run --project . python scripts/docx_to_md.py input.docx output.md` |
| `pdf_to_md.py` | PDF → Markdown | `uv run --project . python scripts/pdf_to_md.py input.pdf output.md` |
| `md_to_confluence.py` | Markdown → Confluence XHTML | `uv run --project . python scripts/md_to_confluence.py input.md [--output file.html]` |
| `confluence_to_md.py` | Confluence → Markdown | `uv run --project . python scripts/confluence_to_md.py input.html output.md` |
| `md_to_docx.py` | Markdown → Word | `uv run --project . python scripts/md_to_docx.py input.md output.docx` |
| `mermaid_to_png.py` | Mermaid → PNG | `uv run --project . python scripts/mermaid_to_png.py input.md [--output-dir DIR]` |
| `confluence_attach.py` | Upload attachments | `uv run --project . python scripts/confluence_attach.py PAGE_ID file1.png [file2.png]` |
| `confluence_embed_images.py` | Embed images in page | `uv run --project . python scripts/confluence_embed_images.py PAGE_ID img1.png [--width 900]` |

## Dependencies

No other skill is required. Confluence page create/read/update needs a
caller-supplied provider or credentials; this skill ships none and only
converts documents and uploads attachments.

```bash
uv sync --project ~/.agents/skills/publish-confluence-docs --python 3.12
npm install --prefix ~/.agents/skills/publish-confluence-docs
```

The included `pyproject.toml` declares python-docx, PyMuPDF, and PyYAML.
The included `package.json` declares Mermaid CLI. Legacy `.doc` conversion also
needs LibreOffice (`soffice` on PATH). Mermaid needs a supported Node version and
its Chromium/browser prerequisites. Uploads need `curl`. Report a missing
dependency before starting its conversion; never report an uncreated output.

## Neutral document style

### Colors

| Usage | Hex |
|-------|-----|
| Primary (slate) | `#334155` |
| Body Text | `#333333` |
| Headings H1-H2 | `#334155` |
| Headings H3+ | `#333333` |
| Table Header BG | `#334155` |
| Table Header Text | `#FFFFFF` |
| Table Alt Row | `#F5F5F5` |
| Borders | `#CCCCCC` |
| Links | `#0060A9` |

### Typography

- **All text**: Arial font family
- **Document Title**: 24pt Bold, slate
- **H1**: 18pt Bold, slate
- **H2**: 14pt Bold, #333333
- **Body**: 11pt Regular, #333333
- **Code**: Consolas 10pt

### Document Classification

Classification is supplied in document metadata. The neutral fallback is
**Unclassified**, which does not grant permission to publish. Apply the target
organization's classification and publication policy before sharing.

## Confluence connection

There is no default instance or space. The attachment and image scripts require
`CONFLUENCE_BASE_URL` and `CONFLUENCE_TOKEN`; image embedding also requires
`CONFLUENCE_SPACE_KEY`. They use the `/rest/api/content` storage-format API with
bearer authentication, not Confluence Cloud v2. Verify server/auth compatibility
before enabling writes. Page creation, general page updates, and reads require
an independently configured page provider. Discover its actual tools and schemas.

## Agent Workflows

### Publish SharePoint doc to Confluence

1. Read the .docx from SharePoint path
2. Convert: `docx_to_md.py source.docx /tmp/draft.md`
3. Review/edit markdown if needed
4. Convert: `md_to_confluence.py /tmp/draft.md`
5. Use the configured page writer with the user-selected space and parent page

### Publish PDF to Confluence

1. Convert: `pdf_to_md.py source.pdf /tmp/draft.md`
2. Review/edit markdown
3. Convert: `md_to_confluence.py /tmp/draft.md`
4. Publish with the configured page writer after approval of the target and content

### Save Confluence page as Word

1. Read the page's storage-format HTML through the configured page reader
2. Convert: `confluence_to_md.py page.html /tmp/page.md`
3. Convert: `md_to_docx.py /tmp/page.md output.docx`

### Publish with Mermaid diagrams

1. Author markdown with ` ```mermaid ` blocks
2. Render: `mermaid_to_png.py draft.md --output-dir /tmp/diagrams/`
3. Convert: `md_to_confluence.py draft.md --output draft.html`
4. Create the page through the configured page writer
5. Upload PNGs: `confluence_attach.py PAGE_ID /tmp/diagrams/*.png`
6. Embed: `confluence_embed_images.py PAGE_ID diagram1.png diagram2.png`

### Markdown Front Matter Format

```yaml
---
title: "Document Title"
subtitle: "Optional Subtitle"
date: "2026-04-28"
author: "Author Name"
classification: "Unclassified"
version: "1.0"
jira_story: "PROJECT-123"
source: "sharepoint"  # or "confluence" or "new"
---
```

## Notes

- `md_to_confluence.py` without `--output` prints to stdout; pass that content using the page provider's supported request format
- `confluence_attach.py` auto-detects existing attachments and updates instead of failing on duplicates
- Tokens come only from `CONFLUENCE_TOKEN` or the explicit `--token` option; prefer the environment to avoid command-history exposure
- Check the configured provider's payload limit; never silently truncate content to fit
- Always render Mermaid to PNG via mmdc (not SVG→PNG) — mmdc uses `<foreignObject>` which only Chromium renders correctly
