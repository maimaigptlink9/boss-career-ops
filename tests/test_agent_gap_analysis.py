import json
from unittest.mock import patch, MagicMock

import pytest

from boss_career_ops.agent.tools import analyze_skill_gap


class TestGapAnalysisWithLlm:
    @patch("boss_career_ops.agent.llm.get_llm")
    def test_llm_gap_analysis(self, mock_get_llm):
        mock_llm = MagicMock()
        response = MagicMock()
        response.content = json.dumps({
            "missing_skills": [
                {"skill": "Kubernetes", "priority": "high", "suggestion": "学习 K8s 编排"},
                {"skill": "Rust", "priority": "medium", "suggestion": "了解 Rust 基础"},
            ],
            "overall_assessment": "需补充云原生技能",
        })
        mock_llm.invoke.return_value = response
        mock_get_llm.return_value = mock_llm
        from boss_career_ops.agent.prompts import GAP_ANALYSIS_SYSTEM
        assert "missing_skills" in GAP_ANALYSIS_SYSTEM
        assert "priority" in GAP_ANALYSIS_SYSTEM


class TestGapAnalysisWithoutLlm:
    @patch("boss_career_ops.agent.tools.list_pipeline_jobs")
    @patch("boss_career_ops.agent.tools.get_profile")
    def test_simple_comparison(self, mock_get_profile, mock_list_jobs):
        mock_get_profile.return_value = {
            "name": "测试用户",
            "skills": ["Python", "Go"],
        }
        mock_list_jobs.return_value = [{"job_id": "job1"}, {"job_id": "job2"}]
        result = analyze_skill_gap()
        assert result["skills"] == ["Python", "Go"]
        assert result["jd_count"] == 2
        assert result["analysis_available"] is True

    @patch("boss_career_ops.agent.tools.list_pipeline_jobs")
    @patch("boss_career_ops.agent.tools.get_profile")
    def test_no_skills_no_jobs(self, mock_get_profile, mock_list_jobs):
        mock_get_profile.return_value = {"name": "测试用户", "skills": []}
        mock_list_jobs.return_value = []
        result = analyze_skill_gap()
        assert result["analysis_available"] is False
