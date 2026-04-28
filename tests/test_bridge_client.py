import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from boss_career_ops.bridge.client import BridgeClient, DEFAULT_BRIDGE_URL
from boss_career_ops.bridge.protocol import BridgeCommand, CommandType, BridgeResult


class TestBridgeClient:
    def test_init_default_url(self):
        client = BridgeClient()
        assert client._bridge_url == DEFAULT_BRIDGE_URL.rstrip("/")

    def test_init_custom_url(self):
        client = BridgeClient(bridge_url="http://localhost:9999/")
        assert client._bridge_url == "http://localhost:9999"

    @patch("boss_career_ops.bridge.client.httpx.Client")
    def test_is_available_true(self, mock_client_cls):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client
        client = BridgeClient()
        assert client.is_available() is True

    @patch("boss_career_ops.bridge.client.httpx.Client")
    def test_is_available_false(self, mock_client_cls):
        mock_client = MagicMock()
        mock_client.get.side_effect = Exception("connection refused")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_cls.return_value = mock_client
        client = BridgeClient()
        assert client.is_available() is False

    @patch.object(BridgeClient, "is_available", return_value=False)
    def test_send_command_unavailable(self, mock_avail):
        client = BridgeClient()
        cmd = BridgeCommand(type=CommandType.PING, id="1")
        result = client.send_command(cmd)
        assert result.ok is False
        assert "不可用" in result.error

    @patch.object(BridgeClient, "is_available", return_value=True)
    @patch.object(BridgeClient, "_ws_send", new_callable=AsyncMock)
    def test_send_command_success(self, mock_ws, mock_avail):
        mock_ws.return_value = {"ok": True, "data": {"url": "https://zhipin.com"}, "id": "42"}
        client = BridgeClient()
        cmd = BridgeCommand(type=CommandType.NAVIGATE, params={"url": "https://zhipin.com"}, id="42")
        result = client.send_command(cmd)
        assert result.ok is True
        assert result.data == {"url": "https://zhipin.com"}
        assert result.id == "42"

    @patch.object(BridgeClient, "is_available", return_value=True)
    @patch.object(BridgeClient, "_ws_send", new_callable=AsyncMock, side_effect=Exception("ws 连接失败"))
    def test_send_command_ws_error(self, mock_ws, mock_avail):
        client = BridgeClient()
        cmd = BridgeCommand(type=CommandType.PING, id="1")
        result = client.send_command(cmd)
        assert result.ok is False
        assert "ws 连接失败" in result.error

    def test_navigate_creates_command(self):
        client = BridgeClient()
        with patch.object(client, "send_command") as mock_send:
            mock_send.return_value = BridgeResult(ok=True)
            client.navigate("https://zhipin.com")
            cmd = mock_send.call_args[0][0]
            assert cmd.type == CommandType.NAVIGATE
            assert cmd.params["url"] == "https://zhipin.com"

    def test_get_cookies_success(self):
        client = BridgeClient()
        with patch.object(client, "send_command") as mock_send:
            mock_send.return_value = BridgeResult(
                ok=True,
                data=[{"name": "wt2", "value": "abc"}, {"name": "stoken", "value": "def"}, {"name": "bst", "value": "xyz"}],
            )
            cookies = client.get_cookies()
            assert cookies == {"wt2": "abc", "stoken": "def", "bst": "xyz"}

    def test_get_cookies_failure_returns_empty(self):
        client = BridgeClient()
        with patch.object(client, "send_command") as mock_send:
            mock_send.return_value = BridgeResult(ok=False, error="扩展未连接")
            cookies = client.get_cookies()
            assert cookies == {}

    @patch.object(BridgeClient, "is_available", return_value=False)
    def test_get_cookies_daemon_unavailable(self, mock_avail):
        client = BridgeClient()
        cookies = client.get_cookies()
        assert cookies == {}

    def test_get_cookies_creates_correct_command(self):
        client = BridgeClient()
        with patch.object(client, "send_command") as mock_send:
            mock_send.return_value = BridgeResult(ok=True, data={})
            client.get_cookies()
            cmd = mock_send.call_args[0][0]
            assert cmd.type == CommandType.GET_COOKIES


class TestBridgeClientAsync:
    @patch.object(BridgeClient, "is_available", return_value=False)
    @pytest.mark.asyncio
    async def test_send_command_async_unavailable(self, mock_avail):
        client = BridgeClient()
        cmd = BridgeCommand(type=CommandType.PING, id="1")
        result = await client.send_command_async(cmd)
        assert result.ok is False
        assert "不可用" in result.error

    @patch.object(BridgeClient, "is_available", return_value=True)
    @patch.object(BridgeClient, "_ws_send", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_send_command_async_success(self, mock_ws, mock_avail):
        mock_ws.return_value = {"ok": True, "data": {"cookies": []}, "id": "abc"}
        client = BridgeClient()
        cmd = BridgeCommand(type=CommandType.GET_COOKIES, id="abc")
        result = await client.send_command_async(cmd)
        assert result.ok is True
        assert result.data == {"cookies": []}
        assert result.id == "abc"

    @patch.object(BridgeClient, "is_available", return_value=True)
    @patch.object(BridgeClient, "_ws_send", new_callable=AsyncMock, side_effect=Exception("ws 断开"))
    @pytest.mark.asyncio
    async def test_send_command_async_error(self, mock_ws, mock_avail):
        client = BridgeClient()
        cmd = BridgeCommand(type=CommandType.PING, id="1")
        result = await client.send_command_async(cmd)
        assert result.ok is False
        assert "ws 断开" in result.error


class TestBridgeClientSyncFromAsync:
    @patch.object(BridgeClient, "is_available", return_value=True)
    @patch.object(BridgeClient, "_ws_send", new_callable=AsyncMock)
    @pytest.mark.asyncio
    async def test_send_command_from_async_context(self, mock_ws, mock_avail):
        mock_ws.return_value = {"ok": True, "data": {"url": "https://zhipin.com"}, "id": "42"}
        client = BridgeClient()
        cmd = BridgeCommand(type=CommandType.NAVIGATE, params={"url": "https://zhipin.com"}, id="42")
        result = await asyncio.to_thread(client.send_command, cmd)
        assert result.ok is True
        assert result.data == {"url": "https://zhipin.com"}

    @patch.object(BridgeClient, "is_available", return_value=True)
    @patch.object(BridgeClient, "_ws_send", new_callable=AsyncMock)
    def test_send_command_from_sync_context(self, mock_ws, mock_avail):
        mock_ws.return_value = {"ok": True, "data": {"url": "https://zhipin.com"}, "id": "42"}
        client = BridgeClient()
        cmd = BridgeCommand(type=CommandType.NAVIGATE, params={"url": "https://zhipin.com"}, id="42")
        result = client.send_command(cmd)
        assert result.ok is True
        assert result.data == {"url": "https://zhipin.com"}
