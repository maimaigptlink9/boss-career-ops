import json

from boss_career_ops.errors import Result
from mcp.server import Server
from mcp.types import TextContent, Tool


def _serialize(obj) -> str:
    if isinstance(obj, Result):
        return json.dumps(obj.to_dict(), ensure_ascii=False, indent=2)
    return json.dumps(obj, ensure_ascii=False, indent=2)


def register_tools(app: Server):

    @app.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="search_jobs",
                description="搜索BOSS直聘职位。keyword为搜索关键词，city为城市名。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "keyword": {
                            "type": "string",
                            "description": "搜索关键词",
                        },
                        "city": {
                            "type": "string",
                            "description": "城市名（如'深圳'）",
                            "default": "",
                        },
                    },
                    "required": ["keyword"],
                },
            ),
            Tool(
                name="evaluate_job",
                description="评估职位匹配度。job_id为职位ID，返回评分和等级。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "job_id": {
                            "type": "string",
                            "description": "职位ID",
                        },
                    },
                    "required": ["job_id"],
                },
            ),
            Tool(
                name="generate_resume",
                description="根据职位信息生成定制简历。job_id为职位ID，返回Markdown格式简历。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "job_id": {
                            "type": "string",
                            "description": "职位ID",
                        },
                    },
                    "required": ["job_id"],
                },
            ),
            Tool(
                name="greet_recruiter",
                description="向招聘者打招呼。security_id为安全校验ID，job_id为职位ID。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "security_id": {
                            "type": "string",
                            "description": "安全校验ID",
                        },
                        "job_id": {
                            "type": "string",
                            "description": "职位ID",
                        },
                    },
                    "required": ["security_id", "job_id"],
                },
            ),
            Tool(
                name="apply_job",
                description="投递简历。security_id为安全校验ID，job_id为职位ID。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "security_id": {
                            "type": "string",
                            "description": "安全校验ID",
                        },
                        "job_id": {
                            "type": "string",
                            "description": "职位ID",
                        },
                    },
                    "required": ["security_id", "job_id"],
                },
            ),
            Tool(
                name="get_pipeline",
                description="获取求职流水线数据。stage为阶段筛选（可选）。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "stage": {
                            "type": "string",
                            "description": "阶段筛选（如'discovered','evaluated'等），为空则返回全部",
                            "default": "",
                        },
                    },
                    "required": [],
                },
            ),
            Tool(
                name="get_job_detail",
                description="获取职位详情，含Pipeline中的评估结果。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "job_id": {
                            "type": "string",
                            "description": "职位ID",
                        },
                    },
                    "required": ["job_id"],
                },
            ),
            Tool(
                name="analyze_skill_gap",
                description="分析技能差距，对比个人技能与Pipeline中职位要求。",
                inputSchema={
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            ),
            Tool(
                name="prepare_interview",
                description="准备面试，获取职位信息用于面试准备。",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "job_id": {
                            "type": "string",
                            "description": "职位ID",
                        },
                    },
                    "required": ["job_id"],
                },
            ),
        ]

    @app.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        try:
            if name == "search_jobs":
                from boss_career_ops.agent.tools import search_jobs

                result = search_jobs(
                    arguments.get("keyword", ""),
                    arguments.get("city", ""),
                )
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(result, ensure_ascii=False, indent=2),
                    )
                ]

            elif name == "evaluate_job":
                from boss_career_ops.agent.tools import evaluate_job

                result = evaluate_job(arguments.get("job_id", ""))
                if result is None:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {"error": "职位不存在"}, ensure_ascii=False
                            ),
                        )
                    ]
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(result, ensure_ascii=False, indent=2),
                    )
                ]

            elif name == "generate_resume":
                from boss_career_ops.agent.tools import generate_resume

                result = generate_resume(arguments.get("job_id", ""))
                if result is None:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {"error": "职位不存在"}, ensure_ascii=False
                            ),
                        )
                    ]
                return [TextContent(type="text", text=result)]

            elif name == "greet_recruiter":
                from boss_career_ops.agent.tools import greet_recruiter

                result = greet_recruiter(
                    arguments.get("security_id", ""),
                    arguments.get("job_id", ""),
                )
                return [
                    TextContent(type="text", text=_serialize(result))
                ]

            elif name == "apply_job":
                from boss_career_ops.agent.tools import apply_job

                result = apply_job(
                    arguments.get("security_id", ""),
                    arguments.get("job_id", ""),
                )
                return [
                    TextContent(type="text", text=_serialize(result))
                ]

            elif name == "get_pipeline":
                from boss_career_ops.agent.tools import list_pipeline_jobs

                stage = arguments.get("stage", "") or None
                result = list_pipeline_jobs(stage=stage)
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(result, ensure_ascii=False, indent=2),
                    )
                ]

            elif name == "get_job_detail":
                from boss_career_ops.agent.tools import get_job_detail

                result = get_job_detail(arguments.get("job_id", ""))
                if not result:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps(
                                {"error": "职位不存在"}, ensure_ascii=False
                            ),
                        )
                    ]
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(result, ensure_ascii=False, indent=2),
                    )
                ]

            elif name == "analyze_skill_gap":
                from boss_career_ops.agent.tools import analyze_skill_gap

                result = analyze_skill_gap()
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(result, ensure_ascii=False, indent=2),
                    )
                ]

            elif name == "prepare_interview":
                from boss_career_ops.agent.tools import prepare_interview

                result = prepare_interview(arguments.get("job_id", ""))
                return [
                    TextContent(type="text", text=_serialize(result))
                ]

            else:
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {"error": f"未知工具: {name}"}, ensure_ascii=False
                        ),
                    )
                ]

        except Exception as e:
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {"error": str(e)}, ensure_ascii=False
                    ),
                )
            ]
