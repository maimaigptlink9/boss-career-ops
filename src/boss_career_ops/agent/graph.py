from langgraph.graph import StateGraph, END

from boss_career_ops.agent.state import AgentState
from boss_career_ops.agent.conditions import route_by_intent
from boss_career_ops.agent.nodes import orchestrator, search, evaluate, resume, apply, gap_analysis

NODE_NAMES = ["search", "evaluate", "resume", "apply", "gap_analysis"]


def route_after_resume(state):
    if "apply" in state.get("intent", ""):
        return "apply"
    next_action = state.get("next_action")
    if next_action and next_action in NODE_NAMES:
        return next_action
    return END


def route_after_action(state):
    next_action = state.get("next_action")
    if next_action and next_action in NODE_NAMES:
        return next_action
    return END


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

    route_map = {**{n: n for n in NODE_NAMES}, END: END}

    graph.add_conditional_edges("resume", route_after_resume, route_map)
    for node_name in ["search", "evaluate", "apply", "gap_analysis"]:
        graph.add_conditional_edges(node_name, route_after_action, route_map)

    return graph.compile()
