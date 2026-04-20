from boss_career_ops.pipeline.stages import Stage, STAGE_ORDER, next_stage, can_transition


class TestStage:
    def test_stage_values(self):
        assert Stage.DISCOVERED.value == "发现"
        assert Stage.EVALUATED.value == "评估"
        assert Stage.APPLIED.value == "投递"
        assert Stage.COMMUNICATING.value == "沟通"
        assert Stage.INTERVIEW.value == "面试"
        assert Stage.OFFER.value == "offer"

    def test_stage_order(self):
        assert STAGE_ORDER == [
            Stage.DISCOVERED,
            Stage.EVALUATED,
            Stage.APPLIED,
            Stage.COMMUNICATING,
            Stage.INTERVIEW,
            Stage.OFFER,
        ]


class TestNextStage:
    def test_discovered_to_evaluated(self):
        assert next_stage(Stage.DISCOVERED) == Stage.EVALUATED

    def test_evaluated_to_applied(self):
        assert next_stage(Stage.EVALUATED) == Stage.APPLIED

    def test_offer_returns_none(self):
        assert next_stage(Stage.OFFER) is None

    def test_full_chain(self):
        current = Stage.DISCOVERED
        stages = [current]
        while True:
            nxt = next_stage(current)
            if nxt is None:
                break
            stages.append(nxt)
            current = nxt
        assert len(stages) == 6


class TestCanTransition:
    def test_same_stage(self):
        assert can_transition(Stage.DISCOVERED, Stage.DISCOVERED) is True

    def test_valid_forward(self):
        assert can_transition(Stage.DISCOVERED, Stage.EVALUATED) is True
        assert can_transition(Stage.EVALUATED, Stage.APPLIED) is True

    def test_skip_stage(self):
        assert can_transition(Stage.DISCOVERED, Stage.APPLIED) is False

    def test_backward(self):
        assert can_transition(Stage.EVALUATED, Stage.DISCOVERED) is False
