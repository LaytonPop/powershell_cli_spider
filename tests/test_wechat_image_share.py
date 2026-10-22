"""微信「图片消息 / 分享页」抓取测试。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spider_core.errors import ParseError  # noqa: E402
from spider_core.scrapers.wechat import WeChatScraper  # noqa: E402

IMAGE_SHARE_HTML = """
<html><head>
<meta property="og:title" content="Jev-Mem？测试图片消息">
<meta property="og:description" content="摘要第一行">
</head><body>
<div class="share_content_page" id="js_article"></div>
<script>
  (function() {
    window.cgiDataNew = {
      nick_name: 'EasyShip.AI',
      create_time: '2026-10-12 18:44',
      title: 'Jev-Mem？测试图片消息',
      content_noencode: '摘要第一行\\x0a摘要第二行',
      picture_page_info_list: [
        {
          cdn_url: 'https://mmbiz.qpic.cn/sz_mmbiz_png/aaa/0?wx_fmt=png\\x26amp;from=appmsg',
          width: '1242' * 1,
        },
        {
          cdn_url: 'https://mmbiz.qpic.cn/sz_mmbiz_jpg/bbb/0?wx_fmt=jpeg',
          width: '1242' * 1,
        },
      ],
    };
  })();
</script>
</body></html>
"""

NORMAL_ARTICLE_HTML = """
<html><head>
<meta property="og:title" content="普通图文">
</head><body>
<h1 class="rich_media_title">普通图文</h1>
<div class="rich_media_content" id="js_content"><p>正文第一段</p></div>
</body></html>
"""

EMPTY_PAGE_HTML = "<html><body><div>该内容已删除</div></body></html>"


class FakeResponse:
    def __init__(self, text: str) -> None:
        self.text = text


class WeChatImageShareTests(unittest.TestCase):
    def _scrape(self, raw_html: str):
        with mock.patch(
            "spider_core.scrapers.wechat.retry_request",
            return_value=FakeResponse(raw_html),
        ):
            return WeChatScraper().scrape("https://mp.weixin.qq.com/s/example")

    def test_image_share_page_is_rebuilt_from_summary_and_images(self) -> None:
        article = self._scrape(IMAGE_SHARE_HTML)

        self.assertEqual(article.title, "Jev-Mem？测试图片消息")
        self.assertEqual(article.account, "EasyShip.AI")
        self.assertEqual(article.publish_time, "2026-10-12 18:44")
        self.assertEqual(article.description, "摘要第一行")
        self.assertIn("摘要第二行", article.html_content)
        self.assertEqual(article.html_content.count("<img"), 2)
        self.assertIn("https://mmbiz.qpic.cn/sz_mmbiz_png/aaa/0?wx_fmt=png&amp;from=appmsg", article.html_content)

    def test_normal_article_still_uses_rich_media_content(self) -> None:
        article = self._scrape(NORMAL_ARTICLE_HTML)

        self.assertEqual(article.title, "普通图文")
        self.assertIn("正文第一段", article.html_content)
        self.assertNotIn("wechat-image-share", article.html_content)

    def test_unknown_page_raises_parse_error(self) -> None:
        with self.assertRaises(ParseError):
            self._scrape(EMPTY_PAGE_HTML)


if __name__ == "__main__":
    unittest.main()
