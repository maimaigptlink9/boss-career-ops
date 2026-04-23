from boss_career_ops.platform.registry import get_active_adapter
from boss_career_ops.display.error_codes import ErrorCode
from boss_career_ops.display.output import output_json, output_error


def run_status():
    adapter = get_active_adapter()
    result = adapter.check_auth_status()
    if result.ok:
        output_json(
            command="status",
            data={"logged_in": True, "message": result.message},
            hints={"next_actions": ["bco search \"关键词\" --city 城市"]},
        )
    else:
        output_error(
            command="status",
            message=result.message or "未登录",
            code=ErrorCode.AUTH_REQUIRED,
            hints={"next_actions": ["bco login"]},
        )
