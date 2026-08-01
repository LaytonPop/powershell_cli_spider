from __future__ import annotations

from spider_core.errors import ParseError
from spider_core.scrapers.wechat import WeChatScraper
from spider_core.scrapers.zhihu import ZhihuScraper


class FakeResponse:
    def __init__(self, text: str):
        self.text = text


WECHAT_HTML = """
<html><body>
  <h1 class="rich_media_title">微信标题</h1>
  <div class="rich_media_content">
    <p>微信正文</p>
    <script>bad()</script>
    <iframe src="x"></iframe>
  </div>
  <em class="rich_media_meta rich_media_meta_text">2024-03-01</em>
</body></html>
"""

ZHIHU_COLUMN_HTML = """
<html><body>
  <h1 class="Post-Title">专栏标题</h1>
  <div class="ContentItem-time">2024-02-01</div>
  <div class="Post-RichText"><p>专栏正文</p><script>x()</script></div>
</body></html>
"""

ZHIHU_QUESTION_HTML = """
<html><body>
  <h1 class="QuestionHeader-title">问题标题</h1>
  <div class="RichContent-inner"><p>高赞回答</p></div>
</body></html>
"""


class TestWeChatScraper:
    def test_match(self):
        assert WeChatScraper().match("https://mp.weixin.qq.com/s/abc123")
        assert not WeChatScraper().match("https://example.com")

    def test_scrape(self, monkeypatch):
        import spider_core.scrapers.wechat as wechat_mod

        monkeypatch.setattr(wechat_mod, "retry_request", lambda url: FakeResponse(WECHAT_HTML))
        article = WeChatScraper().scrape("https://mp.weixin.qq.com/s/abc123")
        assert article.title == "微信标题"
        assert "微信正文" in article.html_content
        assert "bad()" not in article.html_content  # script removed
        assert article.publish_time == "2024-03-01"

    def test_scrape_missing_content_raises(self, monkeypatch):
        import spider_core.scrapers.wechat as wechat_mod

        monkeypatch.setattr(wechat_mod, "retry_request", lambda url: FakeResponse("<html></html>"))
        try:
            WeChatScraper().scrape("https://mp.weixin.qq.com/s/abc123")
        except ParseError:
            pass
        else:
            raise AssertionError("expected ParseError")


class TestZhihuScraper:
    def test_match_column(self):
        assert ZhihuScraper().match("https://zhuanlan.zhihu.com/p/123")

    def test_match_question(self):
        assert ZhihuScraper().match("https://www.zhihu.com/question/362222222")
        assert ZhihuScraper().match("https://www.zhihu.com/question/362222222/answer/999")

    def test_no_match_search(self):
        assert not ZhihuScraper().match("https://www.zhihu.com/search?q=spider")

    def test_scrape_column(self, monkeypatch):
        import spider_core.scrapers.zhihu as zhihu_mod

        monkeypatch.setattr(zhihu_mod, "retry_request", lambda url: FakeResponse(ZHIHU_COLUMN_HTML))
        article = ZhihuScraper().scrape("https://zhuanlan.zhihu.com/p/123")
        assert article.title == "专栏标题"
        assert "专栏正文" in article.html_content
        assert article.publish_time == "2024-02-01"

    def test_scrape_question(self, monkeypatch):
        import spider_core.scrapers.zhihu as zhihu_mod

        monkeypatch.setattr(zhihu_mod, "retry_request", lambda url: FakeResponse(ZHIHU_QUESTION_HTML))
        article = ZhihuScraper().scrape("https://www.zhihu.com/question/362222222")
        assert article.title == "问题标题"
        assert "高赞回答" in article.html_content

    def test_scrape_question_missing_content_raises(self, monkeypatch):
        import spider_core.scrapers.zhihu as zhihu_mod

        monkeypatch.setattr(zhihu_mod, "retry_request", lambda url: FakeResponse("<html><body><h1 class='QuestionHeader-title'>t</h1></body></html>"))
        try:
            ZhihuScraper().scrape("https://www.zhihu.com/question/362222222")
        except ParseError:
            pass
        else:
            raise AssertionError("expected ParseError")
