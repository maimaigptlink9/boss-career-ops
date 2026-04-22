import asyncio
import json
from unittest.mock import patch, MagicMock, AsyncMock

import pytest
import pytest_asyncio
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from aiohttp import web

from boss_career_ops.bridge.daemon import BridgeDaemon
from boss_career_ops.bridge.client import BridgeClient
from boss_career_ops.bridge.protocol import CommandType


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


@pytest.fixture(autouse=True)
def reset_singletons():
    from boss_career_ops.boss.auth.manager import AuthManager
    from boss_career_ops.config.singleton import SingletonMeta
    yield
    SingletonMeta.reset(AuthManager)


# ============================================================
# 1. _login_bridge_cookie() print 输出测试
# ============================================================
class TestLoginBridgeCookiePrint:

    def _make_auth(self):
        from boss_career_ops.boss.auth.manager import AuthManager
        from boss_career_ops.config.singleton import SingletonMeta
        SingletonMeta.reset(AuthManager)
        return AuthManager()

    @staticmethod
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

    def test_daemon_not_running_timeout(self, capsys):
        auth = self._make_auth()
        with patch("boss_career_ops.bridge.client.BridgeClient") as MockBridge, \
             patch("boss_career_ops.bridge.daemon.start_daemon") as mock_start, \
             patch("boss_career_ops.boss.auth.manager.time.sleep"):
            mock_bridge = MockBridge.return_value
            mock_bridge.is_available.return_value = False

            mock_start.side_effect = lambda: None
            result = auth._login_bridge_cookie()

        captured = capsys.readouterr()
        assert "[Bridge] 正在连接 Bridge Daemon..." in captured.out
        assert "[Bridge] Daemon 未运行，正在启动..." in captured.out
        assert "[Bridge] Daemon 启动超时，跳过" in captured.out

    def test_daemon_startup_exception(self, capsys):
        auth = self._make_auth()
        with patch("boss_career_ops.bridge.client.BridgeClient") as MockBridge, \
             patch("boss_career_ops.bridge.daemon.start_daemon") as mock_start, \
             patch("boss_career_ops.boss.auth.manager.time.sleep"):
            mock_bridge = MockBridge.return_value
            mock_bridge.is_available.return_value = False
            mock_start.side_effect = RuntimeError("fail")

            result = auth._login_bridge_cookie()

        captured = capsys.readouterr()
        assert "[Bridge] Daemon 未运行，正在启动..." in captured.out
        assert "[Bridge] Daemon 启动超时，跳过" in captured.out

    def test_extension_wait_timeout(self, capsys):
        auth = self._make_auth()
        with patch("boss_career_ops.bridge.client.BridgeClient") as MockBridge, \
             patch("boss_career_ops.boss.auth.manager.httpx.Client") as mock_client_cls, \
             patch("boss_career_ops.boss.auth.manager.time.sleep"):
            mock_bridge = MockBridge.return_value
            mock_bridge.is_available.return_value = True
            mock_bridge._bridge_url = "http://127.0.0.1:18765"

            self._mock_httpx_client(mock_client_cls, json_data={"ok": True, "extensions_connected": 0})

            result = auth._login_bridge_cookie()

        captured = capsys.readouterr()
        assert "[Bridge] 正在连接 Bridge Daemon..." in captured.out
        assert "[Bridge] Daemon 已就绪" in captured.out
        assert "[Bridge] 等待 Chrome 扩展连接..." in captured.out
        assert "[Bridge] 等待 Chrome 扩展连接超时（30秒）" in captured.out
        assert "[Bridge] 请检查以下事项：" in captured.out

    def test_cookie_empty(self, capsys):
        auth = self._make_auth()
        with patch("boss_career_ops.bridge.client.BridgeClient") as MockBridge, \
             patch("boss_career_ops.boss.auth.manager.httpx.Client") as mock_client_cls, \
             patch("boss_career_ops.boss.auth.manager.time.sleep"):
            mock_bridge = MockBridge.return_value
            mock_bridge.is_available.return_value = True
            mock_bridge._bridge_url = "http://127.0.0.1:18765"
            mock_bridge.get_cookies.return_value = {}

            self._mock_httpx_client(mock_client_cls, json_data={"ok": True, "extensions_connected": 1})

            result = auth._login_bridge_cookie()

        captured = capsys.readouterr()
        assert "[Bridge] 正在获取 Cookie..." in captured.out
        assert "[Bridge] Bridge 返回空 Cookie" in captured.out

    def test_cookie_incomplete(self, capsys):
        auth = self._make_auth()
        with patch("boss_career_ops.bridge.client.BridgeClient") as MockBridge, \
             patch("boss_career_ops.boss.auth.manager.httpx.Client") as mock_client_cls, \
             patch("boss_career_ops.boss.auth.manager.time.sleep"):
            mock_bridge = MockBridge.return_value
            mock_bridge.is_available.return_value = True
            mock_bridge._bridge_url = "http://127.0.0.1:18765"
            mock_bridge.get_cookies.return_value = {"bst": "some_value"}

            self._mock_httpx_client(mock_client_cls, json_data={"ok": True, "extensions_connected": 1})

            result = auth._login_bridge_cookie()

        captured = capsys.readouterr()
        assert "[Bridge] 正在获取 Cookie..." in captured.out
        assert "[Bridge] Cookie 不完整，缺少: wt2, stoken" in captured.out

    def test_cookie_success(self, capsys):
        auth = self._make_auth()
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

            self._mock_httpx_client(mock_client_cls, json_data={"ok": True, "extensions_connected": 1})

            with patch.object(auth._token_store, "save"):
                result = auth._login_bridge_cookie()

        captured = capsys.readouterr()
        assert "[Bridge] 正在获取 Cookie..." in captured.out
        assert "[Bridge] Cookie 有效 (wt2: ✓, stoken: ✓)" in captured.out
        assert result["ok"] is True

    def test_cookie_success_with___zp_stoken__(self, capsys):
        auth = self._make_auth()
        with patch("boss_career_ops.bridge.client.BridgeClient") as MockBridge, \
             patch("boss_career_ops.boss.auth.manager.httpx.Client") as mock_client_cls, \
             patch("boss_career_ops.boss.auth.manager.time.sleep"):
            mock_bridge = MockBridge.return_value
            mock_bridge.is_available.return_value = True
            mock_bridge._bridge_url = "http://127.0.0.1:18765"
            mock_bridge.get_cookies.return_value = {
                "wt2": "wt2_value",
                "__zp_stoken__": "stoken_value",
            }

            self._mock_httpx_client(mock_client_cls, json_data={"ok": True, "extensions_connected": 1})

            with patch.object(auth._token_store, "save"):
                result = auth._login_bridge_cookie()

        captured = capsys.readouterr()
        assert "[Bridge] Cookie 有效 (wt2: ✓, stoken: ✓)" in captured.out
        assert result["ok"] is True

    def test_cookie_exception(self, capsys):
        auth = self._make_auth()
        with patch("boss_career_ops.bridge.client.BridgeClient") as MockBridge, \
             patch("boss_career_ops.boss.auth.manager.httpx.Client") as mock_client_cls, \
             patch("boss_career_ops.boss.auth.manager.time.sleep"):
            mock_bridge = MockBridge.return_value
            mock_bridge.is_available.return_value = True
            mock_bridge._bridge_url = "http://127.0.0.1:18765"
            mock_bridge.get_cookies.side_effect = Exception("network error")

            self._mock_httpx_client(mock_client_cls, json_data={"ok": True, "extensions_connected": 1})

            result = auth._login_bridge_cookie()

        captured = capsys.readouterr()
        assert "[Bridge] Cookie 获取失败" in captured.out


