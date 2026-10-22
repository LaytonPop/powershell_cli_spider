"""HTML 正文清洗测试：保证保存下来的富文本离线可见且干净。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spider_core.html_cleaner import (  # noqa: E402
    clean_article_html,
    clean_style,
    split_style_declarations,
)


class SplitStyleDeclarationsTests(unittest.TestCase):
    def test_splits_on_top_level_semicolons(self) -> None:
        self.assertEqual(
            split_style_declarations("color: red; margin: 0 0 1em"),
            ["color: red", "margin: 0 0 1em"],
        )

    def test_ignores_semicolons_inside_url_and_quotes(self) -> None:
        declarations = split_style_declarations(
            r'background:url("a;b.png"); content:"x;y"; font-family:"A; B"'
        )
        self.assertEqual(len(declarations), 3)
        self.assertIn('content:"x;y"', declarations)


class CleanStyleTests(unittest.TestCase):
    def test_removes_visibility_and_opacity(self) -> None:
        cleaned = clean_style("visibility: hidden; opacity: 0; color: red")
        self.assertNotIn("visibility", cleaned)
        self.assertNotIn("opacity", cleaned)
        self.assertIn("color: red", cleaned)

    def test_display_none_only_dropped_when_requested(self) -> None:
        self.assertIn("display: none", clean_style("display: none; color: red"))
        self.assertEqual(clean_style("display: none; color: red", drop_display_none=True), "color: red")


class CleanArticleHtmlTests(unittest.TestCase):
    def test_removes_invisible_root_style(self) -> None:
        html = (
            '<div id="js_content" style="visibility: hidden; opacity: 0; color: red;">'
            "<p>正文内容</p></div>"
        )
        cleaned = clean_article_html(html, platform="wechat")
        self.assertNotIn("visibility", cleaned)
        self.assertNotIn("opacity", cleaned)
        self.assertIn("color: red", cleaned)
        self.assertIn("正文内容", cleaned)

    def test_keeps_display_none_on_nested_elements(self) -> None:
        html = (
            '<div class="rich_media_content" style="visibility: hidden; display: none;">'
            '<p>可见段落</p><p style="display: none;">注释</p></div>'
        )
        cleaned = clean_article_html(html, platform="wechat")
        self.assertNotIn("visibility", cleaned)
        self.assertEqual(cleaned.count("display: none"), 1)
        self.assertIn('style="display: none"', cleaned)
        self.assertIn("可见段落", cleaned)

    def test_removes_dangerous_tags(self) -> None:
        html = (
            '<div class="rich_media_content">'
            "<script>alert(1)</script><style>p{color:red}</style>"
            "<p>正文</p></div>"
        )
        cleaned = clean_article_html(html, platform="wechat")
        self.assertNotIn("<script", cleaned)
        self.assertNotIn("alert(1)", cleaned)
        self.assertNotIn("<style", cleaned)
        self.assertIn("正文", cleaned)

    def test_removes_tracking_attributes_and_inline_handlers(self) -> None:
        html = (
            '<div class="rich_media_content">'
            '<p data-track="1" onclick="evil()" href="javascript:void(0)">正文</p></div>'
        )
        cleaned = clean_article_html(html, platform="wechat")
        self.assertNotIn("data-track", cleaned)
        self.assertNotIn("onclick", cleaned)
        self.assertNotIn("javascript:", cleaned)
        self.assertIn("正文", cleaned)

    def test_normalizes_local_image_and_drops_lazy_attributes(self) -> None:
        html = (
            '<div id="js_content"><img src="images/abc123.jpg" '
            'data-src="https://mmbiz.qpic.cn/a.jpg" data-wxsrc="https://mmbiz.qpic.cn/a.jpg" '
            'srcset="a.jpg 2x" alt=""></div>'
        )
        cleaned = clean_article_html(html, platform="wechat")
        self.assertIn('src="images/abc123.jpg"', cleaned)
        self.assertNotIn("data-src", cleaned)
        self.assertNotIn("data-wxsrc", cleaned)
        self.assertNotIn("srcset", cleaned)
        self.assertIn('alt=""', cleaned)

    def test_uses_lazy_source_when_src_missing(self) -> None:
        html = (
            '<div id="js_content">'
            '<img data-src="https://mmbiz.qpic.cn/lazy.jpg" alt="插图"></div>'
        )
        cleaned = clean_article_html(html, platform="wechat")
        self.assertIn('src="https://mmbiz.qpic.cn/lazy.jpg"', cleaned)
        self.assertIn('referrerpolicy="no-referrer"', cleaned)
        self.assertNotIn("data-src", cleaned)

    def test_replaces_wechat_custom_media_tags_with_placeholder(self) -> None:
        html = (
            '<div id="js_content"><p>正文</p>'
            "<mpvoice></mpvoice><mp-style-type data-value=\"10000\"></mp-style-type></div>"
        )
        cleaned = clean_article_html(html, platform="wechat")
        self.assertNotIn("mpvoice", cleaned)
        self.assertNotIn("mp-style-type", cleaned)
        self.assertIn("音频内容", cleaned)


if __name__ == "__main__":
    unittest.main()
