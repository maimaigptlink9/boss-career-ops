from boss_career_ops.evaluator.scorer import calculate_weighted_score, score_to_grade, grade_label, get_recommendation, GRADE_RANGES, GRADE_LABELS


class TestCalculateWeightedScore:
    def test_all_max_scores(self):
        scores = {"匹配度": 5.0, "薪资": 5.0, "地点": 5.0, "发展": 5.0, "团队": 5.0}
        result = calculate_weighted_score(scores)
        assert result == 5.0

    def test_all_min_scores(self):
        scores = {"匹配度": 0.0, "薪资": 0.0, "地点": 0.0, "发展": 0.0, "团队": 0.0}
        result = calculate_weighted_score(scores)
        assert result == 0.0

    def test_mixed_scores(self):
        scores = {"匹配度": 4.0, "薪资": 3.0, "地点": 5.0, "发展": 2.0, "团队": 3.0}
        result = calculate_weighted_score(scores)
        expected = 4.0 * 0.30 + 3.0 * 0.25 + 5.0 * 0.15 + 2.0 * 0.15 + 3.0 * 0.15
        assert abs(result - round(expected, 2)) < 0.01

    def test_missing_dimension_defaults_zero(self):
        scores = {"匹配度": 5.0}
        result = calculate_weighted_score(scores)
        assert result < 5.0

    def test_score_clamped_to_max(self):
        scores = {"匹配度": 10.0, "薪资": 10.0, "地点": 10.0, "发展": 10.0, "团队": 10.0}
        result = calculate_weighted_score(scores)
        assert result == 5.0


class TestScoreToGrade:
    def test_grade_a(self):
        assert score_to_grade(4.5) == "A"
        assert score_to_grade(5.0) == "A"
        assert score_to_grade(4.8) == "A"

    def test_grade_b(self):
        assert score_to_grade(3.5) == "B"
        assert score_to_grade(4.4) == "B"

    def test_grade_c(self):
        assert score_to_grade(2.5) == "C"
        assert score_to_grade(3.4) == "C"

    def test_grade_d(self):
        assert score_to_grade(1.5) == "D"
        assert score_to_grade(2.4) == "D"

    def test_grade_f(self):
        assert score_to_grade(0.0) == "F"
        assert score_to_grade(1.4) == "F"

    def test_unknown_returns_f(self):
        assert score_to_grade(-1.0) == "F"


class TestGradeLabel:
    def test_known_grades(self):
        assert grade_label("A") == "强烈推荐，立即行动"
        assert grade_label("B") == "值得投入，优先处理"
        assert grade_label("C") == "一般，需人工判断"
        assert grade_label("D") == "不太匹配，谨慎考虑"
        assert grade_label("F") == "不推荐"

    def test_unknown_grade(self):
        assert grade_label("X") == "未知"


class TestGetRecommendation:
    def test_known_grades(self):
        assert "强烈推荐" in get_recommendation("A")
        assert "值得投入" in get_recommendation("B")
        assert "不推荐" in get_recommendation("F")

    def test_unknown_grade(self):
        assert get_recommendation("X") == "未知等级"


class TestGradeLabelDelegatesToGetRecommendation:
    def test_known_grades_match(self):
        for grade in ("A", "B", "C", "D", "F"):
            assert grade_label(grade) == get_recommendation(grade)

    def test_unknown_grade_differs(self):
        assert grade_label("X") == "未知"
        assert get_recommendation("X") == "未知等级"