# ============================================================
# 2. daemon /status 端点增强字段测试
# ============================================================
class TestDaemonStatusEndpoint:

    def test_status_basic_fields(self):
        daemon = BridgeDaemon()
        status = asyncio.run(daemon._handle_status(MagicMock()))
        body = json.loads(status.body)
        assert body["ok"] is True
        assert "extensions_connected" in body
        assert "version" in body
        assert "uptime_seconds" in body
        assert body["uptime_seconds"] >= 0

    def test_status_no_cookie_result_yet(self):
        daemon = BridgeDaemon()
        status = asyncio.run(daemon._handle_status(MagicMock()))
        body = json.loads(status.body)
        assert "last_cookie_fetch" not in body

    def test_update_cookie_result_valid(self):
        daemon = BridgeDaemon()
        daemon._update_cookie_result({
            "wt2": "v1",
            "stoken": "v2",
            "bst": "v3",
        })
        assert daemon._last_cookie_result is not None
        assert daemon._last_cookie_result["valid"] is True
        assert daemon._last_cookie_result["cookie_count"] == 3
        assert daemon._last_cookie_result["missing"] == []
        assert "time" in daemon._last_cookie_result

    def test_update_cookie_result_missing_wt2(self):
        daemon = BridgeDaemon()
        daemon._update_cookie_result({
            "bst": "v3",
            "stoken": "v2",
        })
        assert daemon._last_cookie_result["valid"] is False
        assert "wt2" in daemon._last_cookie_result["missing"]
        assert "stoken" not in daemon._last_cookie_result["missing"]

    def test_update_cookie_result_missing_stoken(self):
        daemon = BridgeDaemon()
        daemon._update_cookie_result({
            "wt2": "v1",
            "bst": "v3",
        })
        assert daemon._last_cookie_result["valid"] is False
        assert "stoken" in daemon._last_cookie_result["missing"]

    def test_update_cookie_result_missing_both(self):
        daemon = BridgeDaemon()
        daemon._update_cookie_result({"bst": "v3"})
        assert "wt2" in daemon._last_cookie_result["missing"]
        assert "stoken" in daemon._last_cookie_result["missing"]

    def test_update_cookie_result_empty_dict(self):
        daemon = BridgeDaemon()
        daemon._update_cookie_result({})
        assert daemon._last_cookie_result["valid"] is False
        assert daemon._last_cookie_result["cookie_count"] == 0

    def test_update_cookie_result_list_format(self):
        daemon = BridgeDaemon()
        daemon._update_cookie_result([
            {"name": "wt2", "value": "v1"},
            {"name": "stoken", "value": "v2"},
        ])
        assert daemon._last_cookie_result["valid"] is True
        assert daemon._last_cookie_result["cookie_count"] == 2

    def test_status_includes_cookie_result_after_update(self):
        daemon = BridgeDaemon()
        daemon._update_cookie_result({"wt2": "v1", "stoken": "v2"})
        status = asyncio.run(daemon._handle_status(MagicMock()))
        body = json.loads(status.body)
        assert "last_cookie_fetch" in body
        assert body["last_cookie_fetch"]["valid"] is True

    def test_process_command_get_cookies_updates_result(self):
        daemon = BridgeDaemon()
        mock_result = {"ok": True, "data": {"wt2": "v1", "stoken": "v2"}, "id": "t1"}

        async def mock_forward(data):
            return mock_result

        with patch.object(daemon, "_forward_to_extensions", mock_forward):
            result = asyncio.run(
                daemon._process_command({
                    "type": CommandType.GET_COOKIES.value,
                    "id": "t1",
                })
            )

        assert result["ok"] is True
        assert daemon._last_cookie_result is not None
        assert daemon._last_cookie_result["valid"] is True

    def test_process_command_get_cookies_no_update_on_failure(self):
        daemon = BridgeDaemon()
        mock_ws = MagicMock()
        daemon._extensions = [mock_ws]

        async def _run():
            cmd_id = "test_cmd"
            loop = asyncio.get_running_loop()
            future = loop.create_future()
            daemon._pending_results[cmd_id] = future

            task = asyncio.create_task(
                daemon._process_command({
                    "type": CommandType.GET_COOKIES.value,
                    "id": cmd_id,
                })
            )
            await asyncio.sleep(0.01)
            future.set_result({
                "ok": False,
                "error": "timeout",
                "id": cmd_id,
            })
            result = await task
            return result

        result = asyncio.run(_run())
        assert result["ok"] is False
        assert daemon._last_cookie_result is None


