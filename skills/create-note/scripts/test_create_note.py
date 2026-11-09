"""Tests for create_note.py. Run from the skill folder: python3 -m unittest discover -s scripts -v

Input provenance: values marked "captured" come from real notes or system docs in the
BIM vault; everything else is invented for the test. Captured cases keep the real shape,
but their note titles, note IDs, and video IDs are invented, so no private note is quoted.
"""
from __future__ import annotations

import contextlib
import errno
import io
import json
import os
import re
import sys
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
import create_note  # noqa: E402

CET = timezone(timedelta(hours=1))
CLOCK = datetime(2026, 1, 5, 9, 30, 12, tzinfo=CET)


class VaultTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.vault = Path(self._tmp.name).resolve() / "bim"
        for folder in ("notes/contact", "notes/book", "notes/system", "inbox"):
            (self.vault / folder).mkdir(parents=True)
        patcher = mock.patch.object(create_note, "current_time", return_value=CLOCK)
        self.clock = patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(self._tmp.cleanup)

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = create_note.main([argv[0], "--vault", str(self.vault), *argv[1:]])
        report = json.loads(out.getvalue()) if out.getvalue() else None
        return code, report, err.getvalue()

    def create(self, *argv):
        code, report, err = self.run_cli(*argv)
        self.assertEqual(code, 0, err)
        return report, Path(report["path"]).read_text(encoding="utf-8")


class GenericNoteTests(VaultTestCase):
    def test_generic_note_has_template_shape(self):
        report, text = self.create("note", "--title", "sourdough starter care", "--tags", "#Cooking, bread")
        self.assertEqual(report["relative_path"], "notes/20260105093012.md")
        self.assertEqual(report["wikilink"], "[[notes/20260105093012|Sourdough starter care]]")
        self.assertEqual(
            text,
            "---\nid: 20260105093012\ntitle: Sourdough starter care\ndate: 2026-01-05T09:30:12+01:00\n"
            "tags: [cooking, bread]\ntype: note\npublish: false\nprocessed: false\n---\n\n"
            "# Sourdough starter care\n\n---\n",
        )

    def test_body_lands_between_heading_and_rule(self):
        body = Path(self._tmp.name) / "body.md"
        body.write_text("\n\nFeed it daily.  \n\n- flour\n- water\n\n\n", encoding="utf-8")
        _, text = self.create("note", "--title", "Starter", "--body-file", str(body))
        self.assertTrue(text.endswith("# Starter\n\nFeed it daily.  \n\n- flour\n- water\n\n---\n"))

    def test_title_with_colon_or_quote_is_quoted_in_yaml_only(self):
        _, text = self.create("note", "--title", 'Rust: the "borrow" checker')
        self.assertIn('title: "Rust: the \\"borrow\\" checker"\n', text)
        self.assertIn('\n# Rust: the "borrow" checker\n', text)

    def test_type_override_and_rejection_of_templated_types(self):
        _, text = self.create("note", "--title", "Rotate API keys", "--type", "procedure")
        self.assertIn("\ntype: procedure\n", text)
        code, _, err = self.run_cli("note", "--title", "X", "--type", "project")
        self.assertEqual(code, 1)
        self.assertIn("has its own template", err)

    def test_tags_reserved_for_auto_note_mover_are_rejected_elsewhere(self):
        code, _, err = self.run_cli("note", "--title", "X", "--tags", "person")
        self.assertEqual(code, 1)
        self.assertIn("reserved for the contact kind", err)

    def test_nested_and_non_ascii_tags_are_allowed(self):
        _, text = self.create("note", "--title", "X", "--tags", "lang/rust,příklad")  # captured tag shapes
        self.assertIn("tags: [lang/rust, příklad]\n", text)

    def test_invalid_tag_is_rejected(self):
        code, _, err = self.run_cli("note", "--title", "X", "--tags", "two words")
        self.assertEqual(code, 1)
        self.assertIn("invalid tag", err)

    def test_dry_run_writes_nothing(self):
        code, report, _ = self.run_cli("note", "--title", "X", "--dry-run")
        self.assertEqual(code, 0)
        self.assertTrue(report["dry_run"])
        self.assertIn("# X\n", report["content"])
        self.assertFalse(Path(report["path"]).exists())


