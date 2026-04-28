from unittest.mock import patch, MagicMock

import yaml

from boss_career_ops.evaluator.engine import (
    EDUCATION_LEVELS,
    NEARBY_CITIES,
    _skill_matches_jd,
    _SYNONYMS_FILE,
    _CUSTOM_SYNONYMS_FILE,
)
from boss_career_ops.platform.field_mapper import parse_salary
from boss_career_ops.evaluator.scorer import get_recommendation
from boss_career_ops.config.settings import Profile, SalaryExpectation
from boss_career_ops.platform.models import Job


class TestEvaluationEngine:
    def test_evaluate_returns_required_keys(self, make_engine):
        engine = make_engine()
        job = {"jobName": "测试", "brandName": "公司", "salaryDesc": "10-20K"}
        result = engine.evaluate(job)
        assert "scores" in result
        assert "total_score" in result
        assert "grade" in result
        assert "grade_label" in result
        assert "recommendation" in result
        assert "job_name" in result
        assert "company_name" in result
        assert "match_reasons" in result
        assert "mismatch_reasons" in result
        assert "confidence" in result
        assert "confidence_note" in result

    def test_evaluate_total_score_range(self, make_engine):
        engine = make_engine()
        job = {"jobName": "测试"}
        result = engine.evaluate(job)
        assert 0.0 <= result["total_score"] <= 5.0

    def test_evaluate_grade_is_valid(self, make_engine):
        engine = make_engine()
        job = {"jobName": "测试"}
        result = engine.evaluate(job)
        assert result["grade"] in ("A", "B", "C", "D", "F")

    def test_score_match_with_skills(self, make_engine):
        profile = Profile(skills=["Go", "Docker"])
        engine = make_engine(profile=profile)
        job = Job(job_name="Golang", skills=["Go", "Docker", "Kubernetes"])
        score = engine._score_match(job)
        assert score > 1.0

    def test_score_match_no_skills(self, make_engine):
        engine = make_engine()
        job = Job(job_name="测试")
        score = engine._score_match(job)
        assert score == 1.0

    def test_score_salary_matching(self, make_engine):
        profile = Profile(expected_salary=SalaryExpectation(min=20000, max=40000))
        engine = make_engine(profile=profile)
        job = Job(salary_desc="20-40K", salary_min=20000, salary_max=40000, salary_months=12)
        score = engine._score_salary(job)
        assert score >= 4.0

    def test_score_salary_no_desc(self, make_engine):
        engine = make_engine()
        job = Job()
        score = engine._score_salary(job)
        assert score == 1.0

    def test_score_location_preferred_city(self, make_engine):
        profile = Profile(preferred_cities=["广州"])
        engine = make_engine(profile=profile)
        job = Job(city_name="广州")
        score = engine._score_location(job)
        assert score == 5.0

    def test_score_location_not_preferred(self, make_engine):
        profile = Profile(preferred_cities=["北京"])
        engine = make_engine(profile=profile)
        job = Job(city_name="广州")
        score = engine._score_location(job)
        assert score == 1.0

    def test_score_growth_with_keywords(self, make_engine):
        engine = make_engine()
        job = Job(description="晋升通道 培训体系", brand_stage="B轮")
        score = engine._score_growth(job)
        assert score > 1.5

    def test_score_team_with_scale(self, make_engine):
        engine = make_engine()
        job = Job(brand_scale="100-499人")
        score = engine._score_team(job)
        assert score > 1.5

    def test_parse_salary_k_format(self):
        result = parse_salary("20-40K")
        assert result == (20000, 40000, 12)

    def test_parse_salary_plain_numbers(self):
        result = parse_salary("15000-25000")
        assert result == (15000, 25000, 12)

    def test_parse_salary_invalid(self):
        result = parse_salary("面议")
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

    def test_evaluate_with_job_instance(self, make_engine):
        engine = make_engine()
        job = Job(job_name="测试", company_name="公司", salary_desc="10-20K", salary_min=10000, salary_max=20000)
        result = engine.evaluate(job)
        assert result["job_name"] == "测试"
        assert result["company_name"] == "公司"

    def test_score_salary_fallback_to_parse(self, make_engine):
        profile = Profile(expected_salary=SalaryExpectation(min=20000, max=40000))
        engine = make_engine(profile=profile)
        job = Job(salary_desc="20-40K", salary_min=None, salary_max=None)
        score = engine._score_salary(job)
        assert score >= 4.0


