"""配置层测试：目录段拆分、别名展开、知识库路径解析与环境变量覆盖。"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spider_core.config import (  # noqa: E402
    ConfigError,
    load_config,
    normalize_output_path,
    resolve_alias,
    split_dir_segments,
)

CONFIG_TEMPLATE = """\
default_base = "default"
default_inbox = "000-inbox"

[bases]
default = "{vault}"

[aliases]
A = "001-Current_Projects"
B = "002-raw_resource"
"""


def write_config(root: Path, vault: Path) -> Path:
    config_path = root / "spider.config.toml"
    config_path.write_text(CONFIG_TEMPLATE.format(vault=vault.as_posix()), encoding="utf-8")
    return config_path


class SplitDirSegmentsTests(unittest.TestCase):
    def test_splits_forward_and_back_slashes(self) -> None:
        self.assertEqual(split_dir_segments(["A/IoT", r"B\书籍"]), ["A", "IoT", "B", "书籍"])

    def test_drops_empty_and_dot_segments(self) -> None:
        self.assertEqual(split_dir_segments(["A//./B"]), ["A", "B"])

    def test_rejects_parent_traversal(self) -> None:
        with self.assertRaises(ConfigError):
            split_dir_segments(["A/../B"])


class ResolveAliasTests(unittest.TestCase):
    def test_expands_known_aliases(self) -> None:
        self.assertEqual(resolve_alias("A"), "001-Current_Projects")
        self.assertEqual(resolve_alias("b"), "002-raw_resource")

    def test_unknown_alias_is_passed_through(self) -> None:
        self.assertEqual(resolve_alias("custom"), "custom")

    def test_custom_alias_table(self) -> None:
        self.assertEqual(resolve_alias("X", {"X": "custom-dir"}), "custom-dir")


class NormalizeOutputPathTests(unittest.TestCase):
    def test_returns_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertTrue(os.path.isabs(normalize_output_path(os.path.join(tmp, "out"))))

    def test_empty_path_raises(self) -> None:
        with self.assertRaises(ConfigError):
            normalize_output_path("   ")


class LoadConfigTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)

        root = Path(self._tmp.name)
        self.root = root
        self.vault = root / "vault"
        (self.vault / "000-inbox").mkdir(parents=True)
        self.config_path = write_config(root, self.vault)

        self._saved_env = {key: os.environ.pop(key, None) for key in ("SPIDER_VAULT", "SPIDER_BASE")}
        self.addCleanup(self._restore_env)

    def _restore_env(self) -> None:
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_resolves_base_and_aliases(self) -> None:
        config = load_config(self.config_path)
        self.assertEqual(config.default_output_dir(), self.vault / "000-inbox")
        self.assertEqual(
            config.resolve_output_dir(["A", "IoT"]),
            self.vault / "001-Current_Projects" / "IoT",
        )

    def test_single_alias_segment(self) -> None:
        config = load_config(self.config_path)
        self.assertEqual(config.resolve_output_dir(["A"]), self.vault / "001-Current_Projects")

    def test_unknown_base_raises(self) -> None:
        config = load_config(self.config_path)
        with self.assertRaises(ConfigError):
            config.base_root("nope")

    def test_spider_vault_env_override(self) -> None:
        override = self.root / "other-vault"
        os.environ["SPIDER_VAULT"] = str(override)
        self.assertEqual(load_config(self.config_path).base_root(), override)

    def test_spider_base_env_override_fallback(self) -> None:
        override = self.root / "legacy-vault"
        os.environ["SPIDER_BASE"] = str(override)
        self.assertEqual(load_config(self.config_path).base_root(), override)

    def test_spider_vault_wins_over_spider_base(self) -> None:
        os.environ["SPIDER_BASE"] = str(self.root / "legacy-vault")
        os.environ["SPIDER_VAULT"] = str(self.root / "primary-vault")
        self.assertEqual(load_config(self.config_path).base_root(), self.root / "primary-vault")

    def test_missing_config_file_raises(self) -> None:
        with self.assertRaises(ConfigError):
            load_config(self.root / "missing.toml")

    def test_ensure_base_exists(self) -> None:
        config = load_config(self.config_path)
        config.ensure_base_exists()
        with self.assertRaises(ConfigError):
            config.ensure_base_exists("missing")


if __name__ == "__main__":
    unittest.main()
