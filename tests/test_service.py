"""服务层测试：保存、跳过、重名去重与错误传播。"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spider_core.errors import ParseError, UnsupportedURLError  # noqa: E402
from spider_core.models import ScrapedArticle  # noqa: E402
from spider_core.service import save_article, scrape_article  # noqa: E402

URL = "https://mp.weixin.qq.com/s/abc"


def make_article(**overrides) -> ScrapedArticle:
    values = {
        "title": "测试文章",
        "html_content": (
            '<div class="rich_media_content" style="visibility: hidden; opacity: 0;">'
            "<p>正文</p></div>"
        ),
        "publish_time": "2026-08-27 10:00",
        "source_url": URL,
        "author": "作者",
        "account": "公众号",
        "description": "摘要",
    }
    values.update(overrides)
    return ScrapedArticle(**values)


class SaveArticleTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.out = Path(self._tmp.name)

        patcher = mock.patch(
            "spider_core.service.download_and_rewrite_images",
            side_effect=lambda html, base_url, img_dir: html,
        )
        self.addCleanup(patcher.stop)
        self.download = patcher.start()

    def _save(self, article: ScrapedArticle | None = None, **kwargs):
        article = article or make_article()
        with mock.patch("spider_core.service.scrape_article", return_value=article):
            return save_article(URL, self.out, **kwargs)

    def test_writes_markdown_by_default(self) -> None:
        result = self._save()

        self.assertTrue(result.ok)
        self.assertEqual(len(result.files), 1)
        self.assertEqual(result.files[0].name, "测试文章.md")
        content = result.files[0].read_text(encoding="utf-8")
        self.assertIn('title: "测试文章"', content)
        self.assertIn('date: "2026-08-27 10:00"', content)

    def test_writes_both_formats(self) -> None:
        result = self._save(output_formats=["md", "html"])

        self.assertTrue(result.ok)
        self.assertEqual(sorted(path.name for path in result.files), ["测试文章.html", "测试文章.md"])
        html_path = next(path for path in result.files if path.suffix == ".html")
        html = html_path.read_text(encoding="utf-8")
        self.assertIn("<!DOCTYPE html>", html)

    def test_skip_existing_skips_without_downloading(self) -> None:
        first = self._save()
        self.assertTrue(first.ok)

        self.download.reset_mock()
        second = self._save(skip_existing=True)

        self.assertTrue(second.skipped)
        self.assertFalse(second.ok)
        self.download.assert_not_called()

    def test_duplicate_title_gets_suffix(self) -> None:
        first = self._save()
        second = self._save()

        self.assertTrue(first.ok and second.ok)
        self.assertEqual(second.files[0].parent.name, "测试文章_2")
        self.assertTrue((self.out / "测试文章" / "测试文章.md").is_file())
        self.assertTrue((self.out / "测试文章_2" / "测试文章_2.md").is_file())

    def test_parse_error_is_returned_not_raised(self) -> None:
        with mock.patch("spider_core.service.scrape_article", side_effect=ParseError("解析失败")):
            result = save_article(URL, self.out)

        self.assertFalse(result.ok)
        self.assertIn("解析失败", result.error)

    def test_unknown_format_is_rejected_before_scraping(self) -> None:
        with mock.patch("spider_core.service.scrape_article") as scrape:
            result = save_article(URL, self.out, output_formats=["pdf"])

        self.assertFalse(result.ok)
        self.assertIn("未知输出格式", result.error)
        scrape.assert_not_called()
        self.assertEqual(list(self.out.iterdir()), [])


class ScrapeArticleTests(unittest.TestCase):
    def test_unsupported_url_raises(self) -> None:
        with self.assertRaises(UnsupportedURLError):
            scrape_article("https://example.com/post")


if __name__ == "__main__":
    unittest.main()
