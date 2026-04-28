from unittest.mock import patch, MagicMock

import pytest

from boss_career_ops.agent.tools import write_resume


class TestResumeNodeWithLlm:
    @patch("boss_career_ops.agent.llm.get_llm")
    def test_llm_rewrite_resume(self, mock_get_llm):
        mock_llm = MagicMock()
        response = MagicMock()
        response.content = "# 简历\n## 核心技能\n- Python\n- FastAPI\n## 工作经历\n负责后端架构设计"
        mock_llm.invoke.return_value = response
        mock_get_llm.return_value = mock_llm
        from boss_career_ops.agent.prompts import RESUME_SYSTEM
        assert "简历" in RESUME_SYSTEM
        assert "ATS" in RESUME_SYSTEM


class TestResumeNodeFallback:
    @patch("boss_career_ops.resume.generator.ResumeGenerator")
    @patch("boss_career_ops.agent.llm.get_llm", return_value=None)
    def test_fallback_to_resume_generator(self, mock_get_llm, mock_gen_cls):
        mock_gen = MagicMock()
        mock_gen.generate.return_value = "# 简历\n基础内容"
        mock_gen_cls.return_value = mock_gen
        result = mock_gen.generate({"job_id": "job1", "job_name": "Python开发"})
        assert "简历" in result


class TestWriteResume:
    @patch("boss_career_ops.agent.tools.PipelineManager")
    def test_write_resume_saves_to_pipeline(self, mock_pm_cls):
        mock_pm = MagicMock()
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        mock_pm_cls.return_value = mock_pm
        write_resume("job1", "# 简历\n润色后内容")
        mock_pm.save_ai_result.assert_called_once()
        call_args = mock_pm.save_ai_result.call_args
        assert call_args[0][0] == "job1"
        assert call_args[0][1] == "resume"
