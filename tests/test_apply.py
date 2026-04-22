from unittest.mock import MagicMock, patch, AsyncMock

from boss_career_ops.platform.adapters.boss.adapter import BossAdapter
from boss_career_ops.display.error_codes import ErrorCode


class TestBossAdapterApplyViaBridge:
    def test_bridge_navigate_fail(self):
        adapter = BossAdapter.__new__(BossAdapter)
        adapter._client = MagicMock()
        adapter._auth = MagicMock()
        adapter._mapper = MagicMock()
        adapter._browser = MagicMock()
        bridge = MagicMock()
        bridge.navigate.return_value = MagicMock(ok=False, error="连接失败")
        result = adapter._apply_via_bridge(bridge, "sid123", "jid456")
        assert result.ok is False
        assert "连接失败" in result.message

    def test_bridge_apply_success(self):
        adapter = BossAdapter.__new__(BossAdapter)
        adapter._client = MagicMock()
        adapter._auth = MagicMock()
        adapter._mapper = MagicMock()
        adapter._browser = MagicMock()
        bridge = MagicMock()
        bridge.navigate.return_value = MagicMock(ok=True)
        bridge.click.return_value = MagicMock(ok=True)
        result = adapter._apply_via_bridge(bridge, "sid123", "jid456")
        assert result.ok is True


class TestBossAdapterApplyViaPatchright:
    def test_patchright_apply_success(self):
        mock_page = MagicMock()
        mock_apply_btn = MagicMock()
        mock_page.query_selector.side_effect = [mock_apply_btn, None, None]
        browser = MagicMock()
        browser.get_page.return_value = mock_page
        adapter = BossAdapter.__new__(BossAdapter)
        adapter._client = MagicMock()
        adapter._auth = MagicMock()
        adapter._mapper = MagicMock()
        adapter._browser = MagicMock()
        result = adapter._apply_via_patchright(browser, "sid123", "jid456")
        assert result.ok is True
        assert "浏览器通道" in result.message
        mock_page.close.assert_called()

    def test_patchright_no_apply_button(self):
        mock_page = MagicMock()
        mock_page.query_selector.return_value = None
        browser = MagicMock()
        browser.get_page.return_value = mock_page
        adapter = BossAdapter.__new__(BossAdapter)
        adapter._client = MagicMock()
        adapter._auth = MagicMock()
        adapter._mapper = MagicMock()
        adapter._browser = MagicMock()
        result = adapter._apply_via_patchright(browser, "sid123", "jid456")
        assert result.ok is False
        assert result.code == ErrorCode.APPLY_BROWSER_ERROR

    def test_patchright_chat_button_fallback(self):
        mock_page = MagicMock()
        mock_chat_btn = MagicMock()
        mock_page.query_selector.side_effect = [None, None, mock_chat_btn]
        browser = MagicMock()
        browser.get_page.return_value = mock_page
        adapter = BossAdapter.__new__(BossAdapter)
        adapter._client = MagicMock()
        adapter._auth = MagicMock()
        adapter._mapper = MagicMock()
        adapter._browser = MagicMock()
        result = adapter._apply_via_patchright(browser, "sid123", "jid456")
        assert result.ok is True
        assert "沟通按钮" in result.message
