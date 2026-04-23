import pytest

from boss_career_ops.platform.models import Job
from boss_career_ops.config.singleton import SingletonMeta


@pytest.fixture
def tmp_dir(tmp_path):
    SingletonMeta._instances.clear()
    return tmp_path


@pytest.fixture
def sample_job_dict():
    return {
        "encryptJobId": "abc123",
        "securityId": "sec456",
        "jobName": "高级Python开发",
        "brandName": "测试科技",
        "salaryDesc": "20K-40K·16薪",
        "cityName": "深圳",
        "jobExperience": "3-5年",
        "jobDegree": "本科",
        "skills": "Python,Go,Docker",
        "jobLabels": ["五险一金", "弹性工作"],
        "postDescription": "负责后端开发",
        "brandStageName": "B轮",
        "brandScaleName": "100-499人",
        "brandIndustry": "互联网",
    }


@pytest.fixture
def sample_job():
    return Job(
        job_id="abc123",
        security_id="sec456",
        job_name="高级Python开发",
        company_name="测试科技",
        salary_desc="20K-40K·16薪",
        salary_min=20000,
        salary_max=40000,
        salary_months=16,
        city_name="深圳",
        experience="3-5年",
        education="本科",
        skills=["Python", "Go", "Docker"],
        job_labels=["五险一金", "弹性工作"],
        description="负责后端开发",
        brand_stage="B轮",
        brand_scale="100-499人",
        brand_industry="互联网",
    )


@pytest.fixture
def perfect_scores():
    return {
        "匹配度": 5.0,
        "薪资": 5.0,
        "地点": 5.0,
        "发展": 5.0,
        "团队": 5.0,
    }


@pytest.fixture
def zero_scores():
    return {
        "匹配度": 0.0,
        "薪资": 0.0,
        "地点": 0.0,
        "发展": 0.0,
        "团队": 0.0,
    }
