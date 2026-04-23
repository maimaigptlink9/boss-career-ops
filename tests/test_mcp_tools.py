import json
from unittest.mock import patch, MagicMock

import pytest

from boss_career_ops.mcp.tools import register_tools
from mcp.types import TextContent


def _make_decorator_mock():
    captured = {}

    def decorator(*args, **kwargs):
        def wrapper(fn):
            captured["handler"] = fn
            return fn
        return wrapper

    decorator.captured = captured
    return decorator


class TestRegisterTools:
    def test_registers_handlers(self):
        mock_app = MagicMock()
        register_tools(mock_app)
        assert mock_app.list_tools.called
        assert mock_app.call_tool.called

    @pytest.mark.asyncio
    @patch("boss_career_ops.agent.tools.search_jobs")
    async def test_call_tool_with_search_jobs(self, mock_search_jobs):
        mock_search_jobs.return_value = [
            {"job_id": "job1", "job_name": "Python开发", "company_name": "公司A"}
        ]
        mock_app = MagicMock()
        call_tool_dec = _make_decorator_mock()
        list_tools_dec = _make_decorator_mock()
        mock_app.call_tool = call_tool_dec
        mock_app.list_tools = list_tools_dec
        register_tools(mock_app)
        call_tool_handler = call_tool_dec.captured["handler"]
        result = await call_tool_handler("search_jobs", {"keyword": "Python", "city": ""})
        assert len(result) == 1
        assert isinstance(result[0], TextContent)
        parsed = json.loads(result[0].text)
        assert parsed[0]["job_id"] == "job1"

    @pytest.mark.asyncio
    async def test_call_tool_with_unknown_tool(self):
        mock_app = MagicMock()
        call_tool_dec = _make_decorator_mock()
        list_tools_dec = _make_decorator_mock()
        mock_app.call_tool = call_tool_dec
        mock_app.list_tools = list_tools_dec
        register_tools(mock_app)
        call_tool_handler = call_tool_dec.captured["handler"]
        result = await call_tool_handler("unknown_tool", {})
        assert len(result) == 1
        parsed = json.loads(result[0].text)
        assert "error" in parsed
