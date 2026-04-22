from boss_career_ops.bridge.protocol import BridgeCommand, BridgeResult, CommandType


class TestCommandType:
    def test_values(self):
        assert CommandType.PING.value == "ping"
        assert CommandType.GET_COOKIES.value == "get_cookies"
        assert CommandType.NAVIGATE.value == "navigate"
        assert CommandType.CLICK.value == "click"
        assert CommandType.TYPE_TEXT.value == "type_text"
        assert CommandType.SCREENSHOT.value == "screenshot"
        assert CommandType.EXECUTE_JS.value == "execute_js"


class TestBridgeCommand:
    def test_default(self):
        cmd = BridgeCommand(type=CommandType.PING)
        assert cmd.type == CommandType.PING
        assert cmd.params == {}
        assert len(cmd.id) == 12 and cmd.id.isalnum()

    def test_with_params(self):
        cmd = BridgeCommand(type=CommandType.NAVIGATE, params={"url": "https://example.com"}, id="123")
        assert cmd.params["url"] == "https://example.com"
        assert cmd.id == "123"


class TestBridgeResult:
    def test_default(self):
        r = BridgeResult()
        assert r.ok is True
        assert r.data is None
        assert r.error == ""
        assert r.id == ""

    def test_error_result(self):
        r = BridgeResult(ok=False, error="连接失败", id="abc")
        assert r.ok is False
        assert r.error == "连接失败"
