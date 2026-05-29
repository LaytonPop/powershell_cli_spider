from __future__ import annotations

import hashlib
import os
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from .config import HEADERS

SUPPORTED_IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".gif", ".webp")
CONTENT_TYPE_EXTENSIONS = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/gif": ".gif",
    "image/webp": ".webp",
}


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


def _guess_extension(abs_url: str, response: requests.Response) -> str:
    ext = os.path.splitext(urlparse(abs_url).path)[1] or ".jpg"
    if ext.lower() in SUPPORTED_IMAGE_EXTENSIONS:
        return ext
    return CONTENT_TYPE_EXTENSIONS.get(response.headers.get("Content-Type", ""), ".jpg")


def download_and_rewrite_images(html: str, base_url: str, img_dir: str) -> str:
    """Download article images and rewrite src to local relative paths."""
    soup = BeautifulSoup(html, "html.parser")
    os.makedirs(img_dir, exist_ok=True)

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

        try:
            response = requests.get(abs_url, headers=HEADERS, timeout=15)
            response.raise_for_status()
        except requests.exceptions.RequestException:
            continue

        filename = hashlib.md5(abs_url.encode()).hexdigest() + _guess_extension(abs_url, response)
        filepath = os.path.join(img_dir, filename)

        if not os.path.exists(filepath):
            with open(filepath, "wb") as file:
                file.write(response.content)

        image["src"] = "images/" + filename

    return str(soup)
