import json
from unittest.mock import patch, MagicMock

import pytest

from boss_career_ops.mcp.resources import register_resources


def _make_decorator_mock():
    captured = {}

    def decorator(*args, **kwargs):
        def wrapper(fn):
            captured["handler"] = fn
            return fn
        return wrapper

    decorator.captured = captured
    return decorator


class TestRegisterResources:
    def test_registers_handlers(self):
        mock_app = MagicMock()
        register_resources(mock_app)
        assert mock_app.list_resources.called
        assert mock_app.read_resource.called

    @pytest.mark.asyncio
    @patch("boss_career_ops.agent.tools.get_profile")
    async def test_read_resource_profile(self, mock_get_profile):
        mock_get_profile.return_value = {
            "name": "测试用户",
            "title": "工程师",
            "skills": ["Python"],
        }
        mock_app = MagicMock()
        read_dec = _make_decorator_mock()
        list_dec = _make_decorator_mock()
        template_dec = _make_decorator_mock()
        mock_app.read_resource = read_dec
        mock_app.list_resources = list_dec
        mock_app.list_resource_templates = template_dec
        register_resources(mock_app)
        read_handler = read_dec.captured["handler"]
        result = await read_handler("bco://profile")
        parsed = json.loads(result)
        assert parsed["name"] == "测试用户"

    @pytest.mark.asyncio
    @patch("boss_career_ops.agent.tools.get_cv")
    async def test_read_resource_cv(self, mock_get_cv):
        mock_get_cv.return_value = "# 我的简历\nPython工程师"
        mock_app = MagicMock()
        read_dec = _make_decorator_mock()
        list_dec = _make_decorator_mock()
        template_dec = _make_decorator_mock()
        mock_app.read_resource = read_dec
        mock_app.list_resources = list_dec
        mock_app.list_resource_templates = template_dec
        register_resources(mock_app)
        read_handler = read_dec.captured["handler"]
        result = await read_handler("bco://cv")
        assert "简历" in result

    @pytest.mark.asyncio
    async def test_read_resource_unknown_uri(self):
        mock_app = MagicMock()
        read_dec = _make_decorator_mock()
        list_dec = _make_decorator_mock()
        template_dec = _make_decorator_mock()
        mock_app.read_resource = read_dec
        mock_app.list_resources = list_dec
        mock_app.list_resource_templates = template_dec
        register_resources(mock_app)
        read_handler = read_dec.captured["handler"]
        with pytest.raises(ValueError, match="未知资源"):
            await read_handler("bco://unknown")
