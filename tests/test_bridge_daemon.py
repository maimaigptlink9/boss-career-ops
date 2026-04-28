import asyncio
import os
import time
from unittest.mock import patch, MagicMock

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from boss_career_ops.bridge.daemon import BridgeDaemon, _command_handlers
from boss_career_ops.bridge.protocol import CommandType


class TestBridgeDaemon:
    def test_process_command_ping(self):
        daemon = BridgeDaemon()
        result = asyncio.run(daemon._process_command({"type": "ping"}))
        assert result["ok"] is True
        assert result["data"] == "pong"

    def test_process_command_get_cookies_no_extension(self):
        daemon = BridgeDaemon()
        result = asyncio.run(daemon._process_command({"type": "get_cookies"}))
        assert result["ok"] is False
        assert "扩展" in result["error"] or "无" in result["error"]

    def test_process_command_navigate_no_extension(self):
        daemon = BridgeDaemon()
        result = asyncio.run(daemon._process_command({"type": "navigate", "params": {"url": "https://zhipin.com"}}))
        assert result["ok"] is False
        assert "扩展" in result["error"] or "无" in result["error"]

    def test_process_command_click_no_extension(self):
        daemon = BridgeDaemon()
        result = asyncio.run(daemon._process_command({"type": "click", "params": {"selector": "#btn"}}))
        assert result["ok"] is False

    def test_process_command_type_text_no_extension(self):
        daemon = BridgeDaemon()
        result = asyncio.run(daemon._process_command({"type": "type_text", "params": {"selector": "#input", "text": "hello"}}))
        assert result["ok"] is False

    def test_process_command_screenshot_no_extension(self):
        daemon = BridgeDaemon()
        result = asyncio.run(daemon._process_command({"type": "screenshot"}))
        assert result["ok"] is False

    def test_process_command_execute_js_no_extension(self):
        daemon = BridgeDaemon()
        result = asyncio.run(daemon._process_command({"type": "execute_js", "params": {"script": "return 1"}}))
        assert result["ok"] is False

    def test_process_command_unknown(self):
        daemon = BridgeDaemon()
        result = asyncio.run(daemon._process_command({"type": "unknown_cmd"}))
        assert result["ok"] is False
        assert "未知命令" in result["error"]

    def test_daemon_init(self):
        daemon = BridgeDaemon(host="0.0.0.0", port=9999)
        assert daemon._host == "0.0.0.0"
        assert daemon._port == 9999


class TestBridgeDaemonTokenAuth:
    def test_token_file_created_on_init(self, tmp_path):
        with patch("boss_career_ops.bridge.daemon.TOKEN_FILE", tmp_path / "bridge_token"):
            daemon = BridgeDaemon()
            token_file = tmp_path / "bridge_token"
            assert token_file.exists()
            token = token_file.read_text(encoding="utf-8")
            assert token == daemon._token
            assert len(token) == 64

    def test_validate_token_rejects_empty(self):
        daemon = BridgeDaemon()
        mock_request = MagicMock()
        mock_request.query.get.return_value = ""
        assert daemon._validate_token(mock_request) is False

    def test_validate_token_rejects_wrong_token(self):
        daemon = BridgeDaemon()
        mock_request = MagicMock()
        mock_request.query.get.return_value = "wrong-token"
        assert daemon._validate_token(mock_request) is False

    def test_validate_token_accepts_valid_token(self):
        daemon = BridgeDaemon()
        mock_request = MagicMock()
        mock_request.query.get.return_value = daemon._token
        assert daemon._validate_token(mock_request) is True

    def test_ws_rejects_without_token(self):
        async def _test():
            daemon = BridgeDaemon()
            async with TestClient(TestServer(daemon._app)) as cli:
                ws = await cli.ws_connect("/ws")
                msg = await ws.receive()
                assert msg.type == web.WSMsgType.TEXT
                import json
                data = json.loads(msg.data)
                assert data["ok"] is False
                assert "token" in data["error"]
                msg2 = await ws.receive()
                assert msg2.type == web.WSMsgType.CLOSE
        asyncio.run(_test())

    def test_ws_rejects_wrong_token(self):
        async def _test():
            daemon = BridgeDaemon()
            async with TestClient(TestServer(daemon._app)) as cli:
                ws = await cli.ws_connect("/ws?token=wrong-token")
                msg = await ws.receive()
                assert msg.type == web.WSMsgType.TEXT
                import json
                data = json.loads(msg.data)
                assert data["ok"] is False
                assert "token" in data["error"]
                msg2 = await ws.receive()
                assert msg2.type == web.WSMsgType.CLOSE
        asyncio.run(_test())

    def test_ws_accepts_valid_token(self):
        async def _test():
            daemon = BridgeDaemon()
            async with TestClient(TestServer(daemon._app)) as cli:
                ws = await cli.ws_connect(f"/ws?token={daemon._token}")
                await ws.send_str('{"type":"ping","id":"test-1"}')
                msg = await ws.receive()
                assert msg.type == web.WSMsgType.TEXT
                import json
                data = json.loads(msg.data)
                assert data["ok"] is True
                assert data["data"] == "pong"
                await ws.close()
        asyncio.run(_test())


