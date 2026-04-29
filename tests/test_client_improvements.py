import httpx
import pytest

from boss_career_ops.boss.api.client import BossClient, RATE_LIMITED_CODES
from boss_career_ops.config.singleton import SingletonMeta


@pytest.fixture(autouse=True)
def reset_singleton():
    SingletonMeta._instances.clear()
    yield
    SingletonMeta._instances.clear()


@pytest.fixture
def client():
    return BossClient()


class TestHttpClientPersistence:
    def test_get_http_client_returns_same_instance(self, client):
        c1 = client._get_http_client()
        c2 = client._get_http_client()
        assert c1 is c2

    def test_get_http_client_creates_new_after_close(self, client):
        c1 = client._get_http_client()
        client.close()
        c2 = client._get_http_client()
        assert c1 is not c2

    def test_close_sets_http_client_to_none(self, client):
        client._get_http_client()
        client.close()
        assert client._http_client is None

    def test_close_on_already_closed_is_noop(self, client):
        client.close()
        client.close()
        assert client._http_client is None

    def test_close_on_never_opened_is_noop(self, client):
        client.close()
        assert client._http_client is None

    def test_get_http_client_recreates_after_manual_close(self, client):
        c1 = client._get_http_client()
        c1.close()
        c2 = client._get_http_client()
        assert c1 is not c2
        assert not c2.is_closed

    def test_persisted_client_has_correct_config(self, client):
        c = client._get_http_client()
        assert c._transport is not None
        assert c._timeout.connect == 30.0


class TestHandleRateLimit:
    def test_detects_429_status_code(self, client):
        result = client._handle_rate_limit(0, 3, 429, {})
        assert result is not None
        assert "cooldown" in result
        assert "backoff" in result

    def test_detects_rate_limited_api_code(self, client):
        result = client._handle_rate_limit(0, 3, 0, {"code": 10003})
        assert result is not None

    def test_detects_rate_limit_keyword(self, client):
        result = client._handle_rate_limit(0, 3, 0, {"message": "请求频繁"})
        assert result is not None

    def test_returns_none_when_not_rate_limited(self, client):
        result = client._handle_rate_limit(0, 3, 200, {"code": 0, "message": "success"})
        assert result is None

    def test_returns_none_on_last_attempt(self, client):
        result = client._handle_rate_limit(2, 3, 429, {})
        assert result is None

    def test_increments_rate_limit_count(self, client):
        assert client._rate_limit_count == 0
        client._handle_rate_limit(0, 3, 429, {})
        assert client._rate_limit_count == 1
        client._handle_rate_limit(0, 3, 429, {})
        assert client._rate_limit_count == 2

    def test_cooldown_increases_exponentially(self, client):
        r1 = client._handle_rate_limit(0, 3, 429, {})
        client._rate_limit_count = 2
        r2 = client._handle_rate_limit(0, 3, 429, {})
        assert r2["cooldown"] > r1["cooldown"]

    def test_cooldown_capped_at_60(self, client):
        client._rate_limit_count = 10
        result = client._handle_rate_limit(0, 3, 429, {})
        assert result is not None
        assert result["cooldown"] <= 60


class TestHandleRiskBlock:
    def test_passes_through_normal_response(self, client):
        result = {"code": 0, "message": "success"}
        out = client._handle_risk_block(result, "search", None)
        assert out is result
        assert "_risk_blocked" not in out

    def test_marks_risk_blocked(self, client, mocker):
        mocker.patch.object(client, "_request_via_browser", return_value=None)
        result = {"code": 1, "message": "访问行为异常"}
        out = client._handle_risk_block(result, "chat_list", None)
        assert out["_risk_blocked"] is True

    def test_triggers_browser_fallback_for_supported_endpoint(self, client, mocker):
        browser_result = {"code": 0, "data": "ok"}
        mocker.patch.object(client, "_request_via_browser", return_value=browser_result)
        result = {"code": 1, "message": "环境存在异常"}
        out = client._handle_risk_block(result, "search", None)
        assert out == browser_result

    def test_passes_json_data_to_browser_fallback(self, client, mocker):
        mocker.patch.object(client, "_request_via_browser", return_value={"code": 0})
        result = {"code": 1, "message": "环境存在异常"}
        client._handle_risk_block(result, "search", None, json_data={"query": "Python", "city": "101280600"})
        client._request_via_browser.assert_called_once_with(
            "search", None, json_data={"query": "Python", "city": "101280600"},
        )

    def test_no_browser_fallback_for_unsupported_endpoint(self, client, mocker):
        mocker.patch.object(client, "_request_via_browser", return_value=None)
        result = {"code": 1, "message": "风控拦截"}
        out = client._handle_risk_block(result, "chat_list", None)
        assert out["_risk_blocked"] is True
        client._request_via_browser.assert_not_called()

    def test_returns_original_when_browser_fallback_fails(self, client, mocker):
        mocker.patch.object(client, "_request_via_browser", return_value=None)
        result = {"code": 1, "message": "操作异常"}
        out = client._handle_risk_block(result, "search", None)
        assert out is result
        assert out["_risk_blocked"] is True


