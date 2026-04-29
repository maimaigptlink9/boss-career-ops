"""验证风控降级与响应解析修复的测试用例

覆盖三项修复：
- P0: BossAdapter.get_job_detail 使用 code==0 和 zpData 解析响应
- P1: BossClient.request() 风控拦截时对 BROWSER_FALLBACK_ENDPOINTS 尝试浏览器降级
- P2: RISK_CONTROL_KEYWORDS 不再包含单独的 "异常"，改为 "操作异常"
"""

from unittest.mock import patch, MagicMock

from boss_career_ops.platform.adapters.boss.adapter import BossAdapter
from boss_career_ops.boss.api.client import (
    BossClient,
    RISK_CONTROL_KEYWORDS,
    BROWSER_FALLBACK_ENDPOINTS,
)


# ============================================================
# P0: BossAdapter.get_job_detail 响应解析修复
# ============================================================


class TestBossAdapterGetJobDetailResponseParsing:
    """验证 BossAdapter.get_job_detail 使用 code==0 + zpData 解析响应"""

    def test_returns_job_when_code_is_zero(self):
        """code == 0 时返回 Job 模型"""
        adapter = BossAdapter.__new__(BossAdapter)
        adapter._client = MagicMock()
        adapter._auth = MagicMock()
        adapter._mapper = MagicMock()
        adapter._browser = MagicMock()
        adapter._client.get.return_value = {
            "code": 0,
            "zpData": {"jobInfo": {"jobName": "AI工程师", "postDescription": "负责Agent开发", "encryptJobId": "jid1"}},
            "message": "Success",
        }
        mock_job = MagicMock()
        adapter._mapper.map_job.return_value = mock_job

        result = adapter.get_job_detail("sec123")
        assert result is mock_job

    def test_returns_none_when_code_nonzero(self):
        """code != 0 时返回 None"""
        adapter = BossAdapter.__new__(BossAdapter)
        adapter._client = MagicMock()
        adapter._auth = MagicMock()
        adapter._mapper = MagicMock()
        adapter._browser = MagicMock()
        adapter._client.get.return_value = {
            "code": 1,
            "message": "参数错误",
        }

        result = adapter.get_job_detail("sec456")
        assert result is None

    def test_returns_none_when_zpData_missing(self):
        """code == 0 但 zpData 缺失时返回 None"""
        adapter = BossAdapter.__new__(BossAdapter)
        adapter._client = MagicMock()
        adapter._auth = MagicMock()
        adapter._mapper = MagicMock()
        adapter._browser = MagicMock()
        adapter._client.get.return_value = {
            "code": 0,
            "message": "Success",
        }

        result = adapter.get_job_detail("sec789")
        assert result is None

    def test_does_not_use_ok_field(self):
        """确认不再依赖 ok 字段——即使 ok=True 但 code!=0 也返回 None"""
        adapter = BossAdapter.__new__(BossAdapter)
        adapter._client = MagicMock()
        adapter._auth = MagicMock()
        adapter._mapper = MagicMock()
        adapter._browser = MagicMock()
        adapter._client.get.return_value = {
            "ok": True,
            "code": 7,
            "message": "参数错误",
        }

        result = adapter.get_job_detail("sec_old_format")
        assert result is None


# ============================================================
# P1: BossClient.request() 统一浏览器降级
# ============================================================


