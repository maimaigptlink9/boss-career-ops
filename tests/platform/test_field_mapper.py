import pytest

from boss_career_ops.platform.field_mapper import normalize_skills, parse_salary, BossFieldMapper
from boss_career_ops.platform.models import Job, ChatMessage, Contact


class TestParseSalary:
    def test_k_range(self):
        assert parse_salary("20K-40K") == (20000, 40000, 12)

    def test_k_range_with_months(self):
        assert parse_salary("20K-40K·16薪") == (20000, 40000, 16)

    def test_lowercase_k(self):
        assert parse_salary("15k-25k") == (15000, 25000, 12)

    def test_no_k_unit(self):
        result = parse_salary("15000-25000")
        assert result == (15000, 25000, 12)

    def test_negotiable(self):
        assert parse_salary("面议") is None

    def test_negotiable_variant(self):
        assert parse_salary("薪资面议") is None

    def test_negotiable_english(self):
        assert parse_salary("negotiable") is None

    def test_empty_string(self):
        assert parse_salary("") is None

    def test_whitespace_only(self):
        assert parse_salary("   ") is None

    def test_13_salary(self):
        assert parse_salary("10K-20K·13薪") == (10000, 20000, 13)

    def test_tilde_separator(self):
        assert parse_salary("15K~30K") == (15000, 30000, 12)

    def test_em_dash_separator(self):
        assert parse_salary("15K—30K") == (15000, 30000, 12)

    def test_spaces_around_k(self):
        assert parse_salary("20 K - 40 K") == (20000, 40000, 12)


class TestNormalizeSkills:
    def test_string_input(self):
        assert normalize_skills("Python,Go,Docker") == ["Python", "Go", "Docker"]

    def test_string_with_spaces(self):
        assert normalize_skills("Python , Go , Docker") == ["Python", "Go", "Docker"]

    def test_string_empty(self):
        assert normalize_skills("") == []

    def test_list_input(self):
        assert normalize_skills(["Python", "Go", "Docker"]) == ["Python", "Go", "Docker"]

    def test_list_with_non_strings(self):
        assert normalize_skills(["Python", 42, "Go"]) == ["Python", "42", "Go"]

    def test_list_with_empty_items(self):
        assert normalize_skills(["Python", "", "Go", None]) == ["Python", "Go"]

    def test_none_input(self):
        assert normalize_skills(None) == []

    def test_list_with_whitespace(self):
        assert normalize_skills([" Python ", " Go "]) == ["Python", "Go"]

    def test_single_skill_string(self):
        assert normalize_skills("Python") == ["Python"]

    def test_string_with_trailing_comma(self):
        assert normalize_skills("Python,Go,") == ["Python", "Go"]


class TestBossFieldMapperMapJob:
    def test_basic_mapping(self, sample_job_dict):
        mapper = BossFieldMapper()
        job = mapper.map_job(sample_job_dict)
        assert isinstance(job, Job)
        assert job.job_id == "abc123"
        assert job.job_name == "高级Python开发"
        assert job.company_name == "测试科技"
        assert job.salary_min == 20000
        assert job.salary_max == 40000
        assert job.salary_months == 16
        assert job.city_name == "深圳"
        assert job.brand_stage == "B轮"

    def test_skills_from_string(self, sample_job_dict):
        mapper = BossFieldMapper()
        job = mapper.map_job(sample_job_dict)
        assert job.skills == ["Python", "Go", "Docker"]

    def test_skills_from_list(self):
        mapper = BossFieldMapper()
        data = {"skills": ["Python", "Go"], "salaryDesc": ""}
        job = mapper.map_job(data)
        assert job.skills == ["Python", "Go"]

    def test_skills_empty_string(self):
        mapper = BossFieldMapper()
        data = {"skills": "", "salaryDesc": ""}
        job = mapper.map_job(data)
        assert job.skills == []

    def test_job_labels_from_list(self, sample_job_dict):
        mapper = BossFieldMapper()
        job = mapper.map_job(sample_job_dict)
        assert job.job_labels == ["五险一金", "弹性工作"]

    def test_job_labels_from_string(self):
        mapper = BossFieldMapper()
        data = {"jobLabels": "五险一金，弹性工作", "salaryDesc": ""}
        job = mapper.map_job(data)
        assert job.job_labels == ["五险一金", "弹性工作"]

    def test_empty_salary(self):
        mapper = BossFieldMapper()
        data = {"salaryDesc": "面议"}
        job = mapper.map_job(data)
        assert job.salary_min is None
        assert job.salary_max is None
        assert job.salary_months == 12

    def test_missing_fields_default(self):
        mapper = BossFieldMapper()
        job = mapper.map_job({})
        assert job.job_id == ""
        assert job.job_name == ""
        assert job.salary_min is None

    def test_raw_data_preserved(self, sample_job_dict):
        mapper = BossFieldMapper()
        job = mapper.map_job(sample_job_dict)
        assert job.raw_data == sample_job_dict


class TestBossFieldMapperMapChatMessage:
    def test_basic_mapping(self):
        mapper = BossFieldMapper()
        data = {
            "securityId": "sec1",
            "senderName": "张三",
            "content": "你好",
            "time": "2024-01-01",
        }
        msg = mapper.map_chat_message(data)
        assert isinstance(msg, ChatMessage)
        assert msg.security_id == "sec1"
        assert msg.sender_name == "张三"
        assert msg.content == "你好"


class TestBossFieldMapperMapContact:
    def test_basic_mapping(self):
        mapper = BossFieldMapper()
        data = {
            "securityId": "sec1",
            "name": "李四",
            "lastContent": "期待面试",
            "time": "2024-01-01",
        }
        contact = mapper.map_contact(data)
        assert isinstance(contact, Contact)
        assert contact.security_id == "sec1"
        assert contact.name == "李四"
        assert contact.last_message == "期待面试"

    def test_gravity_group_new_fields(self):
        mapper = BossFieldMapper()
        data = {
            "groupId": "grp1",
            "groupName": "王五",
            "lastMsg": "欢迎入职",
            "lastMsgTime": "2024-06-01",
        }
        contact = mapper.map_contact(data)
        assert isinstance(contact, Contact)
        assert contact.security_id == "grp1"
        assert contact.name == "王五"
        assert contact.last_message == "欢迎入职"
        assert contact.time == "2024-06-01"

    def test_old_fields_take_priority(self):
        mapper = BossFieldMapper()
        data = {
            "securityId": "sec_old",
            "groupId": "grp_new",
            "name": "旧名",
            "groupName": "新名",
            "lastContent": "旧消息",
            "lastMsg": "新消息",
            "time": "2024-01-01",
            "lastMsgTime": "2024-06-01",
        }
        contact = mapper.map_contact(data)
        assert contact.security_id == "sec_old"
        assert contact.name == "旧名"
        assert contact.last_message == "旧消息"
        assert contact.time == "2024-01-01"