class TestDetectJobCategory:
    def test_tech_category(self, make_engine):
        engine = make_engine()
        assert engine._detect_job_category("后端开发工程师") == "技术"
        assert engine._detect_job_category("前端工程师") == "技术"
        assert engine._detect_job_category("架构师") == "技术"
        assert engine._detect_job_category("运维工程师") == "技术"
        assert engine._detect_job_category("测试开发") == "技术"
        assert engine._detect_job_category("算法工程师") == "技术"

    def test_product_category(self, make_engine):
        engine = make_engine()
        assert engine._detect_job_category("产品经理") == "产品"
        assert engine._detect_job_category("高级PM") == "产品"

    def test_ops_category(self, make_engine):
        engine = make_engine()
        assert engine._detect_job_category("用户运营") == "运营"
        assert engine._detect_job_category("增长运营") == "运营"

    def test_marketing_category(self, make_engine):
        engine = make_engine()
        assert engine._detect_job_category("市场营销") == "市场"
        assert engine._detect_job_category("品牌经理") == "市场"
        assert engine._detect_job_category("投放专员") == "市场"

    def test_design_category(self, make_engine):
        engine = make_engine()
        assert engine._detect_job_category("UI设计师") == "设计"
        assert engine._detect_job_category("UX设计师") == "设计"
        assert engine._detect_job_category("视觉设计师") == "设计"
        assert engine._detect_job_category("交互设计师") == "设计"

    def test_data_category(self, make_engine):
        engine = make_engine()
        assert engine._detect_job_category("数据分析师") == "数据"
        assert engine._detect_job_category("BI工程师") == "数据"

    def test_management_category(self, make_engine):
        engine = make_engine()
        assert engine._detect_job_category("技术经理") == "管理"
        assert engine._detect_job_category("运营总监") == "管理"
        assert engine._detect_job_category("部门主管") == "管理"
        assert engine._detect_job_category("团队负责人") == "管理"

    def test_general_category(self, make_engine):
        engine = make_engine()
        assert engine._detect_job_category("行政助理") == "通用"
        assert engine._detect_job_category("实习生") == "通用"


class TestNearbyCities:
    def test_nearby_city_scores_3_5(self, make_engine):
        profile = Profile(preferred_cities=["广州"])
        engine = make_engine(profile=profile)
        job = Job(city_name="深圳")
        score = engine._score_location(job)
        assert score == 3.5

    def test_nearby_city_shanghai_to_hangzhou(self, make_engine):
        profile = Profile(preferred_cities=["上海"])
        engine = make_engine(profile=profile)
        job = Job(city_name="杭州")
        score = engine._score_location(job)
        assert score == 3.5

    def test_non_nearby_city_scores_1_0(self, make_engine):
        profile = Profile(preferred_cities=["北京"])
        engine = make_engine(profile=profile)
        job = Job(city_name="成都")
        score = engine._score_location(job)
        assert score == 1.0

    def test_remote_ok_with_remote_label(self, make_engine):
        profile = Profile(preferred_cities=["北京"], remote_ok=True)
        engine = make_engine(profile=profile)
        job = Job(city_name="成都", job_labels=["远程办公"])
        score = engine._score_location(job)
        assert score == 3.5

    def test_nearby_cities_dict_structure(self):
        assert "广州" in NEARBY_CITIES
        assert "深圳" in NEARBY_CITIES["广州"]
        assert "北京" in NEARBY_CITIES
        assert "上海" in NEARBY_CITIES


class TestSalaryContinuousScoring:
    def test_salary_exceeds_expectation(self, make_engine):
        profile = Profile(expected_salary=SalaryExpectation(min=20000, max=30000))
        engine = make_engine(profile=profile)
        job = Job(salary_min=30000, salary_max=40000, salary_months=12)
        score = engine._score_salary(job)
        assert score == 5.0

    def test_salary_min_meets_expectation(self, make_engine):
        profile = Profile(expected_salary=SalaryExpectation(min=20000, max=40000))
        engine = make_engine(profile=profile)
        job = Job(salary_min=20000, salary_max=30000, salary_months=12)
        score = engine._score_salary(job)
        assert 3.5 <= score <= 5.0

    def test_salary_max_in_range(self, make_engine):
        profile = Profile(expected_salary=SalaryExpectation(min=20000, max=40000))
        engine = make_engine(profile=profile)
        job = Job(salary_min=15000, salary_max=25000, salary_months=12)
        score = engine._score_salary(job)
        assert 2.0 <= score <= 3.5

    def test_salary_below_expectation(self, make_engine):
        profile = Profile(expected_salary=SalaryExpectation(min=20000, max=40000))
        engine = make_engine(profile=profile)
        job = Job(salary_min=8000, salary_max=12000, salary_months=12)
        score = engine._score_salary(job)
        assert score < 2.0

    def test_salary_no_expectation_returns_1(self, make_engine):
        profile = Profile(expected_salary=SalaryExpectation(min=0, max=0))
        engine = make_engine(profile=profile)
        job = Job(salary_min=20000, salary_max=40000, salary_months=12)
        score = engine._score_salary(job)
        assert score == 1.0


