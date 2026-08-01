from __future__ import annotations

import logging
import os

from .errors import SpiderError, UnsupportedURLError
from .media import download_and_rewrite_images
from .renderers import render_document, sanitize_filename
from .scrapers import find_scraper, supported_scraper_names

logger = logging.getLogger(__name__)


def scrape_article(url: str):
    """Find a matching scraper and scrape the URL.

    Raises SpiderError (UnsupportedURLError / NetworkError / ParseError)
    instead of returning None, so callers can distinguish failure modes.
    """
    scraper = find_scraper(url)
    if scraper is None:
        supported = ", ".join(supported_scraper_names())
        raise UnsupportedURLError(f"不支持的URL类型。当前支持: {supported}")
    return scraper.scrape(url)


def _unique_article_dir(output_dir: str, base_name: str, ext: str) -> str:
    """Return a non-colliding article dir.

    If the target file already exists (same article re-scraped, or a title
    collision), append a _2/_3 suffix so previous captures are never
    silently overwritten.
    """
    index = 1
    while True:
        suffix = "" if index == 1 else f"_{index}"
        candidate = os.path.join(output_dir, f"{base_name}{suffix}")
        target = os.path.join(candidate, f"{base_name}{suffix}{ext}")
        if not os.path.exists(target):
            return candidate
        index += 1


def save_article(url: str, output_dir: str, output_format: str = "html") -> str:
    """Scrape an article, download images, and save it.

    Returns the saved file path. Raises SpiderError on any failure.
    """
    article = scrape_article(url)

    filename = sanitize_filename(article.title)
    ext = ".md" if output_format == "md" else ".html"

    article_dir = _unique_article_dir(output_dir, filename, ext)
    os.makedirs(article_dir, exist_ok=True)

    localized_html = download_and_rewrite_images(
        article.html_content,
        article.source_url,
        os.path.join(article_dir, "images"),
    )

    _, document = render_document(article, localized_html, output_format)
    output_path = os.path.join(article_dir, f"{os.path.basename(article_dir)}{ext}")

    with open(output_path, "w", encoding="utf-8") as file:
        file.write(document)

    logger.info("文章已保存: %s", output_path)
    return output_path


def process_batch(urls: list[str], output_dir: str, output_format: str) -> int:
    """Process a batch of URLs; returns 0 when all succeeded, 1 otherwise."""
    os.makedirs(output_dir, exist_ok=True)
    succeeded = 0
    failed = 0

    for url in urls:
        try:
            save_article(url, output_dir, output_format)
            succeeded += 1
        except SpiderError as error:
            logger.error("抓取失败: %s — %s", url, error)
            failed += 1

    print(f"批量完成: 成功 {succeeded}，失败 {failed}")
    return 0 if failed == 0 else 1
