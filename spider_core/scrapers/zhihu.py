from __future__ import annotations

import sys

from bs4 import BeautifulSoup

from ..http import retry_request
from ..models import ScrapedArticle
from .base import AbstractScraper


class ZhihuScraper(AbstractScraper):
    def match(self, url: str) -> bool:
        return "zhuanlan.zhihu.com" in url or "www.zhihu.com/question" in url

    def scrape(self, url: str) -> ScrapedArticle | None:
        response = retry_request(url)
        if response is None:
            return None

        soup = BeautifulSoup(response.text, "html.parser")

        title_tag = soup.find("h1", class_="Post-Title")
        title = title_tag.get_text(strip=True) if title_tag else "未知标题"

        content_div = soup.find("div", class_="Post-RichText")
        if not content_div:
            print("未找到知乎文章内容区域。", file=sys.stderr)
            return None

        for tag in content_div(["script", "style", "noscript"]):
            tag.decompose()

        return ScrapedArticle(
            title=title,
            html_content=str(content_div),
            publish_time="",
            source_url=url,
        )