class TestAvoidPatternExactMatch:
    def test_avoid_outsourcing_exact_match(self, make_engine):
        profile = Profile(avoid="外包")
        engine = make_engine(profile=profile)
        job = Job(brand_industry="外包")
        score = engine._score_team(job)
        assert score < 1.5

    def test_it_in_industry_not_matched_by_avoid(self, make_engine):
        profile = Profile(avoid="IT")
        engine = make_engine(profile=profile)
        job = Job(brand_industry="互联网/IT服务")
        score = engine._score_team(job)
        assert score < 1.5

    def test_non_pattern_avoid_matches_substring(self, make_engine):
        profile = Profile(avoid="金融")
        engine = make_engine(profile=profile)
        job = Job(brand_industry="金融/投资")
        score = engine._score_team(job)
        assert score < 1.5

    def test_no_avoid_no_penalty(self, make_engine):
        profile = Profile(avoid="")
        engine = make_engine(profile=profile)
        job = Job(brand_industry="外包服务")
        score = engine._score_team(job)
        assert score >= 1.5


class TestMatchMismatchReasons:
    def test_matched_skills_in_reasons(self, make_engine):
        profile = Profile(skills=["Python"])
        engine = make_engine(profile=profile)
        job = Job(job_name="Python工程师", skills=["Python"], description="需要Python开发经验")
        result = engine.evaluate(job)
        assert any("技能匹配" in r for r in result["match_reasons"])

    def test_missing_skills_in_reasons(self, make_engine):
        profile = Profile(skills=["Rust"])
        engine = make_engine(profile=profile)
        job = Job(job_name="Java工程师", description="需要Java开发经验")
        result = engine.evaluate(job)
        assert any("技能缺失" in r for r in result["mismatch_reasons"])

    def test_salary_above_expectation_in_reasons(self, make_engine):
        profile = Profile(
            skills=["Python"],
            expected_salary=SalaryExpectation(min=15000, max=25000),
        )
        engine = make_engine(profile=profile)
        job = Job(job_name="Python工程师", salary_min=25000, salary_max=35000, salary_months=12)
        result = engine.evaluate(job)
        assert any("薪资超预期" in r for r in result["match_reasons"])

    def test_salary_below_expectation_in_reasons(self, make_engine):
        profile = Profile(
            skills=["Python"],
            expected_salary=SalaryExpectation(min=30000, max=50000),
        )
        engine = make_engine(profile=profile)
        job = Job(job_name="Python工程师", salary_min=10000, salary_max=15000, salary_months=12)
        result = engine.evaluate(job)
        assert any("薪资低于期望" in r for r in result["mismatch_reasons"])

    def test_preferred_city_in_reasons(self, make_engine):
        profile = Profile(
            skills=["Python"],
            preferred_cities=["北京"],
        )
        engine = make_engine(profile=profile)
        job = Job(job_name="Python工程师", city_name="北京")
        result = engine.evaluate(job)
        assert any("目标城市" in r for r in result["match_reasons"])

    def test_non_preferred_city_in_reasons(self, make_engine):
        profile = Profile(
            skills=["Python"],
            preferred_cities=["北京"],
        )
        engine = make_engine(profile=profile)
        job = Job(job_name="Python工程师", city_name="成都")
        result = engine.evaluate(job)
        assert any("非目标城市" in r for r in result["mismatch_reasons"])


class TestConfidenceOutput:
    def test_confidence_full_with_description(self, make_engine):
        engine = make_engine()
        job = Job(job_name="测试", description="负责开发工作")
        result = engine.evaluate(job)
        assert result["confidence"] == "full"
        assert result["confidence_note"] == ""

    def test_confidence_preliminary_without_description(self, make_engine):
        engine = make_engine()
        job = Job(job_name="测试")
        result = engine.evaluate(job)
        assert result["confidence"] == "preliminary"
        assert "初步评估" in result["confidence_note"]

    def test_confidence_preliminary_with_empty_description(self, make_engine):
        engine = make_engine()
        job = Job(job_name="测试", description="  ")
        result = engine.evaluate(job)
        assert result["confidence"] == "preliminary"


