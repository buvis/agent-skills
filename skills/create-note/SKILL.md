---
name: create-note
description: Use when creating BIM notes from Teams messages, articles, videos, meetings, ideas, or inbox items, or adding projects, books, or contacts. Triggers on "take note", "note this", "create a note", "add a zettel", "make meeting minutes".
compatibility: Requires python3 3.10+ (standard library only) and the BIM vault at ~/bim or BIM_VAULT. Harness-neutral.
---

# Create a BIM note

Creates one note in `notes/` with `scripts/create_note.py`. The script
fills a template in `assets/templates/` (ported from the vault's Templater
templates), allocates a unique id, never overwrites a file, and prints a JSON
report.

## Dependencies

- `explain-bim-system` (this repository): read
  `~/.agents/skills/explain-bim-system/SKILL.md` first for vault layout, note
  anatomy, links, tags, and writing rules. If it is missing, stop; do not
  invent conventions.
- Python 3.10+ (standard library only) and a BIM vault at `$BIM_VAULT` or
  `~/bim`. If either is missing, stop and name what is needed.
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

## Pick the kind

| Request | Kind | File | Required options |
|---------|------|------|------------------|
| Plain note, idea, summary, list, procedure, definition, cheatsheet, recipe, ... | `note` | `notes/<id>.md` | `--title`; `--type` when not `note` |
| Diagram or sketch | `illustrated` | `notes/<id>.md` | `--title` |
| Meeting notes | `meeting` | `notes/<id>.md` | `--title`, `--location webex\|teams\|phone\|"face to face"` |
| Notes on a YouTube video | `youtube` | `notes/<id>.md` | `--title`, `--video URL-or-id` |
| Article: published prose to read and keep (news post, blog post, announcement, newsletter, internal comms page) | `article` | archive file `~/Documents/reference/40-archives/articles/YYYY/YYYYMM00/<title>.md` (original) + `notes/<id>.md` (core facts) | `--title`, `--summary-file`, original text via `--body-file` or `--source` |
| Problem investigation, incident, bug analysis | `prr` | `notes/<id>.md` | `--title` |
| Project or loop file | `project` | `notes/<id>.md` + resources folder | `--title`, `--deliverable fix\|enhancement\|support` |
| Book | `book` | `notes/book/<slug>.md` | `--title` |
| Person | `contact` | `notes/contact/<slug>.md` | `--title` (full name) |

## Detect articles

Use `article` without being told when the pasted or inbox text is a finished
piece written for readers: a headline, narrative paragraphs under headings,
an author voice ("we are transitioning", "what you need to do"), call-to-action
sections, often a source URL (`web::` line) or boilerplate such as links, "key
takeaways", "why we are making this change". Meeting notes, task lists, your
own scribbles, and reference material (procedures, definitions) are not
articles. When unsure, ask.

An article is archive content, not a zettel. It always makes a pair:

- the original text, kept whole, goes to the archive at
  `~/Documents/reference/40-archives/articles/YYYY/YYYYMM00/<title>.md`
  (year and month of today, `00` for the day; the file name is the original
  title, not slugified, with only `/ \ :` replaced by `-`);