class IdAllocationTests(VaultTestCase):
    def test_windows_lock_is_released_after_a_failed_write(self):
        lock = mock.Mock(LK_LOCK=1, LK_UNLCK=0)
        with mock.patch.dict(sys.modules, {"msvcrt": lock}), mock.patch.object(sys, "platform", "win32"):
            with self.assertRaisesRegex(ValueError, "write failed"):
                with create_note.vault_lock(self.vault / "notes"):
                    raise ValueError("write failed")
        fd = lock.locking.call_args_list[0].args[0]
        self.assertEqual(lock.locking.call_args_list, [mock.call(fd, 1, 1), mock.call(fd, 0, 1)])
        with self.assertRaises(OSError):
            os.fstat(fd)

    def test_windows_lock_failure_never_enters_the_write(self):
        lock = mock.Mock(LK_LOCK=1, LK_UNLCK=0)
        lock.locking.side_effect = OSError("lock unavailable")
        with mock.patch.dict(sys.modules, {"msvcrt": lock}), mock.patch.object(sys, "platform", "win32"):
            with self.assertRaisesRegex(OSError, "lock unavailable"):
                with create_note.vault_lock(self.vault / "notes"):
                    self.fail("must not write without the lock")
        lock.locking.assert_called_once()
        with self.assertRaises(OSError):
            os.fstat(lock.locking.call_args.args[0])

    def test_taken_second_moves_id_to_next_free_second(self):
        (self.vault / "notes/contact/someone.md").write_text("---\nid: 20260105093012\n---\n", encoding="utf-8")
        (self.vault / "notes/20260105093013.md").write_text("no frontmatter\n", encoding="utf-8")
        self.clock.side_effect = [CLOCK, CLOCK + timedelta(seconds=1), CLOCK + timedelta(seconds=2)]
        with mock.patch.object(create_note.time, "sleep") as sleep:
            report, text = self.create("note", "--title", "X")
        self.assertEqual(report["id"], "20260105093014")
        self.assertIn("date: 2026-01-05T09:30:14+01:00\n", text)
        self.assertEqual(sleep.call_count, 2)

    def test_parallel_runs_never_share_an_id(self):
        # Agents run tool calls in parallel; two runs must not both claim the same free second.
        scan = create_note.used_ids

        def slow_scan(zettelkasten):
            ids = scan(zettelkasten)
            threading.Event().wait(0.2)  # widen the gap between scanning and writing
            return ids

        self.clock.side_effect = [CLOCK, CLOCK, CLOCK + timedelta(seconds=1)]
        reports, failures = [], []

        def run(name):
            args = create_note.build_parser().parse_args(["contact", "--vault", str(self.vault), "--title", name])
            try:
                reports.append(create_note.create(args))
            except Exception as exc:
                failures.append(exc)

        threads = [threading.Thread(target=run, args=(name,)) for name in ("Ada Lovelace", "Alan Turing")]
        with mock.patch.object(create_note, "used_ids", side_effect=slow_scan), mock.patch.object(create_note.time, "sleep"):
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(10)
        self.assertEqual(failures, [])
        self.assertEqual(sorted(report["id"] for report in reports), ["20260105093012", "20260105093013"])

    def test_gives_up_when_clock_never_reaches_a_free_second(self):
        (self.vault / "notes/20260105093012.md").write_text("x\n", encoding="utf-8")
        with mock.patch.object(create_note.time, "sleep"):
            code, _, err = self.run_cli("note", "--title", "X")
        self.assertEqual(code, 1)
        self.assertIn("no free id", err)


