from unittest.mock import patch, MagicMock

from boss_career_ops.bridge.client import BridgeClient, DEFAULT_BRIDGE_URL
from boss_career_ops.bridge.protocol import BridgeCommand, CommandType, BridgeResult


class TestBridgeClient:
    def test_init_default_url(self):
        client = BridgeClient()
        assert client._bridge_url == DEFAULT_BRIDGE_URL.rstrip("/")

    def test_init_custom_url(self):
        client = BridgeClient(bridge_url="http://localhost:9999/")
        assert client._bridge_url == "http://localhost:9999"

    @patch("boss_career_ops.bridge.client.httpx.get")
    def test_is_available_true(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_get.return_value = mock_resp
        client = BridgeClient()
        assert client.is_available() is True

    @patch("boss_career_ops.bridge.client.httpx.get")
    def test_is_available_false(self, mock_get):
        mock_get.side_effect = Exception("connection refused")
        client = BridgeClient()
        assert client.is_available() is False

    @patch.object(BridgeClient, "is_available", return_value=False)
    def test_send_command_unavailable(self, mock_avail):
        client = BridgeClient()
        cmd = BridgeCommand(type=CommandType.PING, id="1")
        result = client.send_command(cmd)
        assert result.ok is False
        assert "不可用" in result.error

    def test_get_cookies_creates_command(self):
        client = BridgeClient()
        with patch.object(client, "send_command") as mock_send:
            mock_send.return_value = BridgeResult(ok=True, data="cookies")
            result = client.get_cookies()
            mock_send.assert_called_once()
            cmd = mock_send.call_args[0][0]
            assert cmd.type == CommandType.GET_COOKIES

    def test_navigate_creates_command(self):
        client = BridgeClient()
        with patch.object(client, "send_command") as mock_send:
            mock_send.return_value = BridgeResult(ok=True)
            client.navigate("https://zhipin.com")
            cmd = mock_send.call_args[0][0]
            assert cmd.type == CommandType.NAVIGATE
            assert cmd.params["url"] == "https://zhipin.com"
