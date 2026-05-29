from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ScrapedArticle:
    title: str
    html_content: str
    publish_time: str
    source_url: str