class ArticleTests(VaultTestCase):
    def setUp(self):
        super().setUp()
        self.archive = self.vault.parent / "archives" / "articles"
        self.archive.parent.mkdir()
        (self.vault / "orig.md").write_text("Original text.\n\n## Part\n\nMore.\n", encoding="utf-8")
        (self.vault / "facts.md").write_text("- Fact one\n- Fact two\n", encoding="utf-8")

    def article(self, *extra, title="Cloud Move: Phase 1/2"):
        return self.run_cli(
            "article", "--title", title, "--tags", "acme", "--archive-root", str(self.archive),
            "--body-file", str(self.vault / "orig.md"), "--summary-file", str(self.vault / "facts.md"), *extra,
        )

    def test_original_goes_to_time_tree_under_its_unslugified_title(self):
        code, report, err = self.article("--web", "https://example.com/a?x=1&y=2")
        self.assertEqual(code, 0, err)
        expected = self.archive / "2026" / "20260100" / "Cloud Move- Phase 1-2.md"
        self.assertEqual(report["archive"]["path"], str(expected))
        self.assertEqual(
            expected.read_text(encoding="utf-8"),
            "# Cloud Move: Phase 1/2\n\nOriginal text.\n\n## Part\n\nMore.\n\n---\n\nSource: https://example.com/a?x=1&y=2\n",
        )
        self.assertEqual(list((self.vault / "notes").glob("*.md")), [Path(report["note"]["path"])])

    def test_note_holds_core_facts_and_links_the_archive_copy(self):
        code, report, err = self.article("--web", "https://example.com/a")
        self.assertEqual(code, 0, err)
        note = Path(report["note"]["path"]).read_text(encoding="utf-8")
        self.assertIn("type: note\n", note)
        self.assertIn("# Cloud Move: Phase 1/2\n\n- Fact one\n- Fact two\n", note)
        self.assertNotIn("Original text", note)
        link = (self.archive / "2026" / "20260100" / "Cloud Move- Phase 1-2.md").as_uri()
        self.assertTrue(note.endswith(f"\n---\n\n- article:: [Cloud Move: Phase 1/2]({link})\n- web:: [Cloud Move: Phase 1/2](https://example.com/a)\n"))

    def test_existing_archive_file_is_never_overwritten_and_no_note_is_written(self):
        existing = self.archive / "2026" / "20260100" / "Cloud Move- Phase 1-2.md"
        existing.parent.mkdir(parents=True)
        existing.write_text("keep\n", encoding="utf-8")
        code, _, err = self.article()
        self.assertEqual(code, 1)
        self.assertIn("already exists", err)
        self.assertEqual(existing.read_text(encoding="utf-8"), "keep\n")
        self.assertEqual(list((self.vault / "notes").glob("*.md")), [])

    def test_empty_summary_is_rejected_and_nothing_is_written(self):
        (self.vault / "facts.md").write_text("\n", encoding="utf-8")
        code, _, err = self.article()
        self.assertEqual(code, 1)
        self.assertIn("--summary-file is empty", err)
        self.assertFalse(self.archive.exists())

    def test_missing_archive_parent_is_rejected(self):
        code, _, err = self.run_cli(
            "article", "--title", "X", "--archive-root", str(self.vault.parent / "nope" / "articles"),
            "--body-file", str(self.vault / "orig.md"), "--summary-file", str(self.vault / "facts.md"))
        self.assertEqual(code, 1)
        self.assertIn("does not exist", err)

    def test_failed_note_write_removes_the_archive_copy(self):
        real = create_note.write_new
        calls = []

        def flaky(path, data):
            calls.append(path)
            if len(calls) == 2:
                raise OSError(errno.ENOSPC, "disk full")
            real(path, data)

        with mock.patch.object(create_note, "write_new", side_effect=flaky):
            code, _, err = self.article()
        self.assertEqual(code, 1)
        self.assertIn("disk full", err)
        self.assertEqual(list(self.archive.rglob("*.md")), [])
        self.assertEqual(list((self.vault / "notes").glob("*.md")), [])

    def test_inbox_source_is_trashed_and_names_the_archive_file(self):
        (self.vault / "inbox/Cloud move.md").write_text("---\nfoo: bar\n---\nOriginal.\n", encoding="utf-8")
        code, report, err = self.run_cli(
            "article", "--source", "inbox/Cloud move.md", "--archive-root", str(self.archive),
            "--summary-file", str(self.vault / "facts.md"))
        self.assertEqual(code, 0, err)
        self.assertTrue((self.vault / ".trash/Cloud move.md").exists())
        self.assertTrue((self.archive / "2026" / "20260100" / "Cloud move.md").exists())


