#!/usr/bin/env python3
"""
通用文章爬虫工具 — 当前支持: 微信公众号, 知乎
扩展: 继承 AbstractScraper 并注册到 SCRAPERS 即可。
"""

import requests
from bs4 import BeautifulSoup
import html2text
import re, os, sys, hashlib, time
from urllib.parse import urljoin, urlparse
from datetime import datetime
from abc import ABC, abstractmethod

HEADERS = {
    'User-Agent': ('Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                   'AppleWebKit/537.36 (KHTML, like Gecko) '
                   'Chrome/120.0.0.0 Safari/537.36')
}
BASES = {
    "default": r"F:\workspace3\wen\Repository\obsidianDB",
}

# 目录别名 — 用于 -f 参数中快速定位知识库一级目录
ALIASES = {
    "A": "001-Current_Projects",
    "B": "002-raw_resource",
    "C": "003-wiki_schema",
}

# 兼容旧写法，避免既有命令失效
LEGACY_FOLDER_ALIASES = {
    "A-CURRENT_PROJECTS": "A",
    "B-RAW_RESOURCE": "B",
    "C-WIKI_SCHEMA": "C",
}


def resolve_alias(segment: str) -> str:
    """将路径段中的目录别名解析为知识库目录名，兼容旧写法与大小写"""
    if not segment:
        return segment
    normalized = segment.strip()
    lookup_key = normalized.upper()
    alias_key = LEGACY_FOLDER_ALIASES.get(lookup_key, lookup_key)
    return ALIASES.get(alias_key, normalized)


def resolve_output_dir(base_key: str, folders: list[str]) -> str:
    """解析 base 并组合文件夹段，构建最终输出路径"""
    if base_key not in BASES:
        known = ", ".join(BASES)
        raise ValueError(f"未知的 base 预设 '{base_key}'，可用: {known}")
    path = BASES[base_key]
    for folder in folders:
        path = os.path.join(path, resolve_alias(folder))
    return path


def retry_request(url, max_retries=3, delay=2):
    """带指数退避的请求"""
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
            return resp
        except requests.exceptions.RequestException as e:
            if attempt == max_retries - 1:
                print(f"请求失败 ({max_retries}次): {url} — {e}", file=sys.stderr)
                return None
            wait = delay * (2 ** attempt)
            print(f"请求失败，{wait}s 后重试 ({attempt+1}/{max_retries}): {e}", file=sys.stderr)
            time.sleep(wait)
    return None


# ---------------------------------------------------------------------------
# 爬虫基类
# ---------------------------------------------------------------------------

class AbstractScraper(ABC):
    """实现 match() 和 scrape() 即可注册一个新的平台爬虫"""

    @abstractmethod
    def match(self, url: str) -> bool: ...

    @abstractmethod
    def scrape(self, url: str) -> dict:
        """返回 {title, html_content, publish_time, source_url}"""


# ---------------------------------------------------------------------------
# 微信公众号
# ---------------------------------------------------------------------------

class WeChatScraper(AbstractScraper):
    def match(self, url: str) -> bool:
        return "mp.weixin.qq.com" in url

    def scrape(self, url: str) -> dict:
        resp = retry_request(url)
        if resp is None:
            return None

        soup = BeautifulSoup(resp.text, 'html.parser')

        title_tag = soup.find('h1', class_='rich_media_title')
        title = title_tag.get_text(strip=True) if title_tag else "未知标题"

        content_div = soup.find('div', class_='rich_media_content')
        if not content_div:
            print("未找到微信公众号文章内容区域。", file=sys.stderr)
            return None

        publish_time = ""
        meta_tag = soup.find('em', class_='rich_media_meta rich_media_meta_text')
        if meta_tag:
            publish_time = meta_tag.get_text(strip=True)

        for tag in content_div(['script', 'style', 'iframe']):
            tag.decompose()

        return {
            'title': title,
            'html_content': str(content_div),
            'publish_time': publish_time,
            'source_url': url,
        }


# ---------------------------------------------------------------------------
# 知乎
# ---------------------------------------------------------------------------

