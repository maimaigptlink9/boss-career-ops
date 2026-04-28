from unittest.mock import patch, MagicMock

import pytest

from boss_career_ops.agent.tools import greet_recruiter, apply_job


class TestApplyNodeWithLlm:
    @patch("boss_career_ops.agent.llm.get_llm")
    def test_generate_personalized_greeting(self, mock_get_llm):
        mock_llm = MagicMock()
        response = MagicMock()
        response.content = "您好，我有5年Python后端经验，熟悉微服务架构，期待与您交流！"
        mock_llm.invoke.return_value = response
        mock_get_llm.return_value = mock_llm
        from boss_career_ops.agent.prompts import APPLY_SYSTEM
        assert "打招呼" in APPLY_SYSTEM
        assert "100字" in APPLY_SYSTEM


class TestApplyNodeWithoutLlm:
    @patch("boss_career_ops.agent.tools.get_active_adapter")
    def test_greet_recruiter_directly(self, mock_adapter_fn):
        mock_adapter = MagicMock()
        mock_result = MagicMock()
        mock_result.ok = True
        mock_result.message = "打招呼成功"
        mock_adapter.greet.return_value = mock_result
        mock_adapter_fn.return_value = mock_adapter
        result = greet_recruiter("sec1", "job1")
        assert result.ok is True
        assert result.data["message"] == "打招呼成功"

    @patch("boss_career_ops.agent.tools.get_active_adapter")
    def test_apply_job_directly(self, mock_adapter_fn):
        mock_adapter = MagicMock()
        mock_result = MagicMock()
        mock_result.ok = True
        mock_result.message = "投递成功"
        mock_adapter.apply.return_value = mock_result
        mock_adapter_fn.return_value = mock_adapter
        result = apply_job("sec1", "job1")
        assert result.ok is True
        assert result.data["message"] == "投递成功"

    @patch("boss_career_ops.agent.tools.get_active_adapter")
    def test_greet_recruiter_error(self, mock_adapter_fn):
        mock_adapter_fn.side_effect = Exception("连接失败")
        result = greet_recruiter("sec1", "job1")
        assert result.ok is False
        assert "连接失败" in result.error
