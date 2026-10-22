"""媒体下载测试：魔数扩展名、懒加载图片解析与 src 本地化。"""

from __future__ import annotations

import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spider_core.errors import NetworkError  # noqa: E402
from spider_core.media import (  # noqa: E402
    _guess_extension,
    _sniff_extension,
    download_and_rewrite_images,
)

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 16
JPG = b"\xff\xd8\xff" + b"0" * 16
GIF = b"GIF89a" + b"0" * 16
WEBP = b"RIFF" + b"\x00" * 4 + b"WEBP" + b"0" * 16

BASE_URL = "https://mp.weixin.qq.com/s/abc"


class FakeResponse:
    def __init__(self, content: bytes, content_type: str = "image/png"):
        self.content = content
        self.headers = {"Content-Type": content_type}


class SniffExtensionTests(unittest.TestCase):
    def test_detects_common_formats(self) -> None:
        self.assertEqual(_sniff_extension(PNG), ".png")
        self.assertEqual(_sniff_extension(JPG), ".jpg")
        self.assertEqual(_sniff_extension(GIF), ".gif")
        self.assertEqual(_sniff_extension(WEBP), ".webp")

    def test_returns_none_for_non_image(self) -> None:
        self.assertIsNone(_sniff_extension(b"<!DOCTYPE html>"))


class GuessExtensionTests(unittest.TestCase):
    def test_magic_bytes_win_over_url_extension(self) -> None:
        self.assertEqual(_guess_extension("https://x.test/a.jpg", FakeResponse(PNG)), ".png")

    def test_falls_back_to_url_extension(self) -> None:
        response = FakeResponse(b"??", "application/octet-stream")
        self.assertEqual(_guess_extension("https://x.test/a.webp", response), ".webp")

    def test_falls_back_to_content_type(self) -> None:
        response = FakeResponse(b"??", "image/gif")
        self.assertEqual(_guess_extension("https://x.test/image", response), ".gif")

    def test_defaults_to_jpg(self) -> None:
        response = FakeResponse(b"??", "application/octet-stream")
        self.assertEqual(_guess_extension("https://x.test/image", response), ".jpg")


class DownloadAndRewriteImagesTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.img_dir = Path(self._tmp.name) / "images"

    def _rewrite(self, html: str, response: FakeResponse | None = None) -> str:
        response = response or FakeResponse(PNG)
        with mock.patch("spider_core.media.retry_request", return_value=response):
            return download_and_rewrite_images(html, BASE_URL, str(self.img_dir))

    def test_localizes_lazy_loaded_image(self) -> None:
        result = self._rewrite('<div><img data-src="https://mmbiz.qpic.cn/a.jpg"></div>')

        expected = hashlib.md5(b"https://mmbiz.qpic.cn/a.jpg").hexdigest() + ".png"
        self.assertIn(f'src="images/{expected}"', result)
        self.assertTrue((self.img_dir / expected).is_file())

    def test_keeps_data_uri_images(self) -> None:
        with mock.patch("spider_core.media.retry_request") as request:
            result = download_and_rewrite_images(
                '<img src="data:image/png;base64,AAAA">', BASE_URL, str(self.img_dir)
            )
        request.assert_not_called()
        self.assertIn('src="data:image/png;base64,AAAA"', result)

    def test_resolves_relative_image_url(self) -> None:
        result = self._rewrite('<img src="/img/a.png">')

        expected = hashlib.md5(b"https://mp.weixin.qq.com/img/a.png").hexdigest() + ".png"
        self.assertIn(f'src="images/{expected}"', result)

    def test_keeps_original_src_when_download_fails(self) -> None:
        with mock.patch("spider_core.media.retry_request", side_effect=NetworkError("boom")):
            result = download_and_rewrite_images(
                '<img src="https://mmbiz.qpic.cn/a.jpg">', BASE_URL, str(self.img_dir)
            )
        self.assertIn('src="https://mmbiz.qpic.cn/a.jpg"', result)


if __name__ == "__main__":
    unittest.main()
