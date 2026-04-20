from boss_career_ops.boss.search_filters import (
    get_city_code,
    build_search_params,
    filter_by_welfare,
    CITY_MAP,
    EXPERIENCE_MAP,
    EDUCATION_MAP,
)


class TestGetCityCode:
    def test_known_city(self):
        assert get_city_code("北京") == "101010100"
        assert get_city_code("上海") == "101020100"
        assert get_city_code("广州") == "101280100"

    def test_unknown_city(self):
        assert get_city_code("未知城市") == ""


class TestBuildSearchParams:
    def test_basic_search(self):
        params = build_search_params("Golang")
        assert params["query"] == "Golang"
        assert params["page"] == 1
        assert params["pageSize"] == 15

    def test_with_city(self):
        params = build_search_params("Golang", city="广州")
        assert params["city"] == "101280100"

    def test_with_experience(self):
        params = build_search_params("Golang", experience="3-5年")
        assert params["experience"] == "104"

    def test_with_education(self):
        params = build_search_params("Golang", education="本科")
        assert params["education"] == "205"

    def test_with_job_type(self):
        params = build_search_params("Golang", job_type="全职")
        assert params["jobType"] == "301"

    def test_with_scale(self):
        params = build_search_params("Golang", scale="100-499人")
        assert params["scale"] == "403"

    def test_with_finance(self):
        params = build_search_params("Golang", finance="B轮")
        assert params["financeStage"] == "504"

    def test_unknown_filters_ignored(self):
        params = build_search_params("Golang", experience="未知", education="未知")
        assert "experience" not in params
        assert "education" not in params

    def test_custom_page(self):
        params = build_search_params("Golang", page=3, page_size=30)
        assert params["page"] == 3
        assert params["pageSize"] == 30


class TestFilterByWelfare:
    def test_no_filter(self):
        jobs = [{"jobLabels": ["五险一金"]}]
        assert filter_by_welfare(jobs, "") == jobs

    def test_single_welfare(self):
        jobs = [
            {"jobLabels": ["五险一金", "双休"]},
            {"jobLabels": ["五险一金"]},
        ]
        result = filter_by_welfare(jobs, "双休")
        assert len(result) == 1
        assert "双休" in result[0]["jobLabels"]

    def test_multiple_welfare(self):
        jobs = [
            {"jobLabels": ["五险一金", "双休", "弹性工作"]},
            {"jobLabels": ["五险一金", "双休"]},
        ]
        result = filter_by_welfare(jobs, "双休,弹性工作")
        assert len(result) == 1

    def test_no_match(self):
        jobs = [{"jobLabels": ["五险一金"]}]
        result = filter_by_welfare(jobs, "远程办公")
        assert len(result) == 0

    def test_welfare_from_string_field(self):
        jobs = [{"welfare": "五险一金，双休，弹性工作"}]
        result = filter_by_welfare(jobs, "双休")
        assert len(result) == 1

    def test_empty_jobs(self):
        assert filter_by_welfare([], "双休") == []
