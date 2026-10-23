"""HTTP 测试：共享 Session、重试策略与网络错误传播。"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import requests  # noqa: E402

from spider_core.errors import NetworkError  # noqa: E402
from spider_core.http import get_session, retry_request  # noqa: E402


class FakeResponse:
    status_code = 200
    text = "ok"

    def raise_for_status(self) -> None:
        return None


class RetryRequestTests(unittest.TestCase):
    def test_raises_network_error_after_all_retries(self) -> None:
        session = mock.Mock()
        session.get.side_effect = requests.exceptions.ConnectionError("boom")

        with mock.patch("spider_core.http.time.sleep") as sleep:
            with self.assertRaises(NetworkError) as context:
                retry_request("https://example.test/a", max_retries=3, delay=1, session=session)

        self.assertIn("https://example.test/a", str(context.exception))
        self.assertEqual(session.get.call_count, 3)
        self.assertEqual(sleep.call_count, 2)

    def test_returns_response_on_first_success(self) -> None:
        session = mock.Mock()
        session.get.return_value = FakeResponse()

        with mock.patch("spider_core.http.time.sleep") as sleep:
            response = retry_request("https://example.test/a", session=session)

        self.assertIs(response.text, "ok")
        sleep.assert_not_called()

    def test_recovers_after_transient_failure(self) -> None:
        session = mock.Mock()
        session.get.side_effect = [requests.exceptions.Timeout("slow"), FakeResponse()]

        with mock.patch("spider_core.http.time.sleep"):
            response = retry_request("https://example.test/a", session=session)

        self.assertIs(response.text, "ok")
        self.assertEqual(session.get.call_count, 2)

    def test_http_error_status_raises_network_error(self) -> None:
        session = mock.Mock()
        response = FakeResponse()

        def raise_http_error() -> None:
            raise requests.exceptions.HTTPError("403")

        response.raise_for_status = raise_http_error
        session.get.return_value = response

        with mock.patch("spider_core.http.time.sleep"):
            with self.assertRaises(NetworkError):
                retry_request("https://example.test/a", max_retries=2, session=session)


class CookieForwardingTests(unittest.TestCase):
    def test_cookie_header_is_forwarded(self) -> None:
        session = mock.Mock()
        session.get.return_value = FakeResponse()

        retry_request(
            "https://zhuanlan.zhihu.com/p/1",
            session=session,
            cookie="z_c0=abc; d_c0=xyz",
        )

        _, kwargs = session.get.call_args
        self.assertEqual(kwargs["headers"], {"Cookie": "z_c0=abc; d_c0=xyz"})

    def test_no_cookie_sends_no_cookie_header(self) -> None:
        session = mock.Mock()
        session.get.return_value = FakeResponse()

        retry_request("https://example.test/a", session=session)

        _, kwargs = session.get.call_args
        self.assertIsNone(kwargs["headers"])


class SessionTests(unittest.TestCase):
    def test_session_is_shared_and_sends_user_agent(self) -> None:
        self.assertIs(get_session(), get_session())
        self.assertIn("User-Agent", get_session().headers)


if __name__ == "__main__":
    unittest.main()
