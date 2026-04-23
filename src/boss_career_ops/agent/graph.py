from langgraph.graph import StateGraph, END

from boss_career_ops.agent.state import AgentState
from boss_career_ops.agent.conditions import route_by_intent
from boss_career_ops.agent.nodes import orchestrator, search, evaluate, resume, apply, gap_analysis


def build_career_agent():
    graph = StateGraph(AgentState)

    graph.add_node("orchestrator", orchestrator.run)
    graph.add_node("search", search.run)
    graph.add_node("evaluate", evaluate.run)
    graph.add_node("resume", resume.run)
    graph.add_node("apply", apply.run)
    graph.add_node("gap_analysis", gap_analysis.run)

    graph.set_entry_point("orchestrator")

    graph.add_conditional_edges("orchestrator", route_by_intent)

    graph.add_edge("search", END)
    graph.add_edge("evaluate", END)
    graph.add_edge("resume", END)
    graph.add_edge("apply", END)
    graph.add_edge("gap_analysis", END)

    return graph.compile()
