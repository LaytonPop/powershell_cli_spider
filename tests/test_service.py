from __future__ import annotations

from spider_core.models import ScrapedArticle
from spider_core.service import _unique_article_dir, save_article, scrape_article
from spider_core.errors import UnsupportedURLError


class TestUniqueArticleDir:
    def test_fresh_dir_uses_base_name(self, tmp_path):
        assert _unique_article_dir(str(tmp_path), "文章", ".md") == str(tmp_path / "文章")

    def test_existing_file_gets_suffix(self, tmp_path):
        d = tmp_path / "文章"
        d.mkdir()
        (d / "文章.md").write_text("old", encoding="utf-8")
        assert _unique_article_dir(str(tmp_path), "文章", ".md") == str(tmp_path / "文章_2")


class TestScrapeArticle:
    def test_unsupported_url(self):
        try:
            scrape_article("https://example.com/nope")
        except UnsupportedURLError:
            pass
        else:
            raise AssertionError("expected UnsupportedURLError")


class TestSaveArticle:
    def test_saves_html_file_with_images_dir(self, tmp_path, monkeypatch):
        article = ScrapedArticle(
            title="测试文章",
            html_content="<p>正文</p>",
            publish_time="2024-01-01",
            source_url="https://example.com/a",
        )
        monkeypatch.setattr("spider_core.service.scrape_article", lambda url: article)
        # no real network: return html unchanged, no images
        monkeypatch.setattr(
            "spider_core.service.download_and_rewrite_images",
            lambda html, base_url, img_dir: html,
        )

        path = save_article("https://example.com/a", str(tmp_path), "html")
        assert path == str(tmp_path / "测试文章" / "测试文章.html")
        assert (tmp_path / "测试文章" / "测试文章.html").exists()

    def test_second_save_gets_suffix(self, tmp_path, monkeypatch):
        article = ScrapedArticle(
            title="重复标题",
            html_content="<p>正文</p>",
            publish_time="",
            source_url="https://example.com/b",
        )
        monkeypatch.setattr("spider_core.service.scrape_article", lambda url: article)
        monkeypatch.setattr(
            "spider_core.service.download_and_rewrite_images",
            lambda html, base_url, img_dir: html,
        )

        save_article("https://example.com/b", str(tmp_path), "html")
        path2 = save_article("https://example.com/b", str(tmp_path), "html")
        assert path2 == str(tmp_path / "重复标题_2" / "重复标题_2.html")
        assert (tmp_path / "重复标题" / "重复标题.html").exists()
        assert (tmp_path / "重复标题_2" / "重复标题_2.html").exists()

    def test_markdown_format(self, tmp_path, monkeypatch):
        article = ScrapedArticle(
            title="md测试",
            html_content="<p>正文</p>",
            publish_time="",
            source_url="https://example.com/c",
        )
        monkeypatch.setattr("spider_core.service.scrape_article", lambda url: article)
        monkeypatch.setattr(
            "spider_core.service.download_and_rewrite_images",
            lambda html, base_url, img_dir: html,
        )

        path = save_article("https://example.com/c", str(tmp_path), "md")
        assert path.endswith(".md")
        content = (tmp_path / "md测试" / "md测试.md").read_text(encoding="utf-8")
        assert content.startswith("---")
        assert 'title: "md测试"' in content
