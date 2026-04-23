from typing import Annotated, TypedDict

from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    intent: str
    job_ids: list[str]
    current_job_id: str
    job_details: dict[str, dict]
    evaluation_results: dict[str, dict]
    resume_versions: dict[str, str]
    skill_gaps: dict
    rag_context: str
    errors: list[str]
    next_action: str
