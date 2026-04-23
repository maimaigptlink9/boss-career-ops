import json

from mcp.server import Server
from mcp.types import Resource, ResourceTemplate


def register_resources(app: Server):

    @app.list_resources()
    async def list_resources() -> list[Resource]:
        return [
            Resource(
                uri="bco://profile",
                name="求职者个人档案",
                mimeType="application/json",
            ),
            Resource(
                uri="bco://cv",
                name="求职者简历",
                mimeType="text/markdown",
            ),
        ]

    @app.list_resource_templates()
    async def list_resource_templates() -> list[ResourceTemplate]:
        return [
            ResourceTemplate(
                uriTemplate="bco://pipeline/{stage}",
                name="求职流水线数据",
                mimeType="application/json",
            ),
        ]

    @app.read_resource()
    async def read_resource(uri) -> str:
        uri_str = str(uri)
        if uri_str == "bco://profile":
            from boss_career_ops.agent.tools import get_profile

            return json.dumps(get_profile(), ensure_ascii=False, indent=2)
        elif uri_str == "bco://cv":
            from boss_career_ops.agent.tools import get_cv

            return get_cv()
        elif uri_str.startswith("bco://pipeline/"):
            stage = uri_str.split("/")[-1]
            from boss_career_ops.agent.tools import list_pipeline_jobs

            jobs = list_pipeline_jobs(stage=stage if stage else None)
            return json.dumps(jobs, ensure_ascii=False, indent=2)
        else:
            raise ValueError(f"未知资源: {uri_str}")
