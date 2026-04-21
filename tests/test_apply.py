import asyncio
from unittest.mock import MagicMock, patch, AsyncMock

from boss_career_ops.commands.apply import (
    _apply_via_bridge,
    _apply_via_patchright,
    _apply_via_browser,
)
from boss_career_ops.display.error_codes import ErrorCode


class TestApplyViaBridge:
    def test_bridge_navigate_fail(self):
        bridge = MagicMock()
        bridge.navigate.return_value = MagicMock(ok=False, error="连接失败")
        result = _apply_via_bridge(bridge, "sid123", "jid456")
        assert result["ok"] is False
        assert "连接失败" in result["message"]

    def test_bridge_apply_success(self):
        bridge = MagicMock()
        bridge.navigate.return_value = MagicMock(ok=True)
        bridge.click.return_value = MagicMock(ok=True)
        result = _apply_via_bridge(bridge, "sid123", "jid456")
        assert result["ok"] is True


class TestApplyViaPatchright:
    def test_patchright_apply_success(self):
        mock_page = MagicMock()
        mock_apply_btn = MagicMock()
        mock_page.query_selector.side_effect = [mock_apply_btn, None, None]
        mock_browser = MagicMock()
        mock_browser.get_page.return_value = mock_page
        result = _apply_via_patchright(mock_browser, "sid123", "jid456")
        assert result["ok"] is True
        assert "浏览器通道" in result["message"]
        mock_page.close.assert_called()

    def test_patchright_no_apply_button(self):
        mock_page = MagicMock()
        mock_page.query_selector.return_value = None
        mock_browser = MagicMock()
        mock_browser.get_page.return_value = mock_page
        result = _apply_via_patchright(mock_browser, "sid123", "jid456")
        assert result["ok"] is False
        assert result["code"] == ErrorCode.APPLY_BROWSER_ERROR

    def test_patchright_chat_button_fallback(self):
        mock_page = MagicMock()
        mock_chat_btn = MagicMock()
        mock_page.query_selector.side_effect = [None, None, mock_chat_btn]
        mock_browser = MagicMock()
        mock_browser.get_page.return_value = mock_page
        result = _apply_via_patchright(mock_browser, "sid123", "jid456")
        assert result["ok"] is True
        assert "沟通按钮" in result["message"]


class TestApplyViaBrowser:
    def test_all_channels_unavailable(self):
        with patch("boss_career_ops.commands.apply.BridgeClient") as MockBridge, \
             patch("boss_career_ops.commands.apply.BrowserClient") as MockBrowser, \
             patch("boss_career_ops.commands.apply.HookManager") as MockHook:
            mock_bridge = MockBridge.return_value
            mock_bridge.is_available.return_value = False
            mock_browser = MockBrowser.return_value
            mock_browser.ensure_connected.return_value = False
            mock_hook = MockHook.return_value
            mock_hook.execute_before = AsyncMock(return_value=MagicMock(action=MagicMock(value="pass")))
            result = asyncio.run(_apply_via_browser("sid", "jid"))
            assert result["ok"] is False
            assert result["code"] == ErrorCode.APPLY_BROWSER_ERROR
