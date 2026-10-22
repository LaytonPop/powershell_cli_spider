from __future__ import annotations

import argparse
import os
import sys
import webbrowser
from pathlib import Path

from .config import (
    ConfigError,
    SpiderConfig,
    load_config,
    normalize_output_path,
    split_dir_segments,
)
from .scrapers import find_scraper
from .service import save_article

VERSION = "1.0.0"

FORMAT_TARGETS: dict[str, list[str]] = {
    "md": ["md"],
    "html": ["html"],
    "both": ["md", "html"],
}

EPILOG = """\
示例:
  spider "https://mp.weixin.qq.com/s/xxx"
  spider "https://mp.weixin.qq.com/s/xxx" -F both -d A/IoT
  spider "url1" "url2" -o D:\\temp\\articles -F both
  spider -b urls.txt -d B -F md -n
  spider --dry-run "https://mp.weixin.qq.com/s/xxx"
  spider --list-bases / --list-aliases
"""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="spider",
        description="抓取微信公众号 / 知乎文章到本地知识库：正文清洗、图片本地化，可输出 md / html",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EPILOG,
    )
    parser.add_argument("urls", nargs="*", metavar="URL", help="文章 URL，可一次传多个")
    parser.add_argument(
        "-b",
        "--batch",
        dest="batch_file",
        metavar="FILE",
        help="包含 URL 列表的文本文件（每行一个，支持 # 注释）",
    )

    output_group = parser.add_argument_group("输出位置（-o 与 -d 二选一；都不给则落到默认收件箱）")
    output_target = output_group.add_mutually_exclusive_group()
    output_target.add_argument("-o", "--out", metavar="DIR", help="直接输出到指定目录")
    output_target.add_argument(
        "-d",
        "--dir",
        dest="dirs",
        action="append",
        default=[],
        metavar="SEG",
        help="知识库内子目录段，可重复；支持 A/B/C 别名与 A/IoT 写法",
    )
    output_group.add_argument("--base", metavar="NAME", help="知识库根预设（见 --list-bases）")

    format_group = parser.add_argument_group("内容格式")
    format_group.add_argument(
        "-F",
        "--format",
        dest="output_format",
        choices=tuple(FORMAT_TARGETS),
        default="md",
        help="输出格式: md / html / both，both 会同时输出 md 和 html（默认: md）",
    )
    format_group.add_argument(
        "-L",
        "--image-links",
        dest="image_links",
        choices=("relative", "wikilink"),
        default="relative",
        help="Markdown 图片链接风格: relative=相对路径, wikilink=Obsidian ![[images/x.png]]（默认: relative）",
    )

    behavior_group = parser.add_argument_group("行为")
    behavior_group.add_argument("-n", "--skip-existing", action="store_true", help="目标文件已存在时跳过")
    behavior_group.add_argument("--dry-run", action="store_true", help="只打印解析结果，不执行抓取")
    behavior_group.add_argument(
        "--open", dest="open_result", action="store_true", help="html 输出后用默认浏览器打开"
    )
    behavior_group.add_argument("-q", "--quiet", action="store_true", help="只输出必要信息")
    behavior_group.add_argument("-v", "--verbose", action="store_true", help="输出更多细节")

    parser.add_argument("--config", metavar="FILE", help="指定配置文件路径（默认 spider.config.toml）")
    parser.add_argument("--list-bases", action="store_true", help="列出知识库根预设")
    parser.add_argument("--list-aliases", action="store_true", help="列出目录别名")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    # 已移除的旧参数：保留解析入口，给出明确的迁移提示，而不是静默误解析
    for legacy_options, legacy_dest in (
        (("-u", "--url"), "legacy_url"),
        (("-df", "--default-folder"), "legacy_default_folder"),
        (("-f", "--full-path"), "legacy_full_path"),
        (("--batch-file",), "legacy_batch_file"),
    ):
        parser.add_argument(
            *legacy_options,
            dest=legacy_dest,
            nargs="?",
            default=None,
            help=argparse.SUPPRESS,
        )
    return parser


#: 旧参数 -> 迁移提示（本项目已断代，不做兼容映射）
LEGACY_FLAGS = (
    ("legacy_url", "-u/--url", "直接使用位置参数，例如: spider URL"),
    ("legacy_default_folder", "-df/--default-folder", "改用 -d/--dir 指定知识库内目录"),
    ("legacy_full_path", "-f/--full-path", "改用 -o/--out 指定直接输出目录"),
    ("legacy_batch_file", "--batch-file", "改用 -b/--batch 指定 URL 列表文件"),
)


def reject_legacy_flags(args: argparse.Namespace, parser: argparse.ArgumentParser) -> None:
    for dest, name, hint in LEGACY_FLAGS:
        if getattr(args, dest, None):
            parser.error(f"{name} 已移除；{hint}")


def read_batch_urls(batch_file: str) -> list[str]:
    urls: list[str] = []
    # utf-8-sig 兼容 Windows 记事本保存的 BOM
    with open(batch_file, "r", encoding="utf-8-sig") as file:
        for line in file:
            stripped = line.strip()
            if stripped and not stripped.startswith("#"):
                urls.append(stripped)
    return urls


def looks_like_format_name(value: str) -> bool:
    normalized = value.strip().lower()
    return normalized in FORMAT_TARGETS and "/" not in value and "\\" not in value


