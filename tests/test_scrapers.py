"""抓取层测试：URL 分发、微信元数据、知乎专栏/问题页与解析失败。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spider_core.errors import ParseError  # noqa: E402
from spider_core.scrapers import SCRAPERS, find_scraper, supported_scraper_names  # noqa: E402
from spider_core.scrapers.wechat import WeChatScraper  # noqa: E402
from spider_core.scrapers.zhihu import ZhihuScraper  # noqa: E402

WECHAT_URL = "https://mp.weixin.qq.com/s/abc"
ZHIHU_COLUMN_URL = "https://zhuanlan.zhihu.com/p/123"
ZHIHU_QUESTION_URL = "https://www.zhihu.com/question/456/answer/789"

WECHAT_PAGE = """
<html><head>
  <meta property="og:title" content="og 标题">
  <meta property="og:description" content="摘要">
</head><body>
  <h1 class="rich_media_title">文章标题</h1>
  <em id="publish_time" class="rich_media_meta rich_media_meta_text"></em>
  <div id="js_name">测试公众号</div>
  <div class="rich_media_content" style="visibility: hidden; opacity: 0;">
    <p>正文</p><script>alert(1)</script>
  </div>
  <script>
    var ct = "1787824800";
    var nickname = "测试公众号";
    var author = "作者甲";
  </script>
</body></html>
"""

ZHIHU_COLUMN_PAGE = """
<html><head><meta property="og:description" content="知乎摘要"></head><body>
  <h1 class="Post-Title">专栏标题</h1>
  <div class="ContentItem-time">2026-08-27 10:00</div>
  <span class="AuthorInfo-name">作者乙</span>
  <div class="Post-RichText"><p>正文</p></div>
</body></html>
"""

ZHIHU_QUESTION_PAGE = """
<html><head>
  <meta itemprop="dateModified" content="2026-08-27T10:00:00+08:00">
  <meta property="og:description" content="问题摘要">
</head><body>
  <h1 class="QuestionHeader-title">问题标题</h1>
  <span class="AuthorInfo-name">答主丙</span>
  <div class="RichContent-inner"><p>回答正文</p></div>
</body></html>
"""


class FakeResponse:
    def __init__(self, text: str):
        self.text = text


def patched_request(module: str, text: str):
    return mock.patch(f"spider_core.scrapers.{module}.retry_request", return_value=FakeResponse(text))


class FindScraperTests(unittest.TestCase):
    def test_dispatches_by_url(self) -> None:
        self.assertIsInstance(find_scraper(WECHAT_URL), WeChatScraper)
        self.assertIsInstance(find_scraper(ZHIHU_COLUMN_URL), ZhihuScraper)
        self.assertIsInstance(find_scraper(ZHIHU_QUESTION_URL), ZhihuScraper)

    def test_unknown_url_returns_none(self) -> None:
        self.assertIsNone(find_scraper("https://example.com/post"))

    def test_supported_scraper_names(self) -> None:
        names = supported_scraper_names()
        self.assertIn("wechat", names)
        self.assertIn("zhihu", names)
        self.assertEqual(len(SCRAPERS), 2)


class WeChatScraperTests(unittest.TestCase):
    def test_extracts_article_and_metadata(self) -> None:
        with patched_request("wechat", WECHAT_PAGE):
            article = WeChatScraper().scrape(WECHAT_URL)

        self.assertEqual(article.title, "文章标题")
        self.assertEqual(article.account, "测试公众号")
        self.assertEqual(article.author, "作者甲")
        self.assertNotEqual(article.publish_time, "")
        self.assertIn("正文", article.html_content)
        self.assertNotIn("<script", article.html_content)

    def test_raises_parse_error_without_content(self) -> None:
        html = "<html><body><h1 class='rich_media_title'>t</h1></body></html>"
        with patched_request("wechat", html):
            with self.assertRaises(ParseError):
                WeChatScraper().scrape(WECHAT_URL)


class ZhihuScraperTests(unittest.TestCase):
    def test_scrapes_column_article(self) -> None:
        with patched_request("zhihu", ZHIHU_COLUMN_PAGE):
            article = ZhihuScraper().scrape(ZHIHU_COLUMN_URL)

        self.assertEqual(article.title, "专栏标题")
        self.assertEqual(article.account, "知乎")
        self.assertEqual(article.author, "作者乙")
        self.assertIn("正文", article.html_content)

    def test_scrapes_question_page(self) -> None:
        with patched_request("zhihu", ZHIHU_QUESTION_PAGE):
            article = ZhihuScraper().scrape(ZHIHU_QUESTION_URL)

        self.assertEqual(article.title, "问题标题")
        self.assertEqual(article.author, "答主丙")
        self.assertIn("回答正文", article.html_content)
        self.assertIn("2026-08-27", article.publish_time)

    def test_raises_parse_error_without_content(self) -> None:
        html = "<html><body><h1 class='Post-Title'>t</h1></body></html>"
        with patched_request("zhihu", html):
            with self.assertRaises(ParseError):
                ZhihuScraper().scrape(ZHIHU_COLUMN_URL)


if __name__ == "__main__":
    unittest.main()
