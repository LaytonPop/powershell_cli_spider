from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import ScrapedArticle


class AbstractScraper(ABC):
    """所有平台抓取器的基类。

    ``scrape()`` 失败时抛 :class:`~spider_core.errors.SpiderError` 的子类
    （``NetworkError`` / ``ParseError``），不再返回 ``None``，
    以便调用方区分失败原因。
    """

    @abstractmethod
    def match(self, url: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    def scrape(self, url: str, cookie: str | None = None) -> ScrapedArticle:
        """抓取一篇文章；``cookie`` 为可选 Cookie 请求头，用于需要登录态的站点。"""
        raise NotImplementedError
