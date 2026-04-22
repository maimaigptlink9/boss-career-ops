import random
import time

from boss_career_ops.platform.registry import get_active_adapter
from boss_career_ops.cache.store import CacheStore
from boss_career_ops.config.thresholds import Thresholds
from boss_career_ops.display.error_codes import ErrorCode
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger
from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.evaluator.engine import EvaluationEngine

logger = get_logger(__name__)


def _page_delay(thresholds: Thresholds):
    rl = thresholds.rate_limit
    mean = (rl.search_page_delay_min + rl.search_page_delay_max) / 2
    std = (rl.search_page_delay_max - rl.search_page_delay_min) / 4
    delay = max(rl.search_page_delay_min, random.gauss(mean, std))
    logger.info("翻页延迟 %.1f 秒", delay)
    time.sleep(delay)


def run_search(keyword: str, city: str, welfare: str, page: int, limit: int, pages: int = 1, output: str | None = None):
    adapter = get_active_adapter()
    thresholds = Thresholds()
    rl = thresholds.rate_limit
    if pages < 1:
        pages = 1
    max_pages = min(pages, rl.search_max_pages)
    all_jobs = []
    has_more = False
    for p in range(page, page + max_pages):
        params = adapter.build_search_params(keyword, city, page=p, page_size=limit)
        params["scene"] = "1"
        try:
            jobs = adapter.search(params)
        except Exception as e:
            logger.error("搜索异常: %s", e)
            output_error(
                command="search",
                message=str(e),
                code=ErrorCode.SEARCH_ERROR,
                hints={"next_actions": ["bco status", "bco login"]},
                output=output,
            )
            return
        if welfare:
            jobs = adapter.filter_by_welfare(jobs, welfare)
        all_jobs.extend(jobs)
        has_more = len(jobs) >= limit
        if not has_more:
            break
        if p < page + max_pages - 1:
            _page_delay(thresholds)
    with CacheStore() as cache:
        cache.set("search:last_result", [j.to_dict() for j in all_jobs], ttl=thresholds.cache.search_ttl)
        cache.set("search:last_params", {"keyword": keyword, "city": city, "welfare": welfare}, ttl=thresholds.cache.search_ttl)
    try:
        pm = PipelineManager()
        with pm:
            pm.batch_add_jobs(all_jobs)
            engine = EvaluationEngine()
            eval_limit = 50
            for i, job in enumerate(all_jobs[:eval_limit]):
                try:
                    eval_result = engine.evaluate(job)
                    job_id = job.job_id if hasattr(job, 'job_id') else ""
                    if job_id:
                        pm.update_job_data(job_id, {"evaluation": eval_result})
                except Exception as e:
                    logger.warning("搜索结果自动评分失败: %s", e)
            if len(all_jobs) > eval_limit:
                logger.info("搜索结果超过 %d 条，仅前 %d 条自动评分，其余请手动评估", eval_limit, eval_limit)
        logger.info("已将 %d 条搜索结果写入 Pipeline", len(all_jobs))
    except Exception as e:
        logger.warning("搜索结果写入 Pipeline 失败: %s", e)
    output_json(
        command="search",
        data=[j.to_dict() for j in all_jobs],
        pagination={
            "page": page,
            "pages_fetched": min(max_pages, (page + max_pages) - page),
            "has_more": has_more,
            "total": len(all_jobs),
        },
        hints={"next_actions": ["bco evaluate --from-search", "bco detail <security_id>"]},
        output=output,
    )
