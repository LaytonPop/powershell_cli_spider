"""命令行参数与路径解析测试（不联网）。"""

from __future__ import annotations

import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spider_core.cli import build_parser, main  # noqa: E402
from spider_core.config import ConfigError, load_config  # noqa: E402

URL = "https://mp.weixin.qq.com/s/SSU_GOBTHxiGQGPAF0xSHg"
CONFIG_TEMPLATE = """\
default_base = "default"
default_inbox = "000-inbox"

[bases]
default = "{vault}"

[aliases]
A = "001-Current_Projects"
B = "002-raw_resource"
"""


def write_config(directory: Path) -> Path:
    vault = directory / "vault"
    (vault / "000-inbox").mkdir(parents=True)
    (vault / "001-Current_Projects").mkdir(parents=True)
    config_path = directory / "spider.config.toml"
    config_path.write_text(CONFIG_TEMPLATE.format(vault=vault.as_posix()), encoding="utf-8")
    return config_path


def run_main(arguments: list[str]) -> tuple[int, str, str]:
    stdout, stderr = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
        code = main(arguments)
    return code, stdout.getvalue(), stderr.getvalue()


class ParserDefaultsTests(unittest.TestCase):
    def test_defaults_prefer_markdown(self) -> None:
        args = build_parser().parse_args([URL])
        self.assertEqual(args.output_format, "md")
        self.assertEqual(args.image_links, "relative")
        self.assertFalse(args.skip_existing)
        self.assertEqual(args.urls, [URL])

    def test_accepts_multiple_urls_and_new_flags(self) -> None:
        args = build_parser().parse_args([URL, URL + "2", "-d", "A/IoT", "-F", "both", "-n", "-L", "wikilink"])
        self.assertEqual(len(args.urls), 2)
        self.assertEqual(args.dirs, ["A/IoT"])
        self.assertEqual(args.output_format, "both")
        self.assertTrue(args.skip_existing)
        self.assertEqual(args.image_links, "wikilink")

    def test_legacy_flags_are_rejected_with_migration_hint(self) -> None:
        for legacy in (
            ["--url", URL],
            ["-u", URL],
            ["-df", "A"],
            ["-f", "some/path"],
            ["--batch-file", "urls.txt"],
            ["--full-path", "some/path"],
        ):
            with self.subTest(legacy=legacy):
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    with self.assertRaises(SystemExit) as caught:
                        main(legacy + [URL])
                self.assertEqual(caught.exception.code, 2)
                self.assertIn("已移除", stderr.getvalue())

    def test_old_o_format_misuse_is_caught(self) -> None:
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as caught:
                main(["-o", "md", URL])
        self.assertEqual(caught.exception.code, 2)
        self.assertIn("-F/--format", stderr.getvalue())


class ConfigResolveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config_path = write_config(self.root)
        self.config = load_config(self.config_path)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_alias_expansion(self) -> None:
        path = self.config.resolve_output_dir(["A/IoT"])
        self.assertEqual(path, self.config.base_root() / "001-Current_Projects" / "IoT")

    def test_multiple_segments(self) -> None:
        path = self.config.resolve_output_dir(["B", "raw_resource", "微信"])
        self.assertEqual(
            path, self.config.base_root() / "002-raw_resource" / "raw_resource" / "微信"
        )

    def test_default_inbox(self) -> None:
        self.assertTrue(str(self.config.default_output_dir()).endswith("000-inbox"))

    def test_unknown_base_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            self.config.base_root("nope")

    def test_missing_vault_rejected(self) -> None:
        missing = Path(self.root) / "not-there"
        config_path = Path(self.root) / "missing.toml"
        config_path.write_text(
            CONFIG_TEMPLATE.format(vault=missing.as_posix()), encoding="utf-8"
        )
        with self.assertRaises(ConfigError):
            load_config(config_path).ensure_base_exists()

    def test_missing_config_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            load_config(Path(self.root) / "absent.toml")


class DryRunTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config_path = write_config(self.root)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_dry_run_prints_resolved_targets_without_network(self) -> None:
        code, stdout, _ = run_main(["--config", str(self.config_path), "--dry-run", URL, "-d", "A", "-F", "both"])
        self.assertEqual(code, 0)
        self.assertIn("001-Current_Projects", stdout)
        self.assertIn("md + html", stdout)
        self.assertIn("WeChat", stdout)

    def test_default_target_is_default_inbox(self) -> None:
        code, stdout, _ = run_main(["--config", str(self.config_path), "--dry-run", URL])
        self.assertEqual(code, 0)
        self.assertIn("000-inbox", stdout)
        self.assertIn("md", stdout)

    def test_list_bases_reports_config_path(self) -> None:
        code, stdout, _ = run_main(["--config", str(self.config_path), "--list-bases"])
        self.assertEqual(code, 0)
        self.assertIn(str(self.config_path), stdout)
        self.assertIn("default", stdout)

    def test_list_aliases_reports_mapping(self) -> None:
        code, stdout, _ = run_main(["--config", str(self.config_path), "--list-aliases"])
        self.assertEqual(code, 0)
        self.assertIn("001-Current_Projects", stdout)

    def test_missing_url_errors(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as caught:
                run_main(["--config", str(self.config_path)])
        self.assertEqual(caught.exception.code, 2)

    def test_output_out_wins_over_dir(self) -> None:
        out_dir = self.root / "direct"
        code, stdout, _ = run_main(
            ["--config", str(self.config_path), "--dry-run", URL, "-o", str(out_dir)]
        )
        self.assertEqual(code, 0)
        self.assertIn(str(out_dir), stdout)
        self.assertNotIn("000-inbox", stdout)

    def test_unsupported_url_is_reported(self) -> None:
        code, stdout, _ = run_main(
            ["--config", str(self.config_path), "--dry-run", "https://example.com/a"]
        )
        self.assertEqual(code, 0)  # dry-run 只报告，不失败
        self.assertIn("不支持", stdout)


class VersionAndEnvTests(unittest.TestCase):
    def test_version_exits_zero(self) -> None:
        with self.assertRaises(SystemExit) as caught:
            with contextlib.redirect_stdout(io.StringIO()):
                build_parser().parse_args(["--version"])
        self.assertEqual(caught.exception.code, 0)

    def test_spider_environment_variables_are_supported(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config_path = write_config(root)
            os.environ["SPIDER_CONFIG"] = str(config_path)
            try:
                config = load_config()
                self.assertEqual(config.config_path, config_path)
            finally:
                os.environ.pop("SPIDER_CONFIG", None)


if __name__ == "__main__":
    unittest.main()
