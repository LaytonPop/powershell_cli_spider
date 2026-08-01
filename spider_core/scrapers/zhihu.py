from __future__ import annotations

import logging
import re

from bs4 import BeautifulSoup

from ..errors import ParseError
from ..http import retry_request
from ..models import ScrapedArticle
from .base import AbstractScraper

logger = logging.getLogger(__name__)


class ZhihuScraper(AbstractScraper):
    # /question/<id> with or without trailing path segments (answers, followers, ...)
    QUESTION_URL_RE = re.compile(r"zhihu\.com/question/\d+")

    def match(self, url: str) -> bool:
        return "zhuanlan.zhihu.com" in url or self.QUESTION_URL_RE.search(url) is not None

    def scrape(self, url: str) -> ScrapedArticle:
        response = retry_request(url)
        soup = BeautifulSoup(response.text, "html.parser")

        if self.QUESTION_URL_RE.search(url):
            return self._scrape_question(soup, url)

        return self._scrape_column(soup, url)

    def _scrape_column(self, soup: BeautifulSoup, url: str) -> ScrapedArticle:
        """Zhihu column / article page (zhuanlan.zhihu.com/p/<id>)."""
        title_tag = soup.find("h1", class_="Post-Title")
        title = title_tag.get_text(strip=True) if title_tag else "未知标题"

        content_div = soup.find("div", class_="Post-RichText")
        if not content_div:
            raise ParseError("未找到知乎文章内容区域（Post-RichText 不存在，页面结构可能已变化）。")

        publish_time = ""
        time_tag = soup.find("div", class_="ContentItem-time")
        if time_tag:
            publish_time = time_tag.get_text(strip=True)
        if not publish_time:
            meta_time = soup.find("meta", {"itemprop": "datePublished"})
            if meta_time and meta_time.get("content"):
                publish_time = meta_time["content"]

        for tag in content_div(["script", "style", "noscript"]):
            tag.decompose()

        return ScrapedArticle(
            title=title,
            html_content=str(content_div),
            publish_time=publish_time,
            source_url=url,
        )

    def _scrape_question(self, soup: BeautifulSoup, url: str) -> ScrapedArticle:
        """Zhihu question page — scrape the question title + top answer."""
        title_tag = soup.find("h1", class_="QuestionHeader-title")
        title = title_tag.get_text(strip=True) if title_tag else "未知标题"

        # Top answer body (current Zhihu DOM); fall back to the first answer card.
        content_div = (
            soup.find("div", class_="RichContent-inner")
            or soup.find("div", class_="AnswerCard")
            or soup.find("div", class_="RichContent")
        )
        if not content_div:
            raise ParseError("未找到知乎问题回答内容区域（RichContent 不存在，页面结构可能已变化）。")

        publish_time = ""
        meta_time = soup.find("meta", {"itemprop": "dateModified"})
        if meta_time and meta_time.get("content"):
            publish_time = meta_time["content"]

        for tag in content_div(["script", "style", "noscript"]):
            tag.decompose()

        return ScrapedArticle(
            title=title,
            html_content=str(content_div),
            publish_time=publish_time,
            source_url=url,
        )