class ZhihuScraper(AbstractScraper):
    def match(self, url: str) -> bool:
        return "zhuanlan.zhihu.com" in url or "www.zhihu.com/question" in url

    def scrape(self, url: str) -> dict:
        resp = retry_request(url)
        if resp is None:
            return None

        soup = BeautifulSoup(resp.text, 'html.parser')

        title_tag = soup.find('h1', class_='Post-Title')
        title = title_tag.get_text(strip=True) if title_tag else "未知标题"

        content_div = soup.find('div', class_='Post-RichText')
        if not content_div:
            print("未找到知乎文章内容区域。", file=sys.stderr)
            return None

        for tag in content_div(['script', 'style', 'noscript']):
            tag.decompose()

        return {
            'title': title,
            'html_content': str(content_div),
            'publish_time': "",
            'source_url': url,
        }


# ---------------------------------------------------------------------------
# 爬虫注册表 — 加新平台只需在这里 append
# ---------------------------------------------------------------------------

SCRAPERS = [
    WeChatScraper(),
    ZhihuScraper(),
]


# ---------------------------------------------------------------------------
# 图片下载 & HTML 内链接重写
# ---------------------------------------------------------------------------

def _resolve_url(src: str, base_url: str) -> str | None:
    """将相对路径或协议相对路径转为绝对 URL"""
    if not src:
        return None
    if src.startswith("data:"):
        return None
    if src.startswith("//"):
        return "https:" + src
    if src.startswith("http"):
        return src
    return urljoin(base_url, src)


def _download_and_rewrite(html: str, base_url: str, img_dir: str) -> str:
    """下载 HTML 中所有图片，返回 src 已被替换为本地路径的 HTML"""
    soup = BeautifulSoup(html, 'html.parser')
    os.makedirs(img_dir, exist_ok=True)

    for img in soup.find_all('img'):
        # 微信公众号常用 data-src / data-wxsrc 做懒加载，把真实 URL 补到 src
        if not img.get('src') or img['src'].startswith('data:'):
            for attr in ('data-wxsrc', 'data-src', 'data-original-src'):
                if img.get(attr):
                    img['src'] = img[attr]
                    break
        if not img.get('src') or img['src'].startswith('data:'):
            continue
        src = img['src']
        abs_url = _resolve_url(src, base_url)
        if abs_url is None:
            continue

        try:
            resp = requests.get(abs_url, headers=HEADERS, timeout=15)
            resp.raise_for_status()
        except requests.exceptions.RequestException:
            continue

        ext = os.path.splitext(urlparse(abs_url).path)[1] or '.jpg'
        # 从 content-type 修正扩展名
        if not ext or ext.lower() not in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
            ct = resp.headers.get('Content-Type', '')
            ext = {'image/jpeg': '.jpg', 'image/png': '.png',
                   'image/gif': '.gif', 'image/webp': '.webp'}.get(ct, '.jpg')

        digest = hashlib.md5(abs_url.encode()).hexdigest()
        filename = f"{digest}{ext}"
        filepath = os.path.join(img_dir, filename)

        if not os.path.exists(filepath):
            with open(filepath, 'wb') as f:
                f.write(resp.content)

        img['src'] = 'images/' + filename

    return str(soup)


# ---------------------------------------------------------------------------
# 工具函数
# ---------------------------------------------------------------------------

def sanitize_filename(title: str) -> str:
    name = re.sub(r'[\\/:*?"<>|]', '', title).strip()
    name = re.sub(r'\s+', '_', name)
    return name[:100] or "article"


