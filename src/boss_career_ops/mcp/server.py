import asyncio

from mcp.server import Server
from mcp.server.stdio import stdio_server

from boss_career_ops.mcp.resources import register_resources
from boss_career_ops.mcp.tools import register_tools

app = Server("boss-career-ops")

register_tools(app)
register_resources(app)


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream, write_stream, app.create_initialization_options()
        )
