from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import ScrapedArticle


class AbstractScraper(ABC):
    """Base interface for all platform scrapers.

    ``scrape()`` raises SpiderError subclasses (NetworkError / ParseError)
    instead of returning None, so callers can distinguish failure modes.
    """

    @abstractmethod
    def match(self, url: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def scrape(self, url: str) -> ScrapedArticle:
        raise NotImplementedError
