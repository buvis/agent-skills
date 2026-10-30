"""Hyperlinks survive Confluence-to-Markdown conversion (authored HTML input)."""

from pathlib import Path
import runpy
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def convert(html):
    parser = runpy.run_path(str(SCRIPTS / "confluence_to_md.py"))["ConfluenceToMd"]()
    parser.feed(html)
    return parser.get_markdown()


class LinkTests(unittest.TestCase):
    def test_html_conversion_preserves_the_hyperlink_destination(self):
        self.assertEqual(
            convert('<p><a href="https://example.com/docs">Read</a></p>'),
            "[Read](https://example.com/docs)",
        )

    def test_link_inside_a_sentence_keeps_surrounding_text(self):
        self.assertEqual(
            convert('<p>See <a href="https://example.com/x">the docs</a> now.</p>'),
            "See [the docs](https://example.com/x) now.",
        )

    def test_anchor_without_href_stays_plain_text(self):
        self.assertEqual(convert("<p><a>Plain</a></p>"), "Plain")


if __name__ == "__main__":
    unittest.main()