def collect_urls(args: argparse.Namespace, parser: argparse.ArgumentParser) -> list[str]:
    urls = [url.strip() for url in args.urls if url.strip()]
    if args.batch_file:
        try:
            urls.extend(read_batch_urls(args.batch_file))
        except OSError as error:
            parser.error(f"读取批量文件失败: {error}")
    if not urls:
        parser.error("请提供文章 URL（位置参数）或使用 -b/--batch 指定文件")
    return list(dict.fromkeys(urls))


def resolve_output_dir(args: argparse.Namespace, config: SpiderConfig) -> Path:
    if args.out:
        return Path(normalize_output_path(args.out))
    segments = split_dir_segments(args.dirs)
    if segments:
        return config.resolve_output_dir(segments, args.base)
    return config.default_output_dir(args.base)


def print_bases(config: SpiderConfig) -> None:
    print(f"配置文件: {config.config_path}")
    for name in config.bases:
        root = config.base_root(name)
        marker = "*" if name == config.default_base else " "
        status = "" if root.is_dir() else "   [目录不存在]"
        print(f" {marker} {name:<12} → {root}{status}")


def print_aliases(config: SpiderConfig) -> None:
    if not config.aliases:
        print(f"配置文件 {config.config_path} 中没有配置 [aliases]。")
        return
    print(f"知识库: {config.base_root()}")
    for alias, target in sorted(config.aliases.items()):
        print(f"   {alias:<4} → {target}")


def print_dry_run(
    args: argparse.Namespace,
    config: SpiderConfig,
    urls: list[str],
    output_dir: Path,
    output_formats: list[str],
    base_problem: str,
) -> None:
    mode = "直接目录" if args.out else "知识库"
    print(f"配置文件: {config.config_path}")
    print(f"模式:     {mode}")
    if not args.out:
        print(f"知识库:   {config.base_root(args.base)}")
    print(f"输出目录: {output_dir}")
    print(f"输出格式: {' + '.join(output_formats)}")
    print(f"图片链接: {args.image_links}")
    print(f"跳过已有: {'是' if args.skip_existing else '否'}")
    print(f"URL 数量: {len(urls)}")
    for index, url in enumerate(urls, 1):
        scraper = find_scraper(url)
        scraper_name = scraper.__class__.__name__.replace("Scraper", "") if scraper else "不支持"
        print(f"  [{index}] {url}  →  {scraper_name}")
    if base_problem:
        print(f"警告: {base_problem}")


def _configure_stdio() -> None:
    """让控制台输出不因编码问题崩溃。

    Windows 控制台常见代码页是 GBK，打印 ✓/✗ 或标题里的 emoji 会抛
    ``UnicodeEncodeError`` 打断整个流程；这里把 stdout/stderr 的错误策略
    改成替换，保证日志永远不会中断抓取。
    """
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(errors="replace")
        except (ValueError, OSError):  # 某些重定向环境不支持 reconfigure
            pass


def main(argv: list[str] | None = None) -> int:
    _configure_stdio()
    parser = build_parser()
    args = parser.parse_args(argv)

    reject_legacy_flags(args, parser)
    if args.out and looks_like_format_name(args.out):
        parser.error(
            "`-o/--out` 现在表示输出目录；输出格式请改用 -F/--format，例如: spider URL -F md"
        )

    try:
        config = load_config(args.config)
    except ConfigError as error:
        print(f"配置错误: {error}", file=sys.stderr)
        return 2

    if args.list_bases:
        print_bases(config)
        return 0
    if args.list_aliases:
        print_aliases(config)
        return 0

    urls = collect_urls(args, parser)
    output_formats = FORMAT_TARGETS[args.output_format]

    try:
        output_dir = resolve_output_dir(args, config)
    except ConfigError as error:
        print(f"错误: {error}", file=sys.stderr)
        return 2

    base_problem = ""
    if not args.out:
        try:
            config.ensure_base_exists(args.base)
        except ConfigError as error:
            base_problem = str(error)
    if base_problem and not args.dry_run:
        print(f"错误: {base_problem}", file=sys.stderr)
        return 2

    if args.dry_run:
        print_dry_run(args, config, urls, output_dir, output_formats, base_problem)
        return 0

    if not args.quiet:
        print(f"输出目录: {output_dir}")
        print(f"输出格式: {' + '.join(output_formats)}")
    os.makedirs(output_dir, exist_ok=True)

    saved = skipped = failed = 0
    opened_html = False
    for index, url in enumerate(urls, 1):
        if len(urls) > 1 and not args.quiet:
            print(f"\n[{index}/{len(urls)}] {url}")
        result = save_article(
            url,
            output_dir,
            output_formats,
            image_links=args.image_links,
            skip_existing=args.skip_existing,
        )
        if result.error:
            failed += 1
            print(f"[失败] {result.error}", file=sys.stderr)
            continue
        if result.skipped:
            skipped += 1
            target = result.files[0] if result.files else ""
            print(f"[跳过] 已存在: {target}")
            continue
        saved += 1
        for path in result.files:
            print(f"[OK] 已保存: {path}")
        if args.open_result:
            for path in result.files:
                if path.suffix == ".html":
                    webbrowser.open(path.resolve().as_uri())
                    opened_html = True

    total = len(urls)
    if not args.quiet or total > 1 or skipped or failed:
        print(f"\n完成: 共 {total} 篇，成功 {saved}，跳过 {skipped}，失败 {failed}")
    if args.open_result and not opened_html and saved:
        print(
            "提示: 当前输出没有 html，--open 未执行；可用 -F both 同时输出 md 和 html。",
            file=sys.stderr,
        )

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
