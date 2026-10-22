from __future__ import annotations

import hashlib
import re
from datetime import datetime
from html import escape

import html2text

from .html_cleaner import clean_article_html
from .models import ScrapedArticle

PLATFORM_LABELS = {
    "wechat": "微信公众号",
    "zhihu": "知乎",
    "web": "网页",
}

PLATFORM_TAGS = {
    "wechat": "wechat",
    "zhihu": "zhihu",
    "web": "webpage",
}

FORMAT_EXTENSIONS = {
    "md": ".md",
    "html": ".html",
}

HTML_STYLE = """
:root { color-scheme: light; }
* { box-sizing: border-box; }
body {
    margin: 0;
    background: #f2f3f5;
    color: #3e3e3e;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC",
        "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
    -webkit-font-smoothing: antialiased;
}
.page { max-width: 720px; margin: 0 auto; padding: 28px 16px 64px; }
.article-header { padding: 4px 6px 22px; border-bottom: 1px solid #e3e3e3; margin-bottom: 22px; }
.platform-badge {
    display: inline-block;
    padding: 2px 9px;
    margin-bottom: 14px;
    border-radius: 3px;
    background: #e8eef9;
    color: #576b95;
    font-size: 12px;
    letter-spacing: .5px;
}
.article-title { margin: 0 0 14px; font-size: 26px; line-height: 1.4; font-weight: 600; color: #1f2329; }
.article-meta { display: flex; flex-wrap: wrap; gap: 6px 18px; font-size: 13px; color: #8a8a8a; }
.article-meta a { color: #576b95; text-decoration: none; word-break: break-all; }
.article-meta a:hover { text-decoration: underline; }
.article-content {
    background: #fff;
    border-radius: 6px;
    padding: 30px 30px 38px;
    box-shadow: 0 1px 4px rgba(0, 0, 0, .05);
    font-size: 17px;
    line-height: 1.75;
    color: #3e3e3e;
    word-wrap: break-word;
    overflow-wrap: break-word;
}
.article-content p { margin: 0 0 16px; }
.article-content img {
    max-width: 100% !important;
    height: auto !important;
    display: block;
    margin: 16px auto;
    border-radius: 2px;
}
.article-content h1, .article-content h2, .article-content h3, .article-content h4 {
    margin: 26px 0 14px;
    line-height: 1.45;
    color: #1f2329;
}
.article-content blockquote {
    margin: 16px 0;
    padding: 8px 16px;
    border-left: 3px solid #d9d9d9;
    background: #fafafa;
    color: #666;
}
.article-content table { max-width: 100%; margin: 16px auto; border-collapse: collapse; }
.article-content td, .article-content th { border: 1px solid #e0e0e0; padding: 6px 10px; }
.article-content pre {
    margin: 16px 0;
    padding: 12px 14px;
    border-radius: 4px;
    background: #f6f8fa;
    overflow-x: auto;
    font-size: 14px;
    line-height: 1.55;
}
.article-content code {
    padding: 2px 5px;
    border-radius: 3px;
    background: #f2f3f5;
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    font-size: .92em;
}
.article-content a { color: #576b95; text-decoration: none; }
.article-content a:hover { text-decoration: underline; }
.article-content .mp-foreign-content {
    padding: 8px 12px;
    border-radius: 4px;
    background: #fafafa;
    color: #999;
    font-size: 14px;
    text-align: center;
}
.article-footer { margin-top: 20px; padding: 0 6px; font-size: 12px; color: #aaa; text-align: center; }
@media (max-width: 600px) {
    .page { padding: 16px 10px 44px; }
    .article-content { padding: 20px 16px 26px; font-size: 16px; }
    .article-title { font-size: 22px; }
}
@media print {
    body { background: #fff; }
    .article-content { box-shadow: none; padding: 0; }
    .article-header { border-bottom: none; }
}
""".strip()


def sanitize_filename(title: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]', "", title).strip()
    name = re.sub(r"\s+", "_", name)
    # 拒绝 "." / ".." / 隐藏文件名等可能造成路径穿越或不可见目录的取值
    if not name or name.startswith(".") or name in {".", ".."} or re.fullmatch(r"\.+", name):
        name = f"article_{hashlib.md5(title.encode()).hexdigest()[:8]}"
    return name[:100]


def detect_platform(url: str) -> str:
    if "mp.weixin.qq.com" in url:
        return "wechat"
    if "zhuanlan.zhihu.com" in url or "www.zhihu.com" in url:
        return "zhihu"
    return "web"


