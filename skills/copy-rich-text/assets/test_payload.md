# Teams Rich-Text Paste - Full Acceptance Test

Paste this payload into a fresh Microsoft Teams compose box. Do not send or
edit it before checking the results. Every section states what should appear.

## 1. Heading hierarchy and spacing
### Level 3 heading
- This list starts immediately after a heading.
- There should still be a visible gap below the heading.

The title, section heading, and level 3 heading should use three visibly
different sizes.

## 2. Paragraphs, line breaks, and Unicode

This is line one.
This is line two after a single source newline.

This is a new paragraph after a blank source line.

Unicode must remain unchanged: café, naïve, Žluťoučký kůň, €42, ✓, and 🙂.

## 3. Inline formatting

**Bold text**, *italic text*, ~~struck text~~, and `inline code` should each
have distinct formatting.

Unformatted filenames must remain intact: copy_rich.py, staged_source_key,
and test_copy_rich.py.

## 4. Links and Jira keys

[This explicit link](https://example.com) should be clickable.

The bare key PROJ-6545 should become a clickable Jira link (when
`JIRA_BASE_URL` is set; otherwise it stays plain text).

[PROJ-6837](https://jira.example.com/browse/PROJ-6837) is already linked
and must not become a nested link.

The inline-code value `PROJ-9999` must remain code and must not become a
link.

These consecutive Jira-key lines should become a bullet list:

PROJ-6545 - first automatically linked item
PROJ-6837 - second automatically linked item

## 5. Unordered and ordered lists

- Unordered level 1
  - Unordered level 2
    - Unordered level 3
  - Back to level 2
* Alternate top-level bullet marker

1. Ordered level 1
   1. Ordered level 2
      1. Ordered level 3
   2. Second item at level 2
2) Second item at level 1 using a closing parenthesis

All nesting levels should remain nested rather than flattening into one list.

## 6. Quote, horizontal rule, and adjacent spacing

> This quoted note should appear italicized as the skill's quote treatment.
---
### Heading immediately after the rule

The quote, rule, and heading should remain distinct without a large blank gap.

## 7. Table

| Format | Expected result | Example |
| --- | --- | --- |
| Bold | Bold text in the cell | **working** |
| Inline code | Monospace code in the cell | `copy_rich.py` |
| Jira key | Clickable link in the cell | PROJ-6545 |

The table should retain three columns and visible cell boundaries.

## 8. Native Python code block with immediate syntax colors

The following must paste as a native Teams code block with a language header,
line numbers, preserved indentation, and syntax colors visible immediately:

```python
# Comment token
def format_message(name: str) -> str:
    if not name:
        return "missing"
    print(f"Hello, {name}")
    return name.upper()
```

## 9. Native plaintext code block

The following must paste as a native plaintext code block. Its spacing and
line breaks must survive, but it should not invent syntax colors or Jira links:

```text
PROJ-9999 must remain plain code, not a link.
copy_rich.py must retain both underscores.
    Four leading spaces must remain visible.
```

## 10. Embedded image

A red-and-blue checkerboard image should appear below, not a local path or a
broken-image marker:

![red and blue checkerboard](/tmp/checker.png)

Text after the image must remain visible and editable.

## 11. Final integrity check

If every section above looks correct, the HTML clipboard path preserved all
formatting currently supported by the skill.
