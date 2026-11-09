---
name: explain-bim-system
description: Use before any task that reads, searches, creates, or edits notes in the BIM Obsidian vault (~/bim or $BIM_VAULT), or when asked how the vault is organized. Covers layout, note anatomy, frontmatter, links, tags, GTD tasks, and agent rules.
compatibility: Harness-neutral reference, no tools required. Assumes the vault at ~/bim or at the path in the BIM_VAULT environment variable.
---

# BIM system reference

BIM (BUVIS InfoMesh) is a personal knowledge system kept as an Obsidian vault.
It blends GTD (David Allen), Zettelkasten (Niklas Luhmann), and PARA (Tiago
Forte). The vault documents itself in `notes/system/` (start at
`notes/system/index.md`). This file condenses what an agent needs and is the
shared source of truth for every BIM skill. Skills must work without Obsidian
running.

## Locate the vault

- Path: `$BIM_VAULT` if set, else `~/bim`. A valid vault has `notes/` and
  `notes/system/` at its root.

## Layout

| Path | Holds | Agent rules |
|------|-------|-------------|
| `inbox/` | Raw material waiting to be processed. Any filename, rarely frontmatter. Obsidian and automations put new files here. | Read freely. Processing turns an item into notes, then moves the item to `.trash/`. |
| `notes/` | Processed notes, the core of the system | See below. |
| `notes/calendar/` | Time-scoped notes: `daily/YYYY-MM-DD.md`, `weekly/YYYY-Www.md` (monthly, quarterly, and yearly folders are linked but empty) | Obsidian creates these. Do not create them. Append to a daily `## Log` only when asked, except that `create-note` adds a log line linking each note it creates. |
| `notes/system/` | System docs (ID-named notes), `templates/` (Templater `.tpl`), `scripts/` (Templater user scripts, CustomJS classes) | Read-only unless asked. Templates define note shapes. |
| `resources/<category>/` | Assets: `book-cover/`, `contact-picture/`, `notes-attachments/` (Obsidian's attachment folder), `screenshots/`, `icon/`, `media-lib/` (Media Extended plugin), and topic folders | Put new assets in the matching category and link them from a note. Leave `media-lib/` alone. |
| `.obsidian/` | App and plugin config | Never edit. |
| `.trash/` | Obsidian's local trash | Move files here instead of deleting them. |

PARA reference material lives outside the vault:
`~/Documents/reference/{10-projects,20-areas,30-resources,40-archives}`. Each
project note links its support folder
`~/Documents/reference/10-projects/<id>-<slug>/`. Notes never go there; they go
to `notes/`. Archived articles (original text) live in
`~/Documents/reference/40-archives/articles/YYYY/YYYYMM00/<original title>.md`;
their core-facts note is a zettel that links the archive file.

## Notes layout

- `notes/<id>.md`: almost every note. `id` is the creation time
  `YYYYMMDDHHmmss` in local time. It is unique and never changes.
- `notes/contact/<slug>.md`: people and companies, named by slug so links are
  easy to type.
- `notes/book/<slug>.md`: books, named by slug for the same reason.
- `notes/kanban/`: Kanban plugin boards. The plugin owns the format.
- `notes/documents/`: zettels for documents, such as device manuals.
- `notes/<id>.svg`: Excalidraw export next to its illustrated note.

`slug` comes from the title: NFKD-normalize, drop combining marks, trim,
lowercase, keep only `a-z 0-9 space -`, turn whitespace runs into `-`, collapse
repeated `-`. Example: `Zoë Ångström-Müller` becomes `zoe-angstrom-muller`.

## Note anatomy

```markdown
---
id: 20260105093012
title: Sourdough starter care
date: 2026-01-05T09:30:12+01:00
tags: [cooking, bread]
type: note
publish: false
processed: false
---

# Sourdough starter care

Body in Markdown.

---

- parent:: [[notes/20251220181544|§ Baking]]
- web:: [Starter basics](https://example.com/starter)
```

- Frontmatter order: `id`, `title`, `date`, `tags`, `type`, `publish`,
  `processed`, then type-specific keys. Older notes vary; do not reorder them.
- `title`: quoted when it contains a colon or other YAML-special characters.
  The H1 repeats it verbatim (problem resolution reports prefix `PRR: `). The
  Front Matter Title plugin shows `title` instead of the filename and adds it
  as an alias, so no `aliases` key is needed.
- `date`: creation time, ISO 8601 with UTC offset, same instant as `id`.
- `tags`: flow list without `#`. Tags are lowercase, may nest with `/`
  (`lang/rust`), and may hold non-ASCII letters.
- `publish: false` always.
- `processed: false` at creation. The owner flips it to `true` after review.
  The daily note offers a random unprocessed note.
- Everything after the last `---` is "backmatter": Dataview inline fields
  `key:: value`, usually as list items, so references stay queryable. Common
  keys: `parent` (link to the parent note or project), `web`, `teams`, `ticket`,
  `us`, `psd`, `pr`, `shop`, `repo`, `reading-notes`. Work projects add keys of
  their own; keep every key you do not recognize when you rewrite a note.
- For Microsoft Teams URLs, use `teams::` rather than `web::` in backmatter.
- Index (MOC) notes have a title starting with `§`.

## Note types

`type` drives Dataview queries. Templates in `notes/system/templates/` exist for:

| `type` | Template | File |
|--------|----------|------|
| `note` | `page.convert-to-generic-note.tpl` | `notes/<id>.md` |
| `note` for an article | `page.convert-to-generic-note.tpl` | `notes/<id>.md` with the core facts; the original text lives in the archive (see above), linked by `article::` |
| `note` with `origin: youtube` | `page.convert-to-notes-on-youtube-video.tpl` | `notes/<id>.md` |
| `illustrated-note` | `page.convert-to-illustrated-note.tpl` | `notes/<id>.md` + `<id>.svg` |
| `meeting-minutes` | `page.convert-to-meeting-minutes.tpl` | `notes/<id>.md` |
| `problem-resolution-report` | `page.convert-to-problem-resolution-report.tpl` | `notes/<id>.md` |
| `project` | `page.create-project.tpl` | `notes/<id>.md` + project support folder |
| `book` | `page.convert-to-book.tpl` | `notes/book/<slug>.md` |
| `contact` | `page.convert-to-contact-person.tpl` | `notes/contact/<slug>.md` |

Other types reuse the generic note shape with a different `type`: `list`,
`procedure`, `definition`, `wiki-article`, `cheatsheet`, `course`, `recipe`,
`snippet`, and more. Check what exists before inventing one:
`rg -NIo '^type: .*' ~/bim/notes | sort | uniq -c | sort -rn`.

Title habits: procedures start with an imperative verb ("Rotate API keys
for the build server"), definitions use the bare term ("Idempotency").

Type-specific frontmatter:

- `project`: `completed` (bool), `resources` (`"[project resources](file:///...)"`
  with the absolute path URL-encoded as one segment), `deliverable` (`fix`,
  `enhancement`, or `support`).
- `meeting-minutes`: `location` (`webex`, `teams`, `phone`, `face to face`),
  `start` and `end` (`HH:mm`), `organizer`, `attendees` (list), `summary`.
- `contact`: `contact-type` (one or more of `person`, `colleague`, `author`,
  `schoolmate`, `friend`, `family`, `business`, comma-separated), `summary`,
  `company`, `job-title`, `email`; rarely `birthday`, `location`,
  `timezone-difference`, `socials`.
- `book`: `summary`, `last-read` (`9999-12-31` means unread), `author`.
- YouTube note: `summary`, `origin: youtube`, `author`, `source` (watch URL).
- `course`: `provider`, `length`, `status`.

## Links

- Internal links are wiki links with the vault-absolute path and the title as
  alias: `[[notes/20251220181544|§ Baking]]`,
  `[[notes/contact/jane-doe|Jane]]`.
- External links are Markdown links: `[Title](https://example.com)`.
- Embeds: `![[note#Heading]]` for a section, `![alt|240](path.jpeg)` for a
  sized image.

## Tags and GTD tasks

- Reuse existing note tags. List them with
  `rg -NIo '^tags: \[.*\]' ~/bim/notes | sed 's/^tags: //' | tr -d '[]' | tr ',' '\n' | sed 's/^ *//' | sort | uniq -c | sort -rn`.
  About 120 older notes use a block list (`tags:` then `- tag`) instead.
- Tasks follow the Tasks plugin: `- [ ] text 📅 YYYY-MM-DD` (due), `⏳`
  (scheduled), `🛫` (start); priority `⏬ 🔽 🔼 ⏫ 🔺`.
- GTD list tags on tasks: `#gtd/act/now`, `#gtd/act/next`, `#gtd/act/later`,
  `#gtd/act/someday`, `#gtd/wait`. The Checklist plugin groups open tasks by
  tag into these lists.
- `#gtd/inbox` marks a note whose checkboxes still need processing (daily
  notes carry it). `#gtd/ignore` keeps checkboxes that are not actions out of
  the GTD lists.
- Project log entry: `- [ ] YYYY-MM-DD HH:mm - what happened => next action | #gtd/act/now 📅 YYYY-MM-DD`.
- Daily log entry (QuickAdd capture): `- [ ] _DD.MM.YYYY HH:mm:ss_ - entry`
  under `## Log` in `notes/calendar/daily/YYYY-MM-DD.md`.

## Plugins that act on files

- Templater runs `.tpl` templates only inside Obsidian. Skills port them.
- Auto Note Mover moves notes tagged `#person` to `notes/contact/` and
  `#book` to `notes/book/`. Do not use those tags on other notes.
- Linter formats on save: strips trailing spaces, sets blank lines around
  headings and rules, drops empty list markers. Write output that already
  passes.
- Dataview, Tasks, and Checklist read `type`, `processed`, `status`, and task
  tags. Keep those fields accurate.
- Excalidraw owns the drawing section of illustrated notes.

## Rules for agents

1. Create notes only through the `create-note` skill, so IDs and shapes stay
   in line with the templates.
2. Never overwrite, rename, or move an existing note. IDs and slugs are link
   targets.
3. To delete, move the file to `.trash/`, keeping its name. On a clash, add a
   space and a number, as Obsidian does (`Untitled 1.md`, `Untitled 2.md`).
4. Do not edit `.obsidian/`, `notes/system/templates/`, `notes/system/scripts/`,
   Kanban board structure, or Excalidraw JSON unless asked.
5. Write UTF-8 with LF line endings and one trailing newline.
6. The vault is private. Do not copy note content into shared repos, tickets,
   or third-party services unless asked.

## Keep this reference current

Sources: `notes/system/20240618170045.md` (organization),
`notes/system/20240619195131.md` (change log), `notes/system/templates/`, and
`.obsidian/plugins/*/data.json`. When vault conventions change, update this
file and every skill that ports a template (for `create-note`, its
`assets/templates/`).
