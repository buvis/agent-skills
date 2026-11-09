"""Failure exit codes and attachment pagination. All HTTP and renderer calls are faked."""

import contextlib
import io
import json
import os
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import urllib.error

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
ENV = {"CONFLUENCE_BASE_URL": "https://example.invalid", "CONFLUENCE_SPACE_KEY": "EX",
       "CONFLUENCE_TOKEN": "t"}


def load(name):
    with patch.dict(os.environ, ENV, clear=True):
        return runpy.run_path(str(SCRIPTS / name))


def quiet(fn, *args):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*args)


def response(payload):
    resp = MagicMock()
    resp.__enter__.return_value = io.BytesIO(json.dumps(payload).encode())
    return resp


def curl(code):
    return subprocess.CompletedProcess([], 0, stdout=code, stderr="")


class AttachTests(unittest.TestCase):
    def setUp(self):
        self.mod = load("confluence_attach.py")
        self.main = self.mod["main"]

    def test_exit_zero_when_every_upload_succeeds(self):
        with patch.dict(self.mod["main"].__globals__, {"get_existing_attachments": lambda *a: {}}):
            with patch("subprocess.run", return_value=curl("200")):
                self.assertEqual(quiet(self.main, ["1", "a.png", "b.png", "--token", "t"]), 0)

    def test_exit_nonzero_when_any_upload_fails(self):
        with patch.dict(self.mod["main"].__globals__, {"get_existing_attachments": lambda *a: {}}):
            with patch("subprocess.run", side_effect=[curl("200"), curl("500")]):
                self.assertEqual(quiet(self.main, ["1", "a.png", "b.png", "--token", "t"]), 1)

    def test_exit_nonzero_when_listing_fails(self):
        err = urllib.error.URLError("down")
        with patch("urllib.request.urlopen", side_effect=err):
            self.assertEqual(quiet(self.main, ["1", "a.png", "--token", "t"]), 1)

    def test_transfer_failure_with_success_status_is_failure(self):
        result = subprocess.CompletedProcess([], 23, stdout="200", stderr="write failed")
        with patch("subprocess.run", return_value=result) as invoked:
            self.assertFalse(quiet(self.mod["upload"], "1", "a.png", "t", {}))
        command = invoked.call_args.args[0]
        self.assertEqual(command[command.index("-o") + 1], os.devnull)

    def test_listing_follows_pagination(self):
        pages = [
            {"results": [{"title": "a.png", "id": "1"}], "_links": {"next": "/x"}},
            {"results": [{"title": "b.png", "id": "2"}], "_links": {}},
        ]
        with patch("urllib.request.urlopen", side_effect=[response(p) for p in pages]) as opened:
            found = self.mod["get_existing_attachments"]("9", "t")
        self.assertEqual(found, {"a.png": "1", "b.png": "2"})
        urls = [c.args[0].full_url for c in opened.call_args_list]
        self.assertIn("start=0", urls[0])
        self.assertIn("start=1", urls[1])


class MermaidTests(unittest.TestCase):
    def run_main(self, returncode):
        mod = runpy.run_path(str(SCRIPTS / "mermaid_to_png.py"))
        with tempfile.TemporaryDirectory() as tmp:
            md = Path(tmp) / "in.md"
            md.write_text("# One\n\n```mermaid\ngraph TD; A-->B\n```\n")

            def fake(cmd, **kw):
                if returncode == 0:
                    Path(cmd[cmd.index("-o") + 1]).write_bytes(b"png")
                return subprocess.CompletedProcess(cmd, returncode, "", "boom")

            with patch("subprocess.run", side_effect=fake):
                return quiet(mod["main"], [str(md), "--output-dir", tmp])

    def test_exit_zero_when_all_render(self):
        self.assertEqual(self.run_main(0), 0)

    def test_exit_nonzero_when_a_render_fails(self):
        self.assertEqual(self.run_main(1), 1)


class EmbedTests(unittest.TestCase):
    def setUp(self):
        self.mod = load("confluence_embed_images.py")
        self.page = {"title": "T", "body": {"storage": {"value": "<p>x</p>"}},
                     "version": {"number": 1}}

    def run_main(self, update):
        g = self.mod["main"].__globals__
        with patch.dict(g, {"get_page": lambda *a: self.page, "update_page": update}):
            return quiet(self.mod["main"], ["1", "d.png", "--token", "t"])

    def test_exit_zero_when_update_succeeds(self):
        self.assertEqual(self.run_main(lambda *a: {"version": {"number": 2}}), 0)

    def test_exit_nonzero_when_update_fails(self):
        def boom(*a):
            raise urllib.error.URLError("down")
        self.assertEqual(self.run_main(boom), 1)

    def test_replacement_preserves_prior_notes_and_intervening_content(self):
        first = ('<ac:structured-macro ac:name="note"><ac:rich-text-body>'
                 '<p>Keep this</p></ac:rich-text-body></ac:structured-macro>')
        between = '<h2>Keep this heading too</h2>'
        placeholder = '<ac:structured-macro ac:name="note"><p>d.png</p></ac:structured-macro>'
        self.page["body"]["storage"]["value"] = first + between + placeholder
        saved = []

        def update(*args):
            saved.append(args[2])
            return {"version": {"number": 2}}

        self.assertEqual(self.run_main(update), 0)
        self.assertEqual(saved, [first + between + self.mod["image_tag"]("d.png", 900)])

    def test_nested_notes_are_preserved_when_appending_an_image(self):
        content = ('<ac:structured-macro ac:name="note"><p>d.png</p>'
                   '<ac:structured-macro ac:name="info"><p>Keep</p></ac:structured-macro>'
                   '</ac:structured-macro>')
        self.page["body"]["storage"]["value"] = content
        saved = []

        def update(*args):
            saved.append(args[2])
            return {"version": {"number": 2}}

        self.assertEqual(self.run_main(update), 0)
        self.assertEqual(saved, [content + "\n" + self.mod["image_tag"]("d.png", 900)])

    def test_image_filename_is_xml_escaped(self):
        from xml.etree import ElementTree

        filename = 'diagram "A&B".png'
        fragment = self.mod["image_tag"](filename, 900)
        root = ElementTree.fromstring(
            '<root xmlns:ac="urn:ac" xmlns:ri="urn:ri">' + fragment + '</root>'
        )
        self.assertEqual(root.find('.//{urn:ri}attachment').attrib['{urn:ri}filename'], filename)


if __name__ == "__main__":
    unittest.main()