class TestEducationLevelMapping:
    def test_education_levels_dict_values(self):
        assert EDUCATION_LEVELS["初中"] == 1
        assert EDUCATION_LEVELS["中专"] == 2
        assert EDUCATION_LEVELS["高中"] == 2
        assert EDUCATION_LEVELS["大专"] == 3
        assert EDUCATION_LEVELS["专科"] == 3
        assert EDUCATION_LEVELS["本科"] == 4
        assert EDUCATION_LEVELS["硕士"] == 5
        assert EDUCATION_LEVELS["博士"] == 6

    def test_master_above_bachelor_adds_score(self, make_engine):
        profile = Profile(skills=["Python"], education="硕士")
        engine = make_engine(profile=profile)
        job = Job(job_name="工程师", education="本科及以上", description="需要本科及以上学历")
        score = engine._score_match(job)
        profile2 = Profile(skills=["Python"], education="")
        engine2 = make_engine(profile=profile2)
        score2 = engine2._score_match(job)
        assert score > score2

    def test_bachelor_below_master_no_bonus(self, make_engine):
        profile = Profile(skills=["Python"], education="本科")
        engine = make_engine(profile=profile)
        job = Job(job_name="工程师", education="硕士", description="硕士及以上学历")
        score_with_edu = engine._score_match(job)
        profile2 = Profile(skills=["Python"], education="")
        engine2 = make_engine(profile=profile2)
        score_without_edu = engine2._score_match(job)
        assert score_with_edu == score_without_edu

    def test_no_education_requirement_adds_score(self, make_engine):
        profile = Profile(skills=["Python"], education="硕士")
        engine = make_engine(profile=profile)
        job = Job(job_name="工程师", description="负责开发工作")
        score_with_edu = engine._score_match(job)
        profile2 = Profile(skills=["Python"], education="")
        engine2 = make_engine(profile=profile2)
        score_without_edu = engine2._score_match(job)
        assert score_with_edu > score_without_edu


class TestProfileEmptyHints:
    def test_skills_empty_hint(self, make_engine):
        engine = make_engine(profile=Profile(), cv_content="")
        result = engine.evaluate({"jobName": "测试"})
        assert "hints" in result
        assert any("profile.skills" in h for h in result["hints"])

    def test_expected_salary_zero_hint(self, make_engine):
        engine = make_engine(
            profile=Profile(
                skills=["Python"],
                expected_salary=SalaryExpectation(min=0, max=0),
                preferred_cities=["北京"],
            )
        )
        result = engine.evaluate({"jobName": "测试"})
        assert "hints" in result
        assert any("expected_salary" in h for h in result["hints"])

    def test_preferred_cities_empty_hint(self, make_engine):
        engine = make_engine(
            profile=Profile(
                skills=["Python"],
                expected_salary=SalaryExpectation(min=20000, max=40000),
                preferred_cities=[],
            )
        )
        result = engine.evaluate({"jobName": "测试"})
        assert "hints" in result
        assert any("preferred_cities" in h for h in result["hints"])

    def test_no_hints_when_profile_complete(self, make_engine):
        engine = make_engine(
            profile=Profile(
                skills=["Python"],
                expected_salary=SalaryExpectation(min=20000, max=40000),
                preferred_cities=["北京"],
            )
        )
        result = engine.evaluate({"jobName": "测试"})
        assert "hints" not in result


class TestSalaryPrecedenceFix:
    def test_job_min_none_with_salary_desc_enters_parse(self, make_engine):
        profile = Profile(
            skills=["Python"],
            expected_salary=SalaryExpectation(min=15000, max=25000),
        )
        engine = make_engine(profile=profile)
        job = Job(salary_desc="20-40K", salary_min=None, salary_max=40000)
        result = engine.evaluate(job)
        assert any("薪资" in r for r in result["match_reasons"] + result["mismatch_reasons"])

    def test_job_min_none_empty_desc_not_enters_parse(self, make_engine):
        profile = Profile(
            skills=["Python"],
            expected_salary=SalaryExpectation(min=15000, max=25000),
        )
        engine = make_engine(profile=profile)
        job = Job(salary_desc="", salary_min=None, salary_max=None)
        result = engine.evaluate(job)
        assert not any("薪资" in r for r in result["match_reasons"] + result["mismatch_reasons"])

    def test_job_max_none_with_salary_desc_enters_parse(self, make_engine):
        profile = Profile(
            skills=["Python"],
            expected_salary=SalaryExpectation(min=15000, max=25000),
        )
        engine = make_engine(profile=profile)
        job = Job(salary_desc="20-40K", salary_min=20000, salary_max=None)
        result = engine.evaluate(job)
        assert any("薪资" in r for r in result["match_reasons"] + result["mismatch_reasons"])

    def test_both_none_with_salary_desc_enters_parse(self, make_engine):
        profile = Profile(
            skills=["Python"],
            expected_salary=SalaryExpectation(min=15000, max=25000),
        )
        engine = make_engine(profile=profile)
        job = Job(salary_desc="20-40K", salary_min=None, salary_max=None)
        result = engine.evaluate(job)
        assert any("薪资" in r for r in result["match_reasons"] + result["mismatch_reasons"])

    def test_both_present_ignores_salary_desc(self, make_engine):
        profile = Profile(
            skills=["Python"],
            expected_salary=SalaryExpectation(min=30000, max=50000),
        )
        engine = make_engine(profile=profile)
        job = Job(salary_desc="20-40K", salary_min=8000, salary_max=12000, salary_months=12)
        result = engine.evaluate(job)
        assert any("薪资低于期望" in r for r in result["mismatch_reasons"])


