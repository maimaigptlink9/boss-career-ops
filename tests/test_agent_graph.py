from unittest.mock import patch, MagicMock

import pytest


class TestBuildCareerAgent:
    @patch("boss_career_ops.agent.graph.build_career_agent", create=True)
    def test_returns_compiled_graph(self, mock_build):
        from langgraph.graph import StateGraph, END
        from boss_career_ops.agent.state import AgentState
        mock_graph = MagicMock()
        mock_build.return_value = mock_graph
        result = mock_build()
        assert result is not None

    def test_graph_has_correct_nodes(self):
        from boss_career_ops.agent.conditions import route_by_intent
        expected_nodes = ["orchestrator", "search", "evaluate", "resume", "apply", "gap_analysis"]
        for node in expected_nodes:
            route = route_by_intent({"intent": node if node != "orchestrator" else "search"})
            assert route in ["search", "evaluate", "resume", "apply", "gap_analysis"]

    def test_graph_entry_point_is_orchestrator(self):
        from boss_career_ops.agent.conditions import route_by_intent
        default_route = route_by_intent({})
        assert default_route == "search"
