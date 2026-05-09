import pytest

from boss_career_ops.platform.field_mapper import BossFieldMapper


def _make_raw_data(**overrides):
    base = {
        "encryptJobId": "abc123",
        "jobName": "Python开发",
        "brandName": "测试公司",
        "cityName": "北京",
        "jobExperience": "3-5年",
        "jobDegree": "本科",
        "salaryDesc": "15-25K·14薪",
    }
    base.update(overrides)
    return base


def test_jobdetail_takes_priority_over_postdescription():
    raw = _make_raw_data(jobDetail="详细JD内容", postDescription="简短描述")
    mapper = BossFieldMapper()
    job = mapper.map_job(raw)
    assert job.description == "详细JD内容"


def test_postdescription_used_when_jobdetail_empty():
    raw = _make_raw_data(jobDetail="", postDescription="简短描述")
    mapper = BossFieldMapper()
    job = mapper.map_job(raw)
    assert job.description == "简短描述"


def test_postdescription_used_when_jobdetail_absent():
    raw = _make_raw_data(postDescription="简短描述")
    mapper = BossFieldMapper()
    job = mapper.map_job(raw)
    assert job.description == "简短描述"


def test_description_empty_when_both_empty():
    raw = _make_raw_data(jobDetail="", postDescription="")
    mapper = BossFieldMapper()
    job = mapper.map_job(raw)
    assert job.description == ""
