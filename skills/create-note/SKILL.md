---
name: create-note
description: Use when creating BIM notes from Teams messages, articles, videos, meetings, ideas, or inbox items, or adding projects, books, or contacts. Triggers on "take note", "note this", "create a note", "add a zettel", "make meeting minutes".
compatibility: Requires the bim CLI from buvis-gems, the first release after 0.19.2 (bim create --json), and the BIM vault at the bim path_zettelkasten setting. Harness-neutral.
---

# Create a BIM note

Decides what to note and how, then creates one note with `bim create`. bim
fills a template that reproduces the vault's Templater notes, assigns the id,
never overwrites a file, and prints a JSON report.

## Dependencies

- `bim` from buvis-gems, the first release after 0.19.2. Check that
  `bim create --help` lists `--json` and `--summary-file`. If bim is missing
  or older, stop and tell the user to upgrade buvis-gems. Do not write the
  note by hand.
- `bim --skill` prints bim's own skill. It is the authority for flags, JSON
  keys, and template answers, and its "The BIM vault" section covers vault
  layout, note anatomy, links, tags, and writing rules. Read it before the
  first create in a session. If it has no "The BIM vault" section, stop; do
  not invent conventions.
- The vault: bim writes to the `path_zettelkasten` setting (default
  `~/bim/notes/`). `path_daily`, `path_projects`, and `path_articles` are
  settings too. Set them in `~/.config/buvis/buvis-bim.yaml`, as
  `BUVIS_BIM_PATH_<NAME>` environment variables, or with `bim --config FILE`.
- Source access: use an available authorized connector or local archive. A
  missing one blocks only that source, not the skill.

## "Take note" means create a BIM note

When the user says "take note of this", "note this", or similar, create a BIM
note with this skill in the same turn. Never reply with only a summary or an
offer to save. Pasted content, a session file, or a URL given with the phrase is
the source; keep any URL in backmatter. The phrase settles that a note is wanted
and defaults to extraction. Use an exact copy only if the user asks for one.
Articles still follow the article workflow below.

## Choose copy or extraction

For published articles, always use the settled article workflow below: archive
the full original and create a separate extracted-knowledge note. Do not ask the
user to choose between those two outputs.

For other referenced text, determine the intended mode from the user's prompt
and explicit instructions already given in the conversation:

- **Exact copy requested:** preserve the complete source text and all links
  verbatim in the note, and pass `--no-link-contacts` so no name is rewritten.
  Do not summarize, omit repetition, or rewrite its wording.
- **Information extraction requested:** write a knowledge note using the rules
  below, without copying the full source.
- **Unclear:** use the available user-input tool to ask whether the user wants
  an exact copy or extracted knowledge, then wait before writing. "Create a BIM
  note from this message/link" alone does not settle the choice.

Ask only when the mode is unclear; do not ask again after the user has specified
it. Both modes retain any source URL in backmatter: use `teams::` for Microsoft
Teams URLs, not `web::`. Use `web::` for ordinary web sources.

## Extract knowledge

In extraction mode, add useful information to the knowledge base rather than
preserving a message archive or transcript:

- Write a self-contained note about the subject, not a recap of the conversation.
- Keep useful facts, reasoning, decisions, prerequisites, steps, and reference
  links. Drop greetings, repetition, conversational filler, and chat formatting.
- Preserve uncertainty: a suggestion is not an agreed decision, and a proposed
  name or access item is not confirmed configuration.
- Choose a subject-based title. Reuse existing tags and link a relevant existing
  note with `parent::` when one exists. Use the source's backmatter field:
  `teams::` for Teams URLs, `web::` for ordinary web URLs. Name the people the
  source involves (sender, owners) by their full name in the text so they link to
  their contact note.
- Do not embed the full message, transcript, screenshot, or attachment.
  The published-article workflow below separately archives its original;
  its zettel still contains only extracted knowledge. Chats and email discussions
  do not become articles merely because they contain headings or links.
- Respect restrictions that apply to the extracted information; paraphrasing
  does not remove confidentiality.

Before writing, check that each claim is supported, tentative details stay
tentative, useful links survive, and the note is not a source dump.
Pass the prepared knowledge text through `--body-file`; `--source` copies the
inbox text rather than extracting knowledge from it.

## Resolve message links

Check existing authorized local sources before requesting a fresh sign-in or
asking the user to paste text. Parse identifiers with code, not by guessing.