def build_html_doc(title, html_content, publish_time, source_url) -> str:
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    meta_time = f'<p>发布时间: {publish_time}</p>' if publish_time else ''
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{title}">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; line-height: 1.6; max-width: 900px; margin: 0 auto; padding: 20px; color: #333; background: #f9f9f9; }}
        .article-header {{ border-bottom: 2px solid #eee; padding-bottom: 20px; margin-bottom: 30px; }}
        .article-title {{ font-size: 28px; font-weight: bold; margin: 0 0 10px 0; }}
        .article-meta {{ font-size: 14px; color: #666; }}
        .article-content {{ background: #fff; padding: 20px; border-radius: 4px; box-shadow: 0 1px 3px rgba(0,0,0,.1); }}
        img {{ max-width: 100%; height: auto; margin: 10px 0; }}
        table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
        table, th, td {{ border: 1px solid #ddd; padding: 8px; }}
        th {{ background: #f5f5f5; }}
        code {{ background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-family: 'Courier New', monospace; }}
        pre {{ background: #f5f5f5; padding: 10px; border-radius: 4px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="article-header">
        <h1 class="article-title">{title}</h1>
        <div class="article-meta">
            {meta_time}
            <p>来源: <a href="{source_url}" target="_blank">{source_url[:50]}...</a></p>
            <p>抓取时间: {now}</p>
        </div>
    </div>
    <div class="article-content">
        {html_content}
    </div>
</body>
</html>"""


def build_markdown_doc(title, html_content, publish_time, source_url) -> str:
    """将已重写图片路径的 HTML 转换为 Markdown（含 YAML 前置元数据）"""
    converter = html2text.HTML2Text()
    converter.body_width = 0          # 不自动换行
    converter.ignore_links = False
    converter.ignore_images = False
    converter.ignore_tables = False
    converter.ignore_emphasis = False
    converter.protect_links = True
    converter.unicode_snob = True     # 保留 Unicode
    converter.skip_internal_links = False

    md_body = converter.handle(html_content).strip()

    # 用 YAML frontmatter 保留元数据
    lines = ["---"]
    lines.append(f'title: "{title}"')
    if publish_time:
        lines.append(f"date: {publish_time}")
    lines.append(f"source: {source_url}")
    lines.append(f"scraped_at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("---")
    lines.append("")
    lines.append(f"# {title}")
    lines.append("")
    lines.append(md_body)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def save_article(url: str, output_dir: str, output_format: str = "html") -> bool:

    scraper = next((s for s in SCRAPERS if s.match(url)), None)
    if scraper is None:
        supported = ", ".join(s.__class__.__name__.replace('Scraper', '') for s in SCRAPERS)
        print(f"不支持的URL类型。当前支持: {supported}", file=sys.stderr)
        return False

    result = scraper.scrape(url)
    if result is None:
        return False

    title = result['title']
    html_content = result['html_content']
    publish_time = result['publish_time']
    source_url = result['source_url']

    filename = sanitize_filename(title)
    article_dir = os.path.join(output_dir, filename)
    os.makedirs(article_dir, exist_ok=True)

    html_content = _download_and_rewrite(html_content, source_url,
                                         os.path.join(article_dir, 'images'))

    ext = ".md" if output_format == "md" else ".html"
    output_path = os.path.join(article_dir, f"{filename}{ext}")

    if output_format == "md":
        doc = build_markdown_doc(title, html_content, publish_time, source_url)
    else:
        doc = build_html_doc(title, html_content, publish_time, source_url)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(doc)

    print(f"文章已保存: {output_path}")
    return True


def main():
    import argparse
    parser = argparse.ArgumentParser(description="通用文章爬虫工具")
    parser.add_argument("base", nargs="?", default="default",
                        help="基础路径预设 (默认: default)")
    parser.add_argument("-u", "--url",
                        help="文章 URL")
    parser.add_argument("-f", "--folder", dest="folders",
                        action="append", default=[],
                        help="子目录段，可多次使用（支持 A→001-Current_Projects，兼容 A-Current_Projects）")
    parser.add_argument("-o", "--format", choices=["html", "md"],
                        default="html",
                        help="输出格式 (默认: html)")
    parser.add_argument("--dry-run", action="store_true",
                        help="仅显示解析路径，不执行爬取")
    parser.add_argument("--list-bases", action="store_true",
                        help="列出所有基础路径预设")
    parser.add_argument("--list-aliases", action="store_true",
                        help="列出所有系列别名")
    args = parser.parse_args()

    if args.list_bases:
        for key, path in BASES.items():
            print(f"  {key:<12} → {path}")
        return

    if args.list_aliases:
        for alias, number in ALIASES.items():
            print(f"  {alias:<4} → {number}")
        return

    try:
        output_dir = resolve_output_dir(args.base, args.folders)
    except ValueError as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print(f"Output dir: {output_dir}")
        if args.url:
            print(f"URL:        {args.url}")
        print(f"Format:     {args.format}")
        return

    if not args.url:
        parser.error("请提供文章 URL（使用 -u/--url）")

    os.makedirs(output_dir, exist_ok=True)
    success = save_article(args.url, output_dir, args.format)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