class TestSkillSynonymsYamlLoading:
    def test_synonyms_loaded_from_yaml(self, make_engine):
        engine = make_engine()
        assert isinstance(engine._synonyms, dict)
        assert "go" in engine._synonyms
        assert "golang" in engine._synonyms["go"]
        assert "java" in engine._synonyms
        assert "jvm" in engine._synonyms["java"]

    def test_synonyms_file_exists(self):
        assert _SYNONYMS_FILE.exists(), f"YAML 文件不存在: {_SYNONYMS_FILE}"

    def test_yaml_is_valid(self):
        with open(_SYNONYMS_FILE, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert isinstance(data, dict)
        assert len(data) > 0

    def test_fallback_when_yaml_missing(self, tmp_path, make_engine):
        from boss_career_ops.evaluator import engine as engine_mod
        original = engine_mod._SYNONYMS_FILE
        engine_mod._SYNONYMS_FILE = tmp_path / "nonexistent.yml"
        try:
            engine = make_engine()
            assert isinstance(engine._synonyms, dict)
        finally:
            engine_mod._SYNONYMS_FILE = original

    def test_custom_synonyms_merged(self, tmp_path, make_engine):
        from boss_career_ops.evaluator import engine as engine_mod
        original = engine_mod._CUSTOM_SYNONYMS_FILE
        custom_file = tmp_path / "skill_synonyms.yml"
        custom_file.write_text("go:\n  - gogo\ncustom_skill:\n  - cs1\n", encoding="utf-8")
        engine_mod._CUSTOM_SYNONYMS_FILE = custom_file
        try:
            engine = make_engine()
            assert "gogo" in engine._synonyms["go"]
            assert "golang" in engine._synonyms["go"]
            assert "custom_skill" in engine._synonyms
            assert "cs1" in engine._synonyms["custom_skill"]
        finally:
            engine_mod._CUSTOM_SYNONYMS_FILE = original

    def test_custom_synonyms_corrupt_file_ignored(self, tmp_path, make_engine):
        from boss_career_ops.evaluator import engine as engine_mod
        original = engine_mod._CUSTOM_SYNONYMS_FILE
        custom_file = tmp_path / "skill_synonyms.yml"
        custom_file.write_text("::invalid[yaml", encoding="utf-8")
        engine_mod._CUSTOM_SYNONYMS_FILE = custom_file
        try:
            engine = make_engine()
            assert "go" in engine._synonyms
        finally:
            engine_mod._CUSTOM_SYNONYMS_FILE = original


class TestSkillMatchesJdWithSynonyms:
    def test_direct_match(self):
        assert _skill_matches_jd("python", "need python developer", {"python": ["py"]}) is True

    def test_synonym_match(self):
        assert _skill_matches_jd("py", "need python developer", {"py": ["python"]}) is True

    def test_no_match(self):
        assert _skill_matches_jd("rust", "need python developer", {"rust": ["rust语言"]}) is False

    def test_case_insensitive(self):
        assert _skill_matches_jd("go", "need Golang developer", {"go": ["golang"]}) is True

    def test_no_synonyms_dict(self):
        assert _skill_matches_jd("python", "need python developer", None) is True

    def test_chinese_synonym(self):
        assert _skill_matches_jd("k8s", "need Kubernetes experience", {"k8s": ["kubernetes"]}) is True

    def test_synonym_matching_in_evaluate(self, make_engine):
        profile = Profile(skills=["go"])
        engine = make_engine(profile=profile)
        job = Job(job_name="Golang", skills=["Go", "Docker", "Kubernetes"])
        result = engine.evaluate(job)
        assert any("技能匹配" in r for r in result["match_reasons"])