class VaultAndSourceTests(VaultTestCase):
    def test_directory_without_vault_folders_is_rejected(self):
        code, _, err = self.run_cli("note", "--title", "X", "--vault", self._tmp.name)
        self.assertEqual(code, 1)
        self.assertIn("is not a BIM vault", err)

    def test_convert_inbox_file_strips_frontmatter_and_trashes_source(self):
        (self.vault / ".trash").mkdir()
        (self.vault / ".trash/meeting idea.md").write_text("older\n", encoding="utf-8")
        source = self.vault / "inbox/meeting idea.md"
        source.write_text("---\nfoo: bar\n---\n\nTalk about **budget**.\n", encoding="utf-8")
        report, text = self.create("note", "--source", str(source))
        self.assertEqual(report["title"], "Meeting idea")
        self.assertTrue(report["stripped_frontmatter"])
        self.assertIn("# Meeting idea\n\nTalk about **budget**.\n\n---\n", text)
        self.assertNotIn("foo: bar", text)
        self.assertFalse(source.exists())
        self.assertEqual(report["trashed_source"], str(self.vault / ".trash/meeting idea 1.md"))

    def test_relative_source_is_resolved_against_the_vault(self):
        source = self.vault / "inbox/idea.md"
        source.write_text("Body.\n", encoding="utf-8")
        self.assertNotEqual(Path.cwd().resolve(), self.vault)
        report, text = self.create("note", "--source", "inbox/idea.md")
        self.assertEqual(report["title"], "Idea")
        self.assertIn("# Idea\n\nBody.\n", text)
        self.assertFalse(source.exists())

    def test_source_that_is_not_utf8_is_reported_and_kept(self):
        source = self.vault / "inbox/caf.md"
        source.write_bytes("café\n".encode("latin-1"))
        code, _, err = self.run_cli("note", "--source", str(source))
        self.assertEqual(code, 1)
        self.assertIn("utf-8", err)
        self.assertTrue(source.exists())

    def test_title_that_cannot_be_utf8_leaves_no_file(self):
        # Python decodes invalid argv bytes (here Latin-1 "café") to lone surrogates.
        code, _, err = self.run_cli("note", "--title", "caf\udce9")
        self.assertEqual(code, 1)
        self.assertIn("utf-8", err)
        self.assertEqual(list((self.vault / "notes").glob("*.md")), [])

    def test_failed_write_removes_the_partial_note(self):
        class FullDisk:
            def __init__(self, handle):
                self.handle = handle

            def __enter__(self):
                return self

            def __exit__(self, *exc):
                self.handle.close()

            def write(self, data):
                raise OSError(errno.ENOSPC, "No space left on device")

        with mock.patch.object(create_note, "open", create=True, side_effect=lambda p, m, **kw: FullDisk(open(p, m, **kw))):
            code, _, err = self.run_cli("note", "--title", "X")
        self.assertEqual(code, 1)
        self.assertIn("No space left", err)
        self.assertEqual(list((self.vault / "notes").glob("*.md")), [])

    def test_source_outside_inbox_is_rejected(self):
        note = self.vault / "notes/20250101000000.md"
        note.write_text("keep me\n", encoding="utf-8")
        code, _, err = self.run_cli("note", "--source", str(note))
        self.assertEqual(code, 1)
        self.assertIn("inside", err)
        self.assertTrue(note.exists())


class ContactAndBookTests(VaultTestCase):
    def test_contact_slug_drops_diacritics_and_title_keeps_inner_capitals(self):
        report, text = self.create("contact", "--title", "zoë ångström-Müller mcDonald")
        self.assertEqual(report["relative_path"], "notes/contact/zoe-angstrom-muller-mcdonald.md")
        self.assertIn("title: Zoë Ångström-Müller McDonald\n", text)
        self.assertIn("tags: [person]\ntype: contact\n", text)
        self.assertIn("![Zoë Ångström-Müller McDonald photo|180](zoe-angstrom-muller-mcdonald.jpeg)", text)

    def test_existing_contact_is_never_overwritten(self):
        target = self.vault / "notes/contact/ada-lovelace.md"
        target.write_text("original\n", encoding="utf-8")
        code, _, err = self.run_cli("contact", "--title", "Ada Lovelace")
        self.assertEqual(code, 1)
        self.assertIn("already exists", err)
        self.assertEqual(target.read_text(encoding="utf-8"), "original\n")

    def test_book_uses_shared_resources_cover_and_dataview_shop_field(self):
        report, text = self.create("book", "--title", "Clean code: a handbook", "--tags", "programming",
                                   "--fields", '{"author": "Robert C. Martin"}')
        self.assertEqual(report["relative_path"], "notes/book/clean-code-a-handbook.md")
        self.assertIn('title: "Clean code: a handbook"\n', text)
        self.assertIn("tags: [book, programming]\n", text)
        self.assertIn("author: Robert C. Martin\n---\n", text)
        self.assertIn("](resources/book-cover/clean-code-a-handbook.cover.jpeg)", text)
        self.assertTrue(text.endswith("## Synthesis\n\n---\n\n- shop::\n"))

    def test_title_without_latin_letters_is_rejected_for_slug_kinds(self):
        code, _, err = self.run_cli("contact", "--title", "李雷")
        self.assertEqual(code, 1)
        self.assertIn("empty slug", err)


