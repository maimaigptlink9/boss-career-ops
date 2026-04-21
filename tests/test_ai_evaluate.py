from unittest.mock import patch, MagicMock

from boss_career_ops.commands.ai_evaluate import (
    run_ai_evaluate,
    _score_to_grade,
    _get_recommendation,
    _get_last_searched_job,
)


class TestAiEvaluateCommand:
    @patch("boss_career_ops.commands.ai_evaluate.output_error")
    @patch("boss_career_ops.commands.ai_evaluate.CacheStore")
    def test_no_job_found(self, mock_cache_cls, mock_output_error):
        mock_cache = MagicMock()
        mock_cache.__enter__ = MagicMock(return_value=mock_cache)
        mock_cache.__exit__ = MagicMock(return_value=False)
        mock_cache.get.return_value = None
        mock_cache_cls.return_value = mock_cache
        run_ai_evaluate()
        mock_output_error.assert_called_once()
        args = mock_output_error.call_args
        assert args[1]["code"] == "JOB_NOT_FOUND" or "JOB_NOT_FOUND" in str(args)

    @patch("boss_career_ops.commands.ai_evaluate.output_json")
    @patch("boss_career_ops.commands.ai_evaluate.PipelineManager")
    @patch("boss_career_ops.commands.ai_evaluate.AIEvaluator")
    @patch("boss_career_ops.commands.ai_evaluate.CacheStore")
    def test_evaluate_with_cached_job(self, mock_cache_cls, mock_ai_eval_cls, mock_pipeline_cls, mock_output_json):
        mock_cache = MagicMock()
        mock_cache.__enter__ = MagicMock(return_value=mock_cache)
        mock_cache.__exit__ = MagicMock(return_value=False)
        mock_cache.get.return_value = [{"jobName": "AI Agent 工程师", "brandName": "测试公司", "salaryDesc": "20-40K", "securityId": "sec1"}]
        mock_cache_cls.return_value = mock_cache

        mock_evaluator = MagicMock()
        mock_evaluator.score_job_match.return_value = 3.8
        mock_ai_eval_cls.return_value = mock_evaluator

        mock_pipeline = MagicMock()
        mock_pipeline.__enter__ = MagicMock(return_value=mock_pipeline)
        mock_pipeline.__exit__ = MagicMock(return_value=False)
        mock_pipeline_cls.return_value = mock_pipeline

        run_ai_evaluate(fetch_detail=False)
        mock_output_json.assert_called_once()
        call_data = mock_output_json.call_args[1]["data"] if "data" in mock_output_json.call_args[1] else mock_output_json.call_args[0][1] if len(mock_output_json.call_args[0]) > 1 else None
        if call_data is None:
            call_data = mock_output_json.call_args[1].get("data")

    def test_score_to_grade(self):
        assert _score_to_grade(4.8) == "A"
        assert _score_to_grade(4.5) == "A"
        assert _score_to_grade(3.8) == "B"
        assert _score_to_grade(3.5) == "B"
        assert _score_to_grade(2.8) == "C"
        assert _score_to_grade(2.5) == "C"
        assert _score_to_grade(1.8) == "D"
        assert _score_to_grade(1.5) == "D"
        assert _score_to_grade(1.0) == "F"
        assert _score_to_grade(0.0) == "F"

    def test_get_recommendation(self):
        assert "强烈推荐" in _get_recommendation(4.5)
        assert "值得投入" in _get_recommendation(3.5)
        assert "一般匹配" in _get_recommendation(2.5)
        assert "谨慎考虑" in _get_recommendation(1.5)
        assert "不推荐" in _get_recommendation(0.5)

    @patch("boss_career_ops.commands.ai_evaluate.CacheStore")
    def test_get_last_searched_job_returns_first(self, mock_cache_cls):
        mock_cache = MagicMock()
        mock_cache.__enter__ = MagicMock(return_value=mock_cache)
        mock_cache.__exit__ = MagicMock(return_value=False)
        mock_cache.get.return_value = [{"jobName": "Job1"}, {"jobName": "Job2"}]
        mock_cache_cls.return_value = mock_cache
        result = _get_last_searched_job()
        assert result == {"jobName": "Job1"}

    @patch("boss_career_ops.commands.ai_evaluate.CacheStore")
    def test_get_last_searched_job_empty(self, mock_cache_cls):
        mock_cache = MagicMock()
        mock_cache.__enter__ = MagicMock(return_value=mock_cache)
        mock_cache.__exit__ = MagicMock(return_value=False)
        mock_cache.get.return_value = None
        mock_cache_cls.return_value = mock_cache
        result = _get_last_searched_job()
        assert result is None
