from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .errors import SpiderError, UnsupportedURLError
from .media import download_and_rewrite_images
from .renderers import FORMAT_EXTENSIONS, render_documents, sanitize_filename
from .scrapers import find_scraper, supported_scraper_names


@dataclass(slots=True)
class SaveResult:
    """一次保存的结果，CLI 据此输出日志并决定退出码。"""

    url: str
    files: list[Path] = field(default_factory=list)
    skipped: bool = False
    error: str = ""

    @property
    def ok(self) -> bool:
        """成功写出文件才为 True；跳过和失败都不算 ok。"""
        return not self.error and not self.skipped


def scrape_article(url: str):
    """按 URL 选择抓取器并抓取；失败时抛 SpiderError 子类。"""
    scraper = find_scraper(url)
    if scraper is None:
        supported = ", ".join(supported_scraper_names())
        raise UnsupportedURLError(f"不支持的 URL 类型（当前支持: {supported}）")
    return scraper.scrape(url)


def _unique_article_dir(
    output_dir: str | os.PathLike[str],
    base_name: str,
    extensions: list[str],
) -> Path:
    """返回不与旧文章冲突的文章目录：重名时追加 ``_2`` / ``_3`` 后缀。"""
    root = Path(output_dir)
    index = 1
    while True:
        suffix = "" if index == 1 else f"_{index}"
        candidate = root / f"{base_name}{suffix}"
        if not any((candidate / f"{base_name}{suffix}{ext}").exists() for ext in extensions):
            return candidate
        index += 1


def save_article(
    url: str,
    output_dir: str | os.PathLike[str],
    output_formats: list[str] | tuple[str, ...] = ("md",),
    image_links: str = "relative",
    skip_existing: bool = False,
) -> SaveResult:
    """抓取一篇文章并写入 ``<output_dir>/<标题>/`` 目录。"""
    formats = [str(item).lower() for item in output_formats] or ["md"]
    unknown = [item for item in formats if item not in FORMAT_EXTENSIONS]
    if unknown:
        return SaveResult(url, error=f"未知输出格式: {', '.join(unknown)}")

    try:
        article = scrape_article(url)
    except SpiderError as error:
        return SaveResult(url, error=str(error))

    filename = sanitize_filename(article.title)
    extensions = [FORMAT_EXTENSIONS[fmt] for fmt in formats]
    base_dir = Path(output_dir) / filename
    target_files = [base_dir / f"{filename}{extension}" for extension in extensions]

    if skip_existing and all(path.exists() for path in target_files):
        return SaveResult(url, files=target_files, skipped=True)

    article_dir = _unique_article_dir(output_dir, filename, extensions)
    article_dir.mkdir(parents=True, exist_ok=True)
    stem = article_dir.name

    localized_html = download_and_rewrite_images(
        article.html_content,
        article.source_url,
        str(article_dir / "images"),
    )
    documents = render_documents(article, localized_html, formats, image_links)

    written: list[Path] = []
    for extension, document in documents:
        output_path = article_dir / f"{stem}{extension}"
        output_path.write_text(document, encoding="utf-8")
        written.append(output_path)
    return SaveResult(url, files=written)


__all__ = ["SaveResult", "save_article", "scrape_article"]
