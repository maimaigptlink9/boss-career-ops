import json

from langchain_core.messages import SystemMessage, HumanMessage

from boss_career_ops.agent.llm import get_llm, is_llm_available
from boss_career_ops.agent.prompts import ORCHESTRATOR_SYSTEM, ORCHESTRATOR_USER, sanitize_input
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)

_KEYWORD_INTENT_MAP = {
    "搜索": "search",
    "找": "search",
    "搜": "search",
    "评估": "evaluate",
    "匹配": "evaluate",
    "评分": "evaluate",
    "简历": "resume",
    "改简历": "resume",
    "投递": "apply",
    "打招呼": "apply",
    "应聘": "apply",
    "技能差距": "gap_analysis",
    "技能分析": "gap_analysis",
}


def _keyword_intent(query: str) -> tuple[str, dict]:
    for keyword, intent in _KEYWORD_INTENT_MAP.items():
        if keyword in query:
            return intent, {}
    return "search", {}


async def run(state: dict) -> dict:
    messages = state.get("messages", [])
    if not messages:
        return {"intent": "search", "next_action": "search", "errors": ["无用户输入"]}

    last_msg = messages[-1]
    query = last_msg.content if hasattr(last_msg, "content") else str(last_msg)

    if not is_llm_available():
        intent, params = _keyword_intent(query)
        return {
            "intent": intent,
            "next_action": intent,
            "messages": [{"role": "system", "content": f"关键词路由: intent={intent}"}],
        }

    llm = get_llm()
    if llm is None:
        intent, params = _keyword_intent(query)
        return {
            "intent": intent,
            "next_action": intent,
            "messages": [{"role": "system", "content": f"LLM不可用,关键词路由: intent={intent}"}],
        }

    try:
        system_msg = SystemMessage(content=ORCHESTRATOR_SYSTEM)
        user_msg = HumanMessage(content=ORCHESTRATOR_USER.safe_substitute(query=sanitize_input(query)))
        response = await llm.ainvoke([system_msg, user_msg])
        content = response.content

        # 尝试从响应中提取 JSON
        json_str = content
        if "```json" in content:
            json_str = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            json_str = content.split("```")[1].split("```")[0].strip()

        parsed = json.loads(json_str)
        intent = parsed.get("intent", "search")
        params = parsed.get("params", {})
        next_action = parsed.get("next_action", intent)

        update = {
            "intent": intent,
            "next_action": next_action,
            "messages": [{"role": "system", "content": f"LLM路由: intent={intent}, next_action={next_action}"}],
        }

        if "job_ids" in params:
            update["job_ids"] = params["job_ids"]
        if "current_job_id" in params:
            update["current_job_id"] = params["current_job_id"]

        return update

    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.warning("LLM 响应解析失败,降级到关键词路由: %s", e)
        intent, params = _keyword_intent(query)
        return {
            "intent": intent,
            "next_action": intent,
            "messages": [{"role": "system", "content": f"解析失败,关键词路由: intent={intent}"}],
        }
    except Exception as e:
        logger.warning("LLM 调用异常,降级到关键词路由: %s", e)
        intent, params = _keyword_intent(query)
        return {
            "intent": intent,
            "next_action": intent,
            "messages": [{"role": "system", "content": f"LLM异常,关键词路由: intent={intent}"}],
        }
