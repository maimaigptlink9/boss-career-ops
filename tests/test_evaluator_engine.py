from unittest.mock import patch, MagicMock

from boss_career_ops.evaluator.engine import EvaluationEngine, EDUCATION_LEVELS
from boss_career_ops.platform.field_mapper import _parse_salary
from boss_career_ops.evaluator.scorer import get_recommendation
from boss_career_ops.config.settings import Settings, Profile, SalaryExpectation
from boss_career_ops.platform.models import Job


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
        job = Job(job_name="Golang", skills=["Go", "Docker", "Kubernetes"])
        score = engine._score_match(job)
        assert score > 1.0

    def test_score_match_no_skills(self):
        engine = self._make_engine()
        job = Job(job_name="测试")
        score = engine._score_match(job)
        assert score == 2.5

    def test_score_salary_matching(self):
        profile = Profile(expected_salary=SalaryExpectation(min=20000, max=40000))
        engine = self._make_engine(profile=profile)
        job = Job(salary_desc="20-40K", salary_min=20000, salary_max=40000, salary_months=12)
        score = engine._score_salary(job)
        assert score >= 4.0

    def test_score_salary_no_desc(self):
        engine = self._make_engine()
        job = Job()
        score = engine._score_salary(job)
        assert score == 2.5

    def test_score_location_preferred_city(self):
        profile = Profile(preferred_cities=["广州"])
        engine = self._make_engine(profile=profile)
        job = Job(city_name="广州")
        score = engine._score_location(job)
        assert score == 4.5

    def test_score_location_not_preferred(self):
        profile = Profile(preferred_cities=["北京"])
        engine = self._make_engine(profile=profile)
        job = Job(city_name="广州")
        score = engine._score_location(job)
        assert score == 2.0

    def test_score_growth_with_keywords(self):
        engine = self._make_engine()
        job = Job(description="晋升通道 培训体系", brand_stage="B轮")
        score = engine._score_growth(job)
        assert score > 3.0

    def test_score_team_with_scale(self):
        engine = self._make_engine()
        job = Job(brand_scale="100-499人")
        score = engine._score_team(job)
        assert score > 3.0

    def test_parse_salary_k_format(self):
        result = _parse_salary("20-40K")
        assert result == (20000, 40000, 12)

    def test_parse_salary_plain_numbers(self):
        result = _parse_salary("15000-25000")
        assert result == (15000, 25000, 12)

    def test_parse_salary_invalid(self):
        result = _parse_salary("面议")
        assert result is None

    def test_get_recommendation(self):
        assert "强烈推荐" in get_recommendation("A")
        assert "值得投入" in get_recommendation("B")
        assert "不推荐" in get_recommendation("F")

    def test_normalize_job_dict(self):
        raw = {"jobName": "Go工程师", "brandName": "测试公司", "salaryDesc": "20-40K"}
        job = Job.normalize(raw)
        assert isinstance(job, Job)
        assert job.job_name == "Go工程师"
        assert job.company_name == "测试公司"
        assert job.salary_desc == "20-40K"

    def test_normalize_job_instance(self):
        job = Job(job_name="Go工程师", company_name="测试公司")
        result = Job.normalize(job)
        assert result is job

    def test_evaluate_with_job_instance(self):
        engine = self._make_engine()
        job = Job(job_name="测试", company_name="公司", salary_desc="10-20K", salary_min=10000, salary_max=20000)
        result = engine.evaluate(job)
        assert result["job_name"] == "测试"
        assert result["company_name"] == "公司"

    def test_score_salary_fallback_to_parse(self):
        profile = Profile(expected_salary=SalaryExpectation(min=20000, max=40000))
        engine = self._make_engine(profile=profile)
        job = Job(salary_desc="20-40K", salary_min=None, salary_max=None)
        score = engine._score_salary(job)
        assert score >= 4.0


