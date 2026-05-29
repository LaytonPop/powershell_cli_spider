from __future__ import annotations

import argparse
import os
import sys

from .config import ALIASES, BASES, normalize_output_path, resolve_default_output_dir
from .service import save_article


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="通用文章爬虫工具")
    parser.add_argument("-u", "--url", help="文章 URL")
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument(
        "-df",
        "--default-folder",
        dest="default_folders",
        action="append",
        default=[],
        help="默认知识库下的子目录段，可多次使用（支持 A→001-Current_Projects）",
    )
    output_group.add_argument(
        "-f",
        "--full-path",
        dest="full_path",
        help="直接输出目录路径（不走默认知识库根目录）",
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


def resolve_cli_output_dir(args: argparse.Namespace) -> tuple[str, str]:
    if args.full_path:
        return normalize_output_path(args.full_path), "direct-path"

    return resolve_default_output_dir(args.default_folders), "default-base"


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
        output_dir, output_mode = resolve_cli_output_dir(args)
    except ValueError as error:
        print(f"错误: {error}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"Mode:       {output_mode}")
        print(f"Output dir: {output_dir}")
        if args.url:
            print(f"URL:        {args.url}")
        print(f"Format:     {args.format}")
        return 0

    if not args.url:
        parser.error("请提供文章 URL（使用 -u/--url）")

    os.makedirs(output_dir, exist_ok=True)
    return 0 if save_article(args.url, output_dir, args.format) else 1