class TestTryHttpRequest:
    def test_delegates_get(self, client, mocker):
        mock_client = mocker.MagicMock(spec=httpx.Client)
        mock_response = mocker.MagicMock()
        mock_client.get.return_value = mock_response
        resp = client._try_http_request(
            mock_client, "GET", "https://example.com",
            {"q": "test"}, None, {"X-Test": "1"}, {"sid": "abc"},
        )
        assert resp is mock_response
        mock_client.get.assert_called_once_with(
            "https://example.com",
            params={"q": "test"},
            headers={"X-Test": "1"}, cookies={"sid": "abc"},
        )

    def test_delegates_post(self, client, mocker):
        mock_client = mocker.MagicMock(spec=httpx.Client)
        mock_response = mocker.MagicMock()
        mock_client.post.return_value = mock_response
        resp = client._try_http_request(
            mock_client, "POST", "https://example.com",
            None, {"key": "val"}, {"X-Test": "1"}, {"sid": "abc"},
        )
        assert resp is mock_response
        mock_client.post.assert_called_once_with(
            "https://example.com",
            params=None, json={"key": "val"},
            headers={"X-Test": "1"}, cookies={"sid": "abc"},
        )

    def test_propagates_transport_error(self, client, mocker):
        mock_client = mocker.MagicMock(spec=httpx.Client)
        mock_client.get.side_effect = httpx.TransportError("connection failed")
        with pytest.raises(httpx.TransportError, match="connection failed"):
            client._try_http_request(
                mock_client, "GET", "https://example.com",
                None, None, {}, {},
            )


class TestRequestViaBrowser:
    def test_returns_none_for_unsupported_endpoint(self, client):
        result = client._request_via_browser("chat_list", None)
        assert result is None

    def test_delegates_get_to_browser_get(self, client, mocker):
        mocker.patch.object(client, "_get_cookies", return_value={"sid": "abc"})
        mocker.patch.object(client, "_browser_get", return_value={"code": 0})
        ep_mock = mocker.MagicMock()
        ep_mock.method = "GET"
        ep_mock.path = "/api/test"
        mocker.patch.object(client._endpoints, "get", return_value=ep_mock)
        result = client._request_via_browser("recommend", {"page": 1})
        assert result == {"code": 0}
        client._browser_get.assert_called_once_with("/api/test", {"page": 1}, {}, {"sid": "abc"})

    def test_delegates_post_to_browser_post(self, client, mocker):
        mocker.patch.object(client, "_get_cookies", return_value={"sid": "abc"})
        mocker.patch.object(client, "_browser_post", return_value={"code": 0})
        ep_mock = mocker.MagicMock()
        ep_mock.method = "POST"
        ep_mock.path = "/api/search"
        mocker.patch.object(client._endpoints, "get", return_value=ep_mock)
        result = client._request_via_browser("search", {"query": "python", "__zp_stoken__": "tok123"})
        assert result == {"code": 0}
        call_args = client._browser_post.call_args
        assert call_args[0][0] == "/api/search?__zp_stoken__=tok123"
        assert call_args[0][1] == {"query": "python"}

    def test_post_endpoint_uses_json_data_when_provided(self, client, mocker):
        mocker.patch.object(client, "_get_cookies", return_value={"sid": "abc"})
        mocker.patch.object(client, "_browser_post", return_value={"code": 0})
        ep_mock = mocker.MagicMock()
        ep_mock.method = "POST"
        ep_mock.path = "/api/search"
        mocker.patch.object(client._endpoints, "get", return_value=ep_mock)
        result = client._request_via_browser(
            "search", {"__zp_stoken__": "tok123"}, json_data={"query": "Python", "city": "101280600"},
        )
        assert result == {"code": 0}
        call_args = client._browser_post.call_args
        assert call_args[0][0] == "/api/search?__zp_stoken__=tok123"
        assert call_args[0][1] == {"query": "Python", "city": "101280600"}

    def test_returns_none_when_no_cookies(self, client, mocker):
        mocker.patch.object(client, "_get_cookies", return_value={})
        result = client._request_via_browser("search", None)
        assert result is None

    def test_returns_none_when_endpoint_not_found(self, client, mocker):
        mocker.patch.object(client, "_get_cookies", return_value={"sid": "abc"})
        mocker.patch.object(client._endpoints, "get", return_value=None)
        result = client._request_via_browser("search", None)
        assert result is None
