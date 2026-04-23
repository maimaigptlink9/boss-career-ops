from unittest.mock import patch, MagicMock

from boss_career_ops.boss.api.client import BossClient


class TestRefererSpoofing:
    """验证 _build_headers 对不同端点返回正确的 Referer"""

    def _make_client(self):
        client = BossClient()
        client._get_cookies = MagicMock(return_value={})
        return client

    def test_search_no_query(self):
        client = self._make_client()
        headers = client._build_headers("search", {})
        assert headers["Referer"] == "https://www.zhipin.com/web/geek/job"

    def test_search_with_query(self):
        client = self._make_client()
        headers = client._build_headers("search", {"query": "Python"})
        assert headers["Referer"] == "https://www.zhipin.com/web/geek/job?query=Python"

    def test_recommend(self):
        client = self._make_client()
        headers = client._build_headers("recommend")
        assert headers["Referer"] == "https://www.zhipin.com/web/geek/recommend"

    def test_recommend_v2(self):
        client = self._make_client()
        headers = client._build_headers("recommend_v2")
        assert headers["Referer"] == "https://www.zhipin.com/web/geek/recommend"

    def test_job_detail(self):
        client = self._make_client()
        headers = client._build_headers("job_detail")
        assert headers["Referer"] == "https://www.zhipin.com/web/geek/job"

    def test_chat_list(self):
        client = self._make_client()
        headers = client._build_headers("chat_list")
        assert headers["Referer"] == "https://www.zhipin.com/web/geek/chat"

    def test_unknown_endpoint_uses_default_referer(self):
        client = self._make_client()
        headers = client._build_headers("unknown_endpoint")
        assert "Referer" in headers


class TestZpToken:
    """验证 zp_token 从 cookie bst 中提取"""

    def test_zp_token_present_when_bst_in_cookies(self):
        client = BossClient()
        client._get_cookies = MagicMock(return_value={"bst": "test_bst_value"})
        headers = client._build_headers("search")
        assert headers.get("zp_token") == "test_bst_value"

    def test_zp_token_absent_when_no_bst(self):
        client = BossClient()
        client._get_cookies = MagicMock(return_value={})
        headers = client._build_headers("search")
        assert "zp_token" not in headers


class TestRateLimitCooldown:
    """验证限流计数器和冷却公式"""

    def test_initial_rate_limit_count_is_zero(self):
        client = BossClient()
        assert client._rate_limit_count == 0

    def test_first_cooldown_is_10_seconds(self):
        client = BossClient()
        client._rate_limit_count = 0
        client._rate_limit_count += 1
        cooldown = min(60, 10 * (2 ** (client._rate_limit_count - 1)))
        assert cooldown == 10

    def test_second_cooldown_is_20_seconds(self):
        client = BossClient()
        client._rate_limit_count = 1
        client._rate_limit_count += 1
        cooldown = min(60, 10 * (2 ** (client._rate_limit_count - 1)))
        assert cooldown == 20

    def test_third_cooldown_is_40_seconds(self):
        client = BossClient()
        client._rate_limit_count = 2
        client._rate_limit_count += 1
        cooldown = min(60, 10 * (2 ** (client._rate_limit_count - 1)))
        assert cooldown == 40

    def test_cooldown_capped_at_60_seconds(self):
        client = BossClient()
        client._rate_limit_count = 5
        client._rate_limit_count += 1
        cooldown = min(60, 10 * (2 ** (client._rate_limit_count - 1)))
        assert cooldown == 60

    @patch("boss_career_ops.boss.api.client.httpx.Client")
    def test_rate_limit_count_resets_on_success(self, mock_client_cls):
        client = BossClient()
        client._gaussian_delay = MagicMock()
        client._get_cookies = MagicMock(return_value={})
        client._inject_stoken = MagicMock(side_effect=lambda p, cookies=None: p if p else {})
        client._rate_limit_count = 3

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"code": 0, "message": "Success"}

        mock_httpx_client = MagicMock()
        mock_httpx_client.__enter__ = MagicMock(return_value=mock_httpx_client)
        mock_httpx_client.__exit__ = MagicMock(return_value=False)
        mock_httpx_client.get.return_value = mock_resp
        mock_client_cls.return_value = mock_httpx_client

        result = client.request("search", params={"query": "Python"})

        assert client._rate_limit_count == 0
        assert result.get("code") == 0
