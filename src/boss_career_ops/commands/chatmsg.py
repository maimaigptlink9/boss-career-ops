from boss_career_ops.boss.api.client import BossClient
from boss_career_ops.ai.provider import get_provider
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)


def run_chatmsg(security_id: str):
    client = BossClient()
    try:
        resp = client.get("chat_messages", params={"securityId": security_id})
        if resp.get("code") != 0:
            output_error(command="chatmsg", message="获取消息失败", code="CHATMSG_ERROR")
            return
        messages = resp.get("zpData", {}).get("list", [])
        output_json(
            command="chatmsg",
            data=messages,
            hints={"next_actions": ["bco chat-summary <security_id>"]},
        )
    except Exception as e:
        output_error(command="chatmsg", message=str(e), code="CHATMSG_ERROR")


def run_chat_summary(security_id: str):
    client = BossClient()
    try:
        resp = client.get("chat_messages", params={"securityId": security_id})
        if resp.get("code") != 0:
            output_error(command="chat-summary", message="获取消息失败", code="CHATMSG_ERROR")
            return
        messages = resp.get("zpData", {}).get("list", [])
        summary = _summarize_with_ai(messages)
        output_json(
            command="chat-summary",
            data=summary,
            hints={"next_actions": ["bco follow-up", "bco pipeline"]},
        )
    except Exception as e:
        output_error(command="chat-summary", message=str(e), code="CHATMSG_ERROR")


def _summarize_with_ai(messages: list) -> dict:
    if not messages:
        return {"total": 0, "summary": "无消息"}
    total = len(messages)
    last_msg = messages[-1] if messages else {}
    provider = get_provider()
    if provider is None:
        return {
            "total": total,
            "last_message": last_msg.get("content", ""),
            "last_time": last_msg.get("time", ""),
            "summary": f"共 {total} 条消息",
            "source": "rule",
        }
    try:
        msg_texts = []
        for m in messages[-20:]:
            role = m.get("senderName", "")
            content = m.get("content", "")
            time_str = m.get("time", "")
            msg_texts.append(f"[{time_str}] {role}: {content}")
        conversation = "\n".join(msg_texts)
        system_prompt = (
            "你是 BOSS 直聘求职助手。请用中文总结以下聊天记录，输出 JSON 格式："
            '{"summary":"一句话总结","key_points":["要点1","要点2"],'
            '"sentiment":"positive/neutral/negative","next_step":"建议下一步动作"}'
        )
        result = provider.chat(system_prompt, f"以下是与 HR 的聊天记录:\n{conversation}")
        import json as _json
        ai_data = _json.loads(result) if isinstance(result, str) else {"summary": str(result)}
        return {
            "total": total,
            "last_message": last_msg.get("content", ""),
            "last_time": last_msg.get("time", ""),
            **ai_data,
            "source": "ai",
        }
    except Exception as e:
        logger.warning("AI 摘要生成失败，回退到规则模板: %s", e)
        return {
            "total": total,
            "last_message": last_msg.get("content", ""),
            "last_time": last_msg.get("time", ""),
            "summary": f"共 {total} 条消息",
            "source": "rule_fallback",
        }
