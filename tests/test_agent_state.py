from boss_career_ops.agent.state import AgentState
from boss_career_ops.agent.conditions import route_by_intent


class TestAgentState:
    def test_create_state_with_required_fields(self):
        state = AgentState(
            messages=[],
            intent="search",
            job_ids=[],
            current_job_id="",
            job_details={},
            evaluation_results={},
            resume_versions={},
            skill_gaps={},
            rag_context="",
            errors=[],
            next_action="",
        )
        assert state["intent"] == "search"
        assert state["messages"] == []
        assert state["job_ids"] == []
        assert state["errors"] == []

    def test_state_with_messages(self):
        state = AgentState(
            messages=[{"role": "user", "content": "帮我搜索Python职位"}],
            intent="search",
            job_ids=["job1"],
            current_job_id="job1",
            job_details={"job1": {"job_name": "Python开发"}},
            evaluation_results={},
            resume_versions={},
            skill_gaps={},
            rag_context="",
            errors=[],
            next_action="evaluate",
        )
        assert len(state["messages"]) == 1
        assert state["job_ids"] == ["job1"]


class TestRouteByIntent:
    def test_search_intent(self):
        assert route_by_intent({"intent": "search"}) == "search"

    def test_evaluate_intent(self):
        assert route_by_intent({"intent": "evaluate"}) == "evaluate"

    def test_resume_intent(self):
        assert route_by_intent({"intent": "resume"}) == "resume"

    def test_apply_intent(self):
        assert route_by_intent({"intent": "apply"}) == "apply"

    def test_gap_analysis_intent(self):
        assert route_by_intent({"intent": "gap_analysis"}) == "gap_analysis"

    def test_resume_plus_apply_combination(self):
        assert route_by_intent({"intent": "resume+apply"}) == "resume"

    def test_unknown_intent_defaults_to_search(self):
        assert route_by_intent({"intent": "unknown"}) == "search"

    def test_empty_intent_defaults_to_search(self):
        assert route_by_intent({}) == "search"