class YoutubeTests(VaultTestCase):
    def test_video_id_from_captured_url_formats(self):
        cases = {  # URL formats captured from the vault's YouTube workflow note; video IDs invented
            "https://www.youtube.com/live/aBcDeFgHiJk?feature=shared": "aBcDeFgHiJk",
            "https://youtu.be/Ab3_dE-fG9h": "Ab3_dE-fG9h",
            "https://www.youtube.com/watch?v=Zx7Qw1Lm0Pq": "Zx7Qw1Lm0Pq",
            "Zx7Qw1Lm0Pq": "Zx7Qw1Lm0Pq",
            "https://www.youtube.com/shorts/Ab3_dE-fG9h": "Ab3_dE-fG9h",
        }
        for url, expected in cases.items():
            with self.subTest(url=url):
                self.assertEqual(create_note.youtube_id(url), expected)

    def test_urls_without_a_video_are_rejected(self):
        for url in ("https://www.youtube.com/playlist?list=PLaBcDeFgHiJkLmNoPqRsTuVwXyZ012345",
                    "https://example.com/watch?v=Zx7Qw1Lm0Pq", "not a video"):
            with self.subTest(url=url), self.assertRaises(create_note.CreateNoteError):
                create_note.youtube_id(url)

    def test_youtube_note_embeds_video_and_puts_body_under_notes(self):
        body = Path(self._tmp.name) / "b.md"
        body.write_text("- rule 1\n", encoding="utf-8")
        _, text = self.create("youtube", "--title", "Intro to unit testing", "--video", "https://youtu.be/Zx7Qw1Lm0Pq",
                              "--body-file", str(body))
        self.assertIn("source: https://www.youtube.com/watch?v=Zx7Qw1Lm0Pq\n", text)
        self.assertIn('src="https://www.youtube-nocookie.com/embed/Zx7Qw1Lm0Pq"', text)
        self.assertTrue(text.endswith("## Notes\n\n- rule 1\n\n---\n"))


