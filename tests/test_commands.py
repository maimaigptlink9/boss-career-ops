from unittest.mock import patch, MagicMock

from boss_career_ops.commands.export import _sanitize_path, _sanitize_csv_value
from boss_career_ops.commands.chatmsg import _summarize_with_ai
from boss_career_ops.commands.interview import _generate_tech_questions, _extract_company_info, _extract_jd_text
from boss_career_ops.commands.negotiate import _generate_negotiation
from boss_career_ops.config.settings import Settings, Profile, SalaryExpectation


class TestSanitizePath:
    def test_relative_path_ok(self):
        from pathlib import Path
        p = _sanitize_path("output.csv")
        assert p == Path("output.csv")

    def test_absolute_path_raises(self):
        try:
            _sanitize_path("C:\\Users\\test.csv")
            assert False, "应抛出 ValueError"
        except ValueError as e:
            assert "不安全" in str(e)

    def test_path_traversal_raises(self):
        try:
            _sanitize_path("../etc/passwd")
            assert False, "应抛出 ValueError"
        except ValueError:
            pass


class TestSanitizeCsvValue:
    def test_formula_injection_prevention(self):
        assert _sanitize_csv_value("=SUM(A1:A10)").startswith("'")
        assert _sanitize_csv_value("+cmd").startswith("'")
        assert _sanitize_csv_value("-1").startswith("'")
        assert _sanitize_csv_value("@sum").startswith("'")

    def test_safe_value_passthrough(self):
        assert _sanitize_csv_value("正常文本") == "正常文本"
        assert _sanitize_csv_value("Golang工程师") == "Golang工程师"


class TestSummarize:
    def test_empty_messages(self):
        result = _summarize_with_ai([])
        assert result["total"] == 0
        assert "无消息" in result["summary"]

    def test_with_messages(self):
        messages = [
            {"content": "你好", "time": "10:00"},
            {"content": "面试时间", "time": "11:00"},
        ]
        result = _summarize_with_ai(messages)
        assert result["total"] == 2
        assert result["last_message"] == "面试时间"


class TestGenerateTechQuestions:
    def test_python_questions(self):
        questions = _generate_tech_questions("需要 Python 开发经验")
        assert len(questions) > 0
        assert any("Python" in q or "GIL" in q for q in questions)

    def test_go_questions(self):
        questions = _generate_tech_questions("Go 语言后端开发")
        assert len(questions) > 0

    def test_no_match_defaults(self):
        questions = _generate_tech_questions("一些非技术描述")
        assert len(questions) > 0

    def test_max_six_questions(self):
        questions = _generate_tech_questions("Python Go Java Docker Kubernetes Redis MySQL")
        assert len(questions) <= 6


class TestExtractCompanyInfo:
    def test_extract(self):
        job = {
            "brandName": "测试公司",
            "brandIndustry": "互联网",
            "brandScaleName": "100-499人",
            "brandStageName": "B轮",
        }
        info = _extract_company_info(job)
        assert info["name"] == "测试公司"
        assert info["industry"] == "互联网"

    def test_empty_job(self):
        info = _extract_company_info({})
        assert info["name"] == ""


class TestGenerateNegotiation:
    def _make_settings(self, profile=None):
        with patch.object(Settings, '__init__', lambda self, *a, **kw: None):
            settings = Settings()
            settings.profile = profile or Profile()
            settings.cv_content = ""
            return settings

    def test_with_expected_salary(self):
        profile = Profile(expected_salary=SalaryExpectation(min=25000, max=40000))
        settings = self._make_settings(profile)
        job = {"jobName": "Golang", "brandName": "公司", "salaryDesc": "20-40K"}
        result = _generate_negotiation(job, settings)
        assert "strategies" in result
        assert len(result["strategies"]) > 0
        assert "scripts" in result

    def test_without_expected_salary(self):
        settings = self._make_settings()
        job = {"jobName": "Golang", "brandName": "公司", "salaryDesc": "20-40K"}
        result = _generate_negotiation(job, settings)
        assert "strategies" in result
        assert "报价" in result["strategies"][0]
