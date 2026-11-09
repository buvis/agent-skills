# Teams clipboard notes

Findings behind `scripts/copy_rich.py`. Read this before changing how the script
writes HTML, RTF, code blocks, or images.

## Teams gotchas

- **Teams treats the HTML and RTF clipboard paths differently.** When both are
  present, Teams uses the raw HTML representation. That path preserves real
  `<s>`, `<code>`, `<blockquote>`, images, and Teams' code-block metadata.
- **A bare `<pre><code>` is not a native Teams code block.** It pastes as a
  line-numbered preformatted box without the stateful header or language
  control. A fenced block must use Teams' `CodeBlockEditor` item type,
  stateful header/body sibling structure, and the `data-teams="true"` clipboard
  marker. Do not fake code with a bordered table, Unicode lookalikes, font
  styling, or literal triple backticks on the plain-text clipboard.
- **Immediate colors need pre-tokenized code.** Teams skips its paste-time
  highlighter for the code block containing the caret. A no-op edit later
  triggers highlighting, but that is not acceptable clipboard behavior. The
  script uses Pygments to emit Teams-supported `hljs-*` spans and marks the
  block `corrected="true"` before it reaches the clipboard.
- **`<br>` line breaks collapse into one line in the RTF path.** The RTF
  converter turns `<br>` into soft line breaks that Teams collapses. Use
  `<ul><li>` for lists of items. The Markdown converter wraps consecutive Jira
  key lines automatically.
- **Pre-linked HTML must close each `<a>` before the description text.** The
  auto-linker does this correctly; hand-written HTML can get it wrong.
- **Plain HTML collapses runs of whitespace and ignores bare newlines.** Use a
  fenced code block when indentation matters.
- **Tables are inconsistent in Teams**, independent of this skill. Tables pasted
  from Word or another Teams message often flatten to plain text; tables copied
  from Excel fare best. The script emits a real `<table>`; paste a one-row test
  before sending a large one.
- **Teams' own compose box uses single-tilde `~text~` for strikethrough.** This
  only matters when typing directly into Teams. The script's Markdown input uses
  the common `~~text~~`.
- **A missing `<meta charset="utf-8">` causes mojibake.** `textutil` guesses the
  encoding and gets UTF-8 wrong. The script always wraps generated HTML in a full
  `<html><head><meta charset="utf-8">` document before calling `textutil`.

## Code blocks

Fenced Markdown blocks render using the Teams compose-editor clipboard contract
found in the installed Teams client:

```html
<span data-teams="true">
  <p>&nbsp;</p>
  <p itemtype="http://schema.skype.com/CodeBlockEditor"
     id="x_x_3ff3ce88c86346a7b3403331dfa75273">&nbsp;</p>
  <pre class="language-python skipProofing"
       itemid="codeBlockEditor-2762c894-5324-486f-849b-694589f621e5"
       corrected="true" spellcheck="false"><code><span
       class="hljs-keyword">def</span>&nbsp;<span
       class="hljs-function">probe</span>():<br>&nbsp;&nbsp;&nbsp;&nbsp;<span
       class="hljs-keyword">return</span>&nbsp;<span
       class="hljs-string">&quot;ok&quot;</span></code></pre>
  <p>&nbsp;</p>
</span>
```

- `data-teams="true"` marks Teams-origin clipboard HTML. One wrapper encloses
  the complete rendered message.
- `CodeBlockEditor` is the item type Teams uses for its stateful code-block
  header. The header and `<pre>` body are siblings, as in HTML copied directly
  from the Teams editor.
- `skipProofing`, `spellcheck="false"`, and `corrected="true"` match the native
  highlighted block.
- Pygments tokens map to Teams' accepted `hljs-keyword`, `hljs-comment`,
  `hljs-string`, and `hljs-function` classes. Other source text stays escaped
  but unwrapped, matching Teams' native copied HTML.
- Code is HTML-escaped. Spaces become `&nbsp;` and newlines become `<br>`, so
  indentation and line structure survive.
- Common fence aliases are normalized to Teams language classes (`c++` to `cpp`,
  `c#` to `csharp`, `js` to `javascript`, `py` to `python`). A fence without a
  language uses `language-plaintext`.

The raw HTML clipboard type is required. The RTF fallback cannot carry the
code-block contract. Pygments is required for language-bearing fences; the script
fails clearly when it is missing or has no lexer for the fence, rather than copy
a block that only gains colors after a no-op edit. A real paste into the current
Teams client is the acceptance test.

## Images

Embedding a real image (`![alt](src)`) in a Teams paste needs the **raw HTML
string** clipboard type (`NSPasteboardTypeHTML`), not RTF or RTFD. All three were
tested directly:

- `textutil -convert rtf` silently drops `<img>` data, whether the source is a
  `file://` path or a base64 `data:` URI (no `\pict`/`pngblip` in the output).
- RTFD built through AppKit embeds the image as an attachment, but Teams still
  drops it on paste.
- A raw HTML string on `NSPasteboardTypeHTML` with
  `<img src="data:image/png;base64,...">` is the only one that survives a real
  paste into Teams.

So the script writes both `NSPasteboardTypeHTML` (carries images) and
`NSPasteboardTypeRTF` (formatting fallback) when PyObjC is available. Without
PyObjC only the RTF path runs, and input with images or Teams code blocks fails
explicitly.
