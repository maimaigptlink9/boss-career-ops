from boss_career_ops.evaluator.utils import extract_jd_text
from boss_career_ops.platform.models import Job


class TestExtractJdText:
    def test_from_job_object(self):
        job = Job(
            job_name="Python开发",
            skills=["Python", "Docker"],
            description="负责后端开发",
            experience="3-5年",
            education="本科",
            job_labels=["远程"],
        )
        text = extract_jd_text(job)
        assert "Python开发" in text
        assert "Python" in text
        assert "Docker" in text
        assert "3-5年" in text
        assert "本科" in text
        assert "远程" in text
        assert "负责后端开发" in text

    def test_from_dict_with_snake_case(self):
        job_dict = {
            "job_name": "Go工程师",
            "skills": ["Go", "Kubernetes"],
            "description": "微服务开发",
        }
        text = extract_jd_text(job_dict)
        assert "Go工程师" in text
        assert "Go" in text
        assert "微服务开发" in text

    def test_from_dict_with_boss_keys(self):
        job_dict = {
            "jobName": "前端开发",
            "brandName": "测试公司",
            "salaryDesc": "15-25K",
            "skills": "React,TypeScript",
        }
        text = extract_jd_text(job_dict)
        assert "前端开发" in text

    def test_empty_job(self):
        job = Job()
        text = extract_jd_text(job)
        assert text == ""

    def test_job_with_no_description(self):
        job = Job(job_name="测试岗位", skills=["Python"])
        text = extract_jd_text(job)
        assert "测试岗位" in text
        assert "Python" in text
