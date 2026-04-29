from boss_career_ops.evaluator.engine import EvaluationEngine
from boss_career_ops.evaluator.report import generate_report
from boss_career_ops.platform.registry import get_active_adapter
from boss_career_ops.cache.store import CacheStore
from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.pipeline.stages import Stage
from boss_career_ops.display.error_codes import ErrorCode
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger
import json

logger = get_logger(__name__)


def run_evaluate(target: str | None, from_search: bool, pending: bool = False):
    engine = EvaluationEngine()
    if pending:
        _evaluate_pending(engine)
    elif from_search:
        _evaluate_from_search(engine)
    elif target:
        _evaluate_single(engine, target)
    else:
        output_error(
            command="evaluate",
            message="请指定评估目标或使用 --from-search / --pending",
            code=ErrorCode.INVALID_PARAM,
            hints={"next_actions": ["bco evaluate <security_id>", "bco evaluate --from-search", "bco evaluate --pending"]},
        )


def _evaluate_single(engine: EvaluationEngine, security_id: str):
    adapter = get_active_adapter()
    try:
        job = adapter.get_job_detail(security_id)
        if job is None:
            output_error(command="evaluate", message="获取职位详情失败", code="DETAIL_ERROR")
            return
        result = engine.evaluate(job)
        report = generate_report(result)
        # 检查 Agent 评估结果
        if job.job_id:
            try:
                with PipelineManager() as pm:
                    ai_result = pm.get_ai_result(job.job_id, "evaluate")
                    if ai_result:
                        ai_data = json.loads(ai_result["result"])
                        result["agent_score"] = ai_data.get("score")
                        result["agent_grade"] = ai_data.get("grade")
                        result["agent_analysis"] = ai_data.get("analysis")
                        result["agent_scores_detail"] = ai_data.get("scores_detail")
                        if ai_data.get("score") is not None and ai_data.get("grade"):
                            result["total_score"] = ai_data["score"]
                            result["grade"] = ai_data["grade"]
                            result["source"] = "agent"
            except Exception as e:
                logger.warning("读取 Agent 评估结果失败: %s", e)
        try:
            pm = PipelineManager()
            with pm:
                if job.job_id:
                    pm.upsert_job(job)
                    pm.update_score(job.job_id, result["total_score"], result["grade"])
                    pm.update_stage(job.job_id, Stage.EVALUATED)
                    pm.update_job_data(job.job_id, {"evaluate_report": report})
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
    results = []
    try:
        pm = PipelineManager()
        with pm:
            pm.batch_add_jobs(jobs)
            for job in jobs:
                result = engine.evaluate(job)
                try:
                    job_id = job.job_id if hasattr(job, "job_id") else job.get("encryptJobId", "")
                    # 检查 Agent 评估结果
                    if job_id:
                        try:
                            ai_result = pm.get_ai_result(job_id, "evaluate")
                            if ai_result:
                                ai_data = json.loads(ai_result["result"])
                                if ai_data.get("score") is not None and ai_data.get("grade"):
                                    result["total_score"] = ai_data["score"]
                                    result["grade"] = ai_data["grade"]
                                    result["source"] = "agent"
                                    result["agent_analysis"] = ai_data.get("analysis")
                        except Exception as e:
                            logger.warning("读取 Agent 评估结果失败: %s", e)
                    if job_id:
                        pm.update_score(job_id, result["total_score"], result["grade"])
                        pm.update_stage(job_id, Stage.EVALUATED)
                        report = generate_report(result)
                        pm.update_job_data(job_id, {"evaluate_report": report})
                except Exception as e:
                    logger.warning("评估结果写入 Pipeline 失败: %s", e)
                results.append(result)
    except Exception as e:
        logger.warning("Pipeline 操作失败: %s", e)
    output_json(
        command="evaluate",
        data=results,
        hints={"next_actions": ["bco auto-action", "bco pipeline"]},
    )


def _evaluate_pending(engine: EvaluationEngine):
    try:
        pm = PipelineManager()
        with pm:
            pending_jobs = pm.get_unevaluated(limit=100)
            if not pending_jobs:
                output_json(
                    command="evaluate",
                    data={"message": "没有未评估的职位", "count": 0},
                )
                return
            logger.info("待评估职位: %d 条", len(pending_jobs))
            results = []
            for job_dict in pending_jobs:
                try:
                    result = engine.evaluate(job_dict)
                    job_id = job_dict.get("job_id", "")
                    if job_id:
                        try:
                            ai_result = pm.get_ai_result(job_id, "evaluate")
                            if ai_result:
                                ai_data = json.loads(ai_result["result"])
                                if ai_data.get("score") is not None and ai_data.get("grade"):
                                    result["total_score"] = ai_data["score"]
                                    result["grade"] = ai_data["grade"]
                                    result["source"] = "agent"
                                    result["agent_analysis"] = ai_data.get("analysis")
                        except Exception as e:
                            logger.warning("读取 Agent 评估结果失败: %s", e)
                        pm.update_score(job_id, result["total_score"], result["grade"])
                        pm.update_stage(job_id, Stage.EVALUATED)
                        report = generate_report(result)
                        pm.update_job_data(job_id, {"evaluate_report": report})
                    results.append({
                        "job_id": job_id,
                        "job_name": job_dict.get("job_name", ""),
                        "company_name": job_dict.get("company_name", ""),
                        "score": result["total_score"],
                        "grade": result["grade"],
                        "recommendation": result.get("recommendation", ""),
                    })
                except Exception as e:
                    logger.warning("评估职位 %s 失败: %s", job_dict.get("job_id", ""), e)
            output_json(
                command="evaluate",
                data={"count": len(results), "results": results},
                hints={"next_actions": ["bco pipeline list", "bco pipeline dismiss --grade D,E"]},
            )
    except Exception as e:
        output_error(command="evaluate", message=str(e), code=ErrorCode.EVALUATE_ERROR)
