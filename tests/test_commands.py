from unittest.mock import patch, MagicMock

from boss_career_ops.commands.export import _sanitize_path, _sanitize_csv_value
from boss_career_ops.commands.interview import _extract_company_info, _extract_jd_text
from boss_career_ops.config.settings import Settings, Profile, SalaryExpectation
from boss_career_ops.platform.models import ChatMessage, Job


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


class TestExtractCompanyInfo:
    def test_extract(self):
        job = Job(
            company_name="测试公司",
            brand_industry="互联网",
            brand_scale="100-499人",
            brand_stage="B轮",
        )
        info = _extract_company_info(job)
        assert info["name"] == "测试公司"
        assert info["industry"] == "互联网"

    def test_empty_job(self):
        job = Job()
        info = _extract_company_info(job)
        assert info["name"] == ""


