"""微信元数据提取测试：发布时间在 JS 变量里，公众号名在 nickname 变量里。"""

from __future__ import annotations

import sys
import unittest
from datetime import datetime
from pathlib import Path

from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spider_core.scrapers.wechat import extract_metadata  # noqa: E402


def expected_time(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M")


class WeChatMetadataTests(unittest.TestCase):
    def test_extracts_timestamp_from_ct_variable(self) -> None:
        raw_html = """
        <html><head>
        <meta property="og:description" content="摘要内容">
        </head><body>
        <em id="publish_time" class="rich_media_meta rich_media_meta_text"></em>
        <script>
        var ct = "1787824800";
        var nickname = htmlDecode("民主经济计划评论DEPR");
        var author = "";
        </script>
        </body></html>
        """
        soup = BeautifulSoup(raw_html, "html.parser")
        metadata = extract_metadata(soup, raw_html)
        self.assertEqual(metadata["publish_time"], expected_time(1787824800))
        self.assertEqual(metadata["account"], "民主经济计划评论DEPR")
        self.assertEqual(metadata["author"], "")
        self.assertEqual(metadata["description"], "摘要内容")

    def test_create_time_variable_is_fallback(self) -> None:
        raw_html = '<html><body><script>var create_time = "1700000000";</script></body></html>'
        soup = BeautifulSoup(raw_html, "html.parser")
        metadata = extract_metadata(soup, raw_html)
        self.assertEqual(metadata["publish_time"], expected_time(1700000000))

    def test_empty_second_level_time_does_not_break_fallback(self) -> None:
        raw_html = """
        <html><body>
        <em id="publish_time" class="rich_media_meta rich_media_meta_text">  </em>
        <script>var create_time = "1700000000";</script>
        </body></html>
        """
        soup = BeautifulSoup(raw_html, "html.parser")
        metadata = extract_metadata(soup, raw_html)
        self.assertEqual(metadata["publish_time"], expected_time(1700000000))

    def test_non_numeric_timestamp_is_ignored(self) -> None:
        raw_html = '<html><body><script>var ct = "not-a-time";</script></body></html>'
        soup = BeautifulSoup(raw_html, "html.parser")
        metadata = extract_metadata(soup, raw_html)
        self.assertEqual(metadata["publish_time"], "")

    def test_account_from_og_author_when_variable_missing(self) -> None:
        raw_html = """
        <html><head>
        <meta property="og:article:author" content="某公众号">
        </head><body></body></html>
        """
        soup = BeautifulSoup(raw_html, "html.parser")
        metadata = extract_metadata(soup, raw_html)
        self.assertEqual(metadata["account"], "某公众号")

    def test_description_escaped_newlines_are_decoded(self) -> None:
        raw_html = """
        <html><head>
        <meta property="og:description" content="第一行\\x0a第二行">
        </head><body></body></html>
        """
        soup = BeautifulSoup(raw_html, "html.parser")
        metadata = extract_metadata(soup, raw_html)
        self.assertEqual(metadata["description"], "第一行\n第二行")


if __name__ == "__main__":
    unittest.main()
