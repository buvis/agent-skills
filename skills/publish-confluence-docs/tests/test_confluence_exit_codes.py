"""Failure exit codes and attachment pagination. All HTTP and renderer calls are faked."""

import contextlib
import inspect
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
import xml.etree.ElementTree as ET

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


def curl_result(returncode, stdout):
    return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr="")


def capture(fn, *args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        result = fn(*args)
    return result, out.getvalue() + err.getvalue()


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

    def test_upload_fails_on_nonzero_curl_exit_even_with_2xx_stdout(self):
        upload = self.mod["upload"]
        with patch("subprocess.run", return_value=curl_result(23, "200")):
            ok, out = capture(upload, "1", "a.png", "secret-token-xyz", {})
        self.assertFalse(ok)
        self.assertIn("FAIL", out)
        self.assertIn("23", out)

    def test_upload_fails_when_curl_binary_is_missing(self):
        upload = self.mod["upload"]
        with patch("subprocess.run", side_effect=FileNotFoundError("no curl")):
            ok, out = capture(upload, "1", "a.png", "secret-token-xyz", {})
        self.assertFalse(ok)
        self.assertIn("curl", out)

    def test_upload_fails_on_non_2xx_http_status_with_zero_exit(self):
        upload = self.mod["upload"]
        with patch("subprocess.run", return_value=curl_result(0, "500")):
            ok, out = capture(upload, "1", "a.png", "secret-token-xyz", {})
        self.assertFalse(ok)
        self.assertIn("FAIL", out)

    def test_upload_succeeds_on_zero_exit_with_2xx_status(self):
        upload = self.mod["upload"]
        with patch("subprocess.run", return_value=curl_result(0, "201")):
            ok, out = capture(upload, "1", "a.png", "secret-token-xyz", {})
        self.assertTrue(ok)
        self.assertIn("OK", out)
        self.assertIn("Uploaded", out)

    def test_upload_reports_updated_when_filename_has_existing_attachment(self):
        upload = self.mod["upload"]
        with patch("subprocess.run", return_value=curl_result(0, "201")):
            ok, out = capture(upload, "1", "a.png", "secret-token-xyz", {"a.png": "99"})
        self.assertTrue(ok)
        self.assertIn("Updated", out)

    def test_upload_never_prints_token(self):
        upload = self.mod["upload"]
        token = "secret-token-xyz"
        scenarios = [
            curl_result(23, "200"),
            curl_result(0, "500"),
            curl_result(0, "201"),
        ]
        for result in scenarios:
            with patch("subprocess.run", return_value=result):
                _, out = capture(upload, "1", "a.png", token, {})
            self.assertNotIn(token, out)
        with patch("subprocess.run", side_effect=FileNotFoundError("no curl")):
            _, out = capture(upload, "1", "a.png", token, {})
        self.assertNotIn(token, out)


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

    def filename_from_image_tag(self, tag):
        wrapped = f'<r xmlns:ac="ac-ns" xmlns:ri="ri-ns">{tag}</r>'
        root = ET.fromstring(wrapped)
        attachment = root.find(".//{ri-ns}attachment")
        return attachment.attrib["{ri-ns}filename"]

    def test_image_tag_escapes_ampersand_so_attribute_round_trips(self):
        image_tag = self.mod["image_tag"]
        tag = image_tag("a&b.png", 900)
        self.assertEqual(self.filename_from_image_tag(tag), "a&b.png")

    def test_image_tag_escapes_double_quote_so_attribute_round_trips(self):
        image_tag = self.mod["image_tag"]
        tag = image_tag('q"x.png', 900)
        self.assertEqual(self.filename_from_image_tag(tag), 'q"x.png')

    def test_image_tag_keeps_literal_backslash_in_filename(self):
        image_tag = self.mod["image_tag"]
        tag = image_tag("a\\b.png", 900)
        self.assertEqual(self.filename_from_image_tag(tag), "a\\b.png")

    def test_image_tag_ordinary_filename_is_byte_identical_to_before(self):
        image_tag = self.mod["image_tag"]
        tag = image_tag("ordinary.png", 900)
        self.assertEqual(
            tag,
            '<p><ac:image ac:width="900">'
            '<ri:attachment ri:filename="ordinary.png" /></ac:image></p>',
        )

    def test_image_tag_signature_stays_two_positional_args_returning_str(self):
        image_tag = self.mod["image_tag"]
        params = list(inspect.signature(image_tag).parameters)
        self.assertEqual(params, ["filename", "width"])
        self.assertIsInstance(image_tag("plain.png", 42), str)

    def test_main_replaces_note_with_image_tag_keeping_backslash_literal(self):
        page = {
            "title": "T",
            "body": {
                "storage": {
                    "value": (
                        '<ac:structured-macro ac:name="note">'
                        "<ac:rich-text-body>See a\\b</ac:rich-text-body>"
                        "</ac:structured-macro>"
                    )
                }
            },
            "version": {"number": 1},
        }
        captured = {}

        def capture_update(page_id, title, content, version, token):
            captured["content"] = content
            return {"version": {"number": version}}

        g = self.mod["main"].__globals__
        with patch.dict(g, {"get_page": lambda *a: page, "update_page": capture_update}):
            quiet(self.mod["main"], ["1", "a\\b.png", "--token", "t"])

        self.assertIn('ri:filename="a\\b.png"', captured["content"])


if __name__ == "__main__":
    unittest.main()
