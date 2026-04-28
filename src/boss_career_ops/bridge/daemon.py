import json
import asyncio
import os
import secrets
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aiohttp import web, WSMsgType

from boss_career_ops.bridge.protocol import BridgeCommand, BridgeResult, CommandType
from boss_career_ops.config.settings import BCO_HOME
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 18765
TOKEN_FILE = BCO_HOME / "bridge_token"

REQUIRED_COOKIE_FIELDS = {"wt2"}
STOKEN_COOKIE_ALIASES = ["stoken", "__zp_stoken__"]

_command_handlers: dict[str, Any] = {}


def _register_handler(command_type: str):
    def decorator(func):
        _command_handlers[command_type] = func
        return func
    return decorator


class BridgeDaemon:
    _command_handlers = _command_handlers

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self._host = host
        self._port = port
        self._started_at: float = time.time()
        self._last_cookie_result: dict | None = None
        self._token: str = self._generate_token()
        self._command_timeout = int(os.environ.get("BCO_BRIDGE_TIMEOUT", "30"))
        self._app = web.Application()
        self._app.router.add_get("/status", self._handle_status)
        self._app.router.add_get("/ws", self._handle_ws)
        self._extensions: list[web.WebSocketResponse] = []
        self._pending_results: dict[str, tuple[asyncio.Future, float]] = {}

    def _generate_token(self) -> str:
        token = secrets.token_hex(32)
        TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_FILE.write_text(token, encoding="utf-8")
        logger.info("Bridge token 已生成并保存到 %s", TOKEN_FILE)
        return token

    async def _handle_status(self, request: web.Request) -> web.Response:
        uptime = int(time.time() - self._started_at)
        result: dict[str, Any] = {
            "ok": True,
            "extensions_connected": len(self._extensions),
            "version": "1.0",
            "uptime_seconds": uptime,
        }
        if self._last_cookie_result is not None:
            result["last_cookie_fetch"] = self._last_cookie_result
        return web.json_response(result)

    def _validate_token(self, request: web.Request) -> bool:
        token_param = request.query.get("token", "")
        return token_param == self._token

    async def _handle_ws(self, request: web.Request) -> web.WebSocketResponse:
        if not self._validate_token(request):
            logger.warning("WebSocket 连接被拒绝：token 无效")
            ws = web.WebSocketResponse()
            await ws.prepare(request)
            await ws.send_json({"ok": False, "error": "认证失败：token 无效"})
            await ws.close()
            return ws
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        self._extensions.append(ws)
        logger.info("Chrome 扩展已连接")
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        cmd_id = data.get("id", "")
                        if cmd_id and cmd_id in self._pending_results:
                            future, _ = self._pending_results.pop(cmd_id)
                            if not future.done():
                                future.set_result(data)
                        else:
                            self._cleanup_expired_pending()
                            result = await self._process_command(data)
                            await ws.send_json(result)
                    except json.JSONDecodeError:
                        await ws.send_json({"ok": False, "error": "无效 JSON"})
                elif msg.type == WSMsgType.ERROR:
                    logger.error("WebSocket 错误: %s", ws.exception())
        finally:
            self._extensions.remove(ws)
            logger.info("Chrome 扩展已断开")
        return ws

    def _update_cookie_result(self, result_data: Any) -> None:
        cookies: dict[str, str] = {}
        if isinstance(result_data, dict):
            cookies = result_data
        elif isinstance(result_data, list):
            for c in result_data:
                if isinstance(c, dict) and "name" in c and "value" in c:
                    cookies[c["name"]] = c["value"]

        missing = []
        if not cookies.get("wt2"):
            missing.append("wt2")
        has_stoken = any(cookies.get(a) for a in STOKEN_COOKIE_ALIASES)
        if not has_stoken:
            missing.append("stoken")

        self._last_cookie_result = {
            "time": datetime.now(timezone.utc).isoformat(),
            "valid": len(missing) == 0,
            "cookie_count": len(cookies),
            "missing": missing,
        }

    async def _process_command(self, data: dict) -> dict:
        cmd_type = data.get("type", "")
        handler = self._command_handlers.get(cmd_type)
        if handler:
            return await handler(self, data)
        return {"ok": False, "error": f"未知命令: {cmd_type}", "id": data.get("id", "")}

    @_register_handler(CommandType.PING.value)
    async def _handle_ping(self, data: dict) -> dict:
        return {"ok": True, "data": "pong", "id": data.get("id", "")}

    @_register_handler(CommandType.GET_COOKIES.value)
    async def _handle_get_cookies(self, data: dict) -> dict:
        result = await self._forward_to_extensions(data)
        if result.get("ok") and result.get("data") is not None:
            self._update_cookie_result(result["data"])
        return result

    async def _handle_forward(self, data: dict) -> dict:
        return await self._forward_to_extensions(data)

    def _cleanup_expired_pending(self):
        now = time.time()
        expired = [
            cmd_id for cmd_id, (future, ts) in self._pending_results.items()
            if now - ts > self._command_timeout
        ]
        for cmd_id in expired:
            future, _ = self._pending_results.pop(cmd_id)
            if not future.done():
                future.set_result({"ok": False, "error": "命令超时", "id": cmd_id})

    async def _forward_to_extensions(self, data: dict) -> dict:
        if not self._extensions:
            return {"ok": False, "error": "无 Chrome 扩展连接", "id": data.get("id", "")}
        cmd_id = data.get("id", "")
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        if cmd_id:
            self._pending_results[cmd_id] = (future, time.time())
        try:
            ws = self._extensions[0]
            await ws.send_json(data)
            try:
                result = await asyncio.wait_for(future, timeout=10.0)
                return result
            except asyncio.TimeoutError:
                self._pending_results.pop(cmd_id, None)
                return {"ok": False, "error": "扩展响应超时", "id": cmd_id}
        except Exception as e:
            self._pending_results.pop(cmd_id, None)
            logger.error("转发命令到扩展失败: %s", e)
            return {"ok": False, "error": str(e), "id": cmd_id}

    def run(self):
        logger.info("Bridge daemon 启动: %s:%d", self._host, self._port)
        web.run_app(self._app, host=self._host, port=self._port)


for _cmd in [
    CommandType.NAVIGATE.value,
    CommandType.CLICK.value,
    CommandType.TYPE_TEXT.value,
    CommandType.SCREENSHOT.value,
    CommandType.EXECUTE_JS.value,
]:
    BridgeDaemon._command_handlers[_cmd] = BridgeDaemon._handle_forward


def start_daemon(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    daemon = BridgeDaemon(host=host, port=port)
    daemon.run()
