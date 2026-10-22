from __future__ import annotations

import re

from bs4 import BeautifulSoup

from ..errors import ParseError
from ..http import retry_request
from ..models import ScrapedArticle
from .base import AbstractScraper


def _meta_content(soup: BeautifulSoup, key: str) -> str:
    tag = (
        soup.find("meta", attrs={"property": key})
        or soup.find("meta", attrs={"name": key})
        or soup.find("meta", attrs={"itemprop": key})
    )
    if tag is None:
        return ""
    return (tag.get("content") or "").strip()


def _text(soup: BeautifulSoup, selector: str) -> str:
    tag = soup.select_one(selector)
    return tag.get_text(strip=True) if tag else ""


class ZhihuScraper(AbstractScraper):
    #: /question/<id> 及其子路径（答案、关注者等）
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
        """知乎专栏文章页（zhuanlan.zhihu.com/p/<id>）。"""
        title = _text(soup, "h1.Post-Title") or _meta_content(soup, "og:title") or "未知标题"

        content_div = soup.find("div", class_="Post-RichText")
        if not content_div:
            raise ParseError("未找到知乎文章内容区域（Post-RichText 不存在，页面结构可能已变化）。")

        publish_time = _text(soup, ".ContentItem-time")
        if not publish_time:
            publish_time = _meta_content(soup, "datePublished")

        author = _text(soup, ".AuthorInfo-name") or _meta_content(soup, "author")
        description = _meta_content(soup, "og:description") or _meta_content(soup, "description")

        for tag in content_div(["script", "style", "noscript"]):
            tag.decompose()

        return ScrapedArticle(
            title=title,
            html_content=str(content_div),
            publish_time=publish_time,
            source_url=url,
            author=author,
            account="知乎",
            description=description,
        )

    def _scrape_question(self, soup: BeautifulSoup, url: str) -> ScrapedArticle:
        """知乎问题页：抓问题标题 + 首个高赞回答。"""
        title = _text(soup, "h1.QuestionHeader-title") or _meta_content(soup, "og:title") or "未知标题"

        content_div = (
            soup.find("div", class_="RichContent-inner")
            or soup.find("div", class_="AnswerCard")
            or soup.find("div", class_="RichContent")
        )
        if not content_div:
            raise ParseError(
                "未找到知乎问题回答内容区域（RichContent 不存在，页面结构可能已变化）。"
            )

        publish_time = _meta_content(soup, "dateModified")
        author = _text(soup, ".AuthorInfo-name") or _meta_content(soup, "author")
        description = _meta_content(soup, "og:description") or _meta_content(soup, "description")

        for tag in content_div(["script", "style", "noscript"]):
            tag.decompose()

        return ScrapedArticle(
            title=title,
            html_content=str(content_div),
            publish_time=publish_time,
            source_url=url,
            author=author,
            account="知乎",
            description=description,
        )
