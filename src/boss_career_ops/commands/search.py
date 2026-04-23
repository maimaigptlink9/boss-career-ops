import random
import time

from boss_career_ops.cache.store import CacheStore
from boss_career_ops.config.thresholds import Thresholds
from boss_career_ops.display.error_codes import ErrorCode
from boss_career_ops.display.output import output_json, output_error
from boss_career_ops.display.logger import get_logger
from boss_career_ops.evaluator.engine import EvaluationEngine
from boss_career_ops.pipeline.manager import PipelineManager
from boss_career_ops.platform.registry import get_active_adapter

logger = get_logger(__name__)

EVAL_LIMIT = 50


def run_search(
    keyword: str,
    city: str,
    welfare: str,
    page: int,
    limit: int,
    pages: int,
    output: str | None = None,
):
    thresholds = Thresholds()
    adapter = get_active_adapter()
    params = adapter.build_search_params(keyword, city, page_size=limit)
    all_jobs = []
    max_pages = min(pages, thresholds.rate_limit.search_max_pages)

    for p in range(page, page + max_pages):
        params["page"] = p
        try:
            jobs = adapter.search(params)
        except Exception as e:
            logger.error("搜索第 %d 页失败: %s", p, e)
            break
        if not jobs:
            break
        if welfare:
            jobs = adapter.filter_by_welfare(jobs, welfare)
        all_jobs.extend(jobs)
        if p < page + max_pages - 1:
            mean = (thresholds.rate_limit.search_page_delay_min + thresholds.rate_limit.search_page_delay_max) / 2
            std = (thresholds.rate_limit.search_page_delay_max - thresholds.rate_limit.search_page_delay_min) / 4
            delay = max(thresholds.rate_limit.search_page_delay_min, random.gauss(mean, std))
            time.sleep(delay)

    if not all_jobs:
        output_error(command="search", message="搜索失败或无结果", code=ErrorCode.SEARCH_ERROR)
        return

    engine = EvaluationEngine()
    eval_jobs = all_jobs[:EVAL_LIMIT]
    for job in eval_jobs:
        try:
            evaluation = engine.evaluate(job)
            job_data = {"evaluation": evaluation}
            try:
                pm = PipelineManager()
                with pm:
                    pm.upsert_job(
                        job_id=job.job_id,
                        security_id=job.security_id,
                    )
                    pm.update_score(job.job_id, evaluation["total_score"], evaluation["grade"])
                    pm.update_job_data(job.job_id, job_data)
            except Exception as e:
                logger.warning("搜索结果写入 Pipeline 失败: %s", e)
        except Exception as e:
            logger.warning("职位 %s 评估失败: %s", job.job_id, e)

    try:
        pm = PipelineManager()
        with pm:
            pm.batch_add_jobs(all_jobs)
    except Exception as e:
        logger.warning("搜索结果批量写入 Pipeline 失败: %s", e)

    output_data = [j.to_dict() for j in all_jobs]
    if output:
        from pathlib import Path
        out_path = Path(output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        import json
        out_path.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")
        output_json(
            command="search",
            data={"count": len(all_jobs), "output": str(out_path)},
            hints={"next_actions": ["bco evaluate --from-search", "bco greet <sid> <jid>"]},
        )
    else:
        output_json(
            command="search",
            data=output_data,
            hints={"next_actions": ["bco evaluate --from-search", "bco greet <sid> <jid>"]},
        )
