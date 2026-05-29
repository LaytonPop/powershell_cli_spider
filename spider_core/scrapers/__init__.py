from __future__ import annotations

from .base import AbstractScraper
from .wechat import WeChatScraper
from .zhihu import ZhihuScraper

SCRAPERS: list[AbstractScraper] = [
    WeChatScraper(),
    ZhihuScraper(),
]


def find_scraper(url: str) -> AbstractScraper | None:
    return next((scraper for scraper in SCRAPERS if scraper.match(url)), None)


def supported_scraper_names() -> list[str]:
    return [scraper.__class__.__name__.replace("Scraper", "") for scraper in SCRAPERS]


__all__ = [
    "AbstractScraper",
    "SCRAPERS",
    "find_scraper",
    "supported_scraper_names",
]
