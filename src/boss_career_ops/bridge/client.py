import json
from typing import Any

import httpx

from boss_career_ops.bridge.protocol import BridgeCommand, BridgeResult, CommandType
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)

DEFAULT_BRIDGE_URL = "http://127.0.0.1:18765"


class BridgeClient:
    def __init__(self, bridge_url: str = DEFAULT_BRIDGE_URL):
        self._bridge_url = bridge_url.rstrip("/")

    def is_available(self) -> bool:
        try:
            resp = httpx.get(f"{self._bridge_url}/status", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    def send_command(self, command: BridgeCommand) -> BridgeResult:
        if not self.is_available():
            return BridgeResult(ok=False, error="Bridge 不可用", id=command.id)
        try:
            payload = {
                "type": command.type.value,
                "params": command.params,
                "id": command.id,
            }
            with httpx.Client(timeout=30.0) as client:
                with client.ws_connect(f"{self._bridge_url}/ws") as ws:
                    ws.send_text(json.dumps(payload))
                    response = ws.receive()
                    data = json.loads(response.data) if response.data else {}
                    return BridgeResult(
                        ok=data.get("ok", False),
                        data=data.get("data"),
                        error=data.get("error", ""),
                        id=data.get("id", command.id),
                    )
        except Exception as e:
            logger.error("Bridge 命令失败: %s", e)
            return BridgeResult(ok=False, error=str(e), id=command.id)

    def get_cookies(self) -> BridgeResult:
        cmd = BridgeCommand(type=CommandType.GET_COOKIES)
        return self.send_command(cmd)

    def navigate(self, url: str) -> BridgeResult:
        cmd = BridgeCommand(type=CommandType.NAVIGATE, params={"url": url})
        return self.send_command(cmd)

    def click(self, selector: str) -> BridgeResult:
        cmd = BridgeCommand(type=CommandType.CLICK, params={"selector": selector})
        return self.send_command(cmd)

    def type_text(self, selector: str, text: str) -> BridgeResult:
        cmd = BridgeCommand(type=CommandType.TYPE_TEXT, params={"selector": selector, "text": text})
        return self.send_command(cmd)

    def screenshot(self) -> BridgeResult:
        cmd = BridgeCommand(type=CommandType.SCREENSHOT)
        return self.send_command(cmd)

    def execute_js(self, script: str) -> BridgeResult:
        cmd = BridgeCommand(type=CommandType.EXECUTE_JS, params={"script": script})
        return self.send_command(cmd)
