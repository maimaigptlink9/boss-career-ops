from boss_career_ops.platform.registry import get_active_adapter
from boss_career_ops.display.output import output_json, output_error


def run_mark(security_id: str, tag: str):
    adapter = get_active_adapter()
    try:
        result = adapter.mark_contact(security_id, tag)
        if result.ok:
            output_json(
                command="mark",
                data={"security_id": security_id, "tag": tag},
                hints={"next_actions": ["bco chat", "bco pipeline"]},
            )
        else:
            output_error(command="mark", message=result.message or "标记失败", code="MARK_ERROR")
    except Exception as e:
        output_error(command="mark", message=str(e), code="MARK_ERROR")