# ============================================================
# 3. bco bridge status 命令测试
# ============================================================
class TestBridgeStatusCommand:

    def test_daemon_not_running(self, capsys):
        with patch("boss_career_ops.bridge.client.BridgeClient") as MockBridge:
            mock_bridge = MockBridge.return_value
            mock_bridge.is_available.return_value = False

            from boss_career_ops.commands.bridge import run_bridge_status
            run_bridge_status()

        captured = capsys.readouterr()
        assert "Bridge Daemon: 未运行" in captured.out
        assert "提示: 运行 bco login 会自动启动 Bridge Daemon" in captured.out

    def test_daemon_running_no_cookie_record(self, capsys):
        with patch("boss_career_ops.bridge.client.BridgeClient") as MockBridge, \
             patch("boss_career_ops.commands.bridge.httpx.Client") as mock_client_cls:
            mock_bridge = MockBridge.return_value
            mock_bridge.is_available.return_value = True
            mock_bridge._bridge_url = "http://127.0.0.1:18765"

            _mock_httpx_client(mock_client_cls, json_data={
                "ok": True,
                "extensions_connected": 1,
                "uptime_seconds": 3661,
            })

            from boss_career_ops.commands.bridge import run_bridge_status
            run_bridge_status()

        captured = capsys.readouterr()
        assert "Bridge Daemon: 运行中" in captured.out
        assert "Chrome 扩展: 已连接 (1 个)" in captured.out
        assert "上次 Cookie 获取: 无记录" in captured.out

    def test_daemon_running_with_cookie_record(self, capsys):
        with patch("boss_career_ops.bridge.client.BridgeClient") as MockBridge, \
             patch("boss_career_ops.commands.bridge.httpx.Client") as mock_client_cls:
            mock_bridge = MockBridge.return_value
            mock_bridge.is_available.return_value = True
            mock_bridge._bridge_url = "http://127.0.0.1:18765"

            _mock_httpx_client(mock_client_cls, json_data={
                "ok": True,
                "extensions_connected": 1,
                "uptime_seconds": 5000,
                "last_cookie_fetch": {
                    "time": "2026-04-23T14:30:00+00:00",
                    "valid": True,
                    "cookie_count": 15,
                    "missing": [],
                },
            })

            from boss_career_ops.commands.bridge import run_bridge_status
            run_bridge_status()

        captured = capsys.readouterr()
        assert "Bridge Daemon: 运行中" in captured.out
        assert "上次 Cookie 获取: ✓ 有效 (wt2: ✓, stoken: ✓)" in captured.out

    def test_daemon_running_incomplete_cookie(self, capsys):
        with patch("boss_career_ops.bridge.client.BridgeClient") as MockBridge, \
             patch("boss_career_ops.commands.bridge.httpx.Client") as mock_client_cls:
            mock_bridge = MockBridge.return_value
            mock_bridge.is_available.return_value = True
            mock_bridge._bridge_url = "http://127.0.0.1:18765"

            _mock_httpx_client(mock_client_cls, json_data={
                "ok": True,
                "extensions_connected": 1,
                "uptime_seconds": 5000,
                "last_cookie_fetch": {
                    "time": "2026-04-23T14:30:00+00:00",
                    "valid": False,
                    "cookie_count": 5,
                    "missing": ["wt2"],
                },
            })

            from boss_career_ops.commands.bridge import run_bridge_status
            run_bridge_status()

        captured = capsys.readouterr()
        assert "✗ 不完整" in captured.out
        assert "wt2: ✗" in captured.out

    def test_daemon_running_no_extensions(self, capsys):
        with patch("boss_career_ops.bridge.client.BridgeClient") as MockBridge, \
             patch("boss_career_ops.commands.bridge.httpx.Client") as mock_client_cls:
            mock_bridge = MockBridge.return_value
            mock_bridge.is_available.return_value = True
            mock_bridge._bridge_url = "http://127.0.0.1:18765"

            _mock_httpx_client(mock_client_cls, json_data={
                "ok": True,
                "extensions_connected": 0,
                "uptime_seconds": 100,
            })

            from boss_career_ops.commands.bridge import run_bridge_status
            run_bridge_status()

        captured = capsys.readouterr()
        assert "Chrome 扩展: 未连接 (0 个)" in captured.out


