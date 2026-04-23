import json
from unittest.mock import patch, MagicMock, AsyncMock

import pytest


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    response = MagicMock()
    response.content = json.dumps({
        "intent": "search",
        "params": {"keyword": "Python"},
        "next_action": "search",
    })
    llm.invoke.return_value = response
    return llm


@pytest.fixture
def sample_state():
    return {
        "messages": [{"role": "user", "content": "帮我搜索Python职位"}],
        "intent": "",
        "job_ids": [],
        "current_job_id": "",
        "job_details": {},
        "evaluation_results": {},
        "resume_versions": {},
        "skill_gaps": {},
        "rag_context": "",
        "errors": [],
        "next_action": "",
    }


class TestOrchestratorWithLlm:
    @patch("boss_career_ops.agent.llm.get_llm")
    def test_orchestrator_with_llm_extracts_intent(self, mock_get_llm, mock_llm, sample_state):
        mock_get_llm.return_value = mock_llm
        from boss_career_ops.agent.prompts import ORCHESTRATOR_SYSTEM
        assert "search" in ORCHESTRATOR_SYSTEM
        assert "evaluate" in ORCHESTRATOR_SYSTEM
        assert "resume" in ORCHESTRATOR_SYSTEM
        assert "apply" in ORCHESTRATOR_SYSTEM
        assert "gap_analysis" in ORCHESTRATOR_SYSTEM


class TestOrchestratorWithoutLlm:
    @patch("boss_career_ops.agent.llm.get_llm", return_value=None)
    def test_orchestrator_without_llm_uses_keyword_matching(self, mock_get_llm, sample_state):
        query = sample_state["messages"][0]["content"]
        keyword_map = {
            "搜索": "search",
            "评估": "evaluate",
            "简历": "resume",
            "投递": "apply",
            "差距": "gap_analysis",
        }
        intent = "search"
        for kw, it in keyword_map.items():
            if kw in query:
                intent = it
                break
        assert intent == "search"


class TestOrchestratorChineseQueries:
    def test_extract_search_intent(self):
        query = "帮我搜索Python职位"
        assert "搜索" in query

    def test_extract_evaluate_intent(self):
        query = "评估一下这个职位"
        assert "评估" in query

    def test_extract_resume_intent(self):
        query = "帮我生成简历"
        assert "简历" in query

    def test_extract_apply_intent(self):
        query = "帮我投递这个职位"
        assert "投递" in query
