from __future__ import annotations

import logging
import time

import requests

from .config import HEADERS
from .errors import NetworkError

logger = logging.getLogger(__name__)

# Shared session: connection pooling across page + image downloads.
_session = requests.Session()
_session.headers.update(HEADERS)


def get_session() -> requests.Session:
    return _session


def retry_request(
    url: str,
    max_retries: int = 3,
    delay: int = 2,
    session: requests.Session | None = None,
) -> requests.Response:
    """Fetch a page with exponential backoff.

    Raises NetworkError when all attempts fail (never returns None).
    """
    http_session = session or _session
    for attempt in range(max_retries):
        try:
            response = http_session.get(url, timeout=15)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as error:
            if attempt == max_retries - 1:
                raise NetworkError(f"请求失败 ({max_retries}次): {url} — {error}") from error

            wait = delay * (2**attempt)
            logger.warning("请求失败，%ss 后重试 (%d/%d): %s", wait, attempt + 1, max_retries, error)
            time.sleep(wait)

    raise NetworkError(f"请求失败: {url}")
