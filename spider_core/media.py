from __future__ import annotations

import hashlib
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from .config import HEADERS
from .errors import NetworkError
from .http import get_session, retry_request

logger = logging.getLogger(__name__)

SUPPORTED_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp")
CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
    "image/bmp": ".bmp",
}
DEFAULT_MAX_WORKERS = 8


def _resolve_url(src: str, base_url: str) -> str | None:
    if not src:
        return None
    if src.startswith("data:"):
        return None
    if src.startswith("//"):
        return "https:" + src
    if src.startswith("http"):
        return src
    return urljoin(base_url, src)


def _sniff_extension(content: bytes) -> str | None:
    """Detect image extension from magic bytes (more reliable than URL/Content-Type)."""
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if content.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if content.startswith(b"GIF87a") or content.startswith(b"GIF89a"):
        return ".gif"
    if content.startswith(b"RIFF") and content[8:12] == b"WEBP":
        return ".webp"
    if content.startswith(b"BM"):
        return ".bmp"
    if content.startswith(b"\x00\x00\x01\x00"):
        return ".ico"
    return None


def _guess_extension(abs_url: str, response) -> str:
    """Pick an extension: magic bytes > URL suffix > Content-Type > .jpg fallback."""
    sniffed = _sniff_extension(response.content[:16])
    if sniffed:
        return sniffed

    ext = os.path.splitext(urlparse(abs_url).path)[1].lower()
    if ext in SUPPORTED_IMAGE_EXTENSIONS:
        return ext

    return CONTENT_TYPE_EXTENSIONS.get(response.headers.get("Content-Type", ""), ".jpg")


def _download_one(abs_url: str, img_dir: str) -> str | None:
    """Download a single image; returns the local filename or None on failure."""
    try:
        response = retry_request(abs_url, session=get_session())
    except NetworkError as error:
        logger.warning("图片下载失败，跳过: %s — %s", abs_url, error)
        return None

    filename = hashlib.md5(abs_url.encode()).hexdigest() + _guess_extension(abs_url, response)
    filepath = os.path.join(img_dir, filename)

    if not os.path.exists(filepath):
        with open(filepath, "wb") as file:
            file.write(response.content)
    return filename


def download_and_rewrite_images(
    html: str,
    base_url: str,
    img_dir: str,
    max_workers: int = DEFAULT_MAX_WORKERS,
) -> str:
    """Download article images (concurrently) and rewrite src to local relative paths."""
    soup = BeautifulSoup(html, "html.parser")
    os.makedirs(img_dir, exist_ok=True)

    # Collect image jobs first so failures can't corrupt the src rewrite pass.
    jobs: list[tuple[object, str]] = []
    for image in soup.find_all("img"):
        if not image.get("src") or image["src"].startswith("data:"):
            for attr in ("data-wxsrc", "data-src", "data-original-src"):
                if image.get(attr):
                    image["src"] = image[attr]
                    break

        if not image.get("src") or image["src"].startswith("data:"):
            continue

        abs_url = _resolve_url(image["src"], base_url)
        if abs_url is None:
            continue
        jobs.append((image, abs_url))

    if not jobs:
        return str(soup)

    results: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(_download_one, url, img_dir): url for _, url in jobs}
        for future in as_completed(future_to_url):
            filename = future.result()
            if filename:
                results[future_to_url[future]] = filename

    for image, abs_url in jobs:
        if abs_url in results:
            image["src"] = "images/" + results[abs_url]

    return str(soup)
