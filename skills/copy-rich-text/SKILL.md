---
name: copy-rich-text
description: Use when content must be formatted, copied, or made ready to paste into Microsoft Teams, Outlook, or another rich-text app; copy it in the same turn. Triggers on "format for Teams", "Teams-ready", "copy to clipboard", "rich copy".
compatibility: macOS only. Needs python3 3.10+, textutil and pbcopy (built in). PyObjC (AppKit) is required for images and Teams-native code blocks; Pygments is required for syntax colors in fenced code. Without PyObjC it falls back to RTF-only. Harness-neutral.
---

# Copy Rich Text

Copy formatted content - with clickable hyperlinks, bold text, etc. - to the
macOS clipboard so it pastes correctly into Teams, Outlook, Confluence, or any
rich-text target.

Run the script as `python3 ~/.agents/skills/copy-rich-text/scripts/copy_rich.py`.

## Dependencies

- macOS with `textutil` and `pbcopy` (built in): hard failure elsewhere.
- Python 3.10+.
- PyObjC (`AppKit`, `Foundation`): needed for embedded images and Teams-native
  code blocks. Without it the script copies RTF only and exits with an error
  when the input needs the HTML path.
- Pygments: needed for syntax colors in fenced code with a language tag.
  Without it such input exits with an error instead of a degraded copy.
- `JIRA_BASE_URL` in the environment (for example
  `https://jira.example.com/browse`): enables Jira key auto-linking. Unset,
  keys stay plain text.

## When to use

Invoke this skill immediately when a rich-text destination is part of the
requested deliverable. The user does not need to say "clipboard."

**Mandatory triggers include:**

- "prepare a report for Teams"
- "in a form I can paste to Teams with formatting"
- "format this for Teams" or "make this Teams-ready"
- "copy this/report/message to the clipboard"
- "post/share/send this in Teams or Outlook"
- any request where the requested report, update, summary, release notes, Jira
  roundup, or message explicitly names Teams/Outlook as its destination

For those requests, generate the requested content, run the clipboard script,
and finish with the content already on the clipboard in the same turn. Do not
first return Markdown and wait for the user to ask again for copying.

**Proactive trigger:** the user is clearly preparing formatted content for an
external audience but has not named a destination. Present the content, then
offer one concise clipboard action.

**Do not trigger** for ordinary questions about Teams features, bugs, APIs, or
behavior when the user is not asking you to prepare content for pasting.

Signs the user will need rich clipboard:
- "for Teams", "for Outlook", "send to the team", "post this"
- Content has Jira keys, URLs, or structured formatting
- The user asked for a summary/changelog/status update (these almost always
  get pasted somewhere)

## The problem this solves

There is no good way to move formatted content from a terminal chat to a
rich-text app:

- **Markdown** renders as raw syntax in Teams/Outlook (`[PROJ-6837](https://...)`)
- **Plain text with URLs** auto-links but duplicates (`https://... (https://...)`)
- A plain clipboard write loses structure. The script writes raw HTML plus an
  RTF fallback so Teams can preserve links, lists, images, and native
  code-block metadata.

## Workflow

### 1. Compose the content

Build whatever the user asked for. This skill handles the last mile, not the
content creation.

### 2. Write natural Markdown - not HTML

The script accepts both Markdown and HTML. **Prefer Markdown** - the script
converts it:

- `**bold**`, `*italic*`, `~~strikethrough~~`, `` `inline code` ``
- `[text](url)` becomes clickable links
- `# Heading` / `## Heading` / `### Heading` become bold text at three distinct
  sizes, so hierarchy survives the paste. A visible gap always follows a
  heading, even with no blank line in the source.
- `- item` / `* item` becomes a bullet list; `1. item` becomes a numbered list.
  Lists can be **nested to arbitrary depth** by indenting with spaces; each
  deeper level alternates bullet style (`•` / `◦` / `▪`) or ordered style
  (`1.` / `a.` / `i.`), matching how Teams nests lists.