class TestEducationLevelMapping:
    def _make_engine(self, profile=None):
        with patch.object(Settings, "__init__", lambda self, *a, **kw: None):
            settings = Settings()
            settings.profile = profile or Profile()
            settings.cv_content = ""
            engine = EvaluationEngine()
            engine._settings = settings
            return engine

    def test_education_levels_dict_values(self):
        assert EDUCATION_LEVELS["初中"] == 1
        assert EDUCATION_LEVELS["中专"] == 2
        assert EDUCATION_LEVELS["高中"] == 2
        assert EDUCATION_LEVELS["大专"] == 3
        assert EDUCATION_LEVELS["专科"] == 3
        assert EDUCATION_LEVELS["本科"] == 4
        assert EDUCATION_LEVELS["硕士"] == 5
        assert EDUCATION_LEVELS["博士"] == 6

    def test_master_above_bachelor_adds_score(self):
        profile = Profile(skills=["Python"], education="硕士")
        engine = self._make_engine(profile=profile)
        job = Job(job_name="工程师", education="本科及以上", description="需要本科及以上学历")
        score = engine._score_match(job)
        profile2 = Profile(skills=["Python"], education="")
        engine2 = self._make_engine(profile=profile2)
        score2 = engine2._score_match(job)
        assert score > score2

    def test_bachelor_below_master_no_bonus(self):
        profile = Profile(skills=["Python"], education="本科")
        engine = self._make_engine(profile=profile)
        job = Job(job_name="工程师", education="硕士", description="硕士及以上学历")
        score_with_edu = engine._score_match(job)
        profile2 = Profile(skills=["Python"], education="")
        engine2 = self._make_engine(profile=profile2)
        score_without_edu = engine2._score_match(job)
        assert score_with_edu == score_without_edu

    def test_no_education_requirement_adds_score(self):
        profile = Profile(skills=["Python"], education="硕士")
        engine = self._make_engine(profile=profile)
        job = Job(job_name="工程师", description="负责开发工作")
        score_with_edu = engine._score_match(job)
        profile2 = Profile(skills=["Python"], education="")
        engine2 = self._make_engine(profile=profile2)
        score_without_edu = engine2._score_match(job)
        assert score_with_edu > score_without_edu


class TestProfileEmptyHints:
    def _make_engine(self, profile=None, cv_content=""):
        with patch.object(Settings, "__init__", lambda self, *a, **kw: None):
            settings = Settings()
            settings.profile = profile or Profile()
            settings.cv_content = cv_content
            engine = EvaluationEngine()
            engine._settings = settings
            return engine

    def test_skills_empty_hint(self):
        engine = self._make_engine(profile=Profile(), cv_content="")
        result = engine.evaluate({"jobName": "测试"})
        assert "hints" in result
        assert any("profile.skills" in h for h in result["hints"])

    def test_expected_salary_zero_hint(self):
        engine = self._make_engine(
            profile=Profile(
                skills=["Python"],
                expected_salary=SalaryExpectation(min=0, max=0),
                preferred_cities=["北京"],
            )
        )
        result = engine.evaluate({"jobName": "测试"})
        assert "hints" in result
        assert any("expected_salary" in h for h in result["hints"])

    def test_preferred_cities_empty_hint(self):
        engine = self._make_engine(
            profile=Profile(
                skills=["Python"],
                expected_salary=SalaryExpectation(min=20000, max=40000),
                preferred_cities=[],
            )
        )
        result = engine.evaluate({"jobName": "测试"})
        assert "hints" in result
        assert any("preferred_cities" in h for h in result["hints"])

    def test_no_hints_when_profile_complete(self):
        engine = self._make_engine(
            profile=Profile(
                skills=["Python"],
                expected_salary=SalaryExpectation(min=20000, max=40000),
                preferred_cities=["北京"],
            )
        )
        result = engine.evaluate({"jobName": "测试"})
        assert "hints" not in result
