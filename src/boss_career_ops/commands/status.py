from boss_career_ops.boss.auth.manager import AuthManager
from boss_career_ops.display.error_codes import ErrorCode
from boss_career_ops.display.output import output_json, output_error


def run_status():
    manager = AuthManager()
    result = manager.check_status()
    if result.get("ok"):
        output_json(
            command="status",
            data={"logged_in": True, "message": result["message"]},
            hints={"next_actions": ["bco search \"关键词\" --city 城市"]},
        )
    else:
        output_error(
            command="status",
            message=result.get("message", "未登录"),
            code=ErrorCode.AUTH_REQUIRED,
            hints={"next_actions": ["bco login"]},
        )
