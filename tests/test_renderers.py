"""渲染层测试：HTML 必须可见、元数据完整，Markdown frontmatter 稳定。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spider_core.models import ScrapedArticle  # noqa: E402
from spider_core.renderers import (  # noqa: E402
    build_html_doc,
    build_markdown_doc,
    detect_platform,
    render_documents,
    sanitize_filename,
)

WECHAT_URL = "https://mp.weixin.qq.com/s/SSU_GOBTHxiGQGPAF0xSHg"


def make_article(**overrides) -> ScrapedArticle:
    values = {
        "title": '测试 <标题> & "引号"',
        "html_content": "<p>正文</p>",
        "publish_time": "2026-08-27 10:00",
        "source_url": WECHAT_URL,
        "author": "作者甲",
        "account": "测试公众号",
        "description": "这是一段摘要",
    }
    values.update(overrides)
    return ScrapedArticle(**values)


class SanitizeFilenameTests(unittest.TestCase):
    def test_strips_illegal_characters(self) -> None:
        self.assertEqual(sanitize_filename('a<b>c:d"e/f\\g|h?i*j'), "abcdefghij")

    def test_replaces_whitespace_with_underscore(self) -> None:
        self.assertEqual(sanitize_filename("书籍译介 智利 实验"), "书籍译介_智利_实验")

    def test_empty_title_falls_back_to_hash(self) -> None:
        self.assertTrue(sanitize_filename("///").startswith("article_"))

    def test_hidden_or_dot_names_fall_back_to_hash(self) -> None:
        for title in (".", "..", "...", ".hidden"):
            self.assertTrue(sanitize_filename(title).startswith("article_"))

    def test_truncates_long_titles(self) -> None:
        self.assertLessEqual(len(sanitize_filename("长" * 300)), 100)


class DetectPlatformTests(unittest.TestCase):
    def test_detects_known_platforms(self) -> None:
        self.assertEqual(detect_platform(WECHAT_URL), "wechat")
        self.assertEqual(detect_platform("https://zhuanlan.zhihu.com/p/123"), "zhihu")
        self.assertEqual(detect_platform("https://example.com/post"), "web")


class BuildHtmlDocTests(unittest.TestCase):
    def test_rendered_html_makes_body_visible(self) -> None:
        article = make_article()
        content = (
            '<div id="js_content" style="visibility: hidden; opacity: 0;">'
            "<p>清洗后可见的正文</p></div>"
        )
        document = build_html_doc(article, content)
        self.assertIn("清洗后可见的正文", document)
        self.assertNotIn("visibility", document)
        self.assertNotIn("opacity: 0", document)

    def test_rendered_html_contains_metadata_and_escapes_title(self) -> None:
        document = build_html_doc(make_article(), "<div id='js_content'><p>正文</p></div>")
        self.assertIn("测试公众号", document)
        self.assertIn("作者甲", document)
        self.assertIn("2026-08-27 10:00", document)
        self.assertIn("微信公众号", document)
        self.assertIn(WECHAT_URL, document)
        self.assertIn("&lt;标题&gt;", document)
        self.assertIn("这是一段摘要", document)
        self.assertIn('class="article-content"', document)

    def test_remote_images_get_no_referrer(self) -> None:
        document = build_html_doc(
            make_article(), '<div id="js_content"><img data-src="https://mmbiz.qpic.cn/a.jpg"></div>'
        )
        self.assertIn('src="https://mmbiz.qpic.cn/a.jpg"', document)
        self.assertIn('referrerpolicy="no-referrer"', document)

    def test_article_reading_style_is_embedded(self) -> None:
        document = build_html_doc(make_article(), "<div id='js_content'><p>正文</p></div>")
        self.assertIn("<style>", document)
        self.assertIn("max-width: 720px", document)
        self.assertIn('charset="UTF-8"', document)


class BuildMarkdownDocTests(unittest.TestCase):
    def test_frontmatter_contains_expected_fields(self) -> None:
        markdown = build_markdown_doc(make_article(), "<p>正文</p>")
        self.assertTrue(markdown.startswith("---\n"))
        self.assertIn('title: "测试 <标题> & \\"引号\\""', markdown)
        self.assertIn('date: "2026-08-27 10:00"', markdown)
        self.assertIn(f'source: "{WECHAT_URL}"', markdown)
        self.assertIn("platform: wechat", markdown)
        self.assertIn("status: inbox", markdown)
        self.assertIn("  - wechat", markdown)
        self.assertIn("正文", markdown)

    def test_date_omitted_when_publish_time_empty(self) -> None:
        markdown = build_markdown_doc(make_article(publish_time=""), "<p>正文</p>")
        self.assertNotIn("\ndate:", markdown)

    def test_wikilink_image_style(self) -> None:
        content = '<p><img src="images/abc.jpg" alt="插图"></p>'
        relative = build_markdown_doc(make_article(), content)
        self.assertIn("![插图](images/abc.jpg)", relative)
        wikilink = build_markdown_doc(make_article(), content, image_links="wikilink")
        self.assertIn("![[images/abc.jpg]]", wikilink)


class RenderDocumentsTests(unittest.TestCase):
    def test_renders_both_formats_in_order(self) -> None:
        documents = render_documents(make_article(), "<p>正文</p>", ["md", "html"])
        self.assertEqual([extension for extension, _ in documents], [".md", ".html"])

    def test_unknown_format_raises(self) -> None:
        with self.assertRaises(ValueError):
            render_documents(make_article(), "<p>正文</p>", ["pdf"])


if __name__ == "__main__":
    unittest.main()
