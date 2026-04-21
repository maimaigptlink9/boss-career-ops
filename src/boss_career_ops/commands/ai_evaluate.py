"""AI 增强评估命令"""

from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger
from boss_career_ops.boss.api.client import BossClient
from boss_career_ops.cache.store import CacheStore
from boss_career_ops.evaluator.ai_scorer import AIEvaluator
from boss_career_ops.pipeline.manager import PipelineManager

logger = get_logger(__name__)


def run_ai_evaluate(security_id: str | None = None, fetch_detail: bool = True):
    """
    使用 AI 对职位进行评估
    
    Args:
        security_id: 职位 ID（可选，不传则使用缓存的最后一个搜索）
        fetch_detail: 是否获取职位详情
    """
    try:
        # 获取职位数据
        if security_id:
            job = _get_job_by_id(security_id)
            # 如果需要获取详情
            if fetch_detail and job:
                logger.info("获取职位详情：%s", security_id)
                detail = _fetch_job_detail(security_id)
                if detail:
                    # 合并基本信息和详情
                    job = {**job, **detail}
        else:
            job = _get_last_searched_job()

        if not job:
            output_error(
                command="ai-evaluate",
                message="未找到职位数据，请先运行 bco search 或提供 security_id",
                code="JOB_NOT_FOUND",
            )
            return

        # 创建评估器
        ai_evaluator = AIEvaluator()

        # 如果获取了职位详情，进行详细评估
        if fetch_detail and job.get("postDescription"):
            result = ai_evaluator.detailed_evaluate(job)
        else:
            # 只进行匹配度评分
            match_score = ai_evaluator.score_job_match(job)
            result = {
                "scores": {
                    "匹配度": match_score,
                    "薪资": 2.5,
                    "地点": 2.5,
                    "发展": 2.5,
                    "团队": 2.5,
                },
                "total_score": match_score,
                "grade": _score_to_grade(match_score),
                "recommendation": _get_recommendation(match_score),
            }

        # 添加到结果中
        result["job_name"] = job.get("jobName", "")
        result["company_name"] = job.get("brandName", "")
        result["salary_desc"] = job.get("salaryDesc", "")

        # 更新 Pipeline
        try:
            with PipelineManager() as pipeline:
                pipeline.upsert_job(
                    job_id=job.get("expectId", ""),
                    job_name=job.get("jobName", ""),
                    company_name=job.get("brandName", ""),
                    salary_desc=job.get("salaryDesc", ""),
                    security_id=job.get("securityId", ""),
                    data={"ai_evaluated": True},
                )
                if "scores" in result:
                    pipeline.update_score(
                        job.get("securityId"),
                        result.get("total_score", result.get("scores", {}).get("匹配度", 2.5)),
                        result["grade"],
                    )
        except Exception as e:
            logger.warning(f"Pipeline 更新失败：{e}")

        output_json(
            command="ai-evaluate",
            data=result,
            hints={
                "next_actions": [
                    "bco ai-evaluate --detail <security_id>",
                    "bco greet <security_id>",
                ]
            },
        )

    except Exception as e:
        output_error(
            command="ai-evaluate",
            message=f"AI 评估失败：{str(e)}",
            code="AI_EVALUATE_ERROR",
        )


def _get_job_by_id(security_id: str) -> dict | None:
    """根据 security_id 获取职位"""
    with CacheStore() as cache:
        cache_key = f"job:{security_id}"
        return cache.get(cache_key)


def _fetch_job_detail(security_id: str) -> dict | None:
    """调用 API 获取职位详情"""
    try:
        client = BossClient()
        result = client.get("job_detail", params={"securityId": security_id})
        if result.get("ok") and result.get("data"):
            return result["data"]
        logger.warning("获取职位详情失败：%s", result.get("message", ""))
        return None
    except Exception as e:
        logger.error("获取职位详情异常：%s", e)
        return None


def _get_last_searched_job() -> dict | None:
    """获取上次搜索的最后一个职位"""
    with CacheStore() as cache:
        # 正确的缓存键
        search_cache = cache.get("search:last_result")
        if search_cache and isinstance(search_cache, list):
            return search_cache[0] if search_cache else None
    return None


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
