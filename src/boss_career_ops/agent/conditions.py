_INTENT_ROUTE_MAP = {
    "search": "search",
    "evaluate": "evaluate",
    "resume": "resume",
    "apply": "apply",
    "gap_analysis": "gap_analysis",
    "resume+apply": "resume",
}


def route_by_intent(state: dict) -> str:
    intent = state.get("intent", "")
    return _INTENT_ROUTE_MAP.get(intent, "search")
