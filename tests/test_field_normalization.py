from boss_career_ops.platform.field_mapper import (
    normalize_experience,
    normalize_education,
    normalize_brand_scale,
    BossFieldMapper,
)
from boss_career_ops.platform.models import Job


class TestNormalizeExperience:
    def test_range(self):
        assert normalize_experience("3-5年") == (3, 5)

    def test_unlimited(self):
        assert normalize_experience("不限") == (0, 0)

    def test_fresh_grad(self):
        assert normalize_experience("应届") == (0, 0)

    def test_empty(self):
        assert normalize_experience("") is None

    def test_single_year(self):
        assert normalize_experience("5年") == (5, 5)


class TestNormalizeEducation:
    def test_bachelor(self):
        assert normalize_education("本科") == 5

    def test_master(self):
        assert normalize_education("硕士") == 6

    def test_unlimited(self):
        assert normalize_education("学历不限") == 0

    def test_empty(self):
        assert normalize_education("") is None

    def test_doctor(self):
        assert normalize_education("博士") == 7

    def test_college(self):
        assert normalize_education("大专") == 4


class TestNormalizeBrandScale:
    def test_range(self):
        assert normalize_brand_scale("1000-9999人") == (1000, 9999)

    def test_empty(self):
        assert normalize_brand_scale("") is None

    def test_above(self):
        assert normalize_brand_scale("10000人以上") == (10000, 99999)


class TestJobModelFields:
    def test_new_fields_exist(self):
        job = Job(
            experience_range=(3, 5),
            education_level=5,
            brand_scale_range=(1000, 9999),
        )
        assert job.experience_range == (3, 5)
        assert job.education_level == 5
        assert job.brand_scale_range == (1000, 9999)

    def test_new_fields_default_none(self):
        job = Job()
        assert job.experience_range is None
        assert job.education_level is None
        assert job.brand_scale_range is None

    def test_to_dict_includes_new_fields(self):
        job = Job(
            experience_range=(3, 5),
            education_level=5,
            brand_scale_range=(1000, 9999),
        )
        d = job.to_dict()
        assert d["experience_range"] == (3, 5)
        assert d["education_level"] == 5
        assert d["brand_scale_range"] == (1000, 9999)


class TestBossFieldMapperNormalization:
    def test_map_job_populates_normalized_fields(self):
        mapper = BossFieldMapper()
        raw = {
            "encryptJobId": "abc123",
            "securityId": "sec1",
            "jobName": "后端工程师",
            "brandName": "测试公司",
            "salaryDesc": "15-25K",
            "cityName": "北京",
            "jobExperience": "3-5年",
            "jobDegree": "本科",
            "skills": "Python,Go",
            "postDescription": "岗位描述",
            "brandStageName": "A轮",
            "brandScaleName": "1000-9999人",
            "brandIndustry": "互联网",
        }
        job = mapper.map_job(raw)
        assert job.experience_range == (3, 5)
        assert job.education_level == 5
        assert job.brand_scale_range == (1000, 9999)

    def test_map_job_empty_fields(self):
        mapper = BossFieldMapper()
        raw = {
            "encryptJobId": "abc123",
            "jobExperience": "",
            "jobDegree": "",
            "brandScaleName": "",
        }
        job = mapper.map_job(raw)
        assert job.experience_range is None
        assert job.education_level is None
        assert job.brand_scale_range is None
