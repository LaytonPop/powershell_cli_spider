from __future__ import annotations

import html as html_lib
import re
from datetime import datetime

from bs4 import BeautifulSoup

from ..errors import ParseError
from ..http import retry_request
from ..models import ScrapedArticle
from .base import AbstractScraper

#: 微信把发布时间写在 JS 变量里（页面上的 #publish_time 常为空，靠 JS 填充）
TIMESTAMP_VARIABLES = ("ct", "create_time")


def _meta_content(soup: BeautifulSoup, key: str) -> str:
    tag = soup.find("meta", attrs={"property": key}) or soup.find("meta", attrs={"name": key})
    if tag is None:
        return ""
    return (tag.get("content") or "").strip()


def _text(soup: BeautifulSoup, selector: str) -> str:
    tag = soup.select_one(selector)
    return tag.get_text(strip=True) if tag else ""


def _js_string_variable(raw_html: str, name: str) -> str:
    """提取 ``var name = "..."`` / ``var name = htmlDecode("...")`` 的值。"""
    pattern = rf"""var\s+{re.escape(name)}\s*=\s*(?:htmlDecode\()?["']([^"']*)["']\)?"""
    match = re.search(pattern, raw_html)
    if not match:
        return ""
    return html_lib.unescape(match.group(1)).strip()


def _format_timestamp(value: str) -> str:
    if not value.isdigit() or len(value) < 10:
        return ""
    try:
        return datetime.fromtimestamp(int(value)).strftime("%Y-%m-%d %H:%M")
    except (OverflowError, OSError, ValueError):
        return ""


def extract_metadata(soup: BeautifulSoup, raw_html: str) -> dict[str, str]:
    """从微信页面提取发布时间、公众号名、作者和摘要。"""
    publish_time = _text(soup, "#publish_time")
    if not publish_time:
        publish_time = _text(soup, "em.rich_media_meta.rich_media_meta_text")
    if not publish_time:
        for variable in TIMESTAMP_VARIABLES:
            publish_time = _format_timestamp(_js_string_variable(raw_html, variable))
            if publish_time:
                break

    account = (
        _text(soup, "#js_name")
        or _text(soup, ".rich_media_meta_nickname")
        or _js_string_variable(raw_html, "nickname")
        or _meta_content(soup, "og:article:author")
    )
    author = _js_string_variable(raw_html, "author") or _meta_content(soup, "author")
    description = _meta_content(soup, "og:description") or _meta_content(soup, "description")

    return {
        "publish_time": publish_time,
        "account": account,
        "author": author,
        "description": description,
    }


class WeChatScraper(AbstractScraper):
    def match(self, url: str) -> bool:
        return "mp.weixin.qq.com" in url

    def scrape(self, url: str) -> ScrapedArticle:
        response = retry_request(url)

        raw_html = response.text
        soup = BeautifulSoup(raw_html, "html.parser")

        title = _text(soup, "h1.rich_media_title") or _meta_content(soup, "og:title")
        if not title:
            title = _js_string_variable(raw_html, "msg_title") or "未知标题"

        content_div = soup.find("div", class_="rich_media_content") or soup.find(id="js_content")
        if not content_div:
            raise ParseError(
                "未找到微信公众号文章内容区域（rich_media_content 不存在，"
                "文章可能已删除或需要验证）。"
            )

        for tag in content_div(["script", "style", "iframe"]):
            tag.decompose()

        metadata = extract_metadata(soup, raw_html)

        return ScrapedArticle(
            title=title,
            html_content=str(content_div),
            publish_time=metadata["publish_time"],
            source_url=url,
            author=metadata["author"],
            account=metadata["account"],
            description=metadata["description"],
        )
