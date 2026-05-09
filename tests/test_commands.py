from pathlib import Path

from boss_career_ops.commands.export import _sanitize_path, _sanitize_csv_value
from boss_career_ops.platform.models import Job


class TestSanitizePath:
    def test_relative_path_ok(self):
        result = _sanitize_path("output.csv")
        assert str(result) == "output.csv"

    def test_absolute_path_raises(self):
        import pytest
        with pytest.raises(ValueError):
            _sanitize_path("/etc/passwd")

    def test_path_traversal_raises(self):
        import pytest
        with pytest.raises(ValueError):
            _sanitize_path("../../etc/passwd")


class TestSanitizeCsvValue:
    def test_formula_injection_prevention(self):
        assert _sanitize_csv_value("=SUM(A1:A10)") == "'=SUM(A1:A10)"
        assert _sanitize_csv_value("+cmd") == "'+cmd"
        assert _sanitize_csv_value("-formula") == "'-formula"
        assert _sanitize_csv_value("@sum") == "'@sum"

    def test_safe_value_passthrough(self):
        assert _sanitize_csv_value("Python开发") == "Python开发"
        assert _sanitize_csv_value("15000") == "15000"


class TestJobModel:
    def test_job_fields(self):
        job = Job(
            job_id="123",
            job_name="Golang",
            company_name="测试公司",
            security_id="sec_123",
            brand_industry="互联网",
            brand_scale="500-999人",
            brand_stage="B轮",
        )
        assert job.company_name == "测试公司"
        assert job.brand_industry == "互联网"

    def test_empty_job(self):
        job = Job(job_id="", job_name="", company_name="", security_id="")
        assert job.company_name == ""