def _extract_description(html_content: str, max_chars: int = 160) -> str:
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html_content, "html.parser")
    for tag in soup.find_all(["script", "style", "pre", "code", "table", "img", "figure"]):
        tag.decompose()
    text = soup.get_text(separator=" ", strip=True)
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + "…"


def _yaml_quote(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    escaped = escaped.replace("\r", " ").replace("\n", " ")
    return f'"{escaped}"'


def _convert_obsidian_image_links(markdown: str) -> str:
    return re.sub(r"!\[[^\]]*\]\((images/[^)]+)\)", r"![[\1]]", markdown)


def build_html_doc(article: ScrapedArticle, html_content: str) -> str:
    """生成自包含的“微信阅读模式”HTML 文档。

    正文先经 :func:`clean_article_html` 清洗（去掉 visibility/opacity 等隐藏样式），
    再套上统一阅读样式；正文原有内联样式保留，以维持富文本观感。
    """
    platform = detect_platform(article.source_url)
    cleaned = clean_article_html(html_content, platform=platform)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    title_html = escape(article.title)
    source_attr = escape(article.source_url, quote=True)
    description = (article.description or _extract_description(cleaned)).strip()
    description_attr = escape(" ".join(description.split()), quote=True)

    meta_chunks: list[str] = []
    for label, value in (
        ("公众号", article.account),
        ("作者", article.author),
        ("发布", article.publish_time),
    ):
        if value:
            meta_chunks.append(f'<span class="meta-item">{label}：{escape(value)}</span>')
    meta_chunks.append(f'<span class="meta-item">抓取：{now}</span>')
    meta_chunks.append(
        f'<a class="meta-item meta-link" href="{source_attr}" '
        f'target="_blank" rel="noopener noreferrer">查看原文 →</a>'
    )
    meta_html = "".join(meta_chunks)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="{description_attr}">
<meta name="generator" content="spider">
<title>{title_html}</title>
<style>
{HTML_STYLE}
</style>
</head>
<body>
<article class="page">
  <header class="article-header">
    <div class="platform-badge">{PLATFORM_LABELS.get(platform, PLATFORM_LABELS["web"])}</div>
    <h1 class="article-title">{title_html}</h1>
    <div class="article-meta">{meta_html}</div>
  </header>
  <main class="article-content">
{cleaned}
  </main>
  <footer class="article-footer">
    由 spider 抓取于 {now} · 图片与正文均保存在本地
  </footer>
</article>
</body>
</html>
"""


def build_markdown_doc(
    article: ScrapedArticle,
    html_content: str,
    image_links: str = "relative",
) -> str:
    converter = html2text.HTML2Text()
    converter.body_width = 0
    converter.ignore_links = False
    converter.ignore_images = False
    converter.ignore_tables = False
    converter.ignore_emphasis = False
    converter.protect_links = True
    converter.unicode_snob = True
    converter.skip_internal_links = False

    md_body = converter.handle(html_content).strip()
    if image_links == "wikilink":
        md_body = _convert_obsidian_image_links(md_body)

    platform = detect_platform(article.source_url)
    description = (article.description or _extract_description(html_content)).strip()

    lines = ["---"]
    lines.append(f"title: {_yaml_quote(article.title)}")
    if article.publish_time:
        lines.append(f"date: {_yaml_quote(article.publish_time)}")
    lines.append(f"source: {_yaml_quote(article.source_url)}")
    lines.append(f"platform: {platform}")
    if article.account:
        lines.append(f"account: {_yaml_quote(article.account)}")
    if article.author:
        lines.append(f"author: {_yaml_quote(article.author)}")
    lines.append("status: inbox")
    lines.append("progress: 0")
    lines.append(f"description: {_yaml_quote(description)}")
    lines.append("tags:")
    lines.append(f"  - {PLATFORM_TAGS.get(platform, 'webpage')}")
    lines.append(f"scraped_at: {_yaml_quote(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {article.title}")
    lines.append("")
    lines.append(md_body)
    return "\n".join(lines)


def render_documents(
    article: ScrapedArticle,
    html_content: str,
    output_formats: list[str],
    image_links: str = "relative",
) -> list[tuple[str, str]]:
    """按格式列表渲染文档，返回 [(扩展名, 内容), ...]。"""
    documents: list[tuple[str, str]] = []
    for output_format in output_formats:
        if output_format == "md":
            documents.append(
                (FORMAT_EXTENSIONS["md"], build_markdown_doc(article, html_content, image_links))
            )
        elif output_format == "html":
            documents.append((FORMAT_EXTENSIONS["html"], build_html_doc(article, html_content)))
        else:
            raise ValueError(f"未知输出格式: {output_format}")
    return documents