class TestCommandRegistry:
    def test_registry_has_all_command_types(self):
        expected = {ct.value for ct in CommandType}
        assert set(BridgeDaemon._command_handlers.keys()) == expected

    def test_registry_dispatches_ping(self):
        daemon = BridgeDaemon()
        result = asyncio.run(daemon._process_command({"type": "ping", "id": "r1"}))
        assert result["ok"] is True
        assert result["data"] == "pong"
        assert result["id"] == "r1"

    def test_registry_dispatches_forward_commands(self):
        daemon = BridgeDaemon()
        for cmd_type in ["navigate", "click", "type_text", "screenshot", "execute_js"]:
            result = asyncio.run(daemon._process_command({"type": cmd_type, "id": "r2"}))
            assert result["ok"] is False
            assert "扩展" in result["error"] or "无" in result["error"]

    def test_registry_unknown_command_returns_error(self):
        daemon = BridgeDaemon()
        result = asyncio.run(daemon._process_command({"type": "nonexistent", "id": "r3"}))
        assert result["ok"] is False
        assert "未知命令" in result["error"]
        assert result["id"] == "r3"

    def test_register_new_handler_without_modifying_process_command(self):
        async def _handle_custom(self, data):
            return {"ok": True, "data": "custom_response", "id": data.get("id", "")}

        original_handlers = dict(BridgeDaemon._command_handlers)
        try:
            BridgeDaemon._command_handlers["custom_cmd"] = _handle_custom
            daemon = BridgeDaemon()
            result = asyncio.run(daemon._process_command({"type": "custom_cmd", "id": "r4"}))
            assert result["ok"] is True
            assert result["data"] == "custom_response"
            assert result["id"] == "r4"
        finally:
            BridgeDaemon._command_handlers = original_handlers
            _command_handlers.clear()
            _command_handlers.update(original_handlers)


class TestPendingResultsTimeout:
    def test_cleanup_removes_expired_entries(self):
        daemon = BridgeDaemon()
        daemon._command_timeout = 5
        loop = asyncio.new_event_loop()
        future = loop.create_future()
        old_timestamp = time.time() - 10
        daemon._pending_results["expired-id"] = (future, old_timestamp)
        daemon._cleanup_expired_pending()
        assert "expired-id" not in daemon._pending_results
        assert future.done()
        assert future.result()["ok"] is False
        assert "命令超时" in future.result()["error"]
        loop.close()

    def test_cleanup_keeps_fresh_entries(self):
        daemon = BridgeDaemon()
        daemon._command_timeout = 30
        loop = asyncio.new_event_loop()
        future = loop.create_future()
        fresh_timestamp = time.time()
        daemon._pending_results["fresh-id"] = (future, fresh_timestamp)
        daemon._cleanup_expired_pending()
        assert "fresh-id" in daemon._pending_results
        assert not future.done()
        loop.close()

    def test_cleanup_does_not_override_resolved_future(self):
        daemon = BridgeDaemon()
        daemon._command_timeout = 5
        loop = asyncio.new_event_loop()
        future = loop.create_future()
        future.set_result({"ok": True, "data": "already_done"})
        old_timestamp = time.time() - 10
        daemon._pending_results["resolved-id"] = (future, old_timestamp)
        daemon._cleanup_expired_pending()
        assert "resolved-id" not in daemon._pending_results
        assert future.result() == {"ok": True, "data": "already_done"}
        loop.close()

    def test_command_timeout_default(self):
        with patch.dict(os.environ, {}, clear=True):
            daemon = BridgeDaemon()
            assert daemon._command_timeout == 30

    def test_command_timeout_from_env(self):
        with patch.dict(os.environ, {"BCO_BRIDGE_TIMEOUT": "60"}):
            daemon = BridgeDaemon()
            assert daemon._command_timeout == 60

    def test_cleanup_multiple_expired(self):
        daemon = BridgeDaemon()
        daemon._command_timeout = 5
        loop = asyncio.new_event_loop()
        old_ts = time.time() - 10
        fresh_ts = time.time()
        f1 = loop.create_future()
        f2 = loop.create_future()
        f3 = loop.create_future()
        daemon._pending_results["exp-1"] = (f1, old_ts)
        daemon._pending_results["fresh-1"] = (f3, fresh_ts)
        daemon._pending_results["exp-2"] = (f2, old_ts)
        daemon._cleanup_expired_pending()
        assert set(daemon._pending_results.keys()) == {"fresh-1"}
        assert f1.done() and f2.done()
        assert not f3.done()
        loop.close()
