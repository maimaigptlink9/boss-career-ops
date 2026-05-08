from unittest.mock import MagicMock, patch

import pytest

from boss_career_ops.boss.api.client import BossClient
from boss_career_ops.boss.browser_client import BrowserClient
from boss_career_ops.config.singleton import SingletonMeta


@pytest.fixture(autouse=True)
def _reset_browser_singleton():
    yield
    SingletonMeta.reset(BrowserClient)


BROWSER_PATCH_TARGET = "boss_career_ops.boss.browser_client.BrowserClient"


def _make_mock_browser():
    browser = MagicMock(spec=BrowserClient)
    page_obj = MagicMock()
    page_obj.evaluate.return_value = {"code": 0, "data": {}}
    browser.get_page.return_value = page_obj
    browser._context = MagicMock()
    return browser, page_obj


class TestBrowserGetNoBrowserClose:
    def test_browser_get_does_not_call_browser_close(self):
        browser, page_obj = _make_mock_browser()

        client = BossClient.__new__(BossClient)
        client._token_manager = MagicMock()
        client._token_manager.get_cookies.return_value = {"zp_token": "fake"}

        with patch(BROWSER_PATCH_TARGET, return_value=browser):
            client._browser_get("https://www.zhipin.com/test", {}, {"Cookie": "x=1"}, {"zp_token": "fake"})

        page_obj.close.assert_called_once()
        browser.close.assert_not_called()

    def test_browser_get_keeps_singleton_context_alive(self):
        browser, page_obj = _make_mock_browser()
        browser._context = MagicMock()

        client = BossClient.__new__(BossClient)
        client._token_manager = MagicMock()
        client._token_manager.get_cookies.return_value = {"zp_token": "fake"}

        with patch(BROWSER_PATCH_TARGET, return_value=browser):
            client._browser_get("https://www.zhipin.com/test", {}, {"Cookie": "x=1"}, {"zp_token": "fake"})

        assert browser._context is not None


class TestBrowserPostNoBrowserClose:
    def test_browser_post_does_not_call_browser_close(self):
        browser, page_obj = _make_mock_browser()

        client = BossClient.__new__(BossClient)
        client._token_manager = MagicMock()
        client._token_manager.get_cookies.return_value = {"zp_token": "fake"}

        with patch(BROWSER_PATCH_TARGET, return_value=browser):
            client._browser_post(
                "https://www.zhipin.com/test",
                {"key": "value"},
                {"Content-Type": "application/json"},
                {"zp_token": "fake"},
            )

        page_obj.close.assert_called_once()
        browser.close.assert_not_called()

    def test_browser_post_keeps_singleton_context_alive(self):
        browser, page_obj = _make_mock_browser()
        browser._context = MagicMock()

        client = BossClient.__new__(BossClient)
        client._token_manager = MagicMock()
        client._token_manager.get_cookies.return_value = {"zp_token": "fake"}

        with patch(BROWSER_PATCH_TARGET, return_value=browser):
            client._browser_post(
                "https://www.zhipin.com/test",
                {"key": "value"},
                {"Content-Type": "application/json"},
                {"zp_token": "fake"},
            )

        assert browser._context is not None


class TestBrowserSingletonReuse:
    def test_consecutive_browser_get_calls_reuse_same_instance(self):
        browser, page_obj = _make_mock_browser()
        page_obj.evaluate.return_value = {"code": 0, "data": {}}

        client = BossClient.__new__(BossClient)
        client._token_manager = MagicMock()
        client._token_manager.get_cookies.return_value = {"zp_token": "fake"}

        with patch(BROWSER_PATCH_TARGET, return_value=browser):
            result1 = client._browser_get("https://www.zhipin.com/test1", {}, {"Cookie": "x=1"}, {"zp_token": "fake"})
            result2 = client._browser_get("https://www.zhipin.com/test2", {}, {"Cookie": "x=1"}, {"zp_token": "fake"})

        assert result1 is not None
        assert result2 is not None
        assert browser.close.call_count == 0
        assert browser.get_page.call_count == 2

    def test_browser_context_survives_after_fallback(self):
        mock_context = MagicMock()
        browser, page_obj = _make_mock_browser()
        browser._context = mock_context

        client = BossClient.__new__(BossClient)
        client._token_manager = MagicMock()
        client._token_manager.get_cookies.return_value = {"zp_token": "fake"}

        with patch(BROWSER_PATCH_TARGET, return_value=browser):
            client._browser_get("https://www.zhipin.com/test", {}, {"Cookie": "x=1"}, {"zp_token": "fake"})

        assert browser._context is mock_context
        browser.close.assert_not_called()
