import asyncio

from boss_career_ops.boss.api.client import BossClient
from boss_career_ops.hooks.manager import HookManager
from boss_career_ops.display.error_codes import ErrorCode
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger
from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.pipeline.stages import Stage

logger = get_logger(__name__)


async def _apply_single(security_id: str, job_id: str) -> dict:
    hooks = HookManager()
    before_result = await hooks.execute_before("apply_before", {"security_id": security_id, "job_id": job_id})
    if before_result.action.value == "veto":
        return {"ok": False, "message": f"Hook veto: {before_result.reason}", "code": ErrorCode.HOOK_VETO}
    client = BossClient()
    try:
        resp = client.post("apply", json_data={"securityId": security_id, "jobId": job_id})
        if resp.get("code") == 0:
            await hooks.execute_after("apply_after", {"security_id": security_id, "job_id": job_id, "result": "success"})
            return {"ok": True, "message": "投递成功"}
        return {"ok": False, "message": resp.get("message", "投递失败"), "code": str(resp.get("code", "UNKNOWN"))}
    except Exception as e:
        return {"ok": False, "message": str(e), "code": ErrorCode.NETWORK_ERROR}


def run_apply(security_id: str, job_id: str):
    result = asyncio.run(_apply_single(security_id, job_id))
    if result.get("ok"):
        try:
            pm = PipelineManager()
            with pm:
                pm.upsert_job(job_id=job_id, security_id=security_id)
                pm.update_stage(job_id, Stage.APPLIED)
        except Exception as e:
            logger.warning("投递阶段推进写入 Pipeline 失败: %s", e)
        output_json(
            command="apply",
            data=result,
            hints={"next_actions": ["bco pipeline", "bco follow-up"]},
        )
    else:
        output_error(
            command="apply",
            message=result.get("message", "投递失败"),
            code=result.get("code", "APPLY_ERROR"),
            hints={"next_actions": ["bco status", "bco login"]},
        )
