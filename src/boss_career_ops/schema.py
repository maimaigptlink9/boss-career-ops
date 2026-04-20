COMMANDS = [
    {
        "name": "doctor",
        "description": "环境诊断，检查依赖、配置、登录态",
        "usage": "bco doctor",
        "params": [],
    },
    {
        "name": "setup",
        "description": "初始化配置（首次使用）",
        "usage": "bco setup",
        "params": [],
    },
    {
        "name": "login",
        "description": "登录 BOSS 直聘（4 级降级：Cookie→CDP→QR→patchright）",
        "usage": "bco login",
        "params": [],
    },
    {
        "name": "status",
        "description": "检查登录态",
        "usage": "bco status",
        "params": [],
    },
    {
        "name": "search",
        "description": "搜索职位 + 8 维筛选 + 福利过滤",
        "usage": "bco search <keyword> --city <city> --welfare <welfare>",
        "params": [
            {"name": "keyword", "type": "str", "required": True, "description": "搜索关键词"},
            {"name": "--city", "type": "str", "required": False, "description": "城市筛选"},
            {"name": "--welfare", "type": "str", "required": False, "description": "福利筛选（逗号分隔）"},
            {"name": "--page", "type": "int", "required": False, "description": "页码"},
            {"name": "--limit", "type": "int", "required": False, "description": "每页数量"},
            {"name": "--pages", "type": "int", "required": False, "description": "连续获取页数"},
        ],
    },
    {
        "name": "recommend",
        "description": "基于个人档案的个性化推荐",
        "usage": "bco recommend",
        "params": [],
    },
    {
        "name": "evaluate",
        "description": "5 维评估（匹配度/薪资/地点/发展/团队）",
        "usage": "bco evaluate <security_id> 或 bco evaluate --from-search",
        "params": [
            {"name": "target", "type": "str", "required": False, "description": "security_id"},
            {"name": "--from-search", "type": "flag", "required": False, "description": "对上次搜索结果批量评估"},
        ],
    },
    {
        "name": "auto-action",
        "description": "阈值驱动自动执行（高分自动打招呼/投递）",
        "usage": "bco auto-action",
        "params": [],
    },
    {
        "name": "greet",
        "description": "打招呼",
        "usage": "bco greet <security_id> <job_id>",
        "params": [
            {"name": "security_id", "type": "str", "required": True},
            {"name": "job_id", "type": "str", "required": True},
        ],
    },
    {
        "name": "batch-greet",
        "description": "批量打招呼（高斯延迟，最大 10 个）",
        "usage": "bco batch-greet <keyword> --city <city>",
        "params": [
            {"name": "keyword", "type": "str", "required": True},
            {"name": "--city", "type": "str", "required": False},
        ],
    },
    {
        "name": "apply",
        "description": "投递简历",
        "usage": "bco apply <security_id> <job_id>",
        "params": [
            {"name": "security_id", "type": "str", "required": True},
            {"name": "job_id", "type": "str", "required": True},
        ],
    },
    {
        "name": "resume",
        "description": "生成定制简历（MD/PDF）",
        "usage": "bco resume <job_id> --format <md|pdf>",
        "params": [
            {"name": "job_id", "type": "str", "required": True},
            {"name": "--format", "type": "choice", "required": False, "description": "输出格式 md/pdf"},
        ],
    },
    {
        "name": "chat",
        "description": "聊天管理 + 导出",
        "usage": "bco chat [--export csv|json]",
        "params": [
            {"name": "--export", "type": "choice", "required": False, "description": "导出格式"},
        ],
    },
    {
        "name": "chatmsg",
        "description": "聊天消息历史",
        "usage": "bco chatmsg <security_id>",
        "params": [
            {"name": "security_id", "type": "str", "required": True},
        ],
    },
    {
        "name": "chat-summary",
        "description": "聊天摘要",
        "usage": "bco chat-summary <security_id>",
        "params": [
            {"name": "security_id", "type": "str", "required": True},
        ],
    },
    {
        "name": "mark",
        "description": "联系人标签",
        "usage": "bco mark <security_id> --tag <tag>",
        "params": [
            {"name": "security_id", "type": "str", "required": True},
            {"name": "--tag", "type": "str", "required": True},
        ],
    },
    {
        "name": "exchange",
        "description": "交换联系方式",
        "usage": "bco exchange <security_id> --type <phone|wechat>",
        "params": [
            {"name": "security_id", "type": "str", "required": True},
            {"name": "--type", "type": "choice", "required": True, "description": "phone/wechat"},
        ],
    },
    {
        "name": "pipeline",
        "description": "求职流水线追踪",
        "usage": "bco pipeline",
        "params": [],
    },
    {
        "name": "follow-up",
        "description": "跟进提醒",
        "usage": "bco follow-up",
        "params": [],
    },
    {
        "name": "digest",
        "description": "每日摘要",
        "usage": "bco digest",
        "params": [],
    },
    {
        "name": "watch",
        "description": "增量监控（add/list/remove/run）",
        "usage": "bco watch add <name> <keyword> --city <city>",
        "params": [
            {"name": "subcommand", "type": "str", "required": True, "description": "add/list/remove/run"},
        ],
    },
    {
        "name": "shortlist",
        "description": "精选列表（B 级及以上）",
        "usage": "bco shortlist",
        "params": [],
    },
    {
        "name": "export",
        "description": "多格式导出（CSV/JSON/HTML/Markdown）",
        "usage": "bco export <keyword> -o <output> --format <fmt>",
        "params": [
            {"name": "keyword", "type": "str", "required": True},
            {"name": "--city", "type": "str", "required": False},
            {"name": "-o", "type": "str", "required": False, "description": "输出文件路径"},
            {"name": "--count", "type": "int", "required": False, "description": "导出数量"},
            {"name": "--format", "type": "choice", "required": False, "description": "csv/json/html/md"},
        ],
    },
    {
        "name": "interview",
        "description": "面试准备",
        "usage": "bco interview <job_id>",
        "params": [
            {"name": "job_id", "type": "str", "required": True},
        ],
    },
    {
        "name": "negotiate",
        "description": "薪资谈判辅助",
        "usage": "bco negotiate <job_id>",
        "params": [
            {"name": "job_id", "type": "str", "required": True},
        ],
    },
    {
        "name": "dashboard",
        "description": "启动 TUI Dashboard",
        "usage": "bco dashboard",
        "params": [],
    },
    {
        "name": "ai-config",
        "description": "AI 配置管理（设置 API Key、模型等）",
        "usage": "bco ai-config --api-key <key> --model <model>",
        "params": [
            {"name": "--api-key", "type": "str", "required": False, "description": "API Key"},
            {"name": "--base-url", "type": "str", "required": False, "description": "API Base URL"},
            {"name": "--model", "type": "str", "required": False, "description": "模型名称"},
            {"name": "--provider", "type": "str", "required": False, "description": "Provider 类型"},
            {"name": "--max-tokens", "type": "int", "required": False, "description": "最大 token 数"},
            {"name": "--temperature", "type": "float", "required": False, "description": "温度参数"},
            {"name": "--show", "type": "flag", "required": False, "description": "显示当前配置"},
        ],
    },
]


def get_all_commands() -> list[dict]:
    return COMMANDS


def get_command(name: str) -> dict | None:
    for cmd in COMMANDS:
        if cmd["name"] == name:
            return cmd
    return None
