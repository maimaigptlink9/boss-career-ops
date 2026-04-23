import sys
from unittest.mock import patch, MagicMock

import pytest


@pytest.fixture(autouse=True)
def mock_console_and_graph():
    mock_console = MagicMock()
    mock_graph_module = MagicMock()
    with patch.dict("sys.modules", {
        "boss_career_ops.agent.graph": mock_graph_module,
    }):
        with patch("boss_career_ops.display.output.console", mock_console, create=True):
            with patch("boss_career_ops.commands.agent_cmd.console", mock_console):
                yield mock_console, mock_graph_module


class TestRunAgentWithQuery:
    def test_run_agent_with_query(self, mock_console_and_graph):
        mock_console, mock_graph_module = mock_console_and_graph
        mock_graph = MagicMock()
        mock_graph.ainvoke = MagicMock(return_value={
            "messages": [],
            "intent": "search",
            "job_ids": ["job1"],
            "current_job_id": "",
            "job_details": {},
            "evaluation_results": {},
            "resume_versions": {},
            "skill_gaps": {},
            "rag_context": "",
            "errors": [],
            "next_action": "",
        })
        mock_graph_module.build_career_agent.return_value = mock_graph
        from boss_career_ops.commands.agent_cmd import run_agent
        with patch("boss_career_ops.commands.agent_cmd.asyncio") as mock_asyncio:
            mock_asyncio.run.return_value = mock_graph.ainvoke.return_value
            run_agent("搜索Python职位")


class TestRunAgentWithoutQuery:
    def test_run_agent_without_query_shows_error(self, mock_console_and_graph):
        mock_console, mock_graph_module = mock_console_and_graph
        mock_graph_module.build_career_agent.return_value = MagicMock()
        from boss_career_ops.commands.agent_cmd import run_agent
        run_agent("")
        mock_console.print.assert_called()
