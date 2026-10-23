from __future__ import annotations

import logging
import time

import requests

from .config import HEADERS
from .errors import NetworkError

logger = logging.getLogger(__name__)

#: 共享 Session：正文与图片下载复用连接池，避免反复建连。
_session = requests.Session()
_session.headers.update(HEADERS)


def get_session() -> requests.Session:
    """返回全局共享的 requests Session。"""
    return _session


def retry_request(
    url: str,
    max_retries: int = 3,
    delay: int = 2,
    session: requests.Session | None = None,
    cookie: str | None = None,
) -> requests.Response:
    """抓取页面，失败时指数退避重试。

    与旧版不同：全部重试失败后抛出 :class:`NetworkError`，不再返回 ``None``，
    调用方可以据此区分失败原因。

    ``cookie`` 是要附加的 Cookie 请求头原文，用于知乎等需要登录态的站点；
    为 ``None`` 或空串时不发送 Cookie。
    """
    http_session = session or _session
    headers = {"Cookie": cookie} if cookie else None
    for attempt in range(max_retries):
        try:
            response = http_session.get(url, timeout=15, headers=headers)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as error:
            if attempt == max_retries - 1:
                raise NetworkError(f"请求失败 ({max_retries}次): {url} — {error}") from error

            wait = delay * (2**attempt)
            logger.warning("请求失败，%ss 后重试 (%d/%d): %s", wait, attempt + 1, max_retries, error)
            time.sleep(wait)

    raise NetworkError(f"请求失败: {url}")
