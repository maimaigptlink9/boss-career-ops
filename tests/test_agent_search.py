from unittest.mock import patch, MagicMock

import pytest

from boss_career_ops.agent.tools import search_jobs


class TestSearchNodeWithLlm:
    @patch("boss_career_ops.agent.tools.get_active_adapter")
    def test_search_with_multi_keyword_strategy(self, mock_adapter_fn):
        mock_adapter = MagicMock()
        job1 = MagicMock()
        job1.job_id = "job1"
        job1.job_name = "Python开发"
        job1.company_name = "公司A"
        job1.city = "深圳"
        job1.salary_desc = "20K-40K"
        job1.skills = ["Python"]
        job1.security_id = "sec1"
        mock_adapter.search.return_value = [job1]
        mock_adapter.build_search_params.return_value = {"keyword": "Python", "city": ""}
        mock_adapter_fn.return_value = mock_adapter
        results = search_jobs("Python")
        assert len(results) == 1
        assert results[0]["job_id"] == "job1"


class TestSearchNodeWithoutLlm:
    @patch("boss_career_ops.agent.tools.get_active_adapter")
    def test_search_single_keyword(self, mock_adapter_fn):
        mock_adapter = MagicMock()
        job1 = MagicMock()
        job1.job_id = "job1"
        job1.job_name = "Go开发"
        job1.company_name = "公司B"
        job1.city = "北京"
        job1.salary_desc = "25K-50K"
        job1.skills = ["Go"]
        job1.security_id = "sec2"
        mock_adapter.search.return_value = [job1]
        mock_adapter.build_search_params.return_value = {"keyword": "Go", "city": ""}
        mock_adapter_fn.return_value = mock_adapter
        results = search_jobs("Go")
        assert len(results) == 1
        assert results[0]["job_name"] == "Go开发"


class TestSearchDeduplication:
    @patch("boss_career_ops.agent.tools.get_active_adapter")
    def test_adapter_error_returns_empty(self, mock_adapter_fn):
        mock_adapter_fn.side_effect = Exception("连接失败")
        results = search_jobs("Python")
        assert results == []
