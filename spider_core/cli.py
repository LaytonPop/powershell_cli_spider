from __future__ import annotations

import argparse
import os
import sys

from .config import ALIASES, BASES, resolve_output_dir
from .service import save_article


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="通用文章爬虫工具")
    parser.add_argument(
        "base",
        nargs="?",
        default="default",
        help="基础路径预设 (默认: default)",
    )
    parser.add_argument("-u", "--url", help="文章 URL")
    parser.add_argument(
        "-f",
        "--folder",
        dest="folders",
        action="append",
        default=[],
        help="子目录段，可多次使用（支持 A→001-Current_Projects，兼容 A-Current_Projects）",
    )
    parser.add_argument(
        "-o",
        "--format",
        choices=["html", "md"],
        default="html",
        help="输出格式 (默认: html)",
    )
    parser.add_argument("--dry-run", action="store_true", help="仅显示解析路径，不执行爬取")
    parser.add_argument("--list-bases", action="store_true", help="列出所有基础路径预设")
    parser.add_argument("--list-aliases", action="store_true", help="列出所有系列别名")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_bases:
        for key, path in BASES.items():
            print(f"  {key:<12} → {path}")
        return 0

    if args.list_aliases:
        for alias, target in ALIASES.items():
            print(f"  {alias:<4} → {target}")
        return 0

    try:
        output_dir = resolve_output_dir(args.base, args.folders)
    except ValueError as error:
        print(f"错误: {error}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"Output dir: {output_dir}")
        if args.url:
            print(f"URL:        {args.url}")
        print(f"Format:     {args.format}")
        return 0

    if not args.url:
        parser.error("请提供文章 URL（使用 -u/--url）")

    os.makedirs(output_dir, exist_ok=True)
    return 0 if save_article(args.url, output_dir, args.format) else 1
