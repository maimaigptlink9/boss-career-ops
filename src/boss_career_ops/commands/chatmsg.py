from boss_career_ops.platform.registry import get_active_adapter
from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger
import json

logger = get_logger(__name__)


def run_chatmsg(security_id: str):
    adapter = get_active_adapter()
    try:
        messages = adapter.get_chat_messages(security_id)
        if not messages:
            output_error(command="chatmsg", message="获取消息失败", code="CHATMSG_ERROR")
            return
        output_json(
            command="chatmsg",
            data=[{"sender_name": m.sender_name, "content": m.content, "time": m.time} for m in messages],
            hints={"next_actions": ["bco chat-summary <security_id>"]},
        )
    except Exception as e:
        output_error(command="chatmsg", message=str(e), code="CHATMSG_ERROR")


def run_chat_summary(security_id: str):
    # 先检查 Agent 生成的摘要
    try:
        with PipelineManager() as pm:
            ai_result = pm.get_ai_result(security_id, "chat_summary")
            if ai_result:
                ai_data = json.loads(ai_result["result"])
                output_json(
                    command="chat-summary",
                    data={**ai_data, "source": "agent"},
                    hints={"next_actions": ["bco follow-up", "bco pipeline"]},
                )
                return
    except Exception as e:
        logger.warning("读取 Agent 聊天摘要失败: %s", e)
    # 规则回退
    adapter = get_active_adapter()
    try:
        messages = adapter.get_chat_messages(security_id)
        if not messages:
            output_error(command="chat-summary", message="获取消息失败", code="CHATMSG_ERROR")
            return
        total = len(messages)
        last_msg = messages[-1] if messages else None
        summary = {
            "total": total,
            "last_message": last_msg.content if last_msg else "",
            "last_time": last_msg.time if last_msg else "",
            "summary": f"共 {total} 条消息",
            "source": "rule",
        }
        output_json(
            command="chat-summary",
            data=summary,
            hints={"next_actions": ["bco follow-up", "bco pipeline"]},
        )
    except Exception as e:
        output_error(command="chat-summary", message=str(e), code="CHATMSG_ERROR")
