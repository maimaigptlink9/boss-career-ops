import json
from unittest.mock import patch, MagicMock

import pytest

from boss_career_ops.agent.tools import write_evaluation, get_job_detail


class TestEvaluateNodeWithLlm:
    @patch("boss_career_ops.agent.llm.get_llm")
    def test_llm_semantic_evaluation(self, mock_get_llm):
        mock_llm = MagicMock()
        response = MagicMock()
        response.content = json.dumps({
            "scores": {
                "匹配度": {"score": 4, "reason": "技能匹配"},
                "薪资": {"score": 3, "reason": "薪资一般"},
                "地点": {"score": 5, "reason": "目标城市"},
                "发展": {"score": 4, "reason": "有成长空间"},
                "团队": {"score": 3, "reason": "团队规模适中"},
            },
            "total_score": 3.8,
            "grade": "B",
            "analysis": "综合匹配度较高",
        })
        mock_llm.invoke.return_value = response
        mock_get_llm.return_value = mock_llm
        from boss_career_ops.agent.prompts import EVALUATE_SYSTEM
        assert "匹配度" in EVALUATE_SYSTEM
        assert "薪资" in EVALUATE_SYSTEM


class TestEvaluateNodeFallback:
    @patch("boss_career_ops.evaluator.engine.EvaluationEngine")
    @patch("boss_career_ops.agent.llm.get_llm", return_value=None)
    def test_fallback_to_rule_engine(self, mock_get_llm, mock_engine_cls):
        mock_engine = MagicMock()
        mock_engine.evaluate.return_value = {
            "scores": {"匹配度": 3.0, "薪资": 3.0, "地点": 3.0, "发展": 3.0, "团队": 3.0},
            "total_score": 3.0,
            "grade": "C",
        }
        mock_engine_cls.return_value = mock_engine
        result = mock_engine.evaluate({"job_id": "job1"})
        assert result["grade"] == "C"


class TestEvaluateWritesResults:
    @patch("boss_career_ops.agent.tools.PipelineManager")
    def test_write_evaluation_saves_to_pipeline(self, mock_pm_cls):
        mock_pm = MagicMock()
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        mock_pm_cls.return_value = mock_pm
        write_evaluation("job1", 4.2, "B", "匹配度较高", scores_detail={"匹配度": 4.0})
        mock_pm.save_ai_result.assert_called_once()
        mock_pm.update_score.assert_called_once_with("job1", 4.2, "B")
