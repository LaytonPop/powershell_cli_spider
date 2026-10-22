from __future__ import annotations


class SpiderError(Exception):
    """所有 spider 错误的基类。"""


class NetworkError(SpiderError):
    """请求在重试后仍失败（超时、连接中断、HTTP 错误状态码）。"""


class ParseError(SpiderError):
    """页面已抓到，但无法从 HTML 中提取正文（结构变化、验证页等）。"""


class UnsupportedURLError(SpiderError):
    """没有抓取器匹配该 URL。"""
