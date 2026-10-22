"""洗白抓下来的文章正文，让它离线打开时是可见、可读的。

微信文章把正文容器写成 ``visibility: hidden; opacity: 0``，直接原样保存会让
浏览器里只剩标题、正文一片空白；本模块在渲染前统一清理这类“不可见”内联样式，
同时处理懒加载图片、微信自定义标签和追踪属性。清洗只做“去掉坏样式”，
不会重写正文自身的富文本内联样式。
"""

from __future__ import annotations

from bs4 import BeautifulSoup, Tag

#: 完全移除的标签：脚本、样式、内嵌框架、广告位等
DANGEROUS_TAGS = ("script", "style", "iframe", "object", "embed", "noscript", "ins")

#: 微信自定义标签 -> 离线可读的占位文案（空字符串表示直接删除）
CUSTOM_ELEMENT_FALLBACKS: dict[str, str] = {
    "mp-style-type": "",
    "mpvoice": "［音频内容，需在微信中查看］",
    "mp-common-mpaudio": "［音频内容，需在微信中查看］",
    "qqmusic": "［音乐内容，需在微信中查看］",
    "mp-common-videosnap": "［视频内容，需在微信中查看］",
    "mp-common-profile": "［公众号名片］",
    "mp-miniprogram": "［小程序内容］",
}

#: 图片懒加载属性，按优先级尝试
LAZY_IMAGE_ATTRIBUTES = ("data-src", "data-wxsrc", "data-original-src", "data-lazy-src")

#: 这些 data-* 属性在清洗后保留；其余视为追踪/冗余属性移除
KEEP_DATA_ATTRIBUTES = frozenset(
    {"data-type", "data-src", "data-wxsrc", "data-original-src", "data-lazy-src"}
)

LOCAL_IMAGE_PREFIX = "images/"


def split_style_declarations(style: str) -> list[str]:
    """按分号拆分内联样式，忽略 url(...) / 引号里的分号。"""
    declarations: list[str] = []
    buffer: list[str] = []
    depth = 0
    quote = ""
    for char in style:
        if quote:
            buffer.append(char)
            if char == quote:
                quote = ""
            continue
        if char in ("'", '"'):
            quote = char
            buffer.append(char)
            continue
        if char == "(":
            depth += 1
        elif char == ")":
            depth = max(depth - 1, 0)
        if char == ";" and depth == 0:
            declarations.append("".join(buffer).strip())
            buffer = []
            continue
        buffer.append(char)
    tail = "".join(buffer).strip()
    if tail:
        declarations.append(tail)
    return [item for item in declarations if item]


def clean_style(style: str, drop_display_none: bool = False) -> str:
    """删除会让正文不可见的声明，保留其余内联样式。"""
    kept: list[str] = []
    for declaration in split_style_declarations(style):
        name, _, value = declaration.partition(":")
        property_name = name.strip().lower()
        if property_name in ("visibility", "opacity"):
            continue
        if drop_display_none and property_name == "display" and value.strip().lower() == "none":
            continue
        kept.append(declaration)
    return "; ".join(kept)


def _is_content_root(element: Tag, soup: BeautifulSoup) -> bool:
    """判断元素是否是正文根节点（微信用 #js_content / .rich_media_content）。"""
    if element.parent is soup or element.parent is None:
        return True
    if element.get("id") == "js_content":
        return True
    classes = element.get("class") or []
    return "rich_media_content" in classes


def _remove_dangerous_nodes(soup: BeautifulSoup) -> None:
    for tag_name in DANGEROUS_TAGS:
        for element in soup.find_all(tag_name):
            element.decompose()


def _replace_custom_elements(soup: BeautifulSoup) -> None:
    for tag_name, fallback in CUSTOM_ELEMENT_FALLBACKS.items():
        for element in soup.find_all(tag_name):
            if element.parent is None:
                continue
            if not fallback:
                element.decompose()
                continue
            placeholder = soup.new_tag("p")
            placeholder["class"] = "mp-foreign-content"
            placeholder.string = fallback
            element.replace_with(placeholder)


def _normalize_images(soup: BeautifulSoup) -> None:
    for image in soup.find_all("img"):
        if image.parent is None:
            continue
        source = (image.get("src") or "").strip()
        if not source or source.startswith("data:"):
            source = ""
            for attribute in LAZY_IMAGE_ATTRIBUTES:
                candidate = (image.get(attribute) or "").strip()
                if candidate and not candidate.startswith("data:"):
                    source = candidate
                    break
            if not source:
                image.decompose()
                continue
            image["src"] = source

        # 本地化后的图片优先；仍然是远程地址的图片补 no-referrer，避免公众号图床防盗链
        if not source.startswith(LOCAL_IMAGE_PREFIX) and not source.startswith("data:"):
            image["referrerpolicy"] = "no-referrer"

        image.attrs.pop("srcset", None)
        for lazy_attribute in LAZY_IMAGE_ATTRIBUTES:
            image.attrs.pop(lazy_attribute, None)
        if not image.get("alt"):
            image["alt"] = ""


def _clean_attributes(element: Tag, drop_display_none: bool) -> None:
    style = element.get("style")
    if style:
        cleaned = clean_style(style, drop_display_none=drop_display_none)
        if cleaned:
            element["style"] = cleaned
        else:
            del element["style"]

    for attribute in list(element.attrs):
        normalized = attribute.lower()
        if normalized.startswith("on"):
            del element[attribute]
        elif normalized.startswith("data-") and normalized not in KEEP_DATA_ATTRIBUTES:
            del element[attribute]

    href = element.get("href")
    if href and href.strip().lower().startswith("javascript:"):
        del element["href"]


def clean_article_html(html_content: str, platform: str = "web") -> str:
    """清洗正文 HTML，返回离线可读的片段。"""
    soup = BeautifulSoup(html_content, "html.parser")

    _remove_dangerous_nodes(soup)
    _replace_custom_elements(soup)
    _normalize_images(soup)

    for element in soup.find_all(True):
        _clean_attributes(element, drop_display_none=_is_content_root(element, soup))

    return str(soup).strip()
