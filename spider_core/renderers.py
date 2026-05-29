from __future__ import annotations

import re
from datetime import datetime

import html2text

from .models import ScrapedArticle


def sanitize_filename(title: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]', "", title).strip()
    name = re.sub(r"\s+", "_", name)
    return name[:100] or "article"


def build_html_doc(title: str, html_content: str, publish_time: str, source_url: str) -> str:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    meta_time = f"<p>发布时间: {publish_time}</p>" if publish_time else ""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{title}">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; line-height: 1.6; max-width: 900px; margin: 0 auto; padding: 20px; color: #333; background: #f9f9f9; }}
        .article-header {{ border-bottom: 2px solid #eee; padding-bottom: 20px; margin-bottom: 30px; }}
        .article-title {{ font-size: 28px; font-weight: bold; margin: 0 0 10px 0; }}
        .article-meta {{ font-size: 14px; color: #666; }}
        .article-content {{ background: #fff; padding: 20px; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,.1); }}
        img {{ max-width: 100%; height: auto; margin: 10px 0; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        table, th, td {{ border: 1px solid #ddd; padding: 8px; }}
        th {{ background: #f5f5f5; }}
        code {{ background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-family: 'Courier New', monospace; }}
        pre {{ background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="article-header">
        <h1 class="article-title">{title}</h1>
        <div class="article-meta">
            {meta_time}
            <p>来源: <a href="{source_url}" target="_blank">{source_url[:50]}...</a></p>
            <p>抓取时间: {now}</p>
        </div>
    </div>
    <div class="article-content">
        {html_content}
    </div>
</body>
</html>"""


def build_markdown_doc(title: str, html_content: str, publish_time: str, source_url: str) -> str:
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

    lines = ["---"]
    lines.append(f'title: "{title}"')
    if publish_time:
        lines.append(f"date: {publish_time}")
    lines.append(f"source: {source_url}")
    lines.append(f"scraped_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {title}")
    lines.append("")
    lines.append(md_body)
    return "\n".join(lines)


def render_document(article: ScrapedArticle, html_content: str, output_format: str) -> tuple[str, str]:
    if output_format == "md":
        return ".md", build_markdown_doc(
            article.title, html_content, article.publish_time, article.source_url
        )

    return ".html", build_html_doc(
        article.title, html_content, article.publish_time, article.source_url
    )
