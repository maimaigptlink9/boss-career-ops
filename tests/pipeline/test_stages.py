from boss_career_ops.pipeline.stages import Stage, STAGE_ORDER, next_stage


class TestStageEnum:
    def test_all_stages_present(self):
        assert Stage.DISCOVERED == "发现"
        assert Stage.EVALUATED == "评估"
        assert Stage.APPLIED == "投递"
        assert Stage.COMMUNICATING == "沟通"
        assert Stage.INTERVIEW == "面试"
        assert Stage.OFFER == "offer"

    def test_stage_order_length(self):
        assert len(STAGE_ORDER) == 6

    def test_stage_order_matches_enum(self):
        expected = [
            Stage.DISCOVERED,
            Stage.EVALUATED,
            Stage.APPLIED,
            Stage.COMMUNICATING,
            Stage.INTERVIEW,
            Stage.OFFER,
        ]
        assert STAGE_ORDER == expected


class TestNextStage:
    def test_discovered_to_evaluated(self):
        assert next_stage(Stage.DISCOVERED) == Stage.EVALUATED

    def test_evaluated_to_applied(self):
        assert next_stage(Stage.EVALUATED) == Stage.APPLIED

    def test_applied_to_communicating(self):
        assert next_stage(Stage.APPLIED) == Stage.COMMUNICATING

    def test_communicating_to_interview(self):
        assert next_stage(Stage.COMMUNICATING) == Stage.INTERVIEW

    def test_interview_to_offer(self):
        assert next_stage(Stage.INTERVIEW) == Stage.OFFER

    def test_offer_is_last(self):
        assert next_stage(Stage.OFFER) is None

    def test_full_pipeline(self):
        stage = Stage.DISCOVERED
        visited = [stage]
        while True:
            stage = next_stage(stage)
            if stage is None:
                break
            visited.append(stage)
        assert visited == list(STAGE_ORDER)
