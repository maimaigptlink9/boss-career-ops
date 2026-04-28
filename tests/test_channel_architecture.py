"""
防御测试：防止浏览器通道架构混淆的 bug 再次发生。

根因回顾：
1. Bridge 是"命令转发"通道，不提供浏览器上下文（_context），
   但旧代码把它放进 ensure_connected() 降级链（与 CDP/Patchright 并列），
   导致 Bridge 返回 True 后 _context 仍为 None，get_page() 必定失败。

2. BrowserClient 初始化时 bridge_url 默认为 None，
   导致 _connect_bridge() 第一行就返回 False，Bridge 通道完全不可用。
   而 AuthManager 用的是独立的 BridgeClient（有默认 URL），所以登录不受影响。

3. Adapter 层的 apply() 用 BridgeClient().is_available() 检查 Bridge，
   但这个检查与 BrowserClient 无关，两者状态不同步。

防御策略：
- 确保 ensure_connected() 降级链中每个方法都建立 _context
- 确保 BrowserClient 默认 bridge_url 不为 None
- 确保 Adapter 操作优先走 Bridge，而非 Patchright
- 确保 registry 创建 adapter 时配置传递完整
"""

import inspect
from unittest.mock import MagicMock, patch

import pytest

from boss_career_ops.boss.browser_client import BrowserClient, DEFAULT_BRIDGE_URL
from boss_career_ops.config.singleton import SingletonMeta


@pytest.fixture(autouse=True)
def _reset_singletons():
    for cls in [BrowserClient]:
        SingletonMeta._instances.pop(cls, None)
    yield
    for cls in [BrowserClient]:
        SingletonMeta._instances.pop(cls, None)


class TestEnsureConnectedChainEstablishesContext:
    """
    防御：ensure_connected() 降级链中的每个方法都必须建立 _context。
    
    如果某个方法返回 True 但 _context 仍为 None，
    后续 get_page() 调用 self._context.new_page() 会抛 AttributeError。
    这正是旧 bug 的核心：_connect_bridge 返回 True 但不建立 _context。
    """

    def test_all_methods_in_chain_establish_context(self):
        bc = BrowserClient()
        source = inspect.getsource(bc.ensure_connected)
        method_names = []
        for line in source.split("\n"):
            line = line.strip()
            if "self._connect_" in line and "(" in line:
                start = line.index("self._connect_") + len("self._connect_")
                end = line.index("(", start)
                method_names.append(line[start:end])

        for name in method_names:
            method = getattr(bc, f"_connect_{name}")
            source = inspect.getsource(method)
            assert "self._context" in source, (
                f"_connect_{name} 返回 True 但未设置 self._context，"
                f"这会导致 get_page() 调用 None.new_page() 抛出 AttributeError。"
                f"如果该方法是命令转发通道（如 Bridge），不应放入 ensure_connected() 降级链。"
            )

    def test_bridge_not_in_ensure_connected_chain(self):
        """
        防御：Bridge 不应在 ensure_connected() 降级链中。
        Bridge 是命令转发通道，不提供浏览器上下文。
        """
        bc = BrowserClient()
        source = inspect.getsource(bc.ensure_connected)
        assert "_connect_bridge" not in source, (
            "Bridge 不应在 ensure_connected() 降级链中。"
            "Bridge 是命令转发通道（navigate/click/get_cookies），不提供 _context。"
            "应通过 is_bridge_available() 单独检查，操作层优先走 Bridge。"
        )

    def test_ensure_connected_returns_true_implies_context_not_none(self):
        """
        防御：ensure_connected() 返回 True 时，_context 必须不为 None。
        """
        bc = BrowserClient()
        with patch.object(bc, "_connect_cdp", return_value=True) as mock_cdp:
            mock_cdp.side_effect = lambda: (
                setattr(bc, "_context", MagicMock()),
                True,
            )[1]
            result = bc.ensure_connected()
            assert result is True
            assert bc._context is not None, (
                "ensure_connected() 返回 True 但 _context 为 None，"
                "后续 get_page() 会抛出异常。"
            )


