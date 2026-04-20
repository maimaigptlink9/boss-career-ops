from unittest.mock import patch, MagicMock

from boss_career_ops.evaluator.engine import EvaluationEngine
from boss_career_ops.config.settings import Settings, Profile, SalaryExpectation


class TestEvaluationEngine:
    def _make_engine(self, profile=None):
        with patch.object(Settings, '__init__', lambda self, *a, **kw: None):
            settings = Settings()
            settings.profile = profile or Profile()
            settings.cv_content = ""
            engine = EvaluationEngine()
            engine._settings = settings
            return engine

    def test_evaluate_returns_required_keys(self):
        engine = self._make_engine()
        job = {"jobName": "测试", "brandName": "公司", "salaryDesc": "10-20K"}
        result = engine.evaluate(job)
        assert "scores" in result
        assert "total_score" in result
        assert "grade" in result
        assert "grade_label" in result
        assert "recommendation" in result
        assert "job_name" in result
        assert "company_name" in result

    def test_evaluate_total_score_range(self):
        engine = self._make_engine()
        job = {"jobName": "测试"}
        result = engine.evaluate(job)
        assert 0.0 <= result["total_score"] <= 5.0

    def test_evaluate_grade_is_valid(self):
        engine = self._make_engine()
        job = {"jobName": "测试"}
        result = engine.evaluate(job)
        assert result["grade"] in ("A", "B", "C", "D", "F")

    def test_score_match_with_skills(self):
        profile = Profile(skills=["Go", "Docker"])
        engine = self._make_engine(profile=profile)
        job = {"jobName": "Golang", "skills": "Go,Docker,Kubernetes"}
        score = engine._score_match(job)
        assert score > 1.0

    def test_score_match_no_skills(self):
        engine = self._make_engine()
        job = {"jobName": "测试"}
        score = engine._score_match(job)
        assert score == 2.5

    def test_score_salary_matching(self):
        profile = Profile(expected_salary=SalaryExpectation(min=20000, max=40000))
        engine = self._make_engine(profile=profile)
        job = {"salaryDesc": "20-40K"}
        score = engine._score_salary(job)
        assert score >= 4.0

    def test_score_salary_no_desc(self):
        engine = self._make_engine()
        job = {}
        score = engine._score_salary(job)
        assert score == 2.5

    def test_score_location_preferred_city(self):
        profile = Profile(preferred_cities=["广州"])
        engine = self._make_engine(profile=profile)
        job = {"cityName": "广州"}
        score = engine._score_location(job)
        assert score == 4.5

    def test_score_location_not_preferred(self):
        profile = Profile(preferred_cities=["北京"])
        engine = self._make_engine(profile=profile)
        job = {"cityName": "广州"}
        score = engine._score_location(job)
        assert score == 2.0

    def test_score_growth_with_keywords(self):
        engine = self._make_engine()
        job = {"postDescription": "晋升通道 培训体系", "brandStageName": "B轮"}
        score = engine._score_growth(job)
        assert score > 3.0

    def test_score_team_with_scale(self):
        engine = self._make_engine()
        job = {"brandScaleName": "100-499人"}
        score = engine._score_team(job)
        assert score > 3.0

    def test_parse_salary_k_format(self):
        engine = self._make_engine()
        result = engine._parse_salary("20-40K")
        assert result == (20000, 40000, 12)

    def test_parse_salary_plain_numbers(self):
        engine = self._make_engine()
        result = engine._parse_salary("15000-25000")
        assert result == (15000, 25000, 12)

    def test_parse_salary_invalid(self):
        engine = self._make_engine()
        result = engine._parse_salary("面议")
        assert result is None

    def test_get_recommendation(self):
        engine = self._make_engine()
        assert "强烈推荐" in engine._get_recommendation("A")
        assert "值得投入" in engine._get_recommendation("B")
        assert "不推荐" in engine._get_recommendation("F")
