import pytest
from unittest.mock import patch, MagicMock

from boss_career_ops.boss.browser_client import BrowserClient, DEFAULT_BRIDGE_URL
from boss_career_ops.config.singleton import SingletonMeta


@pytest.fixture(autouse=True)
def _reset_singleton():
    SingletonMeta._instances.pop(BrowserClient, None)
    yield
    SingletonMeta._instances.pop(BrowserClient, None)


class TestBrowserClientInit:
    def test_default_bridge_url(self):
        bc = BrowserClient()
        assert bc._bridge_url == DEFAULT_BRIDGE_URL

    def test_custom_bridge_url(self):
        SingletonMeta._instances.pop(BrowserClient, None)
        bc = BrowserClient(bridge_url="http://localhost:9999")
        assert bc._bridge_url == "http://localhost:9999"

    def test_none_bridge_url_falls_back_to_default(self):
        SingletonMeta._instances.pop(BrowserClient, None)
        bc = BrowserClient(bridge_url=None)
        assert bc._bridge_url == DEFAULT_BRIDGE_URL


class TestBridgeAvailability:
    def test_bridge_available_with_extensions(self):
        bc = BrowserClient()
        bc._bridge_available = None
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True, "extensions_connected": 1}
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client
            assert bc.is_bridge_available() is True

    def test_bridge_not_available_no_extensions(self):
        bc = BrowserClient()
        bc._bridge_available = None
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"ok": True, "extensions_connected": 0}
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.return_value = mock_resp
            mock_client_cls.return_value = mock_client
            assert bc.is_bridge_available() is False

    def test_bridge_not_available_daemon_offline(self):
        bc = BrowserClient()
        bc._bridge_available = None
        import httpx
        with patch("httpx.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_client.__enter__ = MagicMock(return_value=mock_client)
            mock_client.__exit__ = MagicMock(return_value=False)
            mock_client.get.side_effect = httpx.ConnectError("refused")
            mock_client_cls.return_value = mock_client
            assert bc.is_bridge_available() is False

    def test_bridge_availability_cached(self):
        bc = BrowserClient()
        bc._bridge_available = True
        assert bc.is_bridge_available() is True
        bc._bridge_available = False
        assert bc.is_bridge_available() is False


class TestEnsureConnectedNoBridge:
    def test_ensure_connected_skips_bridge(self):
        bc = BrowserClient()
        assert bc._context is None
        with patch.object(bc, "_connect_cdp", return_value=False), \
             patch.object(bc, "_connect_patchright", return_value=False):
            assert bc.ensure_connected() is False

    def test_ensure_connected_tries_cdp_then_patchright(self):
        bc = BrowserClient()
        with patch.object(bc, "_connect_cdp", return_value=False) as mock_cdp, \
             patch.object(bc, "_connect_patchright", return_value=True) as mock_pr:
            assert bc.ensure_connected() is True
            mock_cdp.assert_called_once()
            mock_pr.assert_called_once()

    def test_ensure_connected_cdp_success_no_patchright(self):
        bc = BrowserClient()
        with patch.object(bc, "_connect_cdp", return_value=True) as mock_cdp, \
             patch.object(bc, "_connect_patchright", return_value=False) as mock_pr:
            assert bc.ensure_connected() is True
            mock_cdp.assert_called_once()
            mock_pr.assert_not_called()


class TestCloseResetsBridgeCache:
    def test_close_resets_bridge_availability(self):
        bc = BrowserClient()
        bc._bridge_available = True
        bc.close()
        assert bc._bridge_available is None
