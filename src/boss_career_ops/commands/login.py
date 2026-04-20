from boss_career_ops.boss.auth.manager import AuthManager, _is_admin
from boss_career_ops.display.error_codes import ErrorCode
from boss_career_ops.display.output import output_json, output_error


def run_login():
    manager = AuthManager()
    result = manager.login()
    if result.get("ok"):
        output_json(
            command="login",
            data=result,
            hints={"next_actions": ["bco status", "bco search \"关键词\" --city 城市"]},
        )
    else:
        next_actions = []
        if not _is_admin():
            next_actions.append("以管理员身份运行终端后重试（可自动提取浏览器 Cookie）")
        next_actions.append("用远程调试模式启动 Chrome 后重试: chrome.exe --remote-debugging-port=9222")
        next_actions.append("在弹出的浏览器窗口中完成登录操作")
        output_error(
            command="login",
            message=result.get("message", "登录失败"),
            code=ErrorCode.LOGIN_FAILED,
            hints={"next_actions": next_actions},
        )
