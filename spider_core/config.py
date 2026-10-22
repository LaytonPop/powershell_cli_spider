"""配置加载与输出路径解析。

知识库根目录、默认落点和目录别名都放在 ``spider.config.toml`` 里，不再硬编码。
配置查找顺序：``--config`` 参数 → ``SPIDER_CONFIG`` 环境变量 → 仓库根目录 →
``~/.config/spider/spider.config.toml``。
"""

from __future__ import annotations

import os
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    )
}

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CONFIG_FILENAME = "spider.config.toml"
DEFAULT_BASE_NAME = "default"
DEFAULT_INBOX = "000-inbox"

#: 兼容旧目录别名写法（A-CURRENT_PROJECTS → A）
LEGACY_FOLDER_ALIASES = {
    "A-CURRENT_PROJECTS": "A",
    "B-RAW_RESOURCE": "B",
    "C-WIKI_SCHEMA": "C",
}

#: 配置文件缺失别名表时的兜底
FALLBACK_ALIASES = {
    "A": "001-Current_Projects",
    "B": "002-raw_resource",
    "C": "003-wiki_schema",
}


class ConfigError(Exception):
    """配置缺失或非法时抛出。"""


@dataclass(slots=True)
class SpiderConfig:
    bases: dict[str, str]
    aliases: dict[str, str] = field(default_factory=dict)
    default_base: str = DEFAULT_BASE_NAME
    default_inbox: str = DEFAULT_INBOX
    config_path: Path | None = None

    @property
    def base_names(self) -> list[str]:
        return list(self.bases)

    def base_root(self, base_key: str | None = None) -> Path:
        name = base_key or self.default_base
        if name not in self.bases:
            known = ", ".join(self.bases)
            raise ConfigError(f"未知的知识库预设 '{name}'，可用: {known}")
        raw_value = os.path.expandvars(os.path.expanduser(self.bases[name]))
        return Path(raw_value)

    def resolve_output_dir(self, folders: list[str], base_key: str | None = None) -> Path:
        """把若干目录段拼到知识库根目录下，并展开 A/B/C 别名。"""
        path = self.base_root(base_key)
        for segment in split_dir_segments(folders):
            path = path / resolve_alias(segment, self.aliases)
        return path

    def default_output_dir(self, base_key: str | None = None) -> Path:
        """未指定 -d/-o 时的默认落点（默认 000-inbox）。"""
        root = self.base_root(base_key)
        if not self.default_inbox.strip():
            return root
        path = root
        for segment in split_dir_segments([self.default_inbox]):
            path = path / resolve_alias(segment, self.aliases)
        return path

    def ensure_base_exists(self, base_key: str | None = None) -> None:
        root = self.base_root(base_key)
        if not root.is_dir():
            config_hint = f"请检查 {self.config_path} 中的 [bases] 配置" if self.config_path else "请检查配置文件中的 [bases] 配置"
            raise ConfigError(
                f"知识库目录不存在: {root}\n  {config_hint}，或改用 -o/--out 直接指定输出目录"
            )


def split_dir_segments(values: list[str]) -> list[str]:
    """拆分目录段：既接受多次 -d，也接受 -d A/IoT。"""
    segments: list[str] = []
    for value in values:
        for part in re.split(r"[\\/]+", str(value).strip()):
            if not part or part == ".":
                continue
            if part == "..":
                raise ConfigError("目录段不能包含 '..'（不允许跳出知识库根目录）")
            segments.append(part)
    return segments


def resolve_alias(segment: str, aliases: dict[str, str] | None = None) -> str:
    """展开单段目录别名；未知别名原样返回。"""
    if not segment:
        return segment
    normalized = str(segment).strip()
    lookup_key = normalized.upper()
    alias_key = LEGACY_FOLDER_ALIASES.get(lookup_key, lookup_key)
    table = aliases if aliases is not None else FALLBACK_ALIASES
    return table.get(alias_key, normalized)


def normalize_output_path(path: str) -> str:
    """规范化 -o/--out 传入的直接输出路径。"""
    normalized = (path or "").strip()
    if not normalized:
        raise ConfigError("输出目录不能为空")
    expanded = os.path.expanduser(os.path.expandvars(normalized))
    return os.path.normpath(os.path.abspath(expanded))


def _resolve_config_path(config_path: str | os.PathLike[str] | None) -> Path | None:
    if config_path:
        path = Path(os.path.expanduser(os.path.expandvars(str(config_path)))).resolve()
        if not path.is_file():
            raise ConfigError(f"配置文件不存在: {path}")
        return path

    env_path = os.environ.get("SPIDER_CONFIG")
    if env_path:
        path = Path(os.path.expanduser(os.path.expandvars(env_path))).resolve()
        if not path.is_file():
            raise ConfigError(f"SPIDER_CONFIG 指向的配置文件不存在: {path}")
        return path

    candidates = (
        PROJECT_ROOT / CONFIG_FILENAME,
        Path.home() / ".config" / "spider" / CONFIG_FILENAME,
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def load_config(config_path: str | os.PathLike[str] | None = None) -> SpiderConfig:
    resolved = _resolve_config_path(config_path)
    if resolved is None:
        raise ConfigError(
            f"未找到配置文件 {CONFIG_FILENAME}。\n"
            f"  请在 {PROJECT_ROOT} 下创建，或用 --config / SPIDER_CONFIG 指定路径"
        )

    try:
        with open(resolved, "rb") as file:
            data = tomllib.load(file)
    except (OSError, tomllib.TOMLDecodeError) as error:
        raise ConfigError(f"读取配置文件失败 ({resolved}): {error}") from error

    bases = {
        str(key).strip(): str(value).strip()
        for key, value in data.get("bases", {}).items()
        if str(key).strip()
    }
    # 兼容两种环境变量：SPIDER_VAULT 优先，其次旧版 SPIDER_BASE
    for variable in ("SPIDER_VAULT", "SPIDER_BASE"):
        override = (os.environ.get(variable) or "").strip()
        if override:
            expanded = os.path.expanduser(os.path.expandvars(override))
            bases["default"] = os.path.normpath(os.path.abspath(expanded))
            break
    if not bases:
        raise ConfigError(f"配置文件缺少 [bases] 配置: {resolved}")

    aliases = {
        str(key).strip().upper(): str(value).strip()
        for key, value in data.get("aliases", {}).items()
        if str(key).strip()
    }
    default_base = str(data.get("default_base", DEFAULT_BASE_NAME)).strip() or DEFAULT_BASE_NAME
    if default_base not in bases:
        raise ConfigError(
            f"default_base '{default_base}' 不在 [bases] 中，可用: {', '.join(bases)}"
        )
    default_inbox = str(data.get("default_inbox", DEFAULT_INBOX)).strip()

    return SpiderConfig(
        bases=bases,
        aliases=aliases,
        default_base=default_base,
        default_inbox=default_inbox,
        config_path=resolved,
    )
