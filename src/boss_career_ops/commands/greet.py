import asyncio
import random
import time

from boss_career_ops.boss.api.client import BossClient
from boss_career_ops.boss.browser_client import BrowserClient
from boss_career_ops.hooks.manager import HookManager
from boss_career_ops.config.thresholds import Thresholds
from boss_career_ops.display.error_codes import ErrorCode
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger
from boss_career_ops.evaluator.engine import EvaluationEngine
from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.pipeline.stages import Stage

logger = get_logger(__name__)


async def _greet_single(security_id: str, job_id: str) -> dict:
    hooks = HookManager()
    before_result = await hooks.execute_before("greet_before", {"security_id": security_id, "job_id": job_id})
    if before_result.action.value == "veto":
        return {"ok": False, "message": f"Hook veto: {before_result.reason}", "code": ErrorCode.HOOK_VETO}
    client = BossClient()
    try:
        resp = client.post("greet", json_data={"securityId": security_id, "jobId": job_id})
        if resp.get("code") == 0:
            await hooks.execute_after("greet_after", {"security_id": security_id, "job_id": job_id, "result": "success"})
            return {"ok": True, "message": "打招呼成功"}
        error_code = resp.get("code", "UNKNOWN")
        error_msg = resp.get("message", "打招呼失败")
        if error_code == 7:
            return {"ok": False, "message": "已打过招呼", "code": ErrorCode.ALREADY_GREETED}
        if "limit" in str(error_msg).lower() or error_code == 10003:
            return {"ok": False, "message": "今日打招呼次数用完", "code": ErrorCode.GREET_LIMIT}
        return {"ok": False, "message": error_msg, "code": str(error_code)}
    except Exception as e:
        return {"ok": False, "message": str(e), "code": ErrorCode.NETWORK_ERROR}


def run_greet(security_id: str, job_id: str):
    result = asyncio.run(_greet_single(security_id, job_id))
    if result.get("ok"):
        try:
            pm = PipelineManager()
            with pm:
                pm.upsert_job(job_id=job_id, security_id=security_id)
                pm.update_stage(job_id, Stage.COMMUNICATING)
        except Exception as e:
            logger.warning("打招呼阶段推进写入 Pipeline 失败: %s", e)
        output_json(
            command="greet",
            data=result,
            hints={"next_actions": ["bco apply <sid> <jid>", "bco pipeline"]},
        )
    else:
        code = result.get("code", "GREET_ERROR")
        output_error(
            command="greet",
            message=result.get("message", "打招呼失败"),
            code=code,
            hints={"next_actions": ["bco status"]},
        )


def run_batch_greet(keyword: str, city: str):
    thresholds = Thresholds()
    rl = thresholds.rate_limit
    client = BossClient()
    engine = EvaluationEngine()
    from boss_career_ops.boss.search_filters import build_search_params
    params = build_search_params(keyword, city)
    try:
        resp = client.get("search", params=params)
        if resp.get("code") != 0:
            output_error(command="batch-greet", message="搜索失败", code=ErrorCode.SEARCH_ERROR)
            return
        jobs = resp.get("zpData", {}).get("jobList", [])[:rl.batch_greet_max]
        results = []
        for job in jobs:
            sid = job.get("securityId", "")
            jid = job.get("encryptJobId", "")
            if not sid or not jid:
                continue
            evaluation = engine.evaluate(job)
            score = evaluation["total_score"]
            if score < thresholds.auto_action.skip_threshold:
                results.append({
                    "job_name": job.get("jobName", ""),
                    "result": {"ok": False, "message": f"评分 {score} 低于跳过阈值 {thresholds.auto_action.skip_threshold}", "code": ErrorCode.SKIPPED_LOW_SCORE},
                    "score": score,
                })
                continue
            if thresholds.auto_action.confirm_required and score < thresholds.auto_action.auto_greet_threshold:
                results.append({
                    "job_name": job.get("jobName", ""),
                    "result": {"ok": False, "message": f"评分 {score} 需人工确认（阈值 {thresholds.auto_action.auto_greet_threshold}）", "code": ErrorCode.CONFIRM_REQUIRED},
                    "score": score,
                })
                continue
            result = asyncio.run(_greet_single(sid, jid))
            results.append({"job_name": job.get("jobName", ""), "result": result, "score": score})
            if result.get("ok"):
                try:
                    pm = PipelineManager()
                    with pm:
                        pm.upsert_job(job_id=jid, security_id=sid)
                        pm.update_stage(jid, Stage.COMMUNICATING)
                except Exception as e:
                    logger.warning("批量打招呼阶段推进写入 Pipeline 失败: %s", e)
            mean = (rl.batch_greet_delay_min + rl.batch_greet_delay_max) / 2
            std = (rl.batch_greet_delay_max - rl.batch_greet_delay_min) / 4
            delay = max(rl.batch_greet_delay_min, random.gauss(mean, std))
            time.sleep(delay)
        output_json(
            command="batch-greet",
            data=results,
            hints={"next_actions": ["bco pipeline", "bco follow-up"]},
        )
    except Exception as e:
        output_error(command="batch-greet", message=str(e), code=ErrorCode.BATCH_GREET_ERROR)
