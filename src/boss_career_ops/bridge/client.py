import asyncio
import concurrent.futures
import json
from pathlib import Path
from typing import Any

import aiohttp
import httpx

from boss_career_ops.bridge.protocol import BridgeCommand, BridgeResult, CommandType
from boss_career_ops.config.settings import BCO_HOME
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)

DEFAULT_BRIDGE_URL = "http://127.0.0.1:18765"
TOKEN_FILE = BCO_HOME / "bridge_token"


def _read_token() -> str:
    try:
        return TOKEN_FILE.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return ""


class BridgeClient:
    def __init__(self, bridge_url: str = DEFAULT_BRIDGE_URL):
        self._bridge_url = bridge_url.rstrip("/")

    def is_available(self) -> bool:
        try:
            with httpx.Client(proxy=None) as client:
                resp = client.get(f"{self._bridge_url}/status", timeout=5.0)
            return resp.status_code == 200
        except Exception:
            return False

    async def _ws_send(self, payload: dict[str, Any]) -> dict[str, Any]:
        token = _read_token()
        ws_url = f"{self._bridge_url}/ws"
        if token:
            ws_url = f"{ws_url}?token={token}"
        async with aiohttp.ClientSession() as session:
            async with session.ws_connect(
                ws_url, timeout=aiohttp.ClientWSTimeout(ws_close=30)
            ) as ws:
                await ws.send_str(json.dumps(payload))
                msg = await ws.receive()
                if msg.type == aiohttp.WSMsgType.TEXT:
                    return json.loads(msg.data)
                return {}

    async def send_command_async(self, command: BridgeCommand) -> BridgeResult:
        if not await asyncio.to_thread(self.is_available):
            return BridgeResult(ok=False, error="Bridge 不可用", id=command.id)
        try:
            payload = {
                "type": command.type.value,
                "params": command.params,
                "id": command.id,
            }
            data = await self._ws_send(payload)
            return BridgeResult(
                ok=data.get("ok", False),
                data=data.get("data"),
                error=data.get("error", ""),
                id=data.get("id", command.id),
            )
        except Exception as e:
            logger.error("Bridge 命令失败: %s", e)
            return BridgeResult(ok=False, error=str(e), id=command.id)

    def send_command(self, command: BridgeCommand) -> BridgeResult:
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        if loop and loop.is_running():
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(asyncio.run, self.send_command_async(command))
                return future.result()
        else:
            return asyncio.run(self.send_command_async(command))

    def get_cookies(self) -> dict[str, str]:
        cmd = BridgeCommand(type=CommandType.GET_COOKIES)
        result = self.send_command(cmd)
        if not result.ok or result.data is None:
            return {}
        if isinstance(result.data, dict):
            return result.data
        if isinstance(result.data, list):
            return {c["name"]: c["value"] for c in result.data if "name" in c and "value" in c}
        return {}

    def navigate(self, url: str) -> BridgeResult:
        cmd = BridgeCommand(type=CommandType.NAVIGATE, params={"url": url})
        return self.send_command(cmd)

    def click(self, selector: str) -> BridgeResult:
        cmd = BridgeCommand(type=CommandType.CLICK, params={"selector": selector})
        return self.send_command(cmd)

    def execute_js(self, script: str) -> BridgeResult:
        cmd = BridgeCommand(type=CommandType.EXECUTE_JS, params={"script": script})
        return self.send_command(cmd)
