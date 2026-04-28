"""验证 Cookie 获取一致性修复的测试用例

覆盖：
- _inject_stoken(cookies=...) 使用传入值
- _build_headers(cookies=...) 使用传入值
- request() 内部 _get_cookies 仅调用一次 per iteration
- _get_cookies() Bridge Cookie 回写 TokenStore
- AuthManager.check_status() 在线/离线两种场景
"""

from unittest.mock import patch, MagicMock, call

from boss_career_ops.boss.api.client import BossClient
from boss_career_ops.boss.auth.manager import AuthManager


class TestInjectStokenCookiesParam:
    """验证 _inject_stoken 使用传入的 cookies 参数"""

    def test_uses_passed_cookies(self):
        client = BossClient()
        client._get_cookies = MagicMock(return_value={"__zp_stoken__": "should_not_use"})
        result = client._inject_stoken({"key": "val"}, cookies={"__zp_stoken__": "from_param"})
        assert result["__zp_stoken__"] == "from_param"
        client._get_cookies.assert_not_called()

    def test_falls_back_to_get_cookies_when_none(self):
        client = BossClient()
        client._get_cookies = MagicMock(return_value={"__zp_stoken__": "from_fallback"})
        result = client._inject_stoken({"key": "val"})
        assert result["__zp_stoken__"] == "from_fallback"
        client._get_cookies.assert_called_once()

    def test_empty_cookies_dict(self):
        client = BossClient()
        result = client._inject_stoken(None, cookies={})
        assert "__zp_stoken__" not in result


class TestBuildHeadersCookiesParam:
    """验证 _build_headers 使用传入的 cookies 参数"""

    def test_uses_passed_cookies_for_zp_token(self):
        client = BossClient()
        client._get_cookies = MagicMock(return_value={"bst": "should_not_use"})
        headers = client._build_headers("search", cookies={"bst": "from_param"})
        assert headers["zp_token"] == "from_param"
        client._get_cookies.assert_not_called()

    def test_falls_back_to_get_cookies_when_none(self):
        client = BossClient()
        client._get_cookies = MagicMock(return_value={"bst": "from_fallback"})
        headers = client._build_headers("search")
        assert headers["zp_token"] == "from_fallback"
        client._get_cookies.assert_called_once()

    def test_no_bst_in_passed_cookies(self):
        client = BossClient()
        headers = client._build_headers("search", cookies={"wt2": "val"})
        assert "zp_token" not in headers


class TestRequestCookieConsistency:
    """验证 request() 每次迭代只调用一次 _get_cookies"""

    @patch("boss_career_ops.boss.api.client.httpx.Client")
    def test_get_cookies_called_once_per_attempt(self, mock_client_cls):
        client = BossClient()
        client._gaussian_delay = MagicMock()
        client._get_cookies = MagicMock(return_value={})

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"code": 0, "message": "Success"}

        mock_httpx_client = MagicMock()
        mock_httpx_client.__enter__ = MagicMock(return_value=mock_httpx_client)
        mock_httpx_client.__exit__ = MagicMock(return_value=False)
        mock_httpx_client.get.return_value = mock_resp
        mock_httpx_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_httpx_client

        result = client.request("search", json_data={"query": "Python"})

        assert result.get("code") == 0
        client._get_cookies.assert_called_once()

    @patch("boss_career_ops.boss.api.client.httpx.Client")
    def test_cookies_passed_to_inject_stoken_and_build_headers(self, mock_client_cls):
        client = BossClient()
        client._gaussian_delay = MagicMock()
        test_cookies = {"wt2": "val", "__zp_stoken__": "stoken_val", "bst": "bst_val"}
        client._get_cookies = MagicMock(return_value=test_cookies)
        client._inject_stoken = MagicMock(side_effect=lambda p, cookies=None: p if p else {})
        client._build_headers = MagicMock(return_value={})

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"code": 0, "message": "Success"}

        mock_httpx_client = MagicMock()
        mock_httpx_client.__enter__ = MagicMock(return_value=mock_httpx_client)
        mock_httpx_client.__exit__ = MagicMock(return_value=False)
        mock_httpx_client.get.return_value = mock_resp
        mock_httpx_client.post.return_value = mock_resp
        mock_client_cls.return_value = mock_httpx_client

        result = client.request("search", json_data={"query": "Python"})

        assert result.get("code") == 0
        client._inject_stoken.assert_called_once()
        call_args = client._inject_stoken.call_args
        assert call_args[1]["cookies"] == test_cookies

        client._build_headers.assert_called_once()
        build_call_args = client._build_headers.call_args
        assert build_call_args[1]["cookies"] == test_cookies


