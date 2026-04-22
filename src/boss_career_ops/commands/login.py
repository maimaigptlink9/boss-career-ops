from boss_career_ops.platform.registry import get_active_adapter
from boss_career_ops.display.error_codes import ErrorCode
from boss_career_ops.display.output import output_json, output_error


def run_login():
    adapter = get_active_adapter()
    result = adapter.login()
    if result.ok:
        output_json(
            command="login",
            data={"ok": result.ok, "message": result.message},
            hints={"next_actions": ["bco status", "bco search \"关键词\" --city 城市"]},
        )
    else:
        next_actions = [
            "用远程调试模式启动 Chrome 后重试: chrome.exe --remote-debugging-port=9222",
            "在弹出的浏览器窗口中完成登录操作",
        ]
        output_error(
            command="login",
            message=result.message or "登录失败",
            code=ErrorCode.LOGIN_FAILED,
            hints={"next_actions": next_actions},
        )
