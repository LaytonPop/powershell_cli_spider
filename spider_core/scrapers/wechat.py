from __future__ import annotations

import logging

from bs4 import BeautifulSoup

from ..errors import ParseError
from ..http import retry_request
from ..models import ScrapedArticle
from .base import AbstractScraper

logger = logging.getLogger(__name__)


class WeChatScraper(AbstractScraper):
    def match(self, url: str) -> bool:
        return "mp.weixin.qq.com" in url

    def scrape(self, url: str) -> ScrapedArticle:
        response = retry_request(url)
        soup = BeautifulSoup(response.text, "html.parser")

        title_tag = soup.find("h1", class_="rich_media_title")
        title = title_tag.get_text(strip=True) if title_tag else "未知标题"

        content_div = soup.find("div", class_="rich_media_content")
        if not content_div:
            raise ParseError("未找到微信公众号文章内容区域（rich_media_content 不存在，文章可能已删除或需要验证）。")

        publish_time = ""
        meta_tag = soup.find("em", class_="rich_media_meta rich_media_meta_text")
        if meta_tag:
            publish_time = meta_tag.get_text(strip=True)
        if not publish_time:
            time_tag = soup.find("em", id="publish_time")
            if time_tag:
                publish_time = time_tag.get_text(strip=True)

        for tag in content_div(["script", "style", "iframe"]):
            tag.decompose()

        return ScrapedArticle(
            title=title,
            html_content=str(content_div),
            publish_time=publish_time,
            source_url=url,
        )
