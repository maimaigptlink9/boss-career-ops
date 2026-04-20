from boss_career_ops.evaluator.engine import EvaluationEngine
from boss_career_ops.evaluator.report import generate_report
from boss_career_ops.boss.api.client import BossClient
from boss_career_ops.cache.store import CacheStore
from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.pipeline.stages import Stage
from boss_career_ops.display.error_codes import ErrorCode
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger

logger = get_logger(__name__)


def run_evaluate(target: str | None, from_search: bool):
    engine = EvaluationEngine()
    if from_search:
        _evaluate_from_search(engine)
    elif target:
        _evaluate_single(engine, target)
    else:
        output_error(
            command="evaluate",
            message="请指定评估目标或使用 --from-search",
            code=ErrorCode.INVALID_PARAM,
            hints={"next_actions": ["bco evaluate <security_id>", "bco evaluate --from-search"]},
        )


def _evaluate_single(engine: EvaluationEngine, security_id: str):
    client = BossClient()
    try:
        resp = client.get("job_detail", params={"securityId": security_id})
        if resp.get("code") != 0:
            output_error(command="evaluate", message="获取职位详情失败", code="DETAIL_ERROR")
            return
        job = resp.get("zpData", {}).get("jobInfo", {})
        result = engine.evaluate(job)
        report = generate_report(result)
        try:
            pm = PipelineManager()
            with pm:
                job_id = job.get("encryptJobId", "")
                if job_id:
                    pm.upsert_job(
                        job_id=job_id,
                        job_name=job.get("jobName", ""),
                        company_name=job.get("brandName", ""),
                        salary_desc=job.get("salaryDesc", ""),
                        security_id=security_id,
                        data=job,
                    )
                    pm.update_score(job_id, result["total_score"], result["grade"])
                    pm.update_stage(job_id, Stage.EVALUATED)
                    pm.update_job_data(job_id, {"evaluate_report": report})
        except Exception as e:
            logger.warning("评估结果写入 Pipeline 失败: %s", e)
        output_json(
            command="evaluate",
            data={"evaluation": result, "report": report},
            hints={"next_actions": ["bco greet <sid> <jid>", "bco auto-action"]},
        )
    except Exception as e:
        output_error(command="evaluate", message=str(e), code=ErrorCode.EVALUATE_ERROR)


def _evaluate_from_search(engine: EvaluationEngine):
    with CacheStore() as cache:
        jobs = cache.get("search:last_result")
        last_params = cache.get("search:last_params")
    if not jobs:
        output_error(
            command="evaluate",
            message="无上次搜索结果，请先运行 bco search",
            code="NO_SEARCH_RESULT",
            hints={"next_actions": ["bco search <keyword> --city <city>"]},
        )
        return
    logger.info("从缓存加载上次搜索结果: %d 条职位", len(jobs))
    if last_params:
        logger.info("上次搜索参数: keyword=%s, city=%s", last_params.get("keyword"), last_params.get("city"))
    try:
        pm = PipelineManager()
        with pm:
            pm.batch_add_jobs(jobs)
    except Exception as e:
        logger.warning("搜索结果写入 Pipeline 失败: %s", e)
    results = []
    for job in jobs:
        result = engine.evaluate(job)
        try:
            pm = PipelineManager()
            with pm:
                job_id = job.get("encryptJobId", "")
                if job_id:
                    pm.update_score(job_id, result["total_score"], result["grade"])
                    pm.update_stage(job_id, Stage.EVALUATED)
                    report = generate_report(result)
                    pm.update_job_data(job_id, {"evaluate_report": report})
        except Exception as e:
            logger.warning("评估结果写入 Pipeline 失败: %s", e)
        results.append(result)
    output_json(
        command="evaluate",
        data=results,
        hints={"next_actions": ["bco auto-action", "bco pipeline"]},
    )
