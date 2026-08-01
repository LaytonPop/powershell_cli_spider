from __future__ import annotations


class SpiderError(Exception):
    """Base class for all spider errors."""


class NetworkError(SpiderError):
    """Request failed after retries (timeout, connection, HTTP status)."""


class ParseError(SpiderError):
    """Page fetched but content could not be extracted."""


class UnsupportedURLError(SpiderError):
    """No scraper matched the given URL."""
