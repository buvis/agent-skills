#!/usr/bin/env python3

"""Tests for copy_rich.py. Run from the skill folder: python3 -m unittest discover -s scripts -v"""

import io
import re
import sys
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import copy_rich  # noqa: E402


class MarkdownCodeBlockTests(unittest.TestCase):
    def test_fenced_code_pastes_with_immediate_teams_syntax_colors(self):
        rendered = copy_rich.markdown_to_html(
            'Before\n\n```python\nif value < 2:\n    print("ok")\n```\n\nAfter'
        )

        self.assertTrue(rendered.startswith('<span data-teams="true">'))
        self.assertTrue(rendered.endswith("</span>"))
        self.assertRegex(
            rendered,
            (
                r'<p>&nbsp;</p><p itemtype="http://schema\.skype\.com/'
                r'CodeBlockEditor" id="x_x_[0-9a-f]{32}">&nbsp;</p>'
            ),
        )
        self.assertRegex(
            rendered,
            (
                r'<pre class="language-python skipProofing" '
                r'itemid="codeBlockEditor-[0-9a-f-]{36}" '
                r'corrected="true" spellcheck="false">'
            ),
        )
        self.assertIn(
            '<span class="hljs-keyword">if</span>&nbsp;value&nbsp;&lt;&nbsp;2:',
            rendered,
        )
        self.assertIn(
            '<span class="hljs-function">print</span>'
            '(<span class="hljs-string">&quot;ok&quot;</span>)',
            rendered,
        )
        self.assertIn("</code></pre><p>&nbsp;</p>", rendered)
        self.assertNotIn("pasteSource", rendered)
        self.assertNotIn("```", rendered)

    def test_fenced_code_without_language_uses_plaintext(self):
        rendered = copy_rich.markdown_to_html("```\na = 1\n```")

        self.assertIn(
            '<pre class="language-plaintext skipProofing"',
            rendered,
        )

    def test_language_alias_uses_teams_supported_class(self):
        rendered = copy_rich.markdown_to_html(
            "```c++\nint main() { return 0; }\n```"
        )

        self.assertIn('class="language-cpp skipProofing"', rendered)
        self.assertIn('<span class="hljs-keyword">int</span>', rendered)

    def test_multiple_code_blocks_share_one_teams_clipboard_wrapper(self):
        rendered = copy_rich.markdown_to_html(
            "```python\npass\n```\n\n```sql\nselect 1\n```"
        )

        self.assertEqual(rendered.count('<span data-teams="true">'), 1)
        block_ids = re.findall(r'itemid="(codeBlockEditor-[0-9a-f-]+)"', rendered)
        self.assertEqual(len(block_ids), 2)
        self.assertEqual(len(set(block_ids)), 2)

    def test_colored_code_requires_pygments(self):
        with (
            patch.object(copy_rich, "lex", None),
            patch.object(copy_rich, "get_lexer_by_name", None),
        ):
            with self.assertRaisesRegex(
                RuntimeError,
                "Pygments is required.*immediate Teams syntax highlighting",
            ):
                copy_rich.markdown_to_html("```python\npass\n```")

    def test_cli_reports_missing_pygments_without_traceback(self):
        stderr = io.StringIO()

        with (
            patch.object(
                copy_rich.sys,
                "argv",
                ["copy_rich.py", "```python\npass\n```"],
            ),
            patch.object(copy_rich, "lex", None),
            patch.object(copy_rich, "get_lexer_by_name", None),
            redirect_stderr(stderr),
        ):
            with self.assertRaises(SystemExit) as exit_context:
                copy_rich.main()

        self.assertEqual(exit_context.exception.code, 1)
        self.assertIn("Error: Pygments is required", stderr.getvalue())

    def test_unknown_fence_language_fails_instead_of_claiming_highlighting(self):
        with self.assertRaisesRegex(
            RuntimeError, "No Pygments lexer is available.*madeuplang"
        ):
            copy_rich.markdown_to_html("```madeuplang\nvalue\n```")

    def test_html_inside_fence_is_detected_as_markdown(self):
        content = "```html\n<div>Hello</div>\n```"

        self.assertFalse(copy_rich.is_html(content))
        rendered = copy_rich.markdown_to_html(content)
        self.assertIn('class="language-html skipProofing"', rendered)
        self.assertIn("&lt;<span class=\"hljs-keyword\">div</span>&gt;", rendered)

    def test_jira_keys_stay_plain_text_without_base_url(self):
        rendered = copy_rich.markdown_to_html("Issue PROJ-1234 is open")

        with patch.object(copy_rich, "JIRA_BASE_URL", ""):
            linked = copy_rich.auto_link_jira_keys(rendered)

        self.assertEqual(linked, rendered)
        self.assertNotIn("<a ", linked)

    def test_jira_auto_linker_does_not_rewrite_code(self):
        rendered = copy_rich.markdown_to_html(
            "Issue PROJ-1234\n\n```text\nPROJ-5678\n```"
        )
        with patch.object(
            copy_rich, "JIRA_BASE_URL", "https://jira.example.com/browse"
        ):
            linked = copy_rich.auto_link_jira_keys(rendered)

        self.assertIn(
            '<a href="https://jira.example.com/browse/PROJ-1234">'
            "PROJ-1234</a>",
            linked,
        )
        self.assertNotIn(
            'href="https://jira.example.com/browse/PROJ-5678"',
            linked,
        )

    def test_code_block_requires_html_clipboard_support(self):
        rendered = copy_rich.markdown_to_html("```python\nprint('ok')\n```")

        with patch.object(copy_rich, "_HAS_APPKIT", False):
            with self.assertRaisesRegex(
                RuntimeError, "PyObjC/AppKit is required.*Teams-native code blocks"
            ):
                copy_rich.copy_html_as_rich_text(rendered)


if __name__ == "__main__":
    unittest.main()
