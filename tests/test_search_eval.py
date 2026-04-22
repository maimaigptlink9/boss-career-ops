from unittest.mock import patch, MagicMock

from boss_career_ops.platform.models import Job


class TestSearchAutoEvaluation:
    @patch("boss_career_ops.commands.search.EvaluationEngine")
    @patch("boss_career_ops.commands.search.PipelineManager")
    @patch("boss_career_ops.commands.search.CacheStore")
    @patch("boss_career_ops.commands.search.get_active_adapter")
    @patch("boss_career_ops.commands.search.Thresholds")
    def test_search_auto_evaluates_jobs(
        self, mock_thresholds_cls, mock_get_adapter, mock_cache_cls, mock_pm_cls, mock_engine_cls
    ):
        mock_thresholds = MagicMock()
        mock_thresholds.rate_limit.search_page_delay_min = 1.0
        mock_thresholds.rate_limit.search_page_delay_max = 2.0
        mock_thresholds.rate_limit.search_max_pages = 1
        mock_thresholds.cache.search_ttl = 300
        mock_thresholds_cls.return_value = mock_thresholds

        job1 = Job(job_id="j1", job_name="Python工程师", company_name="A公司", security_id="s1")
        job2 = Job(job_id="j2", job_name="Go工程师", company_name="B公司", security_id="s2")

        mock_adapter = MagicMock()
        mock_adapter.search.return_value = [job1, job2]
        mock_adapter.build_search_params.return_value = {"scene": "1"}
        mock_get_adapter.return_value = mock_adapter

        mock_cache = MagicMock()
        mock_cache.__enter__ = MagicMock(return_value=mock_cache)
        mock_cache.__exit__ = MagicMock(return_value=False)
        mock_cache_cls.return_value = mock_cache

        mock_pm = MagicMock()
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        mock_pm_cls.return_value = mock_pm

        mock_engine = MagicMock()
        mock_engine.evaluate.side_effect = [
            {"scores": {"匹配度": 4.0}, "total_score": 4.0, "grade": "B"},
            {"scores": {"匹配度": 3.0}, "total_score": 3.0, "grade": "C"},
        ]
        mock_engine_cls.return_value = mock_engine

        from boss_career_ops.commands.search import run_search
        run_search("Python", "北京", "", 1, 15, 1)

        assert mock_engine.evaluate.call_count == 2
        mock_pm.update_job_data.assert_any_call("j1", {"evaluation": {"scores": {"匹配度": 4.0}, "total_score": 4.0, "grade": "B"}})
        mock_pm.update_job_data.assert_any_call("j2", {"evaluation": {"scores": {"匹配度": 3.0}, "total_score": 3.0, "grade": "C"}})

    @patch("boss_career_ops.commands.search.EvaluationEngine")
    @patch("boss_career_ops.commands.search.PipelineManager")
    @patch("boss_career_ops.commands.search.CacheStore")
    @patch("boss_career_ops.commands.search.get_active_adapter")
    @patch("boss_career_ops.commands.search.Thresholds")
    def test_search_eval_limit_50(
        self, mock_thresholds_cls, mock_get_adapter, mock_cache_cls, mock_pm_cls, mock_engine_cls
    ):
        mock_thresholds = MagicMock()
        mock_thresholds.rate_limit.search_page_delay_min = 1.0
        mock_thresholds.rate_limit.search_page_delay_max = 2.0
        mock_thresholds.rate_limit.search_max_pages = 1
        mock_thresholds.cache.search_ttl = 300
        mock_thresholds_cls.return_value = mock_thresholds

        jobs = [Job(job_id=f"j{i}", job_name=f"Job{i}", company_name="C", security_id=f"s{i}") for i in range(55)]

        mock_adapter = MagicMock()
        mock_adapter.search.return_value = jobs
        mock_adapter.build_search_params.return_value = {"scene": "1"}
        mock_get_adapter.return_value = mock_adapter

        mock_cache = MagicMock()
        mock_cache.__enter__ = MagicMock(return_value=mock_cache)
        mock_cache.__exit__ = MagicMock(return_value=False)
        mock_cache_cls.return_value = mock_cache

        mock_pm = MagicMock()
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        mock_pm_cls.return_value = mock_pm

        mock_engine = MagicMock()
        mock_engine.evaluate.return_value = {"scores": {"匹配度": 3.0}, "total_score": 3.0, "grade": "C"}
        mock_engine_cls.return_value = mock_engine

        from boss_career_ops.commands.search import run_search
        run_search("Python", "北京", "", 1, 55, 1)

        assert mock_engine.evaluate.call_count == 50

    @patch("boss_career_ops.commands.search.EvaluationEngine")
    @patch("boss_career_ops.commands.search.PipelineManager")
    @patch("boss_career_ops.commands.search.CacheStore")
    @patch("boss_career_ops.commands.search.get_active_adapter")
    @patch("boss_career_ops.commands.search.Thresholds")
    def test_search_eval_failure_does_not_interrupt(
        self, mock_thresholds_cls, mock_get_adapter, mock_cache_cls, mock_pm_cls, mock_engine_cls
    ):
        mock_thresholds = MagicMock()
        mock_thresholds.rate_limit.search_page_delay_min = 1.0
        mock_thresholds.rate_limit.search_page_delay_max = 2.0
        mock_thresholds.rate_limit.search_max_pages = 1
        mock_thresholds.cache.search_ttl = 300
        mock_thresholds_cls.return_value = mock_thresholds

        job1 = Job(job_id="j1", job_name="Python工程师", company_name="A", security_id="s1")
        job2 = Job(job_id="j2", job_name="Go工程师", company_name="B", security_id="s2")

        mock_adapter = MagicMock()
        mock_adapter.search.return_value = [job1, job2]
        mock_adapter.build_search_params.return_value = {"scene": "1"}
        mock_get_adapter.return_value = mock_adapter

        mock_cache = MagicMock()
        mock_cache.__enter__ = MagicMock(return_value=mock_cache)
        mock_cache.__exit__ = MagicMock(return_value=False)
        mock_cache_cls.return_value = mock_cache

        mock_pm = MagicMock()
        mock_pm.__enter__ = MagicMock(return_value=mock_pm)
        mock_pm.__exit__ = MagicMock(return_value=False)
        mock_pm_cls.return_value = mock_pm

        mock_engine = MagicMock()
        mock_engine.evaluate.side_effect = [Exception("评分异常"), {"scores": {"匹配度": 3.0}, "total_score": 3.0, "grade": "C"}]
        mock_engine_cls.return_value = mock_engine

        from boss_career_ops.commands.search import run_search
        run_search("Python", "北京", "", 1, 15, 1)

        assert mock_engine.evaluate.call_count == 2
        assert mock_pm.update_job_data.call_count == 1