- Consecutive lines starting with a Jira key (e.g. `PROJ-1234 - description`)
  are automatically wrapped in a bullet list
- `` ```fenced code blocks``` `` become native Teams code blocks with syntax
  colors (see [references/teams-clipboard-notes.md](references/teams-clipboard-notes.md))
- `![alt](src)` embeds an image - `src` can be a local file path (read and
  base64-embedded) or a remote `http(s):`/`data:` URI (passed through as-is)
- `> text` becomes an indented/italicized blockquote
- `---` on its own line becomes a horizontal rule
- Pipe tables (`| a | b |` with a `|---|---|` separator row) become a real
  `<table>`. Teams handles pasted tables inconsistently; paste a small test first
  if the table matters.
- Blank lines become paragraph breaks; single newlines become `<br>`

**Jira keys are auto-linked when `JIRA_BASE_URL` is set.** Any bare
`PROJ-1234` pattern that is not already inside a link, `<pre>`, or `<code>`
gets wrapped in a link to `<JIRA_BASE_URL>/PROJ-1234`. Do not build these URLs
by hand. Without the variable, keys stay plain text.

**Format detection is by content, not file extension.** Content with HTML tags
is treated as HTML, otherwise as Markdown. Raw HTML works when Markdown is not
enough (`colspan`, mixed formatting); Jira keys are still auto-linked there.

### 3. Copy to clipboard

**Preferred: write a temp file, pass the path.** This avoids shell quoting
problems (apostrophes, HTML attributes):

1. Create `/tmp/clipboard.md` with the content, using the file-creation tool,
   not a shell heredoc
2. Run: `python3 ~/.agents/skills/copy-rich-text/scripts/copy_rich.py -f /tmp/clipboard.md`
3. Delete the temp file

Other modes, for simple content without quotes:

```bash
python3 ~/.agents/skills/copy-rich-text/scripts/copy_rich.py '<b>Hello</b>'
python3 ~/.agents/skills/copy-rich-text/scripts/copy_rich.py - < /tmp/clipboard.md
```

The script writes raw HTML (which Teams consumes) and an RTF fallback. If the
input contains images or fenced code and PyObjC or Pygments is missing, it exits
with a clear error instead of claiming a degraded copy succeeded.

### 4. Confirm

Tell the user: "On your clipboard - Cmd+V into Teams."

## Common patterns

### Changelog / release notes

```markdown
**Widget service v2.37.7**
Deployed to staging

PROJ-6837 - Fixed health check reporting a closed connection as open
PROJ-6818 - Export now includes archived records
```

### Status update with sections

```markdown
**Sprint Update**

**Completed**
- PROJ-6837 - health check improvements

**In Progress**
- PROJ-6900 - next feature
```

### Code snippet in a status update

Write a normal fenced block with a language tag. Always tag the language, so the
header and colors appear right after paste.

## Limitations

- macOS only
- Jira auto-linking needs `JIRA_BASE_URL` in the environment; unset, keys
  stay plain text.
- Markdown conversion is a useful subset, not full CommonMark. No table cell
  alignment or `colspan`.
- Teams controls the exact color theme and how it sanitizes pasted tables.
- Teams-specific behavior, code-block internals, and image handling:
  [references/teams-clipboard-notes.md](references/teams-clipboard-notes.md).

## Validating changes

Unit tests (standard library only):

```bash
python3 -m unittest discover -s ~/.agents/skills/copy-rich-text/scripts
```

`assets/test_payload.md` is an acceptance fixture that exercises every supported
Markdown feature. Section 10 embeds `/tmp/checker.png`; create any small PNG
there first. After changing `scripts/copy_rich.py`:

```bash
python3 ~/.agents/skills/copy-rich-text/scripts/copy_rich.py -f ~/.agents/skills/copy-rich-text/assets/test_payload.md
```

Paste the result into real Microsoft Teams and compare it to what the fixture
describes. Teams' paste sanitizer is the real test, not the generated HTML.
