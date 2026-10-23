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

#: 「图片消息 / 分享页」的特征：正文容器不存在，文章信息和图片列表在 cgiDataNew 里
IMAGE_SHARE_MARKERS = ("picture_page_info_list", "share_content_page")
JS_OBJECT_STRING_PATTERN = r"\b{key}\s*:\s*'((?:[^'\\]|\\.)*)'"
FORMATTED_TIME_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}")
CDN_URL_PATTERN = re.compile(r"cdn_url:\s*'((?:[^'\\]|\\.)*)'")


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


def _unescape_js_string(value: str) -> str:
    """还原 JS 字符串里的转义，例如 ``\\x0a`` -> 换行、``\\x26amp;`` -> ``&amp;``。"""
    value = (
        value.replace("\\x0a", "\n")
        .replace("\\x0d", "\r")
        .replace("\\x26", "&")
        .replace("\\/", "/")
        .replace("\\'", "'")
        .replace('\\"', '"')
    )
    return html_lib.unescape(value)


def _js_object_string(raw_html: str, key: str) -> str:
    """提取 JS 对象字面量里的字符串字段，例如 ``nick_name: 'xxx'``。"""
    match = re.search(JS_OBJECT_STRING_PATTERN.format(key=re.escape(key)), raw_html)
    return _unescape_js_string(match.group(1)).strip() if match else ""


def _js_array_block(raw_html: str, key: str) -> str:
    """截取 ``key: [ ... ]`` 的方括号块（跳过字符串里的括号）。"""
    start = raw_html.find(f"{key}:")
    if start < 0:
        return ""
    array_start = raw_html.find("[", start)
    if array_start < 0 or array_start > start + 40:
        return ""

    depth = 0
    quote = ""
    index = array_start
    while index < len(raw_html):
        char = raw_html[index]
        if quote:
            if char == "\\":
                index += 2
                continue
            if char == quote:
                quote = ""
        elif char in "'\"":
            quote = char
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return raw_html[array_start : index + 1]
        index += 1
    return ""


def _format_timestamp(value: str) -> str:
    if not value.isdigit() or len(value) < 10:
        return ""
    try:
        return datetime.fromtimestamp(int(value)).strftime("%Y-%m-%d %H:%M")
    except (OverflowError, OSError, ValueError):
        return ""


def _image_share_urls(raw_html: str) -> list[str]:
    block = _js_array_block(raw_html, "picture_page_info_list")
    if not block:
        return []

    urls: list[str] = []
    for raw_url in CDN_URL_PATTERN.findall(block):
        url = _unescape_js_string(raw_url)
        if url and url not in urls:
            urls.append(url)
    return urls


def _build_image_share_html(description: str, image_urls: list[str]) -> str:
    lines = ['<section class="wechat-image-share">']
    for paragraph in description.splitlines():
        text = paragraph.strip()
        if text:
            lines.append(f"<p>{html_lib.escape(text)}</p>")
    for position, url in enumerate(image_urls, start=1):
        lines.append(f'<p><img data-src="{html_lib.escape(url)}" alt="图片 {position}" /></p>')
    lines.append("</section>")
    return "\n".join(lines)


def _image_share_html(soup: BeautifulSoup, raw_html: str) -> str:
    """图片消息/分享页没有 rich_media_content，正文用摘要 + 图片列表重建。"""
    if not any(marker in raw_html for marker in IMAGE_SHARE_MARKERS):
        return ""

    description = _js_object_string(raw_html, "content_noencode") or _meta_content(
        soup, "og:description"
    )
    image_urls = _image_share_urls(raw_html)
    if not description and not image_urls:
        return ""
    return _build_image_share_html(description, image_urls)


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
    if not publish_time:
        object_time = _js_object_string(raw_html, "create_time")
        if FORMATTED_TIME_PATTERN.fullmatch(object_time):
            publish_time = object_time

    account = (
        _text(soup, "#js_name")
        or _text(soup, ".rich_media_meta_nickname")
        or _js_string_variable(raw_html, "nickname")
        or _js_object_string(raw_html, "nick_name")
        or _meta_content(soup, "og:article:author")
    )
    author = _js_string_variable(raw_html, "author") or _meta_content(soup, "author")
    description = (
        _meta_content(soup, "og:description")
        or _meta_content(soup, "description")
        or _js_object_string(raw_html, "content_noencode")
    )
    description = _unescape_js_string(description)

    return {
        "publish_time": publish_time,
        "account": account,
        "author": author,
        "description": description,
    }


class WeChatScraper(AbstractScraper):
    def match(self, url: str) -> bool:
        return "mp.weixin.qq.com" in url

    def scrape(self, url: str, cookie: str | None = None) -> ScrapedArticle:
        response = retry_request(url, cookie=cookie)

        raw_html = response.text
        soup = BeautifulSoup(raw_html, "html.parser")

        title = (
            _text(soup, "h1.rich_media_title")
            or _meta_content(soup, "og:title")
            or _js_string_variable(raw_html, "msg_title")
            or _js_object_string(raw_html, "title")
            or "未知标题"
        )

        metadata = extract_metadata(soup, raw_html)
        content_div = soup.find("div", class_="rich_media_content") or soup.find(id="js_content")

        if content_div:
            for tag in content_div(["script", "style", "iframe"]):
                tag.decompose()
            html_content = str(content_div)
        else:
            html_content = _image_share_html(soup, raw_html)
            if not html_content:
                raise ParseError(
                    "未找到微信公众号正文容器（rich_media_content 不存在，"
                    "文章可能已删除、需要验证，或是不支持的页面类型）。"
                )

        return ScrapedArticle(
            title=title,
            html_content=html_content,
            publish_time=metadata["publish_time"],
            source_url=url,
            author=metadata["author"],
            account=metadata["account"],
            description=metadata["description"],
        )
