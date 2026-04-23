from boss_career_ops.boss.search_filters import (
    CITY_MAP,
    EDUCATION_MAP,
    EXPERIENCE_MAP,
    FINANCE_MAP,
    JOB_TYPE_MAP,
    SALARY_MAP,
    SCALE_MAP,
    build_search_params,
    get_city_code,
)


class TestExperienceMap:
    def test_values(self):
        assert EXPERIENCE_MAP == {
            "在校/应届": "108",
            "1年以内": "101",
            "1-3年": "102",
            "3-5年": "103",
            "5-10年": "104",
            "10年以上": "105",
        }


class TestEducationMap:
    def test_values(self):
        assert EDUCATION_MAP == {
            "初中及以下": "209",
            "中专/中技": "208",
            "高中": "206",
            "大专": "202",
            "本科": "203",
            "硕士": "204",
            "博士": "205",
        }


class TestJobTypeMap:
    def test_values(self):
        assert JOB_TYPE_MAP == {
            "全职": "1901",
            "实习": "1902",
            "兼职": "1903",
        }


class TestScaleMap:
    def test_values(self):
        assert SCALE_MAP == {
            "0-20人": "301",
            "20-99人": "302",
            "100-499人": "303",
            "500-999人": "304",
            "1000-9999人": "305",
            "10000人以上": "306",
        }


class TestFinanceMap:
    def test_values(self):
        assert FINANCE_MAP == {
            "未融资": "801",
            "天使轮": "802",
            "A轮": "803",
            "B轮": "804",
            "C轮": "805",
            "D轮及以上": "806",
            "已上市": "807",
            "不需要融资": "808",
        }


class TestSalaryMap:
    def test_values(self):
        assert SALARY_MAP == {
            "3K以下": "401",
            "3-5K": "402",
            "5-10K": "403",
            "10-15K": "404",
            "15-20K": "405",
            "20-30K": "406",
            "30-50K": "407",
            "50K以上": "408",
        }


class TestCityMap:
    def test_original_cities(self):
        assert CITY_MAP["北京"] == "101010100"
        assert CITY_MAP["上海"] == "101020100"
        assert CITY_MAP["深圳"] == "101280600"

    def test_new_cities(self):
        assert CITY_MAP["全国"] == "100010000"
        assert CITY_MAP["宁波"] == "101210400"
        assert CITY_MAP["昆明"] == "101290100"
        assert CITY_MAP["厦门"] == "101230200"
        assert CITY_MAP["珠海"] == "101280700"
        assert CITY_MAP["无锡"] == "101190200"
        assert CITY_MAP["福州"] == "101230100"
        assert CITY_MAP["济南"] == "101120100"
        assert CITY_MAP["哈尔滨"] == "101050100"
        assert CITY_MAP["长春"] == "101060100"
        assert CITY_MAP["南昌"] == "101240100"
        assert CITY_MAP["贵阳"] == "101260100"
        assert CITY_MAP["南宁"] == "101300100"
        assert CITY_MAP["石家庄"] == "101090100"
        assert CITY_MAP["太原"] == "101100100"
        assert CITY_MAP["兰州"] == "101160100"
        assert CITY_MAP["海口"] == "101310100"
        assert CITY_MAP["常州"] == "101191100"
        assert CITY_MAP["温州"] == "101210700"
        assert CITY_MAP["嘉兴"] == "101210300"
        assert CITY_MAP["徐州"] == "101190800"
        assert CITY_MAP["香港"] == "101320100"

    def test_city_count(self):
        assert len(CITY_MAP) == 42


class TestGetCityCode:
    def test_existing_city(self):
        assert get_city_code("北京") == "101010100"

    def test_new_city(self):
        assert get_city_code("香港") == "101320100"
        assert get_city_code("全国") == "100010000"

    def test_unknown_city(self):
        assert get_city_code("不存在的城市") == ""


class TestBuildSearchParams:
    def test_salary_param(self):
        params = build_search_params("Python", salary="20-30K")
        assert params["salary"] == "406"

    def test_salary_empty(self):
        params = build_search_params("Python")
        assert "salary" not in params

    def test_salary_invalid(self):
        params = build_search_params("Python", salary="无效值")
        assert "salary" not in params

    def test_all_filters(self):
        params = build_search_params(
            "Java",
            city="上海",
            experience="3-5年",
            education="本科",
            job_type="全职",
            scale="100-499人",
            finance="A轮",
            salary="15-20K",
        )
        assert params["query"] == "Java"
        assert params["city"] == "101020100"
        assert params["experience"] == "103"
        assert params["education"] == "203"
        assert params["jobType"] == "1901"
        assert params["scale"] == "303"
        assert params["financeStage"] == "803"
        assert params["salary"] == "405"

    def test_keyword_only(self):
        params = build_search_params("Go")
        assert params == {"query": "Go", "page": 1, "pageSize": 15}
