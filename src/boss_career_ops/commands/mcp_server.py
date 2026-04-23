import asyncio
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)

def run_mcp_server():
    """启动 MCP Server（供 Claude Desktop 等客户端调用）"""
    from boss_career_ops.mcp.server import main
    asyncio.run(main())