class TestBrowserClientDefaultBridgeUrl:
    """
    防御：BrowserClient 的 bridge_url 默认值不能为 None。
    
    旧 bug 中 bridge_url 默认 None，导致 _connect_bridge() 第一行返回 False，
    Bridge 通道完全不可用。而 AuthManager 用独立的 BridgeClient（有默认 URL），
    所以登录走 Bridge 成功，但操作走 Patchright 失败。
    """

    def test_default_bridge_url_not_none(self):
        bc = BrowserClient()
        assert bc._bridge_url is not None, (
            "BrowserClient._bridge_url 不能默认为 None。"
            "否则 Bridge 通道在 BrowserClient 层面完全不可用，"
            "而 AuthManager 用独立的 BridgeClient（有默认 URL），"
            "导致登录走 Bridge 成功但操作走 Patchright。"
        )

    def test_default_bridge_url_matches_bridge_client(self):
        """
        防御：BrowserClient 的默认 bridge_url 必须与 BridgeClient 一致。
        """
        from boss_career_ops.bridge.client import DEFAULT_BRIDGE_URL as BRIDGE_CLIENT_URL
        assert DEFAULT_BRIDGE_URL == BRIDGE_CLIENT_URL, (
            f"BrowserClient 默认 bridge_url ({DEFAULT_BRIDGE_URL}) "
            f"与 BridgeClient 默认 URL ({BRIDGE_CLIENT_URL}) 不一致，"
            f"会导致两者连接不同的 Daemon 实例。"
        )

    def test_bridge_url_fallback_when_none(self):
        SingletonMeta._instances.pop(BrowserClient, None)
        bc = BrowserClient(bridge_url=None)
        assert bc._bridge_url == DEFAULT_BRIDGE_URL, (
            "bridge_url=None 时应回退到默认值，而非保持 None。"
        )


class TestAdapterBridgePriorityOverPatchright:
    """
    防御：Adapter 的浏览器操作必须优先走 Bridge，而非 Patchright。
    
    旧 bug 中 apply() 用 BridgeClient().is_available() 检查 Bridge，
    但 BridgeClient 和 BrowserClient 状态不同步。
    修复后改用 BrowserClient.is_bridge_available()，确保一致性。
    """

    def test_apply_checks_bridge_via_browser_client(self):
        """
        防御：apply() 必须通过 BrowserClient.is_bridge_available() 检查 Bridge，
        而非独立的 BridgeClient().is_available()。
        """
        from boss_career_ops.platform.adapters.boss.adapter import BossAdapter
        source = inspect.getsource(BossAdapter.apply)
        assert "is_bridge_available" in source, (
            "apply() 应通过 BrowserClient.is_bridge_available() 检查 Bridge 状态，"
            "而非独立的 BridgeClient().is_available()。"
            "后者与 BrowserClient 状态不同步，会导致登录走 Bridge 但操作走 Patchright。"
        )

    def test_upload_checks_bridge_via_browser_client(self):
        """
        防御：upload() 必须通过 BrowserClient.is_bridge_available() 检查 Bridge。
        """
        from boss_career_ops.resume.upload import ResumeUploader
        source = inspect.getsource(ResumeUploader.upload)
        assert "is_bridge_available" in source, (
            "upload() 应通过 BrowserClient.is_bridge_available() 检查 Bridge 状态。"
        )


class TestRegistryAdapterConfigPropagation:
    """
    防御：registry 创建 adapter 时必须传递完整配置。
    
    旧 bug 中 get_active_adapter() 调用 adapter_class() 不传任何参数，
    导致 cdp_url 和 bridge_url 都为 None。
    """

    def test_adapter_default_bridge_url_not_none(self):
        """
        防御：即使 registry 不传 bridge_url，adapter 内部的 BrowserClient
        也必须有有效的 bridge_url（通过默认值）。
        """
        from boss_career_ops.platform.adapters.boss.adapter import BossAdapter
        adapter = BossAdapter()
        assert adapter._browser.inner._bridge_url is not None, (
            "BossAdapter 内部 BrowserClient 的 bridge_url 不能为 None。"
            "registry 创建 adapter 时不传 bridge_url，BrowserClient 必须有默认值。"
        )

    def test_adapter_default_bridge_url_equals_daemon_port(self):
        from boss_career_ops.platform.adapters.boss.adapter import BossAdapter
        adapter = BossAdapter()
        assert "18765" in adapter._browser.inner._bridge_url, (
            "BossAdapter 内部 BrowserClient 的 bridge_url 必须指向 Bridge Daemon 端口 18765。"
        )


class TestBridgeAvailabilityChecksExtensions:
    """
    防御：is_bridge_available() 必须检查扩展连接数，而非仅检查 Daemon 在线。
    
    Daemon 在线但无扩展连接时，Bridge 命令无法执行（无执行者）。
    """

    def test_bridge_available_requires_extensions_connected(self):
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
            assert bc.is_bridge_available() is False, (
                "Daemon 在线但无扩展连接时，is_bridge_available() 应返回 False。"
                "Bridge 命令需要扩展执行，无扩展时命令无法完成。"
            )

    def test_bridge_available_with_extensions_connected(self):
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

    def test_is_bridge_available_uses_proxy_none(self):
        """
        防御：本地请求必须绕过代理，否则代理拦截返回 502。
        """
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
            bc.is_bridge_available()
            mock_client_cls.assert_called_with(proxy=None)
