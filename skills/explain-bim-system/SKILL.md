---
name: explain-bim-system
description: Use before any task that reads, searches, creates, or edits notes in the BIM Obsidian vault, or when asked how the vault is organized. Covers vault layout, backmatter, links, GTD tasks, plugins, and agent rules; `bim --skill` covers the CLI.
compatibility: Harness-neutral reference. Assumes the bim CLI from buvis-gems and the vault whose notes/ folder is the bim path_zettelkasten setting (default ~/bim/notes/).
---

# BIM system reference

BIM (BUVIS InfoMesh) is a personal knowledge system kept as an Obsidian vault.
It blends GTD (David Allen), Zettelkasten (Niklas Luhmann), and PARA (Tiago
Forte). The vault documents itself in `notes/system/` (start at
`notes/system/index.md`). Skills must work without Obsidian running.

Two sources split the work:

- `bim --skill` prints bim's own skill. It is the authority for the bim CLI
  (search with `bim query`, read, create, edit metadata, archive) and for the
  shape each bundled template writes: frontmatter keys, file placement, slugs,
  ids. Run it before you use bim.
- This file covers the vault conventions bim does not know: layout, links,
  backmatter, GTD tasks, the Obsidian plugins, and the rules for agents.

## Locate the vault

bim's `path_zettelkasten` setting (default `~/bim/notes/`) is the vault's
`notes/` folder; the vault root is its parent. A valid vault has `notes/` and
`notes/system/` at its root.

## Layout

| Path | Holds | Agent rules |
|------|-------|-------------|
| `inbox/` | Raw material waiting to be processed. Any filename, rarely frontmatter. Obsidian and automations put new files here. | Read freely. Processing turns an item into notes, then moves the item to `.trash/`. |
| `notes/` | Processed notes, the core of the system | See below. |
| `notes/calendar/` | Time-scoped notes: `daily/YYYY-MM-DD.md`, `weekly/YYYY-Www.md` (monthly, quarterly, and yearly folders are linked but empty) | Obsidian creates these. Do not create them. Append to a daily `## Log` only when asked, except that `bim create` adds a log line linking each note it creates. |
| `notes/system/` | System docs (ID-named notes), `templates/` (Templater `.tpl`), `scripts/` (Templater user scripts, CustomJS classes) | Read-only unless asked. Templates define note shapes. |
| `resources/<category>/` | Assets: `book-cover/`, `contact-picture/`, `notes-attachments/` (Obsidian's attachment folder), `screenshots/`, `icon/`, `media-lib/` (Media Extended plugin), and topic folders | Put new assets in the matching category and link them from a note. Leave `media-lib/` alone. |
| `.obsidian/` | App and plugin config | Never edit. |
| `.trash/` | Obsidian's local trash | Move files here instead of deleting them. |

PARA reference material lives outside the vault:
`~/Documents/reference/{10-projects,20-areas,30-resources,40-archives}`. Each
project note links its support folder in `10-projects/`, and each article note
links its archived original in `40-archives/articles/`. Notes never go there;
they go to `notes/`.

## Notes layout

- `notes/<id>.md`: almost every note. `id` is the creation time
  `YYYYMMDDHHmmss` in local time. It is unique and never changes.
- `notes/contact/<slug>.md` and `notes/book/<slug>.md`: people and books,
  named by slug so links are easy to type.
- `notes/kanban/`: Kanban plugin boards. The plugin owns the format.
- `notes/documents/`: zettels for documents, such as device manuals.
- `notes/<id>.svg`: Excalidraw export next to its illustrated note.

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

- Older notes vary in frontmatter key order; do not reorder them.
- The H1 repeats `title` (older problem resolution reports prefix `PRR: `).
  The Front Matter Title plugin shows `title` instead of the filename and adds
  it as an alias, so no `aliases` key is needed.
- `publish: false` always.
- `processed: false` at creation. The owner flips it to `true` after review.
  The daily note offers a random unprocessed note.
- Everything after the last `---` is "backmatter": Dataview inline fields
  `key:: value`, usually as list items, so references stay queryable. Common
  keys: `parent` (link to the parent note or project), `web`, `teams`, `ticket`,
  `us`, `psd`, `pr`, `shop`, `repo`, `reading-notes`, `article`. Work projects
  add keys of their own; keep every key you do not recognize when you rewrite
  a note.
- For Microsoft Teams URLs, use `teams::` rather than `web::` in backmatter.
- Index (MOC) notes have a title starting with `§`.

## Note types

`type` drives Dataview queries. `bim create -l` lists the templates that
write each type. The vault uses `note` (also for YouTube notes, marked
`origin: youtube`, and article notes), `illustrated-note`, `meeting-minutes`,
`problem-resolution-report`, `project`, `book`, and `contact`. Other types
reuse the note shape: `list`, `procedure`, `definition`, `wiki-article`,
`cheatsheet`, `course`, `recipe`, `snippet`, and more. Check what exists
before inventing one:
`rg -NIo '^type: .*' ~/bim/notes | sort | uniq -c | sort -rn`.

Title habits: procedures start with an imperative verb ("Rotate API keys
for the build server"), definitions use the bare term ("Idempotency").

Type-specific frontmatter:

- `project`: `completed` (bool), `resources` (a `file://` link to the support
  folder), `deliverable` (`fix`, `enhancement`, or `support`).
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

- Templater runs `.tpl` templates only inside Obsidian. `bim create`
  reproduces them outside it.
- Auto Note Mover moves notes tagged `#person` to `notes/contact/` and
  `#book` to `notes/book/`. Do not use those tags on other notes.
- Linter formats on save: strips trailing spaces, sets blank lines around
  headings and rules, drops empty list markers. Write output that already
  passes.
- Dataview, Tasks, and Checklist read `type`, `processed`, `status`, and task
  tags. Keep those fields accurate.
- Excalidraw owns the drawing section of illustrated notes.

## Rules for agents

1. Create notes only through the `create-note` skill (it runs `bim create`),
   so IDs and shapes stay in line with the templates.
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
file; when a template changes, update the matching bundled template in
`bim create` (buvis-gems).
