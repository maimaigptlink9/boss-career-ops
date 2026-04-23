import asyncio
from unittest.mock import patch, MagicMock

import pytest

from boss_career_ops.commands.mcp_server import run_mcp_server


class TestRunMcpServer:
    def test_function_exists_and_is_callable(self):
        assert callable(run_mcp_server)

    @patch("boss_career_ops.commands.mcp_server.asyncio")
    @patch("boss_career_ops.commands.mcp_server.main", create=True)
    def test_run_mcp_server_calls_asyncio_run(self, mock_main, mock_asyncio):
        with patch.dict("sys.modules", {"boss_career_ops.mcp.server": MagicMock(main=mock_main)}):
            run_mcp_server()
            mock_asyncio.run.assert_called_once()