class TestBossClientBrowserFallback:
    """验证 BossClient.request() 风控拦截时对 BROWSER_FALLBACK_ENDPOINTS 降级"""

    def _make_client_with_mocked_httpx(self, resp_status, resp_json):
        """构造一个 mock 了 httpx 请求的 BossClient 实例"""
        client = BossClient()
        client._gaussian_delay = MagicMock()
        client._get_cookies = MagicMock(return_value={})
        client._build_headers = MagicMock(return_value={})
        client._inject_stoken = MagicMock(side_effect=lambda p, cookies=None: p if p else {})

        mock_resp = MagicMock()
        mock_resp.status_code = resp_status
        mock_resp.json.return_value = resp_json

        mock_httpx_client = MagicMock()
        mock_httpx_client.__enter__ = MagicMock(return_value=mock_httpx_client)
        mock_httpx_client.__exit__ = MagicMock(return_value=False)
        mock_httpx_client.get.return_value = mock_resp
        mock_httpx_client.post.return_value = mock_resp

        return client, mock_httpx_client

    @patch("boss_career_ops.boss.api.client.httpx.Client")
    def test_risk_blocked_fallback_to_browser_for_user_info(self, mock_client_cls):
        """风控拦截 user_info 端点时尝试浏览器降级"""
        risk_response = {
            "code": 99,
            "message": "环境存在异常，请稍后再试",
        }

        client, mock_httpx_client = self._make_client_with_mocked_httpx(200, risk_response)
        mock_client_cls.return_value = mock_httpx_client

        browser_result = {"code": 0, "zpData": {"userName": "降级成功"}}
        client._request_via_browser = MagicMock(return_value=browser_result)

        result = client.request("user_info")

        client._request_via_browser.assert_called_once_with("user_info", {}, json_data=None)
        assert result == browser_result

    @patch("boss_career_ops.boss.api.client.httpx.Client")
    def test_risk_blocked_no_fallback_for_non_browser_endpoint(self, mock_client_cls):
        """风控拦截非 BROWSER_FALLBACK_ENDPOINTS 端点时不尝试浏览器降级"""
        risk_response = {
            "code": 99,
            "message": "访问行为异常，请稍后再试",
        }

        client, mock_httpx_client = self._make_client_with_mocked_httpx(200, risk_response)
        mock_client_cls.return_value = mock_httpx_client

        client._request_via_browser = MagicMock(return_value=None)

        result = client.request("greet", json_data={"securityId": "test", "jobId": "test"})

        client._request_via_browser.assert_not_called()
        assert result.get("_risk_blocked") is True

    @patch("boss_career_ops.boss.api.client.httpx.Client")
    def test_risk_blocked_browser_fallback_failure(self, mock_client_cls):
        """风控拦截后浏览器降级也失败时返回原始风控响应"""
        risk_response = {
            "code": 99,
            "message": "操作异常，请稍后再试",
        }

        client, mock_httpx_client = self._make_client_with_mocked_httpx(200, risk_response)
        mock_client_cls.return_value = mock_httpx_client

        client._request_via_browser = MagicMock(return_value=None)

        result = client.request("user_info")

        client._request_via_browser.assert_called_once()
        assert result.get("_risk_blocked") is True
        assert result.get("code") == 99

    @patch("boss_career_ops.boss.api.client.httpx.Client")
    def test_no_fallback_when_not_risk_blocked(self, mock_client_cls):
        """正常响应时不触发浏览器降级"""
        normal_response = {
            "code": 0,
            "zpData": {"jobList": []},
            "message": "Success",
        }

        client, mock_httpx_client = self._make_client_with_mocked_httpx(200, normal_response)
        mock_client_cls.return_value = mock_httpx_client

        client._request_via_browser = MagicMock(return_value=None)

        result = client.request("job_detail", params={"securityId": "sec123"})

        client._request_via_browser.assert_not_called()
        assert result.get("code") == 0


# ============================================================
# P2: RISK_CONTROL_KEYWORDS 修复
# ============================================================


class TestRiskControlKeywords:
    """验证 RISK_CONTROL_KEYWORDS 不包含单独的 '异常'，改为 '操作异常'"""

    def test_keywords_do_not_contain_standalone_anomaly(self):
        """RISK_CONTROL_KEYWORDS 不应包含单独的 '异常'"""
        assert "异常" not in RISK_CONTROL_KEYWORDS

    def test_keywords_contain_operation_anomaly(self):
        """RISK_CONTROL_KEYWORDS 应包含 '操作异常'"""
        assert "操作异常" in RISK_CONTROL_KEYWORDS

    def test_standalone_anomaly_does_not_trigger_risk(self):
        """单独的 '异常' 不应触发风控检测"""
        client = BossClient()
        resp_data = {"code": 1, "message": "系统异常"}
        assert client._is_risk_blocked(resp_data) is False

    def test_operation_anomaly_triggers_risk(self):
        """'操作异常' 应触发风控检测"""
        client = BossClient()
        resp_data = {"code": 1, "message": "操作异常，请稍后再试"}
        assert client._is_risk_blocked(resp_data) is True

    def test_environment_anomaly_triggers_risk(self):
        """'环境存在异常' 应触发风控检测"""
        client = BossClient()
        resp_data = {"code": 1, "message": "环境存在异常，请稍后再试"}
        assert client._is_risk_blocked(resp_data) is True

    def test_browser_fallback_endpoints_include_search_and_user_info(self):
        """BROWSER_FALLBACK_ENDPOINTS 应包含 search 和 user_info"""
        assert "search" in BROWSER_FALLBACK_ENDPOINTS
        assert "user_info" in BROWSER_FALLBACK_ENDPOINTS
