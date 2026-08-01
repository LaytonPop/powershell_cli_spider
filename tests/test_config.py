from __future__ import annotations

import spider_core.config as config
from spider_core.config import resolve_alias, resolve_default_output_dir, resolve_output_dir


class TestAliases:
    def test_simple_alias(self):
        assert resolve_alias("A") == "001-Current_Projects"

    def test_lowercase_alias(self):
        assert resolve_alias("a") == "001-Current_Projects"

    def test_legacy_style(self):
        assert resolve_alias("A-Current_Projects") == "001-Current_Projects"

    def test_unknown_passthrough(self):
        assert resolve_alias("mathcs") == "mathcs"


class TestBaseResolution:
    def test_default_base_with_folders(self):
        assert resolve_default_output_dir(["A", "mathcs"]).endswith(
            "001-Current_Projects/mathcs"
        )

    def test_spider_base_env_override(self, monkeypatch):
        monkeypatch.setenv("SPIDER_BASE", "/tmp/kb")
        assert resolve_default_output_dir(["B"]) == "/tmp/kb/002-raw_resource"

    def test_spider_base_empty_env_ignored(self, monkeypatch):
        monkeypatch.setenv("SPIDER_BASE", "   ")
        assert resolve_output_dir("default", []) == config.BASES["default"]

    def test_unknown_base_raises(self):
        import pytest

        with pytest.raises(ValueError):
            resolve_output_dir("nope", [])