- a `note` zettel holds only the core facts, with the surrounding noise
  removed (marketing framing, greetings, repeated links, "why we are doing
  this" filler, calls to subscribe). Keep facts, decisions, dates, owners,
  names, how-to steps, and the links they need. Use short headings or bullets.
  Its backmatter links the archive copy (`article::`, a `file://` link) and
  the source (`web::`).

Write the original and the core facts to temporary files (for example in the
session folder), leave out the H1 in both (the script writes it from the
title), and run:

```sh
python3 ~/.agents/skills/create-note/scripts/create_note.py article --title "<title>" \
  --tags a,b --web "<source URL>" \
  --body-file original.md --summary-file facts.md
```

- `--title` is the article's own title with its original casing; it names the
  archive file and the note. Add no prefix.
- Keep the original verbatim. Fix only clipboard accidents (stray words inside
  a URL) and say so. Do not drop duplicate links or boilerplate from it.
- The script never overwrites an archive file, writes the archive first, and
  removes it if the note cannot be written. `--archive-root` overrides the
  articles folder; the script fails if `~/Documents/reference/40-archives` is
  missing.
- Inbox file: pass `--source inbox/<file>.md` instead of `--body-file`.
- The report has `archive.path` and `note` (with `wikilink`); give both to the
  user.

Calendar notes (daily, weekly) are out of scope. Tell the user to create them
in Obsidian.

## Gather inputs

Infer from the request and context; ask only for what you cannot infer.

- `--title`: a short, specific title. Procedures start with a verb;
  definitions are the bare term. The script capitalizes the first letter
  (every word for contacts).
  - Meeting: give only the subject. The script builds
    `YYYY-MM-DD | <Subject> meeting minutes`, so do not add the date or
    "meeting minutes" yourself. A trailing "meeting minutes" (in the title or
    the inbox file name) is dropped rather than doubled.
  - Book: the title as printed on the cover.
- `--tags`: reuse existing tags (see the command in the reference). `person`
  and `book` belong only to contacts and books and are added automatically.
- `--type` (note only): reuse an existing type. The script rejects types that
  have their own kind.
- `--deliverable` (project): `fix` for broken things, `enhancement` for new
  or better things, `support` for everything else. Ask if unclear.
- `--ticket` (project, optional): the service request or ticket id.
- YouTube title and author: fetch
  `https://www.youtube.com/oembed?url=<video URL>&format=json` and use
  `title` and `author_name`.

## Run the script

```sh
python3 ~/.agents/skills/create-note/scripts/create_note.py <kind> --title "..." [options]
```

Shared options:

- `--tags a,b`: comma-separated, `#` optional.
- `--fields JSON` (not for `article`): frontmatter values. Keys in the template are replaced in
  place, new keys are appended. Strings, numbers, booleans, `null` (empty
  value), and lists (block list) are allowed. `id`, `title`, `date`, `tags`,
  and `type` are reserved. Examples:
  - meeting: `'{"start": "09:00", "end": "10:00", "organizer": "Ada Lovelace", "attendees": ["Ada Lovelace", "Alan Turing"], "summary": "..."}'`
  - contact: `'{"contact-type": "colleague", "company": "Example Corp", "job-title": "...", "email": "..."}'`
  - book: `'{"author": "...", "summary": "..."}'`
  - YouTube: `'{"author": "<author_name>", "summary": "<one sentence>"}'`
- `--body-file PATH` or `--body-file -` (stdin): Markdown placed where the
  template expects content (see below). It is kept verbatim.
- `--source inbox/<file>.md`: convert an inbox file. A relative path is
  taken from the vault root, so it works from any working folder. Its text
  becomes the body (a leading frontmatter block is dropped and reported), its
  name is the default title, and the file moves to `.trash/` after the note
  is written.
- `--dry-run`: print the note in the report without writing anything.
- `--no-link-contacts`: keep the body verbatim. Pass it for exact copies,
  where the text must stay unchanged. Without it, the first mention of each
  person in `notes/contact/` becomes `[[notes/contact/<slug>|name as written]]`.
  Matching uses the contact's `title` and multi-word `aliases`, ignores case and
  diacritics, and also reads "Last, First" (Teams sender order). One-word names
  (first names, nicknames) and names shared by two contacts are never linked.
  Code, existing links, and URLs are skipped. In article mode only the core
  facts are linked, never the archived original. The report lists
  `linked_contacts`; check them. When the source gives a sender whose contact
  match looks likely but was not linked (for example "Novakova, Ada (Acme)"
  matches, but "Ada" alone does not), write the full name in the body so it
  links.
- `--no-daily-log`: skip the daily-note log entry. By default the script adds
  `- [ ] _DD.MM.YYYY HH:mm:ss_ - <wikilink>` as the last line under `## Log` in
  `notes/calendar/daily/YYYY-MM-DD.md` for today, so the note is easy to
  find later. It never creates the daily note (Obsidian does) and never touches
  one without a `## Log` section. The report has `daily_log` with the status
  and the entry. A missing daily note is reported as `skipped`, not an error.
- `--vault PATH`: overrides `$BIM_VAULT` and `~/bim`.

Where the body goes: generic and illustrated notes after the H1 (and drawing
link); meeting under `## Log`; YouTube under `## Notes`; PRR after the
"Gather information" paragraph; project after `## Solution`; book after the
cover; contact after the photo.

The report (JSON on stdout) holds `path`, `relative_path`, `id`, `title`,
`wikilink`, and when relevant `resources_folder`, `trashed_source`,
`stripped_frontmatter`, `linked_contacts`, `daily_log`, `errors`. Exit code 1
means failure and nothing was written unless the report has `errors`; read
stderr. If the report has `errors`, the note was written but a follow-up step
(resources folder, daily-note log entry, or trashing the source) failed; tell
the user. Several notes can be created in parallel; runs take a lock on
`notes/`, so each gets its own id.

## After creating

1. Tell the user the `relative_path` and the `wikilink`.
2. Mention `linked_contacts` and the `daily_log` status in one short line.
3. To add content later, edit the created file. Replace the template's
   guidance text instead of leaving both, keep the frontmatter key order,
   and keep the backmatter fields after the closing `---`. Teams, web, and
   other backmatter fields for a plain `note` are added this way, because only
   the `article` kind writes backmatter itself.
4. To link the new note from another note, paste the `wikilink`.
5. For a project, report the `resources_folder` status. `skipped` means
   `~/Documents/reference/10-projects` does not exist on this machine; the
   link is written anyway.

## Do not

- Write notes by hand or copy a template yourself; run the script.
- Retry with a different title to dodge an "already exists" error for a
  contact or book. Open the existing note and tell the user.
- Convert files from outside `inbox/`; the script refuses.
- Create calendar notes. The script only appends to an existing daily note's
  log.

## Differences from the Obsidian templates

The port matches what the Templater templates produce after the vault's
Linter runs (trailing spaces and empty `- [ ]` placeholders removed, single
blank lines around the content slot), with these deliberate changes:

- Book and contact titles keep the casing you give. The templates lowercase
  everything first, which breaks names like "McDonald" or "iPhone". Books get
  only the first letter capitalized; contacts every word.
- Illustrated note image alt text uses the plain title, not the quoted one.
- YAML values are quoted whenever YAML would misread them (colon, leading
  `-` or `#`, `true`, numbers, dates, quotes), not only on a colon.
- Project resources live under `~/Documents/reference/10-projects`, expanded
  at run time. The `resources:` link must be an absolute `file:///` URL
  (neither file URLs nor Obsidian expand `~`). To link elsewhere, pass
  `--fields '{"resources": "[project resources](file:///...)"}'`.
- Project slug uses the same NFKD slug as books and contacts instead of
  `notes/system/scripts/templater/slugify.js`. Differences: `/ _ , : ; ·` between
  letters are removed instead of turned into `-` (`TCP/IP` gives `tcpip`, not
  `tcp-ip`); accented letters slugify.js does not list survive (`Šňůra` gives
  `snura`, not `ura`); `ł` is dropped instead of mapped to `l`.
- Convert mode drops the old frontmatter for every kind (the vault only does
  that for projects) and only takes files from `inbox/`.

## Maintain

The `article` kind has no vault template: the note reuses `generic-note.md` and the
script adds the `article::`/`web::` backmatter. The archive root is `ARTICLES_ROOT`.

Templates were ported from the vault on 2026-10-22:

| Vault template (`notes/system/templates/`) | Asset (`assets/templates/`) |
|--------------------------------------|-----------------------------|
| `page.convert-to-generic-note.tpl` | `generic-note.md` |
| `page.convert-to-illustrated-note.tpl` | `illustrated-note.md` |
| `page.convert-to-meeting-minutes.tpl` | `meeting-minutes.md` |
| `page.convert-to-notes-on-youtube-video.tpl` | `notes-on-youtube-video.md` |
| `page.convert-to-problem-resolution-report.tpl` | `problem-resolution-report.md` |
| `page.create-project.tpl` | `project.md` (projects root in `PROJECTS_ROOT`) |
| `page.convert-to-book.tpl` | `book.md` |
| `page.convert-to-contact-person.tpl` | `contact-person.md` |

Assets use `${name}` placeholders (Python `string.Template`); `${body}` marks
where content goes. When a vault template changes, update its asset, then run
the tests:

```sh
python3 -m unittest discover -s ~/.agents/skills/create-note/scripts -v
```
