from boss_career_ops.evaluator.report import generate_report


class TestGenerateReport:
    def test_basic_report_structure(self):
        evaluation = {
            "job_name": "Golang工程师",
            "company_name": "测试公司",
            "salary_desc": "20-40K",
            "total_score": 4.2,
            "grade": "B",
            "grade_label": "值得投入，优先处理",
            "recommendation": "值得投入，建议优先处理",
            "scores": {"匹配度": 4.0, "薪资": 4.5, "地点": 3.5, "发展": 4.0, "团队": 4.0},
        }
        report = generate_report(evaluation)
        assert "职位评估报告" in report
        assert "Golang工程师" in report
        assert "测试公司" in report
        assert "20-40K" in report
        assert "4.2" in report
        assert "B" in report

    def test_report_contains_all_dimensions(self):
        evaluation = {
            "job_name": "",
            "company_name": "",
            "salary_desc": "",
            "total_score": 3.0,
            "grade": "C",
            "grade_label": "一般",
            "recommendation": "一般",
            "scores": {"匹配度": 3.0, "薪资": 3.0, "地点": 3.0, "发展": 3.0, "团队": 3.0},
        }
        report = generate_report(evaluation)
        assert "匹配度" in report
        assert "薪资" in report
        assert "地点" in report
        assert "发展" in report
        assert "团队" in report

    def test_report_empty_evaluation(self):
        evaluation = {}
        report = generate_report(evaluation)
        assert "职位评估报告" in report
