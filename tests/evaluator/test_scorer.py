from boss_career_ops.evaluator.scorer import (
    calculate_weighted_score,
    score_to_grade,
    grade_label,
    get_recommendation,
    GRADE_RANGES,
)


class TestCalculateWeightedScore:
    def test_perfect_scores(self, perfect_scores):
        result = calculate_weighted_score(perfect_scores)
        assert result == 5.0

    def test_zero_scores(self, zero_scores):
        result = calculate_weighted_score(zero_scores)
        assert result == 0.0

    def test_partial_scores(self):
        scores = {"匹配度": 4.0, "薪资": 3.0, "地点": 2.0, "发展": 1.0, "团队": 0.0}
        result = calculate_weighted_score(scores)
        expected = 4.0 * 0.30 + 3.0 * 0.25 + 2.0 * 0.15 + 1.0 * 0.15 + 0.0 * 0.15
        assert result == round(expected, 2)

    def test_missing_dimensions_default_to_zero(self):
        scores = {"匹配度": 5.0}
        result = calculate_weighted_score(scores)
        expected = 5.0 * 0.30
        assert result == round(expected, 2)

    def test_score_capped_at_5(self):
        scores = {"匹配度": 10.0, "薪资": 10.0, "地点": 10.0, "发展": 10.0, "团队": 10.0}
        result = calculate_weighted_score(scores)
        assert result == 5.0

    def test_score_floored_at_0(self):
        scores = {"匹配度": -1.0, "薪资": -2.0, "地点": 0.0, "发展": 0.0, "团队": 0.0}
        result = calculate_weighted_score(scores)
        assert result == 0.0

    def test_result_has_two_decimal_places(self):
        scores = {"匹配度": 3.0, "薪资": 3.0, "地点": 3.0, "发展": 3.0, "团队": 3.0}
        result = calculate_weighted_score(scores)
        assert result == 3.0
        assert isinstance(result, float)


class TestScoreToGrade:
    def test_grade_a_lower_bound(self):
        assert score_to_grade(4.5) == "A"

    def test_grade_a_upper_bound(self):
        assert score_to_grade(5.0) == "A"

    def test_grade_b_lower_bound(self):
        assert score_to_grade(3.5) == "B"

    def test_grade_b_upper_bound(self):
        assert score_to_grade(4.4) == "B"

    def test_grade_c_mid(self):
        assert score_to_grade(3.0) == "C"

    def test_grade_d_mid(self):
        assert score_to_grade(2.0) == "D"

    def test_grade_f(self):
        assert score_to_grade(0.0) == "F"

    def test_grade_f_upper(self):
        assert score_to_grade(1.4) == "F"

    def test_all_grade_ranges_covered(self):
        for grade, (low, high) in GRADE_RANGES.items():
            assert score_to_grade(low) == grade
            assert score_to_grade(high) == grade


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
    def test_returns_same_as_grade_label(self):
        for grade in ["A", "B", "C", "D", "F"]:
            assert get_recommendation(grade) == grade_label(grade)

    def test_unknown_grade(self):
        assert get_recommendation("Z") == "未知等级"