class MeetingTests(VaultTestCase):
    def test_meeting_title_location_and_body_under_log(self):
        body = Path(self._tmp.name) / "b.md"
        body.write_text("- decided X\n", encoding="utf-8")
        report, text = self.create("meeting", "--title", "weekly sync", "--location", "face to face",
                                   "--body-file", str(body))
        self.assertEqual(report["title"], "2026-01-05 | Weekly sync meeting minutes")
        self.assertIn("title: 2026-01-05 | Weekly sync meeting minutes\n", text)
        self.assertIn("location: face to face\n", text)
        self.assertIn("## Log\n\n- decided X\n\n## Post-processing\n", text)
        # captured: the vault Linter leaves the GTD headings with no empty checkboxes
        self.assertIn("#gtd/act/now\n\n#gtd/act/next\n\n#gtd/wait\n\n#gtd/act/someday\n\n---\n", text)

    def test_meeting_title_does_not_repeat_meeting_minutes_suffix(self):
        # captured: an inbox file name already ending in "Meeting Minutes" got the suffix twice
        report, _ = self.create("meeting", "--title", "Quarterly planning Meeting Minutes",
                                "--location", "face to face")
        self.assertEqual(report["title"], "2026-01-05 | Quarterly planning meeting minutes")

    def test_meeting_title_without_subject_is_rejected(self):
        code, _, err = self.run_cli("meeting", "--title", "Meeting minutes", "--location", "teams")
        self.assertEqual(code, 1)
        self.assertIn("needs a subject", err)
        self.assertEqual(list((self.vault / "notes").glob("*.md")), [])

    def test_unknown_location_is_rejected(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            create_note.main(["meeting", "--vault", str(self.vault), "--title", "X", "--location", "zoom"])

    def test_fields_replace_template_keys_in_place_and_append_new_ones(self):
        fields = {"start": "09:00", "attendees": ["Ada Lovelace", "Alan Turing"], "organizer": None, "room": "B2"}
        _, text = self.create("meeting", "--title", "X", "--location", "teams", "--fields", json.dumps(fields))
        self.assertIn(
            'start: "09:00"\nend: hh:mm\norganizer:\nattendees:\n  - Ada Lovelace\n  - Alan Turing\n'
            'summary: ""\nroom: B2\n---\n',
            text,
        )

    def test_fields_cannot_change_identity_keys(self):
        code, _, err = self.run_cli("meeting", "--title", "X", "--location", "teams", "--fields", '{"id": "1"}')
        self.assertEqual(code, 1)
        self.assertIn("cannot set 'id'", err)


class ProjectTests(VaultTestCase):
    def test_resources_url_expands_home_and_matches_captured_vault_value(self):
        # shape captured from a real project note made by page.create-project.tpl; user name, title, and ID replaced
        self.clock.return_value = datetime(2026, 3, 14, 10, 15, 0, tzinfo=timezone(timedelta(hours=1)))
        home = "C:/Users/you" if os.name == "nt" else "/Users/you"
        with mock.patch.dict(os.environ, {"HOME": home, "USERPROFILE": home}):
            code, report, _ = self.run_cli("project", "--title", "Plan team offsite",
                                           "--deliverable", "support", "--dry-run")
        self.assertEqual(code, 0)
        expected = (
            "file:///C:/Users/you/Documents/reference/10-projects/20260314101500-plan-team-offsite"
            if os.name == "nt" else
            "file:///%2FUsers%2Fyou%2FDocuments%2Freference%2F10-projects%2F20260314101500-plan-team-offsite"
        )
        self.assertIn(f'resources: "[project resources]({expected})"\n', report["content"])
        self.assertIn("- [ ] 2026-03-14 10:15 - plan the next action to move this project forward"
                      " | #gtd/act/now 📅 2026-03-14\n", report["content"])

    def test_resources_folder_created_under_existing_root_with_ticket_line(self):
        root = Path(self._tmp.name) / "10-projects"
        root.mkdir()
        with mock.patch.object(create_note, "PROJECTS_ROOT", str(root)):
            report, text = self.create("project", "--title", "fix payroll export",
                                       "--deliverable", "fix", "--ticket", "SR-42")
        folder = root / "20260105093012-fix-payroll-export"
        self.assertTrue(folder.is_dir())
        self.assertEqual(report["resources_folder"], {"path": str(folder), "status": "created"})
        self.assertIn("- parent:: [[notes/20260105093012|Fix payroll export]]\n- ticket:: SR-42\n- us::\n", text)

    def test_resources_folder_skipped_when_root_missing(self):
        with mock.patch.object(create_note, "PROJECTS_ROOT", str(Path(self._tmp.name) / "missing")):
            report, text = self.create("project", "--title", "X", "--deliverable", "fix")
        self.assertTrue(report["resources_folder"]["status"].startswith("skipped:"))
        self.assertNotIn("ticket::", text)


class TemplateTests(VaultTestCase):
    KIND_ARGS = {
        "note": [], "illustrated": [], "prr": [], "book": [], "contact": [],
        "meeting": ["--location", "phone"],
        "youtube": ["--video", "Zx7Qw1Lm0Pq"],
        "project": ["--deliverable", "fix"],
    }

    def test_every_kind_renders_clean_markdown(self):
        self.assertEqual(set(self.KIND_ARGS), set(create_note.KINDS))
        for kind, extra in self.KIND_ARGS.items():
            with self.subTest(kind=kind):
                code, report, err = self.run_cli(kind, "--title", f"Sample {kind}", "--dry-run", *extra)
                self.assertEqual(code, 0, err)
                text = report["content"]
                self.assertNotIn("${", text)
                self.assertNotIn("\x00", text)
                self.assertIsNone(re.search(r"[ \t]+$", text, re.M), "trailing whitespace")
                self.assertIsNone(re.search(r"^\s*[-*+] (\[ \])?$", text, re.M), "empty list marker")
                self.assertTrue(text.endswith("\n") and not text.endswith("\n\n"))
                self.assertTrue(text.startswith("---\nid: 20260105093012\n"))

    def test_illustrated_note_alt_text_is_raw_title_and_drawing_kept(self):
        _, text = self.create("illustrated", "--title", "Travel: cables")
        self.assertIn("![Travel: cables](20260105093012.svg)\n\n# Text Elements\n%%\n# Drawing\n```json\n{\n\t\"type\": \"excalidraw\"", text)
        self.assertIn("excalidraw-plugin: parsed\nexcalidraw-open-md: true\n---\n", text)
        self.assertTrue(text.endswith("```\n%%\n"))

    def test_prr_body_follows_gather_information_paragraph(self):
        body = Path(self._tmp.name) / "b.md"
        body.write_text("Ticket says totals are off.\n", encoding="utf-8")
        _, text = self.create("prr", "--title", "Totals off", "--body-file", str(body))
        self.assertIn("\n# PRR: Totals off\n\n## Define the problem\n", text)
        self.assertIn("are considered.\n\nTicket says totals are off.\n\n### What?\n", text)
        self.assertTrue(text.endswith("problem resolution.\n\n---\nparent::\n"))


class ContactLinkTests(VaultTestCase):
    """Contact frontmatter shapes are captured from the vault (comma-scalar aliases); names are invented."""

    def contact(self, slug, title, aliases=None, style="scalar"):
        lines = ["---", "id: 20240101000000", f"title: {title}"]
        if aliases and style == "scalar":
            lines.append("aliases: " + ", ".join(aliases))
        elif aliases and style == "flow":
            lines.append("aliases: [" + ", ".join(aliases) + "]")
        elif aliases:
            lines.extend(["aliases:"] + [f"  - {alias}" for alias in aliases])
        lines += ["type: contact", "---", "", f"# {title}", ""]
        (self.vault / "notes/contact" / f"{slug}.md").write_text("\n".join(lines), encoding="utf-8")

    def body_of(self, text, **kwargs):
        body = Path(self._tmp.name) / "body.md"
        body.write_text(text, encoding="utf-8")
        return self.create("note", "--title", "X", "--body-file", str(body), *kwargs.get("extra", []))

    def test_full_name_is_linked_even_without_diacritics_or_in_teams_sender_order(self):
        self.contact("ada-novak", "Ada Nováková", ["Ada Nováková", "Ada", "Lovelace Jr"])
        report, text = self.body_of("Ada Novakova wrote it. Later Nováková, Ada agreed.")
        self.assertIn("[[notes/contact/ada-novak|Ada Novakova]] wrote it.", text)
        self.assertIn("Later Nováková, Ada agreed.", text)  # only the first mention is linked
        self.assertEqual(report["linked_contacts"], ["[[notes/contact/ada-novak|Ada Novakova]]"])

    def test_teams_sender_order_is_linked_when_it_is_the_first_mention(self):
        self.contact("ada-novak", "Ada Nováková")
        _, text = self.body_of("From Nováková, Ada: see below.")
        self.assertIn("From [[notes/contact/ada-novak|Nováková, Ada]]: see below.", text)

    def test_multi_word_aliases_in_flow_and_block_style_are_linked(self):
        self.contact("bob-ek", "Robert Ek", ["Bob Ek"], style="flow")
        self.contact("cy-lee", "Cyrus Lee", ["Cy Lee"], style="block")
        _, text = self.body_of("Bob Ek and Cy Lee met.")
        self.assertIn("[[notes/contact/bob-ek|Bob Ek]] and [[notes/contact/cy-lee|Cy Lee]] met.", text)

    def test_single_word_names_are_never_linked(self):
        self.contact("ada-novak", "Ada Nováková", ["Ada", "Trist"])
        _, text = self.body_of("Ada and Trist agree.")
        self.assertNotIn("[[", text)

    def test_name_shared_by_two_contacts_is_not_linked(self):
        self.contact("jan-novak-1", "Jan Novák")
        self.contact("jan-novak-2", "Jan Novák")
        _, text = self.body_of("Ask Jan Novák.")
        self.assertNotIn("[[", text)

    def test_names_inside_links_urls_and_code_stay_untouched(self):
        self.contact("ada-novak", "Ada Nováková")
        source = "[[notes/x|Ada Nováková]] `Ada Nováková` [Ada Nováková](https://example.com/a) https://example.com/Ada-Nováková"
        _, text = self.body_of(source)
        self.assertIn(source, text)
        self.assertNotIn("contact/ada-novak", text)

    def test_no_link_contacts_keeps_the_body_verbatim(self):
        self.contact("ada-novak", "Ada Nováková")
        report, text = self.body_of("Ada Nováková wrote it.", extra=["--no-link-contacts"])
        self.assertIn("# X\n\nAda Nováková wrote it.\n", text)
        self.assertNotIn("linked_contacts", report)

    def test_article_links_the_core_facts_but_archives_the_original_verbatim(self):
        self.contact("ada-novak", "Ada Nováková")
        archive = self.vault.parent / "archives" / "articles"
        archive.parent.mkdir()
        (self.vault / "orig.md").write_text("Ada Nováková announced it.\n", encoding="utf-8")
        (self.vault / "facts.md").write_text("- Ada Nováková owns it\n", encoding="utf-8")
        code, report, err = self.run_cli(
            "article", "--title", "News", "--archive-root", str(archive),
            "--body-file", str(self.vault / "orig.md"), "--summary-file", str(self.vault / "facts.md"))
        self.assertEqual(code, 0, err)
        self.assertIn("- [[notes/contact/ada-novak|Ada Nováková]] owns it", Path(report["note"]["path"]).read_text(encoding="utf-8"))
        self.assertEqual((archive / "2026" / "20260100" / "News.md").read_text(encoding="utf-8"), "# News\n\nAda Nováková announced it.\n")


class DailyLogTests(VaultTestCase):
    """The Log shapes are captured from the vault: a filled log and the empty log of the daily template."""

    ENTRY = "- [ ] _05.01.2026 09:30:12_ - [[notes/20260105093012|X]]"

    def daily(self, text):
        path = self.vault / "notes/calendar/daily/2026-01-05.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        return path

    def test_entry_follows_the_last_log_line_and_keeps_the_gap_before_next_heading(self):
        path = self.daily("# Day\n\n## Log\n- [ ] _04.01.2026 19:31:13_ - earlier\n\n\n## Navigation\n\n- link\n")
        report, _ = self.create("note", "--title", "X")
        self.assertEqual(report["daily_log"]["status"], "added")
        self.assertEqual(
            path.read_text(encoding="utf-8"),
            f"# Day\n\n## Log\n- [ ] _04.01.2026 19:31:13_ - earlier\n{self.ENTRY}\n\n\n## Navigation\n\n- link\n",
        )

    def test_empty_log_section_gets_the_entry_right_under_the_heading(self):
        path = self.daily("## Log\n\n\n## Navigation\n")
        self.create("note", "--title", "X")
        self.assertEqual(path.read_text(encoding="utf-8"), f"## Log\n{self.ENTRY}\n\n\n## Navigation\n")

    def test_missing_daily_note_is_reported_and_never_created(self):
        report, _ = self.create("note", "--title", "X")
        self.assertIn("2026-01-05.md does not exist", report["daily_log"]["status"])
        self.assertFalse((self.vault / "notes/calendar").exists())

    def test_daily_note_without_log_section_is_left_alone(self):
        path = self.daily("# Day\n\n## Notes\n")
        report, _ = self.create("note", "--title", "X")
        self.assertIn("no '## Log' section", report["daily_log"]["status"])
        self.assertEqual(path.read_text(encoding="utf-8"), "# Day\n\n## Notes\n")

    def test_no_daily_log_flag_writes_no_entry(self):
        path = self.daily("## Log\n")
        report, _ = self.create("note", "--title", "X", "--no-daily-log")
        self.assertNotIn("daily_log", report)
        self.assertEqual(path.read_text(encoding="utf-8"), "## Log\n")

    def test_dry_run_reports_the_entry_without_writing_it(self):
        path = self.daily("## Log\n")
        code, report, _ = self.run_cli("note", "--title", "Y", "--dry-run")
        self.assertEqual((code, report["daily_log"]["status"]), (0, "not written (dry run)"))
        self.assertEqual(path.read_text(encoding="utf-8"), "## Log\n")

    def test_article_is_logged_with_its_zettel_link(self):
        path = self.daily("## Log\n")
        archive = self.vault.parent / "archives" / "articles"
        archive.parent.mkdir()
        (self.vault / "orig.md").write_text("Text.\n", encoding="utf-8")
        (self.vault / "facts.md").write_text("- Fact\n", encoding="utf-8")
        code, _, err = self.run_cli(
            "article", "--title", "News", "--archive-root", str(archive),
            "--body-file", str(self.vault / "orig.md"), "--summary-file", str(self.vault / "facts.md"))
        self.assertEqual(code, 0, err)
        self.assertIn("_05.01.2026 09:30:12_ - [[notes/20260105093012|News]]", path.read_text(encoding="utf-8"))

    def test_failed_daily_write_is_reported_after_the_note_was_written(self):
        self.daily("## Log\n")
        with mock.patch.object(create_note, "append_daily_log", side_effect=OSError(errno.EACCES, "denied")):
            code, report, err = self.run_cli("note", "--title", "X")
        self.assertEqual(code, 1)
        self.assertIn("daily note log entry", err)
        self.assertTrue(Path(report["path"]).exists())


class YamlScalarTests(unittest.TestCase):
    def test_values_yaml_would_retype_are_quoted(self):
        for value in ("true", "No", "12", "1.5", "2026-01-05", "", " padded", "- dash", "a #b", "x: y"):
            with self.subTest(value=value):
                self.assertTrue(create_note.yaml_scalar(value).startswith('"'))

    def test_plain_text_stays_unquoted(self):
        for value in ("C# guide", "2026-01-05 | Sync meeting minutes", "Zoë", "Plain words"):
            with self.subTest(value=value):
                self.assertEqual(create_note.yaml_scalar(value), value)


if __name__ == "__main__":
    unittest.main()