For a Teams URL shaped as `/l/message/<conversation>/<message>`, URL-decode the
path identifiers. Use the message ID from the path, not `parentMessageId`, which
can identify a different message when the link points to a reply.

If a local message archive is available, match the conversation and message
identifiers from the URL and read only the matched message and any context
needed for the note. Distinguish a missing cached message from an access
failure; do not infer either from a failed sign-in. Keep the original Teams URL
in `teams::` backmatter.

## Pick the template

| Request | Template (`-t`) | File | Required |
|---------|-----------------|------|----------|
| Plain note, idea, summary | `note` | `notes/<id>.md` | `--title` |
| Definition, how-to, list, procedure, quote, recipe, snippet, cheatsheet, course, wiki article | `definition`, `how-to`, `list`, `procedure`, `quote`, `recipe`, `snippet`, `cheatsheet`, `course`, `wiki-article` | `notes/<id>.md` | `--title` |
| Diagram or sketch | `illustrated-note` | `notes/<id>.md` | `--title` |
| Meeting notes | `meeting-minutes` | `notes/<id>.md` | `--title` (subject only), `-a location=webex\|teams\|phone\|"face to face"` |
| Notes on a YouTube video | `youtube` | `notes/<id>.md` | `--title`, `-a video=<URL or id>` |
| Article: published prose to read and keep (news post, blog post, announcement, newsletter, internal comms page) | `article` | archive `<path_articles>/YYYY/YYYYMM00/<title>.md` (original) + `notes/<id>.md` (core facts) | `--title`, `--summary-file`, original via `--body-file` or `--source` |
| Problem investigation, incident, bug analysis | `problem-resolution-report` | `notes/<id>.md` | `--title` |
| Project or loop file | `project` | `notes/<id>.md` + resources folder | `--title`, `-a deliverable=fix\|enhancement\|support` |
| Book | `book` | `notes/book/<slug>.md` | `--title` |
| Person | `contact` | `notes/contact/<slug>.md` | `--title` (full name) |

`bim create -l` lists every template, including user templates. For a `type`
that has no template, create a `note` and then run
`bim edit PATH --type <type>`.

## Detect articles

Use `article` without being told when the pasted or inbox text is a finished
piece written for readers: a headline, narrative paragraphs under headings,
an author voice ("we are transitioning", "what you need to do"), call-to-action
sections, often a source URL (`web::` line) or boilerplate such as links, "key
takeaways", "why we are making this change". Meeting notes, task lists, your
own scribbles, and reference material (procedures, definitions) are not
articles. When unsure, ask.

An article is archive content, not a zettel. `bim create -t article` always
makes a pair:

- the original text, kept whole, goes to the archive at
  `<path_articles>/YYYY/YYYYMM00/<title>.md` (default root
  `~/Documents/reference/40-archives/articles/`; year and month of today, `00`
  for the day; the file name is the original title, not slugified, with only
  `/ \ :` replaced by `-`);
