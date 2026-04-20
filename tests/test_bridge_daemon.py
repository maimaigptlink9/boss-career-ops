import asyncio
from aiohttp.test_utils import AioHTTPTestCase, unittest_run_loop
from aiohttp import web

from boss_career_ops.bridge.daemon import BridgeDaemon


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
