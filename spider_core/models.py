from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ScrapedArticle:
    """一次抓取的结构化结果。

    必填字段保持与旧版本一致，新增元数据字段都有默认值，旧调用方无需改动。
    """

    title: str
    html_content: str
    publish_time: str
    source_url: str
    author: str = ""
    account: str = ""
    description: str = ""
