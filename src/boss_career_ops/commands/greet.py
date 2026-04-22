import random
import time

from boss_career_ops.platform.registry import get_active_adapter
from boss_career_ops.hooks.manager import HookManager
from boss_career_ops.config.thresholds import Thresholds
from boss_career_ops.display.error_codes import ErrorCode
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger
from boss_career_ops.evaluator.engine import EvaluationEngine
from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.pipeline.stages import Stage

logger = get_logger(__name__)


def run_greet(security_id: str, job_id: str):
    adapter = get_active_adapter()
    result = adapter.greet(security_id, job_id)
    if result.ok:
        try:
            pm = PipelineManager()
            with pm:
                pm.upsert_job(job_id=job_id, security_id=security_id)
                pm.update_stage(job_id, Stage.COMMUNICATING)
        except Exception as e:
            logger.warning("打招呼阶段推进写入 Pipeline 失败: %s", e)
        output_json(
            command="greet",
            data={"ok": result.ok, "message": result.message, "code": result.code},
            hints={"next_actions": ["bco apply <sid> <jid>", "bco pipeline"]},
        )
    else:
        code = result.code or "GREET_ERROR"
        output_error(
            command="greet",
            message=result.message or "打招呼失败",
            code=code,
            hints={"next_actions": ["bco status"]},
        )


def run_batch_greet(keyword: str, city: str):
    thresholds = Thresholds()
    rl = thresholds.rate_limit
    adapter = get_active_adapter()
    engine = EvaluationEngine()
    params = adapter.build_search_params(keyword, city)
    try:
        jobs = adapter.search(params)
        if not jobs:
            output_error(command="batch-greet", message="搜索失败", code=ErrorCode.SEARCH_ERROR)
            return
        jobs = jobs[:rl.batch_greet_max]
        results = []
        for job in jobs:
            sid = job.security_id
            jid = job.job_id
            if not sid or not jid:
                continue
            evaluation = engine.evaluate(job)
            score = evaluation["total_score"]
            if score < thresholds.auto_action.skip_threshold:
                results.append({
                    "job_name": job.job_name,
                    "result": {"ok": False, "message": f"评分 {score} 低于跳过阈值 {thresholds.auto_action.skip_threshold}", "code": ErrorCode.SKIPPED_LOW_SCORE},
                    "score": score,
                })
                continue
            if thresholds.auto_action.confirm_required and score < thresholds.auto_action.auto_greet_threshold:
                results.append({
                    "job_name": job.job_name,
                    "result": {"ok": False, "message": f"评分 {score} 需人工确认（阈值 {thresholds.auto_action.auto_greet_threshold}）", "code": ErrorCode.CONFIRM_REQUIRED},
                    "score": score,
                })
                continue
            result = adapter.greet(sid, jid)
            results.append({"job_name": job.job_name, "result": {"ok": result.ok, "message": result.message, "code": result.code}, "score": score})
            if result.ok:
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
