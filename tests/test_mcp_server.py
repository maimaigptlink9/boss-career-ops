from unittest.mock import patch, MagicMock

import pytest

from boss_career_ops.mcp.server import app


class TestMcpServerAppCreation:
    def test_app_is_server_instance(self):
        from mcp.server import Server
        assert isinstance(app, Server)

    def test_server_name(self):
        assert app.name == "boss-career-ops"
