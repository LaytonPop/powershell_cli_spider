from __future__ import annotations

import os
import sys

from .media import download_and_rewrite_images
from .renderers import render_document, sanitize_filename
from .scrapers import find_scraper, supported_scraper_names


def save_article(url: str, output_dir: str, output_format: str = "html") -> bool:
    scraper = find_scraper(url)
    if scraper is None:
        supported = ", ".join(supported_scraper_names())
        print(f"不支持的URL类型。当前支持: {supported}", file=sys.stderr)
        return False

    article = scraper.scrape(url)
    if article is None:
        return False

    filename = sanitize_filename(article.title)
    article_dir = os.path.join(output_dir, filename)
    os.makedirs(article_dir, exist_ok=True)

    localized_html = download_and_rewrite_images(
        article.html_content,
        article.source_url,
        os.path.join(article_dir, "images"),
    )

    ext, document = render_document(article, localized_html, output_format)
    output_path = os.path.join(article_dir, f"{filename}{ext}")

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(document)

    print(f"文章已保存: {output_path}")
    return True
