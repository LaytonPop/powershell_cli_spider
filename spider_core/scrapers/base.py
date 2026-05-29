from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import ScrapedArticle


class AbstractScraper(ABC):
    """Base interface for all platform scrapers."""

    @abstractmethod
    def match(self, url: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def scrape(self, url: str) -> ScrapedArticle | None:
        raise NotImplementedError