# ============================================================
# 4. bco bridge test 命令测试
# ============================================================
class TestBridgeTestCommand:

    def test_daemon_unavailable(self, capsys):
        with patch("boss_career_ops.bridge.client.BridgeClient") as MockBridge:
            mock_bridge = MockBridge.return_value
            mock_bridge.is_available.return_value = False

            from boss_career_ops.commands.bridge import run_bridge_test
            run_bridge_test()

        captured = capsys.readouterr()
        assert "[1/3] Daemon 连通性..." in captured.out
        assert "✗" in captured.out
        assert "[2/3]" not in captured.out
        assert "[3/3]" not in captured.out

    def test_step2_no_extensions(self, capsys):
        with patch("boss_career_ops.bridge.client.BridgeClient") as MockBridge, \
             patch("boss_career_ops.commands.bridge.httpx.Client") as mock_client_cls:
            mock_bridge = MockBridge.return_value
            mock_bridge.is_available.return_value = True
            mock_bridge._bridge_url = "http://127.0.0.1:18765"

            _mock_httpx_client(mock_client_cls, json_data={
                "ok": True,
                "extensions_connected": 0,
            })

            from boss_career_ops.commands.bridge import run_bridge_test
            run_bridge_test()

        captured = capsys.readouterr()
        assert "[1/3] Daemon 连通性... ✓" in captured.out
        assert "[2/3] Chrome 扩展连接... ✗" in captured.out
        assert "[3/3]" not in captured.out

    def test_step3_valid_cookies(self, capsys):
        with patch("boss_career_ops.bridge.client.BridgeClient") as MockBridge, \
             patch("boss_career_ops.commands.bridge.httpx.Client") as mock_client_cls:
            mock_bridge = MockBridge.return_value
            mock_bridge.is_available.return_value = True
            mock_bridge._bridge_url = "http://127.0.0.1:18765"
            mock_bridge.get_cookies.return_value = {
                "wt2": "v1",
                "stoken": "v2",
                "bst": "v3",
            }

            _mock_httpx_client(mock_client_cls, json_data={
                "ok": True,
                "extensions_connected": 1,
            })

            from boss_career_ops.commands.bridge import run_bridge_test
            run_bridge_test()

        captured = capsys.readouterr()
        assert "[1/3] Daemon 连通性... ✓" in captured.out
        assert "[2/3] Chrome 扩展连接... ✓ (1 个)" in captured.out
        assert "[3/3] Cookie 获取... ✓" in captured.out
        assert "登录态有效" in captured.out

    def test_step3_incomplete_cookies(self, capsys):
        with patch("boss_career_ops.bridge.client.BridgeClient") as MockBridge, \
             patch("boss_career_ops.commands.bridge.httpx.Client") as mock_client_cls:
            mock_bridge = MockBridge.return_value
            mock_bridge.is_available.return_value = True
            mock_bridge._bridge_url = "http://127.0.0.1:18765"
            mock_bridge.get_cookies.return_value = {"bst": "v3"}

            _mock_httpx_client(mock_client_cls, json_data={
                "ok": True,
                "extensions_connected": 1,
            })

            from boss_career_ops.commands.bridge import run_bridge_test
            run_bridge_test()

        captured = capsys.readouterr()
        assert "[3/3] Cookie 获取... ✗" in captured.out
        assert "缺少: wt2, stoken" in captured.out

    def test_step3_empty_cookies(self, capsys):
        with patch("boss_career_ops.bridge.client.BridgeClient") as MockBridge, \
             patch("boss_career_ops.commands.bridge.httpx.Client") as mock_client_cls:
            mock_bridge = MockBridge.return_value
            mock_bridge.is_available.return_value = True
            mock_bridge._bridge_url = "http://127.0.0.1:18765"
            mock_bridge.get_cookies.return_value = {}

            _mock_httpx_client(mock_client_cls, json_data={
                "ok": True,
                "extensions_connected": 1,
            })

            from boss_career_ops.commands.bridge import run_bridge_test
            run_bridge_test()

        captured = capsys.readouterr()
        assert "[3/3] Cookie 获取... ✗" in captured.out
        assert "未获取到 Cookie" in captured.out

    def test_step3_exception(self, capsys):
        with patch("boss_career_ops.bridge.client.BridgeClient") as MockBridge, \
             patch("boss_career_ops.commands.bridge.httpx.Client") as mock_client_cls:
            mock_bridge = MockBridge.return_value
            mock_bridge.is_available.return_value = True
            mock_bridge._bridge_url = "http://127.0.0.1:18765"
            mock_bridge.get_cookies.side_effect = Exception("network error")

            _mock_httpx_client(mock_client_cls, json_data={
                "ok": True,
                "extensions_connected": 1,
            })

            from boss_career_ops.commands.bridge import run_bridge_test
            run_bridge_test()

        captured = capsys.readouterr()
        assert "[3/3] Cookie 获取... ✗" in captured.out


# ============================================================
# 5. CLI bridge 命令注册测试
# ============================================================
class TestBridgeCLIGroup:
    def test_bridge_help(self):
        from click.testing import CliRunner
        from boss_career_ops.cli.main import cli

        runner = CliRunner()
        result = runner.invoke(cli, ["bridge", "--help"])
        assert result.exit_code == 0
        assert "status" in result.output
        assert "test" in result.output

    def test_bridge_status_registered(self):
        from click.testing import CliRunner
        from boss_career_ops.cli.main import cli

        runner = CliRunner()
        with patch("boss_career_ops.bridge.client.BridgeClient") as MockBridge:
            mock_bridge = MockBridge.return_value
            mock_bridge.is_available.return_value = False
            result = runner.invoke(cli, ["bridge", "status"])
        assert result.exit_code == 0
        assert "未运行" in result.output

    def test_bridge_test_registered(self):
        from click.testing import CliRunner
        from boss_career_ops.cli.main import cli

        runner = CliRunner()
        with patch("boss_career_ops.bridge.client.BridgeClient") as MockBridge:
            mock_bridge = MockBridge.return_value
            mock_bridge.is_available.return_value = False
            result = runner.invoke(cli, ["bridge", "test"])
        assert result.exit_code == 0
