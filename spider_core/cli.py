from __future__ import annotations

import argparse
import logging
import os
import sys

from .config import ALIASES, BASES, normalize_output_path, resolve_default_output_dir
from .errors import SpiderError
from .scrapers import find_scraper
from .service import process_batch, save_article

logger = logging.getLogger("spider")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="通用文章爬虫工具")
    parser.add_argument("-u", "--url", help="文章 URL")
    parser.add_argument(
        "-B",
        "--batch-file",
        dest="batch_file",
        help="包含 URL 列表的文本文件（每行一个 URL，# 开头为注释，兼容 CRLF）",
    )
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


def _read_urls(batch_file: str) -> list[str]:
    urls: list[str] = []
    with open(batch_file, encoding="utf-8") as file:
        for raw_line in file:
            line = raw_line.strip().rstrip("\r")
            if line and not line.startswith("#"):
                urls.append(line)
    return urls


def _dry_run_single(args: argparse.Namespace, output_dir: str, output_mode: str) -> int:
    print(f"Mode:       {output_mode}")
    print(f"Output dir: {output_dir}")
    if args.url:
        print(f"URL:        {args.url}")
        scraper = find_scraper(args.url)
        scraper_name = scraper.__class__.__name__.replace("Scraper", "") if scraper else "不支持"
        print(f"Scraper:    {scraper_name}")
    print(f"Format:     {args.format}")
    return 0


def _dry_run_batch(batch_file: str, output_dir: str, output_mode: str, fmt: str) -> int:
    print(f"Mode:       {output_mode}")
    print(f"Output dir: {output_dir}")
    print(f"Format:     {fmt}")
    for url in _read_urls(batch_file):
        scraper = find_scraper(url)
        scraper_name = scraper.__class__.__name__.replace("Scraper", "") if scraper else "不支持"
        print(f"  {url}  →  {scraper_name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )

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

    if args.url and args.batch_file:
        parser.error("--batch-file 与 URL 不能同时使用")

    try:
        output_dir, output_mode = resolve_cli_output_dir(args)
    except ValueError as error:
        print(f"错误: {error}", file=sys.stderr)
        return 1

    if args.dry_run:
        if args.batch_file:
            return _dry_run_batch(args.batch_file, output_dir, output_mode, args.format)
        return _dry_run_single(args, output_dir, output_mode)

    if args.batch_file:
        try:
            urls = _read_urls(args.batch_file)
        except OSError as error:
            print(f"错误: 无法读取 batch 文件: {error}", file=sys.stderr)
            return 1
        if not urls:
            print("错误: batch 文件为空或没有有效 URL。", file=sys.stderr)
            return 1
        return process_batch(urls, output_dir, args.format)

    if not args.url:
        parser.error("请提供文章 URL（使用 -u/--url）或 --batch-file")

    os.makedirs(output_dir, exist_ok=True)
    try:
        save_article(args.url, output_dir, args.format)
    except SpiderError as error:
        logger.error("%s", error)
        return 1
    return 0
