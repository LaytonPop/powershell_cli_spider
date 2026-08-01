from __future__ import annotations

from spider_core.renderers import build_html_doc, build_markdown_doc, sanitize_filename


class TestSanitizeFilename:
    def test_normal_title(self):
        assert sanitize_filename("  你好  世界  ") == "你好_世界"

    def test_illegal_chars_removed(self):
        assert sanitize_filename('a/b\\c:d*e?f"g<h>i|j') == "abcdefghij"

    def test_dot_and_dotdot_blocked(self):
        assert sanitize_filename("..") != ".."
        assert sanitize_filename(".") != "."
        assert sanitize_filename("...") != "..."

    def test_hidden_file_style_title_blocked(self):
        # ".hidden" is a hidden file on Linux; fall back to hash name
        result = sanitize_filename(".hidden")
        assert not result.startswith(".")

    def test_empty_title_fallback(self):
        result = sanitize_filename("   ")
        assert result.startswith("article_")

    def test_length_capped(self):
        assert len(sanitize_filename("x" * 300)) == 100


class TestHtmlDoc:
    def test_title_escaped(self):
        doc = build_html_doc('<script>alert(1)</script>', "<p>body</p>", "", "https://example.com")
        assert "<script>alert(1)</script>" not in doc
        assert "&lt;script&gt;" in doc

    def test_source_url_escaped(self):
        doc = build_html_doc("t", "<p>b</p>", "", 'https://example.com/?a="x"')
        assert '"x"' not in doc


class TestMarkdownDoc:
    def test_frontmatter_quoted_title_is_valid_yaml(self):
        doc = build_markdown_doc('He said "hi"', "<p>body</p>", "2024-01-01", "https://example.com")
        lines = doc.splitlines()
        assert lines[0] == "---"
        assert 'title: "He said \\"hi\\""' in lines
        assert "He said \"hi\"" in doc  # body still contains raw title heading

    def test_frontmatter_has_source(self):
        doc = build_markdown_doc("t", "<p>b</p>", "", "https://example.com/p")
        assert 'source: "https://example.com/p"' in doc
