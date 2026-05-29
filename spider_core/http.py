from __future__ import annotations

import sys
import time

import requests

from .config import HEADERS


def retry_request(url: str, max_retries: int = 3, delay: int = 2) -> requests.Response | None:
    """Fetch a page with exponential backoff."""
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as error:
            if attempt == max_retries - 1:
                print(f"请求失败 ({max_retries}次): {url} — {error}", file=sys.stderr)
                return None

            wait = delay * (2**attempt)
            print(f"请求失败，{wait}s 后重试 ({attempt + 1}/{max_retries}): {error}", file=sys.stderr)
            time.sleep(wait)

    return None
