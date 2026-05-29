from __future__ import annotations

import os

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

BASES = {
    "default": r"F:\workspace3\wen\Repository\obsidianDB",
}

ALIASES = {
    "A": "001-Current_Projects",
    "B": "002-raw_resource",
    "C": "003-wiki_schema",
}

LEGACY_FOLDER_ALIASES = {
    "A-CURRENT_PROJECTS": "A",
    "B-RAW_RESOURCE": "B",
    "C-WIKI_SCHEMA": "C",
}


def resolve_alias(segment: str) -> str:
    """Resolve folder aliases while keeping older commands working."""
    if not segment:
        return segment

    normalized = segment.strip()
    lookup_key = normalized.upper()
    alias_key = LEGACY_FOLDER_ALIASES.get(lookup_key, lookup_key)
    return ALIASES.get(alias_key, normalized)


def resolve_output_dir(base_key: str, folders: list[str]) -> str:
    """Resolve the configured base path and all folder segments."""
    if base_key not in BASES:
        known = ", ".join(BASES)
        raise ValueError(f"未知的 base 预设 '{base_key}'，可用: {known}")

    path = BASES[base_key]
    for folder in folders:
        path = os.path.join(path, resolve_alias(folder))
    return path
