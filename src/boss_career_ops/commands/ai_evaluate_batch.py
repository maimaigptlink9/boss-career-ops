"""批量 AI 评估命令"""

from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger
from boss_career_ops.boss.api.client import BossClient
from boss_career_ops.cache.store import CacheStore
from boss_career_ops.evaluator.ai_scorer import AIEvaluator
from boss_career_ops.pipeline.manager import PipelineManager

logger = get_logger(__name__)


def run_ai_evaluate_batch(limit: int = 10):
    """
    对缓存中的职位进行批量 AI 评估
    
    Args:
        limit: 最多评估多少个职位
    """
    try:
        # 获取缓存的搜索结果
        with CacheStore() as cache:
            jobs = cache.get("search:last_result")
            if not jobs or not isinstance(jobs, list):
                output_error(
                    command="ai-evaluate-batch",
                    message="未找到缓存的搜索结果，请先运行 bco search",
                    code="JOB_NOT_FOUND",
                )
                return

        logger.info("从缓存加载 %d 个职位，准备评估前 %d 个", len(jobs), limit)

        # 创建评估器和客户端
        ai_evaluator = AIEvaluator()
        client = BossClient()
        results = []

        # 逐个评估
        for i, job in enumerate(jobs[:limit]):
            security_id = job.get("securityId", "")
            logger.info("[%d/%d] 评估职位：%s - %s", i + 1, limit, job.get("jobName", ""), job.get("brandName", ""))

            # 获取职位详情
            detail = None
            try:
                detail_result = client.get("job_detail", params={"securityId": security_id})
                if detail_result.get("ok") and detail_result.get("data"):
                    detail = detail_result["data"]
            except Exception as e:
                logger.warning("获取职位详情失败：%s", e)

            # 合并数据
            if detail:
                full_job = {**job, **detail}
            else:
                full_job = job

            # AI 评估
            eval_result = ai_evaluator.detailed_evaluate(full_job) if detail else ai_evaluator.score_job_match(full_job)

            # 构建结果
            result_entry = {
                "job_name": job.get("jobName", ""),
                "company_name": job.get("brandName", ""),
                "salary_desc": job.get("salaryDesc", ""),
                "security_id": security_id,
            }

            # 合并评估结果
            if isinstance(eval_result, dict):
                result_entry.update(eval_result)
            else:
                # 如果是分数
                result_entry["scores"] = {"匹配度": eval_result}
                result_entry["total_score"] = eval_result
                result_entry["grade"] = _score_to_grade(eval_result)
                result_entry["recommendation"] = _get_recommendation(eval_result)

            results.append(result_entry)

            # 更新 Pipeline
            try:
                with PipelineManager() as pipeline:
                    pipeline.upsert_job(
                        job_id=job.get("expectId", ""),
                        job_name=job.get("jobName", ""),
                        company_name=job.get("brandName", ""),
                        salary_desc=job.get("salaryDesc", ""),
                        security_id=security_id,
                        data={"ai_evaluated": True, "has_detail": bool(detail)},
                    )
                    if "total_score" in result_entry:
                        pipeline.update_score(security_id, result_entry["total_score"], result_entry["grade"])
            except Exception as e:
                logger.warning("Pipeline 更新失败：%s", e)

        # 输出结果
        output_json(
            command="ai-evaluate-batch",
            data={
                "evaluated_count": len(results),
                "results": results,
            },
            hints={
                "next_actions": [
                    "bco pipeline",
                    "bco greet <security_id>",
                ]
            },
        )

    except Exception as e:
        output_error(
            command="ai-evaluate-batch",
            message=f"批量评估失败：{str(e)}",
            code="AI_BATCH_ERROR",
        )


def _score_to_grade(score: float) -> str:
    """分数转等级"""
    if score >= 4.5:
        return "A"
    elif score >= 3.5:
        return "B"
    elif score >= 2.5:
        return "C"
    elif score >= 1.5:
        return "D"
    else:
        return "F"


def _get_recommendation(score: float) -> str:
    """获取推荐建议"""
    if score >= 4.5:
        return "强烈推荐！立即行动，优先投递"
    elif score >= 3.5:
        return "值得投入，建议优先处理"
    elif score >= 2.5:
        return "一般匹配，需人工判断是否值得投入"
    elif score >= 1.5:
        return "匹配度低，谨慎考虑"
    else:
        return "不推荐，建议跳过"
