from boss_career_ops.evaluator.dimensions import Dimension, DimensionWeight, DIMENSION_WEIGHTS, get_weight


class TestDimension:
    def test_dimension_values(self):
        assert Dimension.MATCH.value == "匹配度"
        assert Dimension.SALARY.value == "薪资"
        assert Dimension.LOCATION.value == "地点"
        assert Dimension.GROWTH.value == "发展"
        assert Dimension.TEAM.value == "团队"

    def test_dimension_count(self):
        assert len(Dimension) == 5

    def test_dimension_weights_sum(self):
        total = sum(dw.weight for dw in DIMENSION_WEIGHTS)
        assert abs(total - 1.0) < 0.001

    def test_get_weight(self):
        assert get_weight(Dimension.MATCH) == 0.30
        assert get_weight(Dimension.SALARY) == 0.25
        assert get_weight(Dimension.LOCATION) == 0.15
        assert get_weight(Dimension.GROWTH) == 0.15
        assert get_weight(Dimension.TEAM) == 0.15

    def test_get_weight_returns_zero_for_unknown(self):
        result = get_weight("nonexistent")
        assert result == 0.0

    def test_dimension_weight_dataclass(self):
        dw = DimensionWeight(dimension=Dimension.MATCH, weight=0.30, description="test")
        assert dw.dimension == Dimension.MATCH
        assert dw.weight == 0.30