- a `note` zettel holds only the core facts, with the surrounding noise
  removed (marketing framing, greetings, repeated links, "why we are doing
  this" filler, calls to subscribe). Keep facts, decisions, dates, owners,
  names, how-to steps, and the links they need. Use short headings or bullets.
  Its backmatter links the archive copy (`article::`, a `file://` link) and
  the source (`web::`).

Write the original and the core facts to temporary files (for example in the
session folder), leave out the H1 in both (bim writes it from the title), and
run:

```sh
bim create -t article --title "<title>" --tags a,b -a web="<source URL>" \
  --body-file original.md --summary-file facts.md --json
```

- `--title` is the article's own title with its original casing; it names the
  archive file and the note. Add no prefix.
- Keep the original verbatim. Fix only clipboard accidents (stray words inside
  a URL) and say so. Do not drop duplicate links or boilerplate from it.
- bim never overwrites an archive file, writes the archive first, and removes
  it if the note cannot be written. It fails if the parent of `path_articles`
  is missing.
- Inbox file: pass `--source <vault>/inbox/<file>.md` instead of `--body-file`.
- Give the user the report's `archive.path` and `wikilink`.

Calendar notes (daily, weekly) are out of scope. Tell the user to create them
in Obsidian.

## Gather inputs

Infer from the request and context; ask only for what you cannot infer.

- `--title`: a short, specific title. Procedures start with a verb;
  definitions are the bare term. bim capitalizes the first letter (every word
  for contacts).
  - Meeting: give only the subject. bim builds
    `YYYY-MM-DD | <Subject> meeting minutes`, so do not add the date or
    "meeting minutes" yourself.
  - Book: the title as printed on the cover.
- `--tags`: reuse existing tags (`rg -NIo '^tags: \[.*\]' ~/bim/notes` lists
  them).
  `person` and `book` belong only to contacts and books; bim adds them and
  rejects them on other templates.
- `-a deliverable=` (project): `fix` for broken things, `enhancement` for new
  or better things, `support` for everything else. Ask if unclear.
- `-a ticket=` (project, optional): the service request or ticket id.
- `-a organizer=` (meeting, optional); `-a company=`, `-a job-title=`,
  `-a email=` (contact, optional).
- YouTube title and author: fetch
  `https://www.youtube.com/oembed?url=<video URL>&format=json` and use
  `title` and `author_name`.

## Run bim create

```sh
bim create -t <template> --title "..." [--tags a,b] [-a key=value ...] \
  [--body-file FILE | --source <vault>/inbox/FILE.md] --json
```

See `bim --skill` for every flag. The ones this skill relies on:

- `--json`: always pass it. Never run `bim create` without `-t` and either
  `--title` or `--source`; a bare call opens a TUI and hangs.
- `--body-file FILE` or `--body-file -` (stdin): Markdown placed in the
  template's body section, kept verbatim.
- `--source <vault>/inbox/FILE.md`: convert an inbox file, given as an
  ordinary path. Its frontmatter is dropped, its name is the default title,
  and it moves to `.trash/` after the note is written. Never combine it with
  `--body-file`.
- `--no-link-contacts`: keep the body verbatim. Pass it for exact copies.
  Without it, bim links the first mention of each person in
  `notes/contact/`. When the source names a sender whose contact was not
  linked (for example "Ada" alone), write the full name in the body so it
  links.
- `--no-daily-log`: keep the note out of today's daily log.
- `--dry-run`: print the rendered note in `content` and write nothing. Hooks
  do not run, so a project shows no `resources` link.
- `-a key=value` answers template questions only. Other frontmatter (meeting
  `start`, `end`, `attendees`, `summary`; contact `contact-type`; book
  `author`, `summary`; YouTube `author`, `summary`) is set after creation
  with `bim edit PATH -s key=value`.

The report is one JSON object: `id`, `type`, `title`, `tags`, `path`,
`relative_path`, `wikilink`, and when relevant `daily_log`,
`linked_contacts`, `archive.path`, `trashed_source`, `warnings`, `errors`.
On failure bim prints `{"error": "..."}`, exits 1, and writes nothing. If the
report has `errors`, the note exists but a follow-up step failed; tell the
user.

## After creating

1. Tell the user the `relative_path` and the `wikilink`.
2. Mention `linked_contacts` and the `daily_log` status in one short line.
3. To add content later, edit the created file. Replace the template's
   guidance text instead of leaving both, keep the frontmatter key order,
   and keep the backmatter fields after the closing `---`. Add `teams::` and
   `web::` backmatter this way; only `article` writes `web::` itself.
4. To link the new note from another note, paste the `wikilink`.
5. For a project, report any `warnings` entry. It means the `path_projects`
   root does not exist on this machine; the `resources` link is written
   anyway.

## Do not

- Write notes by hand or copy a template yourself; run `bim create`.
- Retry with a different title to dodge an "already exists" error for a
  contact or book. Open the existing note and tell the user.
- Convert files from outside `inbox/`; bim refuses.
- Create calendar notes. bim only appends to an existing daily note's log.

## Differences from the Obsidian templates

bim reproduces the Templater notes with these deliberate changes:

- Book and contact titles keep the casing you give. The templates lowercase
  everything first, which breaks names like "McDonald" or "iPhone". Contacts
  get every word capitalized; other notes only the first letter.
- Slugs for the project resources folder follow bim's NFKD rule (the one
  the contact and book templates use), not
  `notes/system/scripts/templater/slugify.js`: `/ _ , : ; ·` between letters
  are removed instead of turned into `-` (`TCP/IP` gives `tcpip`), accented
  letters slugify.js does not list survive (`Šňůra` gives `snura`, not
  `ura`), and `ł` is dropped instead of mapped to `l`.
- A title whose slug would be empty (no Latin letters or digits) fails
  instead of writing `.md`.
- The project `resources` link is a plain `file://` URL.
- The problem resolution report heading is `# <title>`, not
  `# PRR: <title>`, because bim keeps the H1 equal to the title.
- `--source` drops the old frontmatter for every template (the vault only
  does that for projects) and takes files only from `inbox/`.
