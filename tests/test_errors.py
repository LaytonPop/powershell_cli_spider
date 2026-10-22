"""错误类型测试：所有错误都继承 SpiderError，便于统一捕获。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from spider_core.errors import (  # noqa: E402
    NetworkError,
    ParseError,
    SpiderError,
    UnsupportedURLError,
)


class ErrorHierarchyTests(unittest.TestCase):
    def test_concrete_errors_inherit_from_spider_error(self) -> None:
        for error_type in (NetworkError, ParseError, UnsupportedURLError):
            self.assertTrue(issubclass(error_type, SpiderError))
            self.assertTrue(issubclass(error_type, Exception))

    def test_instances_keep_message(self) -> None:
        for error in (NetworkError("网络失败"), ParseError("解析失败"), UnsupportedURLError("不支持")):
            self.assertIsInstance(error, SpiderError)
            self.assertTrue(str(error))

    def test_spider_error_can_wrap_original(self) -> None:
        original = ValueError("原始错误")
        wrapped = ParseError("解析失败")
        wrapped.__cause__ = original
        self.assertIs(wrapped.__cause__, original)


if __name__ == "__main__":
    unittest.main()