class TestGetCookiesWriteback:
    """验证 _get_cookies() Bridge Cookie 回写 TokenStore"""

    def _make_client(self):
        """创建 BossClient 并恢复真实的 _get_cookies 方法"""
        client = BossClient()
        # 恢复真实的 _get_cookies 方法（Singleton 可能被之前的测试 mock 了）
        client._get_cookies = BossClient._get_cookies.__get__(client, BossClient)
        client._token_store = MagicMock()
        return client

    @patch("boss_career_ops.bridge.client.BridgeClient")
    def test_writeback_on_bridge_success(self, mock_bridge_cls):
        mock_bridge = MagicMock()
        mock_bridge.is_available.return_value = True
        mock_bridge.get_cookies.return_value = {"wt2": "fresh", "__zp_stoken__": "fresh_st"}
        mock_bridge_cls.return_value = mock_bridge

        client = self._make_client()
        cookies = client._get_cookies()

        assert cookies == {"wt2": "fresh", "__zp_stoken__": "fresh_st"}
        client._token_store.save.assert_called_once_with({"wt2": "fresh", "__zp_stoken__": "fresh_st"})

    @patch("boss_career_ops.bridge.client.BridgeClient")
    def test_writeback_failure_does_not_affect_return(self, mock_bridge_cls):
        mock_bridge = MagicMock()
        mock_bridge.is_available.return_value = True
        mock_bridge.get_cookies.return_value = {"wt2": "fresh"}
        mock_bridge_cls.return_value = mock_bridge

        client = self._make_client()
        client._token_store.save.side_effect = Exception("disk full")

        cookies = client._get_cookies()

        assert cookies == {"wt2": "fresh"}
        client._token_store.save.assert_called_once()

    @patch("boss_career_ops.bridge.client.BridgeClient")
    def test_no_writeback_when_bridge_unavailable(self, mock_bridge_cls):
        mock_bridge = MagicMock()
        mock_bridge.is_available.return_value = False
        mock_bridge_cls.return_value = mock_bridge

        client = self._make_client()
        client._token_store.load.return_value = {"wt2": "old"}

        cookies = client._get_cookies()

        assert cookies == {"wt2": "old"}
        client._token_store.save.assert_not_called()


class TestCheckStatusOnlineOffline:
    """验证 AuthManager.check_status() 区分在线/离线状态"""

    @patch("boss_career_ops.bridge.client.BridgeClient")
    def test_online_cookie_valid(self, mock_bridge_cls):
        mock_bridge = MagicMock()
        mock_bridge.is_available.return_value = True
        mock_bridge.get_cookies.return_value = {"wt2": "val", "__zp_stoken__": "val"}
        mock_bridge_cls.return_value = mock_bridge

        auth = AuthManager()
        result = auth.check_status()

        assert result["ok"] is True
        assert "在线" in result["message"]
        assert "实时有效" in result["message"]

    @patch("boss_career_ops.bridge.client.BridgeClient")
    def test_online_cookie_incomplete(self, mock_bridge_cls):
        mock_bridge = MagicMock()
        mock_bridge.is_available.return_value = True
        mock_bridge.get_cookies.return_value = {"wt2": "val"}
        mock_bridge_cls.return_value = mock_bridge

        auth = AuthManager()
        result = auth.check_status()

        assert result["ok"] is False
        assert "在线" in result["message"]
        assert "stoken" in result["missing"]

    @patch("boss_career_ops.bridge.client.BridgeClient")
    def test_online_empty_cookies(self, mock_bridge_cls):
        mock_bridge = MagicMock()
        mock_bridge.is_available.return_value = True
        mock_bridge.get_cookies.return_value = {}
        mock_bridge_cls.return_value = mock_bridge

        auth = AuthManager()
        result = auth.check_status()

        assert result["ok"] is False
        assert "在线" in result["message"]
        assert "空 Cookie" in result["message"]

    @patch("boss_career_ops.bridge.client.BridgeClient")
    def test_offline_token_valid(self, mock_bridge_cls):
        mock_bridge = MagicMock()
        mock_bridge.is_available.return_value = False
        mock_bridge_cls.return_value = mock_bridge

        auth = AuthManager()
        auth._token_store = MagicMock()
        auth._token_store.check_quality.return_value = {"ok": True, "missing": []}

        result = auth.check_status()

        assert result["ok"] is True
        assert "离线" in result["message"]
        assert "时效未知" in result["message"]

    @patch("boss_career_ops.bridge.client.BridgeClient")
    def test_offline_no_token(self, mock_bridge_cls):
        mock_bridge = MagicMock()
        mock_bridge.is_available.return_value = False
        mock_bridge_cls.return_value = mock_bridge

        auth = AuthManager()
        auth._token_store = MagicMock()
        auth._token_store.check_quality.return_value = {"ok": False, "missing": ["all"]}

        result = auth.check_status()

        assert result["ok"] is False
        assert "离线" in result["message"]
        assert "bco login" in result["message"]

    @patch("boss_career_ops.bridge.client.BridgeClient")
    def test_bridge_exception_falls_back_to_offline(self, mock_bridge_cls):
        mock_bridge_cls.side_effect = ImportError("no bridge")

        auth = AuthManager()
        auth._token_store = MagicMock()
        auth._token_store.check_quality.return_value = {"ok": True, "missing": []}

        result = auth.check_status()

        assert result["ok"] is True
        assert "离线" in result["message"]
