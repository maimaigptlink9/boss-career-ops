from unittest.mock import patch, MagicMock

from boss_career_ops.evaluator.ai_scorer import AIEvaluator
from boss_career_ops.config.settings import Settings, Profile, SalaryExpectation


class TestAIEvaluator:
    def _make_evaluator(self, provider=None, profile=None):
        with patch("boss_career_ops.evaluator.ai_scorer.get_provider", return_value=provider):
            with patch.object(Settings, "__init__", lambda self, *a, **kw: None):
                settings = Settings()
                settings.profile = profile or Profile(
                    name="测试用户",
                    title="AI Agent 开发工程师",
                    skills=["Python", "Agent 开发", "LangChain"],
                    expected_salary=SalaryExpectation(min=18000, max=30000),
                    preferred_cities=["深圳"],
                    education="本科",
                    career_goals="AI Agent 开发",
                )
                settings.cv_content = ""
                evaluator = AIEvaluator()
                evaluator._settings = settings
                return evaluator

    def test_score_job_match_with_ai(self):
        mock_provider = MagicMock()
        mock_provider.chat.return_value = "4.2"
        evaluator = self._make_evaluator(provider=mock_provider)
        job = {"jobName": "AI Agent 工程师", "brandName": "测试公司", "salaryDesc": "20-40K"}
        score = evaluator.score_job_match(job)
        assert 0.0 <= score <= 5.0
        assert score == 4.2
        mock_provider.chat.assert_called_once()

    def test_score_job_match_ai_failure_fallback(self):
        mock_provider = MagicMock()
        mock_provider.chat.side_effect = Exception("API error")
        evaluator = self._make_evaluator(provider=mock_provider, profile=Profile(skills=["Python"]))
        job = {"jobName": "Python 开发"}
        score = evaluator.score_job_match(job)
        assert 0.0 <= score <= 5.0

    def test_score_job_match_no_provider(self):
        evaluator = self._make_evaluator(provider=None, profile=Profile(skills=["Python"]))
        job = {"jobName": "Python 开发"}
        score = evaluator.score_job_match(job)
        assert 0.0 <= score <= 5.0

    def test_detailed_evaluate_with_ai(self):
        mock_provider = MagicMock()
        mock_provider.chat.return_value = '{"scores":{"匹配度":4.0,"薪资":3.5,"地点":4.5,"发展":3.5,"团队":3.0},"grade":"B","recommendation":"值得投入","analysis":"匹配度较高"}'
        evaluator = self._make_evaluator(provider=mock_provider)
        job = {"jobName": "AI Agent 工程师", "brandName": "测试公司", "postDescription": "负责 Agent 开发"}
        result = evaluator.detailed_evaluate(job)
        assert "scores" in result
        assert "grade" in result
        assert result["grade"] == "B"

    def test_detailed_evaluate_no_provider_fallback(self):
        evaluator = self._make_evaluator(provider=None)
        job = {"jobName": "测试", "brandName": "公司", "salaryDesc": "10-20K"}
        result = evaluator.detailed_evaluate(job)
        assert "scores" in result
        assert "total_score" in result

    def test_parse_score_extracts_number(self):
        evaluator = self._make_evaluator()
        assert evaluator._parse_score("3.8") == 3.8
        assert evaluator._parse_score("分数是 4.2 分") == 4.2
        assert evaluator._parse_score("no number") == 2.5

    def test_parse_json_response_valid(self):
        evaluator = self._make_evaluator()
        resp = '{"scores":{"匹配度":4.0},"grade":"B"}'
        result = evaluator._parse_json_response(resp)
        assert result["grade"] == "B"

    def test_parse_json_response_invalid_returns_default(self):
        evaluator = self._make_evaluator()
        result = evaluator._parse_json_response("not json")
        assert result["grade"] == "C"
        assert "scores" in result

    def test_rule_based_score_with_matching_title(self):
        evaluator = self._make_evaluator(provider=None, profile=Profile(skills=["Python"]))
        job = {"jobName": "Python 开发工程师"}
        score = evaluator._rule_based_score(job)
        assert score > 1.0

    def test_rule_based_score_no_match(self):
        evaluator = self._make_evaluator(provider=None, profile=Profile(skills=["Rust"]))
        job = {"jobName": "Java 开发工程师"}
        score = evaluator._rule_based_score(job)
        assert score == 1.0

    def test_score_clamped_to_range(self):
        mock_provider = MagicMock()
        mock_provider.chat.return_value = "9.9"
        evaluator = self._make_evaluator(provider=mock_provider)
        job = {"jobName": "测试"}
        score = evaluator.score_job_match(job)
        assert score <= 5.0

        mock_provider.chat.return_value = "-1.0"
        score = evaluator.score_job_match(job)
        assert score >= 0.0
