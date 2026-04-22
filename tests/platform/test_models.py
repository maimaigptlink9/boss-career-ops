import pytest

from boss_career_ops.platform.models import Job, ChatMessage, Contact, AuthStatus, OperationResult


class TestJobToDict:
    def test_roundtrip(self, sample_job):
        d = sample_job.to_dict()
        assert d["job_id"] == "abc123"
        assert d["job_name"] == "高级Python开发"
        assert d["salary_min"] == 20000
        assert d["salary_max"] == 40000
        assert d["salary_months"] == 16
        assert d["skills"] == ["Python", "Go", "Docker"]
        assert "raw_data" not in d


class TestJobNormalize:
    def test_from_job_instance(self, sample_job):
        result = Job.normalize(sample_job)
        assert result is sample_job

    def test_from_boss_dict(self, sample_job_dict):
        result = Job.normalize(sample_job_dict)
        assert isinstance(result, Job)
        assert result.job_id == "abc123"
        assert result.job_name == "高级Python开发"
        assert result.salary_min == 20000

    def test_from_internal_dict(self):
        data = {
            "job_id": "xyz",
            "job_name": "测试岗位",
            "company_name": "测试公司",
            "salary_min": 10000,
            "salary_max": 20000,
        }
        result = Job.normalize(data)
        assert isinstance(result, Job)
        assert result.job_id == "xyz"
        assert result.job_name == "测试岗位"
        assert result.raw_data == data

    def test_from_dict_without_boss_keys(self):
        data = {"job_id": "x", "job_name": "y"}
        result = Job.normalize(data)
        assert result.job_id == "x"
        assert result.job_name == "y"

    def test_invalid_type_raises(self):
        with pytest.raises(TypeError, match="不支持的职位数据类型"):
            Job.normalize(42)

    def test_invalid_type_none_raises(self):
        with pytest.raises(TypeError):
            Job.normalize(None)

    def test_internal_dict_ignores_unknown_keys(self):
        data = {"job_id": "x", "unknown_field": "should_be_ignored"}
        result = Job.normalize(data)
        assert result.job_id == "x"
        assert not hasattr(result, "unknown_field")

    def test_boss_dict_takes_priority(self, sample_job_dict):
        data = {**sample_job_dict, "job_id": "should_be_overridden"}
        result = Job.normalize(data)
        assert result.job_id == "abc123"


class TestJobDefaults:
    def test_default_values(self):
        job = Job()
        assert job.job_id == ""
        assert job.salary_min is None
        assert job.salary_months == 12
        assert job.skills == []
        assert job.raw_data == {}


class TestChatMessage:
    def test_defaults(self):
        msg = ChatMessage()
        assert msg.security_id == ""
        assert msg.content == ""
        assert msg.raw_data == {}


class TestContact:
    def test_defaults(self):
        c = Contact()
        assert c.name == ""
        assert c.last_message == ""


class TestAuthStatus:
    def test_defaults(self):
        s = AuthStatus()
        assert s.ok is False
        assert s.missing == []
        assert s.message == ""


class TestOperationResult:
    def test_defaults(self):
        r = OperationResult()
        assert r.ok is False
        assert r.message == ""
        assert r.code == ""
        assert r.data == {}
