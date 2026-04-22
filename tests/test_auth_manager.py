from unittest.mock import MagicMock, patch

import pytest

from boss_career_ops.boss.auth.manager import AuthManager, _check_login_cookies
from boss_career_ops.config.singleton import SingletonMeta


@pytest.fixture(autouse=True)
def reset_singletons():
    yield
    SingletonMeta.reset(AuthManager)


@pytest.fixture
def auth():
    SingletonMeta.reset(AuthManager)
    return AuthManager()


def test_login_bridge_cookie_daemon_not_running(auth):
    with patch("boss_career_ops.bridge.client.BridgeClient") as MockBridge, \
         patch("boss_career_ops.bridge.daemon.start_daemon"), \
         patch("boss_career_ops.boss.auth.manager.time.sleep"):
        mock_bridge = MockBridge.return_value
        mock_bridge.is_available.return_value = False
        result = auth._login_bridge_cookie()
    assert result == {"ok": False, "method": "bridge_cookie"}


def _mock_httpx_client(mock_client_cls, status_code=200, json_data=None):
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    if json_data is not None:
        mock_resp.json.return_value = json_data
    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp
    mock_client.__enter__ = MagicMock(return_value=mock_client)
    mock_client.__exit__ = MagicMock(return_value=False)
    mock_client_cls.return_value = mock_client
    return mock_client


def test_login_bridge_cookie_extension_not_connected(auth):
    with patch("boss_career_ops.bridge.client.BridgeClient") as MockBridge, \
         patch("boss_career_ops.boss.auth.manager.httpx.Client") as mock_client_cls, \
         patch("boss_career_ops.boss.auth.manager.time.sleep"):
        mock_bridge = MockBridge.return_value
        mock_bridge.is_available.return_value = True
        mock_bridge._bridge_url = "http://127.0.0.1:18765"

        _mock_httpx_client(mock_client_cls, json_data={"ok": True, "extensions_connected": 0})

        result = auth._login_bridge_cookie()
    assert result == {"ok": False, "method": "bridge_cookie"}


def test_login_bridge_cookie_invalid_cookies(auth):
    with patch("boss_career_ops.bridge.client.BridgeClient") as MockBridge, \
         patch("boss_career_ops.boss.auth.manager.httpx.Client") as mock_client_cls, \
         patch("boss_career_ops.boss.auth.manager.time.sleep"):
        mock_bridge = MockBridge.return_value
        mock_bridge.is_available.return_value = True
        mock_bridge._bridge_url = "http://127.0.0.1:18765"
        mock_bridge.get_cookies.return_value = {"bst": "some_value"}

        _mock_httpx_client(mock_client_cls, json_data={"ok": True, "extensions_connected": 1})

        result = auth._login_bridge_cookie()
    assert result == {"ok": False, "method": "bridge_cookie"}


def test_login_bridge_cookie_success(auth):
    with patch("boss_career_ops.bridge.client.BridgeClient") as MockBridge, \
         patch("boss_career_ops.boss.auth.manager.httpx.Client") as mock_client_cls, \
         patch("boss_career_ops.boss.auth.manager.time.sleep"):
        mock_bridge = MockBridge.return_value
        mock_bridge.is_available.return_value = True
        mock_bridge._bridge_url = "http://127.0.0.1:18765"
        mock_bridge.get_cookies.return_value = {
            "wt2": "wt2_value",
            "stoken": "stoken_value",
            "bst": "bst_value",
        }

        _mock_httpx_client(mock_client_cls, json_data={"ok": True, "extensions_connected": 1})

        with patch.object(auth._token_store, "save") as mock_save:
            result = auth._login_bridge_cookie()

    assert result["ok"] is True
    assert result["method"] == "bridge_cookie"
    mock_save.assert_called_once_with({
        "wt2": "wt2_value",
        "stoken": "stoken_value",
        "bst": "bst_value",
    })


def test_login_degradation_chain_order(auth):
    call_order = []

    def mock_bridge_cookie():
        call_order.append("bridge_cookie")
        return {"ok": False, "method": "bridge_cookie"}

    def mock_cdp():
        call_order.append("cdp")
        return {"ok": False, "method": "cdp"}

    def mock_patchright():
        call_order.append("patchright")
        return {"ok": True, "method": "patchright", "message": "成功"}

    mock_bridge_cookie.__name__ = "_login_bridge_cookie"
    mock_cdp.__name__ = "_login_cdp"
    mock_patchright.__name__ = "_login_patchright"

    with patch.object(auth, "_login_bridge_cookie", mock_bridge_cookie), \
         patch.object(auth, "_login_cdp", mock_cdp), \
         patch.object(auth, "_login_patchright", mock_patchright):
        result = auth.login()

    assert call_order == ["bridge_cookie", "cdp", "patchright"]
    assert result["ok"] is True
    assert result["method"] == "patchright"


def test_login_bridge_cookie_first_success(auth):
    def mock_bridge_cookie():
        return {"ok": True, "method": "bridge_cookie", "message": "成功"}

    mock_bridge_cookie.__name__ = "_login_bridge_cookie"

    mock_cdp = MagicMock()
    mock_cdp.__name__ = "_login_cdp"
    mock_patchright = MagicMock()
    mock_patchright.__name__ = "_login_patchright"

    with patch.object(auth, "_login_bridge_cookie", mock_bridge_cookie), \
         patch.object(auth, "_login_cdp", mock_cdp), \
         patch.object(auth, "_login_patchright", mock_patchright):
        result = auth.login()

    assert result["ok"] is True
    assert result["method"] == "bridge_cookie"
    mock_cdp.assert_not_called()
    mock_patchright.assert_not_called()
