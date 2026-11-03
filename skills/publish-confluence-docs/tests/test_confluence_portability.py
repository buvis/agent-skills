"""Authored portability fixtures; none are captured SAP or Confluence responses.

Network calls are never permitted here.
"""

import contextlib
import importlib.util
import io
import os
from pathlib import Path
import runpy
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
HAS_DOCX_PDF = all(
    importlib.util.find_spec(m) for m in ("docx", "fitz", "yaml")
)
NEEDS_DEPS = unittest.skipUnless(
    HAS_DOCX_PDF,
    "SKIPPED, NOT PASSED: needs python-docx, pymupdf, pyyaml "
    "(run: uv run --project skills/publish-confluence-docs pytest skills/publish-confluence-docs/tests)",
)
PUBLISHERS = ("confluence_attach.py", "confluence_embed_images.py")


def load_script(name):
    return runpy.run_path(str(SCRIPTS / name))


class PortabilityTests(unittest.TestCase):
    def test_publishers_require_an_explicit_instance(self):
        with tempfile.TemporaryDirectory() as home:
            for name in PUBLISHERS:
                with self.subTest(script=name):
                    result = subprocess.run(
                        [sys.executable, "-B", str(SCRIPTS / name), "100", "diagram.png"],
                        env={"HOME": home},
                        capture_output=True, text=True, check=False,
                    )
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertIn("Set CONFLUENCE_BASE_URL", result.stderr)

    def test_image_embedding_requires_an_explicit_space(self):
        with tempfile.TemporaryDirectory() as home:
            result = subprocess.run(
                [sys.executable, "-B", str(SCRIPTS / PUBLISHERS[1]), "100", "diagram.png"],
                env={"HOME": home, "CONFLUENCE_BASE_URL": "https://example.invalid"},
                capture_output=True, text=True, check=False,
            )
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn("Set CONFLUENCE_SPACE_KEY", result.stderr)

    def test_missing_tokens_never_read_agent_configuration(self):
        for name in PUBLISHERS:
            with self.subTest(script=name):
                module = load_script(name)
                with patch.dict(os.environ, {}, clear=True):
                    with patch("builtins.open", side_effect=AssertionError("Unexpected config read")) as opened:
                        self.assertIsNone(module["get_token"]())
                    opened.assert_not_called()
                sentinel = object()
                self.assertIs(module["get_token"](sentinel), sentinel)

    def test_mermaid_uses_the_skill_local_installed_cli(self):
        module = load_script("mermaid_to_png.py")
        refused = subprocess.CompletedProcess(
            args=[], returncode=1, stdout="", stderr="Authored renderer refusal"
        )
        with tempfile.TemporaryDirectory() as output:
            with patch("subprocess.run", return_value=refused) as invoked:
                with contextlib.redirect_stderr(io.StringIO()):
                    module["render"]([("diagram", "graph TD; A-->B")], output, 800, 1)
        command = invoked.call_args.args[0]
        self.assertEqual(command[:5], [
            "npx", "--no-install", "--prefix", str(SCRIPTS.resolve().parent), "mmdc"
        ])

    @NEEDS_DEPS
    def test_word_output_uses_neutral_style_and_unclassified_metadata(self):
        module = load_script("md_to_docx.py")
        with tempfile.TemporaryDirectory() as output:
            source = Path(output) / "input.md"
            target = Path(output) / "output.docx"
            source.write_text("# Report\n\n| Label | Value |\n|---|---|\n| Count | 2 |\n")
            with contextlib.redirect_stdout(io.StringIO()):
                module["convert"](str(source), str(target))
            with zipfile.ZipFile(target) as archive:
                header = archive.read("word/header1.xml").decode()
                footer = archive.read("word/footer1.xml").decode()
                document = archive.read("word/document.xml").decode()
            self.assertIn('w:color="334155"', header)
            self.assertIn('w:color="334155"', footer)
            self.assertIn('w:fill="334155"', document)
            self.assertIn("Unclassified", footer)

    def test_confluence_output_uses_neutral_heading_and_table_styles(self):
        module = load_script("md_to_confluence.py")
        with tempfile.TemporaryDirectory() as output:
            source = Path(output) / "input.md"
            source.write_text("# Report\n\n| Label | Value |\n|---|---|\n| Count | 2 |\n")
            with contextlib.redirect_stdout(io.StringIO()):
                html = module["convert"](str(source))
        self.assertIn('color:#334155;', html)
        self.assertIn('background-color:#334155;', html)

    @NEEDS_DEPS
    def test_importers_do_not_assign_an_employer_classification(self):
        import fitz
        from docx import Document

        with tempfile.TemporaryDirectory() as output:
            directory = Path(output)
            html = directory / "input.html"
            html.write_text("<h1>Report</h1><p>Authored conversion input.</p>")
            word = directory / "input.docx"
            document = Document()
            document.add_paragraph("Authored conversion input.")
            document.save(word)
            pdf = directory / "input.pdf"
            with fitz.open() as document:
                page = document.new_page()
                page.insert_text((72, 72), "Authored conversion input.")
                document.save(pdf)
            for name, source in (
                ("confluence_to_md.py", html),
                ("docx_to_md.py", word),
                ("pdf_to_md.py", pdf),
            ):
                with self.subTest(script=name):
                    target = directory / f"{source.suffix[1:]}.md"
                    result = subprocess.run(
                        [sys.executable, "-B", str(SCRIPTS / name), str(source), str(target)],
                        capture_output=True, text=True, check=False,
                    )
                    self.assertEqual(result.returncode, 0, result.stderr)
                    self.assertIn('classification: "Unclassified"', target.read_text())


if __name__ == "__main__":
    unittest.main()
