from __future__ import annotations

from spider_core.media import _guess_extension, _resolve_url, _sniff_extension


class TestSniffExtension:
    def test_png(self):
        assert _sniff_extension(b"\x89PNG\r\n\x1a\nrest") == ".png"

    def test_jpeg(self):
        assert _sniff_extension(b"\xff\xd8\xff\xe0rest") == ".jpg"

    def test_gif(self):
        assert _sniff_extension(b"GIF89a rest") == ".gif"

    def test_webp(self):
        assert _sniff_extension(b"RIFF\x00\x00\x00\x00WEBPVP8 ") == ".webp"

    def test_unknown(self):
        assert _sniff_extension(b"not an image") is None


class FakeResponse:
    def __init__(self, content=b"", headers=None):
        self.content = content
        self.headers = headers or {}


class TestGuessExtension:
    def test_magic_bytes_beat_url(self):
        resp = FakeResponse(content=b"\x89PNG\r\n\x1a\n")
        assert _guess_extension("https://x.com/a.jpg", resp) == ".png"

    def test_url_suffix_used_when_no_magic(self):
        resp = FakeResponse(content=b"junk")
        assert _guess_extension("https://x.com/a.PNG", resp) == ".png"

    def test_content_type_fallback(self):
        resp = FakeResponse(content=b"junk", headers={"Content-Type": "image/gif"})
        assert _guess_extension("https://x.com/img", resp) == ".gif"

    def test_jpg_last_resort(self):
        resp = FakeResponse(content=b"junk")
        assert _guess_extension("https://x.com/img", resp) == ".jpg"


class TestResolveUrl:
    def test_protocol_relative(self):
        assert _resolve_url("//cdn.example.com/a.png", "https://x.com") == "https://cdn.example.com/a.png"

    def test_absolute(self):
        assert _resolve_url("https://x.com/a.png", "https://x.com") == "https://x.com/a.png"

    def test_relative(self):
        assert _resolve_url("/a.png", "https://x.com/p/") == "https://x.com/a.png"

    def test_data_uri(self):
        assert _resolve_url("data:image/png;base64,xxx", "https://x.com") is None
