import json
import asyncio
from typing import Any

from aiohttp import web, WSMsgType

from boss_career_ops.bridge.protocol import BridgeCommand, BridgeResult, CommandType
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 18765


class BridgeDaemon:
    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self._host = host
        self._port = port
        self._app = web.Application()
        self._app.router.add_get("/status", self._handle_status)
        self._app.router.add_get("/ws", self._handle_ws)
        self._extensions: list[web.WebSocketResponse] = []
        self._pending_results: dict[str, asyncio.Future] = {}

    async def _handle_status(self, request: web.Request) -> web.Response:
        return web.json_response({
            "ok": True,
            "extensions_connected": len(self._extensions),
            "version": "1.0",
        })

    async def _handle_ws(self, request: web.Request) -> web.WebSocketResponse:
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
                            future = self._pending_results.pop(cmd_id)
                            if not future.done():
                                future.set_result(data)
                        else:
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

    async def _process_command(self, data: dict) -> dict:
        cmd_type = data.get("type", "")
        params = data.get("params", {})
        cmd_id = data.get("id", "")
        if cmd_type == CommandType.PING.value:
            return {"ok": True, "data": "pong", "id": cmd_id}
        elif cmd_type == CommandType.GET_COOKIES.value:
            return await self._forward_to_extensions(data)
        elif cmd_type == CommandType.NAVIGATE.value:
            return await self._forward_to_extensions(data)
        elif cmd_type == CommandType.CLICK.value:
            return await self._forward_to_extensions(data)
        elif cmd_type == CommandType.TYPE_TEXT.value:
            return await self._forward_to_extensions(data)
        elif cmd_type == CommandType.SCREENSHOT.value:
            return await self._forward_to_extensions(data)
        elif cmd_type == CommandType.EXECUTE_JS.value:
            return await self._forward_to_extensions(data)
        else:
            return {"ok": False, "error": f"未知命令: {cmd_type}", "id": cmd_id}

    async def _forward_to_extensions(self, data: dict) -> dict:
        if not self._extensions:
            return {"ok": False, "error": "无 Chrome 扩展连接", "id": data.get("id", "")}
        cmd_id = data.get("id", "")
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        if cmd_id:
            self._pending_results[cmd_id] = future
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


def start_daemon(host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
    daemon = BridgeDaemon(host=host, port=port)
    daemon.run()
